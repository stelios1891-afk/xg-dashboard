"""
euro_totals_draw_test.py — 10/10/2026 (Στελιος: «τρεξτο — αλλα το λογικο δεν ειναι να ειναι ιδιο με τα χαντικαπ;»).
ΕΝΙΣΧΥΣΗ ΙΣΟΠΑΛΙΩΝ στη μηχανη ΣΥΝΟΛΩΝ της Ευρωπης. Σημερα: Poisson × 1.13 στα ισοπαλα σκορ (εγχωριο DRAW_BOOST).
Χαντικαπ Ευρωπης: Poisson × 1.13 στα ισοπαλα ΚΑΙ μετα ×0.85 στη συνολικη μαζα ισοπαλιας (καθαρα ≈ ×0.96).
ΕΚΔΟΧΕΣ: Α ×1.13 (σημερα) · Β «ιδιο με χαντικαπ» (×1.13 → ×0.85 στη μαζα ισοπαλιας) · Γ ×1.00 · Δ ×0.85 · Ε LOSO απο πλεγμα 0.70-1.20.
ΔΕΔΟΜΕΝΑ: 2223-2526, FotMob+FotMob, μηχανη γκολ W2 (πεναλτι .76, χωρις γ, κ μονο UCL νεας μορφης). UCL = κυριο· UEL+UECL = επαναληψη.
ΜΕΤΡΗΣΕΙΣ: (0) μηχανισμος: P(0-0/1-1/2-2) και P(συνολο 0/1/2) μοντελο vs πραγματικο · (1) ακριβεια: log-score συνολου γκολ ανα σεζον
(+ Brier P(over) κυριας γραμμης Crown) · (2) picks over/under @4% στο κλεισιμο ΚΑΙ ροη πρωτης εμφανισης ≤72ω, μεσος Crown/SBOBET.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (για την εκδοχη Β, και για την Ε):
 Κ1 ακριβεια UCL καλυτερη απο Α σε ≥3/4 σεζον ΚΑΙ στις 2 της νεας μορφης · Κ2 ιδια κατευθυνση σε UEL+UECL (pooled + ≥3/4 σεζον) ·
 Κ3 over+under μαζι (μοναδες) οχι χειροτερα απο Α και στα 2 βιβλια· over μονα οχι χειροτερα απο Α − 1SE ·
 Κ4 (ξεχωριστα) under θετικα και στα 2 βιβλια, και στις 2 σεζον νεας μορφης, και σε γειτονικα κατωφλια.
"""
import sys, io, os, json, glob, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import euro_shadow_scan as ES, picks
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
KO = u['KO']; MIDS, COMP, FM, SEA = u['MIDS'], np.asarray(u['COMP']), u['FM'], np.asarray(u['SEA'])
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
GH, GA = np.asarray(w['GH']).astype(int), np.asarray(w['GA']).astype(int)
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
FACT = [math.factorial(k) for k in range(13)]
def matrix(lh, la, boost, hcap_like=False):
    ph = np.array([math.exp(-lh) * lh ** k / FACT[k] for k in range(13)]); pa = np.array([math.exp(-la) * la ** k / FACT[k] for k in range(13)])
    M = np.outer(ph, pa); d = np.eye(13, dtype=bool)
    M[d] *= boost; M /= M.sum()
    if hcap_like:                                    # οπως το χαντικαπ: η συνολικη μαζα ισοπαλιας ×0.85, οι υπολοιπες αναλογικα
        D = M[d].sum(); M[d] *= 0.85; M[~d] *= (1 - 0.85 * D) / (1 - D)
    return M
def totals(M):
    t = np.zeros(25)
    for i in range(13):
        for j in range(13): t[i + j] += M[i, j]
    return t
VAR = {'Α ×1.13 (σημερα)': (1.13, False), 'Β ιδιο με χαντικαπ': (1.13, True), 'Γ ×1.00': (1.00, False), 'Δ ×0.85': (0.85, False)}
GRID = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.13, 1.20]
IDX = [i for i in range(len(MIDS)) if FM[i]]
T = {}; MM = {}
for i in IDX:
    for k, (bo, hc) in VAR.items():
        M = matrix(max(OH[i], .05), max(OA[i], .05), bo, hc); T[(i, k)] = totals(M); MM[(i, k)] = M
    for bo in GRID:
        T[(i, ('G', bo))] = totals(matrix(max(OH[i], .05), max(OA[i], .05), bo))
def logs(i, key): return math.log(max(T[(i, key)][GH[i] + GA[i]], 1e-12))
GRP = {'UCL': ucl, 'UEL+UECL': ~ucl}
SEAS = ['2223', '2324', '2425', '2526']
# ---- 0. μηχανισμος ----
print('0. ΜΗΧΑΝΙΣΜΟΣ — συχνοτητα (%) πραγματικη vs μοντελο')
for gl, gm in GRP.items():
    ii = [i for i in IDX if gm[i]]
    act = {'0-0': np.mean([GH[i] == 0 and GA[i] == 0 for i in ii]), '1-1': np.mean([GH[i] == 1 and GA[i] == 1 for i in ii]),
           'ισοπαλια': np.mean([GH[i] == GA[i] for i in ii]), 'συνολο ≤1': np.mean([GH[i] + GA[i] <= 1 for i in ii]), 'συνολο 2': np.mean([GH[i] + GA[i] == 2 for i in ii])}
    print(f'   {gl} (n{len(ii)}): ΠΡΑΓΜΑΤΙΚΟ ' + ' · '.join(f'{k} {100 * v:.1f}' for k, v in act.items()))
    for k in VAR:
        m = {'0-0': np.mean([MM[(i, k)][0, 0] for i in ii]), '1-1': np.mean([MM[(i, k)][1, 1] for i in ii]), 'ισοπαλια': np.mean([np.trace(MM[(i, k)]) for i in ii]),
             'συνολο ≤1': np.mean([T[(i, k)][:2].sum() for i in ii]), 'συνολο 2': np.mean([T[(i, k)][2] for i in ii])}
        print(f'      {k:20s} ' + ' · '.join(f'{kk} {100 * v:.1f}' for kk, v in m.items()))
# ---- 1. ακριβεια ----
print('\n1. ΑΚΡΙΒΕΙΑ — log-score συνολου γκολ (υψηλοτερο = καλυτερο), διαφορα απο Α ×1000, ανα σεζον')
LOSO = {}
for gl, gm in GRP.items():
    ch = {}
    for te in SEAS:
        tr = [i for i in IDX if gm[i] and SEA[i] != te]
        ch[te] = max(GRID, key=lambda bo: sum(logs(i, ('G', bo)) for i in tr))
    LOSO[gl] = ch
    print(f'   {gl}: LOSO ενισχυση ανα σεζον ' + ' '.join(f'{s}:{v}' for s, v in ch.items()))
    for k in list(VAR)[1:] + ['Ε LOSO']:
        cells = []; tot = 0
        for s in SEAS:
            ii = [i for i in IDX if gm[i] and SEA[i] == s]
            key = (lambda i: ('G', ch[s])) if k == 'Ε LOSO' else (lambda i: k)
            dlt = sum(logs(i, key(i)) - logs(i, 'Α ×1.13 (σημερα)') for i in ii); tot += dlt; cells.append(f'{s}:{1000 * dlt / len(ii):+.1f}')
        print(f'      {k:20s} ' + ' '.join(cells) + f' · συνολο {tot:+.2f}')
# ---- 2. picks ----
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
def pov(t, L):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0.0
    for x in parts:
        for k in range(25):
            if k > x + .01: po += t[k] / len(parts)
            elif k < x - .01: pu += t[k] / len(parts)
    return po, pu
def settle(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
KEYS = list(VAR) + ['Ε LOSO']
rows = []
for i in IDX:
    gl = 'UCL' if ucl[i] else 'UEL+UECL'
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(MIDS[i], bk, h)
            if not s: continue
            L, o, un = s
            for k in KEYS:
                t_ = T[(i, ('G', LOSO[gl][SEA[i]]))] if k == 'Ε LOSO' else T[(i, k)]
                po, pu = pov(t_, L)
                for side, od, pw_, pl_ in (('over', o, po, pu), ('under', un, pu, po)):
                    if not (1.70 <= od <= 2.10): continue
                    e = pw_ * (od - 1) * (1 - picks.MARGIN) - pl_
                    if e >= .02:
                        rows.append(dict(k=k, i=i, grp=gl, new=bool(newf[i]), sea=SEA[i], bk=bk, h=h, side=side, e=e, pnl=settle(GH[i] + GA[i], L, od, side == 'over')))
P = pd.DataFrame(rows)
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size', 'sum'])
    return f'{m["size"].mean():4.0f}/{100 * m["mean"].mean():+5.1f}% ({m["sum"].mean():+5.1f}μ)'
print('\n2. PICKS @4% (μεσος Crown/SBOBET: n / ROI / μοναδες)')
for gl in ('UCL', 'UEL+UECL'):
    for scope, sm in (('νεα μορφη', True), ('ολες οι σεζον', None)):
        if gl != 'UCL' and sm: continue
        print(f'   {gl} · {scope}')
        for k in KEYS:
            x = P[(P.k == k) & (P.grp == gl) & (P.e >= .04) & ((P.new == sm) if sm is not None else True)]
            cl = x[x.h == 0]
            fs = x.sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
            print(f'      {k:20s} ΚΛΕΙΣΙΜΟ over {c(cl[cl.side == "over"])} · under {c(cl[cl.side == "under"])} || ΡΟΗ over {c(fs[fs.side == "over"])} · under {c(fs[fs.side == "under"])}')
print('\n   UCL νεα μορφη — UNDER ανα σεζον/βιβλιο/κατωφλι (κλεισιμο):')
for k in KEYS:
    x = P[(P.k == k) & (P.grp == 'UCL') & P.new & (P.h == 0) & (P.side == 'under')]
    print(f'      {k:20s} ' + ' · '.join(f'≥{int(th * 100)}% {c(x[x.e >= th])}' for th in (.02, .04, .06, .08)) +
          ' · @4% ανα σεζον ' + ' '.join(f'{s} {100 * x[(x.e >= .04) & (x.sea == s)].pnl.mean():+.0f}%' for s in ('2425', '2526')) +
          ' · ανα βιβλιο ' + ' '.join(f'{bk} {100 * x[(x.e >= .04) & (x.bk == bk)].pnl.mean():+.0f}%' for bk in ('Crown', 'SBOBET')))
P.to_pickle('euro_totals_draw_picks.pkl')
