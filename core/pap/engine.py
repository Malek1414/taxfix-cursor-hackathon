"""
Executes the BMF Programmablaufplan (PAP) — the German federal wage-tax algorithm.

The Bundesfinanzministerium publishes the PAP as XML pseudocode precisely so third
parties can reproduce the official calculation. Their words: the graphical DIN 66001
form "does not always translate without problems", and "the rules on decimal places
often leave room for different interpretations, which can ultimately lead to
incorrect results". So they ship this, and they tell you to use BigDecimal.

We honour that: every monetary value here is a decimal.Decimal, never a float.
Floats are the one thing that will silently break a cent-exact claim.

Source: https://www.bmf-steuerrechner.de/interface/pseudocodes.xhtml
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 50

DATA = Path(__file__).resolve().parents[2] / "data" / "truth"


class BD:
    """A BigDecimal work-alike: same method names, same scale semantics.

    Wrapping rather than transpiling means the PAP's Java expressions evaluate
    as Python source almost verbatim, which keeps the translation auditable —
    you can diff our expression strings against the BMF XML line by line.
    """

    __slots__ = ("v",)

    def __init__(self, v: Any = 0):
        self.v = v if isinstance(v, Decimal) else Decimal(str(v))

    # -- arithmetic -------------------------------------------------------
    def add(self, o: "BD") -> "BD":
        return BD(self.v + _d(o))

    def subtract(self, o: "BD") -> "BD":
        return BD(self.v - _d(o))

    def multiply(self, o: "BD") -> "BD":
        return BD(self.v * _d(o))

    def divide(self, o: "BD", scale: int | None = None, rounding: str | None = None) -> "BD":
        q = self.v / _d(o)
        if scale is None:
            return BD(q)
        return BD(_quantize(q, scale, rounding))

    def setScale(self, scale: int, rounding: str | None = None) -> "BD":
        return BD(_quantize(self.v, scale, rounding))

    # -- comparison -------------------------------------------------------
    def compareTo(self, o: "BD") -> int:
        a, b = self.v, _d(o)
        return -1 if a < b else (1 if a > b else 0)

    def longValue(self) -> int:
        return int(self.v.to_integral_value(rounding=ROUND_DOWN))

    def intValue(self) -> int:
        return self.longValue()

    def doubleValue(self) -> float:
        return float(self.v)

    def __repr__(self) -> str:
        return f"BD({self.v})"


def _d(o: Any) -> Decimal:
    if isinstance(o, BD):
        return o.v
    if isinstance(o, Decimal):
        return o
    return Decimal(str(o))


def _quantize(v: Decimal, scale: int, rounding: str | None) -> Decimal:
    mode = ROUND_UP if rounding == "ROUND_UP" else ROUND_DOWN
    # BigDecimal ROUND_UP/DOWN are away-from-zero / toward-zero, same as Decimal's.
    return v.quantize(Decimal(1).scaleb(-scale), rounding=mode)


class _BigDecimalNS:
    """Stands in for the java.math.BigDecimal class object."""

    ZERO = BD(0)
    ONE = BD(1)
    TEN = BD(10)
    ROUND_DOWN = "ROUND_DOWN"
    ROUND_UP = "ROUND_UP"

    @staticmethod
    def valueOf(x: Any) -> BD:
        return BD(x)


# ---------------------------------------------------------------------------
# Java expression -> Python source
# ---------------------------------------------------------------------------

def _to_py(expr: str) -> str:
    """The PAP dialect is small and closed. These are the only differences."""
    s = expr
    s = re.sub(r"\bBigDecimal\.ROUND_(DOWN|UP)\b", r"'ROUND_\1'", s)
    s = re.sub(r"\bnew\s+BigDecimal\s*\(", "BD(", s)  # 2025 PAP uses constructor form
    s = s.replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"!\s*=", "__NE__", s)          # protect !=
    s = re.sub(r"!(?=\s*[\w(])", " not ", s)   # Java logical not
    s = s.replace("__NE__", "!=")
    s = s.replace("true", "True").replace("false", "False")
    return s


class PAP:
    """Loads one year's Programmablaufplan and executes it."""

    def __init__(self, year: int = 2026, path: str | Path | None = None):
        self.year = year
        p = Path(path) if path else DATA / f"Lohnsteuer{year}-PAP.xml"
        if not p.exists():
            raise FileNotFoundError(
                f"PAP for {year} not found at {p}. "
                f"Fetch it from bmf-steuerrechner.de (see scripts/fetch_data.sh)."
            )
        self.root = ET.parse(p).getroot()
        self.name = self.root.get("name", f"Lohnsteuer{year}")

        self.inputs = {i.get("name"): i for i in self.root.iter("INPUT")}
        self.outputs = {o.get("name"): o for o in self.root.iter("OUTPUT")}
        self.internals = {n.get("name"): n for n in self.root.iter("INTERNAL")}
        self.methods = {m.get("name"): m for m in self.root.iter("METHOD")}
        self.main = self.root.find("./METHODS/MAIN")

        self._compiled: dict[str, Any] = {}

    # -- environment ------------------------------------------------------
    def _defaults(self) -> dict[str, Any]:
        env: dict[str, Any] = {"BigDecimal": _BigDecimalNS, "BD": BD}

        for c in self.root.iter("CONSTANT"):
            env[c.get("name")] = self._eval(c.get("value"), env, array=c.get("type", "").endswith("[]"))

        for group in (self.internals, self.outputs, self.inputs):
            for name, node in group.items():
                env[name] = self._default_for(node, env)
        return env

    def _default_for(self, node: ET.Element, env: dict) -> Any:
        raw, typ = node.get("default"), node.get("type", "BigDecimal")
        if raw in (None, "None", ""):
            return 0 if typ in ("int", "double") else BD(0)
        if typ == "int":
            return int(raw)
        if typ == "double":
            return float(raw)
        return self._eval(raw, env)

    def _eval(self, expr: str, env: dict, array: bool = False) -> Any:
        src = _to_py(expr).strip()
        if array:
            src = "[" + src.strip("{}").strip() + "]"
        key = (src, array)
        code = self._compiled.get(key)
        if code is None:
            code = compile(src, "<pap>", "eval")
            self._compiled[key] = code
        return eval(code, {"__builtins__": {}}, env)  # noqa: S307 - closed grammar, no user input

    def _exec(self, expr: str, env: dict) -> None:
        src = _to_py(expr).strip()
        code = self._compiled.get((src, "x"))
        if code is None:
            code = compile(src, "<pap>", "exec")
            self._compiled[(src, "x")] = code
        exec(code, {"__builtins__": {}}, env)  # noqa: S102 - closed grammar, no user input

    # -- interpreter ------------------------------------------------------
    def _run_block(self, node: ET.Element, env: dict) -> None:
        for child in node:
            tag = child.tag
            if tag == "EVAL":
                self._exec(child.get("exec"), env)
            elif tag == "EXECUTE":
                self._run_block(self.methods[child.get("method")], env)
            elif tag == "IF":
                branch = "THEN" if self._eval(child.get("expr"), env) else "ELSE"
                sub = child.find(branch)
                if sub is not None:
                    self._run_block(sub, env)
            elif tag in ("THEN", "ELSE", "METHOD", "MAIN"):
                self._run_block(child, env)

    # -- public API -------------------------------------------------------
    def calculate(self, **kwargs) -> dict[str, Any]:
        """Run the official calculation.

        All amounts are in cents, exactly as the BMF interface expects
        (RE4=6000000 means a gross annual wage of 60,000.00 EUR).
        """
        env = self._defaults()
        for k, v in kwargs.items():
            if k not in self.inputs:
                raise KeyError(
                    f"{k!r} is not a PAP input. Valid: {', '.join(sorted(self.inputs))}"
                )
            typ = self.inputs[k].get("type")
            env[k] = int(v) if typ == "int" else (float(v) if typ == "double" else BD(v))

        self._run_block(self.main, env)
        return {name: env[name] for name in self.outputs}

    def euros(self, **kwargs) -> dict[str, Decimal]:
        """Same as calculate(), but every output converted to euros."""
        out = self.calculate(**kwargs)
        return {
            k: (v.v / 100 if isinstance(v, BD) else Decimal(v) / 100)
            for k, v in out.items()
        }


# ---------------------------------------------------------------------------
# Convenience: the common case
# ---------------------------------------------------------------------------

LZZ_YEAR, LZZ_MONTH, LZZ_WEEK, LZZ_DAY = 1, 2, 3, 4


def lohnsteuer(
    gross_eur: float | Decimal | str,
    stkl: int = 1,
    year: int = 2026,
    kvz: float | Decimal | str = "1.70",
    period: int = LZZ_YEAR,
    **extra,
) -> dict[str, Decimal]:
    """Annual wage tax for a gross wage, in euros.

    gross_eur : gross wage for the period
    stkl      : Steuerklasse, 1-6
    kvz       : employee health-insurance surcharge, in percent
    period    : LZZ_YEAR / LZZ_MONTH / LZZ_WEEK / LZZ_DAY
    """
    pap = PAP(year)
    cents = (Decimal(str(gross_eur)) * 100).quantize(Decimal(1), rounding=ROUND_DOWN)
    return pap.euros(RE4=cents, STKL=stkl, LZZ=period, KVZ=Decimal(str(kvz)), **extra)


if __name__ == "__main__":  # pragma: no cover
    import sys

    gross = float(sys.argv[1]) if len(sys.argv) > 1 else 60000
    stkl = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    r = lohnsteuer(gross, stkl)
    print(f"PAP {2026} · gross {gross:,.2f} EUR · Steuerklasse {stkl}")
    for k in ("LSTLZZ", "SOLZLZZ", "BK"):
        if k in r:
            print(f"  {k:<9} {r[k]:>12,.2f} EUR")
