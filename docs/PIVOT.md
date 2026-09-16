# The pivot playbook

For when the brief does not fit the spine.

This document exists because the honest answer to "will our pre-built tax engine
help tomorrow?" is **probably, but not certainly.** This is a Cursor hackathon
hosted at Taxfix, not a Taxfix hackathon. The previous edition at Bliq floated
themes like *design-to-code workflows* and *AI-native workflows for product and
engineering teams* — neither of which touches the host's domain at all.

If that happens, the worst outcome is forcing a tax engine into a brief that
doesn't want one. Judges notice. **Drop it and say you dropped it.**

## Recognising a pivot

You are in pivot territory when any of these is true:

- The brief never mentions tax, filing, money, documents, or compliance
- The brief is about **Cursor itself** — AI-native development, agent workflows,
  design-to-code, developer productivity
- The brief is about Taxfix's **marketing, brand, hiring, or internal people ops**
  rather than the product
- The brief explicitly constrains you away from the domain ("don't build a
  tax calculator", "anything except…")
- The brief hands you **their own dataset or API** and expects you to use it —
  in which case their data beats your data, always

One-sentence test: *if I deleted `core/`, would the build get meaningfully
harder?* If no, pivot. Keep only `core/harness/` — validation doctrine is
domain-independent and still wins you the proof.

## What survives a pivot

You lose the tax engine. You keep four things, and they are worth more than
people think:

| Asset | Why it still wins |
|---|---|
| **`core/harness/`** | Oracle → cases → metric → pass bar works in any domain. Most teams will show a demo; you show a measured claim. |
| **The 25% principle** | Taxfix's own words: excellence is knowing when the AI output is wrong even when it looks right. True of every brief. |
| **The company research** | `docs/DOSSIER.md` still supplies an opening line that proves you did homework, even for an off-domain brief. |
| **Pod discipline + clock** | Demo path / data+validation / narrative. Feature freeze 20:30. Rehearse twice. |

## Greenfield in 135 minutes

### Minutes 0–10: pick the target, then stop picking
Write one sentence: **"For [who], when [moment], we [do what], measured by [number]."**
If you cannot fill all four blanks, the idea is too vague — pick another. Do not
spend more than ten minutes here; a decent idea executed beats a great idea
half-built.

Bias toward: a moment that is **emotionally legible in ten seconds**, and a
**failure the system can catch on stage**.

### Minutes 10–20: find the oracle before you write code
This is the step everyone skips and it is the whole game. In an unfamiliar
domain, oracles hide in these places, best first:

1. **A reference implementation someone official publishes** — a spec, a
   validator, a conformance suite, a government or standards-body tool.
2. **Ground truth embedded in the artefact** — file formats that carry both a
   human view and a machine view (like ZUGFeRD did for us).
3. **A round trip** — generate → process → regenerate, and diff. Works when
   nothing external exists. Encode → decode must return the original.
4. **A property that must hold** — monotonic, conserved, idempotent, sums to a
   known total. Property tests are real validation and take minutes to write.
5. **A set you construct** — you know the answer because you built the case.
   Weakest, but honest. Say it is constructed.

If you genuinely cannot find one, measure something else honestly — time to
first success, lines of integration code, cold-user completion rate — and say
out loud that correctness was not the question.

### Minutes 20–100: build the demo path end to end, then deepen
Thin and running beats deep and broken. Get the full click sequence working on
fake-but-real-shaped data first, then improve the middle.

### Minutes 100–115: run the suite, get the real number
Declare the pass bar **before** you look at results. Include at least three
adversarial cases designed to break your own system.

### Minutes 115–135: freeze, rehearse twice, record a fallback
More demos die on a live API call than on a missing feature.

## The pivot opening line

Do not hide the pivot. Own it — it reads as judgment, not failure:

> "We came in with a German tax engine built on the BMF's own algorithm. Your
> brief wasn't about tax, so we left it at the door and built this instead."

That sentence does two jobs: it proves you prepared seriously, and it proves you
can read a room and drop sunk cost. Both are things Taxfix says it hires for.

## Anti-patterns

- **Shoehorning.** Bolting the tax engine onto an unrelated brief to justify the
  prep. Judges see it immediately and it costs more than it buys.
- **Pivoting late.** Decide in the first ten minutes. A pivot at 20:00 is a loss.
- **Pivoting because the brief is hard.** Difficulty is not misfit. Only pivot on
  genuine domain mismatch.
- **Dropping the harness.** The validation doctrine is the one thing that
  transfers to literally any brief. Keep it.
- **Abandoning the research.** Even off-domain, knowing Taxfix is sixth in
  Finanztip at the highest price, or that their job ads name Cursor, lets you
  frame the work in their language.

## If the brief hands you their data

Use theirs, not ours. A team building on the host's own dataset or API is
always more credible than a team building on something they brought. Keep
`core/harness/` to prove the result, and treat their data as the oracle's
source where you can.
