"""uel_homefav_model24.py — 9/10: UEL φαβορι εντος (μοντελο, FotMob+FotMob) κλεισιμο vs −48/−24/−6ω ανα σεζον και βιβλιο."""
import sys, io, contextlib
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_timing.py', encoding='utf-8').read(); src = src[:src.index("HAS = {}")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'hm'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
B = g['B']; x = B[(B.comp == 'EuropaLeague') & (B.role == 'fav') & B.home]
for h in (48, 24, 6, 0):
    y = x[x.h == h]; lab = 'κλεισιμο' if h == 0 else f'−{h}ω'
    print(f'{lab:9s} n{len(y) / 2:4.0f} {100 * y.pnl.mean():+6.1f}% · Crown {100 * y[y.book == "Crown"].pnl.mean():+.1f} / SBOBET {100 * y[y.book == "SBOBET"].pnl.mean():+.1f} · '
          + ' '.join(f'{s}: {100 * v.pnl.mean():+.0f}% (n{len(v) // 2})' for s, v in y.groupby('sea')))
