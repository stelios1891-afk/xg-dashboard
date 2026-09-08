"""europe_view.py — Ευρωπαϊκες διοργανωσεις 2627 (UCL/UEL/UECL): match cards απο euro_projections.json.

Τα projections υπολογιζονται ΤΟΠΙΚΑ (euro_live_projections.py, V4 engine: εγχωρια ratings
ανα πηγη FotMob/Ben/γκολ + διαλιγκικα offsets + warm-start K=8) και κανουν commit ως JSON —
το dashboard απλως τα δειχνει.
"""
import os, json, html, math, datetime

import cards  # CSS/FONTS/LOGO απο τα κοινα match cards
import picks  # gd_dist / p_cover για fair τιμες στις γραμμες αγορας

EU_DRAW_SCALE_DEF = 0.85   # fallback· η τρεχουσα τιμη ερχεται απο το euro_projections.json

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


def _eu_dist(xgh, xga, draw_scale):
    """gd_dist με την ευρωπαικη κλιμακωση ισοπαλιων (Χ ×scale, renorm τα υπολοιπα)."""
    dist = picks.gd_dist(max(xgh, 0.05), max(xga, 0.05))
    px = dist.get(0, 0.0)
    if px <= 0 or px >= 1:
        return dist
    k = (1.0 - draw_scale * px) / (1.0 - px)
    return {g: (p * draw_scale if g == 0 else p * k) for g, p in dist.items()}


def _tot_dist(xgh, xga):
    """Κατανομη ΣΥΝΟΛΟΥ γκολ (ιδιος πυρηνας με gd_dist: Poisson × draw boost διαγωνιου)."""
    lh, la = max(xgh, 0.05), max(xga, 0.05)
    F = [math.factorial(i) for i in range(13)]
    ph = [math.exp(-lh) * lh ** i / F[i] for i in range(13)]
    pa = [math.exp(-la) * la ** j / F[j] for j in range(13)]
    tot = {}
    s = 0.0
    for i in range(13):
        for j in range(13):
            p = ph[i] * pa[j] * (picks.DRAW_BOOST if i == j else 1.0)
            tot[i + j] = tot.get(i + j, 0.0) + p
            s += p
    return {t: p / s for t, p in tot.items()}


def _cover_q(dist, side, line):
    """ΣΩΣΤΟ quarter-aware cover (σπαει x.25/x.75 σε 2 μισες γραμμες — ΟΧΙ το picks.p_cover
    που εχει το γνωστο quarter-bug· εδω ειναι καθαρη οθονη, οχι μηχανη picks)."""
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L in parts:
        for k, p in dist.items():
            m = (k if side == 1 else -k) + L
            if m > 0.01:
                pw += p / len(parts)
            elif abs(m) <= 0.01:
                pp += p / len(parts)
    return pw, pp


def _fair_pair(dist, line):
    """Fair αποδοσεις (χωρις γκανιοτα) για γηπεδουχο/φιλοξενουμενο στη γραμμη line (home persp)."""
    out = []
    for side, ln in ((1, line), (-1, -line)):
        pw, pp = _cover_q(dist, side, ln)
        if pw <= 0:
            return None
        out.append(1.0 + (1.0 - pw - pp) / pw)
    return out


def _p_over(tot, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    po = pu = 0.0
    for L in parts:
        for t, p in tot.items():
            if t > L + 0.01:
                po += p / len(parts)
            elif t < L - 0.01:
                pu += p / len(parts)
    return po, pu


def _fair_ou(tot, line):
    po, pu = _p_over(tot, line)
    if po <= 0 or pu <= 0:
        return None
    push = max(1.0 - po - pu, 0.0)
    return (1.0 + pu / po, 1.0 + po / pu) if push == 0 else \
           (1.0 + (1.0 - po - push) / po, 1.0 + (1.0 - pu - push) / pu)


_LT_CELL = ('display:inline-block;text-align:center;font-family:monospace;font-size:10px;')


def _model_ah_line(dist):
    """Η «δικη μας» γραμμη: αυτη οπου το fair ζευγος ειναι το πιο ισορροπημενο."""
    best, bd = 0.0, 9e9
    for q in range(-16, 17):
        ln = q / 4.0
        pw, pp = _cover_q(dist, 1, ln)
        pl = 1.0 - pw - pp
        if pw > 0 and abs(pw - pl) < bd:
            bd, best = abs(pw - pl), ln
    return best


def _model_ou_line(tot):
    best, bd = 2.5, 9e9
    for q in range(4, 25):
        ln = q / 4.0
        po, pu = _p_over(tot, ln)
        if po > 0 and pu > 0 and abs(po - pu) < bd:
            bd, best = abs(po - pu), ln
    return best


def _pick_rows(ladder, center, extra, span=1.01, cap=7):
    """Γραμμες αγορας γυρω απο το center (±span), συν η extra (γραμμη μοντελου)."""
    lines = [r[0] for r in ladder]
    keep = [ln for ln in lines if center is None or abs(ln - center) <= span]
    if len(keep) > cap:
        keep = sorted(keep, key=lambda x: abs(x - (center or 0)))[:cap]
    if extra is not None and extra not in keep:
        keep.append(extra)
    have = {r[0]: (r[1], r[2]) for r in ladder}
    return [(ln, have.get(ln)) for ln in sorted(keep)]


def _ladder_html(title, rows, fair_fn, main_ln, model_ln, signed):
    body = ''
    for ln, mo in rows:
        fp = fair_fn(ln)
        tag = '●' if main_ln is not None and abs(ln - main_ln) < 0.01 else \
              ('◆' if abs(ln - model_ln) < 0.01 else '')
        tagc = '#f5b731' if tag == '●' else '#7ea2ff'
        lnc = tagc if tag else '#e8edf8'
        ln_s = f'{ln:+.2f}' if signed else f'{ln:.2f}'
        fp_s = f'{fp[0]:.2f}/{fp[1]:.2f}' if fp else '—'
        mo_s = f'{mo[0]:.2f}/{mo[1]:.2f}' if mo else '—'
        body += (f'<div style="display:flex;gap:7px;align-items:baseline">'
                 f'<span style="{_LT_CELL}width:10px;color:{tagc};font-size:8px">{tag}</span>'
                 f'<span style="{_LT_CELL}width:42px;color:{lnc};font-weight:700">{ln_s}</span>'
                 f'<span style="{_LT_CELL}width:76px;color:#7ea2ff">{fp_s}</span>'
                 f'<span style="{_LT_CELL}width:76px;color:#8fa3c8">{mo_s}</span></div>')
    head = (f'<div style="display:flex;gap:7px">'
            f'<span style="{_LT_CELL}width:10px"></span>'
            f'<span style="{_LT_CELL}width:42px;font-size:8px;color:#5a6b8c">ΓΡΑΜΜΗ</span>'
            f'<span style="{_LT_CELL}width:76px;font-size:8px;color:#5a6b8c">ΜΟΝΤ</span>'
            f'<span style="{_LT_CELL}width:76px;font-size:8px;color:#5a6b8c">ΑΓΟΡ</span></div>')
    return (f'<div style="display:flex;flex-direction:column;gap:4px">'
            f'<div style="font-size:9px;color:#6b7fa3;letter-spacing:1.5px;text-align:center">{title}</div>'
            f'{head}{body}</div>')


def _odds_pane(m, mk, draw_scale):
    """Το κουτι Match Odds: σκαλες γραμμων ασιατικου & γκολ, μοντελο vs αγορα."""
    mk = mk or {}
    dist = _eu_dist(m['xgh'], m['xga'], draw_scale)
    tot = _tot_dist(m['xgh'], m['xga'])
    ml_ah = _model_ah_line(dist)
    ml_ou = _model_ou_line(tot)
    ah_lad = mk.get('ah') or ([[mk['line'], mk['oh'], mk['oa']]] if mk.get('line') is not None else [])
    ou_lad = mk.get('ou') or ([[mk['tl'], mk['to'], mk['tu']]] if mk.get('tl') is not None else [])
    main_ah = mk.get('line'); main_ou = mk.get('tl')
    rows_ah = _pick_rows(ah_lad, main_ah if main_ah is not None else ml_ah, ml_ah)
    rows_ou = _pick_rows(ou_lad, main_ou if main_ou is not None else ml_ou, ml_ou)
    t1 = _ladder_html('ΑΣΙΑΤΙΚΟ (γηπ/φιλοξ)', rows_ah, lambda ln: _fair_pair(dist, ln), main_ah, ml_ah, True)
    t2 = _ladder_html('ΓΚΟΛ (over/under)', rows_ou, lambda ln: _fair_ou(tot, ln), main_ou, ml_ou, False)
    leg = ('<div style="font-size:8px;color:#5a6b8c;text-align:center;padding-top:5px">'
           '<span style="color:#f5b731">●</span> κυρια γραμμη αγορας &nbsp; '
           '<span style="color:#7ea2ff">◆</span> γραμμη μοντελου (ισορροπια) &nbsp;·&nbsp; '
           'μοντ = fair χωρις γκανιοτα</div>')
    return (f'<div style="display:flex;gap:34px;justify-content:center;flex-wrap:wrap;'
            f'padding:9px 0 4px">{t1}{t2}</div>{leg}')


def _lines_table(m, mk, draw_scale):
    """Μινι-πινακας δεξια απο το 1Χ2: γραμμη | μοντελο | αγορα, για ασιατικο & total."""
    mk = mk or {}
    rows = []
    if mk.get('line') is not None:
        ln = float(mk['line'])
        fp = _fair_pair(_eu_dist(m['xgh'], m['xga'], draw_scale), ln)
        rows.append(('AH', f'{ln:+.2f}',
                     f'{fp[0]:.2f}/{fp[1]:.2f}' if fp else '—',
                     f'{mk.get("oh", 0):.2f}/{mk.get("oa", 0):.2f}'))
    else:
        rows.append(('AH', f'{-(m["xgh"] - m["xga"]):+.2f}', 'μοντ γραμμη', '—'))
    if mk.get('tl') is not None:
        tl = float(mk['tl'])
        fo = _fair_ou(_tot_dist(m['xgh'], m['xga']), tl)
        rows.append(('O/U', f'{tl:.2f}',
                     f'{fo[0]:.2f}/{fo[1]:.2f}' if fo else '—',
                     f'{mk.get("to", 0):.2f}/{mk.get("tu", 0):.2f}'))
    else:
        rows.append(('O/U', f'{m["xgh"] + m["xga"]:.2f}', 'μοντ συνολο', '—'))
    body = ''.join(
        f'<div style="display:flex;gap:7px;align-items:baseline">'
        f'<span style="{_LT_CELL}width:24px;color:#5a6b8c;font-size:8px;text-align:right">{lbl}</span>'
        f'<span style="{_LT_CELL}width:38px;color:#e8edf8;font-weight:700">{ln}</span>'
        f'<span style="{_LT_CELL}width:72px;color:#7ea2ff">{mo}</span>'
        f'<span style="{_LT_CELL}width:72px;color:#8fa3c8">{ag}</span></div>'
        for lbl, ln, mo, ag in rows)
    head = (f'<div style="display:flex;gap:7px">'
            f'<span style="{_LT_CELL}width:24px"></span>'
            f'<span style="{_LT_CELL}width:38px;font-size:8px;color:#5a6b8c;text-transform:uppercase">γραμμη</span>'
            f'<span style="{_LT_CELL}width:72px;font-size:8px;color:#5a6b8c;text-transform:uppercase">μοντ</span>'
            f'<span style="{_LT_CELL}width:72px;font-size:8px;color:#5a6b8c;text-transform:uppercase">αγορ</span></div>')
    return f'<div style="display:flex;flex-direction:column;gap:4px">{head}{body}</div>'


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


def card_html(m, mk=None, draw_scale=EU_DRAW_SCALE_DEF):
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
<div class="tabs2">
  <button class="tbtn" onclick="tg('{m['mid']}','od',this)">Match odds</button>
  <button class="tbtn" onclick="tg('{m['mid']}','su',this)">Match summary</button>
</div>
<div id="od_{m['mid']}" class="pane" hidden>{_odds_pane(m, mk, draw_scale)}</div>
<div id="su_{m['mid']}" class="pane" hidden><div class="detail">
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
</div><div class="time">{_ko_fmt(m.get('utc'))} · αγωνιστικη {esc(m.get('round') or '?')}</div></div></div>"""


_TABS_CSS = """
<style>
.tabs2{display:flex;border-top:1px solid #1e2d47;}
.tbtn{flex:1;background:none;border:none;cursor:pointer;padding:5px;font-size:9px;color:#6b7fa3;
      letter-spacing:1px;text-transform:uppercase;font-family:'DM Sans',sans-serif;transition:all .12s;}
.tbtn:hover{color:#cdd8ee;background:#131c31;}
.tbtn.on{color:#e8edf8;background:#16203a;font-weight:600;}
.tbtn+.tbtn{border-left:1px solid #1e2d47;}
.pane{border-top:1px solid #16203a;}
</style>
<script>
function tg(mid, which, btn){
  var other = (which === 'od') ? 'su' : 'od';
  var me = document.getElementById(which + '_' + mid);
  var ot = document.getElementById(other + '_' + mid);
  var open = me.hidden;
  me.hidden = !open;
  if (ot) ot.hidden = true;
  var row = btn.parentElement;
  Array.prototype.forEach.call(row.children, function(b){ b.classList.remove('on'); });
  if (open) btn.classList.add('on');
}
</script>
"""


def cards_block(matches, odds=None, draw_scale=None):
    odds = odds or {}
    if draw_scale is None:
        d = load()
        draw_scale = float((d or {}).get('eu_draw_scale', EU_DRAW_SCALE_DEF))
    return cards.CARD_CSS + cards.FONTS + _TABS_CSS + '<div class="wrap">' + \
        ''.join(card_html(m, odds.get(str(m.get('mid'))), draw_scale) for m in matches) + '</div>'
