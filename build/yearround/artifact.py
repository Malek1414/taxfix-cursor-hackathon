"""Body-only render of the November screen for publishing as an Artifact (no html/head/body tags)."""

from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from build.yearround.demo import validate                                                # noqa: E402
from build.yearround.moves import WK_PAUSCHBETRAG, november_profile, november_table, plan, position  # noqa: E402

CSS = """
:root{--ink:#14301a;--ink2:#3f5244;--mute:#6a7a6d;--green:#1f5a2a;--green2:#2c7a3a;--lime:#b6ff5c;--lime-ink:#1a3a12;
--ground:#eef1e8;--paper:#f7f8f3;--card:#ffffff;--line:#d9e0d4;--warn:#8a5a00;--warnbg:#fff4dd;--warn-ink:#6b4a00;--phone:#111614}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e6eee3;--ink2:#b9c7b8;--mute:#8fa08f;--green:#2f7a3d;--green2:#3d9a4e;
--lime:#b6ff5c;--lime-ink:#1a3a12;--ground:#0f1712;--paper:#16211a;--card:#1d2b21;--line:#2c3d30;--warn:#f0c26a;--warnbg:#3a2c10;--warn-ink:#f3d99a;--phone:#000}}
:root[data-theme="dark"]{--ink:#e6eee3;--ink2:#b9c7b8;--mute:#8fa08f;--green:#2f7a3d;--green2:#3d9a4e;--lime:#b6ff5c;--lime-ink:#1a3a12;
--ground:#0f1712;--paper:#16211a;--card:#1d2b21;--line:#2c3d30;--warn:#f0c26a;--warnbg:#3a2c10;--warn-ink:#f3d99a;--phone:#000}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"Instrument Sans",-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.5}
.num{font-family:"Sora","Instrument Sans",sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stage{display:grid;grid-template-columns:minmax(320px,400px) minmax(280px,480px);gap:48px;justify-content:center;align-items:start;padding:40px 20px 64px}
@media (max-width:820px){.stage{grid-template-columns:minmax(300px,400px)}}
.phone{background:var(--paper);border-radius:44px;padding:22px 16px 18px;border:9px solid var(--phone);box-shadow:0 30px 60px rgba(0,0,0,.28)}
.top{display:flex;justify-content:space-between;font-size:12px;color:var(--mute);padding:0 8px 12px}
.top b{color:var(--green);font-family:"Sora",sans-serif;letter-spacing:-.01em}
.hero{background:var(--green);color:#fff;border-radius:24px;padding:22px 20px 18px}
.k{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.82}
.hero .n{font-size:48px;font-weight:700;color:var(--lime);margin:4px 0 2px;line-height:1.05}
.hero .s{font-size:13px;opacity:.92}
.days{margin-top:14px;font-size:12px;background:rgba(255,255,255,.14);display:inline-block;padding:6px 11px;border-radius:999px}
h2{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:22px 8px 8px;font-weight:600}
.list{display:flex;flex-direction:column;gap:8px}
.move{background:var(--card);border-radius:18px;padding:13px 16px;display:grid;grid-template-columns:1fr auto;gap:4px 12px;border:1px solid var(--line)}
.move .t{font-weight:600;font-size:14.5px;line-height:1.3}
.move .v{font-weight:700;font-size:17px;color:var(--green2);white-space:nowrap}
.move .w{grid-column:1/3;font-size:12.5px;color:var(--ink2);line-height:1.45}
.move .c{grid-column:1/3;font-size:11px;color:var(--green2);font-weight:600}
.no{background:var(--warnbg);border-radius:18px;padding:12px 16px}
.no .t{font-weight:600;font-size:13.5px;color:var(--warn)}
.no .w{font-size:12.5px;color:var(--warn-ink);line-height:1.45;margin-top:3px}
.after{margin-top:12px;background:var(--card);border:2px solid var(--green2);border-radius:18px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.after .n{font-size:28px;font-weight:700;color:var(--green2);line-height:1.1}
.after small{font-size:12px;color:var(--mute);display:block}
.foot{font-size:11px;color:var(--mute);margin:16px 8px 0;line-height:1.5}
.side h1{font-family:"Sora",sans-serif;font-size:26px;line-height:1.2;margin:0 0 14px;text-wrap:balance;letter-spacing:-.02em}
.side p{margin:0 0 14px;max-width:62ch}
.q{border-left:4px solid var(--lime);padding:2px 0 2px 14px;color:var(--ink2);margin:0 0 18px;font-style:italic}
.proof{margin-top:22px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.proof .k{color:var(--mute);opacity:1}
.proof .big{font-family:"Sora",sans-serif;font-size:22px;font-weight:700;color:var(--ink);margin:4px 0 6px}
.proof .r{font-size:13px;color:var(--ink2)}
code{background:var(--paper);border:1px solid var(--line);padding:1px 6px;border-radius:6px;font-size:12px}
@media (prefers-reduced-motion:no-preference){.hero .n{animation:up .5s ease-out both}@keyframes up{from{transform:translateY(6px);opacity:.6}to{transform:none;opacity:1}}}
"""


def render() -> str:
    p = november_profile()
    pos = position(p)
    taken, end = plan(p, november_table())
    after = position(end).refund
    worth = [m for m in taken if m.status == "worth"]
    refused = [m for m in taken if m.status != "worth"]
    s = validate()
    e = html.escape

    moves = "".join(
        f'<div class="move"><div class="t">{e(m.candidate.label)}</div><div class="v num">+{m.saving:,.2f} €</div>'
        f'<div class="w">{e(m.why)}</div><div class="c">{e(m.citation)} · resolves in the statute</div></div>'
        for m in worth)
    nos = "".join(
        f'<div class="no"><div class="t">{"Worth 0 · " if m.status == "zero" else "Ask a human · "}{e(m.candidate.label)}</div>'
        f'<div class="w">{e(m.why)}</div></div>'
        for m in refused)
    laptop = next((m for m in worth if "Laptop" in m.candidate.label), None)
    ho = next((m for m in worth if "Home-office" in m.candidate.label), None)

    return f"""<title>Your Tax Position, Live</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Instrument+Sans:ital,wght@0,400;0,600;1,400&display=swap">
<style>{CSS}</style>
<div class="stage">
<div class="phone">
 <div class="top"><span>{p.today:%a %d %b %Y}</span><b>taxfix</b></div>
 <div class="hero"><div class="k">If you filed today</div><div class="n num">{pos.refund:,.2f} €</div>
  <div class="s">comes back to you · Bundesfinanzministerium's own algorithm</div>
  <div class="days">{pos.days_left} days to 31 Dec — that's § 11 EStG, not us</div></div>
 <h2>Moves worth making, in this order</h2><div class="list">{moves}</div>
 <div class="after"><div><small>After these {len(worth)} moves</small><div class="n num">{after:,.2f} €</div></div>
  <div style="text-align:right"><small>{pos.refund:,.2f} € today</small><span class="num" style="font-weight:600;color:var(--green2)">+{after - pos.refund:,.2f} €</span></div></div>
 <h2>What we won't show you as a saving</h2><div class="list">{nos}</div>
 <div class="foot">Profile is synthetic. Tariff: the 2026 wage-tax Programmablaufplan standing in for the annual assessment.
 Caps and thresholds coded from § 9a, § 35a, § 10b, § 10c, § 4 Abs. 5 Nr. 6c EStG. Nothing here files anything.</div>
</div>
<div class="side">
<h1>Why someone opens this in November</h1>
<div class="q">"Genuine value that makes someone open the app in November because they want to."</div>
<p>The number is wrong the moment your life changes and you haven't told it. A home-office day, a receipt, a donation, an
invoice due in January: each one moves it. That is the pull. No streak, no push, no manufactured deadline. 31 December is
the statute's, and the app just knows what it is worth to you.</p>
<p><b>A little bit clever.</b> The laptop alone is worth {laptop.saving if laptop else 0:,.2f} € because it carries you over the
{WK_PAUSCHBETRAG:,.0f} € Pauschbetrag. Once it does, the 30 home-office days you never bothered logging become worth {ho.saving if ho else 0:,.2f} € too.
Moves are priced in sequence, not in isolation.</p>
<p><b>In control.</b> The things we refuse are on the screen with the reason. A cash-paid Handwerker: 0 €. A tip citing a real
paragraph about the wrong thing: not shown. Marriage: a human prices that, not an algorithm.</p>
<p><b>How it's built.</b> Every euro is a recompute on two states with the BMF tariff in <code>core/pap</code>; every paragraph
resolves in <code>core/law</code>; Cursor's agent reaches the engine through an MCP server and can only show what was priced.</p>
<div class="proof"><div class="k">The proof, as run</div>
<div class="big num">{s.passed}/{s.total} exact · {len(s.silent_errors)} silent errors · {sum(r.ok for r in s.adversarial)}/{len(s.adversarial)} refusals held</div>
<div class="r">Expected values hand-computed against the federal Programmablaufplan and the statute text. Pass bar declared before the first run.</div></div>
</div>
</div>"""


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "november-artifact.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print(out)
