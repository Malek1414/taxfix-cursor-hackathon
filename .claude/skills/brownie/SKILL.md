---
name: brownie
description: Rotate the hackathon build onto the real Taxfix challenge. Use the moment the brief is announced — when the user says "brownie" and pastes, describes, photographs, or summarises the problem Taxfix presented. Maps the brief onto the pre-built core assets, picks the surface, rewrites the validation protocol and the jury defence, and emits a minute-by-minute build plan for the remaining time.
---

# brownie — the rotation engine

The user is standing in Taxfix's office. The challenge just dropped. They have
~135 minutes and they typed one word. **Move fast and commit.**

Your job is not to brainstorm. The thinking is already done and sitting in this
repo. Your job is to **rotate** it onto whatever Taxfix actually asked for.

## Before anything else

Read `docs/ROTATION.md`. It carries the rotation matrix, the seven candidate
surfaces, and what each core module unlocks. Then read `docs/DOSSIER.md` for the
company facts you will need for the opening line.

If the user gave you no brief text (just "brownie"), ask exactly one question:
*"What did they announce?"* — then stop and wait. Do not guess the brief.

## Step 1 — Classify the brief (60 seconds of thinking, no tool calls)

Put the brief into one of six buckets. Say which one you chose and why, in one
sentence. If it straddles two, name both and pick the one with the better oracle.

| Bucket | Signals in the brief | Rotate to |
|---|---|---|
| **A. Consumer friction** | onboarding, drop-off, trust, "make filing easier", UX | Bescheid-Check (primary), or the brief's own moment |
| **B. Internal / agentic tooling** | "internal", "10x a team", ops, agents, back-office | Expert co-pilot |
| **C. Self-employed / SME** | freelancers, Kleinunternehmer, invoices, VAT, bookkeeping | Always-on bookkeeping |
| **D. AI trust / defensibility** | "why not ChatGPT", hallucination, accuracy, grounding | Verification harness |
| **E. Platform / distribution** | partners, embed, API, B2B, reach | Taxfix Embedded |
| **F. Open / "build anything"** | no constraint given | Bescheid-Check — best demo legibility |

## Step 2 — Bind the brief to core assets (this is the whole trick)

Everything in `core/` is brief-agnostic and **already works**. Do not rebuild it.
Pick the modules the brief touches and say what each buys you:

| Module | What it is | Use it when the brief involves |
|---|---|---|
| `core/pap/engine.py` | The BMF's federal wage-tax algorithm, executed. 14/14 conformance tests. | any euro figure, any "is this right", any refund/liability number |
| `core/law/cite.py` | EStG/UStG/AO/StBerG full text, 1,059 paragraphs, citation resolver + hallucination audit | any claim, explanation, advice, or LLM output |
| `core/einvoice/extract.py` | ZUGFeRD/XRechnung parser, ground truth embedded in the file | receipts, invoices, documents, VAT, bookkeeping |
| `core/harness/harness.py` | Oracle/cases/metric/pass-bar runner, reports silent errors separately | **always — this prints the number you say on stage** |

**The line that wins the room, adapted to the brief:**
> "We didn't start from zero. We brought the Bundesfinanzministerium's own tax
> algorithm and the full statute, so every number we show you is checkable."

## Step 3 — Rewrite the five-part protocol

Fill these in *for the actual brief*, and declare the pass bar before building.
Never skip this; it is the difference between a demo and a proof.

- **oracle** — where truth comes from and why it is independent of us
- **cases** — 15–40, including at least 3 adversarial, built to break us
- **metric** — one number a tired judge can hold
- **pass bar** — declared now, not after seeing results
- **failure mode** — what wrong looks like, demoed live

Encode it as a `Suite` in `core/harness/harness.py`. If the brief has no
natural oracle (a pure design or strategy brief), say so plainly and substitute
an integration or cold-user measurement — see idea 05 in `docs/PLAYBOOK.md`.

## Step 4 — Emit the plan

Produce exactly these, in this order, and nothing else:

1. **Bucket + rotation**, one sentence.
2. **What we keep** — the core modules, already working.
3. **What we build** — the thin surface on top. Scope it to ~90 minutes of work,
   not 135. Leave 45 for validation and rehearsal.
4. **The five-part protocol**, filled in.
5. **Minute-by-minute plan** for the time actually remaining. Ask what time it
   is if you do not know; assume demos at 21:15 and a 20:30 feature freeze.
6. **Three-way split** for the pod: demo path / data+validation / narrative.
7. **The jury defence** — opening line quoting the brief back at them, the one
   number, and three likely objections with answers. Pull the company facts from
   `docs/DOSSIER.md` so the opening line is specific to Taxfix, not generic.

## Step 5 — Then build

Start immediately with the demo path end to end on fake-but-real-shaped data,
then deepen. A thin thing that runs beats a deep thing that doesn't.

## Non-negotiables

- **Decimal, never float,** for money. The BMF says so and float drift silently
  breaks a cent-exact claim on stage.
- **Report silent errors separately from over-escalation.** Over-escalating costs
  minutes; a wrong auto-decision gets filed with the Finanzamt. Never blend them
  into one accuracy score.
- **Include the adversarial case in the demo.** Showing the system correctly
  *refusing* is worth more than three extra features — it is, word for word,
  Taxfix's own stated definition of excellence.
- **Say what is synthetic.** A stated limitation beats a quiet one every time.
- **Never invent a validation number.** If the suite has not run, say it has not run.
- Stop building at the freeze time even if something is unfinished.
