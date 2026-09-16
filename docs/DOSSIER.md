# Taxfix — the facts you need on stage

Compiled 16 Sep 2026 from public sources. Full research: the dossier artifact
and `Taxfix-Validation-Playbook.pdf`.

## Mission
"Fix finance for all." Founded 2016, Berlin, by Lino Teuteberg and Mathis Büchi.
Threw away the form and replaced it with a plain-language questionnaire. They see
themselves as a consumer finance company that starts at tax — not a tax tool.

## Scale
10M+ returns filed · €5bn+ refunded · ~400 staff · DE/ES/UK/IT
Brands: Taxfix, Steuerbot (acq. 2023), TaxScouts→Taxfix UK (acq. 2024, rebranded 2025)

## Money
| Year | Revenue | Loss |
|---|---|---|
| 2022 | — | €58.1m |
| 2023 | €55.9m (+45%) | €48.7m |
| 2024 | €67.3m (+20%) | €19.4m |

Burn down two thirds, growth halved. Steering hard at breakeven. Unicorn Apr 2022
($220m Series D, Ontario Teachers' / Index / Valar / Creandum). No round since.

Pricing DE: free estimate → Basic €39.99–49.99 → Expert 20% of refund, min €99.99
→ self-employed €19.99/mo net (launched Mar 2026) → Instant Refund (they front 50%).

## Who's in the room
| Person | Role | Hired to fix | Pitch them |
|---|---|---|---|
| Martin Ott | CEO since 2021, ex-Meta | survival + "AI first" | defensibility |
| Snir Yarom | CTO since 2024, ex-Zalando | AI-native R&D, R&D productivity | leverage per engineer |
| Kristen Waeber | CPO since 2025, ex-N26 | the funnel: onboarding, activation | drop-off, trust |
| Markus Berger-de León | COO since 2025 | UK/EU growth | repeatable across markets |
| Mohamed Omaizat | CFO | M&A, revenue model | margin, recurring revenue |

## The three-front squeeze
1. **ChatGPT** — tax queries +300% in Q1 2026 (OpenAI). Guided simplicity is now free.
2. **Check24 Steuer** — scored 9.49 in Finanztip 2026, second overall, **completely free**.
3. **The German state** — auto pre-filled mobile return, sign-ups opened 31 Mar 2026,
   first nationwide group mid-2026. The tax office is building their core use case.

## Finanztip 2026 ranking
WISO 9.53 (€45.99, has SteuerGPT) · Check24 9.49 (free) · Smartsteuer 9.0 (€39.99)
· SteuerGo 8.6 · Lohnsteuer kompakt 8.6 · **Taxfix 8.3 (€49.99)** · Steuerbot 8.1

**Taxfix is sixth, at the highest price in the field.**

## Named product gaps (quotable)
- Calculation "not perfect" at the edges
- **No Günstigerprüfung for married couples** (joint vs separate assessment)
- Blocked above the €25k Kleinunternehmer threshold
- **Checking your Steuerbescheid "only possible in a limited way, or expensively"**
- Loudest review complaint: support ends when the Finanzamt writes back
- Users told at the very end that they owe money

## Operational bottleneck
Expert Service needs licensed Steuerberater. Germany can't supply them: 72% of
tax firms report unfillable roles, >50% of advisors are 50+, and 2026 is the first
year more Germans retire than enter the workforce (1.1m out vs 780k in).
**They cannot hire their way out. Only productivity works.**

## The Builder model — their own words
R&D reorganising around "Builders": a primary craft, stretching across product,
design and engineering, using AI to cover gaps, in **pods of 2–3**, *"accountable
to outcomes, not job descriptions."* Job ads name **Claude, Cursor, Lovable**.

> "It's easier than ever to get software to 75%. Excellence lives in the
> remaining 25% — and in knowing when the AI output is wrong even when it
> looks right."
> — Taxfix, AI First Builder (Design), 2026

**That sentence is the judging criterion.** Internally: ~90% of marketing assets
AI-generated, weekly company-wide AI training days, regular internal AI hackathons.

## Stack
React Native single mobile codebase · Node.js + Go microservices · Pub/Sub on GCP
· migrated off a monolith · ELSTER API for submission · Belegabruf pre-fill support.
