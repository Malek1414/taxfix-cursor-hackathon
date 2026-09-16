# Rotation matrix

The variance factor. Whatever Taxfix announces at 19:00, the core is already
built and tested — only the surface rotates.

```
                    ┌─────────────────────────────────────────────┐
  THE BRIEF  ──────▶│  brownie  ──▶  FIT GATE  ──▶  bucket         │
  (unknown until    └───────────────────┬─────────────────────────┘
   19:00)                               │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
              ROTATE / PARTIAL                          PIVOT
                    │                              (docs/PIVOT.md —
                    │  binds to                     drop the spine,
                    ▼                               keep the harness)
        ┌───────────────────────────────────────────────────────┐
        │  CORE — brief-agnostic, already working, tested        │
        │                                                        │
        │  pap/      federal wage-tax algorithm      14/14 pass  │
        │  law/      1,059 statute paragraphs        resolver    │
        │  einvoice/ ZUGFeRD ground truth            4/4 cent    │
        │  harness/  oracle → metric → the number    always      │
        └───────────────────────────────────────────────────────┘
```

## The fit gate — run this first

Four questions, honestly answered. This is judgment, not keyword matching.

| # | Question | Module it unlocks |
|---|---|---|
| 1 | Does the brief involve German tax arithmetic — any euro figure whose correctness matters? | `core/pap/` |
| 2 | Claims, law, explanations, or LLM output that could be wrong? | `core/law/` |
| 3 | Documents, invoices, receipts, VAT? | `core/einvoice/` |
| 4 | Does anything at all need proving? | `core/harness/` — nearly always yes |

| 2+ of Q1–3 | exactly 1 | none |
|---|---|---|
| **ROTATE** — use the spine | **PARTIAL** — keep that module + harness, build the rest fresh | **PIVOT** — abandon the spine, see `docs/PIVOT.md` |

One-sentence test: *if I deleted `core/`, would this build get meaningfully
harder?* If no, pivot.

**If Taxfix hands out their own dataset or API, theirs beats ours** — that is at
least PARTIAL and often PIVOT. A team building on the host's data is always more
credible than a team building on something they brought.

## The seven buckets

| Bucket | Brief sounds like | Surface | Primary oracle |
|---|---|---|---|
| **A** Consumer friction | onboarding, drop-off, trust, "easier filing" | `build/bescheid` | PAP recompute + injected deviations |
| **B** Internal / agentic | "internal tool", "10x a team", ops, back-office | expert co-pilot | constructed cases + escalation matrix |
| **C** Self-employed / SME | freelancers, Kleinunternehmer, VAT, invoices | bookkeeping | **embedded in the ZUGFeRD file** |
| **D** AI trust | "why not ChatGPT", hallucination, grounding | verification harness | EStG XML citation resolution |
| **E** Platform | partners, embed, API, B2B | embedded SDK | none — integration measurement |
| **F** Open | no constraint | `build/bescheid` | as A |
| **G** **Off-domain** | Cursor itself, AI-native dev, design-to-code, marketing, hiring, or "anything except tax" | **greenfield — `docs/PIVOT.md`** | found fresh; harness still applies |

## What each core module unlocks, by bucket

| | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| `pap/` federal tax engine | ●●● | ●●● | ●● | ●● | ● | ●●● | – |
| `law/` statute + citations | ●● | ●● | ● | ●●● | ● | ●● | – |
| `einvoice/` embedded truth | ● | ●●● | ●●● | – | ● | ● | – |
| `harness/` the number | ●●● | ●●● | ●●● | ●●● | ●● | ●●● | **●●●** |

Note the last column: in a pivot you lose three of the four modules and keep the
one that matters most on stage. Validation doctrine is domain-independent.

## Rotations in detail

### A / F — Consumer friction, or open brief → **Bescheid-Check**
Already built. `python3 build/bescheid/demo.py --stage`. If the brief names a
*different* consumer moment (onboarding, document upload, refund estimate), keep
the engine and swap the surface: the PAP still supplies every euro figure, the
harness still prints the number, only the screen changes.

### B — Internal tooling → **Expert co-pilot**
Reuse `einvoice/` for document intake and `pap/` for the draft figures. The new
code is the **triage queue**: rank items by euros at stake, decide what a human
must see. Metric is the escalation confusion matrix, not accuracy. Pass bar:
zero silent errors, over-escalation up to ~20% is an explicit pass.

### C — Self-employed → **Always-on bookkeeping**
Strongest oracle of all: `einvoice/extract.py` already reconciles 4/4 to the
cent against truth embedded in the file. Build the **§19 UStG threshold alarm**
(€25k prior year / €100k current) — it must fire *before* crossing, not after.
That is the detail only someone who knows German tax would add.

### D — AI trust → **Verification harness**
`law/cite.py` already does the hallucination audit: `audit(answer)` returns a
verdict per citation, checkable live. Write 25 questions *before* building,
including 10 a general model handles fine (be fair — it makes the comparison
credible) and 5 where the honest answer is "I need more facts."

### E — Platform → **Embedded SDK**
No accuracy oracle; say so rather than faking a metric. Measure integration:
lines of host code, minutes for a cold integrator, style isolation across three
hosts, and whether the host can read tax data (it must not).

### G — Off-domain → **pivot, and say so**

This is a *Cursor* hackathon hosted at Taxfix, not a Taxfix hackathon. The prior
edition at Bliq floated themes like design-to-code and AI-native engineering
workflows — neither touching the host's domain. If that happens, forcing the tax
engine in loses the room.

Full greenfield path in `docs/PIVOT.md`: how to pick a target in ten minutes,
where oracles hide in an unfamiliar domain, and the opening line that turns the
drop into evidence of judgment rather than failure.

Decide inside the first ten minutes. A pivot at 19:05 is free; a pivot at 20:00
is a loss.

## Fixed, whatever happens

- Decimal, never float, for money.
- Silent errors reported separately from over-escalation.
- The adversarial case goes in the demo.
- Say what is synthetic.
- Feature freeze 20:30. Rehearse twice. Record a fallback capture.
