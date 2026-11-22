"""ucl_under_drawfix_detail.py — 10/10/2026 (Στελιος: «αν η αξια ειναι στα over, πως τα under βγαινουν θετικα με τη διορθωση ισοπαλιων; και μονο FotMob;»).
UCL νεα μορφη, κλεισιμο, 1.70-2.10, μεσος Crown/SBOBET. (1) ΤΥΦΛΑ over/under (ολα, χωρις μοντελο). (2) ποια under φευγουν/μενουν με ×0.85.
(3) ιδια αναλυση και με ΟΛΕΣ τις πηγες (οχι μονο FotMob+FotMob)."""
import sys, io, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import euro_shadow_scan as ES, picks
src = open('ucl_under_engine.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src[:src.index("print('\n4. ΕΝΙΣΧΥΣΗ")] if "print('\n4. ΕΝΙΣΧΥΣΗ" in src else src
g = {'__name__': 'ud'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
R, OH, OA, tot_dist_b, c = g['R'], g['OH'], g['OA'], g.get('tot_dist_b'), g['c']
if tot_dist_b is None:
    exec(open('ucl_under_engine.py', encoding='utf-8').read().split("def tot_dist_b")[1].split("B0 = R[")[0].join(['def tot_dist_b', '']), g); tot_dist_b = g['tot_dist_b']
B = R[(R.h == 0) & R.inz & R.new]
print('1. ΤΥΦΛΑ (ολα τα ματς νεας μορφης, χωρις μοντελο):', ' · '.join(f'{s.upper()} {c(B[B.side == s])}' for s in ('over', 'under')))
def sel(boost):
    out = {}
    for r in B.itertuples():
        po, pu = ES.p_over(tot_dist_b(OH[r.i], OA[r.i], boost), r.L)
        pw, pl_ = (po, pu) if r.side == 'over' else (pu, po)
        if pw * (r.od - 1) * (1 - picks.MARGIN) - pl_ >= .04: out[(r.i, r.bk, r.side)] = r
    return out
A, Z = sel(1.13), sel(0.85)
for side in ('under', 'over'):
    gone = [r for k, r in A.items() if k not in Z and k[2] == side]; new = [r for k, r in Z.items() if k not in A and k[2] == side]
    stay = [r for k, r in A.items() if k in Z and k[2] == side]
    f = lambda L: f'{len(L) / 2:.0f} picks {100 * np.mean([x.pnl for x in L]):+.1f}%' if L else '—'
    print(f'2. {side.upper()} ×1.13 → ×0.85: φευγουν {f(gone)} · μπαινουν {f(new)} · μενουν {f(stay)}')
    if side == 'under' and gone:
        G = pd.DataFrame([dict(L=x.L, model=x.model, mt=x.mt, sup=x.sup) for x in gone])
        print(f'   τα under που φευγουν: μεση γραμμη {G.L.mean():.2f} · μοντελο {G.model.mean():.2f} vs αγορα {G.mt.mean():.2f} · υπεροχη φαβορι {G.sup.mean():.2f} (ισορροπημενα <0.5: {100 * (G.sup < .5).mean():.0f}%)')
