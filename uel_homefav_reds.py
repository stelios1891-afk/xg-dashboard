# -*- coding: utf-8 -*-
"""uel_homefav_reds.py — 4/11/2026 (Στελιος: «δεν καταλαβαινω πως απο 14.9% πεφτουμε στο 9.8%»). ΑΙΤΙΑ του κενου Α→Β του uel_homefav_decomp: το harness euro_inseason_eu_test (26/9)
εχει ακομα την ΠΑΛΙΑ φορμουλα κοκκινων (+0.0083/λεπτο), ενω live και dump 0.8 εχουν την 'emps' (5/10). Εδω το harness με emps (διορθωθηκε στο αρχειο 5/11):
ελεγχος vs dump 0.8 + ο κανονας UEL φαβορι εντος (γηπ ≤−0.5, 1.70-2.10, FotMob+FotMob, σωστα τεταρτα, edge ≥4%, Crown/SBOBET μεσος, 90′) χωρις/με Μ8, 12-36ω και 24ω (προ-δηλωση 9/10).
Οι αριθμοι με τις παλιες κοκκινες: uel_homefav_decomp_out.txt."""
import sys, io, contextlib
import numpy as np, pandas as pd
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
io.StringIO = _Q
src = open('uel_homefav_inseason.py', encoding='utf-8').read()
pre = src[:src.index('rows = []\nfor i, mid in enumerate(MIDS):')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'ur'}
with contextlib.redirect_stdout(_Q()): exec(pre, g)
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8')
import picks
MIDS, SEA, GD, U, D8, INS, BASE, snap, sdist, cover_q, edge = (g[k] for k in ('MIDS', 'SEA', 'GD', 'U', 'D8', 'INS', 'BASE', 'snap', 'sdist', 'cover_q', 'edge'))
Ux = np.asarray(U) & np.asarray(D8['FM'])
ds = (np.asarray(BASE[0]) - np.asarray(BASE[1]))[Ux] - (np.asarray(D8['LH']) - np.asarray(D8['LA']))[Ux]
print(f"Β με emps (σημερινα αρχεια) vs dump 0.8 (9/10), {Ux.sum()} ματς: |Δ υπεροχης γηπ.| μεσο {np.abs(ds).mean():.3f} γκολ · sd {ds.std():.3f} · max {np.abs(ds).max():.3f}")
def rule(LL, hs):
    r = []
    for i, mid in enumerate(MIDS):
        if not Ux[i]: continue
        D = sdist(LL[0][i], LL[1][i])
        for bk in ('Crown', 'SBOBET'):
            for h in hs:
                x = snap(mid, bk, h)
                if not x: continue
                L, oh, oa = x
                if not (1.70 <= oh <= 2.10) or L > -0.5: continue
                pw, pp = cover_q(D, 1, L)
                if edge(pw, pp, oh) >= .04:
                    r.append(dict(i=i, bk=bk, sea=SEA[i], pnl=picks.settle(float(GD[i]), 1, L, oh))); break
    return pd.DataFrame(r)
def line(z, lab):
    print(f"   {lab:22s} picks {len(z) / 2:5.1f} ROI {100 * z.pnl.mean():+6.1f}% {z.pnl.sum() / 2:+6.1f}μ ±{100 * z.groupby('i').pnl.mean().std() / np.sqrt(z.i.nunique()):.1f} │ " + ' '.join(f"{s_[2:]}:{100 * q.pnl.mean():+.0f}" for s_, q in z.groupby('sea')) + f" │ Crown {100 * z[z.bk == 'Crown'].pnl.mean():+.1f} SBOBET {100 * z[z.bk == 'SBOBET'].pnl.mean():+.1f}")
for lab, hs in (('ΚΑΝΟΝΑΣ 36/24/18/12ω', (36, 24, 18, 12)), ('ΠΡΟ-ΔΗΛΩΣΗ 24ω @4%', (24,))):
    print(lab)
    line(rule((D8['LH'], D8['LA']), hs), 'dump 0.8 (9/10)'); line(rule(BASE, hs), 'emps χωρις Μ8'); line(rule(INS, hs), 'emps με Μ8')
