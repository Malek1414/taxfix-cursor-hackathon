import SwiftUI
import UserNotifications

// Demo look-alike of the Taxfix iOS app (v4.1.0 idiom from the 17 Sep screen recording).
// Not distributed. Talks to the Tap n' tax server on the Mac.

@main
struct TaxfixApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject var model = Model()
    var body: some Scene { WindowGroup { RootView().environmentObject(model) } }
}

final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ a: UIApplication, didFinishLaunchingWithOptions o: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
        return true
    }
    // show the banner even when the app is in the foreground (for the split-screen shot)
    func userNotificationCenter(_ c: UNUserNotificationCenter, willPresent n: UNNotification,
                                withCompletionHandler h: @escaping (UNNotificationPresentationOptions) -> Void) { h([.banner, .sound]) }
}

// MARK: - model

struct Card: Decodable {
    struct Headline: Decodable { let amountEur: String; let label: String }
    struct Deadline: Decodable { let daysLeft: Int; let basis: String }
    struct After: Decodable { var amountEur: String; var deltaEur: String }
    struct Week: Decodable { var entries: Int; var saving_eur: String; var vat_eur: String; var receipts_missing: Int }
    struct Move: Decodable, Identifiable {
        let label: String; let status: String; let saving_eur: String; let citation: String; let why: String; let kind: String
        let vat_reclaim_eur: String?; let event_id: Int?
        var id: String { label + status }
    }
    var headline: Headline; var deadline: Deadline; var afterPlan: After; var week: Week?; var moves: [Move]; var disclosure: String
}
struct Events: Decodable { struct E: Decodable { let id: Int; let merchant: String; let amount: Double; let purpose: String?; let receipt: String? }; let events: [E] }

@MainActor final class Model: ObservableObject {
    @AppStorage("server") var server: String = "http://192.168.113.105:8787"
    @Published var card: Card?
    @Published var justFiled: String?          // label of the entry that just arrived
    @Published var error: String?
    private var seen = Set<Int>()
    private var primed = false

    var offline = false
    func start() {
        if card == nil { card = try? JSONDecoder().decode(Card.self, from: Data(CARD_BEFORE.utf8)) }   // bundled, so the screen is never empty
        Task { while true { await tick(); try? await Task.sleep(nanoseconds: 1_000_000_000) } }
    }
    /// A scanned receipt, filed on the phone immediately. Saving is net × marginal rate, shown as an estimate;
    /// the server replaces it with the exact BMF recompute when reachable.
    func fileLocally(merchant: String, amount: Double, vatRate: String) {
        let rate = Double(vatRate) ?? 0.19
        let net = (amount / (1 + rate) * 100).rounded() / 100
        let vat = ((amount - net) * 100).rounded() / 100
        let saving = (net * 0.28).rounded()                       // ≈ marginal rate at 58 k, Steuerklasse 1
        var c = card ?? (try! JSONDecoder().decode(Card.self, from: Data(CARD_BEFORE.utf8)))
        let mv = Card.Move(label: "\(merchant) — \(String(format: "%.2f", amount).replacingOccurrences(of: ".", with: ",")) EUR · receipt ✓",
                           status: "worth", saving_eur: String(saving), citation: "§ 4 EStG",
                           why: "net \(String(format: "%.2f", net).replacingOccurrences(of: ".", with: ",")) EUR is a Betriebsausgabe (§ 4 Abs. 4 EStG); \(String(format: "%.2f", vat).replacingOccurrences(of: ".", with: ",")) EUR VAT back next Voranmeldung (§ 15 UStG) · estimate at 28 %",
                           kind: "betriebsausgabe", vat_reclaim_eur: String(vat), event_id: -2)
        c.moves.insert(mv, at: 0)
        var w = c.week ?? Card.Week(entries: 0, saving_eur: "0", vat_eur: "0", receipts_missing: 0)
        w.entries += 1; w.saving_eur = String((Double(w.saving_eur) ?? 0) + saving); w.vat_eur = String((Double(w.vat_eur) ?? 0) + vat); c.week = w
        c.afterPlan.amountEur = String((Double(c.afterPlan.amountEur) ?? 0) + saving)
        card = c; offline = true; justFiled = merchant
        let n = UNMutableNotificationContent(); n.title = "Tap n' tax"
        n.body = "\(merchant) receipt filed: \(String(format: "%.2f", amount).replacingOccurrences(of: ".", with: ",")) € as office supplies, VAT \(String(format: "%.2f", vat).replacingOccurrences(of: ".", with: ",")) € back."
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: UUID().uuidString, content: n, trigger: nil))
    }

    /// The demo trigger with no network: long-press the title. Same notification, same row.
    func simulatePurchase() {
        offline = true
        notify(Events.E(id: -1, merchant: "REWE", amount: 38.40, purpose: "business", receipt: "ok"))
        card = try? JSONDecoder().decode(Card.self, from: Data(CARD_AFTER.utf8))
    }
    func tick() async {
        if offline { return }
        do {
            let base = server.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            guard let u1 = URL(string: base + "/v1/events"), let u2 = URL(string: base + "/v1/demo/card") else { return }
            let (d, _) = try await URLSession.shared.data(from: u1)
            let ev = try JSONDecoder().decode(Events.self, from: d)
            if !primed { seen = Set(ev.events.map(\.id)); primed = true }
            for e in ev.events where !seen.contains(e.id) {
                seen.insert(e.id)
                if e.purpose == "business" || e.purpose == "work" { notify(e) }
            }
            let (c, _) = try await URLSession.shared.data(from: u2)
            card = try JSONDecoder().decode(Card.self, from: c); error = nil
        } catch { self.error = error.localizedDescription }
    }
    func notify(_ e: Events.E) {
        justFiled = e.merchant
        let n = UNMutableNotificationContent()
        n.title = "Tap n' tax"
        n.body = String(format: "Your %@ payment of %.2f € looks tax-eligible — filed as office supplies, receipt attached. Tap to see.", e.merchant, e.amount).replacingOccurrences(of: ".", with: ",")
        n.sound = .default
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: UUID().uuidString, content: n, trigger: nil))
    }
}
