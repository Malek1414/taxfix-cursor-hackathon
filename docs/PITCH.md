# The two minutes — pitch video (upload by 21:00) and live presentation (21:10)

Record the screen (`build/yearround/out/november.html` + the terminal) with voice.
Say the numbers exactly as the suite printed them. Do not improvise a figure.

## 0:00–0:20 — cold open on their home screen (FollowCam rule: demo first)
Screen: the Simulator at `http://127.0.0.1:8787/` — Taxfix's home screen, the
"Steuerjahr 2025 ✓" card, and our card under it. Five seconds of silence, then:
> "That's the Taxfix home screen after you've filed. Normally it's done until
> April. That card wasn't there this morning: if you filed today you'd get
> **80 euros** back — on the Bundesfinanzministerium's own algorithm — and there
> are 49 days to change that. 31 December is § 11 EStG's deadline, not ours."
Tap **Heute (ohne Karte)** then **Mit Karte** once: "We changed nothing else.
Their rows, their pill, their footer."

## 0:20–1:00 — the moves (screen: the four green cards)
> "Four things are on the table. The Elektriker's bill is due in January — pay
> the labour share in December by bank transfer and **420 euros** come straight
> off your tax, § 35a. The laptop is worth **178**, and here's the clever part:
> it carries you over the 1,230-euro Pauschbetrag, so the 30 home-office days you
> never bothered logging suddenly become worth **49**. The donation, 58.
> 80 euros becomes **785**. Every figure is a recompute on two states, to the cent."

## 1:00–1:30 — the catch (screen: the amber cards)
> "And this is the part that is Taxfix, not ChatGPT. The gardener you paid cash:
> **zero**, and we say why — § 35a only counts transfers. The tip that says
> 'deduct the materials, § 35b': the paragraph exists — it's about inheritance
> tax — so we refuse to show it. 'Get married before the 31st': a human prices
> that, not an algorithm. The refusals are on the screen. That's the trust."

## 1:30–1:50 — the proof and the orchestration (terminal)
> "31 cases, hand-computed against the federal Programmablaufplan and the statute
> text: 100 % exact, zero silent errors, 13 of 13 adversarial refusals held.
> The engine is an MCP server — Cursor's agent calls `q4_plan` and can only show
> what the engine priced and the statute resolved. LLM drafts, engine prices,
> statute audits."

## 1:50–2:00 — what's synthetic, then stop
> "The profile is synthetic. The wage-tax algorithm stands in for the annual
> assessment. Nothing here files anything. That's the year-round loop: not a
> reminder — a number that's wrong the moment your life changes and you haven't
> told it."

## Three objections, one line each
- *Just a refund estimator?* — Estimators are filing-season. This is a quantity that moves in July, in November, whenever your life does, and in Q4 it becomes decisions with a real deadline.
- *Fake urgency?* — 31 December is the statute's. We show €0 moves as €0 and say why.
- *Why not ChatGPT?* — Beat 3. Tax queries to ChatGPT are up 300 %; the value is knowing when the output is wrong even when it looks right. Their own job ad says so.

## Fallback ladder (docs/DESIGN-PRINCIPLES.md)
A Simulator + live server → B artifact page → C `demo.py --stage` → D screenshot + numbers.

## Commands on camera
```
python3 build/yearround/api.py & xcrun simctl openurl booted http://127.0.0.1:8787/
python3 build/yearround/demo.py --stage
python3 build/yearround/demo.py
open build/yearround/out/november.html
```
Cursor: Settings → MCP → the `taxfix-yearround` server from `.cursor/mcp.json` →
in the agent chat: "Call q4_plan with no arguments and summarise the refusals."
