"""europe_view.py — Ευρωπαϊκες διοργανωσεις 2627 (UCL/UEL/UECL): match cards απο euro_projections.json.

Τα projections υπολογιζονται ΤΟΠΙΚΑ (euro_live_projections.py, V4 engine: εγχωρια ratings
ανα πηγη FotMob/Ben/γκολ + διαλιγκικα offsets + warm-start K=8) και κανουν commit ως JSON —
το dashboard απλως τα δειχνει.
"""
import os, json, html, datetime

import cards  # CSS/FONTS/LOGO απο τα κοινα match cards

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJ_F = os.path.join(_ROOT, 'euro_projections.json')
_ODDS_F = os.path.join(_ROOT, 'euro_odds_latest.json')

COMP_LABEL = {'ChampionsLeague': 'Champions League', 'EuropaLeague': 'Europa League',
              'ConferenceLeague': 'Conference League'}
COMP_FOTMOB = {'ChampionsLeague': 42, 'EuropaLeague': 73, 'ConferenceLeague': 10216}
COMP_COLOR = {'ChampionsLeague': '#7ea2ff', 'EuropaLeague': '#f5a623', 'ConferenceLeague': '#3ec98f'}

SRC_STYLE = {'FotMob': ('xG πληρες', '#7ea2ff'), 'Ben': ('xG Opta', '#f5b731'),
             'γκολ+Elo': ('γκολ+Elo', '#c98fa3'), 'γκολ': ('μονο γκολ', '#f04f5a')}


def load():
    if not os.path.exists(_PROJ_F):
        return None
    with open(_PROJ_F, encoding='utf-8') as fh:
        return json.load(fh)


def load_odds():
    """{mid: {h,d,a,line,oh,oa,when}} απο τον scanner (euro_odds_scan.py)· {} αν λειπει."""
    try:
        with open(_ODDS_F, encoding='utf-8') as fh:
            return json.load(fh).get('odds', {})
    except Exception:
        return {}


def esc(s):
    return html.escape(str(s))


def _src_badge(src):
    lbl, c = SRC_STYLE.get(src, (src, '#8fa3c8'))
    return (f'<span style="font-size:8.5px;color:{c};border:1px solid {c}55;border-radius:4px;'
            f'padding:0 4px;letter-spacing:.4px">{esc(lbl)}</span>')


def _ko_fmt(utc):
    try:
        d = datetime.datetime.fromisoformat(str(utc).replace('Z', '+00:00'))
        d = d + datetime.timedelta(hours=3)  # ωρα Ελλαδας (καλοκαιρι UTC+3)
        return d.strftime('%a %d/%m %H:%M')
    except Exception:
        return str(utc)[:16]


def _mkt_span(our, mkt):
    """Οπως cards._mkt_span: πρασινο = η αγορα πληρωνει καλυτερα απο το fair μας (value),
    κοκκινο = η αγορα πιο σιγουρη απο εμας."""
    if not mkt:
        return '<span class="mo none">—</span>'
    if our < mkt * 0.97:
        c = 'val'
    elif our > mkt * 1.03:
        c = 'against'
    else:
        c = 'near'
    return f'<span class="mo {c}">{mkt:.2f}</span>'


def card_html(m, mk=None):
    if not m.get('covered'):
        return (f'<div class="card" style="opacity:.55"><div class="sum">'
                f'<div class="team"><div class="thead">{cards._logo(m.get("hid"))}'
                f'<div class="tn">{esc(m["home"])}</div></div></div>'
                f'<div class="mid" style="font-size:11px;color:#6b7fa3">χωρις projection<br>'
                f'<span style="font-size:9px">{esc(m.get("note") or "ακαλυπτη ομαδα")}</span></div>'
                f'<div class="team away"><div class="thead">{cards._logo(m.get("aid"))}'
                f'<div class="tn">{esc(m["away"])}</div></div></div>'
                f'</div><div class="time" style="padding:0 0 8px">{_ko_fmt(m.get("utc"))}</div></div>')
    hw, dw, aw = m['p1'] * 100, m['px'] * 100, m['p2'] * 100
    hc = '#34d17a' if hw > aw else ('#f04f5a' if hw < aw else '#8fa3c8')
    ac = '#34d17a' if aw > hw else ('#f04f5a' if aw < hw else '#8fa3c8')
    hbg, abg = cards._BG[hc], cards._BG[ac]
    fin = ''
    if m.get('finished') and m.get('score'):
        fin = (f'<span style="font-family:monospace;font-weight:700;color:#e8edf8;'
               f'font-size:13px">{esc(m["score"])}</span>')
    odds = (f'<div class="oddsrow"><span class="rl">μοντ</span><div class="odds">'
            f'<span>{m["o1"]:.2f}</span><span>{m["ox"]:.2f}</span><span>{m["o2"]:.2f}</span></div></div>')
    if mk and mk.get('h'):
        odds += (f'<div class="oddsrow"><span class="rl">αγορ</span><div class="odds">'
                 f'{_mkt_span(m["o1"], mk.get("h"))}{_mkt_span(m["ox"], mk.get("d"))}'
                 f'{_mkt_span(m["o2"], mk.get("a"))}</div></div>')
    return f"""
<div class="card"><div class="sum">
  <div class="team">
    <div class="thead">{cards._logo(m.get('hid'))}<div class="tn">{esc(m['home'])}</div></div>
    <div class="meta"><span class="xg">xG {m['xgh']:.2f}</span>{_src_badge(m.get('src_h'))}</div></div>
  <div class="mid">
    <div class="lbls"><span>Home</span><span>Draw</span><span>Away</span></div>
    <div class="pills"><div class="pill" style="background:{hbg};color:{hc};border:1px solid {hc}44">{hw:.0f}%</div>
      <div class="pill pd">{dw:.0f}%</div><div class="pill" style="background:{abg};color:{ac};border:1px solid {ac}44">{aw:.0f}%</div></div>
    <div class="oddswrap">{odds}</div>{fin}
  </div>
  <div class="team away">
    <div class="thead">{cards._logo(m.get('aid'))}<div class="tn">{esc(m['away'])}</div></div>
    <div class="meta">{_src_badge(m.get('src_a'))}<span class="xg">xG {m['xga']:.2f}</span></div></div>
</div>
<div class="pbar"><div style="width:{hw}%"></div><div style="width:{dw}%"></div><div style="width:{aw}%"></div></div>
<details><summary>▾ model inputs</summary><div class="detail">
  <div class="inp"><div class="h">{esc(m['home'])} (home)</div>
    <div class="row"><span>Λιγκα</span><b>{esc(m.get('lg_h') or '—')}</b></div>
    <div class="row"><span>Πηγη rating</span><b>{esc(m.get('src_h') or '—')}</b></div>
    <div class="row"><span>Φετινα ματς</span><b>{m.get('n_h', 0)}</b></div>
    <div class="row"><span>Neutral xG</span><b>{m['xgh0']:.3f}</b></div>
    <div class="row"><span>Adj xG (HFA)</span><b class="acc">{m['xgh']:.3f}</b></div></div>
  <div class="inp"><div class="h">{esc(m['away'])} (away)</div>
    <div class="row"><span>Λιγκα</span><b>{esc(m.get('lg_a') or '—')}</b></div>
    <div class="row"><span>Πηγη rating</span><b>{esc(m.get('src_a') or '—')}</b></div>
    <div class="row"><span>Φετινα ματς</span><b>{m.get('n_a', 0)}</b></div>
    <div class="row"><span>Neutral xG</span><b>{m['xga0']:.3f}</b></div>
    <div class="row"><span>Adj xG</span><b class="acc">{m['xga']:.3f}</b></div></div>
</div><div class="time">{_ko_fmt(m.get('utc'))} · αγωνιστικη {esc(m.get('round') or '?')}{_ah_note(mk)}</div></details></div>"""


def _ah_note(mk):
    if not mk or mk.get('line') is None:
        return ''
    return (f' · ασιατικο {mk["line"]:+.2f} @{mk.get("oh", 0):.2f}/{mk.get("oa", 0):.2f}'
            f' ({str(mk.get("when", ""))[:16].replace("T", " ")} UTC)')


def cards_block(matches, odds=None):
    odds = odds or {}
    return cards.CARD_CSS + cards.FONTS + '<div class="wrap">' + \
        ''.join(card_html(m, odds.get(str(m.get('mid')))) for m in matches) + '</div>'
