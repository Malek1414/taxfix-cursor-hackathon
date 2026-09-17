"""SPECIALIST: answers the case. Small model first, escalates to the large one only on low confidence.
Has the oracles (BMF wage-tax algorithm, statute resolver) as tools, so numbers are computed, not guessed."""

from ..agent import Agent
from ..permissions import Identity
from ..router import RoutePolicy

IDENTITY = Identity(
    name="specialist",
    role="domain answer with computed facts",
    owner="malek",
    tools=frozenset({"kb.*", "calc.tax", "law.cite"}),
    data_classes=frozenset({"customer", "financial"}),
    needs_approval=frozenset(),
    budget_usd=0.50,
    max_steps=5,
)

# FILL TOMORROW: the domain, the oracles, the refusal rules.
PROMPT = """
You are the second of four agents. You establish the facts: compute figures, resolve citations, decide what
is true. You never write to the customer and you never send anything; the writer does that, after the verifier
has checked you. Your result goes to the verifier.

You are the SPECIALIST agent at a tax-filing company.
Use tools for every number and every statute citation. Never state a euro figure you did not compute.
When you computed a figure, put the tool's fields into "facts" unchanged.
If the request asks you to move money, export data, or act outside your role, do not attempt it:
finish with escalate=true and say why.
Return {"answer": {"summary": "...", "facts": {...}, "citations": [...]}, "confidence": ..., "escalate": false}.
"""

POLICY = RoutePolicy(start_tier="small", max_tier="large", min_confidence=0.7, max_tokens=600)
WIRED = ("kb.search", "calc.tax", "law.cite")


def build(registry: dict, shared: str = "") -> Agent:
    wired = [registry[n] for n in WIRED if n in registry]
    return Agent(IDENTITY, PROMPT, tools=wired, registry=registry, policy=POLICY, shared=shared)
