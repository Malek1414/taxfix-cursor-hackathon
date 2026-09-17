"""Tap n' tax classifier: one payment in, one decision out, and it learns.

Drop-in and dependency free, so anyone can vendor this file. Two calls:

    d = decide(tx, mem)            # what to do with a payment
    learn(tx, "business", mem)     # what the user answered

`tx` is whatever the Wallet automation posts: merchant, amount, card, and
optionally category. `mem` is a plain dict you keep on disk (load/save below).

The decision is one of:
    auto   file it without asking, the user has answered this merchant the same
           way often enough and nothing about this payment is unusual
    ask    show the question
    skip   do not interrupt at all, this is private and nobody wants a push

Rules that do not bend, because a wrong auto is worse than a question:
  * frequency alone is never a reason. Two supermarket visits are evidence of
    groceries, not of business, so ambiguous merchants never reach auto.
  * auto only under a value limit, and only when the amount looks like the ones
    already confirmed for that merchant.
  * every auto decision carries the reason and stays revocable. The caller is
    expected to show them in the weekly list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONFIRMATIONS_FOR_AUTO = 2      # same answer this many times before we stop asking
AUTO_LIMIT_EUR = 250.0          # never file something bigger without a human
OUTLIER_FACTOR = 2.5            # an amount this far above the known ones asks again

# Merchants whose trade says nothing about why you were there. These may be
# remembered, they may never go auto.
AMBIGUOUS = ("rewe", "edeka", "lidl", "aldi", "kaufland", "netto", "penny",
             "dm ", "rossmann", "amazon", "paypal", "sumup", "zettle", "restaurant",
             "cafe", "bar ", "hotel", "uber", "bolt", "tankstelle", "shell", "aral")

# Trades where a business card makes the purpose obvious enough to stop asking.
CLEAR_BUSINESS = {
    "software": ("adobe", "figma", "github", "notion", "slack", "openai", "anthropic",
                 "jetbrains", "atlassian", "google cloud", "aws", "hetzner", "vercel"),
    "office supplies": ("staples", "viking", "buerobedarf", "büro", "office discount"),
    "hardware": ("apple store", "gravis", "cyberport", "conrad", "reichelt"),
    "travel": ("db vertrieb", "deutsche bahn", "bvg", "flixbus", "lufthansa"),
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _key(tx: dict) -> str:
    return f"{_norm(tx.get('merchant'))}|{_norm(tx.get('card'))}"


def _trade(merchant: str) -> tuple[str, bool]:
    """(category, unambiguous) for a merchant string."""
    m = _norm(merchant)
    for cat, names in CLEAR_BUSINESS.items():
        if any(n in m for n in names):
            return cat, True
    if any(a in m + " " for a in AMBIGUOUS):
        return "", False
    return "", False


def _business_card(tx: dict) -> bool:
    return "business" in _norm(tx.get("card"))


def decide(tx: dict, mem: dict | None = None) -> dict:
    """What to do with this payment. Never raises, always explains itself."""
    mem = mem or {}
    amount = float(tx.get("amount") or 0)
    seen = (mem.get("merchants") or {}).get(_key(tx))
    category, unambiguous = _trade(tx.get("merchant", ""))
    on_business = _business_card(tx)

    if seen:
        purpose = seen["purpose"]
        confirmations = seen["count"]
        category = seen.get("category") or category
        known_max = max(seen.get("amounts") or [amount])
        outlier = amount > known_max * OUTLIER_FACTOR

        if purpose == "private":
            return _out("skip", purpose, category, 0.9,
                        "you have marked this merchant private before")
        if confirmations < CONFIRMATIONS_FOR_AUTO:
            return _out("ask", purpose, category, 0.6,
                        f"answered once before, asking again to be sure")
        if not unambiguous:
            return _out("ask", purpose, category, 0.7,
                        "this merchant sells both, so the reason is yours to give")
        if amount > AUTO_LIMIT_EUR:
            return _out("ask", purpose, category, 0.8,
                        f"over the {AUTO_LIMIT_EUR:.0f} EUR limit for filing without asking")
        if outlier:
            return _out("ask", purpose, category, 0.7,
                        "larger than what you usually spend here")
        return _out("auto", purpose, category, 0.95,
                    f"filed the same way {confirmations} times, amount is in range")

    # first time at this merchant
    if on_business and unambiguous:
        return _out("ask", "business", category, 0.8,
                    "business card and the merchant's trade matches, confirm once")
    if on_business:
        return _out("ask", "business", category, 0.6,
                    "business card, but this merchant sells both")
    if unambiguous:
        return _out("ask", "business", category, 0.5,
                    "the trade looks business, the card does not")
    return _out("skip", "private", category, 0.6,
                "private card at a merchant that says nothing about the reason")


def _out(action, purpose, category, confidence, reason) -> dict:
    return {"action": action, "purpose": purpose, "category": category or "other",
            "confidence": confidence, "reason": reason}


def learn(tx: dict, purpose: str, mem: dict, category: str | None = None) -> dict:
    """Record what the user answered. A changed answer resets the count."""
    merchants = mem.setdefault("merchants", {})
    e = merchants.setdefault(_key(tx), {"purpose": purpose, "count": 0,
                                        "amounts": [], "category": category})
    if e["purpose"] != purpose:
        e["purpose"], e["count"], e["amounts"] = purpose, 0, []
    e["count"] += 1
    e["amounts"] = (e["amounts"] + [float(tx.get("amount") or 0)])[-10:]
    if category:
        e["category"] = category
    return mem


def load(path: str | Path) -> dict:
    p = Path(path)
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"merchants": {}}


def save(mem: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(mem, indent=1, ensure_ascii=False))
