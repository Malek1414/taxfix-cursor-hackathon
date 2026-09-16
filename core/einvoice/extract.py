"""
Pulls the structured invoice out of a ZUGFeRD / Factur-X PDF.

This is the best oracle in the whole corpus. A ZUGFeRD invoice is a hybrid: a
human-readable PDF page with the machine-readable truth embedded inside the same
file as factur-x.xml. So you can run your visual pipeline over the rendered page,
then compare against an answer key you did not write and cannot have leaked into.

Nothing circular, nothing synthetic, nothing to label.

Zero dependencies on purpose — do not lose hackathon minutes to pip.
Corpus: Mustangproject fixtures + the KoSIT XRechnung conformance suite.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "einvoice"


# ---------------------------------------------------------------------------
# PDF: find the embedded XML
# ---------------------------------------------------------------------------

def embedded_xml(pdf: str | Path) -> bytes | None:
    """Return the factur-x / ZUGFeRD XML payload from a hybrid PDF."""
    raw = Path(pdf).read_bytes()
    # (?<!end) matters: "endstream" also contains "stream", and matching it
    # shifts every subsequent offset and silently loses the payload.
    for m in re.finditer(rb"(?<!end)stream", raw):
        start = m.end()
        while start < len(raw) and raw[start] in b"\r\n":
            start += 1
        end = raw.find(b"endstream", start)
        if end == -1:
            continue
        blob = raw[start:end].rstrip(b"\r\n")
        for candidate in (_inflate(blob), blob):
            # Scan the whole payload: ZUGFeRD files often open with a long
            # comment block, pushing the root tag well past any fixed window.
            if candidate and (b"CrossIndustryInvoice" in candidate
                              or b":Invoice" in candidate
                              or b"<Invoice" in candidate):
                return candidate
    return None


def _inflate(b: bytes) -> bytes | None:
    try:
        return zlib.decompress(b)
    except zlib.error:
        try:
            return zlib.decompressobj().decompress(b)
        except zlib.error:
            return None


# ---------------------------------------------------------------------------
# The invoice
# ---------------------------------------------------------------------------

@dataclass
class Line:
    name: str = ""
    qty: Decimal = Decimal(0)
    unit_price: Decimal = Decimal(0)
    net: Decimal = Decimal(0)
    vat_rate: Decimal = Decimal(0)


@dataclass
class Invoice:
    number: str = ""
    date: str = ""
    seller: str = ""
    buyer: str = ""
    currency: str = "EUR"
    net: Decimal = Decimal(0)
    vat: Decimal = Decimal(0)
    gross: Decimal = Decimal(0)
    vat_breakdown: dict[str, Decimal] = field(default_factory=dict)
    lines: list[Line] = field(default_factory=list)
    source: str = ""

    def reconciles(self, tolerance: Decimal = Decimal("0.00")) -> bool:
        """net + VAT == gross, to the cent. The claim you make on stage."""
        return abs((self.net + self.vat) - self.gross) <= tolerance

    def discrepancy(self) -> Decimal:
        return (self.net + self.vat) - self.gross

    def __repr__(self) -> str:
        return (f"<Invoice {self.number or '?'} {self.seller[:24]!r} "
                f"net={self.net} vat={self.vat} gross={self.gross}>")


# CII (UN/CEFACT) and UBL use different tag names for the same facts.
def _txt(root, *paths) -> str:
    for p in paths:
        el = root.find(p, _NS)
        if el is not None and (el.text or "").strip():
            return el.text.strip()
    return ""


def _dec(root, *paths) -> Decimal:
    v = _txt(root, *paths)
    try:
        return Decimal(v) if v else Decimal(0)
    except Exception:
        return Decimal(0)


_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def parse_xml(data: bytes | str, source: str = "") -> Invoice:
    root = ET.fromstring(data if isinstance(data, bytes) else data.encode())
    inv = Invoice(source=source)
    is_ubl = root.tag.endswith("}Invoice") and "ubl" in root.tag

    if is_ubl:
        inv.number = _txt(root, "cbc:ID")
        inv.date = _txt(root, "cbc:IssueDate")
        inv.currency = _txt(root, "cbc:DocumentCurrencyCode") or "EUR"
        inv.seller = _txt(root, "cac:AccountingSupplierParty//cbc:RegistrationName",
                          "cac:AccountingSupplierParty//cbc:Name")
        inv.buyer = _txt(root, "cac:AccountingCustomerParty//cbc:RegistrationName",
                         "cac:AccountingCustomerParty//cbc:Name")
        inv.net = _dec(root, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount")
        inv.gross = _dec(root, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount")
        inv.vat = _dec(root, "cac:TaxTotal/cbc:TaxAmount")
        for st in root.findall("cac:TaxTotal/cac:TaxSubtotal", _NS):
            rate = _txt(st, "cac:TaxCategory/cbc:Percent") or "0"
            inv.vat_breakdown[rate] = inv.vat_breakdown.get(rate, Decimal(0)) + _dec(st, "cbc:TaxAmount")
        for ln in root.findall("cac:InvoiceLine", _NS):
            inv.lines.append(Line(
                name=_txt(ln, "cac:Item/cbc:Name"),
                qty=_dec(ln, "cbc:InvoicedQuantity"),
                unit_price=_dec(ln, "cac:Price/cbc:PriceAmount"),
                net=_dec(ln, "cbc:LineExtensionAmount"),
                vat_rate=_dec(ln, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent"),
            ))
    else:
        doc = "rsm:ExchangedDocument/"
        tx = "rsm:SupplyChainTradeTransaction/"
        agr, stl = tx + "ram:ApplicableHeaderTradeAgreement/", tx + "ram:ApplicableHeaderTradeSettlement/"
        inv.number = _txt(root, doc + "ram:ID")
        inv.date = _txt(root, doc + "ram:IssueDateTime/udt:DateTimeString")
        inv.currency = _txt(root, stl + "ram:InvoiceCurrencyCode") or "EUR"
        inv.seller = _txt(root, agr + "ram:SellerTradeParty/ram:Name")
        inv.buyer = _txt(root, agr + "ram:BuyerTradeParty/ram:Name")
        sm = stl + "ram:SpecifiedTradeSettlementHeaderMonetarySummation/"
        inv.net = _dec(root, sm + "ram:TaxBasisTotalAmount")
        inv.vat = _dec(root, sm + "ram:TaxTotalAmount")
        inv.gross = _dec(root, sm + "ram:GrandTotalAmount")
        for t in root.findall(stl + "ram:ApplicableTradeTax", _NS):
            rate = _txt(t, "ram:RateApplicablePercent") or "0"
            inv.vat_breakdown[rate] = inv.vat_breakdown.get(rate, Decimal(0)) + _dec(t, "ram:CalculatedAmount")
        for ln in root.findall(tx + "ram:IncludedSupplyChainTradeLineItem", _NS):
            inv.lines.append(Line(
                name=_txt(ln, "ram:SpecifiedTradeProduct/ram:Name"),
                qty=_dec(ln, "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity"),
                unit_price=_dec(ln, "ram:SpecifiedLineTradeAgreement/"
                                    "ram:NetPriceProductTradePrice/ram:ChargeAmount"),
                net=_dec(ln, "ram:SpecifiedLineTradeSettlement/"
                             "ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount"),
                vat_rate=_dec(ln, "ram:SpecifiedLineTradeSettlement/"
                                  "ram:ApplicableTradeTax/ram:RateApplicablePercent"),
            ))
    return inv


def read(path: str | Path) -> Invoice | None:
    """Parse a .pdf (hybrid), .xml, or .ubl.xml invoice."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        payload = embedded_xml(p)
        return parse_xml(payload, source=p.name) if payload else None
    return parse_xml(p.read_bytes(), source=p.name)


def corpus(limit: int | None = None) -> list[Path]:
    """Every invoice fixture on disk."""
    files = sorted(
        [*DATA.glob("samples/*.pdf"), *DATA.glob("samples/*.xml"), *DATA.glob("samples/*.XML")]
    )
    return files[:limit] if limit else files


if __name__ == "__main__":  # pragma: no cover
    ok = bad = 0
    for f in corpus():
        inv = read(f)
        if inv is None:
            print(f"  --   {f.name:<46} no embedded XML")
            bad += 1
            continue
        flag = "OK  " if inv.reconciles() else "DRIFT"
        if inv.reconciles():
            ok += 1
        else:
            bad += 1
        print(f"  {flag} {f.name:<46} net={inv.net:>10} vat={inv.vat:>9} "
              f"gross={inv.gross:>10} lines={len(inv.lines)}")
    print(f"\n  {ok} reconcile to the cent, {bad} did not")
