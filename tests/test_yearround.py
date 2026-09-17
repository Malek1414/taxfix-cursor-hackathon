"""Properties that must hold whatever the profile, plus the declared pass bar."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build.yearround.moves import (  # noqa: E402
    HANDWERKER_CAP, HAUSHALT_CAP, Candidate, Profile, apply, november_profile, november_table,
    plan, position, price, tax,
)
from build.yearround.demo import validate  # noqa: E402

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(f"  {'ok ' if cond else 'FAIL'}  {name}")


def main() -> int:
    print("properties")
    # 1. more Werbungskosten never raises tax (monotonic), over a grid of incomes
    mono = True
    for gross in (12_000, 30_000, 58_000, 90_000, 150_000):
        last = None
        for wk in range(0, 6001, 250):
            t = tax(Profile(gross=Decimal(gross), werbungskosten=Decimal(wk)))
            if last is not None and t > last:
                mono = False
            last = t
    check("tax is non-increasing in Werbungskosten", mono)

    # 2. § 35a credits never exceed their caps, and tax never goes below 0
    p = Profile(gross=Decimal(58_000), handwerker_labour=Decimal(50_000), haushalt_labour=Decimal(90_000))
    check("§ 35a credit capped at 1 200 + 4 000", p.credit_35a == HANDWERKER_CAP + HAUSHALT_CAP)
    check("tax never negative", tax(Profile(gross=Decimal(9_000), handwerker_labour=Decimal(50_000))) == 0)

    # 3. refund never negative for an employee on today's facts
    check("refund ≥ 0", all(position(Profile(gross=Decimal(g))).refund >= 0 for g in (10_000, 58_000, 200_000)))

    # 4. a priced saving is exactly before − after, and pricing is idempotent
    pr, c = november_profile(), Candidate("werbungskosten", "laptop", Decimal(899))
    m1, m2 = price(pr, c), price(pr, c)
    check("saving == before − after", m1.saving == m1.before - m1.after)
    check("pricing is deterministic", (m1.saving, m1.status, m1.why) == (m2.saving, m2.status, m2.why))

    # 5. the plan's total equals the change in position, to the cent
    taken, end = plan(pr, november_table())
    total = sum((m.saving for m in taken if m.status == "worth"), Decimal(0))
    check("plan total == position delta", total == position(end).refund - position(pr).refund)

    # 6. nothing with a failed citation is ever shown
    check("failed citation never shown", not any(m.shown for m in taken if not m.citation_ok))

    # 7. sequence-awareness: home-office days alone are 0, after the laptop they are > 0
    ho = Candidate("homeoffice", "days", Decimal(30))
    alone = price(pr, ho)
    later = price(apply(pr, Candidate("werbungskosten", "laptop", Decimal(899))), ho)
    check("moves interact: 0 alone, > 0 after crossing the Pauschbetrag", alone.saving == 0 and later.saving > 0)

    print("\nsuite — pass bar declared in demo.py")
    s = validate()
    print("  " + s.headline())
    check("100 % of euro figures exact", s.accuracy == 1.0 if not callable(s.accuracy) else s.accuracy() == 1.0)
    check("0 silent errors", len(s.silent_errors() if callable(s.silent_errors) else s.silent_errors) == 0)
    check("all adversarial held", s.adversarial_held() if callable(s.adversarial_held) else s.adversarial_held)

    failed = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
