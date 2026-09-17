"""
The orchestra demo: a dataset goes in the front, agents work it, results leave through the sinks.

    1. the run table    which agent ran on which tier, what was refused, what went to a human
    2. the harness      declared expectations against what happened: the number
    3. the ledger       actual cost vs. the baseline model: the saving
    4. the sinks        the rows the run produced, written to .orchestra/out/

    python3 orchestra/demo.py                        # offline, deterministic mock provider, < 1 s
    python3 orchestra/demo.py --compare              # routed run AND a measured all-large run, side by side
    python3 orchestra/demo.py --live                 # real provider from .env (claude_code | anthropic | openai)
    python3 orchestra/demo.py --data tickets.csv     # their dataset instead of the built-in records
    python3 orchestra/demo.py --limit 20             # first N records only
    python3 orchestra/demo.py --set market=ES        # a variable the prompts read as {p.market}
    python3 orchestra/demo.py --mcp mcp.json         # hang MCP servers into the registry, behind the same gate
    python3 orchestra/demo.py --no-routing           # run every stage for every record
    python3 orchestra/demo.py --compare-routing      # measure what path routing saves, on and off, side by side
    python3 orchestra/demo.py --scenario <name>      # another brief: orchestra/scenarios/<name>.py

Every run is exported to .orchestra/runs/<label>-<id>.json, the data contract for the comparison page.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestra.config import load_env, mock_models, tier_models                 # noqa: E402
from orchestra.data import Params                                               # noqa: E402
from orchestra.mcp import connect_all, load_config                              # noqa: E402
from orchestra.orchestrator import Orchestrator, build_context                  # noqa: E402
from orchestra.permissions import Approvals                                     # noqa: E402
from orchestra.pipeline import build_steps, collect                             # noqa: E402
from orchestra.triage import Triage                                             # noqa: E402
from orchestra.providers import MockProvider, make_provider                     # noqa: E402
from orchestra.router import RoutePolicy                                        # noqa: E402
from orchestra.scenarios import load as load_scenario                           # noqa: E402

W = 74


def run_once(scn, provider, models, mode: str, persist: bool, records: list, params: Params,
             mcp_tools: dict = None, routing: bool = True):
    """mode: 'routed' (the cascade) or 'baseline' (every agent forced onto the large tier, measured)."""
    ctx = build_context(provider=provider, models=models, persist=persist, approvals=Approvals(),
                        baseline="large" if mode == "baseline" else None)   # a baseline run is its own baseline
    registry = scn.make_tools(params, mcp_tools or {})
    agents = scn.agents(registry)
    if mode == "baseline":
        # Force the large tier, and scale every budget by what the large tier costs, so the comparison
        # measures quality against cost rather than measuring a budget that was sized for a small model.
        large, small = models["large"], models["small"]
        factor = max(1.0, (large.input_usd + large.output_usd) / max(small.input_usd + small.output_usd, 1e-9))
        for a in agents:
            a.policy = RoutePolicy(start_tier="large", max_tier="large", min_confidence=0.0,
                                   max_tokens=a.policy.max_tokens)
            a.identity = dataclasses.replace(a.identity, budget_usd=a.identity.budget_usd * factor)
    stages = scn.stages()
    triage = Triage()
    rules = getattr(scn, "TRIAGE", None)
    route_of = getattr(scn, "route_from_category", None)
    if not routing:                 # every stage runs for every record: the measurement baseline for routing
        stages = [dataclasses.replace(st, when=None, routes=None) for st in stages]
        rules, route_of = None, None
    orch = Orchestrator(agents, ctx)
    orch.triage = triage
    orch.run(build_steps([dict(r) for r in records], stages, params, rules, route_of, triage))
    outcomes = collect(orch.results, records, stages)
    suite = scn.suite(registry, records)
    suite.run(lambda inputs: scn.outcome(outcomes, inputs["tid"], ctx), compare=scn.compare,
              escalated=lambda out: bool(out and out.get("human")))
    harness = {"accuracy": suite.accuracy, "silent_errors": len(suite.silent_errors),
               "adversarial_held": suite.adversarial_held, "clean": suite.clean, "cases": len(suite.cases)}
    written = scn.write_outputs(outcomes, ctx, params) if hasattr(scn, "write_outputs") else []
    path = orch.export(label=mode if routing else mode + "-all-stages",
                       extra={"scenario": scn.NAME, "harness": harness, "routing": routing,
                              "records": len(records), "params": params.values,
                              "triage": {"by_rule": triage.by_rule, "by_model": triage.by_model,
                                         "routes": triage.routes, "stages_skipped": triage.stages_skipped}})
    return orch, ctx, suite, path, written


def print_run(orch, ctx, suite, path, written, title: str) -> None:
    print(f"\n {title}")
    print(orch.report())
    print()
    print(suite.report())
    print("\n  say on stage:", suite.headline())
    print()
    print(ctx.ledger.report())
    print("\n  say on stage:", ctx.ledger.headline())
    if ctx.approvals.queue or orch.human_queue:
        print("\n  for a human:")
        for q in ctx.approvals.queue:
            print(f"    approve? {q['agent']} wants {q['tool']} {q['args']} (owner {q['owner']})")
        for h in orch.human_queue:
            print(f"    {h['step']}: {h['reason']}")
    for w in written or []:
        print(f"  wrote {w}")
    print(f"\n  exported {path}")


def print_comparison(routed, baseline, left: str = "routed", right: str = None, title: str = None) -> None:
    ro, rc, rs = routed[:3]
    bo, bc, bs = baseline[:3]
    right = right or "all large (" + bc.router.models["large"].name + ")"
    saved = (1 - rc.ledger.total_cost / bc.ledger.total_cost) * 100 if bc.ledger.total_cost else 0.0
    tiers = lambda c: ", ".join(f"{t} {n}" for t, n in sorted(c.ledger.calls_by_tier().items())) or "none"  # noqa: E731
    rows = [
        ("harness correct", f"{rs.passed if hasattr(rs, 'passed') else round(rs.accuracy * len(rs.cases))}/{len(rs.cases)}",
         f"{bs.passed if hasattr(bs, 'passed') else round(bs.accuracy * len(bs.cases))}/{len(bs.cases)}"),
        ("silent errors", str(len(rs.silent_errors)), str(len(bs.silent_errors))),
        ("adversarial held", "yes" if rs.adversarial_held else "NO", "yes" if bs.adversarial_held else "NO"),
        ("denied actions", str(ro.denied_count), str(bo.denied_count)),
        ("steps routed past", str(ro.routed_past), str(bo.routed_past)),
        ("stages never created", str(ro.triage.stages_skipped if ro.triage else 0),
         str(bo.triage.stages_skipped if bo.triage else 0)),
        ("classified for free", str(ro.triage.by_rule if ro.triage else 0),
         str(bo.triage.by_rule if bo.triage else 0)),
        ("model calls", str(rc.ledger.model_calls), str(bc.ledger.model_calls)),
        ("calls by tier", tiers(rc), tiers(bc)),
        ("cost $", f"{rc.ledger.total_cost:.5f}", f"{bc.ledger.total_cost:.5f}"),
    ]
    print("\n" + "=" * W)
    print(" " + (title or "comparison, measured: same tickets, same oracle, two real runs"))
    print("=" * W)
    print(f"  {'':<22}{left:<26}{right:<26}")
    for k, a, b in rows:
        print(f"  {k:<22}{a:<26}{b:<26}")
    print("-" * W)
    same = (rs.accuracy == bs.accuracy and len(rs.silent_errors) == len(bs.silent_errors))
    print(f"  SAVED (measured)      {saved:.0f}%   {'same harness result' if same else 'harness result DIFFERS'}, smaller bill")
    print("=" * W)
    if not rs.cases:
        print("\n  say on stage: no declared expectations in this dataset, so correctness is not measured here."
              f" Cost: {saved:.0f}% less than {right}.")
    elif same:
        print(f"\n  say on stage: {len(rs.cases)} cases, {rs.accuracy:.0%} correct on both runs, "
              f"{saved:.0f}% cheaper with routing, caching and budgets.")
    else:
        print(f"\n  say on stage: {len(rs.cases)} cases, routed {rs.accuracy:.0%} correct against "
              f"{bs.accuracy:.0%} on the large model, at {saved:.0f}% of the cost. The runs differ, so say "
              f"which one you are quoting.")


def arg(argv: list, flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and len(argv) > argv.index(flag) + 1 else default


def main(argv: list) -> int:
    live = "--live" in argv
    compare = "--compare" in argv
    compare_routing = "--compare-routing" in argv
    routing = "--no-routing" not in argv
    only_baseline = "--baseline" in argv and not compare
    scn = load_scenario(arg(argv, "--scenario", "support"))
    load_env()
    params = Params.parse([argv[i + 1] for i, a in enumerate(argv) if a == "--set" and i + 1 < len(argv)],
                          getattr(scn, "DEFAULTS", {}))
    limit = int(arg(argv, "--limit", 0)) or None
    records = scn.source(params, data=arg(argv, "--data"), limit=limit)
    mcp = None
    mcp_tools: dict = {}
    if arg(argv, "--mcp"):
        mcp = connect_all(load_config(arg(argv, "--mcp")))
        mcp_tools = mcp.tools()
        for name, why in mcp.failed.items():
            print(f"  MCP server '{name}' did not start: {why}", file=sys.stderr)
    if live:
        models = tier_models()
        provider = make_provider()
    else:
        models = mock_models()                                   # independent of .env, always deterministic
        provider = MockProvider(scn.mock_responder(models))
    persist = live and not compare                               # comparison runs get fresh caches, always

    print(f"\n orchestra demo  scenario={scn.NAME}  provider={provider.name}  records={len(records)}"
          f"  params={params}  routing={'on' if routing else 'off'}"
          f"  tiers=" + ", ".join(f"{t}={m.name}" for t, m in models.items()))
    if mcp_tools:
        print("  MCP tools in the registry: " + ", ".join(sorted(mcp_tools)))

    try:
        routed = None
        if not only_baseline:
            routed = run_once(scn, provider, models, "routed", persist, records, params, mcp_tools, routing)
            print_run(*routed, title="routed run: small first, escalate on doubt")
        baseline = None
        if compare or only_baseline:
            baseline = run_once(scn, provider, models, "baseline", persist, records, params, mcp_tools, routing)
            print_run(*baseline, title="baseline run: every agent on the large model")
        if compare_routing:
            without = run_once(scn, provider, models, "routed", persist, records, params, mcp_tools, routing=False)
            print_run(*without, title="every stage for every record: what routing is compared against")
            print_comparison(routed, without, left="path routing on", right="every stage, every record",
                             title="routing, measured: the same records, with and without the conditions")
        elif routed and baseline:
            print_comparison(routed, baseline)
    finally:
        if mcp is not None:
            mcp.stop()

    print("\n  synthetic: tickets, knowledge base, mailer" + (", token counts of the mock provider" if not live else "")
          + ".\n  real: the wage-tax figure (BMF PAP 2026 via spine/) and the statute check.\n")
    if "--json" in argv and routed:
        print(routed[1].ledger.to_json())
    suite = (routed or baseline)[2]
    if not suite.cases:
        return 0                                  # nothing was claimed, so nothing failed
    return 0 if suite.clean and suite.accuracy == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
