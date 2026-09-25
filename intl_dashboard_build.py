"""intl_dashboard_build.py — 🌐 INTERNATIONAL tab (25/9/2026, εντολη Στελιου): μαζευει σε ΕΝΑ json τις προβολες εθνικων
(NL A-D 2026-27 + προκριματικα AFCON 2027) με τις ΤΡΕΙΣ εκδοχες μοντελου ΞΕΧΩΡΙΣΤΑ και διπλα την αγορα.
  H  = rating H3 + στρωμα αξιας ροστερ (intl_project.py στηλες χωρις καταληξη)
  A  = αγκυρα αγορας λ=0.3 ΧΩΡΙΣ αξια (_A)          AV = αγκυρα + αξια (_AV, ιδιος logit/T με την A)
25/9 (εντολη Στελιου): η ΑΓΟΡΑ = TOA (Pinnacle, αλλιως Matchbook) απο intl_odds_latest.json (intl_odds_scan.py, GitHub Actions) οταν
υπαρχει για το ματς· fair/edges/picks ανα εκδοχη υπολογιζονται ΣΤΗ ΓΡΑΜΜΗ ΤΟΥ TOA με τους ιδιους κανονες (intl_nl_shadow / intl_nl_overs).
Αλλιως fallback Nowgoal (Crown/SBOBET, intl_ng_now.json) ΟΠΩΣ ΠΡΙΝ (picks απο τα CSV της σκιας). market.source / market.ts λενε την πηγη.
Οταν υπαρχουν και τα δυο, η Nowgoal μενει ως δευτερευουσα στηλη (συγκριση).
ΤΡΕΧΕΙ ΣΤΟ ACTIONS (scanner_tick.sh): χρειαζεται ΜΟΝΟ intl_projections.csv (+ picks.py). Προαιρετικα (ανεχεται απουσια):
intl_nl_shadow_2627.csv, intl_nl_overs_2627.csv (picks/κλησεις/αρχικες γραμμες Nowgoal), intl_ng_now.json + nowgoal_intl_team_names.json
(fallback Nowgoal NL), intl_afconq_shadow_2627.csv + intl_afconq_overs_2627.csv + intl_ng_now_afconq.json (+ intl_matches.csv για ids) (AFCONQ).
ΔΕΝ κανει fetch. Εξοδος: intl_projections_dashboard.json (σκια, χαρτινο — ΟΧΙ live)."""
import sys, os, json, re, math, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import picks
import intl_pricing   # 25/9 (Στελιος): σωστο edge over (push/μισα)

OUT = 'intl_projections_dashboard.json'
TOA_F = 'intl_odds_latest.json'
VERS = ('H', 'A', 'AV')
BOOKS = (('3', 'crown'), ('31', 'sbobet'))              # Nowgoal
TOA_BOOKS = ('pinnacle', 'matchbook', 'bovada', 'betfair_ex_eu')   # TOA, σειρα προτεραιοτητας (25/9: Bovada με γκανιοτα «Pinnacle», Betfair μονο 1Χ2)
SRC_BOOKS = ('pinnacle', 'matchbook', 'bovada')                    # TOA βιβλια με AH/OU = «κυρια πηγη» γραμμων
LAB = {'crown': 'Crown', 'sbobet': 'SBOBET', 'pinnacle': 'Pinnacle', 'matchbook': 'Matchbook', 'betfair_ex_eu': 'Betfair', 'bovada': 'Bovada'}
RULES = {'ah': 'AH: dog/φαβορι ≥0.5, τιμη 1.70-2.10, edge ≥10% (Pinnacle πρωτα, μετα Matchbook· χωρις TOA: Crown, μετα SBOBET)',
         'x12': '1Χ2: φαβορι με P ≥75% (και 1/τιμη <0.95)', 'dead': 'νεκρη ομαδα (αδιαφορη για 1η/υποβιβασμο) = κανενα pick',
         'over': 'OVER: edge ≥8% ΚΑΙ (νοκ-αουτ ή |ΔElo| <150 = «κοντινο»)· αλλιως «εκτος κανονα»',
         'hfa': {'NL': 60, 'AFCONQ': 80}, 'T': 'T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[κοντινο] + 0.10·(R_h+R_a)/2/100 − 0.05·[NL]',
         'A_note': 'Η εκδοχη Α (αγκυρα χωρις αξια) δινει ΜΟΝΟ AH picks (οπως τρεχει απο 21/9)· H και AV δινουν AH + 1Χ2 φαβορι.',
         'afconq_note': 'AFCONQ: αγκυρα μη διαθεσιμη για CAF (δεν εχει τρεξει intl_mkt_anchor) — μονο εκδοχη H, HFA 80. Χωρις TOA key → Nowgoal.',
         'market': 'Αγορα = TOA Pinnacle (αλλιως Matchbook) απο τον scanner· χωρις TOA → Nowgoal Crown/SBOBET (snapshot laptop).'}


def _load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return default


def _load_csv(path, **kw):
    try:
        return pd.read_csv(path, **kw)
    except Exception:
        return None


NAMES = _load_json('nowgoal_intl_team_names.json', {})
N2ID = {}
_M = _load_csv('intl_matches.csv', dtype={'mid': str})
if _M is not None:
    for r in _M.itertuples(): N2ID[str(r.hn)] = int(r.hid); N2ID[str(r.an)] = int(r.aid)


def jf(x, nd=2):
    """float για json (NaN -> None)."""
    try:
        return None if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x) else round(float(x), nd)
    except Exception:
        return None


def pct(s):
    """'+12%' -> 12.0, '' -> None."""
    try:
        return float(str(s).replace('%', '').replace('+', '')) if s not in (None, '') and str(s) != 'nan' else None
    except Exception:
        return None


def line_of(s):
    if s in (None, ''): return np.nan
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)


def hk(x):
    v = float(x); return v + 1 if v < 1.5 else v


def ng_ts(o):
    """τελευταιο unix ts στις γραμμες Nowgoal της εγγραφης -> 'YYYY-MM-DD HH:MM' UTC (ή None)."""
    ts = 0
    for b in (o.get('books') or {}).values():
        for k in ('ah', 'ou', 'op'):
            for row in (b or {}).get(k) or []:
                try: ts = max(ts, int(row[0]))
                except Exception: pass
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime('%Y-%m-%d %H:%M') if ts else None


def market_of(o, flipped=False, conv=None):
    """γραμμες ανα book απο εγγραφη Nowgoal (τελευταια σειρα ah/ou/op)· conv = μετατροπη HK -> δεκαδικη."""
    conv = conv or (lambda v: float(v) + 1)
    out = {}
    for cid, lab in BOOKS:
        b = (o.get('books') or {}).get(cid) or {}; rec = {}
        ah = b.get('ah') or []
        if ah:
            try:
                _, g, u, d, _ = ah[-1]; line = -line_of(g); oh = conv(u); oa = conv(d)
                if flipped: line, oh, oa = -line, oa, oh
                rec.update(ah_line=round(line, 2), oh=round(oh, 2), oa=round(oa, 2))
            except Exception: pass
        ou = b.get('ou') or []
        if ou:
            try:
                _, g, u, d, _ = ou[-1]; rec.update(ou_line=round(line_of(g), 2), over=round(conv(u), 2), under=round(conv(d), 2))
            except Exception: pass
        op = b.get('op') or []
        if op:
            try:
                _, gx, g1, g2, _ = op[-1]; o1, ox, o2 = float(g1), float(gx), float(g2)      # op: g=ισοπαλια, u=γηπ, d=εκτος
                if flipped: o1, o2 = o2, o1
                rec.update(o1=round(o1, 2), ox=round(ox, 2), o2=round(o2, 2))
            except Exception: pass
        out[lab] = rec or None
    return out


def toa_market(rec):
    """εγγραφη intl_odds_latest.json -> {pinnacle: {...}|None, matchbook: {...}|None} στο ιδιο σχημα με market_of."""
    out = {}
    for bk in TOA_BOOKS:
        b = (rec.get('books') or {}).get(bk) or {}; r = {}
        if b.get('line') is not None and b.get('oh') and b.get('oa'):
            r.update(ah_line=round(float(b['line']), 2), oh=round(float(b['oh']), 2), oa=round(float(b['oa']), 2))
        if b.get('ou_line') is not None and b.get('over') and b.get('under'):
            r.update(ou_line=round(float(b['ou_line']), 2), over=round(float(b['over']), 2), under=round(float(b['under']), 2))
        if b.get('h') and b.get('d') and b.get('a'):
            r.update(o1=round(float(b['h']), 2), ox=round(float(b['d']), 2), o2=round(float(b['a']), 2))
        for f, val in b.items():      # Betfair/Bovada: ωμες τιμες + γκανιοτες (για hover)
            if (f.startswith('raw_') or f.startswith('gap_') or f.startswith('over_') or f == 'pin_margin') and val is not None:
                r[f] = val
        out[bk] = r or None
    return out


def pick_source(mk):
    """πηγη αγορας: Pinnacle/Matchbook, αλλιως Crown, αλλιως SBOBET, αλλιως Betfair (μονο 1Χ2), αλλιως None."""
    for lab in SRC_BOOKS + tuple(l for _, l in BOOKS) + ('betfair_ex_eu',):
        b = mk.get(lab)
        if b and (b.get('ah_line') is not None or b.get('ou_line') is not None or b.get('o1')):
            return lab
    return None


def ah_edges(xg_h, xg_a, mk):
    """fair/edge στη γραμμη καθε book για γηπεδουχο (H) και φιλοξενουμενο (A) — ιδιος τυπος με intl_nl_shadow.py."""
    if xg_h is None or xg_a is None: return {}
    dist = picks.gd_dist(max(xg_h, .05), max(xg_a, .05)); out = {}
    for lab in mk:
        b = mk.get(lab) or {}
        if b.get('ah_line') is None: out[lab] = None; continue
        line, oh, oa = b['ah_line'], b['oh'], b['oa']; rec = {}
        for side, ud, odds, tag in ((1, line, oh, 'home'), (-1, -line, oa, 'away')):
            pw, pp = picks.p_cover(dist, side, ud); e = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            rec[f'ah_{tag}'] = round(e * 100, 1); rec[f'fair_{tag[0]}'] = round((1 - pp) / pw, 2) if pw > 0 else None
        out[lab] = rec
    return out


def p_over(T, line):
    """ιδιο με intl_nl_overs.p_over."""
    kmax = int(math.floor(line)); p = 1 - sum(math.exp(-T) * T ** k / math.factorial(k) for k in range(kmax + 1))
    if float(line).is_integer(): return p, math.exp(-T) * T ** int(line) / math.factorial(int(line))
    return p, 0.0


def T_of(diff, Rh, Ra, ko=False, nl=True):
    """T με κατασταση (intl_xg_totals 22/9) -> (T, κοντινο)· ιδιο με intl_nl_overs.py."""
    if diff is None or Rh is None or Ra is None or pd.isna(diff) or pd.isna(Rh) or pd.isna(Ra): return None, None
    close = abs(Rh - Ra) < 150
    return 0.29 + 0.33 * abs(diff) / 100 + 0.26 * ko + 0.49 * close + 0.10 * (Rh + Ra) / 2 / 100 - 0.05 * nl, close


def pick_ah(xg_h, xg_a, mk, order, p1=None, p2=None, allow_x12=True):
    """ΧΑΡΤΙΝΟ pick AH (+1Χ2 φαβ) με τους κανονες του intl_nl_shadow.py, στα books του `order` (πρωτο που περναει).
    Οπως στη σκια: ο ελεγχος 1Χ2 γινεται στο ΠΡΩΤΟ book (και «κλειδωνει» το pick πριν το δευτερο)."""
    if xg_h is None or xg_a is None: return ''
    dist = picks.gd_dist(max(xg_h, .05), max(xg_a, .05)); pick = ''
    for i, lab in enumerate(order):
        b = mk.get(lab) or {}
        if b.get('ah_line') is not None:
            line, oh, oa = b['ah_line'], b['oh'], b['oa']
            for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
                pw, pp = picks.p_cover(dist, side, ud); e = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                if not pick and 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= 0.5:
                    pick = f"{'DOG' if ud >= 0.5 else 'FAV'} {'1' if side == 1 else '2'} {ud:+.2f} @{odds:.2f} ({LAB[lab]}, {e*100:+.0f}%)"
        if i == 0 and allow_x12 and b.get('o1'):
            o1, o2 = b['o1'], b['o2']
            if p1 is not None and p1 >= 75 and 1 / o1 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ γηπ ≥75% @{o1:.2f}'
            if p2 is not None and p2 >= 75 and 1 / o2 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ εκτος ≥75% @{o2:.2f}'
    return pick


def pick_over(T, close, mk, order):
    """OVER pick με τους κανονες του intl_nl_overs.py: edge ≥8% ΚΑΙ κοντινο· αλλιως «εκτος κανονα»."""
    if T is None: return ''
    for lab in order:
        b = mk.get(lab) or {}
        if b.get('ou_line') is None: continue
        e = intl_pricing.over_ev(T, b['ou_line'], b['over'])      # 25/9: σωστο (ηταν P(>floor)·τιμη−1)
        if e >= .08:
            return (f'OVER {b["ou_line"]:g} @{b["over"]:.2f} ({LAB[lab]}, {e*100:+.0f}%)' if close
                    else f'(εκτος κανονα: αναντιστοιχια, edge {e*100:+.0f}% {LAB[lab]})')
    return ''


def x12_reprice(pick, bf):
    """pick κειμενο σκιας (Crown) -> το κομματι «1Χ2 φαβ …» με τιμη Betfair (+γκανιοτα Pinnacle)· ιδιος κανονας 1/τιμη < .95."""
    out = []
    for part in [p.strip() for p in str(pick or '').split(' · ') if p.strip()]:
        if part.startswith('1Χ2 φαβ'):
            o = bf.get('o1') if 'γηπ' in part else bf.get('o2')
            if not o or 1 / o >= .95:
                continue
            part = re.sub(r'@\d+(\.\d+)?', f'@{o:.2f} (Betfair)', part)
        out.append(part)
    return ' · '.join(out)


def over_edges(T, mk, labs):
    """{lab: (edge%, p_over%)} για τα TOA books."""
    out = {}
    for lab in labs:
        b = mk.get(lab) or {}
        if T is None or b.get('ou_line') is None: continue
        e = intl_pricing.over_ev(T, b['ou_line'], b['over']); po = intl_pricing.over_p_equiv(T, b['ou_line'], b['over'])
        out[lab] = (round(e * 100, 1), round(po * 100, 1))
    return out


def version(Rh, Ra, vadj, diff, xg_h, xg_a, p1, px, p2, T=None):
    if diff is None or pd.isna(diff): return None
    p1, px, p2 = float(p1), float(px), float(p2)
    return dict(R_h=jf(Rh, 0), R_a=jf(Ra, 0), vadj=jf(vadj, 0), diff=jf(diff, 0), xg_h=jf(xg_h), xg_a=jf(xg_a), T=jf(T),
                p1=round(p1), px=round(px), p2=round(p2),
                fair_1=(round(100 / p1, 2) if p1 > 0 else None), fair_x=(round(100 / px, 2) if px > 0 else None), fair_2=(round(100 / p2, 2) if p2 > 0 else None))


def sget(row, col, default=''):
    if row is None or col not in row.index: return default
    v = row[col]; return default if (v is None or (isinstance(v, float) and np.isnan(v))) else v


def rget(r, col, default=np.nan):
    return getattr(r, col, default)


# ============================ NATIONS LEAGUE ============================
P = _load_csv('intl_projections.csv')
if P is None:
    print('ΣΦΑΛΜΑ: λειπει intl_projections.csv — δεν χτιζεται τιποτα (το υπαρχον json μενει)'); sys.exit(0)
NG = _load_json('intl_ng_now.json', {})
TOA = _load_json(TOA_F, {}); TOA_ODDS = TOA.get('odds') or {}
SH = _load_csv('intl_nl_shadow_2627.csv'); OV = _load_csv('intl_nl_overs_2627.csv')
SHD = {k: SH.iloc[i] for i, k in enumerate(zip(SH.comp, SH.utc.str[:16], SH['ματς']))} if SH is not None else {}
OVD = {k: OV.iloc[i] for i, k in enumerate(zip(OV.comp, OV.utc.str[:16], OV['ματς']))} if OV is not None else {}
print(f"πηγες: TOA {len(TOA_ODDS)} ματς (scanned {TOA.get('scanned_at')}) · Nowgoal {len(NG)} · shadow csv {'ναι' if SH is not None else 'ΟΧΙ'} · overs csv {'ναι' if OV is not None else 'ΟΧΙ'}")


def toks(s):
    s = re.sub(r'[^a-z ]', ' ', str(s).lower().replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')); return set(w for w in s.split() if len(w) > 2)


ALIAS = {'Turkiye': 'Turkey', 'Czechia': 'Czech Republic', 'Bosnia and Herzegovina': 'Bosnia', 'Ireland': 'Republic of Ireland', 'North Macedonia': 'Macedonia', 'Faroe Islands': 'Faroe'}
ng_by_key = {}
for ng, o in NG.items(): ng_by_key[(NAMES.get(str(o['hid']), ''), NAMES.get(str(o['aid']), ''))] = o


def resolve(fm):
    t = toks(ALIAS.get(fm, fm)) | toks(fm); best = None; bs = 0
    for k in ng_by_key:
        for nm in k:
            ov = len(t & toks(nm))
            if ov > bs: bs = ov; best = nm
    return best


comps = {c: [] for c in ('NL A', 'NL B', 'NL C', 'NL D', 'AFCONQ')}
n_chk = 0; chk_bad = []; n_toa = 0; n_ng = 0; t_bad = []
for r in P.itertuples():
    if pd.isna(r.diff): continue
    key = (r.comp, r.utc[:16], f'{r.home} - {r.away}'); sh = SHD.get(key); ov = OVD.get(key)
    # --- Nowgoal (fallback / δευτερευουσα) ---
    o = None; flipped = False
    if ng_by_key:
        h, a = resolve(r.home), resolve(r.away); o = ng_by_key.get((h, a))
        if o is None and ng_by_key.get((a, h)) is not None: o = ng_by_key[(a, h)]; flipped = True
    mk = market_of(o, flipped) if o else {'crown': None, 'sbobet': None}
    ng_when = ng_ts(o) if o else None
    # --- TOA (κυρια) ---
    tkey = f'{int(r.hid)}_{int(r.aid)}_{r.utc[:16]}'; trec = TOA_ODDS.get(tkey)
    if trec: mk.update(toa_market(trec))
    else: mk.update({bk: None for bk in TOA_BOOKS})
    source = pick_source(mk); is_toa = source in TOA_BOOKS
    n_toa += is_toa; n_ng += (source in ('crown', 'sbobet'))
    mk['source'] = source
    mk['ts'] = (str(trec.get('when', '')).replace('T', ' ') if is_toa else ng_when) if source else None
    mk['ng_ts'] = ng_when
    # --- 1Χ2 (25/9): οταν η πηγη δεν ειναι Pinnacle/Matchbook, το 1Χ2 ερχεται απο Betfair (+ γκανιοτα Pinnacle) αν υπαρχει ---
    bf = mk.get('betfair_ex_eu') or {}
    mk['x12_source'] = 'betfair_ex_eu' if (source not in SRC_BOOKS and bf.get('o1')) else source
    if trec: mk['pin_margin'] = trec.get('pin_margin')
    mk['x12_ts'] = str(trec.get('when', '')).replace('T', ' ') if (trec and mk['x12_source'] == 'betfair_ex_eu') else mk['ts']
    # --- T ανα εκδοχη (ιδιος τυπος με intl_nl_overs) ---
    T_H, close_H = T_of(r.diff, r.R_home, r.R_away)
    T_A, close_A = T_of(rget(r, 'diff_A'), rget(r, 'R_home_A'), rget(r, 'R_away_A'))
    T_AV, _ = T_of(rget(r, 'diff_AV'), rget(r, 'R_home_A'), rget(r, 'R_away_A'))
    TT = {'H': (T_H, close_H), 'A': (T_A, close_A), 'AV': (T_AV, close_A)}
    if ov is not None and T_H is not None and sget(ov, 'T_μοντ', None) is not None and abs(float(ov['T_μοντ']) - T_H) > 0.011:
        t_bad.append((key[2], float(ov['T_μοντ']), round(T_H, 2)))
    vers = {'H': version(r.R_home, r.R_away, r.val_adj, r.diff, r.xg_h, r.xg_a, r.P1, r.PX, r.P2, T_H),
            'A': version(rget(r, 'R_home_A'), rget(r, 'R_away_A'), 0, r.diff_A, r.xg_h_A, r.xg_a_A, r.P1_A, r.PX_A, r.P2_A, T_A) if pd.notna(rget(r, 'diff_A')) else None,
            'AV': version(rget(r, 'R_home_A'), rget(r, 'R_away_A'), r.val_adj, r.diff_AV, r.xg_h_AV, r.xg_a_AV, r.P1_AV, r.PX_AV, r.P2_AV, T_AV) if pd.notna(rget(r, 'diff_AV')) else None}
    # --- edges ανα εκδοχη, ανα book (Nowgoal over-edges απο CSV = ιδια με σημερα· TOA over-edges υπολογιζονται εδω) ---
    edges = {}
    for v, suf in (('H', ''), ('A', '_A'), ('AV', '_AV')):
        V = vers[v]
        if V is None: edges[v] = None; continue
        books_here = {lab: mk[lab] for lab in TOA_BOOKS + ('crown', 'sbobet')}
        e = ah_edges(V['xg_h'], V['xg_a'], books_here)
        for _, lab in BOOKS:
            L = LAB[lab]
            if e.get(lab) is not None:
                e[lab]['over'] = pct(sget(ov, f'{L}_edge{suf}')); e[lab]['p_over'] = pct(sget(ov, f'{L}_p_over')) if v == 'H' else None
            elif (mk.get(lab) or {}).get('ou_line') is not None:
                e[lab] = {'over': pct(sget(ov, f'{L}_edge{suf}'))}
        oe = over_edges(TT[v][0], mk, TOA_BOOKS)
        for lab, (ed, po) in oe.items():
            if e.get(lab) is None: e[lab] = {}
            e[lab]['over'] = ed; e[lab]['p_over'] = po
        edges[v] = e
        # ελεγχος συνεπειας με το CSV της σκιας (εκδοχη H: fair/edge Crown)
        if v == 'H' and e.get('crown') and sh is not None and sget(sh, 'Crown_fair_H', None) is not None:
            n_chk += 1
            if abs(float(sh['Crown_fair_H']) - (e['crown']['fair_h'] or 0)) > 0.011 or abs(pct(sh['Crown_edge_H']) - e['crown']['ah_home']) > 0.6:
                chk_bad.append((key[2], sh['Crown_fair_H'], e['crown']['fair_h'], sh['Crown_edge_H'], e['crown']['ah_home']))
    dead = str(getattr(r, 'νεκρη', '') or ''); dead = '' if dead == 'nan' else dead
    # --- picks: στη γραμμη TOA (ιδιοι κανονες) οταν υπαρχει TOA· αλλιως τα CSV της σκιας (Nowgoal) οπως πριν ---
    if is_toa:
        order = tuple(bk for bk in TOA_BOOKS if mk.get(bk))
        pk = {}
        for v, allow in (('H', True), ('A', False), ('AV', True)):
            V = vers[v]
            if V is None: pk[v] = ''; continue
            pk[v] = pick_ah(V['xg_h'], V['xg_a'], mk, order, V['p1'], V['p2'], allow_x12=allow)
            if dead: pk[v] = 'ΟΧΙ (νεκρη ' + dead + ')' if v == 'H' else 'ΟΧΙ (νεκρη)'
        pk_over = {v: (pick_over(TT[v][0], TT[v][1], mk, order) if vers[v] is not None else '') for v in VERS}
        pk_d = dict(H=pk['H'], A=pk['A'], AV=pk['AV'], over=pk_over['H'], over_A=pk_over['A'], over_AV=pk_over['AV'])
    else:
        pk_d = dict(H=str(sget(sh, 'PICK_χαρτι', '')), A=str(sget(sh, 'PICK_αγκυρα', '')), AV=str(sget(sh, 'PICK_αγκυρα_αξια', '')),
                    over=str(sget(ov, 'PICK_over', '')), over_A=str(sget(ov, 'PICK_over_A', '')), over_AV=str(sget(ov, 'PICK_over_AV', '')))
        if mk['x12_source'] == 'betfair_ex_eu':
            for v in ('H', 'A', 'AV'):
                pk_d[v] = x12_reprice(pk_d[v], bf)
    comps[r.comp].append(dict(utc=r.utc[:16].replace('T', ' '), home=r.home, away=r.away, hid=int(r.hid), aid=int(r.aid), dead=dead,
                              callups=str(sget(sh, 'απουσιες_κλησης', '')), init_ah=str(sget(sh, 'αρχικη_AH', '')), init_ou=str(sget(ov, 'αρχικη_OU', '')),
                              versions=vers, market=mk, edges=edges, picks=pk_d))
print(f'NL: αγορα TOA {n_toa} · Nowgoal {n_ng} · χωρις {sum(len(v) for k, v in comps.items() if k != "AFCONQ") - n_toa - n_ng}')
print(f'NL: ελεγχος fair/edge H vs intl_nl_shadow: {n_chk} ματς, αποκλισεις {len(chk_bad)}' + (f' -> {chk_bad[:3]}' if chk_bad else ''))
if t_bad: print(f'NL: T_μοντ CSV vs υπολογισμος: {len(t_bad)} αποκλισεις -> {t_bad[:3]}')

# ============================ AFCONQ (μονο H, μονο Nowgoal — χωρις TOA key) ============================
AQ = _load_csv('intl_afconq_shadow_2627.csv', dtype={'ng': str}); AQO = _load_csv('intl_afconq_overs_2627.csv'); NGQ = _load_json('intl_ng_now_afconq.json', {})
if AQ is None:
    print('AFCONQ: παραλειπεται (λειπει intl_afconq_shadow_2627.csv)')
else:
    AQOD = {}
    if AQO is not None:
        for i, k in enumerate(AQO['ματς']): AQOD.setdefault(k, AQO.iloc[i])
    ALIAS_Q = {'Democratic Rep Congo': 'DR Congo', 'Republic of the Congo': 'Congo', 'Guinea Bissau': 'Guinea-Bissau', "Cote d'Ivoire": 'Ivory Coast', 'Cabo Verde': 'Cape Verde', 'Swaziland': 'Eswatini', 'Sao Tome': 'Sao Tome and Principe'}
    n_q = 0
    for r in AQ.itertuples():
        if pd.isna(r.diff): continue
        o = NGQ.get(str(r.ng)) or {}; hn_, an_ = str(r.ματς).split(' - ', 1)
        hid = N2ID.get(ALIAS_Q.get(NAMES.get(str(o.get('hid')), ''), NAMES.get(str(o.get('hid')), '')) or hn_) or N2ID.get(hn_)
        aid = N2ID.get(ALIAS_Q.get(NAMES.get(str(o.get('aid')), ''), NAMES.get(str(o.get('aid')), '')) or an_) or N2ID.get(an_)
        lh, la = [float(x) for x in str(r.λ).split('-')]; p1, px, p2 = [float(x) for x in str(r.p1X2).split('/')]
        ov = AQOD.get(r.ματς); srow = AQ.iloc[r.Index]
        mk = market_of(o, False, hk) if o else {'crown': None, 'sbobet': None}
        mk.update({bk: None for bk in TOA_BOOKS}); source = pick_source(mk)
        mk['source'] = source; mk['ts'] = (ng_ts(o) if o else None) if source else None; mk['ng_ts'] = ng_ts(o) if o else None
        V = version(r.R_h, r.R_a, r.vadj, r.diff, lh, la, p1, px, p2, sget(ov, 'T_μοντ', None))
        e = ah_edges(lh, la, {lab: mk[lab] for _, lab in BOOKS})
        for _, lab in BOOKS:
            L = LAB[lab]
            if e.get(lab) is not None: e[lab]['over'] = pct(sget(ov, f'{L}_edge')); e[lab]['p_over'] = pct(sget(ov, f'{L}_p_over'))
            elif (mk.get(lab) or {}).get('ou_line') is not None: e[lab] = {'over': pct(sget(ov, f'{L}_edge'))}
        comps['AFCONQ'].append(dict(utc=str(r.utc)[:16].replace('T', ' '), home=hn_, away=an_, hid=hid, aid=aid, dead='', callups='',
                                    init_ah=str(sget(srow, 'αρχικη_AH', '')), init_ou=str(sget(ov, 'αρχικη_OU', '')),
                                    versions={'H': V, 'A': None, 'AV': None}, market=mk, edges={'H': e, 'A': None, 'AV': None},
                                    picks=dict(H=str(sget(srow, 'PICK_χαρτι', '')), A='', AV='', over=str(sget(ov, 'PICK_over', '')), over_A='', over_AV='')))
        n_q += 1
    print(f'AFCONQ: {n_q} ματς (μονο H)')

for c in comps: comps[c].sort(key=lambda m: m['utc'])


def _snap(all_ms):
    """τελευταιο Nowgoal ts αναμεσα στα ματς (ανεξαρτητο απο mtime — στο Actions το checkout αλλαζει mtime)."""
    ts = [m['market'].get('ng_ts') for m in all_ms if m['market'].get('ng_ts')]
    return max(ts) if ts else None


nl_ms = [m for c, ms in comps.items() if c != 'AFCONQ' for m in ms]
out = dict(generated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M'),
           toa_scanned=(str(TOA.get('scanned_at', '')).replace('T', ' ') or None) if TOA_ODDS else None, toa_matches=n_toa,
           ng_snapshot=_snap(nl_ms) or (dt.datetime.fromtimestamp(os.path.getmtime('intl_ng_now.json'), dt.timezone.utc).strftime('%Y-%m-%d %H:%M') if os.path.exists('intl_ng_now.json') else None),
           ng_snapshot_afconq=_snap(comps['AFCONQ']),
           comps=[dict(comp=c, matches=ms) for c, ms in comps.items()], rules=RULES, versions={'H': 'Rating H3 + αξια ροστερ', 'A': 'Αγκυρα αγορας (λ=0.3) χωρις αξια', 'AV': 'Αγκυρα + αξια ροστερ'})
# γραψε ΜΟΝΟ αν αλλαξε κατι πέρα απο το 'generated' (στο Actions τρεχει καθε τικ — αλλιως commit καθε 5')
_prev = _load_json(OUT, None)
_same = isinstance(_prev, dict) and {k: v for k, v in _prev.items() if k != 'generated'} == json.loads(json.dumps({k: v for k, v in out.items() if k != 'generated'}))
if _same:
    print(f'{OUT}: αμεταβλητο (ιδιο περιεχομενο, generated {_prev.get("generated")}) — δεν ξαναγραφεται')
    out = _prev
else:
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _real(p):
    return bool(p) and not p.startswith('ΟΧΙ') and not p.startswith('(')


for c, ms in comps.items():
    n_pick = {v: sum(_real(m['picks'][v]) for m in ms) for v in VERS}
    n_over = {v: sum(_real(m['picks'][k]) for m in ms) for v, k in (('H', 'over'), ('A', 'over_A'), ('AV', 'over_AV'))}
    src = {}
    for m in ms: src[m['market'].get('source')] = src.get(m['market'].get('source'), 0) + 1
    print(f"{c}: {len(ms)} ματς · πηγη {src} · με AH γραμμη {sum(1 for m in ms if m['market'].get('source') and (m['market'].get(m['market']['source']) or {}).get('ah_line') is not None)} · "
          f"picks AH/1Χ2 H {n_pick['H']} A {n_pick['A']} AV {n_pick['AV']} · over H {n_over['H']} A {n_over['A']} AV {n_over['AV']}")
print(f'-> {OUT} · generated {out["generated"]} UTC · TOA scanned {out["toa_scanned"]} · Nowgoal snapshot {out["ng_snapshot"]} UTC')
