"""MCP over stdio: hang any Model Context Protocol server into the registry, behind the same gate.

    servers = connect_all({"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                                          "data_class": "customer"}})
    registry.update(servers.tools())

Every tool an MCP server advertises becomes an ordinary `Tool` named `<server>.<tool>` with a data class,
so the identity allowlist and the approval gate apply to it exactly as they do to a local function. That is
the point: a new MCP server does not widen what any agent may do until someone writes it into an allowlist.

JSON-RPC 2.0 over the child's stdin and stdout, standard library only.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from .agent import Tool

PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


@dataclass
class MCPServer:
    """One running MCP server. `data_class` is what its tools are treated as touching."""

    name: str
    command: list
    env: Optional[dict] = None
    cwd: Optional[str] = None
    data_class: str = "public"
    needs_approval: bool = False
    timeout: float = 60.0
    proc: Optional[subprocess.Popen] = field(default=None, repr=False)
    _id: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _tools: list = field(default_factory=list)

    # -- transport --------------------------------------------------------
    def start(self) -> "MCPServer":
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        env.update(self.env or {})
        try:
            self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, text=True, bufsize=1, env=env, cwd=self.cwd)
        except (OSError, ValueError) as e:
            raise MCPError(f"cannot start MCP server '{self.name}': {e}") from None
        self._request("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                     "clientInfo": {"name": "orchestra", "version": "1"}})
        self._notify("notifications/initialized")
        self._tools = self._request("tools/list", {}).get("tools", [])
        return self

    def _send(self, payload: dict) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise MCPError(f"MCP server '{self.name}' is not running")
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _notify(self, method: str, params: Optional[dict] = None) -> None:
        with self._lock:
            self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _request(self, method: str, params: dict) -> dict:
        with self._lock:
            self._id += 1
            rid = self._id
            self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            if self.proc is None or self.proc.stdout is None:
                raise MCPError(f"MCP server '{self.name}' has no output")
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    raise MCPError(f"MCP server '{self.name}' closed the connection during {method}")
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue                                  # servers sometimes log to stdout; ignore noise
                if msg.get("id") != rid:
                    continue                                  # a notification or another response
                if "error" in msg:
                    raise MCPError(f"{self.name}.{method}: {msg['error'].get('message', msg['error'])}")
                return msg.get("result", {})

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        finally:
            self.proc = None

    # -- tools ------------------------------------------------------------
    def call(self, tool: str, arguments: dict) -> Any:
        result = self._request("tools/call", {"name": tool, "arguments": arguments})
        blocks = result.get("content", [])
        text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if result.get("isError"):
            return {"error": text or "MCP tool reported an error"}
        return {"text": text} if text else result

    def tools(self) -> dict:
        """The server's tools as registry entries named `<server>.<tool>`."""
        out = {}
        for spec in self._tools:
            raw = spec.get("name", "")
            name = f"{self.name}.{raw}"
            schema = spec.get("inputSchema") or {}
            props = schema.get("properties") or {}
            args = "{" + ", ".join(f'"{k}": {(v or {}).get("type", "any")}' for k, v in props.items()) + "}"
            out[name] = Tool(name, (spec.get("description") or "MCP tool").strip().split("\n")[0],
                             (lambda t=raw, **kw: self.call(t, kw)), args or "{}", self.data_class)
        return out


@dataclass
class MCPRegistry:
    servers: dict = field(default_factory=dict)
    failed: dict = field(default_factory=dict)

    def tools(self) -> dict:
        out: dict = {}
        for s in self.servers.values():
            out.update(s.tools())
        return out

    def approval_patterns(self) -> set:
        """Tool patterns from servers marked as needing a human. Add these to the identity that uses them."""
        return {f"{s.name}.*" for s in self.servers.values() if s.needs_approval}

    def stop(self) -> None:
        for s in self.servers.values():
            s.stop()


def connect_all(config: dict, strict: bool = False) -> MCPRegistry:
    """Start the configured servers. A server that fails is recorded, not fatal, unless `strict`.

    config: {"<name>": {"command": "npx", "args": [...], "env": {...}, "cwd": ".",
                        "data_class": "customer", "needs_approval": true}}
    The same shape as an MCP client config file, so a `mcpServers` block can be pasted in.
    """
    reg = MCPRegistry()
    for name, spec in (config or {}).items():
        cmd = spec.get("command")
        if not cmd:
            reg.failed[name] = "no command"
            continue
        server = MCPServer(name, [cmd] + list(spec.get("args") or []), env=spec.get("env"), cwd=spec.get("cwd"),
                           data_class=spec.get("data_class", "public"),
                           needs_approval=bool(spec.get("needs_approval")))
        try:
            reg.servers[name] = server.start()
        except MCPError as e:
            server.stop()
            reg.failed[name] = str(e)
            if strict:
                raise
    return reg


def load_config(path: str) -> dict:
    """Read a `mcpServers` config file (the shape Claude Code and Cursor use)."""
    from pathlib import Path
    doc = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return doc.get("mcpServers", doc)
