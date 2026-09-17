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
    struct After: Decodable { let amountEur: String; let deltaEur: String }
    struct Week: Decodable { let entries: Int; let saving_eur: String; let vat_eur: String; let receipts_missing: Int }
    struct Move: Decodable, Identifiable {
        let label: String; let status: String; let saving_eur: String; let citation: String; let why: String; let kind: String
        let vat_reclaim_eur: String?; let event_id: Int?
        var id: String { label + status }
    }
    let headline: Headline; let deadline: Deadline; let afterPlan: After; let week: Week?; let moves: [Move]; let disclosure: String
}
struct Events: Decodable { struct E: Decodable { let id: Int; let merchant: String; let amount: Double; let purpose: String?; let receipt: String? }; let events: [E] }

@MainActor final class Model: ObservableObject {
    @AppStorage("server") var server: String = "http://192.168.112.222:8787"
    @Published var card: Card?
    @Published var justFiled: String?          // label of the entry that just arrived
    @Published var error: String?
    private var seen = Set<Int>()
    private var primed = false

    func start() {
        Task { while true { await tick(); try? await Task.sleep(nanoseconds: 1_000_000_000) } }
    }
    func tick() async {
        do {
            let (d, _) = try await URLSession.shared.data(from: URL(string: server + "/v1/events")!)
            let ev = try JSONDecoder().decode(Events.self, from: d)
            if !primed { seen = Set(ev.events.map(\.id)); primed = true }
            for e in ev.events where !seen.contains(e.id) {
                seen.insert(e.id)
                if e.purpose == "business" || e.purpose == "work" { notify(e) }
            }
            let (c, _) = try await URLSession.shared.data(from: URL(string: server + "/v1/demo/card")!)
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
