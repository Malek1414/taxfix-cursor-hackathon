# Integration into the Taxfix app — without touching their layout or pipeline

Source of truth for the current app: the App Store listing (id 1163776422,
v4.1.0, 4.8★ / 270k ratings), screenshots in `reference/`, and the web app at
app.taxfix.de. Stack per `docs/DOSSIER.md`: React Native single codebase,
Node.js + Go microservices on GCP, ELSTER for submission, Belegabruf pre-fill.

## What the app is today — from the 3:11 screen recording of iOS 4.1.0 (reference/live/)

Verified against the live app on 17 Sep 2026, not the store screenshots:
- **Two tabs only: Taxes, Account.** No feed, no home beyond the current return.
- **"Your tax returns"** lists 2025 (Continue · With tax advisor), 2024, 2023, 2022
  (Start). **There is no 2026.** That empty slot is the integration point.
- **"Tax year 2025"** is section rows (About you 30 % completed, Job, Self-employed,
  Renting, Income, Children, Education, Expenses, Personal details, Additional
  Documents) with a sticky **Next · About you · Continue** card and a **Help** pill
  carrying three advisor avatars.
- Data is collected through **lime question cards + Confirm**; answered items
  collapse into key/value rows ("Married · No ›").
- A refusal pattern exists: **"Sorry, we can't help you this time"** with the
  toolbox illustration.
- Onboarding asks for push permission ("Want to know when your tax assessment
  is ready?") — the one notification the brief calls theatre.

`simulator.html` now reproduces this exactly: the year chooser with a 2026
card, "Tax year 2026" in the section-row idiom, a move as a question card that
writes into Expenses, and the refusal in their pattern.

## What the store screenshots showed (reference/*.png, older German build)

```
┌──────────────────────────────┐
│ ←                      🎁 👤 │   header: back, referral, profile
│ Steuerjahr 2025              │   ONE tax year, ONE job: finish the return
│ ┌──────────────────────────┐ │
│ │ Dein Fortschritt ━━━━━━  │ │   progress card
│ └──────────────────────────┘ │
│ 👋 Über dich            ✓ › │   category rows: icon tile · label · status · chevron
│ 💼 Arbeit                 › │
│ 🧾 Ausgaben  57 % erledigt ◔ › │
│ 🪪 Persönliche Daten     ✓ › │
│ ┌──────────────────────────┐ │
│ │ Als nächstes   Arbeit  [Weiter] │   sticky next-step footer
└──────────────────────────────┘
```
Inside the questionnaire (reference/3.png) there is already a **live refund
pill** in the header: `1.172 € ⌄`. It exists only while you answer questions
for the past year, and disappears once you file.

## The friction, precisely

| Moment | What the user sees today | Why they close the app |
|---|---|---|
| Filed in May | "Steuerjahr 2025 ✓" — nothing left to do | The home screen has no job until next year |
| July, Bescheid arrives | Nothing (loudest review complaint) | The app is silent when the Finanzamt speaks |
| November, invoice due | Nothing | No reason to open it; the value only exists in April |
| Any month, life changes | Nothing | The refund pill is filing-only |

The brief names all of this: "once-a-year panic button", "value must exist
outside tax season", "improve data quality".

## The integration: one card, their idiom, zero new navigation

Insert **one card** on the existing home screen, above the category rows, for
the *current* tax year. It reuses three things the app already has:

1. The **refund pill** (`1.172 €`) becomes "Wenn du heute abgibst: 80 €", always on.
2. The **category-row** component renders the moves: icon tile, label, euro chip, chevron.
3. The **sticky footer** ("Als nächstes … Weiter") points at the best move.

Tapping a move opens the *existing* "Ausgaben" question for that item
(Handwerkerleistungen, Arbeitsmittel, Homeoffice-Tage, Spenden) — pre-filled for
the 2026 return. So every tap in November is an answer they don't have to give
in April. That is the "improve data quality" line from the brief, for free.

```
┌──────────────────────────────┐
│ Steuerjahr 2025          ✓   │   untouched
│ ┌──────────────────────────┐ │
│ │ STEUERJAHR 2026 · STAND HEUTE│ │   NEW — one card
│ │ Wenn du heute abgibst  80 € │ │   the refund pill, year-round
│ │ 49 Tage bis 31.12.          │ │
│ │ 🔌 Elektriker bezahlen +420 € › │   their row component
│ │ 💻 Laptop            +178 € › │
│ │ 🏠 30 Homeoffice-Tage +49 € › │
│ │ ⚠ Gärtner bar bezahlt   0 € › │   refusals shown as rows too
│ └──────────────────────────┘ │
│ Als nächstes  Elektriker  [Weiter] │   existing footer, new target
└──────────────────────────────┘
```

## What we do not touch
- No new tab, no new screen, no new navigation stack.
- No change to the questionnaire, the ELSTER submission, or Belegabruf.
- No writes from the service. The card is a read model; taps write through the
  existing "Ausgaben" answers exactly as the user would in April.
- No push notifications. The card is there when they open the app; that's it.

## Service contract (`../api.py`, localhost:8787 — one more read-only microservice)

| Route | In | Out |
|---|---|---|
| `GET /v1/demo/card` | — | the card payload below, demo profile |
| `POST /v1/card` | `{profile, candidates}` | same, real profile |
| `POST /v1/moves/price` | `{profile, candidate}` | one priced move |
| `POST /v1/audit` | `{text}` | citation audit for any expert/LLM text |

Card payload (`schema: taxfix.yearround.card/1`):
```json
{"headline": {"amountEur": "80.00", "label": "If you filed today"},
 "deadline": {"date": "2026-12-31", "daysLeft": 49, "basis": "§ 11 Abs. 2 EStG"},
 "afterPlan": {"amountEur": "785.00", "deltaEur": "705.00"},
 "moves": [{"label": "…", "status": "worth|zero|escalate", "saving_eur": "420.00",
            "citation": "§ 35a EStG", "citation_resolves": true, "why": "…", "kind": "handwerker"}]}
```
Where the profile comes from in production: the answers already given for the
previous return (gross, Steuerklasse), Belegabruf, and anything logged since.
Money stays `Decimal` server-side and is serialised as strings; the client
never does arithmetic.

## Run the integration locally
```bash
python3 build/yearround/api.py               # service on :8787
open http://127.0.0.1:8787/                  # their home screen, with the card, live
# or on the iOS Simulator:
xcrun simctl boot "iPhone 17" && open -a Simulator && xcrun simctl openurl booted http://127.0.0.1:8787/
```
`PositionCard.tsx` is the React Native component in their idiom; `simulator.html`
is the same card rendered into a mock of their home screen for the demo, with a
before/after toggle to show the layout is untouched.
