"""
fav_lines_compare.py — 5/10/2026 (Στελιος: «πως τιμολογει η αγορα τα φαβορι; πινακα ανα γραμμη»).
ΤΥΦΛΑ ΦΑΒΟΡΙ ανα ΑΚΡΙΒΗ γραμμη (−0.5 … −2+), γηπεδουχο / φιλοξενουμενο φαβορι:
  «ποσοστο καλυψης» (νικη 1 · μισο-νικη .75 · επιστροφη .5 · μισο-ηττα .25 · ηττα 0): ΑΓΟΡΑ (χωρις γκανιοτα) vs ΕΓΙΝΕ, και τυφλο ROI.
Βραζιλια/MLS: Nowgoal Crown+SBOBET (μεσος), κανονικη περιοδος, αγωνιστικες 7-14 και 15+, κλεισιμο ΚΑΙ ανοιγμα.
CORE7: Pinnacle κλεισιμο (ιδιο δειγμα με core7_sos15_final, 2223-2526), αγωνιστικες 7-14 και 15+.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
LINES = [(-0.5, '−0.5'), (-0.75, '−0.75'), (-1.0, '−1'), (-1.25, '−1.25'), (-1.5, '−1.5'), (-1.75, '−1.75'), (-99, '−2 και κατω')]
def bucket(ln):
    for v, lab in LINES[:-1]:
        if abs(ln - v) < 1e-9: return lab
    return '−2 και κατω' if ln <= -2 else None
def fm(d, nse):
    if len(d) < 20: return f'n{len(d):4d}' + ' ' * 52
    ps = d.groupby('season').pnl.mean()
    return (f'n{len(d):4d} · αγορα {100*d.c_mkt.mean():4.1f}% · εγινε {100*d.c_act.mean():4.1f}% (±{100*d.c_act.std()/np.sqrt(len(d)):3.1f}) · '
            f'λαθος αγορας {100*(d.c_mkt.mean()-d.c_act.mean()):+5.1f} · ROI {100*d.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{nse}')
def rows_from(df, book_col):
    out = []
    for r in df.itertuples():
        for side, ln, o, oo in ((1, r.L, r.oh, r.oa), (-1, -r.L, r.oa, r.oh)):
            if ln > -0.5 or not (o > 1 and oo > 1): continue
            b = bucket(ln)
            if b is None: continue
            out.append(dict(season=r.season, per=r.per, win=getattr(r, 'win', 'close'), book=getattr(r, book_col), home=side == 1, lab=b,
                            c_mkt=(1 / o) / (1 / o + 1 / oo), c_act=(picks.settle(r.gd, side, ln, 2.0) + 1) / 2, pnl=picks.settle(r.gd, side, ln, o)))
    return pd.DataFrame(out)
# ---------------- Βραζιλια / MLS ----------------
L = pd.read_csv('southam_lines.csv', dtype={'ng': str, 'season': str})
L = L[L['sub'] == 'League'].copy()
first = L.drop_duplicates('ng').sort_values('ko'); cnt = {}; md = {}
for r in first.itertuples():
    a = cnt.get((r.league, r.season, r.home), 0) + 1; b = cnt.get((r.league, r.season, r.away), 0) + 1
    cnt[(r.league, r.season, r.home)] = a; cnt[(r.league, r.season, r.away)] = b; md[r.ng] = max(a, b)
L['md'] = L.ng.map(md); L = L[L.md >= 7]; L['per'] = np.where(L.md <= 14, '7-14', '15+'); L['gd'] = L.hg - L.ag
L = L[L.win.isin(['close', 'open'])].rename(columns={'ah': 'L'})
SA = {lg: rows_from(L[L.league == lg], 'book') for lg in ('Brazil', 'MLS')}
for lg, X in SA.items():
    nse = X.season.nunique()
    for per in ('15+', '7-14'):
        print(f'\n[{lg} · αγωνιστικες {per}] τυφλα ΦΑΒΟΡΙ — n = στοιχηματα (2 βιβλια μαζι) · ΚΛΕΙΣΙΜΟ | ΑΝΟΙΓΜΑ (μονο ROI)')
        for home in (True, False):
            for _, lab in LINES:
                x = X[(X.per == per) & (X.home == home) & (X.lab == lab)]
                c = x[x.win == 'close']; o = x[x.win == 'open']
                if len(c) < 20: continue
                po = o.groupby('season').pnl.mean()
                print(f'   {"ΓΗΠ" if home else "ΦΙΛ"} φαβ {lab:11s} ' + fm(c, nse) + (f' | ανοιγμα ROI {100*o.pnl.mean():+6.1f}% {int((po > 0).sum())}/{nse}' if len(o) >= 20 else ''))
# ---------------- CORE7 ----------------
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read()
pre = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'favlines'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D = g['D']; NG = g['NG']
D = D[D.md >= 6].copy(); D['per'] = np.where(D.md >= 14, '15+', '7-14')
rows = []
for r in D.itertuples():
    for bk, q in (('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None), ('Crown', (NG.get((r.mid, 'Crown')) or (None, None))[1])):
        if q is None or q[0] != q[0]: continue
        rows.append(dict(season=r.season, per=r.per, book=bk, L=q[0], oh=q[1], oa=q[2], gd=r.gd))
C7 = rows_from(pd.DataFrame(rows), 'book')
for bk in ('Pinnacle', 'Crown'):
    for per in ('15+', '7-14'):
        print(f'\n[CORE7 · {bk} κλεισιμο · αγωνιστικες {per}] τυφλα ΦΑΒΟΡΙ')
        for home in (True, False):
            for _, lab in LINES:
                x = C7[(C7.book == bk) & (C7.per == per) & (C7.home == home) & (C7.lab == lab)]
                if len(x) >= 20: print(f'   {"ΓΗΠ" if home else "ΦΙΛ"} φαβ {lab:11s} ' + fm(x, 4))
