"""
Year-round tax position — validation and the two-minute stage path.

    python3 build/yearround/demo.py           # the suite, prints the number
    python3 build/yearround/demo.py --stage   # the demo beats

Oracle: the BMF Programmablaufplan (`core.pap`) for the tariff, and the statute
text (`core.law`) for every cited paragraph. Every expected value below is
computed BY HAND in this file — taxable income written out as arithmetic — and
then handed to the tariff. The engine's own helpers are never used to build an
expectation, so agreement is not circular.

Declared before the first run:
    metric    shown euro figures cent-exact vs. hand-computed oracle
    pass bar  100 % exact · 0 silent errors · every adversarial refusal held
              · over-escalation ≤ 20 %
    failure   a move shown with the wrong euro value, or shown when it should
              have been refused
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.harness.harness import Case, Suite                     # noqa: E402
from core.pap.engine import lohnsteuer                           # noqa: E402
from build.yearround.moves import (                              # noqa: E402
    Candidate, Profile, moves_for, november_profile, november_table, plan, position, price,
)

G = Decimal(58_000)


def T(taxable, stkl: int = 1) -> Decimal:
    """The oracle: the federal algorithm on a hand-computed taxable amount."""
    return lohnsteuer(Decimal(taxable), stkl=stkl)["LSTLZZ"]


def exp(delta: Decimal) -> dict:
    """The tariff works in whole euros; a saving that rounds to 0 is honestly 0."""
    return {"status": "worth" if delta > 0 else "zero", "saving": delta}


def prof(**kw) -> dict:
    base = dict(gross=G, stkl=1, werbungskosten=0, homeoffice_days=0,
                handwerker_labour=0, haushalt_labour=0, spenden=0)
    base.update(kw)
    return base


def cand(kind, **kw) -> dict:
    kw.setdefault("label", kind)
    return dict(kind=kind, **kw)


def build_suite() -> Suite:
    s = Suite(
        name="Year-round tax position · Q4 moves",
        oracle="BMF Programmablaufplan on hand-computed taxable income; statute text for citations",
        metric="euro figures cent-exact; silent errors and over-escalations separately",
        pass_bar="100 % exact · 0 silent errors · all adversarial refusals held · over-escalation ≤ 20 %",
        failure_mode="a move shown with the wrong euro value, or shown when it should have been refused",
    )
    A = "adversarial"
    C = s.cases.append

    # --- Werbungskosten and the 1 230 EUR Pauschbetrag (§ 9, § 9a) ---------------
    # WK 410 + 96 home-office days × 6 = 986; + 899 laptop = 1 885; 1 885 − 1 230 = 655 over
    C(Case("laptop crosses the Pauschbetrag", {"profile": prof(werbungskosten=410, homeoffice_days=96),
           "candidate": cand("werbungskosten", amount=899)}, exp(T(G) - T(G - 655))))
    # WK 2 000 already over by 770; + 899 → over by 1 669
    C(Case("laptop, already above", {"profile": prof(werbungskosten=2000),
           "candidate": cand("werbungskosten", amount=899)}, exp(T(G - 770) - T(G - 1669))))
    C(Case("laptop stays below the Pauschbetrag → 0, says why", {"profile": prof(werbungskosten=500),
           "candidate": cand("werbungskosten", amount=300)}, {"status": "zero"}, tier=A,
           note="500 + 300 = 800 < 1 230: the allowance is granted anyway"))
    C(Case("lands exactly on 1 230 → 0", {"profile": prof(werbungskosten=1000),
           "candidate": cand("werbungskosten", amount=230)}, {"status": "zero"}, tier=A))
    C(Case("one euro over — whole-euro tariff decides", {"profile": prof(werbungskosten=1000),
           "candidate": cand("werbungskosten", amount=231)}, exp(T(G) - T(G - 1))))
    # Steuerklasse 3
    C(Case("laptop, Steuerklasse 3", {"profile": prof(stkl=3, werbungskosten=2000),
           "candidate": cand("werbungskosten", amount=899)}, exp(T(G - 770, 3) - T(G - 1669, 3))))
    # interaction: donation already on the board must not change the WK delta
    # WK 1 885 → over 655; spenden 250 → 214; laptop +100 → over 755
    C(Case("WK delta independent of donations already logged",
           {"profile": prof(werbungskosten=1885, spenden=250), "candidate": cand("werbungskosten", amount=100)},
           exp(T(G - 655 - 214) - T(G - 755 - 214))))
    C(Case("valid outside citation with supported claim",
           {"profile": prof(werbungskosten=2000),
            "candidate": cand("werbungskosten", amount=500, citation="§ 9 EStG", claim="Werbungskosten")},
           exp(T(G - 770) - T(G - 1270))))

    # --- home office (§ 4 Abs. 5 Nr. 6c): 6 EUR/day, cap 1 260 -----------------------
    C(Case("30 home-office days, above the Pauschbetrag", {"profile": prof(werbungskosten=1500),
           "candidate": cand("homeoffice", amount=30)}, exp(T(G - 270) - T(G - 450))))
    # 200 days = 1 200; +50 → 250 days = 1 500, capped 1 260 → over by 30
    C(Case("home-office cap at 1 260", {"profile": prof(homeoffice_days=200),
           "candidate": cand("homeoffice", amount=50)}, exp(T(G) - T(G - 30))))
    C(Case("home-office days below the Pauschbetrag → 0", {"profile": prof(werbungskosten=410, homeoffice_days=96),
           "candidate": cand("homeoffice", amount=30)}, {"status": "zero"}, tier=A,
           note="986 + 180 = 1 166 < 1 230"))

    # --- Handwerker (§ 35a Abs. 3): 20 % of labour, cap 1 200, transfer only ----------
    C(Case("Elektriker 2 100 labour → 420 off the tax", {"profile": prof(),
           "candidate": cand("handwerker", amount=2900, labour=2100)}, exp(Decimal(420))))
    C(Case("7 000 labour hits the 1 200 cap", {"profile": prof(),
           "candidate": cand("handwerker", amount=7000, labour=7000)}, exp(Decimal(1200))))
    # 900 used → credit 180; +3 000 → 3 900 × 20 % = 780; 780 − 180 = 600
    C(Case("partial cap already used", {"profile": prof(handwerker_labour=900),
           "candidate": cand("handwerker", amount=3000, labour=3000)}, exp(Decimal(600))))
    # 5 500 used → 1 100; +2 000 → 7 500 × 20 % = 1 500 → cap 1 200; 1 200 − 1 100 = 100
    C(Case("crosses the cap mid-move", {"profile": prof(handwerker_labour=5500),
           "candidate": cand("handwerker", amount=2000, labour=2000)}, exp(Decimal(100))))
    C(Case("cap already maxed → 0, says why", {"profile": prof(handwerker_labour=6000),
           "candidate": cand("handwerker", amount=2000, labour=2000)}, {"status": "zero"}, tier=A))
    C(Case("paid in cash → 0 (§ 35a Abs. 5)", {"profile": prof(),
           "candidate": cand("handwerker", amount=600, labour=600, cash=True)}, {"status": "zero"}, tier=A))
    C(Case("materials only → 0 (§ 35a Abs. 5)", {"profile": prof(),
           "candidate": cand("handwerker", amount=2900, labour=0)}, {"status": "zero"}, tier=A))
    # low income: the credit cannot push tax below zero
    t12 = T(12_000)
    C(Case("low income: credit floors at zero", {"profile": prof(gross=12_000),
           "candidate": cand("handwerker", amount=2100, labour=2100)},
           exp(t12 - max(Decimal(0), t12 - 420)), tier=A))
    C(Case("high income, same 420", {"profile": prof(gross=120_000),
           "candidate": cand("handwerker", amount=2100, labour=2100)}, exp(Decimal(420))))

    # --- haushaltsnahe Dienstleistungen (§ 35a Abs. 2): 20 %, cap 4 000 ---------------
    C(Case("Haushaltshilfe 3 000 → 600", {"profile": prof(),
           "candidate": cand("haushalt", amount=3000, labour=3000)}, exp(Decimal(600))))
    C(Case("25 000 hits the 4 000 cap", {"profile": prof(),
           "candidate": cand("haushalt", amount=25000, labour=25000)}, exp(min(Decimal(4000), T(G)))))

    # --- Spenden (§ 10b, § 10c): above 36, up to 20 % of income ----------------------
    C(Case("250 EUR donation → 214 off taxable", {"profile": prof(),
           "candidate": cand("spende", amount=250)}, exp(T(G) - T(G - 214))))
    C(Case("20 EUR donation, under the 36 EUR Pauschbetrag → 0", {"profile": prof(),
           "candidate": cand("spende", amount=20)}, {"status": "zero"}, tier=A))
    # 20 % of 58 000 = 11 600; − 36 = 11 564
    C(Case("20 000 donation capped at 20 % of income", {"profile": prof(),
           "candidate": cand("spende", amount=20000)}, exp(T(G) - T(G - 11564))))
    # 20 % of 10 000 = 2 000; − 36 = 1 964
    C(Case("donation on low income", {"profile": prof(gross=10_000),
           "candidate": cand("spende", amount=5000)}, exp(T(10_000) - T(10_000 - 1964))))

    # --- refusals: the engine must say no, out loud ------------------------------------
    C(Case("invented paragraph § 99z EStG", {"profile": prof(),
           "candidate": cand("werbungskosten", amount=800, citation="§ 99z EStG", claim="absetzbar")},
           {"status": "escalate"}, tier=A))
    C(Case("real paragraph, wrong subject: § 35b for Materialkosten", {"profile": prof(),
           "candidate": cand("werbungskosten", amount=800, citation="§ 35b EStG", claim="Materialkosten absetzbar")},
           {"status": "escalate"}, tier=A))
    C(Case("marry before 31.12. — needs spouse income", {"profile": prof(),
           "candidate": cand("other", amount=0)}, {"status": "escalate"}, tier=A))
    C(Case("Riester top-up — needs contract facts", {"profile": prof(),
           "candidate": cand("other", label="Riester", amount=2100)}, {"status": "escalate"}, tier=A))
    C(Case("negative amount", {"profile": prof(),
           "candidate": cand("werbungskosten", amount=-500)}, {"status": "escalate"}, tier=A))
    return s


def system(inputs: dict):
    return price(Profile(**inputs["profile"]), Candidate(**inputs["candidate"]))


def compare(move, want: dict) -> bool:
    if move.status != want["status"]:
        return False
    if "saving" in want and move.saving != Decimal(want["saving"]).quantize(Decimal("0.01")):
        return False
    return True


def validate() -> Suite:
    s = build_suite()
    return s.run(system, compare=compare, escalated=lambda m: m.status == "escalate")


# ---------------------------------------------------------------------------

def stage():
    bar = "=" * 74
    p = november_profile()
    pos = position(p)
    print(f"\n{bar}\n  YOUR TAX POSITION, LIVE  ·  {p.today:%d.%m.%Y}\n{bar}")

    print(f"\n  BEAT 1 — the number today (not a reminder, a quantity)")
    print(f"    {p.name}, Steuerklasse {p.stkl}, {p.gross:,.0f} EUR gross")
    print(f"    logged this year: {p.werbungskosten:,.0f} EUR Werbungskosten, {p.homeoffice_days} home-office days, "
          f"{p.handwerker_labour:,.0f} EUR Handwerker labour")
    print(f"    if you filed today you'd get back:        {pos.refund:>10,.2f} EUR")
    print(f"    days to 31.12. (§ 11 EStG, not our design): {pos.days_left:>10}")

    print(f"\n  BEAT 2 — the moves, priced on the BMF algorithm, in order")
    taken, end = plan(p, november_table())
    for m in [m for m in taken if m.status == "worth"]:
        print(f"    + {m.saving:>8,.2f} EUR  {m.candidate.label}")
        print(f"                     {m.why}  [{m.citation}]")
    print(f"    position after the plan:                  {position(end).refund:>10,.2f} EUR")

    print(f"\n  BEAT 3 — the catch (the part that is Taxfix, not ChatGPT)")
    for m in [m for m in taken if m.status != "worth"]:
        print(f"    x {m.status:<8}  {m.candidate.label}")
        print(f"                {m.why}")

    s = validate()
    print(f"\n  BEAT 4 — the proof")
    print(f"    {s.headline()}")
    print(f"\n  Synthetic: the profile. Standing in: the wage-tax PAP for the annual tariff.")
    print(f"  Coded from the statute, not rulings: § 9a, § 35a, § 10b, § 10c, § 4 Abs. 5 Nr. 6c.\n{bar}\n")


if __name__ == "__main__":
    if "--stage" in sys.argv:
        stage()
    else:
        s = validate()
        print(s.report(verbose="-v" in sys.argv))
        print(s.headline())
