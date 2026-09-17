# Taxfix Cursor Hackathon — project instructions

Cursor Hackathon Berlin, hosted at Taxfix SE, Köpenicker Str. 122, 17 Sep 2026.
Challenge announced 19:00, demos 21:15, awards 21:40. Teams of 3+.
Prizes €500 / €300 / €100 per person.

## The trigger word: `brownie`

When the user says **brownie** — with or without a pasted brief — invoke the
`brownie` skill immediately. That is the moment the real Taxfix challenge has
been announced and the build must rotate onto it.

`brownie` + the problem statement → the brief is written to `docs/BRIEF.md`,
then a **fit assessment**, then either a rotation or a pivot, with the validation
protocol, jury defence and minute-by-minute plan. Do not brainstorm; the thinking
is already in `docs/`.

If `brownie` arrives with no brief text, ask one question — *"What did they
announce?"* — and wait. Never guess the brief.

**The spine is allowed to be wrong.** This is a *Cursor* hackathon hosted at
Taxfix, not a Taxfix hackathon — the prior edition floated themes like
design-to-code that never touch the host's domain. If the brief doesn't fit,
`brownie` must say so and send the user to `docs/PIVOT.md` rather than shoehorn
a tax engine into it. Dropping the prep is the strong move, not the weak one —
and it has to be decided in the first ten minutes.

## Why this repo exists

Every team in that room will demo something that looks right in 135 minutes.
Taxfix's own job ads say excellence is *"knowing when the AI output is wrong
even when it looks right."* So the differentiator is not the build. It is the
**oracle** — an independent source of truth we can check ourselves against,
live, on stage.

This repo pre-loads the oracles so that tomorrow is spent on the surface.

## Layout

```
core/       brief-agnostic, already working, do not rebuild
  pap/      the BMF federal wage-tax algorithm, executed  (14/14 tests)
  law/      EStG + UStG + AO + StBerG, 1,059 paragraphs, citation resolver
  einvoice/ ZUGFeRD/XRechnung parser — ground truth embedded in the file
  harness/  oracle → cases → metric → pass bar → the number you say on stage
build/      the surface. bescheid/ is the default bet; brownie may rotate it
data/       the corpus (statutes, PAP XML, invoice fixtures, BMF templates)
docs/       BRIEF (filled at 19:00), ROTATION (fit gate + matrix),
            PIVOT (greenfield path), DOSSIER (company), PLAYBOOK (7 ideas)
tests/      conformance
```

## Status at 19:20 on the day

Brief announced and written to `docs/BRIEF.md`. Verdict ROTATE. Surface is
`build/yearround/` (position + Q4 moves + MCP server + November screen). Pitch
video upload is a **hard 21:00 deadline**; presentation is 2 minutes.
Script in `docs/PITCH.md`, plan in `docs/PLAN.md`.

## Commands

```bash
python3 build/yearround/demo.py --stage    # the demo path (2 min)
python3 build/yearround/demo.py            # 31-case validation, prints the number
python3 tests/test_yearround.py            # properties + pass bar
python3 build/yearround/screen.py          # November screen -> out/november.html
python3 tests/test_pap.py                  # 14 structural conformance checks
python3 build/bescheid/demo.py             # 40-case validation, prints the number
python3 build/bescheid/demo.py --stage     # the 3-minute demo path
python3 core/einvoice/extract.py           # invoice corpus, cent reconciliation
python3 core/law/cite.py "<text>"          # hallucination audit on any text
python3 core/pap/engine.py 60000 1         # federal wage tax, gross + Steuerklasse
```

No dependencies. Python 3 standard library only — do not lose hackathon minutes
to pip. Keep it that way.

## Non-negotiables

- **`Decimal`, never `float`, for money.** The BMF says so explicitly, and float
  drift silently breaks a cent-exact claim on stage. This is the single easiest
  way to lose.
- **Report silent errors separately from over-escalation.** Over-escalating costs
  minutes. A wrong auto-decision gets filed with the Finanzamt and becomes a
  legal problem. Never blend them into one accuracy score.
- **Declare the pass bar before running the suite**, not after seeing results.
- **Put the adversarial case in the demo.** Showing the system correctly
  *refusing* is worth more than three extra features.
- **Say what is synthetic.** A stated limitation beats a quiet one.
- **Never invent a validation number.** If the suite has not run, say so.
- **Never shoehorn.** If the spine doesn't fit the brief, say so and pivot.
- Nothing in `core/` asserts a tax position without a human in the loop. That is
  the §StBerG line and the answer to "who owns the liability when it's wrong".

## Facts worth having ready

- Taxfix: ~400 staff, 10M+ returns, €5bn+ refunded, unicorn 2022, no round since.
- Revenue €55.9m (2023) → €67.3m (2024). Loss €58.1m → €48.7m → €19.4m. Steering at breakeven.
- Finanztip 2026: WISO 9.53, **Check24 9.49 and free**, … **Taxfix 8.3 at €49.99**, sixth.
- Finanztip names the gaps: imperfect calculation, no Günstigerprüfung for
  married couples, blocked above the Kleinunternehmer threshold, and checking
  your Bescheid is "only possible in a limited way, or expensively."
- Loudest review complaint: support ends when the Finanzamt writes back.
- ChatGPT tax queries +300% in Q1 2026. The state's auto-filled return went live
  for a first group mid-2026.

Full detail in `docs/DOSSIER.md`.
