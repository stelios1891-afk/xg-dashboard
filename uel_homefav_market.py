"""uel_homefav_market.py — 9/10 (Στελιος: «στα φαβορι εντος κανει λαθος η αγορα;»). UEL φαβορι εντος (γραμμη ≤ −0.5, 1.70-2.10):
λαθος αγορας = πραγματικη διαφορα γκολ − υπεροχη αγορας (απο γραμμη+αποδοσεις) στις −24ω και στο κλεισιμο · κινηση γραμμης −24ω→κλεισιμο.
Ολα τα ματς 2122-2526 και υποσυνολο FotMob 2223-2526· UCL για συγκριση."""
import sys, io, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_home24_test.py', encoding='utf-8').read(); src = src[:src.index("def cell(d)")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'hm'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
D, FX, home_strength = g['D'], g['FX'], g['home_strength']
V = pickle.load(open('euro_v6_preds.pkl', 'rb')); FM = {m: (h == 'shots' and a == 'shots') for m, h, a in zip(V['mids'], V['src_h'], V['src_a'])}
D = D.copy(); D['gd'] = D.mid.map(lambda m: FX[m]['gd']); D['s_mkt'] = [home_strength(L, oh, 1 / (1 - 1 / oh) if False else oh) for L, oh in zip(D.L, D.oh)]
# υπεροχη αγορας με τις 2 αποδοσεις: ξαναϋπολογισμος απο τις αποθηκευμενες γραμμες
def strength_row(r):
    seq = g['TR'].get((r.mid, r.book)); s = g['snap'](r.mid, r.book, r.h); return home_strength(*s) if s else np.nan
D['s_mkt'] = [strength_row(r) for r in D.itertuples()]
D['err'] = D.gd - D.s_mkt; D['fm'] = D.mid.map(FM).fillna(False)
def row(x, lab):
    if len(x) < 10: return f'   {lab:34s} n{len(x):4d}'
    ps = x.groupby('sea').err.mean()
    return (f'   {lab:34s} n{len(x) / x.book.nunique():4.0f} · λαθος αγορας (πραγμ − αγορα) {x.err.mean():+.3f} ±{x.err.std() / np.sqrt(len(x) / 2):.3f} ({int((ps > 0).sum())}/{ps.size} σεζ >0)'
            f' · κινηση γραμμης ως κλεισιμο {np.nanmean(x.mv):+.3f} · ROI {100 * x.pnl.mean():+.1f}%')
for comp in ('EuropaLeague', 'ChampionsLeague'):
    print(f'\n[{comp}] ΦΑΒΟΡΙ ΕΝΤΟΣ (θετικο λαθος = ο γηπεδουχος πηγε ΚΑΛΥΤΕΡΑ απο οσο ελεγε η αγορα)')
    for h, lab in ((24, '24 ωρες πριν'), (0, 'κλεισιμο')):
        x = D[(D.comp == comp) & (D.h == h) & D.ok & (D.role == 'φαβορι')]
        print(row(x, f'{lab}: ολα 2122-2526'))
        print(row(x[x.fm & (x.sea != '2122')], f'{lab}: FotMob 2223-2526'))
        print(row(x[x.sea == '2122'], f'{lab}: 2122 (αθικτη)'))
