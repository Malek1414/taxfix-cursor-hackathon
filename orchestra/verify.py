"""Bridge to the validation harness in spine/core/harness (Malek's doctrine: oracle → cases → metric →
pass bar → failure mode). If the spine is not checked out, a minimal stand-in with the same API is used,
so the orchestra still prints a number. Never invent that number: if the suite has not run, say so.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Two layouts: the spine sits in spine/ here, and at the repo root in Malek's own
# repo, where core/harness is a top level package. Take whichever one carries it.
SPINE = next((c for c in (ROOT / "spine", ROOT) if (c / "core" / "harness").is_dir()),
             ROOT / "spine")


def _load_spine():
    if SPINE.exists() and str(SPINE) not in sys.path:
        sys.path.insert(0, str(SPINE))
    try:
        from core.harness.harness import Case, Suite, approx   # type: ignore
        return Case, Suite, approx, True
    except ImportError:
        return None, None, None, False


Case, Suite, approx, HAS_SPINE = _load_spine()

if not HAS_SPINE:   # pragma: no cover - only when spine/ is missing
    from dataclasses import dataclass, field
    from typing import Any, Callable

    @dataclass
    class Case:  # type: ignore[no-redef]
        name: str
        inputs: dict
        expected: Any
        tier: str = "normal"
        material: bool = True
        note: str = ""

    @dataclass
    class Suite:  # type: ignore[no-redef]
        name: str
        oracle: str
        metric: str
        pass_bar: str
        failure_mode: str
        cases: list = field(default_factory=list)
        results: list = field(default_factory=list)

        def run(self, system: Callable, compare=None, escalated=None):
            cmp = compare or (lambda a, b: a == b)
            esc = escalated or (lambda out: False)
            self.results = []
            for c in self.cases:
                try:
                    out = system(c.inputs)
                    self.results.append((c, out, cmp(out, c.expected), esc(out)))
                except Exception as e:
                    print(f"harness: case {c.name} crashed: {type(e).__name__}: {e}", file=sys.stderr)
                    self.results.append((c, None, False, False))
            return self

        @property
        def accuracy(self):
            return sum(ok for _, _, ok, _ in self.results) / len(self.results) if self.results else 0.0

        @property
        def silent_errors(self):
            return [r for r in self.results if not r[2] and not r[3] and r[0].material]

        @property
        def adversarial_held(self):
            return all(ok for c, _, ok, _ in self.results if c.tier == "adversarial")

        @property
        def clean(self):
            return not self.silent_errors and self.adversarial_held

        @property
        def verdict(self):
            if not self.results:
                return "NOT MEASURED — this dataset declares no expectations"
            return "PASS" if self.clean and self.accuracy >= 0.95 else "NOT YET"

        def report(self, verbose=True):
            if not self.results:
                return f"{self.name}: no declared expectations, correctness not measured"
            return (f"{self.name}: {self.accuracy:.0%} on {len(self.results)} cases, "
                    f"{len(self.silent_errors)} silent errors (stand-in harness, spine/ missing)")

        def headline(self):
            return self.report()

    def approx(tol="0.005"):  # type: ignore[no-redef]
        return lambda a, b: a == b


def spine_tools() -> dict:
    """Real oracles from the spine, if present: the BMF wage-tax algorithm and the statute resolver."""
    tools: dict = {}
    if not HAS_SPINE:
        return tools
    try:
        from core.pap.engine import lohnsteuer   # type: ignore

        def calc_tax(gross: float, stkl: int = 1) -> dict:
            from decimal import Decimal
            r = lohnsteuer(gross, stkl=int(stkl))
            cents = Decimal("0.01")
            return {"gross": gross, "stkl": int(stkl), "lohnsteuer_eur": str(r["LSTLZZ"].quantize(cents)),
                    "soli_eur": str(r["SOLZLZZ"].quantize(cents)), "source": "BMF Programmablaufplan 2026"}
        tools["calc.tax"] = calc_tax
    except Exception as e:
        print(f"orchestra.verify: calc.tax unavailable ({type(e).__name__}: {e})", file=sys.stderr)
    try:
        from core.law.cite import find_citations, resolve   # type: ignore

        def cite_check(text: str) -> dict:
            found = find_citations(text)
            return {"citations": [{"cite": c, "resolves": resolve(c) is not None} for c in found]}
        tools["law.cite"] = cite_check
    except Exception as e:
        print(f"orchestra.verify: law.cite unavailable ({type(e).__name__}: {e})", file=sys.stderr)
    return tools
