"""Triage: decide what kind of work this is before spending anything on it.

The cheapest model call is the one you never make. Most of what a company handles is small: a password
reset, a where-do-I-click question, the same complaint for the fortieth time. Those do not need a four-stage
pipeline, and the ones that can be recognised by a rule do not even need a model to recognise them.

So there are two layers of triage, in this order:

    rules   pure Python, zero tokens. A matched rule assigns the route before the run starts, and the
            stages that route does not use are never created.
    model   whatever the rules could not settle goes to the cheapest agent, which classifies it, and the
            route follows from that classification at runtime.

A route is a named subset of the pipeline: `express` might be two stages, `full` all four. Stages declare
which routes they belong to. Nothing else in the orchestra changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Rule:
    """One free classification. `match` looks at the whole record, so it can use any column, not just text."""

    route: str
    match: Callable[[dict], bool]
    why: str = ""

    def applies(self, record: dict) -> bool:
        try:
            return bool(self.match(record))
        except Exception:
            return False          # a rule that throws must not decide anything


def when_text(route: str, *patterns: str, why: str = "", field: str = "text") -> Rule:
    """A rule that fires when the record's text matches any of these patterns, case-insensitively."""
    rx = re.compile("|".join(patterns), re.IGNORECASE)
    return Rule(route, lambda rec: bool(rx.search(str(rec.get(field, "")))), why or f"matched {patterns[0]}")


def when_field(route: str, field: str, *values: str, why: str = "") -> Rule:
    """A rule that fires on an exact column value, for datasets that already carry a type or a queue."""
    wanted = {v.lower() for v in values}
    return Rule(route, lambda rec: str(rec.get(field, "")).lower() in wanted,
                why or f"{field} in {', '.join(sorted(wanted))}")


def decide(record: dict, rules: Optional[list]) -> Optional[Rule]:
    """The first rule that applies wins. None means nobody could tell for free; ask the cheapest model."""
    for r in rules or []:
        if r.applies(record):
            return r
    return None


@dataclass
class Triage:
    """What the rules settled, and what it saved. Kept per run so the run table can show it."""

    by_rule: int = 0
    by_model: int = 0
    stages_skipped: int = 0
    routes: dict = None
    seen: set = None

    def __post_init__(self):
        if self.routes is None:
            self.routes = {}
        if self.seen is None:
            self.seen = set()

    def record(self, rid: str, route: str, free: bool, skipped: int = 0) -> None:
        """Count each record once, however many stages ask about its route."""
        if rid in self.seen:
            return
        self.seen.add(rid)
        self.routes[route] = self.routes.get(route, 0) + 1
        self.stages_skipped += skipped
        if free:
            self.by_rule += 1
        else:
            self.by_model += 1

    @property
    def total(self) -> int:
        return self.by_rule + self.by_model

    def line(self) -> str:
        spread = ", ".join(f"{k} {v}" for k, v in sorted(self.routes.items())) or "none"
        return (f"  triage           {self.by_rule} by rule (free), {self.by_model} by model   "
                f"routes: {spread}   stages never created: {self.stages_skipped}")
