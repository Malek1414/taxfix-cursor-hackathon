"""
The validation harness. Whatever you build tomorrow, this prints the number.

The doctrine, in five parts — declare all five BEFORE you write the system:

    oracle      where truth comes from, and why it is independent of you
    cases       small and adversarial beats large and easy (15-40 is plenty)
    metric      one headline number a judge can hold
    pass_bar    declared up front, not chosen after seeing results
    failure     what wrong looks like, demoed live

And the asymmetry that matters in tax: over-escalating costs minutes, while a
silent wrong auto-decision gets filed with the Finanzamt and becomes a legal
problem. Those are never one accuracy score. `Suite` reports them separately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable


@dataclass
class Case:
    """One test case. `expected` is the oracle's answer, not yours."""

    name: str
    inputs: dict[str, Any]
    expected: Any
    tier: str = "normal"            # normal | adversarial
    material: bool = True           # does getting this wrong actually matter?
    note: str = ""


@dataclass
class Result:
    case: Case
    actual: Any
    ok: bool
    escalated: bool = False
    detail: str = ""

    @property
    def silent_error(self) -> bool:
        """Wrong, and it did not ask for a human. The one that must be zero."""
        return (not self.ok) and (not self.escalated)


@dataclass
class Suite:
    name: str
    oracle: str
    metric: str
    pass_bar: str
    failure_mode: str
    cases: list[Case] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)
    elapsed: float = 0.0

    # -- running ----------------------------------------------------------
    def run(
        self,
        system: Callable[[dict], Any],
        compare: Callable[[Any, Any], bool] | None = None,
        escalated: Callable[[Any], bool] | None = None,
    ) -> "Suite":
        cmp_fn = compare or (lambda a, b: a == b)
        esc_fn = escalated or (lambda out: bool(getattr(out, "escalate", False)))
        self.results.clear()
        t0 = time.time()
        for c in self.cases:
            try:
                out = system(c.inputs)
                ok = cmp_fn(out, c.expected)
                detail = ""
            except Exception as e:                       # a crash is a failure, not a skip
                out, ok, detail = None, False, f"{type(e).__name__}: {e}"
            self.results.append(Result(c, out, ok, esc_fn(out) if out is not None else False, detail))
        self.elapsed = time.time() - t0
        return self

    # -- the numbers ------------------------------------------------------
    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(r.ok for r in self.results)

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def silent_errors(self) -> list[Result]:
        return [r for r in self.results if r.silent_error and r.case.material]

    @property
    def over_escalations(self) -> list[Result]:
        return [r for r in self.results if r.ok and r.escalated]

    @property
    def adversarial(self) -> list[Result]:
        return [r for r in self.results if r.case.tier == "adversarial"]

    @property
    def adversarial_held(self) -> bool:
        return all(r.ok for r in self.adversarial)

    @property
    def clean(self) -> bool:
        """The headline claim: nothing wrong slipped through unflagged."""
        return not self.silent_errors and self.adversarial_held

    # -- reporting --------------------------------------------------------
    def report(self, verbose: bool = True) -> str:
        w = 74
        L = [
            "=" * w,
            f" {self.name}",
            "=" * w,
            f"  oracle       {self.oracle}",
            f"  metric       {self.metric}",
            f"  pass bar     {self.pass_bar}",
            f"  failure mode {self.failure_mode}",
            "-" * w,
        ]
        if verbose:
            for r in self.results:
                mark = "pass" if r.ok else ("ESC " if r.escalated else "FAIL")
                tier = "*" if r.case.tier == "adversarial" else " "
                line = f"  {mark}{tier} {r.case.name[:44]:<44}"
                if not r.ok:
                    line += f" got={_short(r.actual)} want={_short(r.case.expected)}"
                if r.detail:
                    line += f"  {r.detail[:40]}"
                L.append(line)
            L.append("-" * w)

        L += [
            f"  cases              {self.total}   ({len(self.adversarial)} adversarial)",
            f"  correct            {self.passed}/{self.total}  ({self.accuracy:.1%})",
            f"  SILENT ERRORS      {len(self.silent_errors)}   <- must be 0",
            f"  over-escalations   {len(self.over_escalations)}   (acceptable)",
            f"  adversarial held   {'yes' if self.adversarial_held else 'NO'}",
            f"  runtime            {self.elapsed*1000:.0f} ms",
            "=" * w,
            f"  VERDICT: {'PASS — ' + self.pass_bar if self.clean and self.accuracy >= 0.95 else 'NOT YET'}",
            "=" * w,
        ]
        return "\n".join(L)

    def headline(self) -> str:
        """The sentence you say on stage. Say a number, not an adjective."""
        return (
            f"{self.total} cases against {self.oracle}: "
            f"{self.accuracy:.0%} correct, {len(self.silent_errors)} silent errors, "
            f"{len(self.adversarial)}/{len(self.adversarial)} adversarial cases held."
            if self.adversarial_held else
            f"{self.total} cases: {self.accuracy:.0%} correct, "
            f"{len(self.silent_errors)} silent errors, adversarial NOT held."
        )


def _short(v: Any, n: int = 22) -> str:
    s = str(v)
    return s if len(s) <= n else s[: n - 1] + "…"


def approx(tol: str | Decimal = "0.005") -> Callable[[Any, Any], bool]:
    """Money comparator. Default tolerance is half a cent — i.e. cent-exact."""
    t = Decimal(str(tol))

    def _cmp(a: Any, b: Any) -> bool:
        try:
            return abs(Decimal(str(a)) - Decimal(str(b))) <= t
        except Exception:
            return a == b

    return _cmp


if __name__ == "__main__":  # pragma: no cover
    # Worked example: the PAP engine is its own best demo of the harness.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from core.pap.engine import lohnsteuer

    s = Suite(
        name="PAP tariff — monotonicity and allowance boundary",
        oracle="BMF Programmablaufplan 2026 (federal algorithm)",
        metric="cent-exact tax, and zero tax at/below the Grundfreibetrag",
        pass_bar="100% correct, 0 silent errors",
        failure_mode="float drift producing sub-cent deviation",
        cases=[
            Case("below allowance -> 0", {"g": 12_347}, Decimal(0)),
            Case("at allowance -> 0", {"g": 12_348}, Decimal(0)),
            Case("StKl 6 taxes small wage", {"g": 10_000, "s": 6}, None, note="just needs > 0"),
        ],
    )
    s.cases[2].expected = lohnsteuer(10_000, stkl=6)["LSTLZZ"]
    s.run(lambda i: lohnsteuer(i["g"], stkl=i.get("s", 1))["LSTLZZ"], compare=approx())
    print(s.report())
    print("\n  say on stage:", s.headline())
