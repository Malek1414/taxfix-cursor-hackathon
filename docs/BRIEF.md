# The brief

Filled by `brownie` at 19:02 on 17 Sep 2026 from six photos of the announcement
slides (WhatsApp, 18:46–18:47). Everything downstream reads from here.

## Announced
_time:_ 18:40–18:46 (slide timestamps), presented over Google Meet by Jessica
Aguinaga Hill (Taxfix), with two Taxfix hosts on the mic in the room.
_form:_ photos of five slides. No dataset, no API handed out.
_submission:_ **21:00 hard deadline — upload a PITCH VIDEO** (organiser PDF, Drive).
Then 21:10 team presentations, **2 minutes per team**. 22:00 winners. Prizes are
Cursor credits: $500 / $300 / $100 per member.

## Verbatim

```
THE CHALLENGE

Build the feature, flow or experience that creates voluntary, recurring
engagement with Taxfix outside of filing season.

Not reminders. Not nudges. Genuine value that makes someone open the app in
November because they *want* to.

---
TAX DEADLINE
Germany's hard filing deadline. Peak activity compressed into a few frantic
weeks — then silence for the rest of the year.

Users feel anxiety, not engagement. We have a product that could be deeply
valuable 12 months a year — helping optimise taxes and reduce stress — but
right now, it's a once-a-year panic button.

The opportunity
If we shift even a fraction of engagement to a different point in the year, we
reduce user stress, improve data quality, and create a durable loop that makes
Taxfix genuinely sticky.

---
A NOTE ON TONE
Tax is serious. But how we make people feel about it doesn't have to be.
- The best version of this feature makes users feel in control, financially
  savvy, and a little bit clever — not dutiful, anxious, or guilty.
- Design for the emotional outcome, not just the functional one.

Judged on
- Value outside filing season
- Return loop quality
- Taxfix brand fit
- Buzz factor

                       [ Make Taxes Year Around ]

---
WHAT WE DON'T WANT
- No Notification theatre — push alerts with no new value attached.
- No Fake urgency — manufactured deadlines or manipulative streaks.
- No Engagement for its own sake — clicks that don't create genuine value.
- Filing-only features — the value must exist outside tax season.
- Complexity for its own sake — the best engagement mechanics are deceptively
  simple.
Be honest with yourselves about these patterns. Then go build something better.

---
JURY'S CRITERIA FOR SCORING IDEAS
- Innovation (25%) — How original, sharp, and memorable is the idea? Does it
  feel inevitable in hindsight?
- Multi-agent Orchestration (25%) — How effectively did the team use Cursor,
  agents, MCP, SDK, CLI, or AI-native workflows to build faster or create
  something that would be hard to build manually?
- taxfix scope (25%) — How well does the solution answer the Taxfix challenge:
  making users open Taxfix outside filing season, especially around Q4? Strong
  submissions create voluntary recurring value, reduce anxiety, improve tax
  readiness, or help users feel financially clever without relying on empty
  reminders or fake urgency.
- Demo quality (25%) — Is there a clear working prototype or MVP? Can the team
  [show the] problem, solution, and value in 2-3 minutes?
```

## The room
- _judges:_ Taxfix (Jessica Aguinaga Hill presenting remotely; two hosts in the room). Cursor co-hosts.
- _data or API handed out:_ none.
- _constraints said aloud but not on the slide:_ none captured. Q4 is named
  explicitly in the scoring; "November" is the reference month.
- _scored on:_ idea 25 / orchestration 25 / scope 25 / demo 25 — equal weight.
- _source of record:_ 'Cursor Berlin Hackathon at taxfix 17.09.26.pdf' (Drive, owner kaan@designjobs.world):
  agenda 18:00 doors · 18:30 welcome · 18:45 kickoff · **21:00 uploading pitch videos (hard deadline)**
  · 21:10 team presentation (2 min per team) · 22:00 winners & closing.

## Fit assessment

| Question | Applies | Module |
|---|---|---|
| German tax arithmetic — a euro figure whose correctness matters? | **yes** — every "worth €X before 31 Dec" is a euro claim | `core/pap/` |
| Claims, law, explanations, or LLM output that could be wrong? | **yes** — every move carries a statute the user can check | `core/law/` |
| Documents, invoices, receipts, VAT? | partial — Handwerker invoices are the Q4 trigger; parser optional | `core/einvoice/` |
| Anything at all that needs proving? | **yes** — the cent-exact delta and the refusals | `core/harness/` |

**Verdict:** ROTATE
**Why:** Bucket A (consumer, "value outside filing season"). Two of three
domain questions apply hard; only the surface changes — from a Bescheid screen
to a year-round "your tax position, live" screen with concrete Q4 moves.

## Decision
- _keep:_ `core/pap` (tariff recompute), `core/law` (citation audit), `core/harness`
- _drop:_ `build/bescheid` as the demo surface (keep as the "this also arrives
  outside filing season" footnote); `core/einvoice` unless time allows
- _build:_ `build/yearround/` — Year-Round Tax Position + Q4 Moves, an MCP server
  exposing it to Cursor, a November screen, a validation suite.
