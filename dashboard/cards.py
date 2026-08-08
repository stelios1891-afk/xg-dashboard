"""cards.py — HTML/CSS για τα match cards (κοινο για το Streamlit app & το static preview)."""
import html

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&'
         'family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">')

CARD_CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:4px;}
.wrap{display:flex;flex-direction:column;gap:9px;}
.card{background:#111827;border:1px solid #1e2d47;border-radius:12px;overflow:hidden;}
.sum{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;padding:11px 15px 7px;align-items:center;}
.team{display:flex;flex-direction:column;gap:3px;}
.team.away{align-items:flex-end;}
.thead{display:flex;align-items:center;gap:9px;}
.team.away .thead{flex-direction:row-reverse;}
.logo{width:28px;height:28px;object-fit:contain;flex:none;}
.tn{font-family:'Bebas Neue','Arial Narrow',sans-serif;font-size:19px;letter-spacing:.7px;font-weight:600;}
.meta{font-size:10px;color:#6b7fa3;display:flex;gap:6px;flex-wrap:wrap;}
.meta .xg{font-family:'JetBrains Mono',monospace;font-weight:700;color:#7ea2ff;}
.mid{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:220px;}
.lbls{display:flex;width:100%;justify-content:space-around;}
.lbls span{font-size:8.5px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.6px;flex:1;text-align:center;}
.pills{display:flex;gap:5px;}
.pill{padding:4px 0;border-radius:7px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;width:62px;text-align:center;}
.ph{background:rgba(52,209,122,.12);color:#34d17a;border:1px solid rgba(52,209,122,.22);}
.pd{background:rgba(245,183,49,.12);color:#f5b731;border:1px solid rgba(245,183,49,.22);}
.pa{background:rgba(240,79,90,.12);color:#f04f5a;border:1px solid rgba(240,79,90,.22);}
.odds{display:flex;gap:5px;}
.odds span{width:62px;text-align:center;font-family:'JetBrains Mono',monospace;font-size:10px;color:#8fa3c8;}
.pbar{display:flex;height:4px;margin-top:9px;}
.pbar div:first-child{background:#34d17a;}.pbar div:nth-child(2){background:#f5b731;}.pbar div:last-child{background:#f04f5a;}
details{border-top:1px solid #1e2d47;}
summary{list-style:none;cursor:pointer;text-align:center;padding:5px;font-size:9px;color:#6b7fa3;letter-spacing:1px;text-transform:uppercase;}
summary::-webkit-details-marker{display:none;}
.detail{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:6px 16px 15px;}
.inp{background:#1c2a42;border-radius:9px;padding:11px;}
.inp .h{font-size:11px;font-weight:600;margin-bottom:8px;color:#e8edf8;}
.row{display:flex;justify-content:space-between;font-size:11px;padding:2px 0;color:#8fa3c8;}
.row b{font-family:'JetBrains Mono',monospace;color:#e8edf8;font-weight:600;}
.row b.acc{color:#7ea2ff;}
.time{font-size:9px;color:#5a6b8c;text-align:center;padding-top:2px;}
</style>
"""

def esc(s):
    return html.escape(str(s))

LOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'

def _logo(tid):
    return f'<img class="logo" src="{LOGO.format(tid)}" loading="lazy" onerror="this.style.visibility=\'hidden\'">' if tid else ''

_BG = {'#34d17a': 'rgba(52,209,122,.14)', '#f04f5a': 'rgba(240,79,90,.14)', '#8fa3c8': 'rgba(143,163,200,.10)'}

def card_html(m):
    hw, dw, aw = m['hw'], m['d'], m['aw']
    hc = '#34d17a' if hw > aw else ('#f04f5a' if hw < aw else '#8fa3c8')
    ac = '#34d17a' if aw > hw else ('#f04f5a' if aw < hw else '#8fa3c8')
    hbg, abg = _BG[hc], _BG[ac]
    day = (m.get('utc') or '')[:10]
    return f"""
<div class="card"><div class="sum">
  <div class="team">
    <div class="thead">{_logo(m.get('home_id'))}<div class="tn">{esc(m['home'])}</div></div>
    <div class="meta"><span class="xg">xG {m['home_adj_xg']:.2f}</span><span>{m['home_exp_shots']:.1f} sh</span></div></div>
  <div class="mid">
    <div class="lbls"><span>Home</span><span>Draw</span><span>Away</span></div>
    <div class="pills"><div class="pill" style="background:{hbg};color:{hc};border:1px solid {hc}44">{hw:.0f}%</div>
      <div class="pill pd">{dw:.0f}%</div><div class="pill" style="background:{abg};color:{ac};border:1px solid {ac}44">{aw:.0f}%</div></div>
    <div class="odds"><span>{m['hw_odds']:.2f}</span><span>{m['d_odds']:.2f}</span><span>{m['aw_odds']:.2f}</span></div>
  </div>
  <div class="team away">
    <div class="thead">{_logo(m.get('away_id'))}<div class="tn">{esc(m['away'])}</div></div>
    <div class="meta"><span>{m['away_exp_shots']:.1f} sh</span><span class="xg">xG {m['away_adj_xg']:.2f}</span></div></div>
</div>
<div class="pbar"><div style="width:{hw}%"></div><div style="width:{dw}%"></div><div style="width:{aw}%"></div></div>
<details><summary>▾ model inputs</summary><div class="detail">
  <div class="inp"><div class="h">{esc(m['home'])} (home)</div>
    <div class="row"><span>Exp Shots</span><b class="acc">{m['home_exp_shots']:.2f}</b></div>
    <div class="row"><span>npxG / Shot</span><b>{m['home_xg_shot']:.4f}</b></div>
    <div class="row"><span>Neutral xG</span><b>{m['home_xg']:.3f}</b></div>
    <div class="row"><span>Adj xG (HFA)</span><b class="acc">{m['home_adj_xg']:.3f}</b></div></div>
  <div class="inp"><div class="h">{esc(m['away'])} (away)</div>
    <div class="row"><span>Exp Shots</span><b class="acc">{m['away_exp_shots']:.2f}</b></div>
    <div class="row"><span>npxG / Shot</span><b>{m['away_xg_shot']:.4f}</b></div>
    <div class="row"><span>Neutral xG</span><b>{m['away_xg']:.3f}</b></div>
    <div class="row"><span>Adj xG</span><b class="acc">{m['away_adj_xg']:.3f}</b></div></div>
</div><div class="time">{esc(day)}</div></details></div>"""

def cards_block(matches):
    """Το CSS + fonts + όλα τα cards σε <div class=wrap> (για components.html ή static)."""
    return CARD_CSS + FONTS + '<div class="wrap">' + ''.join(card_html(m) for m in matches) + '</div>'
