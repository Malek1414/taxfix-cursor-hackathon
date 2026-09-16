# Data provenance

Everything here is public and redistributable. Re-fetch with `scripts/fetch_data.sh`.

| Path | Source | Terms |
|---|---|---|
| `law/*.xml.zip` | gesetze-im-internet.de — Bundesamt für Justiz / BMJ | Federal law, published for free use and reuse, XML with a published DTD |
| `truth/Lohnsteuer20*-PAP.xml` | bmf-steuerrechner.de — Bundesministerium der Finanzen | The official wage-tax algorithm, published as XML pseudocode expressly so third parties can reproduce the calculation |
| `forms/Muster-Lohnsteuerbescheinigung-2026.pdf` | BMF-Schreiben, 29 Aug 2025 | Official template, published for use |
| `einvoice/samples/*` | Mustangproject test fixtures | Apache-2.0 |
| `einvoice/xrechnung-testsuite.zip` | KoSIT (itplr-kosit) XRechnung test suite | Apache-2.0 |
| `stats/*.xlsx` | Destatis — Statistisches Bundesamt | Official statistics, free reuse |

No personal data. No Taxfix systems were accessed — all company research is from
published sources (press, filings reported in trade press, public job ads,
public reviews).

The BMF also operates a *live* calculator API. It needs a Zugriffscode with no
self-service signup — email Steuerrechner@bmf.bund.de. This repo does not use it:
`core/pap/engine.py` runs the published algorithm directly.
