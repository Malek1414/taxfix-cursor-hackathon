"""
Localhost API for the year-round tax position — the shape Taxfix's app would call.

    python3 build/yearround/api.py            # http://127.0.0.1:8787
    curl -s localhost:8787/v1/position | python3 -m json.tool

Taxfix's stack (docs/DOSSIER.md): React Native single codebase, Node.js + Go
microservices on GCP. This service is one more read-only microservice behind
their gateway: it takes what the app already knows (the profile the user built
for last year's return, Belegabruf pre-fill, anything logged since) and returns
one number and a ranked list of moves. It writes nothing, files nothing, and
never touches the ELSTER pipeline. The client is a single card on the existing
home screen — see integration/.

Standard library only. CORS open for the demo so a local RN/web client can hit it.

Routes
  GET  /                       the home-screen simulator with the card, live
  GET  /v1/health
  GET  /v1/position?profile=demo                 the number today
  POST /v1/position            {profile}         the number for a real profile
  POST /v1/moves/price         {profile, candidate}
  POST /v1/q4/plan             {profile?, candidates?}  omit both for the demo
  POST /v1/audit               {text}            hallucination audit
  POST /v1/events/classify     {id, purpose}     work | business | private
  POST /v1/events/receipt      {id, status}      ok | unclear | wrong — no photo, no entry
  POST /v1/events/transaction  {merchant, amount, card?, category?, business?, receipt?}
                               from the iOS Shortcuts 'Transaction' automation on an Apple Pay payment
  GET  /v1/demo/card           the card payload the RN component renders
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from build.yearround.mcp_server import _candidate, _move, _plain, _profile, call   # noqa: E402
from build.yearround.moves import Candidate, Profile, november_profile, november_table, plan, position, price  # noqa: E402
from decimal import Decimal  # noqa: E402


def demo_candidates():
    """The November table plus anything the phone posted since the server started."""
    extra = []
    for e in EVENTS:
        if e.get("receipt") != "ok":
            continue                      # no photo, no entry (decided on the night); priced separately as pending
        label = f"{e['merchant']} — {e['amount']:.2f} EUR · receipt ✓"
        if e.get("purpose") == "work":
            extra.append(Candidate("werbungskosten", label, amount=Decimal(str(e["amount"]))))
        elif e.get("purpose") == "business":
            extra.append(Candidate("betriebsausgabe", label, amount=Decimal(str(e["amount"])),
                                   vat_rate=Decimal(str(e.get("vat_rate", "0.19")))))
        # private, or not yet classified: not a move
    return november_table() + extra

HOST, PORT = "0.0.0.0", 8787
EVENTS: list = []          # transactions posted from the phone (Shortcuts "Transaction" trigger)
RULES: dict = {}           # (merchant, card) -> purpose; "No writes a rule so that merchant never asks again"
BUSINESS_CARDS = ("business", "firma", "geschäft", "4821")   # the business card is the signal


def event_candidate(e) -> Candidate | None:
    label = f"{e['merchant']} — {e['amount']:.2f} EUR"
    if e.get("purpose") == "work":
        return Candidate("werbungskosten", label, amount=Decimal(str(e["amount"])))
    if e.get("purpose") == "business":
        return Candidate("betriebsausgabe", label, amount=Decimal(str(e["amount"])), vat_rate=Decimal(str(e.get("vat_rate", "0.19"))))
    return None


def pending_entries(p: Profile) -> list[dict]:
    """Classified but no usable receipt yet: show the value, don't count it (§ 14 UStG for VAT)."""
    out = []
    for e in EVENTS:
        c = event_candidate(e)
        if c is None or e.get("receipt") == "ok":
            continue
        m = price(p, c)
        out.append({**_move(m), "kind": c.kind, "shown": False, "status": "pending", "event_id": e["id"],
                    "receipt": e.get("receipt"), "vat_reclaim_eur": "0.00",
                    "why": {"none": "add the receipt photo — the entry counts the moment it's attached",
                            "unclear": "photo unreadable — retake it",
                            "wrong": "that receipt doesn't match this payment — upload the right one"}[e.get("receipt", "none")]})
    return out


def week_summary(card_moves: list[dict], pending: list[dict]) -> dict:
    filed = [m for m in card_moves if m["status"] == "worth" and m["label"].endswith("receipt ✓")]
    return _plain({"entries": len(filed), "saving_eur": sum((Decimal(m["saving_eur"]) for m in filed), Decimal(0)),
                   "vat_eur": sum((Decimal(m.get("vat_reclaim_eur", "0")) for m in filed), Decimal(0)),
                   "receipts_missing": len(pending)})


def card_payload(profile=None, candidates=None) -> dict:
    """Exactly what the PositionCard component consumes. Stable contract."""
    p = _profile(profile)
    cs = [_candidate(c) for c in candidates] if candidates else demo_candidates()
    pos = position(p)
    taken, end = plan(p, cs)
    after = position(end).refund
    pend = pending_entries(p) if not candidates else []
    moves = [{**_move(m), "kind": m.candidate.kind, "shown": m.shown} for m in taken] + pend
    return _plain({
        "week": week_summary(moves, pend),
        "schema": "taxfix.yearround.card/1",
        "asOf": p.today,
        "headline": {"amountEur": pos.refund, "label": "If you filed today"},
        "deadline": {"date": p.deadline, "daysLeft": p.days_left, "basis": "§ 11 Abs. 2 EStG"},
        "afterPlan": {"amountEur": after, "deltaEur": after - pos.refund},
        "moves": moves,
        "disclosure": "Recomputed on the BMF Programmablaufplan. Nothing is filed. "
                      "Moves marked escalate need an expert.",
    })


class H(BaseHTTPRequestHandler):
    def _send(self, code: int, body):
        data = json.dumps(body, ensure_ascii=False, indent=1).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html", "/simulator"):
                html = (Path(__file__).resolve().parent / "integration" / "simulator.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html))); self.end_headers(); self.wfile.write(html); return
            if u.path == "/v1/health":
                return self._send(200, {"ok": True, "engine": "BMF PAP 2026", "writes": False})
            if u.path == "/v1/position":
                return self._send(200, call("tax_position", {}))
            if u.path == "/v1/demo/card":
                return self._send(200, card_payload())
            if u.path == "/v1/events":
                return self._send(200, {"events": EVENTS, "rules": {f"{k[0]} | {k[1]}": v for k, v in RULES.items()},
                                        "unclassified": [e for e in EVENTS if e.get("purpose") is None],
                                        "needs_receipt": [e for e in EVENTS if e.get("purpose") in ("work", "business") and e.get("receipt") != "ok"]})
            return self._send(404, {"error": f"no route {u.path}"})
        except Exception as e:
            return self._send(400, {"error": f"refused: {e}"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            b = self._body()
            if u.path == "/v1/position":
                return self._send(200, call("tax_position", {"profile": b.get("profile")}))
            if u.path == "/v1/moves/price":
                return self._send(200, call("price_move", b))
            if u.path == "/v1/q4/plan":
                return self._send(200, call("q4_plan", b))
            if u.path == "/v1/card":
                return self._send(200, card_payload(b.get("profile"), b.get("candidates")))
            if u.path == "/v1/events/transaction":
                # from the iOS Shortcuts "Transaction" automation: merchant, amount, card, category
                ev = {"id": len(EVENTS), "merchant": str(b.get("merchant", "Unknown")), "amount": float(b.get("amount", 0)),
                      "card": b.get("card", ""), "category": b.get("category", ""), "vat_rate": b.get("vat_rate", "0.19"),
                      "purpose": b.get("purpose"),            # work | business | private | None = ask the user
                      "receipt": b.get("receipt_status", "ok" if b.get("receipt") else "none"),  # none | ok | unclear | wrong
                      "ts": b.get("ts") or __import__("datetime").datetime.now().isoformat(timespec="seconds")}
                if ev["amount"] <= 0:
                    return self._send(400, {"error": "refused: amount must be positive"})
                key = (ev["merchant"].lower(), ev["card"].lower())
                on_business_card = any(t in ev["card"].lower() for t in BUSINESS_CARDS)
                if key in RULES:                                   # seen before: apply the rule, don't ask
                    ev["purpose"] = RULES[key]; ev["suggest"] = RULES[key]; ev["remembered"] = True
                else:                                              # first time: suggest from the card
                    ev["suggest"] = "business" if on_business_card else "private"; ev["remembered"] = False
                EVENTS.append(ev)
                card = card_payload()
                return self._send(200, {"saved": ev, "position_today_eur": card["headline"]["amountEur"],
                                        "after_plan_eur": card["afterPlan"]["amountEur"],
                                        "moves": len([m for m in card["moves"] if m["status"] == "worth"])})
            if u.path == "/v1/events/receipt":
                # the photo step: ok | unclear | wrong  (unclear/wrong keep the entry pending, offer re-upload)
                ev = EVENTS[int(b["id"])]
                ev["receipt"] = b.get("status", "ok")
                return self._send(200, {"event": ev, "card": card_payload()})
            if u.path == "/v1/events/classify":
                ev = EVENTS[int(b["id"])]
                ev["purpose"] = b["purpose"]
                RULES[(ev["merchant"].lower(), ev["card"].lower())] = b["purpose"]   # remember per merchant + card
                return self._send(200, {"event": ev, "card": card_payload(), "rule": f"{ev['merchant']} on {ev['card']} → {b['purpose']}, won't ask again"})
            if u.path == "/v1/audit":
                return self._send(200, call("audit_claim", b))
            return self._send(404, {"error": f"no route {u.path}"})
        except Exception as e:
            return self._send(400, {"error": f"refused: {e}"})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print(f"year-round position API on http://{HOST}:{port}  (read-only, files nothing)")
    ThreadingHTTPServer((HOST, port), H).serve_forever()
