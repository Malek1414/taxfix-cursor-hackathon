"""Sources and sinks: what comes in at the front, what leaves at the back.

    load_records(path)      csv, tsv, json, jsonl, ndjson, txt, or a directory of files → list[dict]
    write_records(path)     csv, jsonl, json, md → whatever the run produced
    Params                  key=value settings from the command line or .env, readable inside prompts

Whatever dataset the brief hands you at 19:00 ("here are 5,000 support tickets"), point `--data` at it.
Nothing in the orchestra knows the shape of a record: every record is a dict, and two conventional keys,
`id` and `text`, are filled in if they can be inferred. Everything else stays and is available to prompts.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# Field names datasets use in the wild for the two things a pipeline needs: a key and the text.
ID_KEYS = ("id", "ticket_id", "case_id", "uuid", "key", "number", "ref", "reference")
TEXT_KEYS = ("text", "body", "message", "content", "description", "complaint", "comment", "review",
             "question", "subject", "summary", "ticket", "input")
# Who the record is about. Prompts refer to it as {customer}, so map the usual column names onto it.
WHO_KEYS = ("customer", "customer_email", "email", "user", "user_email", "author", "from", "sender", "account")


class DataError(RuntimeError):
    pass


def _rows_from_json(raw: str) -> list:
    doc = json.loads(raw)
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for key in ("items", "records", "data", "rows", "results", "tickets", "reviews"):
            if isinstance(doc.get(key), list):
                return doc[key]
        return [doc]
    raise DataError("JSON must be a list, or an object holding one")


def _rows_from_jsonl(raw: str) -> list:
    out = []
    for i, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError as e:
            raise DataError(f"line {i} is not JSON: {e}") from None
    return out


def _rows_from_delimited(path: Path, delimiter: str) -> list:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [dict(r) for r in csv.DictReader(f, delimiter=delimiter)]


def load_records(path: str | Path, limit: Optional[int] = None, id_key: Optional[str] = None,
                 text_key: Optional[str] = None) -> list:
    """Read a dataset into a list of dicts. Raises DataError with the reason, never a silent empty list."""
    p = Path(path).expanduser()
    if not p.exists():
        raise DataError(f"no such dataset: {p}")
    if p.is_dir():
        files = sorted(q for q in p.iterdir() if q.is_file() and not q.name.startswith("."))
        rows: list = [{"id": q.stem, "text": q.read_text(encoding="utf-8", errors="replace"), "source_file": q.name}
                      for q in files]
    else:
        raw = p.read_text(encoding="utf-8", errors="replace")
        suffix = p.suffix.lower()
        if suffix in (".csv",):
            rows = _rows_from_delimited(p, ",")
        elif suffix in (".tsv", ".tab"):
            rows = _rows_from_delimited(p, "\t")
        elif suffix in (".jsonl", ".ndjson"):
            rows = _rows_from_jsonl(raw)
        elif suffix == ".json":
            rows = _rows_from_json(raw)
        else:                                            # one record per non-empty line
            rows = [{"text": ln.strip()} for ln in raw.splitlines() if ln.strip()]
    rows = [r if isinstance(r, dict) else {"text": str(r)} for r in rows]
    if not rows:
        raise DataError(f"{p} parsed to zero records")
    return normalise(rows, id_key=id_key, text_key=text_key)[: limit or None]


def normalise(rows: list, id_key: Optional[str] = None, text_key: Optional[str] = None) -> list:
    """Give every record an `id` and a `text`, without throwing away the columns it already has."""
    first = rows[0]
    if text_key is None:
        text_key = next((k for k in TEXT_KEYS if k in first), None)
        if text_key is None:                             # fall back to the longest string column
            text_key = max(((k, len(str(v))) for k, v in first.items() if isinstance(v, str)),
                           key=lambda kv: kv[1], default=(None, 0))[0]
    if id_key is None:
        id_key = next((k for k in ID_KEYS if k in first), None)
    who_key = next((k for k in WHO_KEYS if k in first), None)
    out = []
    for i, r in enumerate(rows, 1):
        rec = dict(r)
        rec["text"] = str(rec.get(text_key, "")).strip() if text_key else ""
        rec["id"] = str(rec.get(id_key, "")).strip() if id_key and rec.get(id_key) else f"r{i:04d}"
        if who_key and "customer" not in rec:
            rec["customer"] = str(rec.get(who_key, "")).strip()
        out.append(rec)
    return out


def write_records(path: str | Path, rows: list, title: str = "") -> Path:
    """Write the result of a run. Format from the extension: csv, jsonl, json, md."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(r) for r in rows]
    suffix = p.suffix.lower()
    if suffix == ".jsonl":
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows) + "\n", encoding="utf-8")
    elif suffix == ".json":
        p.write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    elif suffix == ".md":
        cols = list({k: None for r in rows for k in r})
        head = "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |\n"
        body = "".join("| " + " | ".join(str(r.get(c, "")).replace("|", "\\|").replace("\n", " ") for c in cols)
                       + " |\n" for r in rows)
        p.write_text((f"# {title}\n\n" if title else "") + head + body, encoding="utf-8")
    else:
        cols = list({k: None for r in rows for k in r})
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return p


@dataclass
class Params:
    """Settings a run can be steered with, without touching code: `--set tone=formal --set market=ES`.

    Prompts and task templates read them as `{p.<name>}`; a scenario reads them as `params["name"]`.
    """

    values: dict = field(default_factory=dict)

    @classmethod
    def parse(cls, pairs: Iterable[str], defaults: Optional[dict] = None) -> "Params":
        values = dict(defaults or {})
        for pair in pairs:
            if "=" not in pair:
                raise DataError(f"--set needs key=value, got '{pair}'")
            k, _, v = pair.partition("=")
            values[k.strip()] = v.strip()
        return cls(values)

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def __contains__(self, key: str) -> bool:
        return key in self.values

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def __getattr__(self, key: str) -> Any:        # `{p.tone}` inside a template
        try:
            return self.values[key]
        except KeyError:
            raise AttributeError(key) from None

    def __str__(self) -> str:
        return ", ".join(f"{k}={v}" for k, v in sorted(self.values.items())) or "none"


_FIELD = re.compile(r"\{([a-zA-Z_][\w.]*)\}")


def fill(template: str, record: Optional[dict] = None, params: Optional[Params] = None, **extra) -> str:
    """Substitute {field} from the record, {p.name} from the params, {name} from extras.

    A field that does not exist is left as written rather than raising: a half-filled prompt is easier to
    debug on stage than a traceback, and the model sees the placeholder and says so.
    """
    record = record or {}

    def sub(m):
        key = m.group(1)
        if key.startswith("p.") and params is not None:
            return str(params.get(key[2:], m.group(0)))
        if key in extra:
            return str(extra[key])
        if key in record:
            return str(record[key])
        return m.group(0)
    return _FIELD.sub(sub, template)
