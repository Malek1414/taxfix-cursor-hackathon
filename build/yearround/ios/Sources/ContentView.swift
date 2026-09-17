import SwiftUI

// tokens read off the screen recording
extension Color {
    static let lime = Color(red: 0.80, green: 0.96, blue: 0.54)
    static let btn = Color(red: 0.65, green: 0.91, blue: 0.42)
    static let btn2 = Color(red: 0.87, green: 0.96, blue: 0.75)
    static let tile = Color(red: 0.957, green: 0.957, blue: 0.949)
    static let help = Color(red: 0.93, green: 0.95, blue: 0.97)
    static let nextTile = Color(red: 0.99, green: 0.96, blue: 0.78)
    static let green = Color(red: 0.18, green: 0.48, blue: 0.23)
    static let warn = Color(red: 1.0, green: 0.96, blue: 0.87)
}
func eur(_ s: String) -> String { let v = Double(s) ?? 0; return String(format: "%.0f €", v) }
func eur2(_ s: String) -> String { let v = Double(s) ?? 0; return String(format: "%.2f €", v).replacingOccurrences(of: ".", with: ",") }
let icon: [String: String] = ["handwerker": "🔌", "haushalt": "🧹", "werbungskosten": "💻", "homeoffice": "🏠", "spende": "💚", "betriebsausgabe": "🧾", "other": "👥"]

struct RootView: View {
    @EnvironmentObject var m: Model
    var body: some View {
        TabView {
            TaxYearView().tabItem { Label("Taxes", systemImage: "folder") }
            AccountView().tabItem { Label("Account", systemImage: "person") }
        }.tint(.black).onAppear { m.start() }
    }
}

struct HelpPill: View {
    var body: some View {
        HStack(spacing: 6) {
            HStack(spacing: -6) { ForEach(0..<3) { _ in Circle().fill(Color(red: 0.79, green: 0.64, blue: 0.49)).frame(width: 18, height: 18).overlay(Circle().stroke(.white, lineWidth: 2)) } }
            Text("Help").font(.system(size: 13, weight: .semibold))
        }.padding(.vertical, 5).padding(.horizontal, 10).background(Color.help).clipShape(Capsule())
    }
}

struct TaxYearView: View {
    @EnvironmentObject var m: Model
    var body: some View {
        ZStack(alignment: .bottom) {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack { Text("←").font(.system(size: 20)); Spacer(); HelpPill() }.padding(.horizontal, 16).padding(.top, 8)
                    Text("Tax year 2026").font(.system(size: 26, weight: .heavy)).padding(.horizontal, 16).padding(.vertical, 10)
                    if let c = m.card {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("If you filed today").font(.system(size: 12, weight: .semibold))
                            Text(eur(c.headline.amountEur)).font(.system(size: 30, weight: .heavy)).monospacedDigit()
                            Text("\(c.deadline.daysLeft) days to 31 Dec — that's \(c.deadline.basis), not us").font(.system(size: 12)).foregroundStyle(Color(red: 0.17, green: 0.29, blue: 0.07))
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(16).background(Color.lime).clipShape(RoundedRectangle(cornerRadius: 12)).padding(.horizontal, 16)

                        section("This week · Tap n' tax")
                        if let w = c.week {
                            row(tile: "🧾", title: "\(w.entries) purchase\(w.entries == 1 ? "" : "s") filed", sub: "\(w.receipts_missing) receipt\(w.receipts_missing == 1 ? "" : "s") missing",
                                right: "+" + eur(w.saving_eur), right2: (Double(w.vat_eur) ?? 0) > 0 ? "+\(eur2(w.vat_eur)) VAT" : nil, highlight: false)
                        }
                        let worth = c.moves.filter { $0.status == "worth" }
                        section("Before 31 December")
                        ForEach(worth) { mv in
                            row(tile: icon[mv.kind] ?? "•", title: mv.label, sub: mv.why, right: "+" + eur(mv.saving_eur),
                                right2: (Double(mv.vat_reclaim_eur ?? "0") ?? 0) > 0 ? "+\(eur2(mv.vat_reclaim_eur!)) VAT" : nil,
                                highlight: m.justFiled != nil && mv.label.hasPrefix(m.justFiled!))
                        }
                        HStack { Text("After these moves").font(.system(size: 13)); Spacer(); Text(eur(c.afterPlan.amountEur)).font(.system(size: 16, weight: .heavy)).foregroundStyle(Color.green) }.padding(.horizontal, 16).padding(.vertical, 10)
                        section("Not worth it, and why")
                        ForEach(c.moves.filter { $0.status == "zero" }) { mv in row(tile: icon[mv.kind] ?? "•", title: mv.label, sub: mv.why, right: "0 €", right2: nil, highlight: false, warn: true) }
                        section("Ask your advisor")
                        ForEach(c.moves.filter { $0.status == "escalate" }) { mv in row(tile: "👥", title: mv.label, sub: mv.why, right: "›", right2: nil, highlight: false) }
                        Text(c.disclosure).font(.system(size: 11)).foregroundStyle(.secondary).padding(16)
                    } else {
                        VStack(spacing: 8) { ProgressView(); Text("Loading…").font(.system(size: 17, weight: .bold)); if let e = m.error { Text(e).font(.footnote).foregroundStyle(.secondary) }
                            TextField("server", text: $m.server).textFieldStyle(.roundedBorder).padding() }.frame(maxWidth: .infinity).padding(.top, 120)
                    }
                    Spacer(minLength: 120)
                }
            }
            if let c = m.card, let first = c.moves.first(where: { $0.status == "worth" }) {
                HStack(spacing: 10) {
                    Text(icon[first.kind] ?? "•").frame(width: 36, height: 36).background(Color.nextTile).clipShape(RoundedRectangle(cornerRadius: 10))
                    VStack(alignment: .leading, spacing: 1) { Text("Next").font(.system(size: 11)).foregroundStyle(.secondary); Text(first.label.components(separatedBy: " — ").first ?? first.label).font(.system(size: 14, weight: .bold)).lineLimit(1) }
                    Spacer()
                    Text("Continue").font(.system(size: 14, weight: .bold)).padding(.vertical, 10).padding(.horizontal, 16).background(Color.btn).clipShape(RoundedRectangle(cornerRadius: 8))
                }.padding(10).background(.white).clipShape(RoundedRectangle(cornerRadius: 12)).shadow(color: .black.opacity(0.14), radius: 9, y: 4).padding(.horizontal, 16).padding(.bottom, 8)
            }
        }.background(Color.white)
    }
    func section(_ t: String) -> some View { Text(t.uppercased()).font(.system(size: 12, weight: .bold)).foregroundStyle(.secondary).kerning(0.6).padding(.horizontal, 16).padding(.top, 18).padding(.bottom, 4) }
    func row(tile: String, title: String, sub: String, right: String, right2: String?, highlight: Bool, warn: Bool = false) -> some View {
        HStack(spacing: 12) {
            Text(tile).font(.system(size: 18)).frame(width: 40, height: 40).background(warn ? Color.warn : Color.tile).clipShape(RoundedRectangle(cornerRadius: 10))
            VStack(alignment: .leading, spacing: 2) { Text(title).font(.system(size: 15)).lineLimit(2); Text(sub).font(.system(size: 11.5)).foregroundStyle(.secondary).lineLimit(2) }
            Spacer(minLength: 6)
            VStack(alignment: .trailing, spacing: 1) { Text(right).font(.system(size: 15, weight: .bold)).foregroundStyle(warn ? Color(red: 0.48, green: 0.32, blue: 0) : Color.green).monospacedDigit()
                if let r2 = right2 { Text(r2).font(.system(size: 11, weight: .semibold)).foregroundStyle(.secondary) } }
        }.padding(.vertical, 10).padding(.horizontal, highlight ? 10 : 0)
         .background(highlight ? Color.lime.opacity(0.55) : Color.clear).clipShape(RoundedRectangle(cornerRadius: 10))
         .overlay(Rectangle().frame(height: 1).foregroundStyle(Color(white: 0.93)), alignment: .bottom)
         .padding(.horizontal, 16)
         .animation(.easeOut(duration: 0.4), value: highlight)
    }
}

struct AccountView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("My account").font(.system(size: 26, weight: .heavy)).padding(.horizontal, 16).padding(.top, 20)
            Text("malek@code.berlin").font(.system(size: 13)).foregroundStyle(.secondary).padding(.horizontal, 16).padding(.top, 4)
            Text("Account settings").font(.system(size: 15, weight: .bold)).padding(16)
            ForEach(["Prefilled tax return", "Billing history", "Refer a friend", "My vouchers", "Tax advisor mandate", "Tap n' tax cards", "Change PIN", "Privacy settings"], id: \.self) { s in
                HStack { Text(s).font(.system(size: 15)); Spacer(); Text("›").foregroundStyle(.secondary) }.padding(.vertical, 12).padding(.horizontal, 16).overlay(Rectangle().frame(height: 1).foregroundStyle(Color(white: 0.93)), alignment: .bottom)
            }
            Spacer()
        }
    }
}
