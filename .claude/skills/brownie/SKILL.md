---
name: brownie
description: Ingest the real Taxfix hackathon brief and adapt the whole project around it. Use the moment the challenge is announced — when the user says "brownie" and pastes, describes, photographs, or summarises what Taxfix presented. Assesses honestly whether the pre-built spine fits, then either rotates the build onto the brief or advises abandoning the spine and building something different. Emits the validation protocol, the jury defence, and a minute-by-minute plan.
---

# brownie — the rotating spine

The user is standing in Taxfix's office. The challenge just dropped. They have
roughly 135 minutes and they typed one word. **Move fast and commit.**

The thinking is already done and sitting in this repo. Your job is to take the
real brief, judge honestly whether the prepared work applies, and then either
rotate onto it or tell the user to drop it and build something else.

**You are allowed — and expected — to say "abandon the spine."** Forcing a tax
engine into a brief that doesn't want one loses the room. Saying so early is the
most valuable thing you can do.

## Step 0 — Ingest

The brief may arrive as pasted slide text, a photo of a slide, a verbal summary,
a link, or a few words the user half-remembers. Take whatever form it comes in.

If the user sent **only** the word `brownie` with no brief, ask exactly one
question — *"What did they announce?"* — and stop. Never guess the brief.

Otherwise, immediately write the brief verbatim to `docs/BRIEF.md`, with the
time it was announced and anything the user adds about the room (who is judging,
whether data or an API was handed out, any constraints said aloud but not on the
slide). This is the spine's memory: everything downstream reads from it, and it
survives a context compaction. Do this before analysing.

## Step 1 — Fit assessment (do this before anything else)

Read `docs/ROTATION.md` and `docs/PIVOT.md`. Then score the fit **honestly**.
This is a judgment call, not a keyword match — do not fake precision.

Ask four questions:

1. Does the brief involve **German tax arithmetic** — any euro figure whose
   correctness matters? → `core/pap/` applies
2. Does it involve **claims, law, explanations, or LLM output** that could be
   wrong? → `core/law/` applies
3. Does it involve **documents, invoices, receipts, VAT**? → `core/einvoice/` applies
4. Does **anything at all need proving**? → `core/harness/` applies (nearly always yes)

Then decide, and state the decision in one sentence before anything else:

| Verdict | When | What happens |
|---|---|---|
| **ROTATE** | 2+ of questions 1–3 apply | Use the spine. Go to step 2. |
| **PARTIAL** | exactly 1 of 1–3 applies | Keep that module and the harness, build the rest fresh. Say which parts you are dropping. |
| **PIVOT** | none of 1–3 apply | **Advise abandoning the spine.** Go to `docs/PIVOT.md` and run the greenfield path. |

Pivot triggers worth naming explicitly: the brief is about Cursor itself, about
AI-native development, design-to-code, developer productivity, Taxfix's
marketing or hiring, or it explicitly steers away from the tax domain. Also:
**if Taxfix hands out their own dataset or API, theirs beats ours** — that is at
least a PARTIAL and often a PIVOT.

One-sentence test: *if I deleted `core/`, would this build get meaningfully
harder?* If no, pivot.

Be decisive. "It could go either way" is not an answer the user can act on at
19:02. Pick one, say why in a sentence, and move.

## Step 2 — Bind to the spine (ROTATE and PARTIAL only)

Everything in `core/` **already works and is tested**. Do not rebuild it. Name
the modules the brief touches and what each buys:

| Module | What it is | Use when the brief involves |
|---|---|---|
| `core/pap/engine.py` | The BMF's federal wage-tax algorithm, executed. 14/14 conformance. | any euro figure, any "is this right" |
| `core/law/cite.py` | EStG/UStG/AO/StBerG, 1,059 paragraphs, resolver + hallucination audit | any claim, explanation, or model output |
| `core/einvoice/extract.py` | ZUGFeRD/XRechnung parser, ground truth embedded in the file | receipts, invoices, VAT, bookkeeping |
| `core/harness/harness.py` | oracle → cases → metric → pass bar | **always — it prints the number you say on stage** |

The line that wins the room, adapted to the brief:
> "We didn't start from zero. We brought the Bundesfinanzministerium's own tax
> algorithm and the full statute, so every number we show you is checkable."

## Step 3 — The five-part protocol

Fill these in for the actual brief, and declare the pass bar **before** building.
This is the difference between a demo and a proof.

- **oracle** — where truth comes from, and why it is independent of us
- **cases** — 15–40, at least 3 adversarial, built to break us
- **metric** — one number a tired judge can hold
- **pass bar** — declared now, not after seeing results
- **failure mode** — what wrong looks like, demoed live

Encode it as a `Suite` from `core/harness/harness.py`. If the brief has no
natural oracle, say so plainly and substitute an honest integration or
cold-user measurement — `docs/PIVOT.md` lists where oracles hide in unfamiliar
domains.

## Step 4 — Emit the plan

Produce exactly these, in this order, nothing else:

1. **Verdict** — ROTATE / PARTIAL / PIVOT, one sentence of why.
2. **What we keep** and **what we drop**. Be explicit about the drop.
3. **What we build** — scope to ~90 minutes, not 135. Leave 45 for validation
   and rehearsal.
4. **The five-part protocol**, filled in.
5. **Minute-by-minute plan** for the time actually remaining. Ask the time if
   you don't know it; otherwise assume 20:30 freeze, 21:15 demos.
6. **Pod split** — demo path / data+validation / narrative. Three people.
7. **Jury defence** — opening line quoting the brief back at them, the one
   number, three likely objections with answers. Pull company facts from
   `docs/DOSSIER.md` so it is specific to Taxfix, not generic. On a PIVOT, use
   the pivot opening line from `docs/PIVOT.md` — own the drop, don't hide it.

## Step 5 — Build

Start with the demo path end to end on fake-but-real-shaped data, then deepen.
Thin and running beats deep and broken.

## Non-negotiables

- **`Decimal`, never `float`, for money.** The BMF says so; float drift silently
  breaks a cent-exact claim on stage.
- **Report silent errors separately from over-escalation.** Over-escalating costs
  minutes; a wrong auto-decision gets filed and becomes a legal problem. Never
  blend them into one accuracy score.
- **Put the adversarial case in the demo.** Showing the system correctly
  *refusing* is worth more than three extra features — it is, word for word,
  Taxfix's own definition of excellence.
- **Say what is synthetic.** A stated limitation beats a quiet one.
- **Never invent a validation number.** If the suite hasn't run, say it hasn't run.
- **Never shoehorn.** If the spine doesn't fit, dropping it is the strong move,
  not the weak one.
- Stop building at the freeze even if something is unfinished.

## Re-entry

If the user says `brownie` again later with more information — a clarification
from the organisers, a judging criterion, a constraint they missed — update
`docs/BRIEF.md`, re-run the fit assessment, and say plainly whether the verdict
changed. A verdict that flips at 19:30 is recoverable. At 20:30 it is not: past
the freeze, note the mismatch and optimise the narrative instead of rebuilding.
