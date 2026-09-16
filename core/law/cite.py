"""
Resolves German statute citations against the official text.

Every citation your system emits should be checkable live, on stage. That is the
whole point: a general model can invent "§ 9b EStG" and sound completely
convincing. With the real statute on disk you can type the citation into the
resolver in front of the jury and show it either resolving or not existing.

Source: gesetze-im-internet.de — Bundesamt für Justiz, free to reuse, XML with a
published DTD. Laws on disk: EStG, UStG, AO, StBerG.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

LAW_DIR = Path(__file__).resolve().parents[2] / "data" / "law"

# Filed under their gesetze-im-internet zip names.
LAWS = {
    "EStG": "EStG.xml.zip",
    "UStG": "UStG.xml.zip",
    "AO": "AO.xml.zip",
    "StBerG": "StBerG.xml.zip",
}


@dataclass
class Norm:
    law: str
    para: str          # e.g. "§ 9"
    title: str
    text: str
    doknr: str = ""

    @property
    def citation(self) -> str:
        return f"{self.para} {self.law}"

    def excerpt(self, n: int = 400) -> str:
        t = re.sub(r"\s+", " ", self.text).strip()
        return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"

    def __repr__(self) -> str:
        return f"<Norm {self.citation}: {self.title[:48]!r}>"


@dataclass
class Verdict:
    """What a citation check returns. `supported` is the honest bit."""

    citation: str
    exists: bool
    norm: Norm | None = None
    supported: bool | None = None       # None = not checked against a claim
    matched_terms: list[str] = field(default_factory=list)
    reason: str = ""

    def __bool__(self) -> bool:
        return self.exists and (self.supported is not False)


def _norm_text(el: ET.Element) -> str:
    return " ".join(t.strip() for t in el.itertext() if t and t.strip())


@lru_cache(maxsize=8)
def load(law: str = "EStG") -> dict[str, Norm]:
    """Parse one statute into {'§ 9': Norm}. Cached."""
    law = law.strip()
    if law not in LAWS:
        raise KeyError(f"Unknown law {law!r}. Available: {', '.join(LAWS)}")

    zpath = LAW_DIR / LAWS[law]
    unpacked = LAW_DIR / law.lower()
    if unpacked.is_dir() and any(unpacked.glob("*.xml")):
        raw = next(unpacked.glob("*.xml")).read_bytes()
    elif zpath.exists():
        with zipfile.ZipFile(zpath) as z:
            raw = z.read(next(n for n in z.namelist() if n.endswith(".xml")))
    else:
        raise FileNotFoundError(f"{law} not found. Run scripts/fetch_data.sh")

    out: dict[str, Norm] = {}
    for n in ET.fromstring(raw).iter("norm"):
        meta = n.find("metadaten")
        if meta is None:
            continue
        enbez = meta.findtext("enbez") or ""
        if not enbez.startswith("§"):
            continue
        body = n.find("textdaten/text")
        out[_key(enbez)] = Norm(
            law=law,
            para=enbez.strip(),
            title=(meta.findtext("titel") or "").strip(),
            text=_norm_text(body) if body is not None else "",
            doknr=n.get("doknr", ""),
        )
    return out


def _key(s: str) -> str:
    """'§9 a', '§ 9a', 'Paragraph 9a' all collapse to the same key."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("Paragraf", "§").replace("Paragraph", "§")
    s = re.sub(r"[^\w§]", "", s).lower()
    return s


CITE_RE = re.compile(
    # The suffix letter must not be the first letter of the law name:
    # "§ 9 EStG" is paragraph 9, not paragraph "9E".
    r"§+\s*(\d+(?:\s*[a-z](?![a-zA-Z]))?)"      # § 9b
    r"(?:\s*Abs(?:atz|\.)?\s*(\d+))?"           # Abs. 1
    r"(?:\s*(?:S\.|Satz)\s*(\d+))?"             # Satz 2
    r"(?:\s*(EStG|UStG|AO|StBerG))?",           # law, if named
    re.IGNORECASE,
)


def find_citations(text: str, default_law: str = "EStG") -> list[str]:
    """Pull every statutory citation out of free text (e.g. an LLM answer)."""
    seen, out = set(), []
    for m in CITE_RE.finditer(text):
        para = re.sub(r"\s+", "", m.group(1))
        law = (m.group(4) or default_law)
        law = next((k for k in LAWS if k.lower() == law.lower()), default_law)
        c = f"§ {para} {law}"
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def resolve(citation: str, law: str | None = None) -> Norm | None:
    """Look up a single citation. Returns None if it does not exist."""
    m = CITE_RE.search(citation)
    if not m:
        return None
    law = law or m.group(4) or "EStG"
    law = next((k for k in LAWS if k.lower() == law.lower()), "EStG")
    return load(law).get(_key("§" + re.sub(r"\s+", "", m.group(1))))


def check(citation: str, claim: str = "", law: str | None = None) -> Verdict:
    """Does this citation exist — and does its text plausibly support the claim?

    `supported` is a weak signal by design: it reports term overlap between the
    claim and the statute text, not legal correctness. Present it as
    "the cited paragraph exists and mentions X", never as "the claim is right".
    """
    norm = resolve(citation, law)
    if norm is None:
        return Verdict(citation, exists=False, reason="no such paragraph in the statute")

    if not claim:
        return Verdict(citation, exists=True, norm=norm, reason="exists; claim not checked")

    body = norm.text.lower() + " " + norm.title.lower()
    terms = [w for w in re.findall(r"[a-zäöüß]{5,}", claim.lower()) if w not in _STOP]
    hits = sorted({t for t in terms if t in body})
    ratio = len(hits) / len(terms) if terms else 0.0
    return Verdict(
        citation, exists=True, norm=norm,
        supported=ratio >= 0.25,
        matched_terms=hits,
        reason=f"{len(hits)}/{len(terms)} claim terms appear in the cited text",
    )


_STOP = {
    "werden", "wurde", "haben", "einem", "einer", "eines", "diese", "dieser",
    "welche", "nicht", "sowie", "gemaess", "gemäß", "kann", "koennen", "können",
    "muss", "müssen", "wenn", "dann", "aber", "oder", "auch", "nach", "ueber",
    "über", "durch", "steuer",
}


def audit(answer: str, default_law: str = "EStG") -> list[Verdict]:
    """Check every citation in a block of text. The hallucination detector."""
    return [check(c, claim=answer) for c in find_citations(answer, default_law)]


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) > 1:
        for v in audit(" ".join(sys.argv[1:])):
            mark = "OK  " if v.exists else "MISSING"
            print(f"{mark} {v.citation:<16} {v.norm.title[:60] if v.norm else v.reason}")
    else:
        estg = load("EStG")
        print(f"EStG: {len(estg)} paragraphs on disk")
        for c in ("§ 9 EStG", "§ 32a EStG", "§ 9b EStG", "§ 999 EStG"):
            v = check(c)
            print(f"  {c:<14} {'exists ' if v.exists else 'MISSING'} "
                  f"{v.norm.title[:56] if v.norm else ''}")
