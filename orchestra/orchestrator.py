"""The supervisor. Runs steps in dependency waves, fans independent steps out in parallel, stops a chain
once a step went to a human, collects the human queue, prints the numbers, and exports the run as JSON.
Agents never talk to each other directly: results flow through the orchestrator, trimmed.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union

from .agent import Agent, AgentResult
from .cache import ResponseCache
from .compress import trim
from .config import STATE_DIR, ModelSpec, baseline_tier, tier_models
from .ledger import Ledger
from .permissions import Approvals, Audit, Gate
from .providers import Provider, make_provider
from .router import Router

TaskSpec = Union[str, Callable[[dict], str]]      # a string, or f(results_so_far) -> task text


@dataclass
class Context:
    run_id: str
    router: Router
    gate: Gate
    audit: Audit
    ledger: Ledger
    approvals: Approvals
    started: float = field(default_factory=time.time)


@dataclass
class Step:
    name: str
    agent: str
    task: TaskSpec
    depends_on: list = field(default_factory=list)
    context_from: list = field(default_factory=list)    # step names whose answers are passed in (trimmed)
    context_chars: int = 1200
    when: Optional[Callable[[dict], bool]] = None       # run this step only if the results so far say so
    why_skipped: str = "not needed for this record"


def build_context(provider: Optional[Provider] = None, models: Optional[dict] = None, persist: bool = True,
                  approvals: Optional[Approvals] = None, baseline: Optional[str] = None) -> Context:
    models = models or tier_models()
    provider = provider or make_provider()
    audit = Audit(STATE_DIR / "audit.jsonl" if persist else None)
    approvals = approvals or Approvals()
    gate = Gate(audit, approvals)
    ledger = Ledger(models[baseline or baseline_tier()])
    cache = ResponseCache(STATE_DIR / "cache.json" if persist else None)
    router = Router(provider, models, ledger, cache, gate, audit)
    return Context(uuid.uuid4().hex[:8], router, gate, audit, ledger, approvals)


class Orchestrator:
    def __init__(self, agents: list, ctx: Context, max_workers: Optional[int] = None):
        self.agents: dict[str, Agent] = {a.name: a for a in agents}
        self.ctx = ctx
        # one wave should be one batch: with a real provider every extra batch costs its full latency
        self.max_workers = max_workers or int(os.environ.get("ORCHESTRA_WORKERS", "8"))
        self.results: dict[str, AgentResult] = {}
        self.steps: list = []
        self.human_queue: list = []
        self.triage = None          # set by the runner when a scenario triages its records

    # -- patterns ---------------------------------------------------------
    @staticmethod
    def pipeline(agent_names: list, first_task: str, name_prefix: str = "") -> list:
        """A → B → C, each step gets the previous answer as context."""
        steps, prev = [], None
        for i, agent in enumerate(agent_names):
            name = f"{name_prefix}{i + 1}_{agent}"
            task = first_task if prev is None else "Continue the work on the task above using the previous result."
            steps.append(Step(name, agent, task, depends_on=[prev] if prev else [],
                              context_from=[prev] if prev else []))
            prev = name
        return steps

    @staticmethod
    def fanout(agent: str, tasks: list, name_prefix: str = "") -> list:
        """Same agent, N independent tasks, run in parallel."""
        return [Step(f"{name_prefix}{i + 1}", agent, t) for i, t in enumerate(tasks)]

    # -- running ----------------------------------------------------------
    def run(self, steps: list) -> dict:
        self.steps = list(steps)
        pending = {s.name: s for s in steps}
        for s in steps:
            if s.agent not in self.agents:
                raise KeyError(f"step {s.name}: unknown agent '{s.agent}'")
        while pending:
            wave = [s for s in pending.values() if all(d in self.results for d in s.depends_on)]
            if not wave:
                raise RuntimeError("dependency cycle or missing step: " + ", ".join(pending))
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                outs = list(pool.map(self._run_step, wave))
            for s, r in zip(wave, outs):
                self.results[s.name] = r
                if r.to_human:
                    self.human_queue.append({"step": s.name, "agent": r.agent, "reason": r.reason})
                del pending[s.name]
        return self.results

    def _run_step(self, step: Step) -> AgentResult:
        agent = self.agents[step.agent]
        blocked = [d for d in step.depends_on
                   if self.results[d].to_human or self.results[d].blocked_by_human]
        if blocked:                                   # a handover stops the chain, and keeps stopping it
            self.ctx.audit.log(self.ctx.run_id, agent.name, "step_skipped", step=step.name,
                               reason="upstream to human", upstream=blocked[0])
            return AgentResult(agent=agent.name, text="", skipped=True, blocked_by_human=True,
                               reason=f"upstream to human: {blocked[0]}")
        if step.when is not None:
            try:
                needed = bool(step.when(self.results))
            except Exception as e:                    # a broken condition must not silently skip real work
                self.ctx.audit.log(self.ctx.run_id, agent.name, "condition_error", step=step.name,
                                   detail=f"{type(e).__name__}: {e}")
                needed = True
            if not needed:
                why = getattr(step.when, "reason", step.why_skipped)
                self.ctx.audit.log(self.ctx.run_id, agent.name, "step_skipped", step=step.name,
                                   reason="routed past", why=why)
                return AgentResult(agent=agent.name, text="", skipped=True, reason=why)
        task = step.task(self.results) if callable(step.task) else step.task
        # labelled by agent, not by step name, so identical upstream answers stay cache-identical
        context = "\n".join(f"[{self.results[n].agent}] {trim(str(self.results[n].answer), step.context_chars)}"
                            for n in step.context_from if n in self.results)
        self.ctx.audit.log(self.ctx.run_id, agent.name, "step_start", step=step.name)
        result = agent.run(task, self.ctx, context=context, step=step.name)
        self.ctx.audit.log(self.ctx.run_id, agent.name, "step_end", step=step.name, tier=result.final_tier,
                           steps=result.steps, escalate=result.escalate, denied=len(result.denied))
        return result

    # -- reporting --------------------------------------------------------
    @property
    def routed_past(self) -> int:
        """Steps the router decided this record did not need. The other lever next to model choice."""
        return sum(1 for e in self.ctx.audit.events
                   if e["event"] == "step_skipped" and e.get("reason") == "routed past")

    @property
    def denied_count(self) -> int:
        return sum(1 for e in self.ctx.audit.events if e["event"] == "tool_check" and e.get("decision") == "deny")

    def report(self) -> str:
        w = 74
        L = ["=" * w, f" run {self.ctx.run_id}", "=" * w,
             f"  {'step':<22}{'agent':<12}{'tier':<8}{'steps':>5}{'esc':>4}{'cache':>6}{'denied':>7}  outcome"]
        for name, r in self.results.items():
            outcome = ("skipped" if r.skipped else "to HUMAN" if r.to_human
                       else "ok" if r.answer is not None else "no answer")
            L.append(f"  {name:<22}{r.agent:<12}{r.final_tier:<8}{r.steps:>5}{r.escalations:>4}"
                     f"{r.cache_hits:>6}{len(r.denied):>7}  {outcome}")
        a = self.ctx.audit
        L += ["-" * w,
              f"  tool checks {a.count('tool_check')}   denied {self.denied_count}"
              f"   awaiting approval {len(self.ctx.approvals.queue)}   escalated to a human {len(self.human_queue)}",
              f"  cache hit rate {self.ctx.router.cache.hit_rate:.0%}   steps routed past {self.routed_past}"
              f"   audit events {len(a.events)}"]
        if self.triage is not None and self.triage.total:
            L.append(self.triage.line())
        L.append("=" * w)
        return "\n".join(L)

    def export(self, path: Optional[Path] = None, label: str = "", extra: Optional[dict] = None) -> Path:
        """One JSON per run: the data contract for the comparison page. No prompt text, no secrets."""
        path = path or STATE_DIR / "runs" / f"{label or 'run'}-{self.ctx.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        steps = []
        for s in self.steps:
            r = self.results.get(s.name)
            if r is None:
                continue
            steps.append({"step": s.name, "agent": r.agent, "tier": r.final_tier, "steps": r.steps,
                          "escalations": r.escalations, "cache_hits": r.cache_hits, "tools_used": r.tools_used,
                          "denied": r.denied, "to_human": r.to_human, "skipped": r.skipped, "reason": r.reason,
                          "confidence": r.confidence, "answer": trim(json.dumps(r.answer, default=str), 400)})
        led = self.ctx.ledger
        doc = {"run_id": self.ctx.run_id, "label": label, "provider": self.ctx.router.provider.name,
               "models": {t: m.name for t, m in self.ctx.router.models.items()},
               "baseline_model": led.baseline.name, "started": self.ctx.started, "exported": time.time(),
               "steps": steps, "ledger": [asdict(e) for e in led.entries],
               "totals": {"routed_past": self.routed_past, "cache_rate": led.cache_rate, "cost_usd": led.total_cost, "baseline_usd": led.total_baseline,
                          "savings_pct": led.savings_pct, "model_calls": led.model_calls,
                          "cache_hits": led.cache_hits, "calls_by_tier": led.calls_by_tier(),
                          "denied": self.denied_count, "awaiting_approval": len(self.ctx.approvals.queue),
                          "to_human": len(self.human_queue)},
               "audit": self.ctx.audit.events, "approvals": self.ctx.approvals.queue,
               "human_queue": self.human_queue, **(extra or {})}
        path.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
        return path
