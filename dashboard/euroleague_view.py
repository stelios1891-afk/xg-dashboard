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
    try:
        with open(HIST_F, encoding='utf-8') as fh:
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


def _team_meta(r):
    if not r:
        return ''
    return (f'<span>net <b style="color:{"#34d17a" if r["net"] >= 0 else "#f04f5a"}">{r["net"]:+.1f}</b></span>'
            f'<span>O {r["O"]:+.1f}</span><span>D {r["D"]:+.1f}</span>')


def _lines_table(g, mk, vers, sm, st, gr_by_ver):
    """Πινακας γραμμων: ανα αγορα (handicap/συνολο) × εκδοση μοντελου."""
    has_mk = bool(mk)
    played = bool(g.get('played'))
    head = ('<tr><th></th><th>εκδ.</th><th>γραμμη μας</th><th>αγορα</th><th>διαφωνια</th><th>τιμες αγορας</th>'
            '<th>fair μας</th><th>edge γηπ/over</th><th>edge φιλ/under</th>'
            + ('<th>αποτελεσμα</th>' if played else '') + '</tr>')
    rows = ''
    for i, (v, p, a) in enumerate(vers):
        gr = gr_by_ver.get(v)
        # --- handicap ---
        if has_mk and mk.get('line') is not None:
            mk_s = f'{float(mk["line"]):+.1f}'
            pr_s = f'{mk.get("oh") or 0:.2f} / {mk.get("oa") or 0:.2f}'
            fr_s = f'{a["sp_fh"]:.2f} / {a["sp_fa"]:.2f}' if a.get('sp_fh') and a.get('sp_fa') else '—'
            eh, ea, df = _edge_span(a.get('sp_eh')), _edge_span(a.get('sp_ea')), _sgn(a.get('sp_diff'))
        else:
            mk_s = pr_s = fr_s = '—'; eh = ea = _edge_span(None); df = '—'
        res = ''
        if played:
            if gr and gr.get('sp_res'):
                res = (f'κάλυψε <b>{_SIDE_GR[gr["sp_res"]]}</b> · δικη μας πλευρα '
                       f'({_SIDE_GR.get(a.get("sp_side"), "—")}) {_ok(gr.get("sp_ok"))}')
            elif gr:
                res = f'vs γραμμη μας: <b>{_SIDE_GR[gr["our_sp_res"]]}</b>'
            res = f'<td class="l">{res}</td>'
        rows += (f'<tr><td class="l">Handicap γηπ</td><td class="l">{esc(v)}</td>'
                 f'<td class="our">{a["fair_line"]:+.1f}</td><td class="mk">{mk_s}</td><td>{df}</td>'
                 f'<td>{pr_s}</td><td>{fr_s}</td><td>{eh}</td><td>{ea}</td>{res}</tr>')
        # --- συνολο ---
        if has_mk and mk.get('tl') is not None:
            mk_s = f'{float(mk["tl"]):.1f}'
            pr_s = f'{mk.get("to") or 0:.2f} / {mk.get("tu") or 0:.2f}'
            fr_s = f'{a["t_fo"]:.2f} / {a["t_fu"]:.2f}' if a.get('t_fo') and a.get('t_fu') else '—'
            eo, eu, df = _edge_span(a.get('t_eo')), _edge_span(a.get('t_eu')), _sgn(a.get('t_diff'))
        else:
            mk_s = pr_s = fr_s = '—'; eo = eu = _edge_span(None); df = '—'
        res = ''
        if played:
            if gr and gr.get('t_res'):
                res = (f'<b>{_SIDE_GR[gr["t_res"]]}</b> · δικη μας πλευρα '
                       f'({_SIDE_GR.get(a.get("t_side"), "—")}) {_ok(gr.get("t_ok"))}')
            elif gr:
                res = f'vs γραμμη μας: <b>{_SIDE_GR[gr["our_t_res"]]}</b>'
            res = f'<td class="l">{res}</td>'
        rows += (f'<tr><td class="l">Συνολο</td><td class="l">{esc(v)}</td>'
                 f'<td class="our">{a["fair_tot"]:.1f}</td><td class="mk">{mk_s}</td><td>{df}</td>'
                 f'<td>{pr_s}</td><td>{fr_s}</td><td>{eo}</td><td>{eu}</td>{res}</tr>')
    return f'<div class="lwrap"><table class="ltab">{head}{rows}</table></div>'


def _market_pane(mk):
    if not mk:
        return ('<div style="padding:10px 16px;font-size:11px;color:#6b7fa3">Δεν υπαρχει ακομα γραμμη αγορας για αυτο το '
                'ματς (ο scanner την πιανει οταν το ματς μπει στο 48ωρο).</div>')
    pin, best = mk.get('pin') or {}, mk.get('best') or {}

    def v(d, k, f='{:.2f}'):
        return f.format(d[k]) if d.get(k) is not None else '—'

    def bk(k):
        return f' <span style="color:#5a6b8c;font-size:8.5px">{esc(best.get(k + "_bk"))}</span>' if best.get(k + '_bk') else ''
    rows = (f'<tr><td class="l">Pinnacle</td><td>{v(pin, "line", "{:+.1f}")}</td><td>{v(pin, "oh")} / {v(pin, "oa")}</td>'
            f'<td>{v(pin, "tl", "{:.1f}")}</td><td>{v(pin, "to")} / {v(pin, "tu")}</td><td>{v(pin, "mh")} / {v(pin, "ma")}</td></tr>'
            f'<tr><td class="l">Καλυτερη τιμη (ολα τα βιβλια, ιδια γραμμη)</td><td>{v(best, "line", "{:+.1f}")}</td>'
            f'<td>{v(best, "oh")}{bk("oh")} / {v(best, "oa")}{bk("oa")}</td><td>{v(best, "tl", "{:.1f}")}</td>'
            f'<td>{v(best, "to")}{bk("to")} / {v(best, "tu")}{bk("tu")}</td>'
            f'<td>{v(best, "mh")}{bk("mh")} / {v(best, "ma")}{bk("ma")}</td></tr>'
            f'<tr><td class="l">Διαμεσος γραμμη βιβλιων</td>'
            f'<td>{v(mk, "cons_line", "{:+.1f}")}</td><td></td>'
            f'<td>{v(mk, "cons_tl", "{:.1f}")}</td><td></td><td></td></tr>')
    head = ('<tr><th></th><th>handicap γηπ</th><th>γηπ / φιλ</th><th>συνολο</th><th>over / under</th>'
            '<th>νικη γηπ / φιλ</th></tr>')
    nb = f' · {mk["n_books"]} βιβλια' if mk.get('n_books') else ''
    return (f'<div style="padding:6px 16px 10px"><table class="btab">{head}{rows}</table>'
            f'<div class="mkrow">{esc(mk.get("label", ""))}{nb}</div></div>')


def _summary_pane(g, rm, vers, sm, st):
    rh, ra = rm.get(g['hcode']), rm.get(g['acode'])

    def inp(r, nm, side):
        if not r:
            return f'<div class="inp"><div class="h">{esc(nm)} ({side})</div><div class="row"><span>—</span></div></div>'
        return (f'<div class="inp"><div class="h">{esc(nm)} ({side})</div>'
                f'<div class="row"><span>Net (ποντοι/100)</span><b class="acc">{r["net"]:+.2f}</b></div>'
                f'<div class="row"><span>Επιθεση O</span><b>{r["O"]:+.2f}</b></div>'
                f'<div class="row"><span>Αμυνα D (αρνητικο = καλη)</span><b>{r["D"]:+.2f}</b></div>'
                f'<div class="row"><span>Ρυθμος (κατοχες ±)</span><b>{r["pace"]:+.2f}</b></div>'
                f'<div class="row"><span>Ματς φετος</span><b>{r["games"]}</b></div></div>')
    p = vers[0][1]
    extra = (f'<div class="row"><span>Κατοχες (προβλ.)</span><b>{p.get("poss", "—")}</b></div>'
             f'<div class="row"><span>σ διαφορας / συνολου</span><b>{sm} / {st}</b></div>'
             f'<div class="row"><span>Εδρα</span><b>{"ουδετερο (0)" if g.get("neutral") else "κανονικη"}</b></div>')
    return (f'<div class="detail">{inp(rh, g["home"], "home")}{inp(ra, g["away"], "away")}</div>'
            f'<div style="padding:0 16px 12px"><div class="inp">{extra}</div></div>')


def card_html(g, data, rm, now=None):
    proj = data['proj']
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    mk = market_for(g, data, now)
    vers = [(v, p, analyse(p, mk, sm, st)) for v, p in versions_of(g)]
    gr_by_ver = {v: grade(g, mk, a) for v, p, a in vers}
    v0, p0, a0 = vers[0]
    hw = a0['p_home'] * 100; aw = 100 - hw
    hc = '#34d17a' if hw > aw else ('#f04f5a' if hw < aw else '#8fa3c8')
    ac = '#34d17a' if aw > hw else ('#f04f5a' if aw < hw else '#8fa3c8')
    hbg, abg = cards._BG[hc], cards._BG[ac]
    # προβλεπομενο σκορ ανα εκδοση (στηλες) — v2 κλπ μπαινουν διπλα αυτοματα
    scores = ''.join(f'<div class="score"><small>{esc(v)}</small>{p["pts_h"]:.1f} – {p["pts_a"]:.1f}</div>'
                     for v, p, _ in vers)
    fin = ''
    if g.get('played') and g.get('hs') is not None:
        fin = f'<div class="final">ΤΕΛΙΚΟ {g["hs"]} – {g["as_"]}</div>'
    # νικη: fair μοντελου (με τη γκανιοτα της αγορας, οπως στα αλλα tabs) vs αγορα
    ph = a0['p_home']
    s2 = (1.0 / mk['mh'] + 1.0 / mk['ma']) if mk and mk.get('mh') and mk.get('ma') else None
    fo_h, fo_a = (1 / ph, 1 / (1 - ph)) if 0 < ph < 1 else (None, None)
    if s2 and fo_h:
        fo_h, fo_a = fo_h / s2, fo_a / s2
    odds = (f'<div class="oddsrow"><span class="rl">μοντ</span><div class="odds">'
            f'<span>{fo_h:.2f}</span><span>{fo_a:.2f}</span></div></div>') if fo_h else ''
    if mk and mk.get('mh'):
        odds += (f'<div class="oddsrow"><span class="rl">αγορ</span><div class="odds">'
                 f'{cards._mkt_span(fo_h, mk.get("mh"))}{cards._mkt_span(fo_a, mk.get("ma"))}</div></div>')
    # badges
    badges = f'<span class="badge b-ver">μοντελο {esc(" + ".join(v for v, _, _ in vers))}</span>'
    if g.get('neutral'):
        badges += ' <span class="badge b-neu">ουδετερο γηπεδο</span>'
    if mk:
        cls = 'b-mor' if mk.get('kind') == 'morning' else 'b-mk'
        src = mk.get('src_sp') or mk.get('src_tot') or ''
        badges += f' <span class="badge {cls}" title="{esc(mk.get("label", ""))}">{esc(src)} · {esc(mk.get("label", ""))}</span>'
    else:
        badges += ' <span class="badge b-mk">χωρις γραμμη αγορας</span>'
    vals = []
    for side, key, lbl in (('sp_eh', 'line', 'ΓΗΠ'), ('sp_ea', 'line', 'ΦΙΛ'), ('t_eo', 'tl', 'OVER'), ('t_eu', 'tl', 'UNDER')):
        e = a0.get(side)
        if e is not None and e >= EDGE_HI:
            vals.append(f'{lbl} {e * 100:+.0f}%')
    if vals and not g.get('played'):
        badges += f' <span class="badge b-val">edge ≥5%: {esc(" · ".join(vals))}</span>'
    k = f'el{g["code"]}'
    return f"""
<div class="card"><div class="sum">
  <div class="team">
    <div class="thead"><span class="code">{esc(g['hcode'])}</span><div class="tn">{esc(g['home'])}</div></div>
    <div class="meta">{_team_meta(rm.get(g['hcode']))}</div></div>
  <div class="mid">
    <div class="lbls"><span>Home</span><span>Away</span></div>
    <div class="pills"><div class="pill" style="background:{hbg};color:{hc};border:1px solid {hc}44">{hw:.0f}%</div>
      <div class="pill" style="background:{abg};color:{ac};border:1px solid {ac}44">{aw:.0f}%</div></div>
    <div style="display:flex;gap:14px;justify-content:center">{scores}</div>{fin}
    <div class="oddswrap">{odds}</div>
  </div>
  <div class="team away">
    <div class="thead"><span class="code">{esc(g['acode'])}</span><div class="tn">{esc(g['away'])}</div></div>
    <div class="meta">{_team_meta(rm.get(g['acode']))}</div></div>
</div>
<div class="pbar2"><div style="width:{hw}%"></div><div style="width:{aw}%"></div></div>
{_lines_table(g, mk, vers, sm, st, gr_by_ver)}
<div class="mkrow">{badges}</div>
<div class="tabs2">
  <button class="tbtn" onclick="tg('{k}','od',this)">Αγορα αναλυτικα</button>
  <button class="tbtn" onclick="tg('{k}','su',this)">Στοιχεια ομαδων</button>
</div>
<div id="od_{k}" class="pane" hidden>{_market_pane(mk)}</div>
<div id="su_{k}" class="pane" hidden>{_summary_pane(g, rm, [(v, p) for v, p, _ in vers], sm, st)}</div>
<div class="time" style="padding:4px 0 7px">{tip_fmt(g.get('utc'))} (ωρα Ελλαδας) · {esc(g.get('venue') or '—')} ·
  αγωνιστικη {esc(g.get('round'))}{'' if g.get('phase') in (None, 'RS') else ' · ' + esc(PHASE_LABEL.get(g['phase'], g['phase']))}</div>
</div>"""


def cards_block(games, data, now=None):
    rm = _ratings_map(data['proj'])
    return (cards.CARD_CSS + cards.FONTS + lc.TABS_CSS + EL_CSS + '<div class="wrap">'
            + ''.join(card_html(g, data, rm, now) for g in games) + '</div>')


def block_height(games):
    h = 40
    for g in games:
        nv = len(versions_of(g))
        h += 250 + 44 * (nv - 1) + (22 if g.get('played') else 0)
    return min(h, 9000)


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
