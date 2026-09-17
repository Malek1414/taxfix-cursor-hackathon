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
from build.yearround.moves import Candidate, november_profile, november_table, plan, position  # noqa: E402
from decimal import Decimal  # noqa: E402


def demo_candidates():
    """The November table plus anything the phone posted since the server started."""
    extra = []
    for e in EVENTS:
        if not e.get("business", True):
            continue
        extra.append(Candidate("werbungskosten", f"{e['merchant']} — {e['amount']} EUR ({e.get('category') or 'business purchase'})",
                               amount=Decimal(str(e["amount"]))))
    return november_table() + extra

HOST, PORT = "0.0.0.0", 8787
EVENTS: list = []          # transactions posted from the phone (Shortcuts "Transaction" trigger)


def card_payload(profile=None, candidates=None) -> dict:
    """Exactly what the PositionCard component consumes. Stable contract."""
    p = _profile(profile)
    cs = [_candidate(c) for c in candidates] if candidates else demo_candidates()
    pos = position(p)
    taken, end = plan(p, cs)
    after = position(end).refund
    return _plain({
        "schema": "taxfix.yearround.card/1",
        "asOf": p.today,
        "headline": {"amountEur": pos.refund, "label": "If you filed today"},
        "deadline": {"date": p.deadline, "daysLeft": p.days_left, "basis": "§ 11 Abs. 2 EStG"},
        "afterPlan": {"amountEur": after, "deltaEur": after - pos.refund},
        "moves": [{**_move(m), "kind": m.candidate.kind, "shown": m.shown} for m in taken],
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
                ev = {"merchant": str(b.get("merchant", "Unknown")), "amount": float(b.get("amount", 0)),
                      "card": b.get("card", ""), "category": b.get("category", ""),
                      "business": bool(b.get("business", True)), "receipt": bool(b.get("receipt", False))}
                if ev["amount"] <= 0:
                    return self._send(400, {"error": "refused: amount must be positive"})
                EVENTS.append(ev)
                card = card_payload()
                return self._send(200, {"saved": ev, "position_today_eur": card["headline"]["amountEur"],
                                        "after_plan_eur": card["afterPlan"]["amountEur"],
                                        "moves": len([m for m in card["moves"] if m["status"] == "worth"])})
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
