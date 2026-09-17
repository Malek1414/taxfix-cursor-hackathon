# User story: pay with Apple Pay at REWE, photograph the receipt, Taxfix knows

Validated 17 Sep 2026, 19:50. Sources at the bottom.

## The story
Someone buys office supplies for their business at REWE, pays with Apple Pay,
photographs the receipt. Taxfix should learn the purchase without being opened,
and the year-round position should move. In November the receipt is one row on
the "Tax year 2026" card, and in April it is one question fewer.

## Can Taxfix read Apple Pay purchases? — No, and it never will via an API

| Route | Reality | Time to access |
|---|---|---|
| Apple Pay / PassKit merchant API | For *accepting* payments in your own app. Gives a merchant nothing about purchases made elsewhere. | n/a |
| **FinanceKit** (iOS 17.4+) | Reads transactions, but only Apple Card, Apple Cash and Savings. Needs the `com.apple.developer.financekit` entitlement, which Apple reviews per app; the app must be in the Finance category and ship in the US or UK App Store. Apple Card does not exist in Germany. | Weeks, and not for a German app |
| Wallet Orders (iOS 16+) | Merchants push order details into Wallet after an Apple Pay purchase. Merchant-side; third-party apps can't read them. | n/a |

## The workaround that works tonight: the Shortcuts "Transaction" automation
Since iOS 17, the Shortcuts app has a personal-automation trigger that fires on
every Wallet payment and exposes **card, merchant, amount, name**. It can be set
to **Run Immediately** with no confirmation. In iOS 26 Apple renamed the
trigger from "Transaction" to **"Wallet"**. No developer account, no entitlement,
no review. Known caveat: the trigger occasionally times out when the card
issuer's notification is slow.

That is a real Apple Pay hook a user installs in two minutes, and it is exactly
the "Kurzbefehle → in Taxfix" arrow on the whiteboard.

### Build it on the phone (2 minutes)
1. Shortcuts → Automation → **+** → **Wallet** (iOS 26; "Transaction" on 17–18).
2. Cards: the business card. Categories: all. Merchants: don't filter. **Run Immediately.**
3. Action **Ask for Input** → question "Business purchase?" (or skip and default yes).
4. Action **Get Contents of URL**
   - URL `http://192.168.112.222:8787/v1/events/transaction` (the Mac's LAN IP; phone on the same Wi-Fi)
   - Method POST, Request Body JSON:
     `merchant` = Shortcut Input › Merchant · `amount` = Shortcut Input › Amount ·
     `card` = Shortcut Input › Card or Pass · `category` = "Office supplies" · `business` = true
5. Optional: **Take Photo** → `receipt` = true. (Real product: upload to the existing
   Expenses document flow; the app already scans documents.)

The server appends the purchase as a Werbungskosten candidate and re-prices the
plan. Tested: a 38,40 € REWE purchase moved "after these moves" from 785 € to
795 € because the profile is already above the 1 230 € Pauschbetrag.

## Bank APIs instead? — Possible, not tonight
PSD2 obliges every German bank to expose an account-information API, but only a
licensed AISP may call it. Taxfix would go through an aggregator:

| Aggregator | Status Sep 2026 | Time to a working demo |
|---|---|---|
| GoCardless Bank Account Data (ex-Nordigen) | **Closed to new signups**, being wound down. Existing users keep the free tier and the `SANDBOXFINANCE_SFIN0000` sandbox bank. | not available |
| finAPI (Schufa), Tink (Visa), Klarna Kosma | Sales-led contracts, sandbox on request | days to weeks |
| Enable Banking, Salt Edge | Developer sandboxes on signup; production after KYC | hours for sandbox, weeks for real accounts |

For the pitch: the bank route is the production answer ("Taxfix already asks
for Belegabruf consent; account-information consent is the same shape"). The
Shortcut is the demo answer, and it is honest: it is what a user can do today.

## What we demo
- Screen: "Your tax returns" → the 2026 card → the REWE row appears with its euro value.
- Say: "That row came from an Apple Pay payment, through a Shortcut, with no
  Apple approval. In production it comes from the bank consent you already give
  for Belegabruf."

## Sources
- Apple Support, Transaction triggers in Shortcuts: https://support.apple.com/guide/shortcuts/transaction-trigger-apd65c67538a/ios
- Apple Developer Forums, Transaction automation on iOS 18: https://www.developer.apple.com/forums/thread/758053
- Apple Developer Forums, Transaction trigger timeouts: https://developer.apple.com/forums/thread/765516
- TravelSpend setup guide (Run Immediately, iOS 26 rename to "Wallet"): https://help.travel-spend.com/shortcuts--automation/ignQHsp85RQDsig2QwVcdX/set-up-apple-pay-automation/7tL8XfjBceg4D7mQeiSK2V
- Apple, Get started with FinanceKit (entitlement, Finance category, US/UK): https://developer.apple.com/financekit
- Apple Developer Forums, FinanceKit "not entitled": https://developer.apple.com/forums/thread/746770
- GoCardless Bank Account Data overview and sandbox: https://developer.gocardless.com/bank-account-data/overview · https://developer.gocardless.com/bank-account-data/sandbox/
- Signups disabled, alternatives: https://dev.to/johnfrandsen/gocardless-bank-account-data-alternatives-what-to-use-when-signups-are-disabled-326d · https://www.openbankingtracker.com/guides/free-open-banking-apis
