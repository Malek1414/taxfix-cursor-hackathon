"""Exact-match response cache with in-flight dedup.

Same tier + same prompt within the TTL means no model call at all. And when two agents ask the identical
question at the same time (a duplicate ticket in the same wave), the second one waits for the first instead
of paying for the same answer twice. Without that, parallel duplicates both miss.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Optional

from .compress import squeeze


class ResponseCache:
    def __init__(self, path: Optional[Path] = None, ttl_seconds: int = 3600):
        self.path = path
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        self._inflight: dict[str, threading.Event] = {}
        if path and path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._data = {}

    @staticmethod
    def key(tier: str, system: str, messages: list[dict]) -> str:
        norm = json.dumps({"t": tier, "s": squeeze(system),
                           "m": [[m["role"], squeeze(str(m["content"]))] for m in messages]},
                          ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def begin(self, key: str) -> bool:
        """Claim this key as in flight. False means someone else is already asking; call `await_result`."""
        with self._lock:
            if key in self._inflight:
                return False
            self._inflight[key] = threading.Event()
            return True

    def finish(self, key: str) -> None:
        with self._lock:
            ev = self._inflight.pop(key, None)
        if ev is not None:
            ev.set()

    def await_result(self, key: str, timeout: float = 300.0) -> Optional[str]:
        """Wait for the agent that claimed this key, then read its answer. None if it failed or timed out."""
        with self._lock:
            ev = self._inflight.get(key)
        if ev is None:
            return self.get(key)
        ev.wait(timeout)
        return self.get(key)

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._data.get(key)
            if row and time.time() - row["ts"] <= self.ttl:
                self.hits += 1
                return row["text"]
            self.misses += 1
            return None

    def set(self, key: str, text: str) -> None:
        with self._lock:
            self._data[key] = {"ts": time.time(), "text": text}
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self._data), encoding="utf-8")
                tmp.replace(self.path)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
