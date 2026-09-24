"""euroleague_view.py — 🏀 Euroleague (25/9/2026): προβλεψεις μοντελου v1 vs αγορα, σε match cards οπως το Europe tab.

Πηγες (ολα committed αρχεια στο repo, οπως τα υπολοιπα tabs):
  el_projections.json  — el_refresh.py (καθημερινα στο euro-refresh): ΟΛΗ η σεζον. Για παιγμενα ματς τα pts/margin/total
                         ειναι η PRE-GAME προβλεψη (walk-forward) + τελικο σκορ (hs/as_).
  el_odds_latest.json  — el_odds_scan.py (scanner): τρεχουσες γραμμες (Pinnacle + καλυτερες τιμες + διαμεσος).
  el_odds_hist.jsonl   — διαδρομη γραμμων· η τελευταια εγγραφη ΠΡΙΝ το τζαμπολ = «κλεισιμο» για παιγμενα ματς.
  toa_el_now.json      — ωμο TOA snapshot 24/9 12:05 UTC· fallback «πρωινη γραμμη, οχι closing» (1η αγωνιστικη).

Πιθανοτητες μοντελου απο Κανονικη κατανομη:  διαφορα ~ N(margin, σ_m),  συνολο ~ N(total, σ_t).
  Handicap γηπεδουχου L (π.χ. −2.5 = δινει 2.5): καλυπτει αν διαφορα + L > 0.
    μισες γραμμες (.5): P = Φ((margin+L)/σ_m)
    ακεραιες: διορθωση συνεχειας ±0.5 — P(νικη) = Φ((margin+L−0.5)/σ), P(ηττα) = Φ((−margin−L−0.5)/σ), P(push) = υπολοιπο
  Over T: μισες 1−Φ((T−total)/σ_t)· ακεραιες ιδια διορθωση ±0.5.
  Edge = P(νικη)·απoδοση + P(push)·1 − 1.  Fair = (P(νικη)+P(ηττα))/P(νικη)  (= 1/p στις μισες γραμμες).

ΕΚΔΟΣΕΙΣ: καθε ματς δινει λιστα εκδοσεων μοντελου (versions_of) — σημερα μονο 'v1' απο τα πεδια του ματς·
ενα μελλοντικο json με g['versions'] = {'v2': {pts_h, pts_a, margin, total, p_home}, ...} εμφανιζεται αυτοματα ως
επιπλεον στηλη/γραμμη (ιδια αγορα, ιδιο αποτελεσμα) — για συγκριση βελτιωσεων στα ΙΔΙΑ ματς.
"""
import os, json, math, datetime, email.utils

import cards  # CARD_CSS / FONTS / esc / _mkt_span — τα κοινα match cards
import lines_common as lc  # TABS_CSS (κουμπια καρτας + tg())

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ_F = os.path.join(ROOT, 'el_projections.json')
ODDS_F = os.path.join(ROOT, 'el_odds_latest.json')
HIST_F = os.path.join(ROOT, 'el_odds_hist.jsonl')
NOW_F = os.path.join(ROOT, 'toa_el_now.json')
FILES = (PROJ_F, ODDS_F, HIST_F, NOW_F)

EDGE_HI = 0.05          # edge ≥5% -> πρασινο (οπως το «value» των αλλων tabs)
esc = cards.esc
_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']
PHASE_LABEL = {'RS': 'Κανονικη περιοδος', 'PI': 'Play-in', 'PO': 'Playoffs', 'FF': 'Final Four'}

NOTES = [
    '**Μοντελο v1** (πρωτη εκδοση): ratings επιθεσης/αμυνας/ρυθμου ανα ομαδα απο box scores (ημιζωη 120 μερες, '
    'μεταφορα 70% απο περσι), εδρα 6 ποντοι/100 κατοχες. Αβεβαιοτητα γυρω απο την προβλεψη: σ διαφορας 11.5 · σ συνολου 16.7 '
    '(μετρημενες απο την αγορα E2023-25).',
    '**Συνολα χαμηλα:** το μοντελο βγαζει συστηματικα ~1-2 ποντους ΧΑΜΗΛΟΤΕΡΟ συνολο απο την αγορα — τα «under» edges '
    'θελουν αλατι.',
    '**Εδρα:** ισως λιγο ψηλη (6/100) — τα edges υπερ γηπεδουχων θελουν προσοχη.',
    '**Νεες ομαδες:** η Μπεσικτας ξεκινα με prior −2/100 (κατω απο τη μεση) — λιγα δεδομενα στις πρωτες αγωνιστικες.',
    '**Ουδετερα γηπεδα:** «εντος» ματς που παιζονται >300 χλμ απο την πολη της ομαδας (π.χ. ισραηλινες σε Σοφια/Βελιγραδι) '
    'μετρανε ως ουδετερα (χωρις εδρα).',
    '**Playoffs / Final Four:** δεν εχουν αξιολογηθει — μονο κανονικη περιοδος.',
    '**Γραμμη αγορας:** Pinnacle απο το Odds API (scanner). Για παιγμενα ματς: η τελευταια καταγραφη πριν το τζαμπολ '
    '(«κλεισιμο»)· αν δεν υπαρχει, η πρωινη γραμμη της 24/9 (οχι closing).',
]


# ---------------- φορτωση ----------------
def _json(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def files_mtime():
    """Κλειδι cache για το Streamlit: αλλαζει μολις ερθει νεο commit/αρχειο."""
    return tuple(os.path.getmtime(f) if os.path.exists(f) else 0 for f in FILES)


def _pdt(s):
    s = str(s)
    if len(s) == 16:
        s += ':00+00:00'
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))


def _closing_from_hist():
    """{code: τελευταια γραμμη hist με t < commence}."""
    out = {}
    for path in (HIST_F, os.path.join(ROOT, 'el_closing_backfill.jsonl')):   # scanner + συμπληρωμα ιστορικου (toa_el_backfill_closing.py)
      try:
        with open(path, encoding='utf-8') as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                    if _pdt(r['t']) >= _pdt(r['commence']):
                        continue
                except Exception:
                    continue
                k = str(r.get('code'))
                if k not in out or str(r['t']) >= str(out[k]['t']):
                    out[k] = r
      except Exception:
        pass
    return out


def _morning(proj):
    """toa_el_now.json (ωμο TOA) -> {code: rec} με την ιδια λογικη ταιριασματος του el_odds_scan."""
    raw = _json(NOW_F)
    if not raw or not proj:
        return {}, None
    try:
        import el_odds_scan as E
        when = email.utils.parsedate_to_datetime(raw.get('fetched'))
        games = [dict(code=g['code'], round=g.get('round'), utc=E._pdt(g['utc']), hcode=g['hcode'],
                      acode=g['acode'], home=g['home'], away=g['away']) for g in proj.get('games', [])]
        odds, _, _, _ = E.build_records(raw.get('data') or [], games, when, {})
        return odds, when.strftime('%d/%m %H:%M')
    except Exception:
        return {}, None


def load_all():
    """Ολα τα δεδομενα της σελιδας (dict) ή None αν λειπει το el_projections.json."""
    proj = _json(PROJ_F)
    if not proj or not proj.get('games'):
        return None
    lat = _json(ODDS_F) or {}
    morning, morning_when = _morning(proj)
    return dict(proj=proj, odds=(lat.get('odds') or {}) if isinstance(lat, dict) else {},
                scanned_at=lat.get('scanned_at') if isinstance(lat, dict) else None,
                closing=_closing_from_hist(), morning=morning, morning_when=morning_when)


# ---------------- μαθηματικα ----------------
def Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def round_half(x):
    return math.floor(x * 2 + 0.5) / 2.0


def _is_int(L):
    return abs(L - round(L)) < 1e-9


def spread_probs(margin, L, s):
    """(P νικη, P push, P ηττα) για τον γηπεδουχο στο handicap L."""
    if _is_int(L):
        pw = Phi((margin + L - 0.5) / s)
        pl = Phi((-margin - L - 0.5) / s)
        return pw, max(1.0 - pw - pl, 0.0), pl
    pw = Phi((margin + L) / s)
    return pw, 0.0, 1.0 - pw


def total_probs(total, T, s):
    """(P over, P push, P under) στη γραμμη T."""
    if _is_int(T):
        po = 1.0 - Phi((T + 0.5 - total) / s)
        pu = Phi((T - 0.5 - total) / s)
        return po, max(1.0 - po - pu, 0.0), pu
    po = 1.0 - Phi((T - total) / s)
    return po, 0.0, 1.0 - po


def edge(pw, pp, odds):
    return pw * odds + pp - 1.0 if odds else None


def fair(pw, pl):
    return (pw + pl) / pw if pw > 0 else None


# ---------------- εκδοσεις μοντελου ----------------
def versions_of(g):
    """[(ετικετα, dict προβλεψης)] — σημερα 1 (v1)· με g['versions'] = {v: {...}} προστιθενται αυτοματα."""
    out = [(g.get('version') or 'v1', g)]
    for v, p in (g.get('versions') or {}).items():
        if v != out[0][0] and isinstance(p, dict) and p.get('margin') is not None:
            out.append((v, p))
    return out


# ---------------- αγορα ανα ματς ----------------
def _from_rec(rec):
    pin, best = rec.get('pin') or {}, rec.get('best') or {}
    mk = dict(when=rec.get('when'), n_books=rec.get('n_books'), cons_line=(rec.get('cons') or {}).get('line'),
              cons_tl=(rec.get('cons') or {}).get('tl'), best=best, pin=pin)
    if pin.get('line') is not None:
        mk.update(line=pin['line'], oh=pin.get('oh'), oa=pin.get('oa'), src_sp='Pinnacle')
    elif best.get('line') is not None:
        mk.update(line=best['line'], oh=best.get('oh'), oa=best.get('oa'), src_sp='καλυτερη τιμη')
    if pin.get('tl') is not None:
        mk.update(tl=pin['tl'], to=pin.get('to'), tu=pin.get('tu'), src_tot='Pinnacle')
    elif best.get('tl') is not None:
        mk.update(tl=best['tl'], to=best.get('to'), tu=best.get('tu'), src_tot='καλυτερη τιμη')
    if pin.get('mh'):
        mk.update(mh=pin['mh'], ma=pin.get('ma'))
    elif best.get('mh'):
        mk.update(mh=best['mh'], ma=best.get('ma'))
    return mk


def _from_hist(r):
    best = {k: r.get(b) for k, b in (('line', 'bl'), ('oh', 'boh'), ('oa', 'boa'), ('tl', 'btl'), ('to', 'bto'),
                                      ('tu', 'btu'), ('mh', 'bmh'), ('ma', 'bma')) if r.get(b) is not None}
    pin = {k: r[k] for k in ('line', 'oh', 'oa', 'tl', 'to', 'tu', 'mh', 'ma') if r.get(k) is not None}
    return _from_rec(dict(when=r.get('t'), pin=pin, best=best, cons=dict(line=r.get('cl'), tl=r.get('ctl'))))


def market_for(g, data, now=None):
    """Αγορα για ενα ματς (dict με line/oh/oa/tl/to/tu/mh/ma + kind/label) ή None."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    k = str(g.get('code'))
    try:
        tipped = g.get('played') or _pdt(g['utc']) <= now
    except Exception:
        tipped = bool(g.get('played'))
    rec, hist, mor = data['odds'].get(k), data['closing'].get(k), data['morning'].get(k)
    order = (('hist', hist), ('rec', rec), ('mor', mor)) if tipped else (('rec', rec), ('hist', hist), ('mor', mor))
    for kind, x in order:
        if not x:
            continue
        mk = _from_hist(x) if kind == 'hist' else _from_rec(x)
        if mk.get('line') is None and mk.get('tl') is None and not mk.get('mh'):
            continue
        w = str(mk.get('when') or '')[:16].replace('T', ' ')
        if kind == 'mor':
            mk.update(kind='morning', label=f'πρωινη γραμμη {data.get("morning_when") or ""} UTC, οχι closing')
        elif tipped:
            mk.update(kind='closing', label=f'κλεισιμο (τελευταια καταγραφη πριν το τζαμπολ, {w} UTC)')
        else:
            mk.update(kind='live', label=f'τρεχουσα γραμμη (scan {w} UTC)')
        return mk
    return None


# ---------------- υπολογισμοι ανα ματς/εκδοση ----------------
def analyse(p, mk, sm, st):
    """Για μια εκδοση προβλεψης p και αγορα mk -> dict με fair γραμμες, edges, πλευρες."""
    m, T = float(p['margin']), float(p['total'])
    a = dict(fair_line=round_half(-m), fair_tot=round_half(T), p_home=float(p.get('p_home') or Phi(m / sm)))
    mk = mk or {}
    if mk.get('line') is not None:
        L = float(mk['line'])
        pw, pp, pl = spread_probs(m, L, sm)
        a.update(sp_ph=pw, sp_pp=pp, sp_pa=pl, sp_fh=fair(pw, pl), sp_fa=fair(pl, pw),
                 sp_eh=edge(pw, pp, mk.get('oh')), sp_ea=edge(pl, pp, mk.get('oa')),
                 sp_diff=-m - L, sp_side='home' if pw > pl else 'away')
    if mk.get('tl') is not None:
        TL = float(mk['tl'])
        po, pp, pu = total_probs(T, TL, st)
        a.update(t_po=po, t_pp=pp, t_pu=pu, t_fo=fair(po, pu), t_fu=fair(pu, po),
                 t_eo=edge(po, pp, mk.get('to')), t_eu=edge(pu, pp, mk.get('tu')),
                 t_diff=T - TL, t_side='over' if po > pu else 'under')
    if mk.get('mh'):
        ph = a['p_home']
        a.update(ml_eh=ph * mk['mh'] - 1.0, ml_ea=(1 - ph) * mk['ma'] - 1.0 if mk.get('ma') else None)
    return a


def grade(g, mk, a):
    """Για παιγμενο ματς: αποτελεσμα πλευρων vs αγορα και vs δικη μας γραμμη."""
    if not g.get('played') or g.get('hs') is None:
        return None
    M, S = g['hs'] - g['as_'], g['hs'] + g['as_']
    out = dict(M=M, S=S)
    if mk and mk.get('line') is not None:
        x = M + float(mk['line'])
        out['sp_res'] = 'home' if x > 0 else ('away' if x < 0 else 'push')
        if 'sp_side' in a:
            out['sp_ok'] = None if out['sp_res'] == 'push' else (out['sp_res'] == a['sp_side'])
    if mk and mk.get('tl') is not None:
        y = S - float(mk['tl'])
        out['t_res'] = 'over' if y > 0 else ('under' if y < 0 else 'push')
        if 't_side' in a:
            out['t_ok'] = None if out['t_res'] == 'push' else (out['t_res'] == a['t_side'])
    x2 = M + a['fair_line']
    out['our_sp_res'] = 'home' if x2 > 0 else ('away' if x2 < 0 else 'push')
    y2 = S - a['fair_tot']
    out['our_t_res'] = 'over' if y2 > 0 else ('under' if y2 < 0 else 'push')
    return out


# ---------------- μορφοποιηση ----------------
def _athens(dt):
    """UTC -> ωρα Ελλαδας (EET/EEST, κανονας ΕΕ: τελευταια Κυριακη Μαρτιου/Οκτωβριου 01:00 UTC)."""
    def last_sun(y, mo):
        d = datetime.datetime(y, mo, 31, 1, tzinfo=datetime.timezone.utc)
        return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
    dst = last_sun(dt.year, 3) <= dt < last_sun(dt.year, 10)
    return dt + datetime.timedelta(hours=3 if dst else 2)


def tip_fmt(utc):
    try:
        d = _athens(_pdt(utc))
        return f'{_DAYS[d.weekday()]} {d:%d/%m %H:%M}'
    except Exception:
        return str(utc)[:16]


def date_fmt(utc):
    try:
        return f'{_athens(_pdt(utc)):%d/%m}'
    except Exception:
        return ''


def _sgn(x, nd=1):
    return '—' if x is None else f'{x:+.{nd}f}'


def _pct(x):
    return '—' if x is None else f'{x * 100:+.0f}%'


def _edge_span(e):
    if e is None:
        return '<span class="ed none">—</span>'
    c = 'hi' if e >= EDGE_HI else ('pos' if e > 0 else 'neg')
    return f'<span class="ed {c}">{e * 100:+.1f}%</span>'


def _ok(v):
    if v is None:
        return '<span class="gr push">push</span>'
    return '<span class="gr win">✓</span>' if v else '<span class="gr loss">✗</span>'


_SIDE_GR = {'home': 'ΓΗΠ', 'away': 'ΦΙΛ', 'over': 'OVER', 'under': 'UNDER', 'push': 'PUSH'}

EL_CSS = """
<style>
.code{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:#f5a623;border:1px solid #f5a62355;
      border-radius:5px;padding:2px 5px;min-width:36px;text-align:center;}
.score{font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;color:#e8edf8;letter-spacing:.5px;}
.score small{font-size:8.5px;color:#6b7fa3;letter-spacing:1px;font-weight:400;display:block;text-align:center;}
.final{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:#f5b731;}
.badge{font-size:8.5px;border-radius:4px;padding:1px 5px;letter-spacing:.4px;}
.b-neu{color:#c98fa3;border:1px solid #c98fa355;}
.b-ver{color:#7ea2ff;border:1px solid #7ea2ff55;}
.b-val{color:#34d17a;border:1px solid #34d17a66;background:rgba(52,209,122,.10);font-weight:700;}
.b-mk{color:#8fa3c8;border:1px solid #26324e;}
.b-mor{color:#f5b731;border:1px solid #f5b73155;}
.ltab{width:100%;border-collapse:collapse;margin:8px 0 2px;font-size:10.5px;}
.ltab th{font-size:8px;color:#5a6b8c;font-weight:400;letter-spacing:.8px;text-transform:uppercase;padding:2px 5px;text-align:center;}
.ltab td{font-family:'JetBrains Mono',monospace;color:#cdd8ee;padding:3px 5px;text-align:center;border-top:1px solid #16203a;}
.ltab td.l{font-family:'DM Sans',sans-serif;color:#8fa3c8;text-align:left;font-size:10px;}
.ltab td.our{color:#7ea2ff;font-weight:700;}
.ltab td.mk{color:#e8edf8;font-weight:700;}
.ed{font-family:'JetBrains Mono',monospace;}
.ed.hi{color:#34d17a;font-weight:700;background:rgba(52,209,122,.13);border-radius:4px;padding:0 3px;}
.ed.pos{color:#8fa3c8;}
.ed.neg{color:#5a6b8c;}
.ed.none{color:#3d4a63;}
.gr{font-weight:700;}
.gr.win{color:#34d17a;}.gr.loss{color:#f04f5a;}.gr.push{color:#f5b731;font-size:9px;}
.lwrap{padding:0 15px 6px;overflow-x:auto;}
.mkrow{font-size:9px;color:#6b7fa3;text-align:center;padding:1px 0 5px;}
.pbar2{display:flex;height:4px;margin-top:9px;}
.pbar2 div:first-child{background:#34d17a;}.pbar2 div:last-child{background:#f04f5a;}
.btab{width:100%;border-collapse:collapse;font-size:10.5px;margin:4px 0;}
.btab th{font-size:8px;color:#5a6b8c;font-weight:400;letter-spacing:.8px;text-transform:uppercase;padding:2px 6px;}
.btab td{font-family:'JetBrains Mono',monospace;color:#cdd8ee;padding:2px 6px;text-align:center;}
.btab td.l{font-family:'DM Sans',sans-serif;color:#8fa3c8;text-align:left;}
.rt{width:100%;border-collapse:collapse;font-family:'DM Sans',sans-serif;font-size:12.5px;color:#cdd8ee;}
.rt th{font-size:9px;color:#5a6b8c;font-weight:400;letter-spacing:1px;text-transform:uppercase;padding:6px 8px;
       text-align:center;border-bottom:1px solid #1e2d47;}
.rt td{padding:5px 8px;text-align:center;border-bottom:1px solid #131c31;font-family:'JetBrains Mono',monospace;}
.rt td.nm{text-align:left;font-family:'DM Sans',sans-serif;}
.rt tr:hover td{background:#131c31;}
.rt .g{color:#34d17a;}.rt .r{color:#f04f5a;}.rt .n{color:#8fa3c8;}
</style>
"""


def _ratings_map(proj):
    return {r['code']: r for r in proj.get('ratings', [])}


# ---------------- ΚΑΡΤΑ — ιδιο στησιμο με Europe / Match Projections ----------------
_LT = 'display:inline-block;text-align:center;font-family:monospace;font-size:10px;'


def _logo(url):
    return f'<img class="logo" src="{esc(url)}" loading="lazy" onerror="this.style.visibility=\'hidden\'">' if url else ''


def _vig2(fair_pair, mkt_pair):
    """Φορεσε τη γκανιοτα της αγορας (ισομερως) στο fair ζευγος μας -> αμεσα συγκρισιμες τιμες."""
    if not fair_pair or None in fair_pair:
        return fair_pair
    try:
        S = 1.0 / mkt_pair[0] + 1.0 / mkt_pair[1]
    except Exception:
        S = 1.025
    return (fair_pair[0] / S, fair_pair[1] / S)


def _sp_fair(m, L, sm):
    pw, pp, pl = spread_probs(m, L, sm)
    return (fair(pw, pl), fair(pl, pw))


def _tot_fair(T, TL, st):
    po, pp, pu = total_probs(T, TL, st)
    return (fair(po, pu), fair(pu, po))


def _ladder(title, lines, fair_fn, main_ln, main_px, model_ln, signed):
    head = (f'<div style="display:flex;gap:7px"><span style="{_LT}width:10px"></span>'
            f'<span style="{_LT}width:44px;font-size:8px;color:#5a6b8c">ΓΡΑΜΜΗ</span>'
            f'<span style="{_LT}width:76px;font-size:8px;color:#5a6b8c">ΜΟΝΤ</span>'
            f'<span style="{_LT}width:76px;font-size:8px;color:#5a6b8c">ΑΓΟΡ</span></div>')
    body = ''
    for ln in lines:
        on_main = main_ln is not None and abs(ln - main_ln) < 0.01
        fp = _vig2(fair_fn(ln), main_px if main_px and None not in main_px else (1.95, 1.95))
        tag = '●' if on_main else ('◆' if abs(ln - model_ln) < 0.01 else '')
        tagc = '#f5b731' if tag == '●' else '#7ea2ff'
        lnc = tagc if tag else '#e8edf8'
        fp_s = f'{fp[0]:.2f}/{fp[1]:.2f}' if fp and None not in fp else '—'
        mo_s = f'{main_px[0]:.2f}/{main_px[1]:.2f}' if on_main and main_px and None not in main_px else '—'
        ln_s = f'{ln:+.1f}' if signed else f'{ln:.1f}'
        body += (f'<div style="display:flex;gap:7px;align-items:baseline">'
                 f'<span style="{_LT}width:10px;color:{tagc};font-size:8px">{tag}</span>'
                 f'<span style="{_LT}width:44px;color:{lnc};font-weight:700">{ln_s}</span>'
                 f'<span style="{_LT}width:76px;color:#7ea2ff">{fp_s}</span>'
                 f'<span style="{_LT}width:76px;color:#8fa3c8">{mo_s}</span></div>')
    return (f'<div style="display:flex;flex-direction:column;gap:4px">'
            f'<div style="font-size:9px;color:#6b7fa3;letter-spacing:1.5px;text-align:center">{title}</div>{head}{body}</div>')


def _odds_pane(g, mk, sm, st):
    """Match odds: σκαλα handicap (γηπ/φιλοξ) και συνολου (over/under), μοντελο ΜΕ τη γκανιοτα της αγορας vs αγορα."""
    mk = mk or {}
    m, T = float(g['margin']), float(g['total'])
    ml_sp, ml_t = round_half(-m), round_half(T)
    c_sp = mk.get('line') if mk.get('line') is not None else ml_sp
    c_t = mk.get('tl') if mk.get('tl') is not None else ml_t
    sp_lines = sorted({round(c_sp + k, 1) for k in (-2, -1, 0, 1, 2)} | {ml_sp})
    t_lines = sorted({round(c_t + k, 1) for k in (-4, -2, 0, 2, 4)} | {ml_t})
    t1 = _ladder('HANDICAP (γηπ/φιλοξ)', sp_lines, lambda L: _sp_fair(m, L, sm), mk.get('line'),
                 (mk.get('oh'), mk.get('oa')) if mk.get('oh') else None, ml_sp, True)
    t2 = _ladder('ΣΥΝΟΛΟ ΠΟΝΤΩΝ (over/under)', t_lines, lambda L: _tot_fair(T, L, st), mk.get('tl'),
                 (mk.get('to'), mk.get('tu')) if mk.get('to') else None, ml_t, False)
    src = f' · αγορα: {esc(mk.get("label"))}' if mk.get('label') else ' · αγορα: καμια γραμμη ακομα'
    leg = ('<div style="font-size:8px;color:#5a6b8c;text-align:center;padding-top:5px">'
           '<span style="color:#f5b731">●</span> κυρια γραμμη αγορας &nbsp; <span style="color:#7ea2ff">◆</span> γραμμη μοντελου &nbsp;·&nbsp; '
           'μοντ = τιμη μοντελου ΜΕ τη γκανιοτα της αγορας (αμεσα συγκρισιμη)' + src + '</div>')
    return (f'<div style="display:flex;gap:34px;justify-content:center;flex-wrap:wrap;padding:9px 0 4px">'
            f'{t1}{t2}</div>{leg}')


def _summary_pane(g, rm):
    def side(code, name, lab):
        r = rm.get(code) or {}
        return (f'<div class="inp"><div class="h">{esc(name)} ({lab})</div>'
                f'<div class="row"><span>Rating (net)</span><b class="acc">{r.get("net", 0):+.2f}</b></div>'
                f'<div class="row"><span>Επιθεση O</span><b>{r.get("O", 0):+.2f}</b></div>'
                f'<div class="row"><span>Αμυνα D</span><b>{r.get("D", 0):+.2f}</b></div>'
                f'<div class="row"><span>Ρυθμος</span><b>{r.get("pace", 0):+.2f}</b></div>'
                f'<div class="row"><span>Φετινα ματς</span><b>{r.get("games", 0)}</b></div></div>')
    vers = ''.join(f'<div class="row"><span>Εκδοση {esc(v)}</span><b>{float(p["pts_h"]):.1f} – {float(p["pts_a"]):.1f} · '
                   f'γραμμη {round_half(-float(p["margin"])):+.1f} · συνολο {round_half(float(p["total"])):.1f}</b></div>'
                   for v, p in versions_of(g))
    return (f'<div class="detail">{side(g["hcode"], g["home"], "home")}{side(g["acode"], g["away"], "away")}</div>'
            f'<div class="detail" style="padding-top:0"><div class="inp" style="flex:1">{vers}</div></div>')


def card_html(g, data, rm, now=None):
    proj = data['proj']
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    mk = market_for(g, data, now) or {}
    ph = float(g.get('p_home') or Phi(float(g['margin']) / sm)); pa = 1 - ph
    hw, aw = ph * 100, pa * 100
    hc = '#34d17a' if hw > aw else ('#f04f5a' if hw < aw else '#8fa3c8')
    ac = '#34d17a' if aw > hw else ('#f04f5a' if aw < hw else '#8fa3c8')
    hbg, abg = cards._BG[hc], cards._BG[ac]
    f1, f2 = 1 / max(ph, 1e-6), 1 / max(pa, 1e-6)
    if mk.get('mh') and mk.get('ma'):
        f1, f2 = _vig2((f1, f2), (mk['mh'], mk['ma']))
    odds = (f'<div class="oddsrow"><span class="rl">μοντ</span><div class="odds">'
            f'<span>{f1:.2f}</span><span>{f2:.2f}</span></div></div>')
    if mk.get('mh'):
        odds += (f'<div class="oddsrow"><span class="rl">αγορ</span><div class="odds">'
                 f'{cards._mkt_span(f1, mk.get("mh"))}{cards._mkt_span(f2, mk.get("ma"))}</div></div>')
    rh, ra = rm.get(g['hcode']) or {}, rm.get(g['acode']) or {}
    uid = f"el{g['code']}"
    neu = ' · <span style="color:#f5b731">ουδετερο γηπεδο</span>' if g.get('neutral') else ''
    return f"""
<div class="card"><div class="sum">
  <div class="team">
    <div class="thead">{_logo(g.get('hcrest'))}<div class="tn">{esc(g['home'])}</div></div>
    <div class="meta"><span class="xg">προβλ. {float(g['pts_h']):.1f}</span><span class="xg" style="opacity:.7">rating {rh.get('net', 0):+.1f}</span></div></div>
  <div class="mid">
    <div class="lbls"><span>Home</span><span>Away</span></div>
    <div class="pills"><div class="pill" style="background:{hbg};color:{hc};border:1px solid {hc}44">{hw:.0f}%</div>
      <div class="pill" style="background:{abg};color:{ac};border:1px solid {ac}44">{aw:.0f}%</div></div>
    <div class="oddswrap">{odds}</div>
  </div>
  <div class="team away">
    <div class="thead">{_logo(g.get('acrest'))}<div class="tn">{esc(g['away'])}</div></div>
    <div class="meta"><span class="xg" style="opacity:.7">rating {ra.get('net', 0):+.1f}</span><span class="xg">προβλ. {float(g['pts_a']):.1f}</span></div></div>
</div>
<div class="pbar"><div style="width:{hw}%"></div><div style="width:{aw}%"></div></div>
<div class="tabs2">
  <button class="tbtn" onclick="tg('{uid}','od',this)">Match odds</button>
  <button class="tbtn" onclick="tg('{uid}','su',this)">Match summary</button>
</div>
<div id="od_{uid}" class="pane" hidden>{_odds_pane(g, mk, sm, st)}</div>
<div id="su_{uid}" class="pane" hidden>{_summary_pane(g, rm)}</div>
<div class="time">{tip_fmt(g.get('utc'))} · {esc(g.get('venue') or '')}{neu} · αγωνιστικη {esc(g.get('round'))}</div></div>"""


_TABS_CSS = """
<style>
.tabs2{display:flex;border-top:1px solid #1e2d47;}
.tbtn{flex:1;background:none;border:none;cursor:pointer;padding:5px;font-size:9px;color:#6b7fa3;
      letter-spacing:1px;text-transform:uppercase;font-family:'DM Sans',sans-serif;transition:all .12s;}
.tbtn:hover{color:#cdd8ee;background:#131c31;}
.tbtn.on{color:#e8edf8;background:#16203a;font-weight:600;}
.tbtn+.tbtn{border-left:1px solid #1e2d47;}
.pane{border-top:1px solid #16203a;}
.pbar div:nth-child(2){background:#f04f5a;}
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


def cards_block(games, data, now=None):
    rm = _ratings_map(data['proj'])
    return (cards.CARD_CSS + cards.FONTS + _TABS_CSS + '<div class="wrap">'
            + ''.join(card_html(g, data, rm, now) for g in games) + '</div>')


def block_height(games):
    return min(len(games) * 150 + 40, 6000)


def visible_games(proj):
    """Επερχομενα ματς + ΜΟΝΟ η 1η αγωνιστικη απο τα παιγμενα (αιτημα Στελιου 25/9: για να φαινεται
    πως αλλαζει η προβλεψη με καθε βελτιωση του μοντελου — οχι αποτελεσματα)."""
    return [g for g in proj.get('games', []) if not g.get('played') or (g.get('phase', 'RS') == 'RS' and g.get('round') == 1)]


# ---------------- αγωνιστικες ----------------
def rounds(proj):
    """[(phase, round)] με σειρα ημερομηνιας."""
    first = {}
    for g in proj.get('games', []):
        key = (g.get('phase') or 'RS', g.get('round'))
        if key not in first or str(g['utc']) < first[key]:
            first[key] = str(g['utc'])
    return sorted(first, key=lambda k: first[k])


def round_games(proj, key):
    return sorted([g for g in proj.get('games', []) if ((g.get('phase') or 'RS'), g.get('round')) == key],
                  key=lambda g: (str(g['utc']), str(g.get('code'))))


def default_round(proj, keys):
    """Τρεχουσα/επομενη αγωνιστικη = η πρωτη με ματς που δεν εχει παιχτει."""
    for k in keys:
        if any(not g.get('played') for g in round_games(proj, k)):
            return k
    return keys[-1] if keys else None


def round_label(proj, key):
    gs = round_games(proj, key)
    ph, r = key
    d0, d1 = date_fmt(gs[0]['utc']), date_fmt(gs[-1]['utc'])
    npl = sum(1 for g in gs if g.get('played'))
    st = 'παιχτηκε' if npl == len(gs) else (f'{npl}/{len(gs)} παιχτηκαν' if npl else 'επερχομενη')
    phs = '' if ph == 'RS' else f'{PHASE_LABEL.get(ph, ph)} · '
    return f'{phs}Αγωνιστικη {r} · {d0}' + (f'–{d1}' if d1 != d0 else '') + f' · {st}'


def round_summary(games, data):
    """Απολογισμος παιγμενων ματς της αγωνιστικης (v1): πλευρα μας στη γραμμη αγορας + σφαλμα προβλεψης."""
    proj = data['proj']
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    sp = [0, 0, 0]; tt = [0, 0, 0]; em = []; et = []; n = 0
    for g in games:
        if not g.get('played') or g.get('hs') is None:
            continue
        n += 1
        mk = market_for(g, data)
        a = analyse(g, mk, sm, st)
        gr = grade(g, mk, a)
        em.append(gr['M'] - float(g['margin'])); et.append(gr['S'] - float(g['total']))
        if 'sp_ok' in gr:
            sp[0 if gr['sp_ok'] else (2 if gr['sp_ok'] is None else 1)] += 1
        if 't_ok' in gr:
            tt[0 if gr['t_ok'] else (2 if gr['t_ok'] is None else 1)] += 1
    if not n:
        return None
    mae_m = sum(abs(x) for x in em) / n; bias_t = sum(et) / n
    return (f'Παιγμενα {n} · δικη μας πλευρα στη γραμμη αγορας — handicap {sp[0]}-{sp[1]}'
            + (f'-{sp[2]}' if sp[2] else '') + f' · συνολο {tt[0]}-{tt[1]}' + (f'-{tt[2]}' if tt[2] else '')
            + f' · μεσο |σφαλμα διαφορας| {mae_m:.1f} π. · συνολο πραγματικο − προβλεψη {bias_t:+.1f} π. (v1)')


# ---------------- ratings ----------------
def ratings_html(proj):
    rows = ''
    for i, r in enumerate(sorted(proj.get('ratings', []), key=lambda x: -x['net']), 1):
        cn = 'g' if r['net'] > 0 else ('r' if r['net'] < 0 else 'n')
        co = 'g' if r['O'] > 0 else ('r' if r['O'] < 0 else 'n')
        cd = 'g' if r['D'] < 0 else ('r' if r['D'] > 0 else 'n')
        rows += (f'<tr><td class="n">{i}</td><td><span class="code">{esc(r["code"])}</span></td>'
                 f'<td class="nm">{esc(r["name"])}</td><td class="{cn}"><b>{r["net"]:+.2f}</b></td>'
                 f'<td class="{co}">{r["O"]:+.2f}</td><td class="{cd}">{r["D"]:+.2f}</td>'
                 f'<td class="n">{r["pace"]:+.2f}</td><td class="n">{r["games"]}</td></tr>')
    head = ('<tr><th>#</th><th></th><th style="text-align:left">Ομαδα</th><th>Net</th><th>Επιθεση O</th>'
            '<th>Αμυνα D</th><th>Ρυθμος</th><th>Ματς</th></tr>')
    return cards.CARD_CSS + cards.FONTS + EL_CSS + f'<table class="rt">{head}{rows}</table>'


def ratings_height(proj):
    return 34 * len(proj.get('ratings', [])) + 50
