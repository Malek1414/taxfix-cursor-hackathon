"""Configuration: .env loader (stdlib), model tiers, prices."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".orchestra"          # cache + audit, gitignored

TIERS = ("small", "medium", "large")


def load_env(path: Path = ROOT / ".env") -> int:
    """Read KEY=VALUE lines into os.environ without overriding existing values. Returns count loaded."""
    if not path.exists():
        return 0
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            n += 1
    return n


# USD per million tokens (input, output).
# Anthropic rows: Claude API pricing table as cached in the claude-api skill on 2026-06-24.
# Everything else must be filled from the provider's pricing page; unknown models are priced 0 and flagged.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-fable-5-1": (10.00, 50.00),
    "mock-small": (1.00, 5.00),
    "mock-medium": (2.00, 10.00),
    "mock-large": (5.00, 25.00),
}
CACHE_READ_FACTOR = 0.10    # provider prompt cache: read ≈ 0.1× input price (Anthropic; Fable 5.1 is 0.025×)
CACHE_WRITE_FACTOR = 1.25   # provider prompt cache: write ≈ 1.25× input price (5-minute TTL)

DEFAULT_MODELS = {
    "mock": {"small": "mock-small", "medium": "mock-medium", "large": "mock-large"},
    "anthropic": {"small": "claude-haiku-4-5", "medium": "claude-sonnet-5", "large": "claude-opus-5"},
    "claude_code": {"small": "claude-haiku-4-5", "medium": "claude-sonnet-5", "large": "claude-opus-5"},
    "openai": {"small": "", "medium": "", "large": ""},   # set ORCHESTRA_SMALL/MEDIUM/LARGE explicitly
}


@dataclass(frozen=True)
class ModelSpec:
    tier: str
    name: str
    provider: str
    input_usd: float      # per million tokens
    output_usd: float

    @property
    def priced(self) -> bool:
        return self.input_usd > 0 or self.output_usd > 0


def price_of(model: str) -> tuple[float, float]:
    """Price from the table, or ORCHESTRA_PRICE_<MODEL>="in,out" in the environment, else (0, 0)."""
    if model in PRICES:
        return PRICES[model]
    env = os.environ.get("ORCHESTRA_PRICE_" + model.upper().replace("-", "_").replace(".", "_"), "")
    if "," in env:
        i, o = env.split(",", 1)
        return float(i), float(o)
    return (0.0, 0.0)


def mock_models() -> dict[str, ModelSpec]:
    """The offline tiers, independent of .env. Used by tests and the offline demo."""
    return {t: ModelSpec(t, n, "mock", *price_of(n)) for t, n in DEFAULT_MODELS["mock"].items()}


def baseline_tier() -> str:
    """Which tier the ledger's counterfactual runs on. Default medium: what a normal team would use everywhere."""
    tier = os.environ.get("ORCHESTRA_BASELINE", "medium")
    if tier not in TIERS:
        raise ValueError(f"ORCHESTRA_BASELINE must be one of {TIERS}, got '{tier}'")
    return tier


def tier_models(provider: str | None = None) -> dict[str, ModelSpec]:
    """The three tiers for the configured provider. ORCHESTRA_PROVIDER=mock|anthropic|openai."""
    provider = provider or os.environ.get("ORCHESTRA_PROVIDER", "mock")
    defaults = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openai"])
    out: dict[str, ModelSpec] = {}
    for tier in TIERS:
        name = os.environ.get("ORCHESTRA_" + tier.upper(), defaults[tier])
        if not name:
            raise ValueError(f"no model for tier '{tier}': set ORCHESTRA_{tier.upper()} in .env")
        i, o = price_of(name)
        out[tier] = ModelSpec(tier, name, provider, i, o)
    return out
