"""euro_homefav24_split.py — 9/10: «φαβορι εντος UEL −24ω» — γιατι +11% στον πινακα (FotMob 2223-2526) αλλα +2-3% στο ολικο τεστ;
Σπασιμο: FotMob+FotMob vs υπολοιπα, ανα σεζον, ανα βιβλιο (τυφλα, αποδοση 1.70-2.10, γραμμη ≤ −0.5)."""
import sys, io, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_home24_test.py', encoding='utf-8').read(); src = src[:src.index("def cell(d)")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'hs'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
D = g['D']
V = pickle.load(open('euro_v6_preds.pkl', 'rb')); FM = {m: (h == 'shots' and a == 'shots') for m, h, a in zip(V['mids'], V['src_h'], V['src_a'])}
x = D[(D.comp == 'EuropaLeague') & (D.h == 24) & D.ok & (D.role == 'φαβορι')].copy()
x['grp'] = np.where(x.sea == '2122', '2122 (αθικτη)', np.where(x.mid.map(FM) == True, 'FotMob 2223-2526', 'οχι FotMob 2223-2526'))
def c(d):
    ps = d.groupby('sea').pnl.mean()
    return f'n{len(d) / d.book.nunique():4.0f} {100 * d.pnl.mean():+6.1f}% σεζ {int((ps > 0).sum())}/{ps.size} (Crown {100 * d[d.book == "Crown"].pnl.mean():+.1f} / SBOBET {100 * d[d.book == "SBOBET"].pnl.mean():+.1f})'
print('UEL ΦΑΒΟΡΙ ΕΝΤΟΣ, τυφλα, 24 ωρες πριν (1.70-2.10):')
print('   ΟΛΑ                    ', c(x))
for k, v in x.groupby('grp'): print(f'   {k:24s}', c(v))
print('   ανα σεζον (ολα):        ' + ' · '.join(f'{s}: {100 * v.pnl.mean():+.0f}% (n{len(v) // 2})' for s, v in x.groupby('sea')))
y = x[x.grp == 'FotMob 2223-2526']; print('   ανα σεζον (FotMob):     ' + ' · '.join(f'{s}: {100 * v.pnl.mean():+.0f}% (n{len(v) // 2})' for s, v in y.groupby('sea')))
