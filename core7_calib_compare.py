"""
core7_calib_compare.py — 5/10/2026 (Στελιος): ο ΙΔΙΟΣ πινακας βαθμονομησης με το southam_diag (μοντελο / αγορα / εγινε, «ποσοστο καλυψης»)
για τις CORE7 — ποσο διαφερει η αγορα των εγχωριων στα (βαθια) αουτσαιντερ απο Βραζιλια/MLS;
Μηχανη CORE7 live (σωστο SoS, νεες κοκκινες: core7_mech_preds_cur_0.75_6_13~emps.csv), ΧΩΡΙΣ αγκυρα (συγκρισιμο με Βραζ/MLS),
τελικες τιμες Pinnacle / Crown / Bet365 (ιδιο δειγμα με core7_sos15_final), 4 σεζον 2223-2526, αγωνιστικες 7-14 και 15+.
+ τυφλο ROI ανα κατηγορια και τα δικα μας dogs (κανονας: +0.5 και πανω, παλια τεταρτα, edge ≥10%, 1.70-2.10).
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read()
pre = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'c7cal'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, run_L, load, NG, picks = g['D'], g['run_L'], g['load'], g['NG'], g['picks']
xh, xa, _ = load('cur_0.75_6_13~emps'); D['xh'] = xh; D['xa'] = xa
S0 = run_L(0, 0, 6); T = xh + xa
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
rows = []
for i in np.where((D.md >= 6).values)[0]:
    r = D.loc[i]
    per = '15+' if r.md >= 14 else '7-14'
    dist = picks.gd_dist_dom(max((T[i] + S0[i]) / 2, .05), max((T[i] - S0[i]) / 2, .05))
    quotes = [('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None)]
    for bk in ('Crown', 'Bet365'):
        q = NG.get((r.mid, bk)); quotes.append((bk, q[1] if q else None))
    for bk, q in quotes:
        if q is None or q[0] != q[0]: continue
        L, oh, oa = q
        for side, ln, o, oo in ((1, L, oh, oa), (-1, -L, oa, oh)):
            cm = 0.
            for x in parts(ln):
                a, p = picks.p_cover(dist, side, x); cm += (a + 0.5 * p) / len(parts(ln))
            pw, pp = picks.p_cover(dist, side, ln); e = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            rows.append(dict(book=bk, season=r.season, per=per, home=side == 1, line=ln, odds=o, c_mod=cm, c_mkt=(1 / o) / (1 / o + 1 / oo),
                             c_act=(picks.settle(r.gd, side, ln, 2.0) + 1) / 2, pnl=picks.settle(r.gd, side, ln, o),
                             pick=(ln >= 0.5 and 1.70 <= o <= 2.10 and e >= 0.10)))
S = pd.DataFrame(rows)
def calib(d):
    if len(d) < 30: return f'n{len(d):5d}'
    ps = d.groupby('season').pnl.mean()
    return (f'n{len(d):5d} · μοντελο {100*d.c_mod.mean():5.1f}% · αγορα {100*d.c_mkt.mean():5.1f}% · ΕΓΙΝΕ {100*d.c_act.mean():5.1f}% (±{100*d.c_act.std()/np.sqrt(len(d)):.1f})'
            f' → αγορα−πραγμ. {100*(d.c_mkt.mean()-d.c_act.mean()):+5.1f} · τυφλο ROI {100*d.pnl.mean():+5.1f}% ({int((ps > 0).sum())}/{len(ps)})')
BUCK = ((-9, -1.6, '≤−1.75'), (-1.6, -1.1, '−1.25/−1.5'), (-1.1, -0.4, '−0.5/−1'), (-0.4, 0.4, '−0.25..+0.25'), (0.4, 1.1, '+0.5/+1'), (1.1, 1.6, '+1.25/+1.5'), (1.6, 9, '≥+1.75'))
for bk in ('Pinnacle', 'Crown'):
    for per in ('15+', '7-14'):
        x = S[(S.book == bk) & (S.per == per)]
        print(f'\n[CORE7 · {bk} κλεισιμο · αγωνιστικες {per}] — «ποσοστο καλυψης»')
        for home in (True, False):
            for lo, hi, lab in BUCK:
                y = x[(x.home == home) & (x.line > lo) & (x.line <= hi)]
                if len(y) >= 30: print(f'   {"ΓΗΠ" if home else "ΦΙΛ"} {lab:13s} ' + calib(y))
        y = x[x.pick]; print(f'   ΤΑ ΔΙΚΑ ΜΑΣ dogs (≥10%)  ' + calib(y))
        for lo, hi, lab in ((0.4, 0.8, '+0.5/+0.75'), (0.8, 9, '+1 και πανω')):
            z = y[(y.line > lo) & (y.line <= hi)]; print(f'     {lab:22s} ' + calib(z))
