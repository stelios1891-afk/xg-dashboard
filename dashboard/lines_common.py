"""lines_common.py — Κοινη μηχανη για τα Match Odds panes (σκαλες AH/O-U, fair+γκανιοτα).

Χρησιμοποιειται απο τα ΕΓΧΩΡΙΑ cards (cards.py)· το europe_view.py εχει προς το παρον
δικο του αντιγραφο (ιδια μαθηματικα + ευρωπαικο draw scale) — cleanup αργοτερα.
Standalone: εξαρταται μονο απο picks (gd_dist, DRAW_BOOST).
"""
import math

import picks

_LT_CELL = 'display:inline-block;text-align:center;font-family:monospace;font-size:10px;'


def match_dist(xgh, xga, draw_scale=1.0):
    """Κατανομη goal difference (gd_dist)· προαιρετικο scale στην ισοπαλια (Ευρωπη)."""
    dist = picks.gd_dist(max(xgh, 0.05), max(xga, 0.05))
    if draw_scale == 1.0:
        return dist
    px = dist.get(0, 0.0)
    if px <= 0 or px >= 1:
        return dist
    k = (1.0 - draw_scale * px) / (1.0 - px)
    return {g: (p * draw_scale if g == 0 else p * k) for g, p in dist.items()}


def tot_dist(xgh, xga):
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


def cover_q(dist, side, line):
    """Quarter-aware cover (x.25/x.75 σπασμενα σε 2 μισες γραμμες — ΟΧΙ το picks.p_cover)."""
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


def fair_pair(dist, line):
    out = []
    for side, ln in ((1, line), (-1, -line)):
        pw, pp = cover_q(dist, side, ln)
        if pw <= 0:
            return None
        out.append(1.0 + (1.0 - pw - pp) / pw)
    return out


def p_over(tot, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    po = pu = 0.0
    for L in parts:
        for t, p in tot.items():
            if t > L + 0.01:
                po += p / len(parts)
            elif t < L - 0.01:
                pu += p / len(parts)
    return po, pu


def fair_ou(tot, line):
    po, pu = p_over(tot, line)
    if po <= 0 or pu <= 0:
        return None
    push = max(1.0 - po - pu, 0.0)
    return (1.0 + (1.0 - po - push) / po, 1.0 + (1.0 - pu - push) / pu)


def model_ah_line(dist):
    best, bd = 0.0, 9e9
    for q in range(-16, 17):
        ln = q / 4.0
        pw, pp = cover_q(dist, 1, ln)
        pl = 1.0 - pw - pp
        if pw > 0 and abs(pw - pl) < bd:
            bd, best = abs(pw - pl), ln
    return best


def model_ou_line(tot):
    best, bd = 2.5, 9e9
    for q in range(4, 25):
        ln = q / 4.0
        po, pu = p_over(tot, ln)
        if po > 0 and pu > 0 and abs(po - pu) < bd:
            bd, best = abs(po - pu), ln
    return best


def overround(pair):
    try:
        return 1.0 / pair[0] + 1.0 / pair[1]
    except (TypeError, ZeroDivisionError, IndexError):
        return None


def vig(fair, S):
    """Φορεσε γκανιοτα S στο fair ζευγος (ισομερης): Σ(1/o') = S."""
    if not fair or not S:
        return fair
    return [o / S for o in fair]


def pick_rows(ladder, center, extra, span=1.01, cap=7):
    lines = [r[0] for r in ladder]
    keep = [ln for ln in lines if center is None or abs(ln - center) <= span]
    if len(keep) > cap:
        keep = sorted(keep, key=lambda x: abs(x - (center or 0)))[:cap]
    if extra is not None and extra not in keep:
        keep.append(extra)
    have = {r[0]: (r[1], r[2]) for r in ladder}
    return [(ln, have.get(ln)) for ln in sorted(keep)]


def ladder_html(title, rows, fair_fn, main_ln, model_ln, signed, s_fallback=None):
    body = ''
    for ln, mo in rows:
        fp = vig(fair_fn(ln), overround(mo) or s_fallback or 1.025)
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


def odds_pane(xgh, xga, mk, draw_scale=1.0):
    """Το κουτι Match Odds: σκαλες AH & O/U, μοντελο (με γκανιοτα αγορας) vs αγορα."""
    mk = mk or {}
    dist = match_dist(xgh, xga, draw_scale)
    tot = tot_dist(xgh, xga)
    ml_ah = model_ah_line(dist)
    ml_ou = model_ou_line(tot)
    ah_lad = mk.get('ah') or ([[mk['line'], mk['oh'], mk['oa']]] if mk.get('line') is not None else [])
    ou_lad = mk.get('ou') or ([[mk['tl'], mk['to'], mk['tu']]] if mk.get('tl') is not None else [])
    main_ah = mk.get('line'); main_ou = mk.get('tl')
    rows_ah = pick_rows(ah_lad, main_ah if main_ah is not None else ml_ah, ml_ah)
    rows_ou = pick_rows(ou_lad, main_ou if main_ou is not None else ml_ou, ml_ou)
    s_ah = overround((mk.get('oh'), mk.get('oa'))) if mk.get('oh') else None
    s_ou = overround((mk.get('to'), mk.get('tu'))) if mk.get('to') else None
    t1 = ladder_html('ΑΣΙΑΤΙΚΟ (γηπ/φιλοξ)', rows_ah, lambda ln: fair_pair(dist, ln),
                     main_ah, ml_ah, True, s_ah)
    t2 = ladder_html('ΓΚΟΛ (over/under)', rows_ou, lambda ln: fair_ou(tot, ln),
                     main_ou, ml_ou, False, s_ou)
    leg = ('<div style="font-size:8px;color:#5a6b8c;text-align:center;padding-top:5px">'
           '<span style="color:#f5b731">●</span> κυρια γραμμη αγορας &nbsp; '
           '<span style="color:#7ea2ff">◆</span> γραμμη μοντελου (ισορροπια) &nbsp;·&nbsp; '
           'μοντ = τιμη μοντελου ΜΕ τη γκανιοτα της αγορας (αμεσα συγκρισιμη)</div>')
    return (f'<div style="display:flex;gap:34px;justify-content:center;flex-wrap:wrap;'
            f'padding:9px 0 4px">{t1}{t2}</div>{leg}')


TABS_CSS = """
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
