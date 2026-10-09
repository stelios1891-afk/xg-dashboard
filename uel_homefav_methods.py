"""
uel_homefav_methods.py — 9/10/2026 (Στελιος: «η καλυτερη μεθοδος για να κρατησουμε τουλαχιστον τα φαβορι εντος στο Europa;»).
UEL, FotMob+FotMob, 2223-2526, ΦΑΒΟΡΙ ΕΝΤΟΣ (γραμμη ≤ −0.5, 1.70-2.10, σωστα τεταρτα), Crown & SBOBET.
Συνδυασμοι: μιξη xG {60 σημερα, 80, 100} × εδρα UEL {×1.00, ×1.04, ×1.08} × κατωφλι edge {0, 4, 8, 12%} × ωρα εισοδου {48ω, 24ω, κλεισιμο}
+ ΤΥΦΛΑ (χωρις μοντελο) ανα ωρα.
ΠΡΟ-ΔΗΛΩΣΗ: επιλογη με LOSO (μεγιστες μοναδες στις 3 σεζον, ≥15 picks) → κριση στην 4η. Η μεθοδος «κραταμε» αν το LOSO συνολο ειναι
θετικο ΚΑΙ στα 2 βιβλια ΧΩΡΙΣΤΑ ΚΑΙ σε ≥3/4 σεζον. Επισης: ποιος ΣΤΑΘΕΡΟΣ συνδυασμος ειναι πιο «ανθεκτικος» (θετικος στις περισσοτερες σεζον).
"""
import sys, io, pickle, itertools, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_timing.py', encoding='utf-8').read(); src = src[:src.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')      # δεν χρειαζονται τα picks του
g = {'__name__': 'hm'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
snap, sdist, cover_q, edge, picks = g['snap'], g['sdist'], g['cover_q'], g['edge'], g['picks']
BASES = {60: 'euro_blend_dump_0.6.pkl', 80: 'euro_blend_dump_0.8.pkl', 100: 'euro_blend_dump_1.0.pkl'}
DD = {k: pickle.load(open(v, 'rb')) for k, v in BASES.items()}
D0 = DD[60]; MIDS, SEA, COMP, FM, GD = D0['MIDS'], D0['SEA'], D0['COMP'], D0['FM'], D0['GD']
IDX = [i for i, m in enumerate(MIDS) if COMP[i] == 'EuropaLeague' and FM[i]]
HOURS = (48, 24, 0); HS = (1.00, 1.04, 1.08); THR = (0.0, 0.04, 0.08, 0.12)
SN = {(i, bk, h): snap(MIDS[i], bk, h) for i in IDX for bk in ('Crown', 'SBOBET') for h in HOURS}
rows = []
for bl, D in DD.items():
    for hc in HS:
        for i in IDX:
            dist = sdist(D['LH'][i] * hc, D['LA'][i] / hc)
            for bk in ('Crown', 'SBOBET'):
                for h in HOURS:
                    s = SN[(i, bk, h)]
                    if not s: continue
                    L, oh, oa = s
                    if L > -0.5 or not (1.70 <= oh <= 2.10): continue
                    pw, pp = cover_q(dist, 1, L); e = edge(pw, pp, oh)
                    rows.append(dict(bl=bl, hc=hc, h=h, i=i, sea=SEA[i], book=bk, e=e, pnl=picks.settle(GD[i], 1, L, oh)))
R = pd.DataFrame(rows)
BL = R[(R.bl == 60) & (R.hc == 1.0)].drop_duplicates(['i', 'book', 'h'])          # τυφλα = ολα τα φαβορι εντος της ζωνης
CONF = list(itertools.product(DD, HS, THR, HOURS))
def sel(c, d=R):
    bl, hc, th, h = c; return d[(d.bl == bl) & (d.hc == hc) & (d.h == h) & (d.e >= th)]
def cell(x):
    if len(x) < 6: return f'n{len(x) / 2:3.0f}' + ' ' * 26
    ps = x.groupby('sea').pnl.mean(); pb = x.groupby('book').pnl.mean()
    return f'n{len(x) / 2:3.0f} {100 * x.pnl.mean():+6.1f}% σεζ {int((ps > 0).sum())}/{ps.size} (C {100 * pb.get("Crown", np.nan):+.0f} / S {100 * pb.get("SBOBET", np.nan):+.0f})'
print('ΤΥΦΛΑ φαβορι εντος UEL (FotMob):  ' + ' · '.join(f'{("κλεισ" if h == 0 else f"{h}ω")}: {cell(BL[BL.h == h])}' for h in HOURS))
print('\nΠΙΝΑΚΑΣ (κατωφλι 4%) — μιξη × εδρα × ωρα')
for bl in DD:
    for hc in HS:
        print(f'   xG {bl:3d}% · εδρα ×{hc:.2f}: ' + ' · '.join(f'{("κλεισ" if h == 0 else f"{h}ω")} {cell(sel((bl, hc, 0.04, h)))}' for h in HOURS))
SEAS = ('2223', '2324', '2425', '2526'); res = []
print('\nLOSO (συνδυασμος απο τις 3 σεζον → 4η)')
for te in SEAS:
    tr = R[R.sea != te]
    best = max(CONF, key=lambda c: (lambda x: x.pnl.sum() if len(x) >= 30 else -99)(sel(c, tr)))
    x = sel(best, R[R.sea == te]); res.append(x)
    print(f'   εκτος {te}: xG {best[0]}% · εδρα ×{best[1]:.2f} · edge ≥{best[2]:.0%} · {("κλεισιμο" if best[3] == 0 else f"{best[3]}ω πριν")} → {cell(x)}')
X = pd.concat(res); pb = X.groupby('book').pnl.mean(); ps = X.groupby('sea').pnl.mean()
ok = (pb > 0).all() and int((ps > 0).sum()) >= 3
print(f'   LOSO ΣΥΝΟΛΟ {cell(X)} → {"ΚΡΑΤΑΜΕ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
print('\nΑΝΘΕΚΤΙΚΟΤΕΡΟΙ σταθεροι συνδυασμοι (θετικες σεζον, μετα ελαχιστο ROI σεζον, ≥30 picks):')
rob = []
for c in CONF:
    x = sel(c)
    if len(x) / 2 < 30: continue
    ps = x.groupby('sea').pnl.mean(); rob.append((int((ps > 0).sum()), ps.min(), x.pnl.mean(), c, x))
for npos, mn, mean, c, x in sorted(rob, key=lambda z: (-z[0], -z[1]))[:8]:
    print(f'   xG {c[0]}% · εδρα ×{c[1]:.2f} · edge ≥{c[2]:.0%} · {("κλεισ" if c[3] == 0 else f"{c[3]}ω")}: {cell(x)} · χειροτερη σεζον {100 * mn:+.0f}%')
