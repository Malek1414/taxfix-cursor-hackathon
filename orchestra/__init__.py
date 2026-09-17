"""
orchestra — the barebone agent-orchestration infrastructure for the Taxfix Cursor Hackathon.

Standard library only (Python 3.9+). No pip.

    config       .env loader, model tiers, prices
    providers    mock / anthropic / openai-compatible HTTP adapters
    router       tiered cascade: small model first, escalate on low confidence
    cache        exact-match response cache with TTL
    compress     tool-result trimming, history compaction
    ledger       tokens, cost, baseline ("everything on the big model"), savings
    permissions  identity, scopes, tool allowlist, approval gate, audit log
    agent        barebone Agent with a provider-neutral JSON tool protocol
    orchestrator supervisor: waves of steps, parallel fan-out, human queue
    verify       bridge to spine/core/harness (oracle → cases → the number)

Fill `orchestra/agents/*.py` tomorrow. Everything else already runs: `python3 orchestra/demo.py`.
"""
__all__ = ["config", "providers", "router", "cache", "compress", "ledger", "permissions", "agent", "orchestrator", "verify"]
