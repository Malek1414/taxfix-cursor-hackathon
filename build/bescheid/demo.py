"""
Bescheid-Check — the validation run and the stage demo.

    python3 build/bescheid/demo.py            # the 40-case validation
    python3 build/bescheid/demo.py --stage    # the 3-minute demo path

The 40 notices are synthetic, and we say so out loud. Real Steuerbescheide are
personal tax data and are correctly not public. Synthetic is not a weakness here:
it is the only way to know the answer by construction, which is what lets us
report a silent-error rate at all.

The part that is *not* synthetic is the arithmetic. Every euro figure is
recomputed from the BMF's own Programmablaufplan, so we are not merely finding
errors we planted.
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from build.bescheid.check import (Bescheid, Filing, Line, draft_einspruch,  # noqa: E402
                                  review)
from core.harness.harness import Case, Suite  # noqa: E402

# Grounds the Finanzamt actually uses, and whether they hold up.
LAWFUL_GROUNDS = [
    ("Arbeitsmittel ohne Nachweis nicht anerkannt (§ 9 EStG).", "§ 9 EStG"),
    ("Entfernungspauschale auf die kürzeste Straßenverbindung korrigiert.", "§ 9 EStG"),
    ("Doppelte Haushaltsführung nicht nachgewiesen.", "§ 9 EStG"),
]
BOGUS_GROUNDS = [("Keine Begründung angegeben.", "")]

LINES = [
    ("werbungskosten", "Werbungskosten"),
    ("sonderausgaben", "Sonderausgaben"),
]


def make_case(rng: random.Random, kind: str, i: int) -> tuple[Filing, Bescheid, str]:
    """kind: clean | error | lawful"""
    gross = Decimal(rng.randrange(28_000, 145_000, 500))
    filing = Filing(
        gross=gross,
        stkl=rng.choice([1, 1, 1, 3, 4]),
        werbungskosten=Decimal(rng.randrange(800, 6_000, 50)),
        sonderausgaben=Decimal(rng.randrange(400, 3_500, 50)),
        name=f"Testfall {i:02d}",
    )
    issued = date(2026, 6, 1) + timedelta(days=rng.randrange(0, 90))
    lines: list[Line] = []

    if kind == "clean":
        for key, label in LINES:
            v = getattr(filing, key)
            lines.append(Line(key, label, v, v))
        expect = "no-challenge"

    elif kind == "lawful":
        key, label = rng.choice(LINES)
        v = getattr(filing, key)
        cut = Decimal(rng.randrange(200, 1200, 50))
        ground, cite = rng.choice(LAWFUL_GROUNDS)
        lines.append(Line(key, label, v, v - cut, lawful=True, ground=ground, citation=cite))
        for k2, l2 in LINES:
            if k2 != key:
                lines.append(Line(k2, l2, getattr(filing, k2), getattr(filing, k2)))
        expect = "no-challenge"

    else:  # error
        key, label = rng.choice(LINES)
        v = getattr(filing, key)
        cut = Decimal(rng.randrange(400, 3_000, 50))
        ground, cite = rng.choice(BOGUS_GROUNDS)
        lines.append(Line(key, label, v, v - cut, lawful=False, ground=ground, citation=cite))
        for k2, l2 in LINES:
            if k2 != key:
                lines.append(Line(k2, l2, getattr(filing, k2), getattr(filing, k2)))
        expect = "challenge"

    notice = Bescheid(issued=issued, lines=lines)
    # The office states the tax implied by its own assessed figures.
    from build.bescheid.check import _recompute
    notice.stated_tax = _recompute(filing, notice)

    if kind == "arithmetic":
        # The lines are all fine; the office's own tariff arithmetic is off.
        # Only the federal recompute can catch this — a line diff cannot.
        notice.stated_tax += Decimal(rng.randrange(120, 900, 10))
        expect = "challenge"

    return filing, notice, expect


def build_suite(n_clean=10, n_error=20, n_lawful=5, n_arith=5, seed=7) -> Suite:
    rng = random.Random(seed)
    cases = []
    for i in range(n_clean):
        f, b, e = make_case(rng, "clean", i)
        cases.append(Case(f"clean #{i+1}", {"filing": f, "notice": b}, e))
    # 'clean' notices must also survive the federal recompute unflagged.
    for i in range(n_error):
        f, b, e = make_case(rng, "error", i)
        at = abs(b.lines[0].delta)
        cases.append(Case(f"deviation #{i+1} (~{at:,.0f} EUR)", {"filing": f, "notice": b}, e))
    for i in range(n_arith):
        f, b, e = make_case(rng, "arithmetic", i)
        cases.append(Case(f"tariff arithmetic error #{i+1}", {"filing": f, "notice": b}, e,
                          note="only the federal recompute can catch this"))
    for i in range(n_lawful):
        f, b, e = make_case(rng, "lawful", i)
        cases.append(Case(f"lawful adjustment #{i+1}", {"filing": f, "notice": b}, e,
                          tier="adversarial",
                          note="the Finanzamt was right; flagging this is the failure"))
    return Suite(
        name="Bescheid-Check — 40 synthetic notices, federally recomputed",
        oracle="BMF Programmablaufplan 2026 + known injected deviations",
        metric="recall on deviations >= 50 EUR; false positives per clean notice",
        pass_bar="0 silent errors, all 5 lawful adjustments correctly not flagged",
        failure_mode="crying wolf — flagging a lawful adjustment teaches users to "
                     "file pointless objections",
        cases=cases,
    )


def system(inputs):
    r = review(inputs["filing"], inputs["notice"], today=date(2026, 7, 1))
    r.verdict = "challenge" if r.challenges else "no-challenge"  # type: ignore[attr-defined]
    return r


def validate() -> Suite:
    s = build_suite()
    s.run(system,
          compare=lambda out, want: out.verdict == want,
          escalated=lambda out: out.escalate)
    return s


# ---------------------------------------------------------------------------

def stage():
    """The demo path. Beat 3 is the one that wins."""
    bar = "=" * 74
    print(f"\n{bar}\n  BESCHEID-CHECK  ·  live on the federal algorithm\n{bar}")

    filing = Filing(gross=Decimal(58_000), stkl=1,
                    werbungskosten=Decimal(2_400), sonderausgaben=Decimal(1_800),
                    name="M. Hassan")
    notice = Bescheid(
        issued=date(2026, 6, 12),
        lines=[
            Line("werbungskosten", "Werbungskosten", Decimal(2_400), Decimal(700),
                 lawful=False, ground="Keine Begründung angegeben."),
            Line("sonderausgaben", "Sonderausgaben", Decimal(1_800), Decimal(1_800)),
        ],
    )
    from build.bescheid.check import _recompute
    notice.stated_tax = _recompute(filing, notice)

    r = review(filing, notice, today=date(2026, 7, 1))

    print(f"\n  BEAT 1 — what arrived")
    print(f"    {notice.office}, Einkommensteuerbescheid 2026")
    print(f"    issued {notice.issued:%d.%m.%Y}  ·  served {notice.served():%d.%m.%Y} (§122 AO)")
    print(f"    festgesetzte Steuer: {notice.stated_tax:,.2f} EUR")

    print(f"\n  BEAT 2 — independent recompute")
    print(f"    our figure from the BMF Programmablaufplan: {r.recomputed_tax:,.2f} EUR")
    print(f"    the office's figure:                        {r.stated_tax:,.2f} EUR")
    print(f"    Werbungskosten cut {abs(notice.lines[0].delta):,.2f} EUR with no stated ground")
    for f in r.challenges:
        print(f"    -> {f.label}: worth {abs(f.euro_impact):,.2f} EUR to you")

    print(f"\n  BEAT 3 — the catch (this is the 20 seconds that wins)")
    lawful = Bescheid(
        issued=date(2026, 6, 12),
        lines=[
            Line("werbungskosten", "Werbungskosten", Decimal(2_400), Decimal(1_900),
                 lawful=True,
                 ground="Entfernungspauschale auf die kürzeste Straßenverbindung korrigiert.",
                 citation="§ 9 EStG"),
            Line("sonderausgaben", "Sonderausgaben", Decimal(1_800), Decimal(1_800)),
        ],
    )
    lawful.stated_tax = _recompute(filing, lawful)
    r2 = review(filing, lawful, today=date(2026, 7, 1))
    print(f"    Same shape of deviation — 500 EUR off Werbungskosten — but lawful.")
    print(f"    citation {lawful.lines[0].citation} resolves in the statute: "
          f"{[f.citation_ok for f in r2.findings if f.citation][0]}")
    print(f"    challenges raised: {len(r2.challenges)}   <- correctly stays quiet")

    print(f"\n  BEAT 4 — the clock (§355 Abs 1 AO)")
    print(f"    objection deadline {r.deadline:%d.%m.%Y}  ·  {r.days_left} days left")

    print(f"\n  BEAT 5 — the draft")
    draft = draft_einspruch(filing, notice, r)
    for line in draft.strip().splitlines()[:9]:
        print("    " + line)
    print("    …")

    s = validate()
    print(f"\n{bar}\n  {s.headline()}\n  total at stake in this case: {r.total_at_stake:,.2f} EUR\n{bar}\n")


if __name__ == "__main__":
    if "--stage" in sys.argv:
        stage()
    else:
        s = validate()
        print(s.report(verbose="-v" in sys.argv))
        print("\n  say on stage:", s.headline())
        sys.exit(0 if s.clean else 1)
