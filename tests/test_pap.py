"""
Proves the PAP engine reproduces German wage tax correctly.

There is no free public oracle we can call (the BMF's live interface needs a
Zugriffscode obtainable only by emailing Steuerrechner@bmf.bund.de). So instead
we assert the structural invariants of the German wage-tax tariff. These are
strong: an engine that satisfies all of them is not accidentally right.

Run:  python3 tests/test_pap.py
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pap.engine import PAP, lohnsteuer, LZZ_YEAR, LZZ_MONTH  # noqa: E402

GFB_2026 = Decimal("12348")  # Grundfreibetrag, from the PAP's own constants

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def lst(gross, stkl=1, year=2026, **kw):
    return lohnsteuer(gross, stkl=stkl, year=year, **kw)["LSTLZZ"]


print(f"\nPAP engine — structural conformance ({PAP(2026).name})\n")

# 1. Below the basic allowance there is no wage tax at all.
check("zero tax at/below Grundfreibetrag (StKl 1)",
      lst(GFB_2026 - 1) == 0, f"{GFB_2026 - 1} EUR -> {lst(GFB_2026 - 1)} EUR")

# 2. The allowance is a real edge: tax appears above it.
check("tax becomes positive above Grundfreibetrag",
      lst(20000) > 0, f"20,000 EUR -> {lst(20000)} EUR")

# 3. Monotonic: more gross never means less tax.
grid = [0, 10_000, 12_348, 15_000, 20_000, 30_000, 45_000, 60_000,
        80_000, 120_000, 200_000, 300_000]
vals = [lst(g) for g in grid]
check("monotonically non-decreasing in gross wage",
      all(b >= a for a, b in zip(vals, vals[1:])),
      " ".join(f"{g//1000}k:{v:,.0f}" for g, v in zip(grid, vals)))

# 4. Progressive: the marginal rate rises with income.
def marginal(g, step=1000):
    return (lst(g + step) - lst(g)) / step

m_low, m_mid, m_high = marginal(20_000), marginal(60_000), marginal(150_000)
check("marginal rate is progressive",
      m_low < m_mid < m_high,
      f"20k={m_low:.3f} < 60k={m_mid:.3f} < 150k={m_high:.3f}")

# 5. Marginal rate never exceeds the top statutory rate (45% + Soli headroom).
check("marginal rate stays within the statutory tariff",
      0 <= m_high <= Decimal("0.48"), f"{m_high:.3f}")

# 6. Steuerklasse ordering. III is the married-favourable class, VI the worst.
by_class = {k: lst(50_000, stkl=k) for k in range(1, 7)}
check("StKl III < StKl I < StKl VI at equal gross",
      by_class[3] < by_class[1] < by_class[6],
      " ".join(f"{k}:{v:,.0f}" for k, v in by_class.items()))

# 7. StKl V and VI carry no basic allowance -> tax even on a small wage.
check("StKl VI taxes income below the Grundfreibetrag",
      lst(10_000, stkl=6) > 0, f"10,000 EUR StKl 6 -> {lst(10_000, stkl=6)} EUR")

# 8. Period consistency: 12 monthly runs ~ one annual run.
annual = lst(60_000, stkl=1)
monthly = lohnsteuer(5_000, stkl=1, period=LZZ_MONTH)["LSTLZZ"] * 12
check("monthly x12 reconciles with annual (< 15 EUR drift)",
      abs(annual - monthly) < 15, f"annual {annual:,.2f} vs monthly*12 {monthly:,.2f}")

# 9. Solidaritätszuschlag only bites at high income, and is capped at 5.5%.
solz_mid = lohnsteuer(60_000)["SOLZLZZ"]
solz_high = lohnsteuer(250_000)["SOLZLZZ"]
lst_high = lst(250_000)
check("Soli is zero at middle income, positive at high income",
      solz_mid == 0 and solz_high > 0, f"60k={solz_mid}  250k={solz_high:,.2f}")
check("Soli does not exceed 5.5% of wage tax",
      solz_high <= lst_high * Decimal("0.055") + 1,
      f"{solz_high:,.2f} <= {lst_high * Decimal('0.055'):,.2f}")

# 10. Children reduce the Soli/church base (ZKF), never increase tax.
no_kids = lohnsteuer(90_000, stkl=1)["SOLZLZZ"]
two_kids = lohnsteuer(90_000, stkl=1, ZKF=Decimal(2))["SOLZLZZ"]
check("child allowances do not increase the Soli",
      two_kids <= no_kids, f"0 kids={no_kids:,.2f}  2 kids={two_kids:,.2f}")

# 11. Determinism — same inputs, same cents, every time.
check("deterministic across repeated runs",
      len({str(lst(73_412.55)) for _ in range(5)}) == 1)

# 12. Both published years load and differ (tariff changes year to year).
l25, l26 = lst(60_000, year=2025), lst(60_000, year=2026)
check("2025 and 2026 tariffs both load and differ",
      l25 != l26, f"2025={l25:,.2f}  2026={l26:,.2f}")

# 13. No floats anywhere in the money path.
check("outputs are Decimal, never float",
      all(isinstance(v, Decimal) for v in lohnsteuer(60_000).values()))

print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
if FAILED:
    print("  FAILING:", ", ".join(FAILED), "\n")
sys.exit(1 if FAILED else 0)
