"""
uel_homefav_depth.py — 9/10/2026 (Στελιος: «το 4% υπολογιστηκε; κοντα vs βαθια φαβορι οπως στα εγχωρια;»).
UEL φαβορι εντος, FotMob+FotMob, 2223-2526, μηχανη 80% xG (live), σωστα τεταρτα, 1.70-2.10, εισοδος 24ω (και κλεισιμο για συγκριση),
μεσος Crown/SBOBET. ΠΕΡΙΓΡΑΦΙΚΟ (καμια επιλογη εδω): (1) ανα κατωφλι edge 0-14% · (2) ανα βαθος γραμμης, με μοντελο @4% και ΤΥΦΛΑ.
"""
import sys, io, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_timing.py', encoding='utf-8').read(); src = src[:src.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
g = {'__name__': 'hd'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
snap, sdist, cover_q, edge, picks = g['snap'], g['sdist'], g['cover_q'], g['edge'], g['picks']
D = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb'))
MIDS, SEA, COMP, FM, GD = D['MIDS'], D['SEA'], D['COMP'], D['FM'], D['GD']
rows = []
for i, mid in enumerate(MIDS):
    if COMP[i] != 'EuropaLeague' or not FM[i]: continue
    dist = sdist(D['LH'][i], D['LA'][i])
    for bk in ('Crown', 'SBOBET'):
        for h in (24, 0):
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            if L > -0.5 or not (1.70 <= oh <= 2.10): continue
            pw, pp = cover_q(dist, 1, L)
            rows.append(dict(i=i, sea=SEA[i], book=bk, h=h, L=L, e=edge(pw, pp, oh), pnl=picks.settle(GD[i], 1, L, oh)))
R = pd.DataFrame(rows)
def cell(x):
    if len(x) < 4: return f'n{len(x) / 2:4.0f}'
    ps = x.groupby('sea').pnl.mean(); pb = x.groupby('book').pnl.mean()
    return (f'n{len(x) / 2:4.0f} {100 * x.pnl.mean():+6.1f}% ±{100 * x.pnl.std() / np.sqrt(len(x) / 2):4.1f} σεζ {int((ps > 0).sum())}/{ps.size}'
            f' (C {100 * pb.get("Crown", np.nan):+.0f} / S {100 * pb.get("SBOBET", np.nan):+.0f})')
for h in (24, 0):
    X = R[R.h == h]; lab = '24ω πριν' if h else 'ΚΛΕΙΣΙΜΟ'
    print(f'\n===== {lab} =====')
    print('1. ΑΝΑ ΚΑΤΩΦΛΙ edge (ολα τα βαθη):')
    print(f'   τυφλα (ολα)      {cell(X)}')
    for th in (0, .02, .04, .06, .08, .10, .12, .14):
        print(f'   edge ≥{th:4.0%}       {cell(X[X.e >= th])}')
    print('   ζωνες:  ' + ' · '.join(f'{a:.0%}-{b:.0%}: {cell(X[(X.e >= a) & (X.e < b)])}' for a, b in ((0, .04), (.04, .08), (.08, .12), (.12, 9))))
    print('2. ΑΝΑ ΒΑΘΟΣ ΓΡΑΜΜΗΣ:')
    for lab2, m in (('−0.5/−0.75 (κοντα)', X.L >= -0.76), ('−1/−1.25', (X.L < -0.76) & (X.L >= -1.26)), ('−1.5 και βαθυτερα', X.L < -1.26)):
        print(f'   {lab2:20s} τυφλα {cell(X[m])}')
        print(f'   {"":20s} edge≥4% {cell(X[m & (X.e >= .04)])}')
