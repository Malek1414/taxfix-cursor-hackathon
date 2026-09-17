# Deploy — Tap n' tax demo (for Sammy's agent)

Everything the demo needs, with every link. Hosting the server makes the iPad
terminal and the iPhone app talk over the internet, no shared Wi-Fi.

## Links
| What | Link |
|---|---|
| Repo (Dockerfile at root, port 8080) | https://github.com/Malek1414/taxfix-cursor-hackathon |
| iPad card terminal (GitHub Pages, static) | https://malek1414.github.io/taxfix-cursor-hackathon/ |
| Terminal wired to the hosted server | `https://malek1414.github.io/taxfix-cursor-hackathon/?api=https://<service>.sliplane.app` |
| Their screens with the 2026 card (static copy) | https://malek1414.github.io/taxfix-cursor-hackathon/app.html |
| Native iPhone app, signed build | https://github.com/Malek1414/taxfix-cursor-hackathon/releases/tag/tap-n-tax-demo |
| Pages source branch | `gh-pages` (index.html = terminal, app.html = simulator) |

## 1. Host the server on Sliplane
1. Sliplane → New Service → Deploy from GitHub → `Malek1414/taxfix-cursor-hackathon`, branch `main`.
2. Build: Dockerfile at repo root. Port: **8080** (the server reads `$PORT`). No env vars, no database.
3. Deploy. Copy the service URL, e.g. `https://tapntax.sliplane.app`.
4. Check: `https://<service>.sliplane.app/v1/health` → `{"ok": true, "engine": "BMF PAP 2026", "writes": false}`
   and `https://<service>.sliplane.app/terminal` (the same terminal page, served by the app).

Any Docker host works the same way: `docker build -t tapntax . && docker run -p 8080:8080 tapntax`.

## 2. Point the iPad at it
Open on the iPad: `https://malek1414.github.io/taxfix-cursor-hackathon/?api=https://<service>.sliplane.app`
Tap the screen → "Approved" → it POSTs the REWE purchase to the hosted server.
(The footer says "LINKED" when the `?api=` is set.)

## 3. Point the phone at it
Taxfix app → **Account** tab → server row → paste `https://<service>.sliplane.app`.
The dot goes green when it polls. Within one second of the iPad tap: notification + the REWE row.

## 4. Reset between takes
The server keeps purchases in memory. Restart the service (Sliplane → Restart) to clear them,
or just keep going: each tap adds one more filed purchase.

## What the server exposes
```
GET  /v1/health
GET  /terminal                 iPad page
GET  /                         simulator of their screens, live
GET  /v1/demo/card             the card the app renders
POST /v1/events/transaction    {merchant, amount, card, purpose, receipt_status, partner}
POST /v1/events/classify       {id, purpose}
POST /v1/events/receipt        {id, status}
GET  /v1/events
POST /v1/audit                 {text}  citation audit
```
Read-only against the world: nothing files, nothing writes to disk.
