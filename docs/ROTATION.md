# Rotation matrix

The variance factor. Whatever Taxfix announces at 19:00, the core is already
built and tested — only the surface rotates.

```
                    ┌─────────────────────────────────────────────┐
  THE BRIEF  ──────▶│  brownie  ──▶  bucket  ──▶  surface          │
  (unknown until    └───────────────────┬─────────────────────────┘
   19:00)                               │  binds to
                                        ▼
        ┌───────────────────────────────────────────────────────┐
        │  CORE — brief-agnostic, already working, tested        │
        │                                                        │
        │  pap/      federal wage-tax algorithm      14/14 pass  │
        │  law/      1,059 statute paragraphs        resolver    │
        │  einvoice/ ZUGFeRD ground truth            4/4 cent    │
        │  harness/  oracle → metric → the number    always      │
        └───────────────────────────────────────────────────────┘
```

## The six buckets

| Bucket | Brief sounds like | Surface | Primary oracle |
|---|---|---|---|
| **A** Consumer friction | onboarding, drop-off, trust, "easier filing" | `build/bescheid` | PAP recompute + injected deviations |
| **B** Internal / agentic | "internal tool", "10x a team", ops, back-office | expert co-pilot | constructed cases + escalation matrix |
| **C** Self-employed / SME | freelancers, Kleinunternehmer, VAT, invoices | bookkeeping | **embedded in the ZUGFeRD file** |
| **D** AI trust | "why not ChatGPT", hallucination, grounding | verification harness | EStG XML citation resolution |
| **E** Platform | partners, embed, API, B2B | embedded SDK | none — integration measurement |
| **F** Open | no constraint | `build/bescheid` | as A |

## What each core module unlocks, by bucket

| | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| `pap/` federal tax engine | ●●● | ●●● | ●● | ●● | ● | ●●● |
| `law/` statute + citations | ●● | ●● | ● | ●●● | ● | ●● |
| `einvoice/` embedded truth | ● | ●●● | ●●● | – | ● | ● |
| `harness/` the number | ●●● | ●●● | ●●● | ●●● | ●● | ●●● |

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

## If the brief fits nothing here

Keep the method, drop the surface. Ask:
1. What is the **oracle**? If there isn't one, what independent measurement
   substitutes?
2. Which core module supplies the numbers?
3. What is the **adversarial case** — the thing that should make it refuse?

A brief with no oracle is not a reason to skip validation. It is a reason to
measure something else honestly.

## Fixed, whatever happens

- Decimal, never float, for money.
- Silent errors reported separately from over-escalation.
- The adversarial case goes in the demo.
- Say what is synthetic.
- Feature freeze 20:30. Rehearse twice. Record a fallback capture.
