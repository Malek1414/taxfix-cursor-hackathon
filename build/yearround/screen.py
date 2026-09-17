"""
The November screen. Renders the plan to one self-contained HTML file.

    python3 build/yearround/screen.py            # -> build/yearround/out/november.html

Tone, from the brief: in control, financially savvy, a little bit clever.
Not dutiful, anxious, or guilty. So: one number, the moves, and the things we
refused to show you — with the reason — because the refusal is the trust.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from build.yearround.moves import november_profile, november_table, plan, position  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "november.html"

CSS = """
:root{--ink:#14301a;--green:#1f5a2a;--lime:#b6ff5c;--paper:#f6f7f2;--card:#fff;--mute:#5b6b5e;--warn:#8a5a00;--warnbg:#fff4dd}
*{box-sizing:border-box}body{margin:0;background:#e9ebe4;font-family:-apple-system,Inter,Segoe UI,Roboto,sans-serif;color:var(--ink)}
.stage{display:flex;gap:40px;justify-content:center;align-items:flex-start;padding:40px 20px;flex-wrap:wrap}
.phone{width:390px;background:var(--paper);border-radius:44px;padding:22px 18px;box-shadow:0 30px 60px rgba(0,0,0,.25);border:10px solid #111}
.top{display:flex;justify-content:space-between;font-size:12px;color:var(--mute);padding:0 6px 10px}
.hero{background:var(--green);color:#fff;border-radius:24px;padding:22px 20px}
.hero .k{font-size:12px;letter-spacing:.06em;text-transform:uppercase;opacity:.8}
.hero .n{font-size:46px;font-weight:700;color:var(--lime);margin:6px 0 2px;letter-spacing:-.02em}
.hero .s{font-size:13px;opacity:.9}
.hero .days{margin-top:14px;font-size:12px;background:rgba(255,255,255,.12);display:inline-block;padding:6px 10px;border-radius:999px}
h2{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin:22px 6px 8px}
.move{background:var(--card);border-radius:18px;padding:14px 16px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:6px 12px}
.move .t{font-weight:600;font-size:15px}.move .v{font-weight:700;font-size:17px;color:var(--green);white-space:nowrap}
.move .w{grid-column:1/3;font-size:12.5px;color:var(--mute);line-height:1.4}
.move .c{grid-column:1/3;font-size:11px;color:var(--green);font-weight:600}
.no{background:var(--warnbg);border-radius:18px;padding:12px 16px;margin-bottom:10px}
.no .t{font-weight:600;font-size:14px;color:var(--warn)}.no .w{font-size:12.5px;color:#6b4a00;line-height:1.4;margin-top:4px}
.after{margin-top:14px;background:#fff;border:2px solid var(--green);border-radius:18px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center}
.after .n{font-size:26px;font-weight:700;color:var(--green)}
.foot{font-size:11px;color:var(--mute);margin:16px 6px 0;line-height:1.5}
.side{max-width:420px;font-size:14px;line-height:1.55;color:var(--ink)}
.side h1{font-size:22px;margin:0 0 8px}.side .q{border-left:4px solid var(--lime);padding-left:12px;color:var(--mute);margin:12px 0}
.side code{background:#fff;padding:2px 6px;border-radius:6px;font-size:12px}
"""


def render() -> str:
    p = november_profile()
    pos = position(p)
    taken, end = plan(p, november_table())
    after = position(end).refund
    worth = [m for m in taken if m.status == "worth"]
    refused = [m for m in taken if m.status != "worth"]
    e = html.escape

    moves = "".join(
        f'<div class="move"><div class="t">{e(m.candidate.label)}</div><div class="v">+{m.saving:,.2f} €</div>'
        f'<div class="w">{e(m.why)}</div><div class="c">{e(m.citation)} · resolves in the statute ✓</div></div>'
        for m in worth)
    nos = "".join(
        f'<div class="no"><div class="t">{"Worth 0 —" if m.status == "zero" else "Ask a human —"} {e(m.candidate.label)}</div>'
        f'<div class="w">{e(m.why)}</div></div>'
        for m in refused)

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Taxfix · your tax position, live</title>
<style>{CSS}</style></head><body><div class="stage">
<div class="phone">
 <div class="top"><span>{p.today:%a %d %b %Y}</span><span>taxfix</span></div>
 <div class="hero"><div class="k">If you filed today</div><div class="n">{pos.refund:,.2f} €</div>
  <div class="s">comes back to you · on the Bundesfinanzministerium's own algorithm</div>
  <div class="days">{pos.days_left} days to 31 Dec — that's § 11 EStG, not us</div></div>
 <h2>Moves worth making — in this order</h2>{moves}
 <div class="after"><div><div style="font-size:12px;color:var(--mute)">After these {len(worth)} moves</div>
  <div class="n">{after:,.2f} €</div></div><div style="font-size:12px;color:var(--mute);text-align:right">{pos.refund:,.2f} € today<br>+{after - pos.refund:,.2f} €</div></div>
 <h2>What we won't show you as a saving</h2>{nos}
 <div class="foot">Profile is synthetic. Tariff: the 2026 wage-tax Programmablaufplan standing in for the annual assessment.
 Caps and thresholds coded from § 9a, § 35a, § 10b, § 10c, § 4 Abs. 5 Nr. 6c EStG — not from rulings. Nothing here files anything.</div>
</div>
<div class="side"><h1>Why someone opens this in November</h1>
<div class="q">"Genuine value that makes someone open the app in November because they <i>want</i> to."</div>
<p>The number is wrong the moment your life changes and you haven't told it. A home-office day, a receipt, a donation, an
invoice due in January — each one moves it. That is the pull. No streak, no push, no manufactured deadline: 31 December is
the statute's, and the app just knows what it's worth to you.</p>
<p><b>A little bit clever:</b> the laptop alone is worth {worth[1].saving if len(worth) > 1 else 0:,.2f} € because it carries you
over the 1 230 € Pauschbetrag — and once it does, the 30 home-office days you never bothered logging become worth something too.</p>
<p><b>In control:</b> the things we refuse are on the screen with the reason. Cash-paid Handwerker: 0 €. A tip citing a real
paragraph about the wrong thing: not shown. Marriage: a human prices that, not an algorithm.</p>
<p>Every euro is a recompute on two states with <code>core/pap</code>; every paragraph resolves in <code>core/law</code>;
the suite in <code>build/yearround/demo.py</code> prints the number we say on stage.</p>
</div></div></body></html>"""


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(OUT)
