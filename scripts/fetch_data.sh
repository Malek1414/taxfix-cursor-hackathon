#!/usr/bin/env bash
# Re-fetch the public corpus. Everything here is free, open, and ungated.
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p data/{law,einvoice/samples,truth,forms,stats}
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36'
get(){ curl -sL --max-time 60 -A "$UA" -o "$2" "$1" && [ -s "$2" ] && echo "  ok   $2" || echo "  FAIL $2"; }

# Statutes — Bundesamt für Justiz, free to reuse, published DTD
get https://www.gesetze-im-internet.de/estg/xml.zip      data/law/EStG.xml.zip
get https://www.gesetze-im-internet.de/ustg_1980/xml.zip data/law/UStG.xml.zip
get https://www.gesetze-im-internet.de/ao_1977/xml.zip   data/law/AO.xml.zip
get https://www.gesetze-im-internet.de/stberg/xml.zip    data/law/StBerG.xml.zip

# The federal wage-tax algorithm — ungated, no signup
get https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2026.xml.xhtml data/truth/Lohnsteuer2026-PAP.xml
get https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2025.xml.xhtml data/truth/Lohnsteuer2025-PAP.xml

# E-invoice conformance corpus — KoSIT
get https://projekte.kosit.org/xrechnung/xrechnung-testsuite/-/archive/master/xrechnung-testsuite-master.zip data/einvoice/xrechnung-testsuite.zip

echo
echo "NOTE: the BMF's *live* calculator API needs a Zugriffscode with no"
echo "self-service signup — email Steuerrechner@bmf.bund.de. Not needed:"
echo "core/pap/engine.py runs the published algorithm directly."
