# brownie plan — 17 Sep 2026, 19:05

Read `docs/BRIEF.md` first. **Pitch video upload is a hard 21:00 deadline.**
Presentation is 2 minutes, not 3. Freeze 20:15. Record 20:30–20:45. Upload by 20:55.

## 1. Verdict
**ROTATE.** The brief is on-domain (bucket A, "value outside filing season"):
every year-round move is a euro claim that must be right and a statute the user
can check, so `pap/` and `law/` bind directly. Only the surface changes.

## 2. Keep / drop
- **Keep:** `core/pap` (tariff recompute), `core/law` (citation audit), `core/harness`.
- **Drop:** `build/bescheid` as the demo surface — it is once-a-year, not recurring.
  It survives as one line in the pitch ("the Bescheid also arrives in July").
  `core/einvoice` dropped unless there is time after 20:00.

## 3. What we build — `build/yearround/`  (~85 min)
**"Your tax position, live."** A number that is true all year and a ranked list
of moves for Q4, each with a cent-exact saving from the BMF algorithm and a
statute citation that resolves — and each move the engine *can't* price gets
refused to a human, out loud.

The loop, in the brief's own words: not a reminder, a quantity. Every receipt,
home-office day, donation or Handwerker invoice moves the number. November is
the month the moves are worth the most, because 31 December is a *statutory*
deadline (§ 11 Abs. 2 EStG, Abflussprinzip), not a manufactured one.

Files:
- `moves.py`   — Profile → Position; Candidate → Move (worth / zero / escalate)
- `demo.py`    — `validate()` suite + `--stage` three-minute path
- `mcp_server.py` + `.cursor/mcp.json` — stdio MCP server: Cursor calls the engine
- `screen.py`  — renders the November screen to HTML (the thing the jury sees)
- `tests/test_yearround.py`

## 4. The five-part protocol (declared before building)
- **oracle** — the BMF Programmablaufplan for the tariff (independent of us);
  statutory thresholds/caps written by hand from the statute text and
  cross-checked by `core/law` resolving the cited paragraph. Suite cases compute
  taxable income *by hand* in the test, never via the engine's own helper.
- **cases** — 30+: 12 priced moves, 6 threshold/cap cases, 6 properties
  (monotonic, non-negative, cap), 8 adversarial (below-Pauschbetrag laptop,
  cash-paid Handwerker, maxed § 35a, hallucinated citation, marriage/Riester
  that need a human).
- **metric** — euro claims cent-exact vs. independent recompute, with silent
  errors and over-escalations reported separately.
- **pass bar** — 100% of shown euro figures exact; 0 silent errors; every
  adversarial refusal held; over-escalation ≤ 20%.
- **failure mode** — a move shown with a wrong euro value, or a move shown
  that should have been refused. Demoed live in beat 3.

## 5. Minute-by-minute
| Time | Do |
|---|---|
| 19:05–19:25 | `moves.py`: profile, position, candidates, thresholds, refusals |
| 19:25–19:45 | `demo.py validate()` — suite + first real number; `--stage` |
| 19:45–20:05 | `mcp_server.py` + `.cursor/mcp.json`; call it from Cursor |
| 20:05–20:15 | `screen.py` November screen; tests; docs |
| 20:15 | **freeze.** run everything once more, screenshot the screen + the number |
| 20:15–20:30 | write the 2-minute script; one dry run against the clock |
| 20:30–20:45 | **record the pitch video** (screen + voice; the number and the refusal on camera) |
| 20:45–20:55 | **upload** — hard deadline 21:00; do not cut it fine |
| 21:10 | 2-minute live presentation: the number, the refusal, the MCP call |

## 6. Pod split (3 people)
- **Demo path** — `--stage` and the November screen; owns the laptop on stage.
- **Data + validation** — suite cases, hand-computed oracles, the number.
- **Narrative** — three-minute script, jury defence, Cursor/MCP live call.

## 7. Jury defence
**Opening:** "You said: genuine value that makes someone open the app in
November because they want to. Here is what Taxfix knows in November that
nobody else does: what your return is worth *today*, and which three moves
before 31 December change it — to the cent, on the Bundesfinanzministerium's own
algorithm, with the paragraph you can check."

**The one number:** the suite headline (see `demo.py`), stated as run.

**Two minutes, not three:** 0:00–0:20 the brief quoted back + the number today ·
0:20–1:00 the moves, €80 → €785 · 1:00–1:30 the catch (cash, § 35b, marriage refused) ·
1:30–1:50 the proof number + Cursor calling the MCP server · 1:50–2:00 what's synthetic. Stop.

**Objections:**
1. *"That's just a refund estimator."* — An estimator is filing-season. This is
   a quantity that changes when your life changes, and in Q4 it turns into
   decisions with a real deadline. Finanztip already docks Taxfix for imperfect
   calculation; ours recomputes on the BMF algorithm every time.
2. *"Why won't ChatGPT do this?"* — Beat 3: the tip with the invented paragraph.
   ChatGPT tax queries are up 300%; the value is knowing when the output is
   wrong even when it looks right — Taxfix's own words. We refuse and cite.
3. *"Where's the recurring loop?"* — The number is wrong the moment you don't
   tell it something. That is the pull: a home-office day, a receipt, a donation
   each move it. No streak, no push. And the Bescheid arriving in July is a
   second calendar-guaranteed moment we already handle.
4. *"Isn't this fake urgency?"* — 31 December is § 11 EStG, not our design.
   We show €0 moves as €0 and say why. The system saying "no" is in the demo.

**Say what is synthetic:** profiles are constructed; the tariff is the wage-tax
PAP standing in for the annual assessment; § 35a / § 9a / § 10b caps are coded
from the statute, not from a Finanzamt ruling.
