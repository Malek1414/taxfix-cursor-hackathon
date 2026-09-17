"""Identity, scopes, tool allowlist, approval gate, audit log.

The rule the room will recognise: no agent gets the keys to the kingdom. Every agent has an identity,
a named owner, a tool allowlist, the data classes it may touch, a budget, and a list of actions that
need a human. The gate runs before every tool call, in code, not in the prompt.

The audit log is append-only JSONL. It records decisions, never prompt contents, never secrets.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Optional


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"          # needs a human before it runs


@dataclass(frozen=True)
class Identity:
    name: str
    role: str
    owner: str                                     # the human accountable for this agent
    tools: frozenset = frozenset()                 # glob patterns: "kb.*", "calc.tax"
    data_classes: frozenset = frozenset()          # "public", "customer", "financial", "pii"
    needs_approval: frozenset = frozenset()        # tool patterns that must be approved by a human
    budget_usd: float = 1.0                        # hard stop per run; over budget → human, not a bigger model
    max_steps: int = 6                             # tool-call loop ceiling

    def may_use(self, tool: str) -> bool:
        return any(fnmatch(tool, p) for p in self.tools)

    def must_ask(self, tool: str) -> bool:
        return any(fnmatch(tool, p) for p in self.needs_approval)

    def may_touch(self, data_class: str) -> bool:
        return data_class in self.data_classes


@dataclass
class Verdict:
    decision: Decision
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW


class Audit:
    """Append-only event log. One JSON object per line. No prompt text, no secrets."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.events: list[dict] = []
        self._lock = threading.Lock()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, run_id: str, agent: str, event: str, **fields) -> dict:
        row = {"ts": round(time.time(), 3), "run": run_id, "agent": agent, "event": event, **fields}
        with self._lock:
            self.events.append(row)
            if self.path:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def count(self, event: str) -> int:
        return sum(1 for e in self.events if e["event"] == event)


ApprovalHandler = Callable[[Identity, str, dict], bool]   # (identity, tool, args) -> approved?


@dataclass
class Approvals:
    """Human-in-the-loop. Default handler approves nothing: it queues the request for a person."""

    handler: Optional[ApprovalHandler] = None
    queue: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def request(self, identity: Identity, tool: str, args: dict, run_id: str = "", step: str = "") -> bool:
        if self.handler is None:
            shown = {k: (str(v)[:120] + "…" if len(str(v)) > 120 else v) for k, v in args.items()}
            with self._lock:                                       # several agents may queue at once
                self.queue.append({"run": run_id, "step": step, "agent": identity.name, "owner": identity.owner,
                                   "tool": tool, "args": shown})   # the approver must see what they approve
            return False
        return bool(self.handler(identity, tool, args))


class Gate:
    def __init__(self, audit: Audit, approvals: Approvals):
        self.audit = audit
        self.approvals = approvals

    def check_tool(self, identity: Identity, tool: str, args: dict, run_id: str,
                   data_class: Optional[str] = None, step: str = "") -> Verdict:
        if not identity.may_use(tool):
            v = Verdict(Decision.DENY, f"'{tool}' is not in the allowlist of {identity.name}")
        elif data_class and data_class != "public" and not identity.may_touch(data_class):
            v = Verdict(Decision.DENY, f"'{tool}' touches '{data_class}' data, which {identity.name} may not see")
        elif identity.must_ask(tool):
            approved = self.approvals.request(identity, tool, args, run_id, step)
            v = (Verdict(Decision.ALLOW, f"'{tool}' approved by a human") if approved
                 else Verdict(Decision.ASK, f"'{tool}' queued for approval by {identity.owner}"))
        else:
            v = Verdict(Decision.ALLOW, "in allowlist")
        self.audit.log(run_id, identity.name, "tool_check", step=step, tool=tool,
                       decision=v.decision.value, reason=v.reason)
        return v

    def check_budget(self, identity: Identity, spent_usd: float, run_id: str) -> Verdict:
        if spent_usd >= identity.budget_usd:
            v = Verdict(Decision.ASK,
                        f"budget ${identity.budget_usd:.2f} for this record exhausted (spent ${spent_usd:.4f})")
        else:
            v = Verdict(Decision.ALLOW, "within budget")
        if not v.allowed:
            self.audit.log(run_id, identity.name, "budget_stop", spent=round(spent_usd, 5), budget=identity.budget_usd)
        return v
