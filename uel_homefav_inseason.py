"""uel_homefav_inseason.py — 9/10/2026 (Στελιος: «δοκιμασε το 1»): ο κανονας UEL φαβορι εντος ΜΕ φετινα ευρωπαικα (Μ8, βαρος 0.5).
Μηχανη 80% xG (picks.BLEND=0.8 στο harness του euro_inseason_eu_test), γ+κ, Μ8 με LOSO συντελεστες ΠΑΝΩ στον στοχο 80%.
Κανονας: γηπεδουχος ≤ −0.5, 1.70-2.10, FotMob+FotMob, σωστα τεταρτα, edge ≥4%, εισοδος 24ω (και 48ω/κλεισιμο για εικονα), Crown/SBOBET.
ΠΡΟ-ΔΗΛΩΣΗ: τα φετινα μπαινουν και στον κανονα ΜΟΝΟ αν στις 24ω @4%: ROI ≥ χωρις, θετικο σε ≥3/4 σεζον, θετικο και στα 2 βιβλια.
Ελεγχος αναπαραγωγης: η βαση του harness vs euro_blend_dump_0.8 (λ UEL)."""
import sys, io, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
picks.BLEND = 0.8; picks._BLEND_D = (picks.BLEND_EARLY - 0.8) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
g = {'__name__': 'ui'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_adj_methods.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
assert abs(g['b_bl'] - 0.8) < 1e-9, f"blend {g['b_bl']}"
MIDS, SEA, COMP, GD = g['g']['MIDS'], g['SEA'], g['g']['COMP'], g['g']['GD']
FMm = g['g']['FMm']
BASE = g['BASE']; INS = g['RES']['M8'][0][0.5][0]
D8 = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb'))
assert list(D8['MIDS']) == list(MIDS)
U = np.asarray(COMP) == 'EuropaLeague'
print(f'αναπαραγωγη: |λ βαση harness − dump 0.8| UEL μεσο {np.abs(BASE[0][U] - D8["LH"][U]).mean():.4f} / max {np.abs(BASE[0][U] - D8["LH"][U]).max():.3f}')
print('M8 συντελεστες (στοχος 80%): ' + ' | '.join(f'{f}: ' + ' '.join(f'{x:+.2f}' for x in c) for f, c in g['COEF8'].items()))
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
snap, sdist, cover_q, edge = u['snap'], u['sdist'], u['cover_q'], u['edge']
rows = []
for i, mid in enumerate(MIDS):
    if not U[i] or not D8['FM'][i]: continue
    for lab, L in (('dump 0.8 (backtest)', (D8['LH'], D8['LA'])), ('χωρις φετινα', BASE), ('ΜΕ φετινα (Μ8 .5)', INS)):
        dist = sdist(L[0][i], L[1][i])
        for bk in ('Crown', 'SBOBET'):
            for h in (48, 24, 0):
                s = snap(mid, bk, h)
                if not s: continue
                Ln, oh, oa = s
                if Ln > -0.5 or not (1.70 <= oh <= 2.10): continue
                pw, pp = cover_q(dist, 1, Ln)
                rows.append(dict(v=lab, i=i, sea=SEA[i], bk=bk, h=h, e=edge(pw, pp, oh), pnl=picks.settle(GD[i], 1, Ln, oh)))
R = pd.DataFrame(rows)
def cell(x):
    if len(x) < 4: return f'n{len(x) / 2:3.0f}'
    ps = x.groupby('sea').pnl.mean(); pb = x.groupby('bk').pnl.mean()
    return f'{len(x) / 2:3.0f} {100 * x.pnl.mean():+6.1f}% ±{100 * x.pnl.std() / np.sqrt(len(x) / 2):4.1f} {int((ps > 0).sum())}/{ps.size} (C {100 * pb.get("Crown", np.nan):+.0f}/S {100 * pb.get("SBOBET", np.nan):+.0f})'
V = ('dump 0.8 (backtest)', 'χωρις φετινα', 'ΜΕ φετινα (Μ8 .5)')
for h in (24, 48, 0):
    print(f'\n=== {"κλεισιμο" if h == 0 else f"{h}ω πριν"} ===')
    for th in (0.0, 0.04, 0.08):
        print(f'   edge ≥{th:.0%}: ' + '  |  '.join(f'{v}: {cell(R[(R.v == v) & (R.h == h) & (R.e >= th)])}' for v in V))
X = R[(R.h == 24) & (R.e >= .04)]
a = X[X.v == 'χωρις φετινα']; b = X[X.v == 'ΜΕ φετινα (Μ8 .5)']
ka = set(zip(a.i, a.bk)); kb = set(zip(b.i, b.bk))
print('\n24ω @4% — αλλαγες picks (χωρις → με):')
print(f'   κοινα       {cell(b[[k in ka for k in zip(b.i, b.bk)]])}')
print(f'   φευγουν     {cell(a[[k not in kb for k in zip(a.i, a.bk)]])}')
print(f'   μπαινουν    {cell(b[[k not in ka for k in zip(b.i, b.bk)]])}')
ps = b.groupby('sea').pnl.mean(); pb = b.groupby('bk').pnl.mean()
ok = b.pnl.mean() >= a.pnl.mean() and int((ps > 0).sum()) >= 3 and (pb > 0).all()
print(f'\nΚΡΙΣΗ (προ-δηλωμενη): {"ΜΠΑΙΝΟΥΝ και στον κανονα" if ok else "ΔΕΝ μπαινουν — ο κανονας μενει χωρις φετινα"} '
      f'(ROI {100 * b.pnl.mean():+.1f} vs {100 * a.pnl.mean():+.1f}, σεζον {int((ps > 0).sum())}/4, βιβλια {"✓" if (pb > 0).all() else "✗"})')
