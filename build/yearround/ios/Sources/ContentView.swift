import SwiftUI

// Every token below is read off the 17 Sep screen recording of Taxfix iOS 4.1.0.
extension Color {
    static let ink = Color(red: 0.09, green: 0.09, blue: 0.09)
    static let lime = Color(red: 0.80, green: 0.965, blue: 0.54)      // question cards, active tab pill
    static let btn = Color(red: 0.65, green: 0.915, blue: 0.42)       // primary button
    static let btn2 = Color(red: 0.875, green: 0.96, blue: 0.75)      // secondary button
    static let tile = Color(red: 0.957, green: 0.957, blue: 0.949)    // row icon tile
    static let help = Color(red: 0.93, green: 0.95, blue: 0.97)       // Help pill
    static let nextTile = Color(red: 0.99, green: 0.96, blue: 0.78)   // sticky Next icon tile
    static let green = Color(red: 0.18, green: 0.48, blue: 0.23)
    static let line = Color(white: 0.925)
    static let warn = Color(red: 1.0, green: 0.957, blue: 0.867)
    static let warnInk = Color(red: 0.48, green: 0.32, blue: 0.0)
}
func eur(_ s: String) -> String { String(format: "%.0f €", Double(s) ?? 0) }
func eur2(_ s: String) -> String { String(format: "%.2f €", Double(s) ?? 0).replacingOccurrences(of: ".", with: ",") }
let icon: [String: String] = ["handwerker": "🔌", "haushalt": "🧹", "werbungskosten": "💻", "homeoffice": "🏠", "spende": "💚", "betriebsausgabe": "🧾", "other": "👥"]

struct RootView: View {
    @EnvironmentObject var m: Model
    @State private var tab = 0
    var body: some View {
        VStack(spacing: 0) {
            ZStack { if tab == 0 { TaxYearView() } else { AccountView() } }.frame(maxHeight: .infinity)
            TabBar(tab: $tab)
        }.background(Color.white).ignoresSafeArea(edges: .bottom).onAppear { m.start() }
    }
}

// their tab bar: two items, a lime rounded pill behind the active icon, 11pt labels
struct TabBar: View {
    @Binding var tab: Int
    var body: some View {
        HStack {
            item(0, "folder", "Taxes"); Spacer(); item(1, "person", "Account")
        }.padding(.horizontal, 64).padding(.top, 8).padding(.bottom, 28)
         .background(Color.white.overlay(Rectangle().frame(height: 1).foregroundStyle(Color.line), alignment: .top))
    }
    func item(_ i: Int, _ sys: String, _ label: String) -> some View {
        Button { tab = i } label: {
            VStack(spacing: 3) {
                Image(systemName: sys).font(.system(size: 16)).foregroundStyle(Color.ink)
                    .frame(width: 44, height: 26).background(tab == i ? Color.lime : .clear).clipShape(RoundedRectangle(cornerRadius: 8))
                Text(label).font(.system(size: 11)).foregroundStyle(Color.ink)
            }
        }.buttonStyle(.plain)
    }
}

struct HelpPill: View {
    var body: some View {
        HStack(spacing: 6) {
            HStack(spacing: -6) { ForEach(0..<3) { i in Circle().fill([Color(red: 0.79, green: 0.64, blue: 0.49), Color(red: 0.55, green: 0.45, blue: 0.38), Color(red: 0.85, green: 0.72, blue: 0.6)][i]).frame(width: 18, height: 18).overlay(Circle().stroke(.white, lineWidth: 2)) } }
            Text("Help").font(.system(size: 13, weight: .semibold)).foregroundStyle(Color.ink)
        }.padding(.vertical, 5).padding(.leading, 6).padding(.trailing, 10).background(Color.help).clipShape(Capsule())
    }
}

struct TaxYearView: View {
    @EnvironmentObject var m: Model
    @State private var scanning = false
    var body: some View {
        ZStack(alignment: .bottom) {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 0) {
                    HStack { Image(systemName: "arrow.left").font(.system(size: 18)); Spacer()
                        Button { scanning = true } label: { Image(systemName: "camera").font(.system(size: 15, weight: .semibold)).foregroundStyle(Color.ink).frame(width: 34, height: 30).background(Color.lime).clipShape(Capsule()) }.padding(.trailing, 8)
                        HelpPill() }.padding(.horizontal, 16).padding(.top, 8)
                    Text("Tax year 2026").font(.system(size: 26, weight: .heavy)).tracking(-0.3).padding(.horizontal, 16).padding(.top, 10).padding(.bottom, 14)
                        .onLongPressGesture(minimumDuration: 0.8) { m.simulatePurchase() }
                    if let c = m.card {
                        // the refund pill from the questionnaire header, made year-round — in their lime question-card style
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 3) {
                                Text("If you filed today").font(.system(size: 16, weight: .bold)).foregroundStyle(Color.ink)
                                Text("\(c.deadline.daysLeft) days to 31 December · that's \(c.deadline.basis), not us").font(.system(size: 12)).foregroundStyle(Color(red: 0.17, green: 0.29, blue: 0.07))
                            }
                            Spacer()
                            Text(eur(c.headline.amountEur)).font(.system(size: 28, weight: .heavy)).monospacedDigit().foregroundStyle(Color.ink)
                        }.padding(16).background(Color.lime).clipShape(RoundedRectangle(cornerRadius: 12)).padding(.horizontal, 16)

                        section("This week · Tap n' tax")
                        if let w = c.week {
                            row(tile: "🧾", title: "\(w.entries) purchase\(w.entries == 1 ? "" : "s") filed", sub: w.receipts_missing == 0 ? "Every entry carries its receipt" : "\(w.receipts_missing) receipt\(w.receipts_missing == 1 ? "" : "s") missing",
                                right: "+" + eur(w.saving_eur), right2: (Double(w.vat_eur) ?? 0) > 0 ? "+\(eur2(w.vat_eur)) VAT" : nil, highlight: false)
                        }
                        section("Before 31 December")
                        ForEach(c.moves.filter { $0.status == "worth" }) { mv in
                            row(tile: icon[mv.kind] ?? "•", title: mv.label, sub: mv.why, right: "+" + eur(mv.saving_eur),
                                right2: (Double(mv.vat_reclaim_eur ?? "0") ?? 0) > 0 ? "+\(eur2(mv.vat_reclaim_eur!)) VAT" : nil,
                                highlight: m.justFiled != nil && mv.label.hasPrefix(m.justFiled!))
                        }
                        HStack { Text("After these moves").font(.system(size: 13)).foregroundStyle(.secondary); Spacer()
                            Text(eur(c.afterPlan.amountEur)).font(.system(size: 17, weight: .heavy)).monospacedDigit().foregroundStyle(Color.green) }
                            .padding(.horizontal, 16).padding(.vertical, 12)
                        section("Not worth it, and why")
                        ForEach(c.moves.filter { $0.status == "zero" }) { mv in row(tile: icon[mv.kind] ?? "•", title: mv.label, sub: mv.why, right: "0 €", right2: nil, highlight: false, warn: true) }
                        section("Ask your advisor")
                        ForEach(c.moves.filter { $0.status == "escalate" }) { mv in row(tile: "👥", title: mv.label, sub: mv.why, right: "›", right2: nil, highlight: false, chev: true) }
                        Text(c.disclosure).font(.system(size: 11)).foregroundStyle(.secondary).lineSpacing(2).padding(16)
                    } else {
                        VStack(spacing: 10) {
                            ProgressView().tint(Color.green).scaleEffect(1.4)
                            Text("Loading...").font(.system(size: 18, weight: .bold))
                            if let e = m.error { Text(e).font(.system(size: 11)).foregroundStyle(.secondary).multilineTextAlignment(.center).padding(.horizontal, 24) }
                            TextField("server", text: $m.server).font(.system(size: 12)).textFieldStyle(.roundedBorder).padding(.horizontal, 40)
                        }.frame(maxWidth: .infinity).padding(.top, 140)
                    }
                    Spacer(minLength: 110)
                }
            }
            if let c = m.card, let first = c.moves.first(where: { $0.status == "worth" }) {
                HStack(spacing: 10) {
                    Text(icon[first.kind] ?? "•").font(.system(size: 16)).frame(width: 36, height: 36).background(Color.nextTile).clipShape(RoundedRectangle(cornerRadius: 10))
                    VStack(alignment: .leading, spacing: 1) { Text("Next").font(.system(size: 11)).foregroundStyle(.secondary)
                        Text(first.label.components(separatedBy: " — ").first ?? first.label).font(.system(size: 14, weight: .bold)).lineLimit(1) }
                    Spacer()
                    Text("Continue").font(.system(size: 14, weight: .bold)).foregroundStyle(Color.ink).padding(.vertical, 10).padding(.horizontal, 16).background(Color.btn).clipShape(RoundedRectangle(cornerRadius: 8))
                }.padding(10).background(.white).clipShape(RoundedRectangle(cornerRadius: 12)).shadow(color: .black.opacity(0.14), radius: 9, y: 4).padding(.horizontal, 16).padding(.bottom, 10)
            }
        }
        .fullScreenCover(isPresented: $scanning) { ScanSheet().environmentObject(m) }
    }
    func section(_ t: String) -> some View {
        Text(t.uppercased()).font(.system(size: 11, weight: .bold)).foregroundStyle(.secondary).kerning(0.7).padding(.horizontal, 16).padding(.top, 18).padding(.bottom, 4)
    }
    func row(tile: String, title: String, sub: String, right: String, right2: String?, highlight: Bool, warn: Bool = false, chev: Bool = false) -> some View {
        HStack(spacing: 12) {
            Text(tile).font(.system(size: 18)).frame(width: 40, height: 40).background(warn ? Color.warn : Color.tile).clipShape(RoundedRectangle(cornerRadius: 10))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.system(size: 15)).foregroundStyle(Color.ink).lineLimit(2)
                Text(sub).font(.system(size: 11.5)).foregroundStyle(.secondary).lineLimit(2)
            }
            Spacer(minLength: 6)
            VStack(alignment: .trailing, spacing: 1) {
                Text(right).font(.system(size: chev ? 20 : 15, weight: .bold)).monospacedDigit().foregroundStyle(chev ? Color(white: 0.7) : (warn ? Color.warnInk : Color.green))
                if let r2 = right2 { Text(r2).font(.system(size: 11, weight: .semibold)).foregroundStyle(.secondary) }
            }
        }
        .padding(.vertical, 10).padding(.horizontal, highlight ? 10 : 0)
        .background(highlight ? Color.lime.opacity(0.6) : .clear).clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(Rectangle().frame(height: 1).foregroundStyle(Color.line), alignment: .bottom)
        .padding(.horizontal, 16)
        .animation(.easeOut(duration: 0.5), value: highlight)
    }
}

struct AccountView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("My account").font(.system(size: 26, weight: .heavy)).padding(.horizontal, 16).padding(.top, 24)
                Text("malek@code.berlin").font(.system(size: 13)).foregroundStyle(.secondary).padding(.horizontal, 16).padding(.top, 4)
                Text("Account settings").font(.system(size: 15, weight: .bold)).padding(.horizontal, 16).padding(.top, 20).padding(.bottom, 6)
                ForEach([("Prefilled tax return", "doc.text"), ("Billing history", "doc.plaintext"), ("Refer a friend", "person.2"), ("My vouchers", "gift"), ("Tax advisor mandate", "square.and.pencil"), ("Tap n' tax cards", "creditcard"), ("Change PIN", "lock"), ("Privacy settings", "shield"), ("Change language", "globe")], id: \.0) { s in
                    HStack(spacing: 12) { Image(systemName: s.1).font(.system(size: 14)).frame(width: 20); Text(s.0).font(.system(size: 15)); Spacer(); Text("›").foregroundStyle(Color(white: 0.7)).font(.system(size: 18)) }
                        .padding(.vertical, 12).padding(.horizontal, 16).overlay(Rectangle().frame(height: 1).foregroundStyle(Color.line), alignment: .bottom)
                }
            }
        }
    }
}
