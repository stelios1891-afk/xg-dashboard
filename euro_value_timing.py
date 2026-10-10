"""euro_value_timing.py — 10/10/2026 (Στελιος: «σε ποια ωρα ειναι αυτα τα picks; τρεξτο και σε 24/72ω»).
Στρωμα αξιας (παραλλαγη _D, LOSO) vs σημερα, με τους σημερινους κανονες picks, σε τιμες 72ω / 48ω / 24ω πριν και κλεισιμο,
Crown & SBOBET (ιστορικο Nowgoal) — μεσος ορος των 2 βιβλιων + ανα βιβλιο."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_value_changed_picks.py', encoding='utf-8').read().split('ef = json.load(open(')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'vt'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
BASE, LH, LA, MIDS, COMP, GD, FMm, SEA = (g[k] for k in ('BASE', 'LH', 'LA', 'MIDS', 'COMP', 'GD', 'FMm', 'SEA'))
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
snap, sdist, cover_q, edge, picks = u['snap'], u['sdist'], u['cover_q'], u['edge'], u['picks']
rows = []
for i, mid in enumerate(MIDS):
    if not FMm[i]: continue
    ucl = COMP[i] == 'ChampionsLeague'
    for v, (lh, la) in (('σημερα', (BASE[0][i], BASE[1][i])), ('με αξια', (LH[i], LA[i]))):
        dist = sdist(lh, la)
        for bk in ('Crown', 'SBOBET'):
            for h in (72, 48, 24, 0):
                s = snap(mid, bk, h)
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if not (1.70 <= o <= 2.10): continue
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
                    if role is None: continue
                    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                    e = edge(pw, pp, o)
                    thr = (0.10 if role == 'fav' else 0.04) if ucl else (0.04 if role == 'fav' else 0.10)
                    if e >= thr:
                        rows.append(dict(v=v, i=i, side=side, bk=bk, h=h, comp=COMP[i], sea=SEA[i], pnl=picks.settle(GD[i], side, ln, o)))
R = pd.DataFrame(rows)
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():4.0f} picks {100 * m["mean"].mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size})'
for h in (72, 48, 24, 0):
    X = R[R.h == h]; lab = 'ΚΛΕΙΣΙΜΟ' if h == 0 else f'{h}ω ΠΡΙΝ'
    print(f'\n===== {lab} (μεσος Crown/SBOBET) =====')
    for comp in ('ΟΛΑ', 'ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
        y = X if comp == 'ΟΛΑ' else X[X.comp == comp]
        print(f'   {comp:17s} σημερα {c(y[y.v == "σημερα"])} · με αξια {c(y[y.v == "με αξια"])}')
    for bk in ('Crown', 'SBOBET'):
        a = X[(X.v == 'σημερα') & (X.bk == bk)]; b = X[(X.v == 'με αξια') & (X.bk == bk)]
        ka = set(zip(a.i, a.side)); kb = set(zip(b.i, b.side))
        go = a[[k not in kb for k in zip(a.i, a.side)]]; nw = b[[k not in ka for k in zip(b.i, b.side)]]
        print(f'   {bk:7s}: φευγουν {len(go)} ({100 * go.pnl.mean():+.1f}%, {go.pnl.sum():+.1f}μ) · μπαινουν {len(nw)} ({100 * nw.pnl.mean():+.1f}%, {nw.pnl.sum():+.1f}μ) · καθαρο {nw.pnl.sum() - go.pnl.sum():+.1f}μ')
