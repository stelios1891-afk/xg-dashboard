"""uel_homefav_gamma.py — 9/10/2026 (Στελιος: «ελεγξε το» — UEL φαβορι εντος ΧΩΡΙΣ γ στις 24ω).
Live κανονας UEL φαβ εντος (μηχανη 80% xG, σωστα τεταρτα, 1.70-2.10, FotMob+FotMob, γραμμη ≤ −0.5) με και χωρις το ξεφουσκωμα γ.
Crown & SBOBET (μεσος), 48ω / 24ω / κλεισιμο, κατωφλια 0/4/8%. Περιγραφικο (η συγκριση βρεθηκε απο το προηγουμενο τεστ → post-hoc)."""
import sys, os, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
os.environ['W2_IN'] = 'euro_v6w2_preds_bl0.8.pkl'
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
b = {'__name__': 'ub'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, b)
G2 = b['g']; Dv, LH2, LA2, GAM = (np.asarray(G2[k], float) for k in ('D', 'LH2', 'LA2')) + (G2['GAMMA_LIVE'],) if False else (np.asarray(G2['D'], float), np.asarray(G2['LH2'], float), np.asarray(G2['LA2'], float), G2['GAMMA_LIVE'])
LHN, LAN, MIDS, COMP, SEA, FM, GD = (b[k] for k in ('LH_N', 'LA_N', 'MIDS', 'COMP', 'SEA', 'FM', 'GD'))
UEL = np.asarray(COMP) == 'EuropaLeague'
assert np.allclose(np.maximum(LH2 - GAM * Dv / 2, .05)[UEL], np.asarray(LHN)[UEL]), 'ανακατασκευη'
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
snap, sdist, cover_q, edge, picks = u['snap'], u['sdist'], u['cover_q'], u['edge'], u['picks']
rows = []
for i, mid in enumerate(MIDS):
    if not UEL[i] or not FM[i]: continue
    for lab, lh, la in (('με γ (live)', LHN[i], LAN[i]), ('χωρις γ', LH2[i], LA2[i])):
        dist = sdist(lh, la)
        for bk in ('Crown', 'SBOBET'):
            for h in (48, 24, 0):
                s = snap(mid, bk, h)
                if not s: continue
                L, oh, oa = s
                if L > -0.5 or not (1.70 <= oh <= 2.10): continue
                pw, pp = cover_q(dist, 1, L)
                rows.append(dict(v=lab, i=i, sea=SEA[i], bk=bk, h=h, e=edge(pw, pp, oh), pnl=picks.settle(GD[i], 1, L, oh), D=Dv[i]))
R = pd.DataFrame(rows)
def cell(x):
    if len(x) < 4: return f'n{len(x) / 2:3.0f}'
    ps = x.groupby('sea').pnl.mean(); pb = x.groupby('bk').pnl.mean()
    return f'{len(x) / 2:3.0f} {100 * x.pnl.mean():+6.1f}% ±{100 * x.pnl.std() / np.sqrt(len(x) / 2):4.1f} {int((ps > 0).sum())}/{ps.size} (C {100 * pb.get("Crown", np.nan):+.0f}/S {100 * pb.get("SBOBET", np.nan):+.0f})'
for h in (24, 48, 0):
    print(f'\n=== {"κλεισιμο" if h == 0 else f"{h}ω πριν"} ===')
    for th in (0.0, 0.04, 0.08):
        print(f'   edge ≥{th:.0%}:  ' + '  |  '.join(f'{v}: {cell(R[(R.v == v) & (R.h == h) & (R.e >= th)])}' for v in ('με γ (live)', 'χωρις γ')))
X = R[R.h == 24]
a = X[(X.v == 'με γ (live)') & (X.e >= .04)]; c = X[(X.v == 'χωρις γ') & (X.e >= .04)]
ka = set(zip(a.i, a.bk)); kc = set(zip(c.i, c.bk))
print('\n24ω @4% — ποια picks αλλαζουν:')
print(f'   κοινα     {cell(a[[k in kc for k in zip(a.i, a.bk)]])}')
print(f'   μονο με γ {cell(a[[k not in kc for k in zip(a.i, a.bk)]])}  (μεσο χασμα λιγκας D {a[[k not in kc for k in zip(a.i, a.bk)]].D.mean():+.2f})')
print(f'   μονο χωρις γ {cell(c[[k not in ka for k in zip(c.i, c.bk)]])}')
print('\n24ω @4% ανα χασμα λιγκας (γηπ − φιλ, D>0 = ισχυροτερη λιγκα ο γηπεδουχος):')
for lo, hi, lab in ((-9, 0, 'D ≤ 0'), (0, .3, '0-0.3'), (.3, 9, '> 0.3')):
    print(f'   {lab:7s} ' + '  |  '.join(f'{v}: {cell(X[(X.v == v) & (X.e >= .04) & (X.D > lo) & (X.D <= hi)])}' for v in ('με γ (live)', 'χωρις γ')))
