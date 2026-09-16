# The seven candidate surfaces

Full validation protocols and jury defences: `Taxfix-Validation-Playbook.pdf`
(12 pages, one per idea). Condensed here for the `brownie` rotation.

| # | Surface | Oracle | Buildable | Demo | Verdict |
|---|---|---|---|---|---|
| 01 | Expert co-pilot | constructed | yes | medium | take if brief is internal tooling |
| **02** | **Bescheid-Check** | constructed, exact + PAP recompute | yes | **very high** | **default pick — BUILT** |
| 03 | Finanzamt correspondence agent | constructed | yes | high | strong, close second |
| **04** | **Self-employed bookkeeping** | **embedded in the file** | tight | medium | **best oracle of all** |
| 05 | Embedded SDK | none — integration | yes | medium | strategy swing, risky |
| 06 | ChatGPT verification harness | EStG XML | yes | high | on-thesis, needs prep |
| **07** | **Günstigerprüfung** | **the federal algorithm** | yes | medium | **unbeatable proof** |

## Why 02 is the default
Legible in three minutes to a non-tax judge with zero setup. A named, published
gap you can quote from Finanztip. And the Bescheid arrives 6–12 weeks after
filing — a calendar-guaranteed re-engagement moment on a once-a-year product,
which is Taxfix's actual structural problem.

Built on 07's engine, so the demo is **not circular**: we independently recompute
from the BMF's own algorithm rather than only catching errors we injected.

## The two failure classes — say this out loud
| Failure | Cost | Behaviour |
|---|---|---|
| Over-escalation | low, wasted minutes | acceptable, tune toward it |
| **Silent error** | **severe — filed, legal** | **must be zero** |

## The three minutes
- 0:00–0:25 the pain, quoted from their own review/scorecard/job ad
- 0:25–1:30 the thing working, live, on a real German tax document
- 1:30–1:55 **the catch** — the adversarial case, correctly refused
- 1:55–2:30 the proof — oracle, test set size, one number
- 2:30–3:00 what you didn't build and why. Then stop.
