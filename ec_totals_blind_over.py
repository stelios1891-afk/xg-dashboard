# -*- coding: utf-8 -*-
"""ec_totals_blind_over.py — ΠΑΡΑΤΗΡΗΣΗ (οχι προ-δηλωμενο τεστ) απο το ec_totals_test (1/10/2026): η αγορα συνολων EuroCup
βγαινει ΧΑΜΗΛΑ στην αρχη της σεζον (πραγματικο − κλεισιμο Crown: αγων 1-6 +1.9, 7-10 +1.1, 11+ +0.4). Τυφλο OVER ανα φαση, ανοιγμα/κλεισιμο,
ανα σεζον. Εξοδος: ec_totals_blind_over_out.txt"""
import sys, json, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
exec(open('ec_totals_test.py', encoding='utf-8').read().split('EFF = {w: luck_eff')[0])
tot = (D.hs + D.as_).values.astype(float); seasn = D.season.values
mk_src = open('ec_totals_test.py', encoding='utf-8').read()
mk_src = mk_src[mk_src.index('N = NormalDist(); Phi = N.cdf'):mk_src.index("P(''); P(f'=== ΑΓΟΡΑ")]
exec(mk_src)
out = []
def P2(s=''): print(s); out.append(s)
P2('=== ΤΥΦΛΟ OVER EuroCup (Crown) ανα φαση · U2020-25 ===')
for lab, m in (('αγων 1-3', GN <= 3), ('αγων 1-6', GN <= 6), ('7-10', (GN >= 7) & (GN <= 10)), ('11+', GN >= 11), ('ολα', GN >= 0)):
    for w in ('o', 'c'):
        R = []
        for i in MK:
            if not m[i]: continue
            T, oo, ou, mu = MK[i][w]; v = tot[i] - T
            R.append(((oo - 1) if v > 0 else (0 if v == 0 else -1), seasn[i], tot[i] - T))
        a = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R))
        per = {Y: np.mean([q[0] for q in R if q[1] == Y]) for Y in ys}
        P2(f'  {lab:8s} {"ανοιγμα " if w == "o" else "κλεισιμο"} n {len(a):4d} · over {a.mean()*100:+5.1f}% ({a.sum():+6.1f}u) · πραγματικο − γραμμη {np.mean([q[2] for q in R]):+.2f} · θετικες {sum(v > 0 for v in per.values())}/{len(per)} ['
           + ' '.join(f'{Y[-2:]}:{v*100:+.0f}' for Y, v in per.items()) + ']')
open('ec_totals_blind_over_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
