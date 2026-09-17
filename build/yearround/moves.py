"""
Year-round tax position, and the moves that change it before 31 December.

    Profile   what Taxfix knows about you today (gross, class, what you've logged)
    Position  what your return is worth if you filed today — from the BMF tariff
    Candidate something on the table (a laptop, an invoice, a donation …)
    Move      the candidate priced: worth / zero / escalate, with the statute

Every euro figure comes from `core.pap.engine.lohnsteuer` (the federal
Programmablaufplan) on two states — before and after — so the saving is a
recompute, not a heuristic. Every move carries a citation that must resolve in
`core.law`; a move whose citation fails is refused, never shown.

Decimal everywhere. No float touches money.

Honest limits (say these on stage):
  * The wage-tax PAP stands in for the annual assessment tariff.
  * Thresholds and caps below are coded from the statute text, not rulings.
  * Marriage, Riester, capital gains: the engine refuses and asks for a human.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.law.cite import check as cite_check          # noqa: E402
from core.pap.engine import lohnsteuer                 # noqa: E402

CENT = Decimal("0.01")

# --- statutory constants, 2026 -------------------------------------------------
# Each one is a claim. The citation next to it is what `core.law` resolves.
WK_PAUSCHBETRAG   = Decimal(1230)   # § 9a S. 1 Nr. 1a EStG  Arbeitnehmer-Pauschbetrag
HOMEOFFICE_DAY    = Decimal(6)      # § 4 Abs. 5 S. 1 Nr. 6c EStG  Tagespauschale
HOMEOFFICE_CAP    = Decimal(1260)   #   … höchstens 1 260 EUR (210 Tage)
HANDWERKER_RATE   = Decimal("0.20") # § 35a Abs. 3 EStG  20 % der Arbeitskosten
HANDWERKER_CAP    = Decimal(1200)   #   … höchstens 1 200 EUR
HAUSHALT_RATE     = Decimal("0.20") # § 35a Abs. 2 EStG  haushaltsnahe Dienstleistungen
HAUSHALT_CAP      = Decimal(4000)   #   … höchstens 4 000 EUR
SPENDEN_CAP_RATE  = Decimal("0.20") # § 10b Abs. 1 EStG  bis 20 % des Gesamtbetrags der Einkünfte
SA_PAUSCHBETRAG   = Decimal(36)     # § 10c EStG  Sonderausgaben-Pauschbetrag

CITES = {
    "werbungskosten": "§ 9 EStG",
    "pauschbetrag":   "§ 9a EStG",
    "homeoffice":     "§ 4 EStG",
    "handwerker":     "§ 35a EStG",
    "haushalt":       "§ 35a EStG",
    "spende":         "§ 10b EStG",
    "abfluss":        "§ 11 EStG",
}


def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


# --- the profile ----------------------------------------------------------------

@dataclass
class Profile:
    """What Taxfix knows about you today."""

    gross: Decimal                        # Bruttoarbeitslohn, full year
    stkl: int = 1
    year: int = 2026
    werbungskosten: Decimal = Decimal(0)  # logged this year, excluding home office
    homeoffice_days: int = 0
    handwerker_labour: Decimal = Decimal(0)   # labour already paid by transfer this year
    haushalt_labour: Decimal = Decimal(0)
    spenden: Decimal = Decimal(0)
    today: date = date(2026, 11, 12)
    name: str = "Musterperson"

    def __post_init__(self):
        for f in ("gross", "werbungskosten", "handwerker_labour", "haushalt_labour", "spenden"):
            setattr(self, f, D(getattr(self, f)))

    # -- derived, each one a statutory rule ---------------------------------
    @property
    def homeoffice_pauschale(self) -> Decimal:
        return min(HOMEOFFICE_DAY * self.homeoffice_days, HOMEOFFICE_CAP)

    @property
    def werbungskosten_total(self) -> Decimal:
        return self.werbungskosten + self.homeoffice_pauschale

    @property
    def werbungskosten_effective(self) -> Decimal:
        """Only the part above the Pauschbetrag lowers taxable income (§ 9a)."""
        return max(Decimal(0), self.werbungskosten_total - WK_PAUSCHBETRAG)

    @property
    def spenden_effective(self) -> Decimal:
        capped = min(self.spenden, (self.gross * SPENDEN_CAP_RATE).quantize(CENT))
        return max(Decimal(0), capped - SA_PAUSCHBETRAG)

    @property
    def taxable(self) -> Decimal:
        return max(Decimal(0), self.gross - self.werbungskosten_effective - self.spenden_effective)

    @property
    def credit_35a(self) -> Decimal:
        hw = min((self.handwerker_labour * HANDWERKER_RATE).quantize(CENT), HANDWERKER_CAP)
        hh = min((self.haushalt_labour * HAUSHALT_RATE).quantize(CENT), HAUSHALT_CAP)
        return hw + hh

    @property
    def deadline(self) -> date:
        return date(self.year, 12, 31)

    @property
    def days_left(self) -> int:
        return (self.deadline - self.today).days


def tariff(taxable: Decimal, stkl: int, year: int) -> Decimal:
    """The BMF algorithm on a taxable amount. The oracle."""
    return lohnsteuer(max(Decimal(0), taxable), stkl=stkl, year=year)["LSTLZZ"]


def tax(p: Profile) -> Decimal:
    """Tax owed for the year on today's facts: tariff minus § 35a credit, never below 0."""
    return max(Decimal(0), tariff(p.taxable, p.stkl, p.year) - p.credit_35a)


@dataclass
class Position:
    withheld: Decimal      # what the employer will have paid in by December
    tax: Decimal           # what you actually owe on today's facts
    refund: Decimal        # the number on the screen
    taxable: Decimal
    credit_35a: Decimal
    wk_total: Decimal
    wk_gap: Decimal        # how far below the Pauschbetrag you still are (0 if above)
    days_left: int


def position(p: Profile) -> Position:
    withheld = tariff(p.gross, p.stkl, p.year)
    t = tax(p)
    return Position(
        withheld=withheld, tax=t, refund=withheld - t, taxable=p.taxable,
        credit_35a=p.credit_35a, wk_total=p.werbungskosten_total,
        wk_gap=max(Decimal(0), WK_PAUSCHBETRAG - p.werbungskosten_total),
        days_left=p.days_left,
    )


# --- candidates and moves --------------------------------------------------------

@dataclass
class Candidate:
    """Something on the table this November. `kind` decides the rule."""

    kind: str                    # werbungskosten | homeoffice | handwerker | haushalt | spende | other
    label: str
    amount: Decimal = Decimal(0) # euros, or days for homeoffice
    labour: Decimal | None = None   # handwerker/haushalt: labour share (materials never count)
    cash: bool = False           # § 35a Abs. 5: cash payment gets nothing
    due: date | None = None      # when the bill is due — the December/January question
    citation: str | None = None  # an externally supplied citation (e.g. from an LLM tip)
    claim: str = ""

    def __post_init__(self):
        self.amount = D(self.amount)
        if self.labour is not None:
            self.labour = D(self.labour)


@dataclass
class Move:
    candidate: Candidate
    status: str                 # worth | zero | escalate
    saving: Decimal             # tax before − tax after, on the BMF algorithm
    citation: str
    citation_ok: bool
    why: str                    # the one honest sentence
    before: Decimal = Decimal(0)
    after: Decimal = Decimal(0)
    deadline: date | None = None

    @property
    def shown(self) -> bool:
        """Only priced, cited moves reach the screen. Refusals are shown *as* refusals."""
        return self.status == "worth" and self.citation_ok


def apply(p: Profile, c: Candidate) -> Profile | None:
    """The profile after the move. None = the engine cannot model it."""
    if c.kind == "werbungskosten":
        return replace(p, werbungskosten=p.werbungskosten + c.amount)
    if c.kind == "homeoffice":
        return replace(p, homeoffice_days=p.homeoffice_days + int(c.amount))
    if c.kind in ("handwerker", "haushalt"):
        if c.cash:
            return p                                  # § 35a Abs. 5 S. 3: nothing counts
        labour = c.labour if c.labour is not None else c.amount
        if c.due and c.due > p.deadline:
            pass                                      # paying early is the move; model it as paid this year
        key = "handwerker_labour" if c.kind == "handwerker" else "haushalt_labour"
        return replace(p, **{key: getattr(p, key) + labour})
    if c.kind == "spende":
        return replace(p, spenden=p.spenden + c.amount)
    return None


def price(p: Profile, c: Candidate) -> Move:
    """Price one candidate. Refuse what we cannot price; say why when it is zero."""
    citation = c.citation or CITES.get(c.kind, "")
    verdict = cite_check(citation, c.claim) if citation else None
    citation_ok = bool(verdict) if verdict is not None else False
    before = tax(p)

    # 1. an outside citation that does not resolve: refuse, never show
    if citation and not citation_ok:
        if verdict.exists:
            title = verdict.norm.title if getattr(verdict.norm, "title", "") else "a different matter"
            why = (f"cites {citation} — the paragraph exists but is about '{title}', "
                   f"not this claim ({verdict.reason}) — not shown; ask an expert")
        else:
            why = f"cites {citation}, which does not exist in the statute — not shown; ask an expert"
        return Move(c, "escalate", Decimal(0), citation, False, why, before, before, p.deadline)

    # 1b. nonsense input: refuse rather than guess
    if c.amount < 0 or (c.labour is not None and c.labour < 0):
        return Move(c, "escalate", Decimal(0), citation, citation_ok,
                    "negative amount — refused rather than guessed", before, before, p.deadline)

    after_p = apply(p, c)
    # 2. something the engine cannot model: refuse to a human
    if after_p is None:
        return Move(c, "escalate", Decimal(0), citation, citation_ok,
                    "needs facts the engine does not have (spouse income, contract, "
                    "holding period) — a human prices this, not an algorithm",
                    before, before, p.deadline)

    after = tax(after_p)
    saving = (before - after).quantize(CENT)
    assert saving >= 0, "a deduction never raises tax — if this fires, the model is wrong"

    # 3. priced, and zero: say exactly why
    if saving == 0:
        return Move(c, "zero", saving, citation, citation_ok, _why_zero(p, c, after_p),
                    before, after, p.deadline)

    return Move(c, "worth", saving, citation, citation_ok, _why_worth(p, c, after_p, saving),
                before, after, p.deadline)


def _why_zero(p: Profile, c: Candidate, q: Profile) -> str:
    if c.kind in ("handwerker", "haushalt") and c.cash:
        return "paid in cash — § 35a Abs. 5 EStG only counts bank transfers, so this is worth 0"
    if c.kind in ("handwerker", "haushalt") and c.labour is not None and c.labour == 0:
        return "materials only — § 35a Abs. 5 EStG counts labour, never materials, so this is worth 0"
    if c.kind in ("handwerker", "haushalt") and tax(p) == 0:
        return (f"you owe no tax in {p.year} to take this off — § 35a cannot go below zero; "
                f"paying in January puts the credit into {p.year + 1} instead")
    if False:
        return "paid in cash — § 35a Abs. 5 EStG only counts bank transfers, so this is worth 0"
    if c.kind in ("handwerker", "haushalt"):
        cap = HANDWERKER_CAP if c.kind == "handwerker" else HAUSHALT_CAP
        return f"your § 35a credit is already at the {cap:,.0f} EUR cap for {p.year}"
    if c.kind in ("werbungskosten", "homeoffice"):
        gap = WK_PAUSCHBETRAG - q.werbungskosten_total
        if gap > 0:
            return (f"still {gap:,.2f} EUR below the {WK_PAUSCHBETRAG:,.0f} EUR Pauschbetrag "
                    f"(§ 9a EStG) — you get that allowance anyway, so this saves 0 today")
        if c.kind == "homeoffice" and p.homeoffice_pauschale >= HOMEOFFICE_CAP:
            return f"home-office days are capped at {HOMEOFFICE_CAP:,.0f} EUR (§ 4 Abs. 5 Nr. 6c EStG)"
    if c.kind == "spende":
        return f"donations only count above the {SA_PAUSCHBETRAG} EUR Pauschbetrag (§ 10c) and up to 20 % of income (§ 10b)"
    return "no tax effect on today's facts"


def _why_worth(p: Profile, c: Candidate, q: Profile, saving: Decimal) -> str:
    if c.kind in ("handwerker", "haushalt"):
        when = f"by {p.deadline:%d.%m.%Y}" + (f", not {c.due:%d.%m.%Y}" if c.due and c.due > p.deadline else "")
        return (f"pay the labour share {when} by bank transfer — 20 % comes straight off "
                f"your tax (§ 35a EStG, Abfluss § 11 EStG)")
    if c.kind == "werbungskosten":
        crossed = p.werbungskosten_total < WK_PAUSCHBETRAG <= q.werbungskosten_total
        if crossed:
            over = q.werbungskosten_total - WK_PAUSCHBETRAG
            return (f"this takes you over the {WK_PAUSCHBETRAG:,.0f} EUR Pauschbetrag by "
                    f"{over:,.2f} EUR — only that part lowers your taxable income (§ 9, § 9a EStG)")
        return "you are above the Pauschbetrag, so every euro lowers taxable income (§ 9 EStG)"
    if c.kind == "homeoffice":
        return f"{int(c.amount)} more days × 6 EUR (§ 4 Abs. 5 Nr. 6c EStG) — log them, they count as Werbungskosten"
    if c.kind == "spende":
        return "deductible as Sonderausgaben, receipt needed above 300 EUR (§ 10b EStG)"
    return "lowers your tax on today's facts"


def moves_for(p: Profile, candidates: list[Candidate]) -> list[Move]:
    """Price everything; show worth first, largest saving first; refusals last, out loud."""
    ms = [price(p, c) for c in candidates]
    order = {"worth": 0, "zero": 1, "escalate": 2}
    return sorted(ms, key=lambda m: (order[m.status], -m.saving))


def plan(p: Profile, candidates: list[Candidate]) -> tuple[list[Move], Profile]:
    """Apply the worthwhile moves one after another and re-price the rest each time.

    This is where the 'a little bit clever' lives: a laptop that crosses the
    Pauschbetrag makes the home-office days worth something they weren't alone.
    Returns the moves in the order taken (refusals kept, unpriced) and the end state.
    """
    remaining = list(candidates)
    taken: list[Move] = []
    state = p
    while remaining:
        priced = moves_for(state, remaining)
        best = priced[0]
        if best.status != "worth":
            taken.extend(priced)          # nothing left that pays; keep the refusals visible
            break
        taken.append(best)
        state = apply(state, best.candidate)
        remaining.remove(best.candidate)
    return taken, state


# --- a November worth demoing -----------------------------------------------------

def november_profile() -> Profile:
    return Profile(gross=Decimal(58_000), stkl=1, werbungskosten=Decimal(410),
                   homeoffice_days=96, handwerker_labour=Decimal(400), spenden=Decimal(0),
                   today=date(2026, 11, 12), name="M. Hassan")


def november_table() -> list[Candidate]:
    return [
        Candidate("handwerker", "Elektriker — Sicherungskasten, Rechnung 2 900 EUR",
                  amount=Decimal(2900), labour=Decimal(2100), due=date(2027, 1, 15)),
        Candidate("werbungskosten", "Laptop für die Arbeit, 899 EUR", amount=Decimal(899)),
        Candidate("homeoffice", "Home-office days you haven't logged yet (Nov–Dec)", amount=Decimal(30)),
        Candidate("spende", "Spende an die Tafel, 250 EUR", amount=Decimal(250)),
        # the ones that must be refused, in the demo
        Candidate("handwerker", "Gärtner, 600 EUR bar bezahlt", amount=Decimal(600), labour=Decimal(600), cash=True),
        Candidate("werbungskosten", "ChatGPT tip: 'Materialkosten der Elektrik absetzen (§ 35b EStG)'",
                  amount=Decimal(800), citation="§ 35b EStG", claim="Materialkosten absetzbar"),
        Candidate("other", "Heiraten vor dem 31.12. — Ehegattensplitting", amount=Decimal(0)),
    ]


if __name__ == "__main__":  # pragma: no cover
    p = november_profile()
    pos = position(p)
    print(f"{p.name} · {p.today:%d.%m.%Y} · {pos.days_left} days to {p.deadline:%d.%m.%Y}")
    print(f"  withheld {pos.withheld:,.2f}  owed {pos.tax:,.2f}  -> refund today {pos.refund:,.2f} EUR")
    taken, end = plan(p, november_table())
    for m in taken:
        print(f"  [{m.status:<8}] {m.saving:>9,.2f} EUR  {m.candidate.label}")
        print(f"             {m.why}  ({m.citation}{'' if m.citation_ok else ' ✗'})")
    print(f"  position after the plan: {position(end).refund:,.2f} EUR")
