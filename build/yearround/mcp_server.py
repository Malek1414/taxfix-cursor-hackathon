"""
MCP server for the year-round tax position. Stdio, newline-delimited JSON-RPC.
Standard library only — no SDK, so it runs on any laptop in the room.

Register in Cursor (.cursor/mcp.json is already written):

    {"mcpServers": {"taxfix-yearround": {"command": "python3",
                    "args": ["<abs path>/build/yearround/mcp_server.py"]}}}

Then in Cursor's agent: "call q4_plan for the demo profile" — the agent gets
cent-exact moves from the BMF algorithm and the refusals, and can only show
what the engine priced. That is the orchestration story: the LLM drafts, the
engine prices, the statute audits, and nothing unpriced reaches the user.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.law.cite import audit                                   # noqa: E402
from build.yearround.moves import (                               # noqa: E402
    Candidate, Profile, moves_for, november_profile, november_table, plan, position, price,
)

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "gross": {"type": "number", "description": "gross annual wage, EUR"},
        "stkl": {"type": "integer", "description": "Steuerklasse 1-6", "default": 1},
        "werbungskosten": {"type": "number", "default": 0},
        "homeoffice_days": {"type": "integer", "default": 0},
        "handwerker_labour": {"type": "number", "default": 0, "description": "labour already paid by transfer this year"},
        "haushalt_labour": {"type": "number", "default": 0},
        "spenden": {"type": "number", "default": 0},
        "today": {"type": "string", "description": "YYYY-MM-DD", "default": "2026-11-12"},
        "name": {"type": "string", "default": "Musterperson"},
    },
    "required": ["gross"],
}
CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["werbungskosten", "homeoffice", "handwerker", "haushalt", "spende", "betriebsausgabe", "other"]},
        "vat_rate": {"type": "number", "description": "betriebsausgabe: 0.19 / 0.07 / 0", "default": 0.19},
        "label": {"type": "string"},
        "amount": {"type": "number", "description": "EUR, or days for homeoffice"},
        "labour": {"type": "number", "description": "handwerker/haushalt: labour share (materials never count)"},
        "cash": {"type": "boolean", "default": False},
        "due": {"type": "string", "description": "YYYY-MM-DD the bill is due"},
        "citation": {"type": "string", "description": "a paragraph you are citing, e.g. '§ 35a EStG' — it will be checked"},
        "claim": {"type": "string"},
    },
    "required": ["kind", "label"],
}

TOOLS = [
    {"name": "tax_position",
     "description": "What the user's return is worth if filed today, from the BMF Programmablaufplan. Decimal-exact.",
     "inputSchema": {"type": "object", "properties": {"profile": PROFILE_SCHEMA}, "required": ["profile"]}},
    {"name": "price_move",
     "description": "Price one candidate move before 31 December: worth / zero / escalate, with the saving and the statute. "
                    "A citation that does not resolve is refused, never shown.",
     "inputSchema": {"type": "object", "properties": {"profile": PROFILE_SCHEMA, "candidate": CANDIDATE_SCHEMA},
                     "required": ["profile", "candidate"]}},
    {"name": "q4_plan",
     "description": "Rank and sequence all candidates (moves interact: crossing the Pauschbetrag changes later moves). "
                    "Omit both arguments for the demo profile.",
     "inputSchema": {"type": "object", "properties": {"profile": PROFILE_SCHEMA,
                     "candidates": {"type": "array", "items": CANDIDATE_SCHEMA}}}},
    {"name": "audit_claim",
     "description": "Hallucination audit: every '§ … EStG/UStG/AO' in the text is resolved against the statute.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
]


def _profile(d: dict | None) -> Profile:
    if not d:
        return november_profile()
    d = dict(d)
    if "today" in d:
        d["today"] = date.fromisoformat(d["today"])
    return Profile(**d)


def _candidate(d: dict) -> Candidate:
    d = dict(d)
    if "due" in d and d["due"]:
        d["due"] = date.fromisoformat(d["due"])
    return Candidate(**d)


def _plain(o):
    if isinstance(o, Decimal):
        return f"{o:.2f}"
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    return o


def _move(m) -> dict:
    return _plain({"label": m.candidate.label, "status": m.status, "saving_eur": m.saving,
                   "citation": m.citation, "citation_resolves": m.citation_ok, "why": m.why,
                   "tax_before": m.before, "tax_after": m.after, "deadline": m.deadline,
                   "vat_reclaim_eur": m.vat_reclaim})


def call(name: str, args: dict):
    if name == "tax_position":
        return _plain(asdict(position(_profile(args.get("profile")))))
    if name == "price_move":
        return _move(price(_profile(args.get("profile")), _candidate(args["candidate"])))
    if name == "q4_plan":
        p = _profile(args.get("profile"))
        cs = [_candidate(c) for c in args["candidates"]] if args.get("candidates") else november_table()
        taken, end = plan(p, cs)
        return _plain({"position_today_eur": position(p).refund, "position_after_plan_eur": position(end).refund,
                       "days_to_deadline": p.days_left, "moves": [_move(m) for m in taken]})
    if name == "audit_claim":
        vs = audit(args["text"])
        return [{"citation": v.citation, "exists": v.exists, "supported": v.supported, "reason": v.reason,
                 "title": v.norm.title if v.norm else None} for v in vs]
    raise KeyError(name)


def handle(req: dict) -> dict | None:
    m, rid = req.get("method"), req.get("id")
    if m == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": req.get("params", {}).get("protocolVersion", "2024-11-05"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "taxfix-yearround", "version": "0.1"}}}
    if m == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if m == "tools/call":
        params = req.get("params", {})
        try:
            out = call(params["name"], params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)}]}}
        except Exception as e:  # the agent sees the refusal, never a silent guess
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": f"refused: {e}"}], "isError": True}}
    if m == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if rid is None:
        return None                                  # a notification; nothing to say
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"unknown method {m}"}}


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve()
