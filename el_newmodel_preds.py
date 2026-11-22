# -*- coding: utf-8 -*-
"""el_newmodel_preds.py — ΙΣΤΟΡΙΚΕΣ ΠΡΟΒΛΕΨΕΙΣ ΤΟΥ LIVE ΜΟΝΤΕΛΟΥ (1/10/2026) για αναλυσεις timing/alerts, 5 σεζον E2021-E2025.
χαντικαπ: el_preseason_test PRED[κ .5] = Β1 + ειδικοι + προετοιμασια (αγων ≤10) + φετινα εγχωρια (κ .5, απο 11ο) — ιδιο με το live.
συνολο:   el_preseason_totals_test C2 (v2 + Κ2) + .25·(r_T γηπ + r_T φιλ) στις αγων ≤10 — ιδιο με το live.
Εξοδος: el_newmodel_preds.pkl {(season, home, away, t): dict(h_new, h_old, t_new, t_old, gn)}"""
import sys, pickle
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
A = {}
src = open('el_preseason_test.py', encoding='utf-8').read().split('# ---- 3. b, ROI')[0]
src = src.replace("open('el_preseason_test_out.txt', 'w'", "open('_unused_np1.txt', 'w'")
exec(src, A)
D1 = A['D']; HN = A['PRED'][0.5]; HB = A['base']; GN = A['GN']
B = {}
src = open('el_preseason_totals_test.py', encoding='utf-8').read().split('# ---- 1. διαγνωση ----')[0]
src = src.replace("open('el_preseason_totals_test_out.txt', 'w'", "open('_unused_np2.txt', 'w'")
exec(src, B)
D2, IDX2, C2, PRE_T, SE2, RND2 = B['D'], B['IDX'], np.array(B['C2'], float), B['PRE_T'], B['SE'], B['RND']
DH, DA = D2.home.values[IDX2], D2.away.values[IDX2]
TN = C2 + np.where(RND2 <= 10, 0.25 * np.array([PRE_T.get((SE2[j], DH[j]), 0.0) + PRE_T.get((SE2[j], DA[j]), 0.0) for j in range(len(IDX2))]), 0.0)
def k(D, i): return (D.season.values[i], D.home.values[i], D.away.values[i], str(pd.Timestamp(D.t.values[i]))[:16])
OUT = {}
for i in range(len(D1)):
    if np.isfinite(HN[i]): OUT.setdefault(k(D1, i), {}).update(h_new=float(HN[i]), h_old=float(HB[i]), gn=int(GN[i]))
for j, i in enumerate(IDX2):
    OUT.setdefault(k(D2, i), {}).update(t_new=float(TN[j]), t_old=float(C2[j]), rnd=float(RND2[j]))
pickle.dump(OUT, open('el_newmodel_preds.pkl', 'wb'))
print(f"{len(OUT)} ματς · με χαντικαπ {sum('h_new' in v for v in OUT.values())} · με συνολο {sum('t_new' in v for v in OUT.values())} · με ΚΑΙ τα δυο {sum('h_new' in v and 't_new' in v for v in OUT.values())}")
print('διαφορα χαντικαπ νεο−παλιο αγων ≤10: ', np.mean([abs(v['h_new'] - v['h_old']) for v in OUT.values() if 'h_new' in v and v['gn'] <= 10]))
