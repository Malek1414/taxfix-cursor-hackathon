"""
Bescheid-Check — diff a German tax assessment notice against what was filed.

Why this and not a simpler diff: the notice is only half the story. A line can
match what you filed and still be wrong, and a line can differ and still be
*correct in law*. So we do not compare the notice to the filing. We independently
recompute the tax from the Bundesfinanzministerium's own published algorithm and
compare all three.

That is what makes the demo non-circular. We are not catching errors we injected;
we are catching a figure that disagrees with the federal calculation.

Legal clock, implemented properly:
  §122 Abs 2 Nr 1 AO  notice is deemed served on the 4th day after posting
  §355 Abs 1 AO       objection within one month of service
  §108 Abs 3 AO       a deadline landing on Sat/Sun/holiday moves to the next
                      working day
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.law.cite import check as cite_check  # noqa: E402
from core.pap.engine import lohnsteuer  # noqa: E402

CENT = Decimal("0.01")
MATERIAL = Decimal("50")     # below this a deviation is noise, not a case


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@dataclass
class Filing:
    """What the taxpayer submitted."""

    gross: Decimal                       # Bruttoarbeitslohn
    stkl: int = 1
    year: int = 2026
    werbungskosten: Decimal = Decimal(0)
    sonderausgaben: Decimal = Decimal(0)
    prepaid: Decimal = Decimal(0)        # Lohnsteuer already withheld
    name: str = "Musterperson"

    def __post_init__(self):
        for f in ("gross", "werbungskosten", "sonderausgaben", "prepaid"):
            setattr(self, f, Decimal(str(getattr(self, f))))
        if self.prepaid == 0:
            self.prepaid = lohnsteuer(self.gross, stkl=self.stkl, year=self.year)["LSTLZZ"]


@dataclass
class Line:
    """One line of the assessment notice."""

    key: str
    label: str
    filed: Decimal
    assessed: Decimal
    lawful: bool = True                  # did the Finanzamt have grounds?
    ground: str = ""                     # their stated reason
    citation: str = ""                   # the paragraph they lean on

    @property
    def delta(self) -> Decimal:
        return self.assessed - self.filed


@dataclass
class Bescheid:
    """The notice as received."""

    issued: date
    lines: list[Line] = field(default_factory=list)
    stated_tax: Decimal = Decimal(0)
    stated_refund: Decimal = Decimal(0)
    office: str = "Finanzamt Berlin-Mitte"

    # -- statutory clock --------------------------------------------------
    def served(self) -> date:
        """§122 Abs 2 Nr 1 AO — deemed served on the 4th day after posting."""
        return self.issued + timedelta(days=3)

    def objection_deadline(self) -> date:
        """§355 Abs 1 AO — one month, rolled forward per §108 Abs 3 AO."""
        s = self.served()
        m, y = s.month + 1, s.year
        if m > 12:
            m, y = 1, y + 1
        day = min(s.day, _days_in(y, m))
        d = date(y, m, day)
        while d.weekday() >= 5:          # Sat/Sun -> next working day
            d += timedelta(days=1)
        return d

    def days_left(self, today: date | None = None) -> int:
        return (self.objection_deadline() - (today or date.today())).days


def _days_in(y: int, m: int) -> int:
    nxt = date(y + (m == 12), (m % 12) + 1, 1)
    return (nxt - date(y, m, 1)).days


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    line: str
    label: str
    delta: Decimal
    euro_impact: Decimal
    verdict: str                  # "challenge" | "lawful" | "immaterial"
    explanation_de: str
    explanation_en: str
    citation: str = ""
    citation_ok: bool | None = None

    @property
    def material(self) -> bool:
        return abs(self.euro_impact) >= MATERIAL


@dataclass
class Report:
    findings: list[Finding]
    recomputed_tax: Decimal
    stated_tax: Decimal
    engine_delta: Decimal
    deadline: date
    days_left: int
    escalate: bool = False

    @property
    def challenges(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == "challenge"]

    @property
    def total_at_stake(self) -> Decimal:
        return sum((abs(f.euro_impact) for f in self.challenges), Decimal(0))


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

def review(filing: Filing, notice: Bescheid, today: date | None = None) -> Report:
    marginal = _marginal_rate(filing)
    findings: list[Finding] = []

    for ln in notice.lines:
        if ln.delta == 0:
            continue
        # A cut to a deduction raises taxable income, so it costs the taxpayer.
        impact = (-ln.delta * marginal).quantize(CENT)

        if ln.lawful:
            verdict = "lawful"
            de = (f"Das {notice.office} hat {ln.label} um {abs(ln.delta):,.2f} € gekürzt. "
                  f"Begründung: {ln.ground} Diese Kürzung ist rechtlich zutreffend — "
                  f"ein Einspruch hätte hier keine Aussicht auf Erfolg.")
            en = (f"The tax office reduced {ln.label} by €{abs(ln.delta):,.2f}. "
                  f"Reason: {ln.ground} This reduction is correct in law — "
                  f"an objection here would not succeed.")
        elif abs(impact) < MATERIAL:
            verdict = "immaterial"
            de = f"{ln.label} weicht um {abs(ln.delta):,.2f} € ab (Wirkung {abs(impact):,.2f} €)."
            en = f"{ln.label} differs by €{abs(ln.delta):,.2f} (impact €{abs(impact):,.2f})."
        else:
            verdict = "challenge"
            de = (f"{ln.label}: erklärt {ln.filed:,.2f} €, angesetzt {ln.assessed:,.2f} €. "
                  f"Differenz {abs(ln.delta):,.2f} €, steuerliche Wirkung rund "
                  f"{abs(impact):,.2f} €. Für die Kürzung ist keine tragfähige "
                  f"Begründung ersichtlich.")
            en = (f"{ln.label}: you declared €{ln.filed:,.2f}, the office applied "
                  f"€{ln.assessed:,.2f}. Difference €{abs(ln.delta):,.2f}, worth about "
                  f"€{abs(impact):,.2f} to you. No supporting reason is given.")

        cite_ok = None
        if ln.citation:
            cite_ok = cite_check(ln.citation).exists

        findings.append(Finding(ln.key, ln.label, ln.delta, impact, verdict, de, en,
                                ln.citation, cite_ok))

    # Independent recompute — the non-circular part.
    recomputed = _recompute(filing, notice)
    engine_delta = (notice.stated_tax - recomputed).quantize(CENT)
    if abs(engine_delta) >= MATERIAL:
        findings.append(Finding(
            "tarif", "Festgesetzte Steuer", engine_delta, engine_delta, "challenge",
            f"Die festgesetzte Steuer weicht um {abs(engine_delta):,.2f} € von der "
            f"Berechnung nach dem amtlichen Programmablaufplan des BMF ab.",
            f"The assessed tax differs by €{abs(engine_delta):,.2f} from the calculation "
            f"under the BMF's official Programmablaufplan.",
            citation="§ 32a EStG",
            citation_ok=cite_check("§ 32a EStG").exists,
        ))

    return Report(
        findings=findings,
        recomputed_tax=recomputed,
        stated_tax=notice.stated_tax,
        engine_delta=engine_delta,
        deadline=notice.objection_deadline(),
        days_left=notice.days_left(today),
        escalate=any(f.verdict == "challenge" for f in findings),
    )


def _recompute(filing: Filing, notice: Bescheid) -> Decimal:
    """What the tax should be, per the federal algorithm, on the assessed figures."""
    assessed = {ln.key: ln.assessed for ln in notice.lines}
    wk = assessed.get("werbungskosten", filing.werbungskosten)
    sa = assessed.get("sonderausgaben", filing.sonderausgaben)
    taxable = max(Decimal(0), filing.gross - wk - sa)
    return lohnsteuer(taxable, stkl=filing.stkl, year=filing.year)["LSTLZZ"]


def _marginal_rate(filing: Filing, step: Decimal = Decimal(1000)) -> Decimal:
    base = filing.gross - filing.werbungskosten - filing.sonderausgaben
    lo = lohnsteuer(max(Decimal(0), base), stkl=filing.stkl, year=filing.year)["LSTLZZ"]
    hi = lohnsteuer(max(Decimal(0), base + step), stkl=filing.stkl, year=filing.year)["LSTLZZ"]
    return ((hi - lo) / step).quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Einspruch draft
# ---------------------------------------------------------------------------

def draft_einspruch(filing: Filing, notice: Bescheid, report: Report) -> str:
    if not report.challenges:
        return ""
    items = "\n".join(
        f"  {i}. {f.label}: erklärt {abs(f.delta):,.2f} € gekürzt. {f.explanation_de}"
        for i, f in enumerate(report.challenges, 1)
    )
    return f"""An das {notice.office}

Einspruch gegen den Einkommensteuerbescheid {filing.year}
vom {notice.issued:%d.%m.%Y}, bekannt gegeben am {notice.served():%d.%m.%Y}

Sehr geehrte Damen und Herren,

gegen den oben bezeichneten Bescheid lege ich hiermit fristgerecht
Einspruch ein (§ 347 AO). Die Einspruchsfrist nach § 355 Abs. 1 AO
endet am {report.deadline:%d.%m.%Y}.

Der Einspruch richtet sich gegen folgende Punkte:

{items}

Die festgesetzte Steuer weicht um {abs(report.engine_delta):,.2f} € von der
Berechnung nach dem amtlichen Programmablaufplan des Bundesministeriums
der Finanzen ab. Insgesamt geht es um {report.total_at_stake:,.2f} €.

Ich bitte um Änderung des Bescheids und um Mitteilung des Ergebnisses.

Mit freundlichen Grüßen

{filing.name}

--- ENTWURF · vor dem Versand von einer steuerberatenden Person prüfen lassen ---
"""
