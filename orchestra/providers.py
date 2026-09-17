"""Provider adapters. Raw HTTP via urllib because the project rule is: standard library only, no pip.

    MockProvider           deterministic, offline, for tests and the rehearsal
    AnthropicProvider      POST https://api.anthropic.com/v1/messages   (ANTHROPIC_API_KEY)
    OpenAICompatProvider   POST {OPENAI_BASE_URL}/chat/completions      (OPENAI_API_KEY): OpenAI, OpenRouter,
                           Gemini's OpenAI-compatible endpoint, or the claude-code-api wrapper on the VPS
    ClaudeCodeProvider     `claude -p` subprocess with the user's own Claude login, no key, real usage and cost

Keys come from the environment only. They are never logged.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .compress import estimate_tokens

Message = dict  # {"role": "user"|"assistant", "content": str}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0      # served from the provider's prompt cache
    cache_write_tokens: int = 0     # written to the provider's prompt cache
    cost_usd_reported: Optional[float] = None   # the provider's own bill, when it reports one


@dataclass
class Completion:
    text: str
    usage: Usage
    model: str
    provider: str


class ProviderError(RuntimeError):
    pass


class Provider:
    name = "base"

    def complete(self, model: str, system: str, messages: list[Message], max_tokens: int = 1024,
                 temperature: float = 0.0,
                 system_blocks: Optional[list] = None) -> Completion:  # pragma: no cover - interface
        raise NotImplementedError


Responder = Callable[[str, str, list], str]   # (model, system, messages) -> text


class MockProvider(Provider):
    """Offline provider. `responder` decides the text; token usage is estimated from lengths."""

    name = "mock"

    def __init__(self, responder: Optional[Responder] = None):
        self.responder = responder or (lambda model, system, messages: json.dumps(
            {"answer": "mock reply to: " + str(messages[-1]["content"])[:60], "confidence": 0.9}))
        self.calls = 0

    def complete(self, model, system, messages, max_tokens=1024, temperature=0.0, system_blocks=None):
        self.calls += 1
        text = self.responder(model, system, messages)
        prompt = system + "".join(str(m["content"]) for m in messages)
        return Completion(text, Usage(estimate_tokens(prompt), estimate_tokens(text)), model, self.name)


def _post_json(url: str, headers: dict, body: dict, timeout: int = 120) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        snippet = e.read().decode("utf-8", "replace")[:300]
        raise ProviderError(f"HTTP {e.code} from {url}: {snippet}") from None
    except urllib.error.URLError as e:
        raise ProviderError(f"cannot reach {url}: {e.reason}") from None


class AnthropicProvider(Provider):
    name = "anthropic"
    url = "https://api.anthropic.com/v1/messages"
    # The API needs a minimum prefix (1024 tokens on Sonnet 5, 4096 on Haiku 4.5) before it caches; a shorter
    # prefix with cache_control is simply not cached, so we always mark it and build prompts long enough.
    # The scenario's policy text is in the first block on purpose: it is the same for every agent, so one
    # cache entry serves all of them rather than one entry per role.

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY missing (put it in .env, never in code)")

    def complete(self, model, system, messages, max_tokens=1024, temperature=0.0, system_blocks=None):
        # Three breakpoints, after ProjectDiscovery's write-up of the same problem:
        #   the shared prefix every agent sends gets the long-lived cache, because it is identical across
        #   agents and across records; the role block gets its own; and the conversation gets a sliding
        #   window on its last block, because that is the only part that grows.
        parts = [b for b in (system_blocks or [system]) if b]
        blocks: Any = []
        for i, text in enumerate(parts):
            blk = {"type": "text", "text": text}
            blk["cache_control"] = {"type": "ephemeral", "ttl": "1h"} if i == 0 else {"type": "ephemeral"}
            blocks.append(blk)
        msgs = [{"role": m["role"], "content": str(m["content"])} for m in messages]
        if len(msgs) > 1:                       # a conversation exists: cache everything up to its last turn
            last = msgs[-1]
            last["content"] = [{"type": "text", "text": last["content"],
                                "cache_control": {"type": "ephemeral"}}]
        body = {"model": model, "max_tokens": max_tokens, "system": blocks, "messages": msgs}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "anthropic-beta": "extended-cache-ttl-2025-04-11"}
        data = _post_json(self.url, headers, body)
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        u = data.get("usage", {})
        usage = Usage(int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)),
                      int(u.get("cache_read_input_tokens", 0) or 0), int(u.get("cache_creation_input_tokens", 0) or 0))
        return Completion(text, usage, model, self.name)


class OpenAICompatProvider(Provider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY missing (put it in .env, never in code)")

    def complete(self, model, system, messages, max_tokens=1024, temperature=0.0, system_blocks=None):
        body = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m["role"], "content": str(m["content"])} for m in messages]}
        headers = {"Authorization": "Bearer " + self.api_key}
        try:
            data = _post_json(self.base_url + "/chat/completions", headers, body)
        except ProviderError as e:
            if "max_tokens" not in str(e) or "HTTP 400" not in str(e):
                raise
            body["max_completion_tokens"] = body.pop("max_tokens")     # newer OpenAI models reject max_tokens
            data = _post_json(self.base_url + "/chat/completions", headers, body)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected response shape: " + json.dumps(data)[:200]) from None
        u = data.get("usage", {}) or {}
        cached = int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
        usage = Usage(int(u.get("prompt_tokens", 0)) - cached, int(u.get("completion_tokens", 0)), cached, 0)
        return Completion(text, usage, model, self.name)


class ClaudeCodeProvider(Provider):
    """Headless `claude -p` with the user's own Claude login. No API key. Real usage and cost from the JSON result.

    One shot per call: `--max-turns 1`, no tools, our own system prompt. Claude Code still sends about 11k tokens
    of its own prefix; they are cached after the first call per agent, and the ledger records what the CLI reports.
    Multi-message histories are flattened into one prompt (sent on stdin, so no flag can swallow it).
    """

    name = "claude_code"
    ALIASES = {"claude-haiku-4-5": "haiku", "claude-sonnet-5": "sonnet", "claude-opus-5": "opus"}

    def __init__(self, binary: Optional[str] = None, timeout: int = 180):
        self.binary = binary or os.environ.get("CLAUDE_BIN", "claude")
        self.timeout = timeout
        if shutil.which(self.binary) is None:
            raise ProviderError(f"'{self.binary}' not found on PATH (install Claude Code or set CLAUDE_BIN)")

    @staticmethod
    def flatten(messages: list[Message]) -> str:
        if len(messages) == 1:
            return str(messages[0]["content"])
        lines = ["Conversation so far. Continue as the assistant; answer in the required JSON only."]
        for m in messages:
            lines.append(f"[{m['role']}]\n{m['content']}")
        return "\n\n".join(lines)

    def complete(self, model, system, messages, max_tokens=1024, temperature=0.0, system_blocks=None):
        cmd = [self.binary, "-p", "--no-session-persistence", "--max-turns", "1",
               "--model", self.ALIASES.get(model, model), "--output-format", "json",
               "--system-prompt", system, "--exclude-dynamic-system-prompt-sections",
               "--tools", "", "--strict-mcp-config"]      # no built-in tools, no MCP servers: JSON text only
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}   # allow nesting inside a Claude session
        try:
            proc = subprocess.run(cmd, input=self.flatten(messages), capture_output=True, text=True,
                                  timeout=self.timeout, env=env)
        except subprocess.TimeoutExpired:
            raise ProviderError(f"claude -p timed out after {self.timeout}s") from None
        if proc.returncode != 0:
            raise ProviderError(f"claude -p exit {proc.returncode}: {(proc.stderr or proc.stdout)[:300]}")
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            raise ProviderError("claude -p returned no JSON: " + proc.stdout[:200]) from None
        if data.get("is_error"):
            raise ProviderError("claude -p error: " + str(data.get("result", ""))[:300])
        u = data.get("usage", {}) or {}
        usage = Usage(int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)),
                      int(u.get("cache_read_input_tokens", 0) or 0), int(u.get("cache_creation_input_tokens", 0) or 0),
                      float(data["total_cost_usd"]) if data.get("total_cost_usd") is not None else None)
        return Completion(str(data.get("result", "")), usage, model, self.name)


def make_provider(name: Optional[str] = None, responder: Optional[Responder] = None) -> Provider:
    name = name or os.environ.get("ORCHESTRA_PROVIDER", "mock")
    if name == "mock":
        return MockProvider(responder)
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openai":
        return OpenAICompatProvider()
    if name == "claude_code":
        return ClaudeCodeProvider()
    raise ProviderError(f"unknown provider '{name}' (mock | anthropic | openai | claude_code)")
