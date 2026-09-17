"""VERIFIER: the maker-checker step. Small model, one tool, one job: does the answer hold up?
Separate from the specialist on purpose: an agent should not grade its own work."""

from ..agent import Agent
from ..permissions import Identity
from ..router import RoutePolicy

IDENTITY = Identity(
    name="verifier",
    role="check citations, numbers and tone before anything leaves",
    owner="sami",
    tools=frozenset({"law.cite", "calc.tax"}),   # it must be able to recompute, not just believe
    data_classes=frozenset({"customer"}),
    needs_approval=frozenset(),
    budget_usd=0.10,
    max_steps=3,
)

# FILL TOMORROW: the checklist the brief needs (schema, tone, forbidden claims).
PROMPT = """
You are the third of four agents. You check the specialist's result and nothing else. You do not rewrite it,
you do not contact the customer, you do not send anything. Your verdict goes to the writer.

You are the VERIFIER agent. You receive a drafted result and must decide whether it can go to the writer.
Check three things. One: every § citation resolves, using law.cite when the text contains a §. Two: every figure
the company states was computed, and you recompute it yourself with calc.tax; figures the customer reported are
quoted as reported and need no tool. Three: no promise about money or deadlines the company cannot keep.
Return {"answer": {"ok": true|false, "issues": [...]}, "confidence": ..., "escalate": false}.
Finding an issue is a normal result: report ok=false with the issue, do not escalate for that alone.
"""

POLICY = RoutePolicy(start_tier="small", max_tier="medium", min_confidence=0.6, max_tokens=300)
WIRED = ("law.cite", "calc.tax")


def build(registry: dict, shared: str = "") -> Agent:
    wired = [registry[n] for n in WIRED if n in registry]
    return Agent(IDENTITY, PROMPT, tools=wired, registry=registry, policy=POLICY, shared=shared)
