"""euro_no_top5_picks.py — 11/10/2026 (Στελιος: «πως πηγαινουν τα picks μας οταν δεν περιεχουν καποια ομαδα απο μεγαλο πρωταθλημα?»).
Υποθεση: χωρις ομαδες top-5 λιγκων το rotation ειναι μικρο → το μοντελο ισως δουλευει και στο UEL. 1) πληροφορια μοντελου περαν αγορας
(κλιση λαθους αγορας ~ διαφωνια) χωρις / με top-5 ομαδα · 2) picks χαντικαπ με τους σημερινους κανονες ανα αριθμο top-5 ομαδων στο ματς.
UCL/UEL/UECL, FotMob+FotMob, 2223-2526, Crown & SBOBET. ΠΕΡΙΓΡΑΦΙΚΟ.
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

import pickle as _pkl
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
# ---- 1. πληροφορια (απο τη διαγνωση) ----
X = pd.read_pickle('uel_vs_ucl_diag_rows.pkl')
X['n5'] = X.lg_h.isin(TOP5).astype(int) + X.lg_a.isin(TOP5).astype(int)
print('1. ΟΤΑΝ ΔΙΑΦΩΝΟΥΜΕ ΜΕ ΤΗΝ ΑΓΟΡΑ, ποσο πηγαινει η πραγματικοτητα προς εμας (κλιση· >0 = το μοντελο ξερει κατι) — 4 σεζον, FotMob+FotMob')
for cm in CL:
    cells = []
    for lab, m in (('ΧΩΡΙΣ top-5', X.n5 == 0), ('ΜΕ ≥1 top-5', X.n5 >= 1)):
        x = X[(X.comp == cm) & m]
        if len(x) > 20:
            b, s = ols(x.dis.values, x.rk.values); cells.append(f'{lab}: n{len(x):3d} κλιση {b:+.2f} (t {b / s:+.1f})')
    print(f'   {CL[cm]:5s} ' + ' · '.join(cells))
# ---- 2. picks με τους σημερινους κανονες ----
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i in range(len(MIDS)):
    if SRCC[i] != 'FF': continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    n5 = int(V6['lg_h'][j] in TOP5) + int(V6['lg_a'][j] in TOP5)
    c = COMP[i]; ucl_ = c == 'ChampionsLeague'
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10): continue
                if abs(ln) < .01 and ucl_: kind, thr = 'DNB', .04
                elif ln <= -0.5: kind, thr = 'φαβορι', (.10 if ucl_ else .04)
                elif ln >= 0.5: kind, thr = 'αουτσαιντερ', (.04 if ucl_ else .10)
                else: continue
                pw, pp = cover_q(D, side, ln) if kind != 'αουτσαιντερ' else picks.p_cover(D, side, ln)
                e = edge(pw, pp, o)
                if e >= thr:
                    rows.append(dict(i=i, bk=bk, h=h, side=side, comp=c, sea=SEA[i], kind=kind, home=side == 1, n5=n5,
                                     pnl=picks.settle(GD[i], side, ln, o)))
P = pd.DataFrame(rows).sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print(NL + '2. PICKS ΧΑΝΤΙΚΑΠ με τους σημερινους κανονες (UCL φαβ ≥10%/dog ≥4%/DNB · UEL & UECL φαβ ≥4%/dog ≥10%), FotMob+FotMob, πρωτη εμφανιση ≤72ω')
for cm in CL:
    print(f'   {CL[cm]}:')
    for lab, m in (('ΧΩΡΙΣ top-5 ομαδα', P.n5 == 0), ('με 1 top-5', P.n5 == 1), ('με 2 top-5', P.n5 == 2)):
        x = P[(P.comp == cm) & m]
        print(f'      {lab:18s} ολα {cc(x)}')
        if cm == 'EuropaLeague' and len(x):
            for k in ('φαβορι', 'αουτσαιντερ'):
                for hv, hl in ((True, 'εντος'), (False, 'εκτος')):
                    y = x[(x.kind == k) & (x.home == hv)]
                    if len(y): print(f'         {k} {hl}: {cc(y)}')
    x = P[(P.comp == cm) & (P.n5 == 0) & P.sea.isin(NEW)]
    print(f'      ΧΩΡΙΣ top-5, νεα μορφη: {cc(x)}')
