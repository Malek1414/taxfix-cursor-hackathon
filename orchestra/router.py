"""Tiered cascade. Small model first; escalate only when the answer does not pass the accept check.

This is the cost lever: most calls are cheap, and the big model only sees what the small one could
not settle. `accept` is where quality is guarded: a confidence field, a schema check, a citation
resolver, a harness case. Defaults: parse JSON, require "confidence" >= min_confidence when present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Optional

from .cache import ResponseCache
from .config import TIERS, ModelSpec
from .ledger import Ledger
from .permissions import Audit, Gate, Identity
from .providers import Provider, Usage  # noqa: F401

AcceptFn = Callable[[str, str], bool]   # (text, tier) -> accepted?


def parse_json(text: str) -> Optional[dict]:
    """Tolerant JSON: the whole text, or the first {...} block inside prose/fences."""
    text = text.strip()
    for candidate in (text, text[text.find("{"): text.rfind("}") + 1] if "{" in text else ""):
        if not candidate:
            continue
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except ValueError:
            continue
    return None


@dataclass
class RoutePolicy:
    start_tier: str = "small"
    max_tier: str = "large"
    min_confidence: float = 0.7
    accept: Optional[AcceptFn] = None
    max_tokens: int = 1024

    def accepts(self, text: str, tier: str) -> bool:
        if self.accept is not None:
            return bool(self.accept(text, tier))
        obj = parse_json(text)
        if obj is None or "confidence" not in obj:
            return True                    # no signal → accept (tool calls, plain answers)
        try:
            return float(obj["confidence"]) >= self.min_confidence
        except (TypeError, ValueError):
            return False

    def ladder(self, start: Optional[str] = None) -> list[str]:
        lo = TIERS.index(start or self.start_tier)
        hi = TIERS.index(self.max_tier)
        return list(TIERS[lo: hi + 1])


@dataclass
class RouteResult:
    text: str
    tier: str
    model: str
    escalations: int = 0
    cache_hit: bool = False
    budget_stop: bool = False


class BudgetExceeded(RuntimeError):
    pass


class Router:
    def __init__(self, provider: Provider, models: dict, ledger: Ledger, cache: ResponseCache,
                 gate: Gate, audit: Audit):
        self.provider = provider
        self.models: dict[str, ModelSpec] = models
        self.ledger = ledger
        self.cache = cache
        self.gate = gate
        self.audit = audit

    def complete(self, identity: Identity, system: str, messages: list, policy: RoutePolicy,
                 run_id: str, start_tier: Optional[str] = None,
                 blocks: Optional[list] = None, step: str = "") -> RouteResult:
        escalations = 0
        previous = ""
        ladder = policy.ladder(start_tier)
        for tier in ladder:
            spec = self.models[tier]
            record = step.rsplit("_", 1)[0] if "_" in step else ""
            budget = self.gate.check_budget(identity, self.ledger.spent_by(identity.name, record), run_id)
            if not budget.allowed:
                raise BudgetExceeded(budget.reason)

            key = self.cache.key(tier, system, messages)
            cached = self.cache.get(key)
            if cached is None and not self.cache.begin(key):
                cached = self.cache.await_result(key)      # an identical question is already in flight
            if cached is not None:
                # nothing sent; the baseline still counts what it would have cost
                self.ledger.record(run_id, identity.name, spec, _estimated(system, messages, cached),
                                   local_cache_hit=True, note="local cache", step=step)
                self.audit.log(run_id, identity.name, "cache_hit", tier=tier)
                return RouteResult(cached, tier, spec.name, escalations, cache_hit=True)

            try:
                completion = self.provider.complete(spec.name, system, messages, max_tokens=policy.max_tokens,
                                                    system_blocks=blocks)
            except Exception:
                self.cache.finish(key)                     # never leave a waiter hanging on a failed call
                raise
            self.ledger.record(run_id, identity.name, spec, completion.usage, escalated_from=previous, step=step)
            self.audit.log(run_id, identity.name, "model_call", tier=tier, model=spec.name,
                           input_tokens=completion.usage.input_tokens, output_tokens=completion.usage.output_tokens,
                           cache_read=completion.usage.cache_read_tokens, escalated_from=previous)

            if policy.accepts(completion.text, tier) or tier == ladder[-1]:
                self.cache.set(key, completion.text)
                if tier != ladder[0]:                       # next identical request skips the whole ladder
                    self.cache.set(self.cache.key(ladder[0], system, messages), completion.text)
                self.cache.finish(key)
                return RouteResult(completion.text, tier, spec.name, escalations)
            self.cache.finish(key)                          # escalating: release waiters, they retry one tier up

            escalations += 1
            previous = tier
            self.audit.log(run_id, identity.name, "escalate", **{"from": tier, "to": ladder[ladder.index(tier) + 1]})
        raise RuntimeError("unreachable: ladder exhausted")   # pragma: no cover


def _estimated(system: str, messages: list, text: str) -> Usage:
    from .compress import estimate_tokens
    prompt = system + "".join(str(m["content"]) for m in messages)
    return Usage(estimate_tokens(prompt), estimate_tokens(text))
