"""uel_lineup_rule_by_league.py — 11/10/2026 (Στελιος: «πως δεν εξαρταται απο τη λιγκα;» — ο κανονας ενδεκαδων ανα λιγκα του φαβορι). Βαση: uel_lineup_rule_test.py (Στελιος: «ναι» — κανονικο τεστ· «γιατι συμπεριλαμβανουμε και το κονφερενς?» → UEL ΚΥΡΙΟ, UECL μονο επαναληψη).
ΚΑΝΟΝΑΣ: χαντικαπ στο ΦΑΒΟΡΙ ΑΓΟΡΑΣ (γραμμη ≤−0.25, 1.70-2.10) στην τιμη ΜΕΤΑ τις ενδεκαδες (κλεισιμο Nowgoal· + τιμη 1ω πριν για συγκριση),
ΜΟΝΟ οταν η ενδεκαδα του φαβορι αξιζει ≥ τ της συνηθισμενης (αξια βασικων FotMob / διαμεσος 5 τελευταιων εγχωριων ≤45 μερες).
τ απο LOSO στα {0.90, 0.93, 0.95, 0.97, 1.00}. Εκδοχες: A τυφλα · B + μοντελο συμφωνει (edge ≥0, FotMob+FotMob). 2223-2526, Crown & SBOBET.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (UEL): Κ1 LOSO εκτος δειγματος >0 ΚΑΙ θετικο στα 2 βιβλια · Κ2 ≥3/4 σεζον θετικες ΚΑΙ οι 2 σεζον νεας μορφης ·
Κ3 φαβορι με ενδεκαδα <τ χειροτερα απο ≥τ. UECL με το ιδιο τ = μονο αναφορα (δεν μπαινει στην αποφαση).
"""
import sys, io, os, json, glob, contextlib
DRAW_SCALE = 0.85
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
picks, KO = u['picks'], u['KO']
MIDS, COMP, FM, SEA = u['MIDS'], np.asarray(u['COMP']), u['FM'], np.asarray(u['SEA'])
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA = np.asarray(w['GH']), np.asarray(w['GA'])
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
import euro_shadow_scan as ES
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
TOU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        if bk is None: continue
        seq = sorted((int(mt), pl(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or []) if mt and pl(gg) is not None)
        if seq: TOU[(str(r['mid']), bk)] = seq
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
def mtot(L, o, un):
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def _cat(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return '?'
    a, b = sorted((_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')))
    return a + b
SRCC = [_cat(i) for i in range(len(MIDS))]

import datetime as _dt, pickle as _pkl
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
SQ = {}
for fn in ('euro_squads.json', 'core7_squads.json'):
    for mid, v in json.load(open(fn, encoding='utf-8')).items():
        if v: SQ[str(mid)] = v
DATE = {}
for f in glob.glob('data_*.json'):
    if 'Europe' in f: continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for mid, m in d.items():
        try: DATE[str(mid)] = pd.Timestamp(_dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC'))
        except Exception: pass
DOMXI = {}
for mid, v in SQ.items():
    t = DATE.get(mid)
    if t is None: continue
    for k in ('h', 'a'):
        x = v.get(k) or {}
        if x.get('t') and x.get('mv'): DOMXI.setdefault(int(x['t']), []).append((t, float(x['mv'])))
for k in DOMXI: DOMXI[k].sort(key=lambda z: z[0])
def ratio(mid, side, ko):
    x = (SQ.get(str(mid)) or {}).get(side) or {}
    if not x.get('t') or not x.get('mv'): return np.nan
    prev = [z for z in DOMXI.get(int(x['t']), []) if ko - pd.Timedelta(days=45) <= z[0] < ko - pd.Timedelta(hours=12)][-5:]
    if len(prev) < 3: return np.nan
    return float(x['mv']) / np.median([z[1] for z in prev])
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague'): continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j])
    rh, ra = ratio(MIDS[i], 'h', ko), ratio(MIDS[i], 'a', ko)
    D = sdist(LH_N[i], LA_N[i]) if LH_N[i] > 0 else None
    for bk in ('Crown', 'SBOBET'):
        for h in (0, 1):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            if abs(L) < 0.2: continue
            side = 1 if L < 0 else -1; ln = L if side == 1 else -L; o = oh if side == 1 else oa
            if not (1.70 <= o <= 2.10): continue
            r = rh if side == 1 else ra
            if not np.isfinite(r): continue
            e = edge(*cover_q(D, side, ln), o) if (D is not None and SRCC[i] == 'FF') else np.nan
            rows.append(dict(comp=COMP[i], sea=SEA[i], bk=bk, h=h, ratio=r, home=side == 1, e=e, top5=(V6['lg_h'][j] if side == 1 else V6['lg_a'][j]) in {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}, pnl=picks.settle(GD[i], side, ln, o)))
B = pd.DataFrame(rows)
def cc(x):
    if len(x) == 0: return '   —'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'

print(NL + 'ΚΑΝΟΝΑΣ ΕΝΔΕΚΑΔΩΝ ανα λιγκα του ΦΑΒΟΡΙ (τιμη κλεισιματος, φαβορι αγορας ≤−0.25, 1.70-2.10)')
for cm in ('EuropaLeague', 'ConferenceLeague'):
    U = B[(B.comp == cm) & (B.h == 0)]
    for lab, m in (('φαβορι απο TOP-5', U.top5), ('φαβορι απο ΑΛΛΗ λιγκα', ~U.top5)):
        y = U[m]
        print(f'   {cm[:6]} {lab:24s} rotation (<0.90) στο {100 * (y.ratio < 0.90).groupby(y.bk).mean().mean():3.0f}% · πληρης (≥1.00): {cc(y[y.ratio >= 1.0])} · rotation (<0.90): {cc(y[y.ratio < 0.90])}')
