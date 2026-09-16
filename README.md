# Taxfix Cursor Hackathon

Berlin, 17 Sep 2026 · Taxfix SE, Köpenicker Str. 122 · challenge at 19:00, demos 21:15

## The one thing to know

Say **`brownie`** with the challenge Taxfix announces, and the build rotates onto it.

```
brownie  <paste the problem statement here>
```

Everything in `core/` is brief-agnostic and already working. Only the surface changes.

And if the brief doesn't fit the prep at all — it's a *Cursor* hackathon, the
challenge may never touch German tax — `brownie` says so and switches to the
greenfield path in `docs/PIVOT.md` instead of shoehorning. That call gets made in
the first ten minutes.

## Why this exists

Every team will demo something that *looks* right in 135 minutes. Taxfix's own job
ads say excellence is "knowing when the AI output is wrong even when it looks right."
So the differentiator isn't the build — it's the **oracle**: an independent source of
truth you can check yourself against, live, on stage.

This repo pre-loads the oracles.

## What's already working

| | | Status |
|---|---|---|
| `core/pap/` | The Bundesfinanzministerium's own wage-tax algorithm, executed | **14/14 conformance** |
| `core/law/` | EStG, UStG, AO, StBerG — 1,059 paragraphs + citation resolver | resolves + audits |
| `core/einvoice/` | ZUGFeRD/XRechnung parser, truth embedded in the file | **4/4 cent-exact** |
| `core/harness/` | oracle → cases → metric → pass bar → the number | ready |
| `build/bescheid/` | Bescheid-Check, the default bet | **40/40, 0 silent errors** |

## Try it

```bash
python3 tests/test_pap.py                 # 14 structural checks on German wage tax
python3 build/bescheid/demo.py --stage    # the 3-minute demo path
python3 build/bescheid/demo.py            # the 40-case validation
python3 core/einvoice/extract.py          # invoice corpus, cent reconciliation
python3 core/pap/engine.py 60000 1        # federal wage tax: gross, Steuerklasse
python3 core/law/cite.py "nach § 9 EStG und § 4b EStG"   # hallucination audit
```

No dependencies. Python 3 standard library only — don't lose hackathon minutes to pip.

## Research

`research/` holds the source documents: the company dossier and the 12-page
validation playbook (one page per candidate idea, each with an oracle, a declared
pass bar, and a prepared jury defence). Condensed versions in `docs/` are what the
`brownie` skill reads at speed.

## Data provenance

Everything in `data/` is public and free to reuse. Re-fetch with `scripts/fetch_data.sh`.

- **Statutes** — gesetze-im-internet.de (Bundesamt für Justiz), XML with published DTD
- **PAP 2025/2026** — bmf-steuerrechner.de, the official algorithm as XML pseudocode
- **Invoice fixtures** — Mustangproject + the KoSIT XRechnung conformance suite
- **Lohnsteuerbescheinigung 2026** — the BMF's official printed-form template
- **Income statistics** — Destatis

The BMF's *live* calculator API also exists but needs a Zugriffscode with no
self-service signup (email only). We don't need it — `core/pap/engine.py` runs the
published algorithm directly.

## Reading order

1. `CLAUDE.md` — project instructions and the non-negotiables
2. `docs/ROTATION.md` — the fit gate, then brief → bucket → surface
3. `docs/PIVOT.md` — what to do when the spine doesn't fit
4. `docs/DOSSIER.md` — company facts for the opening line
5. `docs/PLAYBOOK.md` — the seven candidate surfaces
6. `docs/BRIEF.md` — empty until 19:00; the spine's memory
7. `research/` — the full dossier and playbook behind all of the above
