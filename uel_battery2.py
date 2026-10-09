"""uel_battery2.py — 9/10: αναλυση των UEL picks της σημερινης αλυσιδας (περιγραφικο, συμπληρωμα uel_battery):
ρολος × εδρα, top-5, μορφη, edge, και συνδυασμος εδρα h=1.04 + κ_UEL 0.95 (μονο ενδεικτικα — οχι προ-δηλωμενο)."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('# ---- Γ διορθωσεις')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'u2'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
P0, fm, make_picks, LH_N, LA_N, COMP, NEW, FAVH, T5H, T5A, SEA = (g[k] for k in ('P0', 'fm', 'make_picks', 'LH_N', 'LA_N', 'COMP', 'NEW', 'FAVH', 'T5H', 'T5A', 'SEA'))
x = P0[P0.comp == 'EuropaLeague'].copy()
x['new'] = NEW[x.i.values]; x['t5team'] = np.where(x.home, T5H[x.i.values], T5A[x.i.values]); x['t5opp'] = np.where(x.home, T5A[x.i.values], T5H[x.i.values])
print('UEL picks σημερα (κλεισιμο, μεσος Crown/SBOBET):', fm(x))
for role in ('fav', 'dog'):
    y = x[x.role == role]; print(f' [{role}] εντος {fm(y[y.home])} · εκτος {fm(y[~y.home])}')
    print(f'        ομαδα μας top-5 {fm(y[y.t5team])} · οχι {fm(y[~y.t5team])}')
    print(f'        παλια μορφη {fm(y[~y.new])} · νεα {fm(y[y.new])}')
UEL = COMP == 'EuropaLeague'
for h, k in ((1.04, 1.0), (1.0, 0.95), (1.04, 0.95), (1.08, 0.92)):
    LH = np.where(UEL, LH_N * h, LH_N); LA = np.where(UEL, LA_N / h, LA_N)
    LH = np.where(UEL & NEW & FAVH, LH * k, LH); LA = np.where(UEL & NEW & ~FAVH, LA * k, LA)
    P = make_picks(LH, LA, mask=UEL); y = P[P.comp == 'EuropaLeague']
    print(f' ενδεικτικα εδρα ×{h} & φαβ νεας ×{k}: {fm(y)} · φαβ {fm(y[y.role == "fav"])[:24]} · dogs {fm(y[y.role == "dog"])[:24]}')
