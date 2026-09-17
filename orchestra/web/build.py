"""
Builds the comparison page: two runs (routed vs. all large) replayed side by side from their exported JSON.

    python3 orchestra/web/build.py                       # latest routed-*.json and baseline-*.json in .orchestra/runs
    python3 orchestra/web/build.py routed.json base.json # explicit files
    open .orchestra/runs/compare.html

Static, single file, data inlined. Replays the audit events on a compressed clock: agents light up with the tier
that answered, denied actions and approvals flash, the cost counters run, then the measured numbers stand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / ".orchestra" / "runs"


def latest(label: str) -> Path:
    files = sorted(RUNS.glob(f"{label}-*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"no {label}-*.json in {RUNS}; run `python3 orchestra/demo.py --compare` first")
    return files[-1]


def build(routed: Path, baseline: Path, out: Path) -> Path:
    data = {"routed": json.loads(routed.read_text()), "baseline": json.loads(baseline.read_text())}
    html = TEMPLATE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>orchestra: routed vs all large</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap">
<style>
:root{--bg:#f3f6fa;--card:#fff;--ink:#1c1f24;--muted:#5b6470;--line:#e1e7ef;--accent:#367ee2;--band:#e4ecf7;
--small:#9cc3f5;--medium:#367ee2;--large:#1c1f24;--deny:#d0463d;--ask:#b8791a;--good:#1e8f6b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Lato,"Helvetica Neue",Arial,sans-serif;font-size:15px;padding:24px 16px 48px}
main{max-width:1180px;margin:0 auto}
h1{font-size:28px;font-weight:900;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0 0 14px}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
button{font:inherit;font-weight:700;background:var(--accent);color:#fff;border:0;border-radius:10px;padding:9px 16px;cursor:pointer}
button.ghost{background:var(--band);color:var(--ink)}
button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.clock{font-variant-numeric:tabular-nums;color:var(--muted);min-width:90px}
.lanes{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:820px){.lanes{grid-template-columns:1fr}}
.lane{background:var(--card);border-radius:16px;box-shadow:0 6px 24px rgba(28,31,36,.06);padding:18px 18px 14px;display:grid;gap:12px;align-content:start}
.lane h2{margin:0;font-size:18px;font-weight:900}
.lane .models{color:var(--muted);font-size:13px}
.agents{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.ag{border:1px solid var(--line);border-radius:12px;padding:10px 10px 8px;min-height:64px;transition:background .25s,border-color .25s,transform .25s}
.ag b{display:block;font-size:14px}
.ag small{color:var(--muted);font-size:12px;display:block;min-height:15px}
.ag.small{background:var(--small);border-color:var(--small)}
.ag.medium{background:var(--medium);border-color:var(--medium);color:#fff}
.ag.medium small{color:#e8edf3}
.ag.large{background:var(--large);border-color:var(--large);color:#fff}
.ag.large small{color:#c9d1dc}
.ag.deny{background:var(--deny);border-color:var(--deny);color:#fff;transform:scale(1.04)}
.ag.deny small{color:#fff}
.ag.ask{background:var(--ask);border-color:var(--ask);color:#fff}
.ag.ask small{color:#fff}
.counters{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.ct{background:var(--band);border-radius:12px;padding:10px 12px}
.ct b{display:block;font-size:22px;font-weight:900;font-variant-numeric:tabular-nums}
.ct span{color:var(--muted);font-size:12px}
.log{border-top:1px solid var(--line);max-height:260px;min-height:120px;overflow:auto;font-size:13px}
.log div{display:grid;grid-template-columns:76px 82px 60px 1fr;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);animation:in .2s ease-out}
.log .t{color:var(--muted);font-variant-numeric:tabular-nums}
.log .tier{font-weight:700}
.log .deny{color:var(--deny);font-weight:700}
.log .ask{color:var(--ask);font-weight:700}
.log .human{color:var(--ask)}
@keyframes in{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:none}}
.final{background:var(--card);border-radius:16px;box-shadow:0 6px 24px rgba(28,31,36,.06);padding:18px;margin-top:16px}
.final.hide{visibility:hidden}
.final h2{margin:0 0 10px;font-size:18px;font-weight:900}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
td,th{text-align:left;padding:7px 0;border-top:1px solid var(--line)}
th{font-weight:700}
tr:first-child td,tr:first-child th{border-top:0}
.saved{font-size:34px;font-weight:900;margin-top:10px}
.saved small{font-size:14px;font-weight:400;color:var(--muted);display:block}
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:13px;margin-top:6px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:5px}
@media (prefers-reduced-motion:reduce){.ag,.log div{transition:none;animation:none}}
</style>
</head>
<body>
<main>
<h1>Routed vs. all large</h1>
<p class="sub" id="sub"></p>
<div class="bar">
  <button id="play">Replay</button>
  <button class="ghost" id="skip">Show result</button>
  <span class="clock" id="clock">0.0 s</span>
  <span class="legend"><span><i style="background:var(--small)"></i>small</span><span><i style="background:var(--medium)"></i>medium</span><span><i style="background:var(--large)"></i>large</span><span><i style="background:var(--deny)"></i>denied</span><span><i style="background:var(--ask)"></i>needs approval</span></span>
</div>
<div class="lanes">
  <section class="lane" data-lane="routed"><h2>Routed: small first, escalate on doubt</h2><div class="models"></div>
    <div class="agents"></div><div class="counters"></div><div class="log"></div></section>
  <section class="lane" data-lane="baseline"><h2>Baseline: every agent on the large model</h2><div class="models"></div>
    <div class="agents"></div><div class="counters"></div><div class="log"></div></section>
</div>
<section class="final" id="final"><h2>Measured, same tickets, same oracle</h2><div id="table"></div><div class="saved" id="saved"></div></section>
<script>
const RUNS = __DATA__;
const LANES = ["routed","baseline"];
const AGENTS = ["intake","specialist","verifier","writer"];
const PLAY_SECONDS = 12;
const fmt = n => "$" + n.toFixed(4);
function prep(run){
  const t0 = Math.min(...run.audit.map(e => e.ts));
  const events = run.audit.map(e => ({...e, rel: e.ts - t0})).sort((a,b) => a.rel - b.rel);
  const ledger = run.ledger.map(e => ({...e, rel: e.ts - t0})).sort((a,b) => a.rel - b.rel);
  const end = Math.max(events.length ? events[events.length-1].rel : 0, ledger.length ? ledger[ledger.length-1].rel : 0);
  return {run, events, ledger, end};
}
const R = {routed: prep(RUNS.routed), baseline: prep(RUNS.baseline)};
const span = Math.max(R.routed.end, R.baseline.end, 0.001);
const scale = PLAY_SECONDS / span;
document.getElementById("sub").textContent = `scenario ${RUNS.routed.scenario || ""}, provider ${RUNS.routed.provider}, `
  + `${RUNS.routed.steps.length} steps per run, replayed ${span.toFixed(1)} s of wall clock in ${PLAY_SECONDS} s`;
const ui = {};
for (const lane of LANES){
  const el = document.querySelector(`[data-lane="${lane}"]`);
  const run = RUNS[lane];
  el.querySelector(".models").textContent = Object.entries(run.models).map(([t,m]) => `${t} ${m}`).join(", ");
  const ag = el.querySelector(".agents");
  for (const a of AGENTS){
    const d = document.createElement("div"); d.className = "ag"; d.dataset.agent = a;
    const b = document.createElement("b"); b.textContent = a;
    d.append(b, document.createElement("small")); ag.appendChild(d);
  }
  const ct = el.querySelector(".counters");
  ct.innerHTML = `<div class="ct"><b data-k="cost">$0.0000</b><span>cost</span></div><div class="ct"><b data-k="calls">0</b><span>model calls</span></div><div class="ct"><b data-k="denied">0</b><span>denied</span></div>`;
  ui[lane] = {el, ag, ct, log: el.querySelector(".log"), cost: 0, calls: 0, denied: 0, ei: 0, li: 0, timers: []};
}
function box(lane, agent){ return ui[lane].ag.querySelector(`[data-agent="${agent}"]`); }
function flash(lane, agent, cls, text, ms){
  const b = box(lane, agent); if (!b) return;
  b.className = "ag " + cls; b.querySelector("small").textContent = text || "";
  clearTimeout(b._t); b._t = setTimeout(() => { b.className = "ag"; b.querySelector("small").textContent = ""; }, ms || 900);
}
function cell(text, cls){ const s = document.createElement("span"); if (cls) s.className = cls; s.textContent = text == null ? "" : String(text); return s; }
function logRow(lane, rel, agent, tier, text, cls){
  const d = document.createElement("div");
  d.append(cell(rel.toFixed(1) + " s", "t"), cell(agent), cell(tier || "", "tier"), cell(text, cls || ""));
  ui[lane].log.prepend(d);
}
function applyEvent(lane, e){
  const u = ui[lane];
  if (e.event === "model_call"){ flash(lane, e.agent, e.tier, e.model, 1200); u.calls++; }
  else if (e.event === "escalate"){ logRow(lane, e.rel, e.agent, e.from, `unsure, escalating to ${e.to}`); }
  else if (e.event === "tool_check" && e.decision === "deny"){ flash(lane, e.agent, "deny", "denied: " + e.tool, 1600); u.denied++; logRow(lane, e.rel, e.agent, "", `refused ${e.tool}: ${e.reason}`, "deny"); }
  else if (e.event === "tool_check" && e.decision === "ask"){ flash(lane, e.agent, "ask", "approval: " + e.tool, 1600); logRow(lane, e.rel, e.agent, "", `${e.tool} queued for a human`, "ask"); }
  else if (e.event === "tool_call"){ logRow(lane, e.rel, e.agent, "", `tool ${e.tool}`); }
  else if (e.event === "cache_hit"){ logRow(lane, e.rel, e.agent, e.tier, "cache hit, no model call"); }
  else if (e.event === "step_end"){ logRow(lane, e.rel, e.agent, e.tier, `${e.step} ${e.escalate ? "to a human" : "done"}`, e.escalate ? "human" : ""); }
  else if (e.event === "step_skipped"){ logRow(lane, e.rel, e.agent, "", `${e.step} skipped, upstream went to a human`, "human"); }
  u.ct.querySelector('[data-k="calls"]').textContent = u.calls;
  u.ct.querySelector('[data-k="denied"]').textContent = u.denied;
}
function applyLedger(lane, e){ const u = ui[lane]; u.cost += e.cost_usd; u.ct.querySelector('[data-k="cost"]').textContent = fmt(u.cost); }
let start = null, raf = null, playing = false;
function reset(){
  for (const lane of LANES){ const u = ui[lane]; u.cost = u.calls = u.denied = u.ei = u.li = 0; u.log.innerHTML = ""; u.ct.querySelector('[data-k="cost"]').textContent = "$0.0000"; u.ct.querySelector('[data-k="calls"]').textContent = "0"; u.ct.querySelector('[data-k="denied"]').textContent = "0"; for (const b of u.ag.children){ b.className = "ag"; b.querySelector("small").textContent = ""; } }
  document.getElementById("final").classList.add("hide");
}
function tick(now){
  if (start === null) start = now;
  const t = (now - start) / 1000 / scale;
  for (const lane of LANES){
    const d = R[lane], u = ui[lane];
    while (u.ei < d.events.length && d.events[u.ei].rel <= t){ applyEvent(lane, d.events[u.ei]); u.ei++; }
    while (u.li < d.ledger.length && d.ledger[u.li].rel <= t){ applyLedger(lane, d.ledger[u.li]); u.li++; }
  }
  document.getElementById("clock").textContent = Math.min(t, span).toFixed(1) + " s";
  if (t < span) raf = requestAnimationFrame(tick); else finish();
}
function finish(){
  playing = false; document.getElementById("play").textContent = "Replay";
  for (const lane of LANES){ const d = R[lane], u = ui[lane]; while (u.ei < d.events.length) applyEvent(lane, d.events[u.ei++]); while (u.li < d.ledger.length) applyLedger(lane, d.ledger[u.li++]); }
  const r = RUNS.routed, b = RUNS.baseline;
  const h = x => x.harness || {};
  const tiers = x => Object.entries(x.totals.calls_by_tier).map(([t,n]) => `${t} ${n}`).join(", ") || "none";
  const rows = [
    ["harness correct", `${Math.round((h(r).accuracy||0)*(h(r).cases||0))}/${h(r).cases||0}`, `${Math.round((h(b).accuracy||0)*(h(b).cases||0))}/${h(b).cases||0}`],
    ["silent errors", h(r).silent_errors, h(b).silent_errors],
    ["adversarial held", h(r).adversarial_held ? "yes" : "no", h(b).adversarial_held ? "yes" : "no"],
    ["denied actions", r.totals.denied, b.totals.denied],
    ["model calls", r.totals.model_calls, b.totals.model_calls],
    ["calls by tier", tiers(r), tiers(b)],
    ["wall clock", `${R.routed.end.toFixed(1)} s`, `${R.baseline.end.toFixed(1)} s`],
    ["cost", fmt(r.totals.cost_usd), fmt(b.totals.cost_usd)],
  ];
  const table = document.createElement("table");
  const head = table.insertRow();
  for (const h of ["", "routed", "all large"]){ const th = document.createElement("th"); th.textContent = h; head.appendChild(th); }
  for (const r of rows){ const tr = table.insertRow(); for (const v of r) tr.insertCell().textContent = v == null ? "" : String(v); }
  const host = document.getElementById("table"); host.textContent = ""; host.appendChild(table);
  const saved = b.totals.cost_usd ? (1 - r.totals.cost_usd / b.totals.cost_usd) * 100 : 0;
  const same = (h(r).accuracy === h(b).accuracy) && (h(r).silent_errors === h(b).silent_errors);
  const savedEl = document.getElementById("saved");
  savedEl.textContent = saved.toFixed(0) + "% cheaper";
  const note = document.createElement("small");
  note.textContent = (same ? "same harness result" : "harness result differs") + ", measured on " + RUNS.routed.provider;
  savedEl.appendChild(note);
  document.getElementById("final").classList.remove("hide");
}
document.getElementById("play").addEventListener("click", () => { if (playing) return; reset(); start = null; playing = true; document.getElementById("play").textContent = "Playing"; raf = requestAnimationFrame(tick); });
document.getElementById("skip").addEventListener("click", () => { if (raf) cancelAnimationFrame(raf); if (playing) { playing = false; document.getElementById("play").textContent = "Replay"; } finish(); });
finish();   // the page opens on the result; Replay runs the two traces again
</script>
</main>
</body>
</html>
"""


def main(argv: list) -> int:
    routed = Path(argv[0]) if len(argv) > 0 else latest("routed")
    baseline = Path(argv[1]) if len(argv) > 1 else latest("baseline")
    out = Path(argv[2]) if len(argv) > 2 else RUNS / "compare.html"
    print("built", build(routed, baseline, out), "from", routed.name, "and", baseline.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
