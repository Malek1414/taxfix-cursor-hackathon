"""Context hygiene: the cheapest token you never send."""

from __future__ import annotations

import re

_WS = re.compile(r"[ \t]+")


def estimate_tokens(text: str) -> int:
    """Rough count for budgeting and the mock provider: ~4 characters per token."""
    return max(1, len(text) // 4)


def trim(text: str, max_chars: int = 2000, marker: str = " …[trimmed {n} chars]") -> str:
    """Cut a tool result to `max_chars`, keeping head and tail. Says how much it cut."""
    if len(text) <= max_chars:
        return text
    cut = len(text) - max_chars
    head = int(max_chars * 0.7)
    tail = max_chars - head
    return text[:head] + marker.format(n=cut) + text[-tail:]


def squeeze(text: str) -> str:
    """Collapse runs of spaces/tabs and blank lines. Same meaning, fewer tokens."""
    lines = [_WS.sub(" ", ln).strip() for ln in text.splitlines()]
    out, blank = [], False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def compact_messages(messages: list[dict], keep_last: int = 6, max_chars_each: int = 1500) -> list[dict]:
    """Keep the first message (the task) and the last `keep_last`; trim each body. No LLM call."""
    if len(messages) <= keep_last + 1:
        return [{**m, "content": trim(str(m["content"]), max_chars_each)} for m in messages]
    head, tail = messages[:1], messages[-keep_last:]
    dropped = len(messages) - len(head) - len(tail)
    note = {"role": "user", "content": f"[{dropped} earlier messages compacted]"}
    return [{**m, "content": trim(str(m["content"]), max_chars_each)} for m in head + [note] + tail]
