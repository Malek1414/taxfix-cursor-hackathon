"""Tokens, cost, and the number for the stage: what this run cost versus "everything on the baseline model".

The baseline is a counterfactual (same tokens, one model, no cache). For the stage, run `demo.py --compare`:
it measures the baseline instead of computing it."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field

from .config import CACHE_READ_FACTOR, CACHE_WRITE_FACTOR, ModelSpec


@dataclass
class Entry:
    ts: float
    run_id: str
    agent: str
    tier: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    baseline_usd: float
    local_cache_hit: bool = False
    escalated_from: str = ""
    note: str = ""
    step: str = ""              # which step of which record this call belonged to


def cost_usd(spec: ModelSpec, input_tokens: int, output_tokens: int,
             cache_read: int = 0, cache_write: int = 0) -> float:
    """Actual spend at this model's price, with provider-cache discounts."""
    per = 1_000_000
    return (input_tokens * spec.input_usd
            + cache_read * spec.input_usd * CACHE_READ_FACTOR
            + cache_write * spec.input_usd * CACHE_WRITE_FACTOR
            + output_tokens * spec.output_usd) / per


def baseline_usd(baseline: ModelSpec, input_tokens: int, output_tokens: int) -> float:
    """The counterfactual: the same tokens, all on the baseline model, no cache."""
    return (input_tokens * baseline.input_usd + output_tokens * baseline.output_usd) / 1_000_000


@dataclass
class Ledger:
    baseline: ModelSpec
    entries: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, entry: Entry) -> None:
        with self._lock:
            self.entries.append(entry)

    def record(self, run_id: str, agent: str, spec: ModelSpec, usage, *, local_cache_hit: bool = False,
               escalated_from: str = "", note: str = "", step: str = "") -> Entry:
        prompt_tokens = usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens
        if local_cache_hit:
            actual = 0.0
        elif getattr(usage, "cost_usd_reported", None) is not None:
            actual = float(usage.cost_usd_reported)          # the provider's own bill beats our price table
        else:
            actual = cost_usd(spec, usage.input_tokens, usage.output_tokens,
                              usage.cache_read_tokens, usage.cache_write_tokens)
        e = Entry(time.time(), run_id, agent, spec.tier, spec.name, usage.input_tokens, usage.output_tokens,
                  usage.cache_read_tokens, usage.cache_write_tokens, actual,
                  baseline_usd(self.baseline, prompt_tokens, usage.output_tokens),
                  local_cache_hit, escalated_from, note, step)
        self.add(e)
        return e

    # -- the numbers ------------------------------------------------------
    @property
    def cache_rate(self) -> float:
        """Share of prompt tokens the provider served from its cache. The number to watch in production."""
        read = sum(e.cache_read_tokens for e in self.entries)
        fresh = sum(e.input_tokens + e.cache_write_tokens for e in self.entries)
        total = read + fresh
        return read / total if total else 0.0

    @property
    def model_calls(self) -> int:
        return sum(1 for e in self.entries if not e.local_cache_hit)

    @property
    def cache_hits(self) -> int:
        return sum(1 for e in self.entries if e.local_cache_hit)

    @property
    def total_cost(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    @property
    def total_baseline(self) -> float:
        return sum(e.baseline_usd for e in self.entries)

    @property
    def savings_pct(self) -> float:
        b = self.total_baseline
        return (1 - self.total_cost / b) * 100 if b else 0.0

    def spent_by(self, agent: str, record: str = "") -> float:
        """What this agent has spent, on one record when given one.

        A budget is per agent per record, not per agent per run: otherwise the first few records in a queue
        use up the allowance and every record after them is handed to a person for no reason.
        """
        if not record:
            return sum(e.cost_usd for e in self.entries if e.agent == agent)
        prefix = record + "_"
        return sum(e.cost_usd for e in self.entries if e.agent == agent and e.step.startswith(prefix))

    def calls_by_tier(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            if not e.local_cache_hit:
                out[e.tier] = out.get(e.tier, 0) + 1
        return out

    def by_agent(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in self.entries:
            a = out.setdefault(e.agent, {"calls": 0, "cost": 0.0, "baseline": 0.0, "cache_hits": 0, "escalations": 0})
            a["calls"] += 1
            a["cost"] += e.cost_usd
            a["baseline"] += e.baseline_usd
            a["cache_hits"] += int(e.local_cache_hit)
            a["escalations"] += int(bool(e.escalated_from))
        return out

    def report(self) -> str:
        w = 74
        L = ["=" * w, " cost ledger", "=" * w,
             f"  {'agent':<14}{'calls':>6}{'cache':>7}{'escal.':>8}{'cost $':>12}{'baseline $':>13}{'saved':>9}"]
        for name, a in self.by_agent().items():
            saved = (1 - a["cost"] / a["baseline"]) * 100 if a["baseline"] else 0.0
            L.append(f"  {name:<14}{a['calls']:>6}{a['cache_hits']:>7}{a['escalations']:>8}"
                     f"{a['cost']:>12.5f}{a['baseline']:>13.5f}{saved:>8.0f}%")
        tiers = ", ".join(f"{t} {n}" for t, n in sorted(self.calls_by_tier().items()))
        L += ["-" * w,
              f"  model calls by tier   {tiers or 'none'}",
              f"  provider cache rate   {self.cache_rate:.0%}   (tokens served from the provider's cache)",
              f"  actual cost           ${self.total_cost:.5f}",
              f"  baseline (all {self.baseline.name}, no cache)  ${self.total_baseline:.5f}",
              f"  SAVED                 {self.savings_pct:.0f}%   (counterfactual; run --compare for a measured one)",
              "=" * w]
        return "\n".join(L)

    def headline(self) -> str:
        return (f"{self.model_calls} model calls and {self.cache_hits} cache hits: ${self.total_cost:.4f} spent, "
                f"${self.total_baseline:.4f} if everything ran on {self.baseline.name}, {self.savings_pct:.0f}% saved.")

    def to_json(self) -> str:
        return json.dumps([asdict(e) for e in self.entries], indent=1)
