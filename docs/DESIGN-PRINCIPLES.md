# Design principles — carried over from FollowCam (CODE, 28 Aug 2026) and Ember

Pulled from `code hackathon project/pitch/*.md`, `IDEA.md`, and the SCIO/Ember
spec. Each principle, and what it means for tonight.

| # | FollowCam principle | Tonight |
|---|---|---|
| 1 | **Demo first, cold open, no slides.** "Don't look at me — look at the tripod." | Open on the phone/Simulator home screen. Say nothing for 5 s. Then: "That's the Taxfix home screen. That card wasn't there this morning." |
| 2 | **One number, one comparison.** €20 vs €2,000. | 80 € today → 785 € after four moves. And: 49 days, § 11 EStG, not ours. |
| 3 | **Retrofit what they already own.** Don't sell a camera; clamp the tripod. | One card on the existing home screen, in their row idiom, their refund pill. No new tab, no new screen, no pipeline change (`build/yearround/integration/INTEGRATION.md`). |
| 4 | **The video is just the input; the data layer is the moat.** | The number is the input; the *moves* and the *refusals* are the value. Every tap in November is an answer they don't give in April → data quality (their word). |
| 5 | **Measured numbers, not vibes.** Human-eval harness in the repo. | 31/31 exact, 0 silent errors, 13/13 refusals held, pass bar declared before the run. Say it as run, never rounded up. |
| 6 | **Honest build story.** The servo pocket didn't fit; every fix is a commit. | Say what's synthetic (the profile), what stands in (wage-tax PAP for the annual tariff), what we dropped (e-invoice, Bescheid surface). |
| 7 | **Fallback degradation ladder** A → B → C → D, decided before the demo. | See below. |
| 8 | **Q&A ammo written before the stage.** | `docs/PITCH.md`, three objections + `docs/PLAN.md` jury defence. |
| 9 | **Ember:** get a person to say something true they hadn't put into words. | The brief's "emotional outcome": the screen makes someone feel *a little bit clever* — the laptop that unlocks the home-office days — not dutiful. |

## Fallback ladder for the demo (decide now, not at 21:09)

| Tier | Demo path | Trigger to drop a tier |
|---|---|---|
| **A** | iOS Simulator, Safari, `http://127.0.0.1:8787/` — their home screen with the live card, before/after toggle. Cursor agent calling `q4_plan` over MCP on the side. | Simulator or server hiccups |
| **B** | The published artifact page (phone frame + narrative), already recorded in the video. | No network |
| **C** | Terminal: `python3 build/yearround/demo.py --stage`. Always works, no deps. | — |
| **D** | The screenshot in `build/yearround/out/` and the numbers said out loud. | Laptop dies |

Record the video on tier A with tier C as the proof shot. Never improvise a number.

## The recruit line (if anyone asks what you built)
"We put one card on Taxfix's home screen that is true all year: what your return
is worth today, on the Finanzministerium's own algorithm, and the three moves
before 31 December that change it — including the ones it refuses to price."
