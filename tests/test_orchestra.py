"""Tests for the orchestra skeleton. Run: python3 -m unittest tests.test_orchestra -v"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestra.agent import AGENT_MARKER, Agent, Tool                    # noqa: E402
from orchestra.compress import compact_messages, trim                  # noqa: E402
from orchestra.data import DataError, Params, fill, load_records, write_records   # noqa: E402
from orchestra.mcp import connect_all                                  # noqa: E402
from orchestra.pipeline import Stage, build_steps, collect             # noqa: E402
from orchestra.triage import Rule, Triage, when_text                   # noqa: E402
from orchestra.config import load_env, mock_models, tier_models        # noqa: E402
from orchestra.ledger import Ledger                                    # noqa: E402
from orchestra.orchestrator import Orchestrator, Step, build_context   # noqa: E402
from orchestra.permissions import Approvals, Audit, Decision, Gate, Identity   # noqa: E402
from orchestra.providers import AnthropicProvider, ClaudeCodeProvider, MockProvider, Usage   # noqa: E402
from orchestra.router import BudgetExceeded, RoutePolicy, parse_json   # noqa: E402
from orchestra.scenarios import load as load_scenario                  # noqa: E402

MODELS = mock_models()


def ctx_with(responder, baseline="medium"):
    return build_context(provider=MockProvider(responder), models=MODELS, persist=False,
                         approvals=Approvals(), baseline=baseline)


def ident(**kw) -> Identity:
    base = dict(name="a", role="r", owner="sami", tools=frozenset({"kb.*"}), budget_usd=1.0)
    base.update(kw)
    return Identity(**base)


def final(answer="x", confidence=0.9, **extra) -> str:
    return json.dumps({"answer": answer, "confidence": confidence, **extra})


def is_agent(system: str, name: str) -> bool:
    """The role marker sits at the end of the system prompt so the shared opening stays cacheable."""
    return system.rstrip().endswith(AGENT_MARKER + name)


class RouterCascade(unittest.TestCase):
    def test_low_confidence_escalates_small_to_medium_to_large(self):
        seen = []

        def responder(model, system, messages):
            seen.append(model)
            return final(confidence=0.3 if "large" not in model else 0.9)
        ctx = ctx_with(responder)
        r = ctx.router.complete(ident(), "sys", [{"role": "user", "content": "q"}], RoutePolicy(), "run")
        self.assertEqual(seen, ["mock-small", "mock-medium", "mock-large"])
        self.assertEqual(r.tier, "large")
        self.assertEqual(r.escalations, 2)

    def test_confident_answer_stays_on_small(self):
        ctx = ctx_with(lambda m, s, msgs: final(confidence=0.95))
        r = ctx.router.complete(ident(), "sys", [{"role": "user", "content": "q"}], RoutePolicy(), "run")
        self.assertEqual(r.tier, "small")
        self.assertEqual(ctx.ledger.calls_by_tier(), {"small": 1})

    def test_max_tier_caps_the_ladder(self):
        ctx = ctx_with(lambda m, s, msgs: final(confidence=0.1))
        r = ctx.router.complete(ident(), "sys", [{"role": "user", "content": "q"}],
                                RoutePolicy(max_tier="medium"), "run")
        self.assertEqual(r.tier, "medium")

    def test_identical_prompt_hits_local_cache_and_costs_nothing(self):
        ctx = ctx_with(lambda m, s, msgs: final())
        msgs = [{"role": "user", "content": "same   question"}]
        ctx.router.complete(ident(), "sys", msgs, RoutePolicy(), "run")
        r2 = ctx.router.complete(ident(), "sys", [{"role": "user", "content": "same question"}], RoutePolicy(), "run")
        self.assertTrue(r2.cache_hit)
        self.assertEqual(ctx.ledger.entries[-1].cost_usd, 0.0)
        self.assertGreater(ctx.ledger.entries[-1].baseline_usd, 0.0)

    def test_repeat_after_escalation_skips_the_whole_ladder(self):
        seen = []

        def responder(model, system, messages):
            seen.append(model)
            return final(confidence=0.2 if "small" in model else 0.9)
        ctx = ctx_with(responder)
        msgs = [{"role": "user", "content": "hard"}]
        ctx.router.complete(ident(), "sys", msgs, RoutePolicy(), "run")
        r2 = ctx.router.complete(ident(), "sys", msgs, RoutePolicy(), "run")
        self.assertEqual(seen, ["mock-small", "mock-medium"])
        self.assertTrue(r2.cache_hit)

    def test_budget_covers_small_but_stops_before_medium(self):
        seen = []

        def responder(model, system, messages):
            seen.append(model)
            return final(confidence=0.2)
        ctx = ctx_with(responder)
        who = ident(budget_usd=0.000001)         # one small call fits (cost is a few micro-dollars), no second
        with self.assertRaises(BudgetExceeded):
            ctx.router.complete(who, "sys", [{"role": "user", "content": "q" * 400}], RoutePolicy(), "run")
        self.assertEqual(seen, ["mock-small"])
        self.assertEqual(ctx.audit.count("budget_stop"), 1)


class Permissions(unittest.TestCase):
    def setUp(self):
        self.audit = Audit(None)

    def test_tool_outside_allowlist_is_denied(self):
        gate = Gate(self.audit, Approvals())
        v = gate.check_tool(ident(tools=frozenset({"kb.*"})), "refund.issue", {}, "run")
        self.assertIs(v.decision, Decision.DENY)

    def test_tool_with_foreign_data_class_is_denied_even_if_allowlisted(self):
        gate = Gate(self.audit, Approvals())
        v = gate.check_tool(ident(tools=frozenset({"data.*"}), data_classes=frozenset({"customer"})),
                            "data.export", {}, "run", data_class="pii")
        self.assertIs(v.decision, Decision.DENY)
        self.assertIn("pii", v.reason)

    def test_tool_needing_approval_is_queued_with_its_arguments(self):
        approvals = Approvals()
        gate = Gate(self.audit, approvals)
        v = gate.check_tool(ident(tools=frozenset({"mail.send"}), needs_approval=frozenset({"mail.send"})),
                            "mail.send", {"to": "x@y", "body": "b" * 300}, "run")
        self.assertIs(v.decision, Decision.ASK)
        self.assertEqual(approvals.queue[0]["args"]["to"], "x@y")
        self.assertLess(len(approvals.queue[0]["args"]["body"]), 130)

    def test_human_approval_allows(self):
        gate = Gate(self.audit, Approvals(handler=lambda i, t, a: True))
        v = gate.check_tool(ident(tools=frozenset({"mail.send"}), needs_approval=frozenset({"mail.send"})),
                            "mail.send", {}, "run")
        self.assertIs(v.decision, Decision.ALLOW)

    def test_audit_never_stores_prompt_text(self):
        gate = Gate(self.audit, Approvals())
        gate.check_tool(ident(), "kb.search", {"query": "SECRET-PROMPT-TEXT"}, "run")
        self.assertNotIn("SECRET-PROMPT-TEXT", json.dumps(self.audit.events))


class AgentLoop(unittest.TestCase):
    def test_agent_calls_allowed_tool_then_finishes(self):
        calls = {"n": 0}

        def responder(model, system, messages):
            last = str(messages[-1]["content"])
            if last.startswith("{") and "result" in last:
                return final("done")
            return json.dumps({"tool": "kb.search", "args": {"query": "x"}})

        def kb(query=""):
            calls["n"] += 1
            return {"hits": [query]}
        ctx = ctx_with(responder)
        agent = Agent(ident(), "You are the T agent.", tools=[Tool("kb.search", "d", kb)])
        r = agent.run("task", ctx)
        self.assertEqual(r.answer, "done")
        self.assertEqual(calls["n"], 1)
        self.assertEqual(r.tools_used, ["kb.search"])

    def test_registry_tool_is_visible_but_denied_and_never_executed(self):
        ran = {"n": 0}

        def responder(model, system, messages):
            self.assertIn("refund.issue", system)          # the model knows the tool exists
            last = str(messages[-1]["content"])
            if "denied" in last:
                return final(None, escalate=True, reason="no rights")
            return json.dumps({"tool": "refund.issue", "args": {"amount": 1}})

        def refund(amount=0):
            ran["n"] += 1
        registry = {"refund.issue": Tool("refund.issue", "d", refund, data_class="financial")}
        ctx = ctx_with(responder)
        agent = Agent(ident(tools=frozenset({"kb.*"})), "You are the T agent.", tools=[], registry=registry)
        r = agent.run("task", ctx)
        self.assertEqual(ran["n"], 0)
        self.assertTrue(r.escalate)
        self.assertEqual(r.denied[0]["decision"], "deny")

    def test_shared_text_comes_first_and_the_role_marker_last(self):
        a = Agent(ident(name="probe"), "role text", shared="POLICY TEXT")
        blocks = a.system_blocks()
        self.assertTrue(blocks[0].startswith("POLICY TEXT"))       # the part every agent shares, first
        self.assertTrue(blocks[-1].rstrip().endswith(AGENT_MARKER + "probe"))
        b = Agent(ident(name="other"), "different role", shared="POLICY TEXT")
        self.assertEqual(a.system_blocks()[0], b.system_blocks()[0])  # so two roles share one cache entry

    def test_step_limit_escalates_to_human(self):
        ctx = ctx_with(lambda m, s, msgs: json.dumps({"tool": "kb.search", "args": {}}))
        agent = Agent(ident(max_steps=2), "You are the T agent.", tools=[Tool("kb.search", "d", lambda **k: {})])
        r = agent.run("task", ctx)
        self.assertTrue(r.to_human)
        self.assertEqual(r.steps, 2)


class OrchestratorWaves(unittest.TestCase):
    def test_dependencies_run_in_order_and_context_flows(self):
        order = []

        def responder(model, system, messages):
            content = str(messages[-1]["content"])
            order.append(content[:20])
            return final("A:" + content[-5:])
        ctx = ctx_with(responder)
        a = Agent(ident(name="a"), "A")
        b = Agent(ident(name="b"), "B")
        orch = Orchestrator([a, b], ctx)
        res = orch.run([Step("s1", "a", "first"), Step("s2", "b", "second", depends_on=["s1"], context_from=["s1"])])
        self.assertIn("A:", res["s2"].answer)
        self.assertTrue(order[0].startswith("first"))
        self.assertTrue(order[1].startswith("[a]"))

    def test_chain_stops_after_a_step_went_to_a_human(self):
        def responder(model, system, messages):
            if is_agent(system, "a"):
                return final(None, escalate=True, reason="needs a person")
            return final("should not run")
        ctx = ctx_with(responder)
        orch = Orchestrator([Agent(ident(name="a"), "A"), Agent(ident(name="b"), "B")], ctx)
        res = orch.run([Step("s1", "a", "t"), Step("s2", "b", "t", depends_on=["s1"]),
                        Step("s3", "b", "t", depends_on=["s2"])])
        self.assertTrue(res["s2"].skipped and res["s3"].skipped)
        self.assertTrue(res["s2"].blocked_by_human and res["s3"].blocked_by_human)
        self.assertEqual(ctx.ledger.model_calls, 1)
        self.assertEqual(ctx.audit.count("step_skipped"), 2)

    def test_cycle_is_reported_not_hung(self):
        ctx = ctx_with(lambda m, s, msgs: "{}")
        orch = Orchestrator([Agent(ident(name="a"), "x")], ctx)
        with self.assertRaises(RuntimeError):
            orch.run([Step("s1", "a", "t", depends_on=["s2"]), Step("s2", "a", "t", depends_on=["s1"])])

    def test_export_writes_json_without_prompt_text(self):
        ctx = ctx_with(lambda m, s, msgs: final("hello"))
        orch = Orchestrator([Agent(ident(name="a"), "SECRET-SYSTEM-PROMPT")], ctx)
        orch.run([Step("s1", "a", "SECRET-TASK-TEXT")])
        path = orch.export(Path(__file__).parent / "_run_test.json", label="t")
        try:
            doc = json.loads(path.read_text())
            self.assertEqual(doc["steps"][0]["agent"], "a")
            self.assertNotIn("SECRET-SYSTEM-PROMPT", path.read_text())
            self.assertNotIn("SECRET-TASK-TEXT", path.read_text())
        finally:
            path.unlink()


class LedgerMath(unittest.TestCase):
    def test_savings_against_baseline_model(self):
        ledger = Ledger(MODELS["large"])
        ledger.record("r", "a", MODELS["small"], Usage(1_000_000, 100_000))
        self.assertAlmostEqual(ledger.total_cost, 1 + 0.5)          # $1 in + $0.5 out at small
        self.assertAlmostEqual(ledger.total_baseline, 5 + 2.5)      # same tokens at large
        self.assertAlmostEqual(ledger.savings_pct, 80.0)

    def test_provider_cache_read_is_discounted(self):
        ledger = Ledger(MODELS["large"])
        e = ledger.record("r", "a", MODELS["small"], Usage(0, 0, cache_read_tokens=1_000_000))
        self.assertAlmostEqual(e.cost_usd, 0.1)

    def test_reported_cost_beats_the_price_table(self):
        ledger = Ledger(MODELS["large"])
        e = ledger.record("r", "a", MODELS["small"], Usage(1000, 10, cost_usd_reported=0.42))
        self.assertAlmostEqual(e.cost_usd, 0.42)

    def test_headline_separates_calls_and_cache_hits(self):
        ledger = Ledger(MODELS["large"])
        ledger.record("r", "a", MODELS["small"], Usage(10, 10))
        ledger.record("r", "a", MODELS["small"], Usage(10, 10), local_cache_hit=True)
        self.assertIn("1 model calls and 1 cache hits", ledger.headline())


class ScenarioSupport(unittest.TestCase):
    def test_offline_routed_run_is_clean_and_measured_comparison_saves(self):
        scn = load_scenario("support")
        provider = MockProvider(scn.mock_responder(MODELS))
        params = Params.parse([], scn.DEFAULTS)
        records = scn.source(params)
        results = {}
        for mode in ("routed", "baseline"):
            ctx = build_context(provider=provider, models=MODELS, persist=False, approvals=Approvals())
            registry = scn.make_tools(params)
            agents = scn.agents(registry)
            if mode == "baseline":
                for a in agents:
                    a.policy = RoutePolicy(start_tier="large", max_tier="large", min_confidence=0.0)
            orch = Orchestrator(agents, ctx)
            orch.run(build_steps(records, scn.stages(), params))
            outcomes = collect(orch.results, records, scn.stages())
            suite = scn.suite(registry, records)
            suite.run(lambda inputs, c=ctx, o=outcomes: scn.outcome(o, inputs["tid"], c), compare=scn.compare,
                      escalated=lambda out: bool(out and (out.get("human") or out.get("approval_queued"))))
            results[mode] = (orch, ctx, suite)
        r_orch, r_ctx, r_suite = results["routed"]
        b_orch, b_ctx, b_suite = results["baseline"]
        self.assertTrue(r_suite.clean and r_suite.accuracy == 1.0)
        self.assertTrue(b_suite.clean and b_suite.accuracy == 1.0)
        self.assertGreaterEqual(r_orch.denied_count, 1)                 # an agent tried refund.issue and was refused
        self.assertTrue(any(q["tool"] == "mail.send" for q in r_ctx.approvals.queue))
        self.assertTrue(all(str(q["step"]).endswith("_writer") for q in r_ctx.approvals.queue))
        self.assertLess(r_ctx.ledger.total_cost, b_ctx.ledger.total_cost)
        self.assertEqual(r_ctx.ledger.calls_by_tier().get("large", 0), 0)

    def test_duplicate_ticket_in_the_same_wave_costs_one_call(self):
        scn = load_scenario("support")
        params = Params.parse([], scn.DEFAULTS)
        ctx = build_context(provider=MockProvider(scn.mock_responder(MODELS)), models=MODELS, persist=False,
                            approvals=Approvals())
        registry = scn.make_tools(params)
        orch = Orchestrator(scn.agents(registry), ctx, max_workers=8)
        orch.run(build_steps(scn.source(params), scn.stages(), params))
        t1, t3 = orch.results["t1_intake"], orch.results["t3_intake"]        # identical text, same wave
        self.assertEqual(t1.answer, t3.answer)
        self.assertEqual(t1.cache_hits + t3.cache_hits, 1)                   # one asked, one waited

    def test_t4_expected_figure_comes_from_the_oracle(self):
        scn = load_scenario("support")
        registry = scn.make_tools(Params.parse([], scn.DEFAULTS))
        if "calc.tax" not in registry:
            self.skipTest("spine/ not present")
        suite = scn.suite(registry)
        t4 = next(c for c in suite.cases if c.name == "t4")
        self.assertEqual(t4.expected["lohnsteuer_eur"], "9634.00")


class ClaudeCodeFlattening(unittest.TestCase):
    def test_single_message_is_passed_verbatim(self):
        self.assertEqual(ClaudeCodeProvider.flatten([{"role": "user", "content": "hi"}]), "hi")

    def test_history_is_flattened_with_roles(self):
        out = ClaudeCodeProvider.flatten([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
        self.assertIn("[user]\na", out)
        self.assertIn("[assistant]\nb", out)


class Helpers(unittest.TestCase):
    def test_parse_json_tolerates_prose_and_fences(self):
        self.assertEqual(parse_json('Sure:\n```json\n{"a": 1}\n```')["a"], 1)
        self.assertIsNone(parse_json("no json here"))

    def test_trim_keeps_head_and_tail_and_says_so(self):
        out = trim("a" * 100 + "b" * 100, 50)
        self.assertTrue(out.startswith("a") and out.endswith("b") and "trimmed" in out)

    def test_compact_keeps_task_and_tail(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(12)]
        out = compact_messages(msgs, keep_last=3)
        self.assertEqual(out[0]["content"], "m0")
        self.assertIn("compacted", out[1]["content"])
        self.assertEqual(len(out), 5)

    def test_load_env_does_not_override(self):
        p = Path(__file__).parent / "_env_test"
        p.write_text("A_TEST_KEY=from_file\n# c\nB_TEST_KEY='q'\n")
        os.environ["A_TEST_KEY"] = "preset"
        try:
            n = load_env(p)
            self.assertEqual(os.environ["A_TEST_KEY"], "preset")
            self.assertEqual(os.environ["B_TEST_KEY"], "q")
            self.assertEqual(n, 1)
        finally:
            p.unlink()
            os.environ.pop("A_TEST_KEY", None)
            os.environ.pop("B_TEST_KEY", None)

    def test_unknown_model_is_unpriced_not_crashing(self):
        os.environ["ORCHESTRA_PROVIDER"] = "openai"
        for t in ("SMALL", "MEDIUM", "LARGE"):
            os.environ["ORCHESTRA_" + t] = "some-model"
        try:
            m = tier_models()
            self.assertFalse(m["small"].priced)
        finally:
            for t in ("SMALL", "MEDIUM", "LARGE"):
                os.environ.pop("ORCHESTRA_" + t, None)
            os.environ.pop("ORCHESTRA_PROVIDER", None)


if __name__ == "__main__":
    unittest.main()


class DataSourcesAndSinks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).parent / "_data_test"
        self.tmp.mkdir(exist_ok=True)

    def tearDown(self):
        for f in self.tmp.iterdir():
            f.unlink()
        self.tmp.rmdir()

    def test_csv_with_foreign_column_names_is_mapped(self):
        p = self.tmp / "t.csv"
        p.write_text("ticket_id,customer_email,complaint\n9001,a@b.de,Abo abgebucht\n", encoding="utf-8")
        rows = load_records(p)
        self.assertEqual(rows[0]["id"], "9001")
        self.assertEqual(rows[0]["text"], "Abo abgebucht")
        self.assertEqual(rows[0]["customer"], "a@b.de")
        self.assertEqual(rows[0]["complaint"], "Abo abgebucht")      # the original column survives

    def test_jsonl_and_json_and_lines_and_directory(self):
        (self.tmp / "a.jsonl").write_text('{"id":"1","body":"x"}\n{"id":"2","body":"y"}\n', encoding="utf-8")
        (self.tmp / "b.json").write_text('{"items":[{"id":"1","text":"x"}]}', encoding="utf-8")
        (self.tmp / "c.txt").write_text("first\nsecond\n", encoding="utf-8")
        self.assertEqual(len(load_records(self.tmp / "a.jsonl")), 2)
        self.assertEqual(load_records(self.tmp / "b.json")[0]["text"], "x")
        self.assertEqual(load_records(self.tmp / "c.txt")[1]["text"], "second")
        self.assertEqual(len(load_records(self.tmp, limit=2)), 2)     # the directory itself, one record per file

    def test_a_missing_or_empty_dataset_says_why(self):
        with self.assertRaises(DataError):
            load_records(self.tmp / "nope.csv")
        (self.tmp / "empty.jsonl").write_text("", encoding="utf-8")
        with self.assertRaises(DataError):
            load_records(self.tmp / "empty.jsonl")

    def test_sinks_write_every_format(self):
        rows = [{"id": "1", "note": "a|b"}, {"id": "2", "note": "c"}]
        for name in ("out.csv", "out.jsonl", "out.json", "out.md"):
            p = write_records(self.tmp / name, rows, title="T")
            self.assertTrue(p.exists() and p.stat().st_size > 0, name)
        self.assertIn('"id": "1"', (self.tmp / "out.jsonl").read_text())

    def test_params_fill_templates_and_leave_unknown_fields_visible(self):
        p = Params.parse(["market=ES"], {"language": "de"})
        out = fill("{id} in {p.market}, {p.language}, {missing}", {"id": "7"}, p)
        self.assertEqual(out, "7 in ES, de, {missing}")


class PipelineBuilding(unittest.TestCase):
    def test_one_step_per_record_per_stage_with_dependencies(self):
        records = [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]
        stages = [Stage("one", "intake", "{text}"),
                  Stage("two", "writer", "after {one.category}", after="one", context="one")]
        steps = build_steps(records, stages, Params())
        self.assertEqual([s.name for s in steps], ["a_one", "a_two", "b_one", "b_two"])
        self.assertEqual(steps[1].depends_on, ["a_one"])
        self.assertTrue(callable(steps[1].task))          # it reads an earlier stage, so it renders late

    def test_a_stage_referring_to_an_unknown_stage_fails_loudly(self):
        with self.assertRaises(KeyError):
            build_steps([{"id": "a"}], [Stage("one", "intake", "x", after="nope")], Params())

    def test_stage_reference_renders_from_the_earlier_answer(self):
        records = [{"id": "a", "text": "x"}]
        stages = [Stage("one", "intake", "{text}"), Stage("two", "writer", "cat={one.category}", after="one")]
        steps = build_steps(records, stages, Params())

        class R:
            answer = {"category": "refund"}
        self.assertEqual(steps[1].task({"a_one": R()}), "cat=refund")
        self.assertIn("unavailable", steps[1].task({}))


class MCPBridge(unittest.TestCase):
    SERVER = Path(__file__).parent / "_mcp_echo.py"

    @classmethod
    def setUpClass(cls):
        cls.SERVER.write_text('''import json, sys
TOOLS = [{"name": "echo", "description": "Return the text", "inputSchema": {"type": "object",
          "properties": {"text": {"type": "string"}}}}]
def send(m): sys.stdout.write(json.dumps(m) + "\\n"); sys.stdout.flush()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    m = json.loads(line); rid = m.get("id")
    if rid is None: continue
    if m["method"] == "initialize": send({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2025-06-18"}})
    elif m["method"] == "tools/list": send({"jsonrpc":"2.0","id":rid,"result":{"tools":TOOLS}})
    elif m["method"] == "tools/call":
        send({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":m["params"]["arguments"].get("text","")}]}})
    else: send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"no"}})
''', encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.SERVER.unlink(missing_ok=True)

    def test_mcp_tools_enter_the_registry_namespaced_and_gated(self):
        reg = connect_all({"probe": {"command": sys.executable, "args": [str(self.SERVER)],
                                     "data_class": "customer", "needs_approval": True}}, strict=True)
        try:
            tools = reg.tools()
            self.assertIn("probe.echo", tools)
            self.assertEqual(tools["probe.echo"].data_class, "customer")
            self.assertEqual(tools["probe.echo"].fn(text="hi"), {"text": "hi"})
            self.assertEqual(reg.approval_patterns(), {"probe.*"})
            # the gate decides, exactly as it does for a local tool
            audit = Audit(None)
            gate = Gate(audit, Approvals())
            v = gate.check_tool(ident(tools=frozenset({"kb.*"})), "probe.echo", {}, "run",
                                data_class=tools["probe.echo"].data_class)
            self.assertIs(v.decision, Decision.DENY)
        finally:
            reg.stop()

    def test_a_server_that_cannot_start_is_recorded_not_fatal(self):
        reg = connect_all({"broken": {"command": "definitely-not-a-real-binary-xyz"}})
        self.assertIn("broken", reg.failed)
        self.assertEqual(reg.tools(), {})


class PathRouting(unittest.TestCase):
    """The cascade picks how big a model answers. A condition picks whether a stage runs at all."""

    def responder(self, model, system, messages):
        if is_agent(system, "a"):
            return final({"kind": "simple"})
        return final("ran")

    def test_a_stage_whose_condition_is_false_never_reaches_a_model(self):
        ctx = ctx_with(self.responder)
        orch = Orchestrator([Agent(ident(name="a"), "A"), Agent(ident(name="b"), "B")], ctx)
        stages = [Stage("a", "a", "{text}"),
                  Stage("b", "b", "second", after="a",
                        when=lambda rec, answer: (answer("a") or {}).get("kind") == "hard",
                        why_skipped="simple record")]
        res = orch.run(build_steps([{"id": "r1", "text": "x"}], stages, Params()))
        self.assertTrue(res["r1_b"].skipped)
        self.assertEqual(res["r1_b"].reason, "simple record")
        self.assertFalse(res["r1_b"].blocked_by_human)      # routed past, not handed over
        self.assertEqual(ctx.ledger.model_calls, 1)          # the skipped stage cost nothing
        self.assertEqual(orch.routed_past, 1)

    def test_a_true_condition_runs_the_stage(self):
        ctx = ctx_with(lambda m, s, msgs: final({"kind": "hard"}) if is_agent(s, "a") else final("ran"))
        orch = Orchestrator([Agent(ident(name="a"), "A"), Agent(ident(name="b"), "B")], ctx)
        stages = [Stage("a", "a", "{text}"),
                  Stage("b", "b", "second", after="a",
                        when=lambda rec, answer: (answer("a") or {}).get("kind") == "hard")]
        res = orch.run(build_steps([{"id": "r1", "text": "x"}], stages, Params()))
        self.assertEqual(res["r1_b"].answer, "ran")
        self.assertEqual(orch.routed_past, 0)

    def test_a_broken_condition_runs_the_stage_rather_than_dropping_work(self):
        ctx = ctx_with(self.responder)
        orch = Orchestrator([Agent(ident(name="a"), "A"), Agent(ident(name="b"), "B")], ctx)

        def boom(rec, answer):
            raise ValueError("bad condition")
        stages = [Stage("a", "a", "{text}"), Stage("b", "b", "second", after="a", when=boom)]
        res = orch.run(build_steps([{"id": "r1", "text": "x"}], stages, Params()))
        self.assertFalse(res["r1_b"].skipped)
        self.assertEqual(ctx.audit.count("condition_error"), 1)

    def test_routing_past_a_stage_does_not_stop_the_rest_of_the_chain(self):
        ctx = ctx_with(self.responder)
        orch = Orchestrator([Agent(ident(name=n), n.upper()) for n in ("a", "b", "c")], ctx)
        stages = [Stage("a", "a", "{text}"),
                  Stage("b", "b", "x", after="a", when=lambda rec, answer: False),
                  Stage("c", "c", "y", after="b")]
        res = orch.run(build_steps([{"id": "r1", "text": "x"}], stages, Params()))
        self.assertTrue(res["r1_b"].skipped)
        self.assertFalse(res["r1_c"].skipped)                # c still runs: b was not needed, not blocked


class TriageAboveThePipeline(unittest.TestCase):
    """The layer above the agents: decide what kind of work this is, then pick the cheapest process."""

    STAGES = [Stage("intake", "a", "{text}", routes=("standard", "full")),
              Stage("expert", "b", "x", after="intake", routes=("standard", "full")),
              Stage("check", "b", "y", after="expert", routes=("full",)),
              Stage("reply", "c", "z", after=["expert", "check"])]

    def agents(self):
        return [Agent(ident(name=n), n.upper()) for n in ("a", "b", "c")]

    def test_a_rule_decides_the_route_before_anything_runs(self):
        rules = [when_text("express", r"password", why="self-service")]
        rec = {"id": "r1", "text": "I forgot my password"}
        t = Triage()
        steps = build_steps([rec], self.STAGES, Params(), rules, None, t)
        self.assertEqual([s.name for s in steps], ["r1_reply"])   # three stages were never created
        self.assertEqual(rec["route"], "express")
        self.assertEqual(rec["route_reason"], "self-service")
        self.assertEqual((t.by_rule, t.by_model, t.stages_skipped), (1, 0, 3))

    def test_an_unmatched_record_keeps_every_stage_and_is_routed_by_the_model(self):
        ctx = ctx_with(lambda m, s, msgs: final({"category": "tax"}) if is_agent(s, "a") else final("done"))
        t = Triage()
        rec = {"id": "r2", "text": "a question no rule matches"}
        steps = build_steps([rec], self.STAGES, Params(), [when_text("express", r"password")],
                            lambda r, answer: "standard", t)
        self.assertEqual(len(steps), 4)                            # nothing dropped up front
        orch = Orchestrator(self.agents(), ctx)
        res = orch.run(steps)
        self.assertTrue(res["r2_check"].skipped)                   # 'check' is full-only
        self.assertIn("not on this record's route", res["r2_check"].reason)
        self.assertFalse(res["r2_intake"].skipped)                 # the classifier is never gated by itself
        self.assertEqual((t.by_rule, t.by_model), (0, 1))          # counted once, not once per stage

    def test_a_rule_that_throws_decides_nothing(self):
        def boom(rec):
            raise ValueError("bad rule")
        steps = build_steps([{"id": "r3", "text": "x"}], self.STAGES, Params(),
                            [Rule("express", boom)], None, Triage())
        self.assertEqual(len(steps), 4)

    def test_rules_are_free_and_the_cheapest_route_costs_the_fewest_calls(self):
        ctx = ctx_with(lambda m, s, msgs: final("done"))
        t = Triage()
        records = [{"id": "a", "text": "reset my password"}, {"id": "b", "text": "a real tax dispute"}]
        steps = build_steps(records, self.STAGES, Params(), [when_text("express", r"password")],
                            lambda r, answer: "full", t)
        res = Orchestrator(self.agents(), ctx).run(steps)
        self.assertEqual(t.by_rule, 1)
        self.assertEqual(len(steps), 5)                            # 1 step for the express record, 4 for the other
        self.assertFalse(any(r.skipped for r in res.values()))
        self.assertEqual(ctx.ledger.model_calls, 4)                # and the two identical replies share one call
        self.assertEqual(ctx.ledger.cache_hits, 1)


class ProviderCacheShape(unittest.TestCase):
    """What the request looks like on the wire decides whether a provider can serve it from cache."""

    def body_for(self, blocks, messages):
        captured = {}
        prov = AnthropicProvider(api_key="test-key-not-used")

        def fake_post(url, headers, body, timeout=120):
            captured["body"], captured["headers"] = body, headers
            return {"content": [{"type": "text", "text": "{}"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
        import orchestra.providers as P
        real, P._post_json = P._post_json, fake_post
        try:
            prov.complete("claude-haiku-4-5", "\n\n".join(blocks), messages, system_blocks=blocks)
        finally:
            P._post_json = real
        return captured

    def test_the_shared_block_gets_the_long_lived_cache_and_the_role_block_its_own(self):
        c = self.body_for(["shared policy", "role text"], [{"role": "user", "content": "hi"}])
        sys_blocks = c["body"]["system"]
        self.assertEqual(len(sys_blocks), 2)
        self.assertEqual(sys_blocks[0]["cache_control"], {"type": "ephemeral", "ttl": "1h"})
        self.assertEqual(sys_blocks[1]["cache_control"], {"type": "ephemeral"})
        self.assertIn("extended-cache-ttl", c["headers"]["anthropic-beta"])

    def test_a_single_turn_is_not_marked_but_a_conversation_gets_a_sliding_window(self):
        one = self.body_for(["a"], [{"role": "user", "content": "hi"}])
        self.assertIsInstance(one["body"]["messages"][0]["content"], str)
        many = self.body_for(["a"], [{"role": "user", "content": "hi"},
                                     {"role": "assistant", "content": "{}"},
                                     {"role": "user", "content": "tool result"}])
        last = many["body"]["messages"][-1]["content"]
        self.assertEqual(last[0]["cache_control"], {"type": "ephemeral"})
        self.assertIsInstance(many["body"]["messages"][0]["content"], str)   # only the last one is marked

    def test_two_roles_send_a_byte_identical_opening(self):
        reg = {}
        a = Agent(ident(name="one"), "role one", registry=reg, shared="THE POLICY")
        b = Agent(ident(name="two"), "role two", registry=reg, shared="THE POLICY")
        self.assertEqual(a.system_blocks()[0], b.system_blocks()[0])
        self.assertNotEqual(a.system_blocks()[1], b.system_blocks()[1])


class BudgetIsPerRecord(unittest.TestCase):
    """A per-run budget starves a queue: the first records spend it and the rest go to a person for nothing."""

    def test_spending_on_one_record_does_not_starve_the_next(self):
        ctx = ctx_with(lambda m, s, msgs: final("done"))
        agent = Agent(ident(name="a", budget_usd=0.000002), "A")
        orch = Orchestrator([agent], ctx)
        stages = [Stage("only", "a", "{text}")]
        records = [{"id": f"r{i}", "text": f"record {i} " + "x" * 600} for i in range(4)]  # distinct, so no cache
        res = orch.run(build_steps(records, stages, Params()))
        self.assertTrue(all(not r.budget_stop for r in res.values()), "a later record was starved by an earlier one")
        self.assertEqual(ctx.ledger.model_calls, 4)

    def test_a_record_that_really_overspends_still_stops(self):
        ctx = ctx_with(lambda m, s, msgs: json.dumps({"tool": "kb.search", "args": {}}))
        agent = Agent(ident(name="a", budget_usd=0.000002, max_steps=6),
                      "A", tools=[Tool("kb.search", "d", lambda **k: {"hit": "x" * 400})])
        orch = Orchestrator([agent], ctx)
        res = orch.run(build_steps([{"id": "r1", "text": "y" * 600}], [Stage("only", "a", "{text}")], Params()))
        self.assertTrue(res["r1_only"].budget_stop)
        self.assertIn("for this record", res["r1_only"].reason)
