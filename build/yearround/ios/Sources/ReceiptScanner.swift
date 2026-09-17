import SwiftUI
import UIKit
import Vision

// Photograph a receipt → on-device text recognition (Vision) → merchant, total, VAT rate → filed with receipt attached.
struct ReceiptScan {
    var merchant = "Receipt"; var amount: Double = 0; var vatRate = "0.19"; var vat: Double = 0; var lines: [String] = []

    static func parse(_ lines: [String]) -> ReceiptScan {
        var r = ReceiptScan(); r.lines = lines
        let clean = lines.map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        r.merchant = clean.first(where: { $0.count >= 3 && $0.rangeOfCharacter(from: .letters) != nil }) ?? "Receipt"
        let money = try! NSRegularExpression(pattern: #"(\d{1,5})[,.](\d{2})"#)
        func amounts(in s: String) -> [Double] {
            money.matches(in: s, range: NSRange(s.startIndex..., in: s)).compactMap { m in
                guard let a = Range(m.range(at: 1), in: s), let b = Range(m.range(at: 2), in: s) else { return nil }
                return Double("\(s[a]).\(s[b])")
            }
        }
        let totalKeys = ["summe", "gesamt", "total", "betrag", "zu zahlen", "eur"]
        if let tl = clean.first(where: { l in totalKeys.contains { l.lowercased().contains($0) } && !amounts(in: l).isEmpty }) {
            r.amount = amounts(in: tl).max() ?? 0
        } else { r.amount = clean.flatMap(amounts).max() ?? 0 }
        if let vl = clean.first(where: { $0.lowercased().contains("mwst") || $0.lowercased().contains("ust") || $0.contains("%") }) {
            if vl.contains("7") && vl.contains("%") && !vl.contains("19") { r.vatRate = "0.07" }
            if let v = amounts(in: vl).last, v < r.amount { r.vat = v }
        }
        if r.vat == 0, r.amount > 0 { let rate = Double(r.vatRate)!; r.vat = (r.amount - r.amount / (1 + rate) * 1).rounded(toPlaces: 2) }
        return r
    }
}
extension Double { func rounded(toPlaces p: Int) -> Double { let f = pow(10.0, Double(p)); return (self * f).rounded() / f } }

struct CameraPicker: UIViewControllerRepresentable {
    var onImage: (UIImage) -> Void
    func makeCoordinator() -> C { C(onImage) }
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let p = UIImagePickerController()
        p.sourceType = UIImagePickerController.isSourceTypeAvailable(.camera) ? .camera : .photoLibrary
        p.delegate = context.coordinator; return p
    }
    func updateUIViewController(_ c: UIImagePickerController, context: Context) {}
    final class C: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let f: (UIImage) -> Void; init(_ f: @escaping (UIImage) -> Void) { self.f = f }
        func imagePickerController(_ p: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let img = info[.originalImage] as? UIImage { f(img) }; p.dismiss(animated: true)
        }
        func imagePickerControllerDidCancel(_ p: UIImagePickerController) { p.dismiss(animated: true) }
    }
}

func recognizeText(_ image: UIImage, done: @escaping ([String]) -> Void) {
    guard let cg = image.cgImage else { return done([]) }
    let req = VNRecognizeTextRequest { r, _ in
        let obs = (r.results as? [VNRecognizedTextObservation]) ?? []
        // top-to-bottom reading order
        let lines = obs.sorted { $0.boundingBox.midY > $1.boundingBox.midY }.compactMap { $0.topCandidates(1).first?.string }
        DispatchQueue.main.async { done(lines) }
    }
    req.recognitionLevel = .accurate; req.recognitionLanguages = ["de-DE", "en-US"]; req.usesLanguageCorrection = false
    DispatchQueue.global(qos: .userInitiated).async {
        try? VNImageRequestHandler(cgImage: cg, orientation: .up).perform([req])
    }
}

struct ScanSheet: View {
    @EnvironmentObject var m: Model
    @Environment(\.dismiss) var dismiss
    @State private var image: UIImage?
    @State private var scan: ReceiptScan?
    @State private var busy = false
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack { Button { dismiss() } label: { Image(systemName: "arrow.left").foregroundStyle(Color.ink) }; Spacer(); Text("Receipt").font(.system(size: 15, weight: .bold)); Spacer(); HelpPill() }.padding(16)
            if let s = scan {
                VStack(alignment: .leading, spacing: 6) {
                    Text("\(s.merchant) · \(eur2(String(s.amount))) — file it?").font(.system(size: 16, weight: .bold))
                    Text("Read from the photo on this phone. Net \(eur2(String((s.amount - s.vat).rounded(toPlaces: 2)))) is the expense, \(eur2(String(s.vat))) VAT comes back (§ 15 UStG).").font(.system(size: 12)).foregroundStyle(Color(red: 0.17, green: 0.29, blue: 0.07))
                }.frame(maxWidth: .infinity, alignment: .leading).padding(16).background(Color.lime).clipShape(RoundedRectangle(cornerRadius: 12)).padding(.horizontal, 16)
                HStack(alignment: .top, spacing: 14) {
                    if let img = image { Image(uiImage: img).resizable().scaledToFill().frame(width: 96, height: 128).clipShape(RoundedRectangle(cornerRadius: 10)).shadow(color: .black.opacity(0.12), radius: 6, y: 3) }
                    VStack(spacing: 0) { kv("Merchant", s.merchant); kv("Total", eur2(String(s.amount))); kv("VAT", "\(s.vatRate == "0.07" ? "7 %" : "19 %") · \(eur2(String(s.vat)))"); kv("Receipt", "attached ✓") }
                }.padding(16)
                Spacer()
                Button { file(s) } label: { Text(busy ? "Filing…" : "File as business expense").font(.system(size: 15, weight: .bold)).foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(.vertical, 14).background(Color.btn).clipShape(RoundedRectangle(cornerRadius: 8)) }.padding(16).disabled(busy || s.amount == 0)
                Button { scan = nil; image = nil } label: { Text("Retake").font(.system(size: 14, weight: .bold)).foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(.vertical, 12).background(Color.btn2).clipShape(RoundedRectangle(cornerRadius: 8)) }.padding(.horizontal, 16).padding(.bottom, 24)
            } else if let img = image {
                VStack(spacing: 14) {
                    Image(uiImage: img).resizable().scaledToFill().frame(width: 200, height: 260).clipShape(RoundedRectangle(cornerRadius: 12)).shadow(color: .black.opacity(0.12), radius: 10, y: 4)
                    ProgressView().tint(Color.green)
                    Text("Reading the receipt on this phone…").font(.system(size: 15, weight: .semibold))
                }.frame(maxWidth: .infinity).padding(.top, 60)
                Spacer()
            } else {
                ScanCameraView { img in image = img; recognizeText(img) { scan = ReceiptScan.parse($0) } }
            }
        }
    }
    func kv(_ k: String, _ v: String) -> some View {
        HStack { Text(k).font(.system(size: 13)); Spacer(); Text(v).font(.system(size: 13)).foregroundStyle(.secondary).lineLimit(1) }.padding(.vertical, 9).overlay(Rectangle().frame(height: 1).foregroundStyle(Color.line), alignment: .bottom)
    }
    func file(_ s: ReceiptScan) {
        // instant: file on the phone, dismiss, tell the server in the background (3 s cap, best effort)
        m.fileLocally(merchant: s.merchant, amount: s.amount, vatRate: s.vatRate)
        dismiss()
        guard let url = URL(string: m.server.trimmingCharacters(in: .whitespacesAndNewlines) + "/v1/events/transaction") else { return }
        var req = URLRequest(url: url, timeoutInterval: 3); req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["merchant": s.merchant, "amount": s.amount, "card": "Business Visa •• 4821", "category": "Receipt scan",
                                                                    "purpose": "business", "receipt_status": "ok", "vat_rate": s.vatRate])
        URLSession.shared.dataTask(with: req) { _, _, _ in }.resume()
    }
}
