"""uel_league_phase_newfmt.py — 11/10/2026 (Στελιος: «ας επικεντρωθουμε στις 2 τελευταιες σεζον με το νεο φορματ και στη φαση ομιλων»).
Europa League 2425-2526, ΜΟΝΟ φαση λιγκας, FotMob+FotMob. 1) picks με τους σημερινους κανονες UEL ανα top-5/εντος-εκτος/ρολο ·
2) εδρα πραγματικη vs μοντελο · 3) ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ (μια παραμετρος h: γηπ ×h, φιλοξ ÷h), 2-fold (μια σεζον → αλλη).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: περνα αν Poisson log-lik καλυτερη ΚΑΙ στις 2 σεζον-κρισης, picks (μοναδες) καλυτερα ΚΑΙ στις 2, και συνολικες μοναδες ↑.
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
from math import lgamma
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
IDX = []
for i in range(len(MIDS)):
    j = VI.get(str(MIDS[i]))
    if j is None or COMP[i] != 'EuropaLeague' or SEA[i] not in NEW or V6['phase'][j] != 'league' or SRCC[i] != 'FF': continue
    IDX.append((i, int(V6['lg_h'][j] in TOP5) + int(V6['lg_a'][j] in TOP5)))
I = np.array([i for i, _ in IDX]); N5 = {i: n for i, n in IDX}
print(f'Europa League, νεα μορφη (2425-2526), ΦΑΣΗ ΛΙΓΚΑΣ, FotMob+FotMob: {len(I)} ματς · ανα σεζον ' + ' '.join(f'{s}:{int((SEA[I] == s).sum())}' for s in NEW))
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
SN = {}
for i in I:
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if s: SN[(i, bk, h)] = s
def picks_for(hf):
    rows = []
    for (i, bk, h), (L, oh, oa) in SN.items():
        D = sdist(max(LH_N[i] * hf, .05), max(LA_N[i] / hf, .05))
        for side, ln, o in ((1, L, oh), (-1, -L, oa)):
            if not (1.70 <= o <= 2.10): continue
            if ln <= -0.5: kind, thr = 'φαβορι', .04
            elif ln >= 0.5: kind, thr = 'αουτσαιντερ', .10
            else: continue
            pw, pp = cover_q(D, side, ln) if kind == 'φαβορι' else picks.p_cover(D, side, ln)
            e = edge(pw, pp, o)
            if e >= thr:
                rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], kind=kind, home=side == 1, n5=N5[i], pnl=picks.settle(GD[i], side, ln, o)))
    if not rows: return pd.DataFrame(columns=['i', 'bk', 'h', 'side', 'sea', 'kind', 'home', 'n5', 'pnl'])
    return pd.DataFrame(rows).sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
P0 = picks_for(1.0)
print(NL + '1. PICKS ΣΗΜΕΡΑ (κανονες UEL: φαβ ≥4% σωστα τεταρτα · dog ≥10% p_cover · πρωτη εμφανιση ≤72ω)')
print(f'   ΟΛΑ: {cc(P0)}')
for lab, m in (('χωρις top-5', P0.n5 == 0), ('με top-5', P0.n5 >= 1)):
    x = P0[m]; print(f'   {lab:12s} {cc(x)}')
    for k in ('φαβορι', 'αουτσαιντερ'):
        for hv, hl in ((True, 'εντος'), (False, 'εκτος')):
            y = x[(x.kind == k) & (x.home == hv)]
            if len(y): print(f'      {k} {hl}: {cc(y)}')
# ---- 2. εδρα ----
gd = GD[I]; mg = LH_N[I] - LA_N[I]
print(NL + f'2. ΕΔΡΑ: πραγματικη {gd.mean():+.2f} · μοντελο {mg.mean():+.2f} · γκολ γηπεδουχου πραγμ {GH[I].mean():.2f} vs μοντ {LH_N[I].mean():.2f} · φιλοξ πραγμ {GA[I].mean():.2f} vs μοντ {LA_N[I].mean():.2f}')
for lab, m in (('χωρις top-5', np.array([N5[i] == 0 for i in I])), ('με top-5', np.array([N5[i] >= 1 for i in I]))):
    print(f'   {lab:12s} n{m.sum():3d} · πραγμ {gd[m].mean():+.2f} · μοντελο {mg[m].mean():+.2f}')
# ---- 3. διορθωση εδρας, 2-fold ----
LGF = {i: lgamma(GH[i] + 1) + lgamma(GA[i] + 1) for i in I}
def ll(hf, idx):
    a = np.maximum(LH_N[idx] * hf, .05); b = np.maximum(LA_N[idx] / hf, .05)
    return (GH[idx] * np.log(a) - a + GA[idx] * np.log(b) - b - np.array([LGF[i] for i in idx])).sum()
GRID = np.round(np.arange(0.90, 1.36, 0.01), 2)
print(NL + '3. ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ: γηπεδουχος ×h, φιλοξενουμενος ÷h (επιπλεον του σημερινου ~1.14) — h απο τη μια σεζον, κριση στην αλλη')
oks = []; Pf = []
for tr, te in (('2425', '2526'), ('2526', '2425')):
    itr = I[SEA[I] == tr]; ite = I[SEA[I] == te]
    hf = GRID[np.argmax([ll(g, itr) for g in GRID])]
    dll = ll(hf, ite) - ll(1.0, ite)
    p1 = picks_for(hf); p1 = p1[p1.sea == te]; p0 = P0[P0.sea == te]
    u0 = p0.groupby('bk').pnl.sum().mean() if len(p0) else 0; u1 = p1.groupby('bk').pnl.sum().mean() if len(p1) else 0
    oks.append((dll > 0, u1 > u0)); Pf.append(p1)
    print(f'   εκπαιδευση {tr} → h = {hf:.2f} · στη {te}: Δlog-lik {dll:+.2f} · picks {cc(p0)}  →  {cc(p1)}')
P1 = pd.concat(Pf)
uu0 = P0.groupby('bk').pnl.sum().mean(); uu1 = P1.groupby('bk').pnl.sum().mean()
full = GRID[np.argmax([ll(g, I) for g in GRID])]
print(f'   h με τις 2 σεζον μαζι: {full:.2f} · ΣΥΝΟΛΟ εκτος δειγματος: picks {cc(P0)} → {cc(P1)}')
ok = all(a for a, _ in oks) and all(b for _, b in oks) and uu1 > uu0
print(f'   ΚΡΙΤΗΡΙΑ: προβλεψη καλυτερη 2/2 {"✓" if all(a for a, _ in oks) else "✗"} · picks καλυτερα 2/2 {"✓" if all(b for _, b in oks) else "✗"} · μοναδες {uu0:+.1f} → {uu1:+.1f} {"✓" if uu1 > uu0 else "✗"} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
print('   picks με τη διορθωση, ανα ομαδα:')
for lab, m in (('χωρις top-5', P1.n5 == 0), ('με top-5', P1.n5 >= 1)):
    x = P1[m]; print(f'   {lab:12s} {cc(x)}')
    for k in ('φαβορι', 'αουτσαιντερ'):
        for hv, hl in ((True, 'εντος'), (False, 'εκτος')):
            y = x[(x.kind == k) & (x.home == hv)]
            if len(y): print(f'      {k} {hl}: {cc(y)}')
