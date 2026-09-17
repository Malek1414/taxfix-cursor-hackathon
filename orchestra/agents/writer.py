"""WRITER: turns the verified facts into the customer-facing text. Sending is a human decision:
mail.send always needs approval, refund.issue is not on its allowlist at all."""

from ..agent import Agent
from ..permissions import Identity
from ..router import RoutePolicy

IDENTITY = Identity(
    name="writer",
    role="customer reply",
    owner="sami",
    tools=frozenset({"mail.send", "kb.search"}),   # on the short route it answers from the help centre itself
    data_classes=frozenset({"customer"}),
    needs_approval=frozenset({"mail.send"}),     # drafts freely, sends only with a human
    budget_usd=0.10,
    max_steps=3,
)

# FILL TOMORROW: tone, language, signature rules.
PROMPT = """
You are the last of four agents. You turn checked facts into the customer's reply and request mail.send for
it. You do not recompute figures and you do not act on the account.

You are the WRITER agent. Write a short, plain reply to the customer from the facts you are given.
When no earlier agent has supplied facts, look the answer up with kb.search before writing; that is the
normal case for routine questions, which reach you directly.
No emojis, no dashes as punctuation, no promises the facts do not support.
When the reply is ready, request mail.send with {"to": "...", "body": "..."}; if it is not approved,
finish with the draft and escalate=true so a person sends it.
Return {"answer": {"draft": "..."}, "confidence": ..., "escalate": false}.
"""

POLICY = RoutePolicy(start_tier="small", max_tier="medium", min_confidence=0.6, max_tokens=400)
WIRED = ("mail.send", "kb.search")


def build(registry: dict, shared: str = "") -> Agent:
    wired = [registry[n] for n in WIRED if n in registry]
    return Agent(IDENTITY, PROMPT, tools=wired, registry=registry, policy=POLICY, shared=shared)
