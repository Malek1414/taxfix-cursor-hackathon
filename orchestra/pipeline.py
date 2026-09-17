"""One pipeline definition, many records: the shape between the source and the sinks.

A scenario says what the stages are; this turns them into the orchestrator's steps for every record in the
dataset. Adding a stage is one line. Swapping the dataset changes nothing here.

    STAGES = [
        Stage("intake",     "intake",     "Ticket from {customer}:\\n{text}"),
        Stage("specialist", "specialist", "Handle the ticket above. Category: {intake.category}.",
              after="intake", context="intake"),
    ]
    steps = build_steps(records, STAGES, params)

Task templates read `{field}` from the record, `{p.name}` from the params, and `{<stage>.<key>}` from an
earlier stage's answer, which is why a stage that reads another one names it in `after`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .data import Params, fill
from .orchestrator import Step
from .triage import Triage, decide

# {stage.key} refers to an earlier stage. {p.name} is a run parameter, not a stage, hence the exclusion.
_STAGE_REF = re.compile(r"\{(?!p\.)([a-zA-Z_][\w]*)\.([\w]+)\}")


def _as_list(v) -> list:
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple, set)) else [v]


@dataclass
class Stage:
    """One step of the pipeline.

    `when` is the second routing lever. The cascade picks how big a model answers; `when` picks whether a
    stage runs at all. It is a callable `(record, answer) -> bool`, where `answer(stage_name)` returns what
    an earlier stage produced for this record. A stage without a condition always runs.
    """

    name: str
    agent: str
    task: str
    after: object = None        # stage name(s) that must finish first
    context: object = None      # stage name(s) whose answer is passed in, trimmed
    context_chars: int = 1200
    when: Optional[Callable] = None
    why_skipped: str = "not needed for this record"
    routes: object = None       # route name(s) this stage belongs to; None means every route

    @property
    def depends(self) -> list:
        return _as_list(self.after)

    @property
    def reads(self) -> list:
        return _as_list(self.context)

    def in_route(self, route: Optional[str]) -> bool:
        """A stage with no route list is in every route. An undecided record keeps every stage."""
        if self.routes is None or route is None:
            return True
        return route in _as_list(self.routes)


def step_name(record_id: str, stage: str) -> str:
    return f"{record_id}_{stage}"


def build_steps(records: list, stages: list, params: Optional[Params] = None,
                rules: Optional[list] = None, route_of: Optional[Callable] = None,
                triage: Optional[Triage] = None) -> list:
    """Cross the dataset with the pipeline: one step per record per stage, minus what triage rules out.

    `rules` decide a record's route for free, before anything runs; a stage outside that route is never
    created, so it cannot cost anything. `route_of(record, answer)` decides the route at runtime for the
    records no rule could settle, and every stage after the first then carries it as a condition. The first
    stage is exempt on purpose: it is the one that produces the classification the route is derived from.
    """
    names = {s.name for s in stages}
    for s in stages:
        unknown = [d for d in s.depends + s.reads if d not in names]
        if unknown:
            raise KeyError(f"stage '{s.name}' refers to unknown stage(s): {', '.join(unknown)}")
    steps = []
    for rec in records:
        rid = str(rec.get("id"))
        hit = decide(rec, rules)
        if hit is not None:
            rec["route"], rec["route_reason"] = hit.route, hit.why
        wanted = [s for s in stages if s.in_route(rec.get("route"))]
        dropped = {s.name for s in stages} - {s.name for s in wanted}
        if triage is not None and hit is not None:
            triage.record(rid, hit.route, free=True, skipped=len(dropped))
        for s in wanted:
            cond = _condition_for(rec, s, route_of if (hit is None and s.depends) else None, triage)
            steps.append(Step(
                name=step_name(rid, s.name),
                agent=s.agent,
                task=_task_for(rec, s, params),
                depends_on=[step_name(rid, d) for d in s.depends if d not in dropped],
                context_from=[step_name(rid, c) for c in s.reads if c not in dropped],
                context_chars=s.context_chars,
                when=cond,
                why_skipped=cond.reason if cond is not None else s.why_skipped,
            ))
    return steps


class _Condition:
    """A stage's run-or-skip decision for one record, carrying the reason it last said no."""

    def __init__(self, fn, default_reason: str):
        self._fn = fn
        self.reason = default_reason

    def __call__(self, results: dict) -> bool:
        ok, why = self._fn(results)
        if not ok:
            self.reason = why
        return ok


def _condition_for(record: dict, stage: Stage, route_of: Optional[Callable] = None,
                   triage: Optional[Triage] = None):
    """Bind this stage's conditions to this record: its own `when`, and the route if one is decided late."""
    if stage.when is None and route_of is None:
        return None
    rid = str(record.get("id"))

    def condition(results: dict):
        def read(stage_name: str):
            res = results.get(step_name(rid, stage_name))
            return getattr(res, "answer", None)
        if route_of is not None:
            route = record.get("route") or route_of(record, read)
            if route is not None:
                record["route"] = route
                if triage is not None:
                    triage.record(rid, route, free=False)
                if not stage.in_route(route):
                    return False, f"not on this record's route ({route})"
        if stage.when is not None and not bool(stage.when(record, read)):
            return False, stage.why_skipped
        return True, ""
    return _Condition(condition, stage.why_skipped)


def _task_for(record: dict, stage: Stage, params: Optional[Params]):
    """A literal task when nothing refers to an earlier stage, otherwise a function the orchestrator calls."""
    if not _STAGE_REF.search(stage.task):
        return fill(stage.task, record, params)
    rid = str(record.get("id"))

    def render(results: dict) -> str:
        def sub(m):
            other, key = m.group(1), m.group(2)
            res = results.get(step_name(rid, other))
            answer = getattr(res, "answer", None)
            if isinstance(answer, dict) and key in answer:
                return str(answer[key])
            return f"[{other}.{key} unavailable]"
        return fill(_STAGE_REF.sub(sub, stage.task), record, params)
    return render


@dataclass
class Outcome:
    """What a pipeline did to one record, in the vocabulary the harness and the sinks both use."""

    record: dict
    results: dict = field(default_factory=dict)

    @property
    def chain(self) -> list:
        return list(self.results.values())

    def answer(self, stage: str):
        res = self.results.get(stage)
        return getattr(res, "answer", None)

    def field(self, stage: str, key: str, default=None):
        a = self.answer(stage)
        return a.get(key, default) if isinstance(a, dict) else default

    @property
    def tools_used(self) -> list:
        return [t for r in self.chain for t in getattr(r, "tools_used", [])]

    @property
    def denied(self) -> list:
        return [d for r in self.chain for d in getattr(r, "denied", [])]

    @property
    def to_human(self) -> bool:
        return any(getattr(r, "to_human", False) for r in self.chain)

    @property
    def stopped_at(self) -> Optional[str]:
        for name, r in self.results.items():
            if getattr(r, "to_human", False):
                return name
        return None


def collect(results: dict, records: list, stages: list) -> dict:
    """Group the flat step results back per record."""
    out = {}
    for rec in records:
        rid = str(rec.get("id"))
        out[rid] = Outcome(rec, {s.name: results[step_name(rid, s.name)]
                                 for s in stages if step_name(rid, s.name) in results})
    return out
