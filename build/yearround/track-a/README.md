# Track A — Sammy: the safe demo path (Shortcut + Safari), owns this folder

Goal: the same shot as the native app, with zero signing risk. Phone shows a
notification after the payment, tap opens the Taxfix-look screens full screen.
Malek is on Track B (native app in `../ios/`). Whichever is ready at 20:40 gets recorded.

## What already runs (don't rebuild)
- Server on the Mac: `python3 build/yearround/api.py` → http://192.168.112.222:8787
  - `/`          Taxfix-look screens (year chooser → Tax year 2026 → question → receipt)
  - `/terminal`  the iPad card-terminal page (tap = Approved → posts the REWE purchase, partner receipt attached)
  - `POST /v1/events/transaction` what the Shortcut posts
- Check from the phone first: open http://192.168.112.222:8787/v1/health in Safari. If it fails,
  phone and Mac are not on the same network → Mac: System Settings → Sharing → Internet Sharing,
  phone joins the Mac hotspot, and the IP becomes 192.168.2.1.

## Build on the phone (Shortcuts app), ~5 minutes
1. Shortcuts → **+** new shortcut, name it **Tap n' tax**. Actions, in order:
   1. **Get Contents of URL** — `http://192.168.112.222:8787/v1/events/transaction`, Method POST,
      Request Body JSON: `merchant` = REWE · `amount` = 38.40 · `card` = Business Visa •• 4821 ·
      `category` = Office supplies · `purpose` = business · `receipt_status` = ok · `partner` = true
   2. **Show Notification** — Title `Tap n' tax` · Body
      `Your REWE payment of 38,40 € looks tax-eligible — filed as office supplies, receipt attached. Tap to see.`
   3. **Open URLs** — `http://192.168.112.222:8787/`
2. Automation → **+** → **Wallet** (iOS 26; "Transaction" on 17/18) → the business card → Run Immediately
   → run the **Tap n' tax** shortcut. This makes a real Apple Pay payment fire it.
   For the video with no real payment: run the shortcut by hand from the Shortcuts widget right
   after tapping the iPad terminal.
3. Safari: open http://192.168.112.222:8787/ once, **Share → Add to Home Screen** (name "Taxfix")
   so it opens full screen without the Safari bar.

## The shot (iPad + phone side by side, phone screen-recorded)
1. iPad: http://192.168.112.222:8787/terminal shows REWE 38,40 €.
2. Phone: double-click side button (real Apple Pay sheet), hold to iPad, tap iPad → "Approved".
3. Phone: run the shortcut (or the Wallet automation fires) → notification banner → tap → Taxfix
   home screen with the REWE row filed, 9 € + 6,13 € VAT, "This week: 1 purchase filed".
4. Voice-over from docs/PITCH.md, ending: "Less taxes, more benefits. This is Taxfix."

## If the server is unreachable from the phone
Fallback inside Safari: open http://192.168.112.222:8787/ on the **Mac** in a phone-sized window
and screen-record the Mac instead. The "⌘ Apple Pay @ REWE" button in the toggle posts the same event.
