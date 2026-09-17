// Bundled fallback so the demo never depends on the network.
let CARD_BEFORE = #"""
{
 "week": {
  "entries": 0,
  "saving_eur": "0.00",
  "vat_eur": "0.00",
  "receipts_missing": 0
 },
 "schema": "taxfix.yearround.card/1",
 "asOf": "2026-11-12",
 "headline": {
  "amountEur": "80.00",
  "label": "If you filed today"
 },
 "deadline": {
  "date": "2026-12-31",
  "daysLeft": 49,
  "basis": "§ 11 Abs. 2 EStG"
 },
 "afterPlan": {
  "amountEur": "785.00",
  "deltaEur": "705.00"
 },
 "moves": [
  {
   "label": "Elektriker — Sicherungskasten, Rechnung 2 900 EUR",
   "status": "worth",
   "saving_eur": "420.00",
   "citation": "§ 35a EStG",
   "citation_resolves": true,
   "why": "pay the labour share by 31.12.2026, not 15.01.2027 by bank transfer — 20 % comes straight off your tax (§ 35a EStG, Abfluss § 11 EStG)",
   "tax_before": "9004.00",
   "tax_after": "8584.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "handwerker",
   "shown": true
  },
  {
   "label": "Laptop für die Arbeit, 899 EUR",
   "status": "worth",
   "saving_eur": "178.00",
   "citation": "§ 9 EStG",
   "citation_resolves": true,
   "why": "this takes you over the 1,230 EUR Pauschbetrag by 655.00 EUR — only that part lowers your taxable income (§ 9, § 9a EStG)",
   "tax_before": "8584.00",
   "tax_after": "8406.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "werbungskosten",
   "shown": true
  },
  {
   "label": "Spende an die Tafel, 250 EUR",
   "status": "worth",
   "saving_eur": "58.00",
   "citation": "§ 10b EStG",
   "citation_resolves": true,
   "why": "deductible as Sonderausgaben, receipt needed above 300 EUR (§ 10b EStG)",
   "tax_before": "8406.00",
   "tax_after": "8348.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "spende",
   "shown": true
  },
  {
   "label": "Home-office days you haven't logged yet (Nov–Dec)",
   "status": "worth",
   "saving_eur": "49.00",
   "citation": "§ 4 EStG",
   "citation_resolves": true,
   "why": "30 more days × 6 EUR (§ 4 Abs. 5 Nr. 6c EStG) — log them, they count as Werbungskosten",
   "tax_before": "8348.00",
   "tax_after": "8299.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "homeoffice",
   "shown": true
  },
  {
   "label": "Gärtner, 600 EUR bar bezahlt",
   "status": "zero",
   "saving_eur": "0.00",
   "citation": "§ 35a EStG",
   "citation_resolves": true,
   "why": "paid in cash — § 35a Abs. 5 EStG only counts bank transfers, so this is worth 0",
   "tax_before": "8299.00",
   "tax_after": "8299.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "handwerker",
   "shown": false
  },
  {
   "label": "ChatGPT tip: 'Materialkosten der Elektrik absetzen (§ 35b EStG)'",
   "status": "escalate",
   "saving_eur": "0.00",
   "citation": "§ 35b EStG",
   "citation_resolves": false,
   "why": "cites § 35b EStG — the paragraph exists but is about 'Steuerermäßigung bei Belastung mit Erbschaftsteuer', not this claim (0/2 claim terms appear in the cited text) — not shown; ask an expert",
   "tax_before": "8299.00",
   "tax_after": "8299.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "werbungskosten",
   "shown": false
  },
  {
   "label": "Heiraten vor dem 31.12. — Ehegattensplitting",
   "status": "escalate",
   "saving_eur": "0.00",
   "citation": "",
   "citation_resolves": false,
   "why": "needs facts the engine does not have (spouse income, contract, holding period) — a human prices this, not an algorithm",
   "tax_before": "8299.00",
   "tax_after": "8299.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "other",
   "shown": false
  }
 ],
 "disclosure": "Recomputed on the BMF Programmablaufplan. Nothing is filed. Moves marked escalate need an expert."
}
"""#
let CARD_AFTER = #"""
{
 "week": {
  "entries": 1,
  "saving_eur": "9.00",
  "vat_eur": "6.13",
  "receipts_missing": 0
 },
 "schema": "taxfix.yearround.card/1",
 "asOf": "2026-11-12",
 "headline": {
  "amountEur": "80.00",
  "label": "If you filed today"
 },
 "deadline": {
  "date": "2026-12-31",
  "daysLeft": 49,
  "basis": "§ 11 Abs. 2 EStG"
 },
 "afterPlan": {
  "amountEur": "794.00",
  "deltaEur": "714.00"
 },
 "moves": [
  {
   "label": "Elektriker — Sicherungskasten, Rechnung 2 900 EUR",
   "status": "worth",
   "saving_eur": "420.00",
   "citation": "§ 35a EStG",
   "citation_resolves": true,
   "why": "pay the labour share by 31.12.2026, not 15.01.2027 by bank transfer — 20 % comes straight off your tax (§ 35a EStG, Abfluss § 11 EStG)",
   "tax_before": "9004.00",
   "tax_after": "8584.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "handwerker",
   "shown": true
  },
  {
   "label": "Laptop für die Arbeit, 899 EUR",
   "status": "worth",
   "saving_eur": "178.00",
   "citation": "§ 9 EStG",
   "citation_resolves": true,
   "why": "this takes you over the 1,230 EUR Pauschbetrag by 655.00 EUR — only that part lowers your taxable income (§ 9, § 9a EStG)",
   "tax_before": "8584.00",
   "tax_after": "8406.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "werbungskosten",
   "shown": true
  },
  {
   "label": "Spende an die Tafel, 250 EUR",
   "status": "worth",
   "saving_eur": "58.00",
   "citation": "§ 10b EStG",
   "citation_resolves": true,
   "why": "deductible as Sonderausgaben, receipt needed above 300 EUR (§ 10b EStG)",
   "tax_before": "8406.00",
   "tax_after": "8348.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "spende",
   "shown": true
  },
  {
   "label": "Home-office days you haven't logged yet (Nov–Dec)",
   "status": "worth",
   "saving_eur": "49.00",
   "citation": "§ 4 EStG",
   "citation_resolves": true,
   "why": "30 more days × 6 EUR (§ 4 Abs. 5 Nr. 6c EStG) — log them, they count as Werbungskosten",
   "tax_before": "8348.00",
   "tax_after": "8299.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "homeoffice",
   "shown": true
  },
  {
   "label": "REWE — 38.40 EUR · receipt ✓",
   "status": "worth",
   "saving_eur": "9.00",
   "citation": "§ 4 EStG",
   "citation_resolves": true,
   "why": "net 32.27 EUR is a Betriebsausgabe in full (§ 4 Abs. 4 EStG); the 6.13 EUR VAT comes back in your next Voranmeldung (§ 15 UStG) — keep the receipt",
   "tax_before": "8299.00",
   "tax_after": "8290.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "6.13",
   "kind": "betriebsausgabe",
   "shown": true
  },
  {
   "label": "Gärtner, 600 EUR bar bezahlt",
   "status": "zero",
   "saving_eur": "0.00",
   "citation": "§ 35a EStG",
   "citation_resolves": true,
   "why": "paid in cash — § 35a Abs. 5 EStG only counts bank transfers, so this is worth 0",
   "tax_before": "8290.00",
   "tax_after": "8290.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "handwerker",
   "shown": false
  },
  {
   "label": "ChatGPT tip: 'Materialkosten der Elektrik absetzen (§ 35b EStG)'",
   "status": "escalate",
   "saving_eur": "0.00",
   "citation": "§ 35b EStG",
   "citation_resolves": false,
   "why": "cites § 35b EStG — the paragraph exists but is about 'Steuerermäßigung bei Belastung mit Erbschaftsteuer', not this claim (0/2 claim terms appear in the cited text) — not shown; ask an expert",
   "tax_before": "8290.00",
   "tax_after": "8290.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "werbungskosten",
   "shown": false
  },
  {
   "label": "Heiraten vor dem 31.12. — Ehegattensplitting",
   "status": "escalate",
   "saving_eur": "0.00",
   "citation": "",
   "citation_resolves": false,
   "why": "needs facts the engine does not have (spouse income, contract, holding period) — a human prices this, not an algorithm",
   "tax_before": "8290.00",
   "tax_after": "8290.00",
   "deadline": "2026-12-31",
   "vat_reclaim_eur": "0.00",
   "kind": "other",
   "shown": false
  }
 ],
 "disclosure": "Recomputed on the BMF Programmablaufplan. Nothing is filed. Moves marked escalate need an expert."
}
"""#
