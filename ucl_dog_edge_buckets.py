"""ucl_dog_edge_buckets.py — 10/10/2026 (Στελιος: Roma–Real / City–PSG «πολυ μεγαλες διαφορες με την αγορα»).
Ιστορικα (2223-2526, σημερινη αλυσιδα, κλεισιμο, μεσος Crown/Pinnacle): πως πανε τα UCL picks ανα μεγεθος edge (μηπως τα τεραστια edge = λαθος μοντελου),
και ειδικα οταν το κ μπαινει σε σχεδον ισοπαλο ματς (υπεροχη πριν το κ < 0.4)."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'ue'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']; MIDS, COMP, SEA, GD, FMm = G['MIDS'], G['COMP'], g['SEA'], G['GD'], G['FMm']
LH, LA = g['BASE']; picks = g['picks']; eu_dist, cover_q = g['eu_dist'], g['cover_q']
C = G['C_ARR']; KS = G['KSCOPE']; RAW = G['predict_arm'](G['rate_base'])
pre_h = np.maximum(RAW[0] - C / 2, .05); pre_a = np.maximum(RAW[1] + C / 2, .05); PRE = np.abs(pre_h - pre_a)
rows = []
for bk, OD in (('Crown', g['CROWN']), ('Pin', g['PIN'])):
    for i, mid in enumerate(MIDS):
        if COMP[i] != 'ChampionsLeague' or not FMm[i] or mid not in OD: continue
        lf, oh, oa = OD[mid]; dist = eu_dist(LH[i], LA[i])
        for side, ln, o in ((1, lf, oh), (-1, -lf, oa)):
            if not (1.70 <= o <= 2.10): continue
            role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
            if role is None: continue
            pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
            e = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            if (role == 'fav' and e >= .10) or (role == 'dog' and e >= .04):
                rows.append(dict(bk=bk, sea=SEA[i], role=role, e=e, pnl=picks.settle(GD[i], side, ln, o), kapflip=bool(KS[i] and PRE[i] < 0.4),
                                 kdir=('κ στον αντιπαλο' if KS[i] and ((LH[i] / max(pre_h[i], 1e-9) > 1.01) == (side == -1)) else 'κ στην ομαδα του pick' if KS[i] else '—')))
R = pd.DataFrame(rows)
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():4.0f} picks {100 * m["mean"].mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size} σεζ)'
for role in ('dog', 'fav'):
    x = R[R.role == role]; print(f'\nUCL {"ΑΟΥΤΣΑΙΝΤΕΡ (@4)" if role == "dog" else "ΦΑΒΟΡΙ (@10)"}: ολα {c(x)}')
    for lo, hi in ((.04, .10), (.10, .20), (.20, .30), (.30, 9)):
        print(f'   edge {lo:.0%}-{(hi if hi < 9 else 9):.0%}: {c(x[(x.e >= lo) & (x.e < hi)])}'.replace('900%', '+'))
    print(f'   σχεδον ισοπαλο πριν το κ (<0.4): {c(x[x.kapflip])} · αλλα: {c(x[~x.kapflip])}')
    if role == 'dog':
        y = x[x.kapflip]; print(f'      ισοπαλα, κ στον αντιπαλο του pick: {c(y[y.kdir == "κ στον αντιπαλο"])} · κ στην ομαδα του pick: {c(y[y.kdir == "κ στην ομαδα του pick"])}')
