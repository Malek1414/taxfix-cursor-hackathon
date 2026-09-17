"""Barebone agent definitions. Each file exports IDENTITY, PROMPT, POLICY, WIRED and build(registry, prefix).

Tomorrow: keep the four roles, rewrite PROMPT and the allowlists for the real brief, change WIRED to the tools
the scenario registers. The infrastructure around them does not change.
"""

from typing import Optional

from . import intake, specialist, verifier, writer

ROLES = (intake, specialist, verifier, writer)


def load_all(registry: dict, shared: Optional[dict] = None) -> list:
    """`registry` maps tool name → Tool. `shared` maps role name → text that agent shares with the others.

    Shared text is a separate layer rather than a prefix glued onto the role prompt, so the provider can
    serve it from one cache entry for every agent that sends it.
    """
    shared = shared or {}
    return [role.build(registry, shared.get(role.IDENTITY.name, "")) for role in ROLES]
