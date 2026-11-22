# -*- coding: utf-8 -*-
"""bcl_live_formula_bt.py — backtest με ΤΗ ΣΗΜΕΡΙΝΗ live φορμουλα (6/10/2026, Στελιος «τι λειπει απο εκεινο το backtest;»).
Σταθερες live ρυθμισεις (οχι LOSO): Μ1 (1.4, 8, ∞, .5) 25% + Μ2 (1.3, 1.5, ∞, 25, φιλικα .5, εγχωρια ×1.5) 75%.
ΛΕΙΠΟΥΝ ακομα: αποδοσεις νικητη (δεν υπαρχει ιστορικο). Εξοδος: bcl_engine_preds_live.pkl → bcl_market_check.py"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, pickle, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import bcl_common as B
D = pickle.load(open('bcl_engine_preds2f.pkl', 'rb')); ids = D['id']
pos = {i: k for k, i in enumerate(ids)}
pr = B.run(B.load(pre=True), 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5)
M2 = np.full(len(ids), np.nan)
for mid, (p, y) in pr.items():
    if mid in pos: M2[pos[mid]] = p
src = open('dom_bk_engine_test.py', encoding='utf-8').read().split("LIVE = (.7, 8, 9999, .5, False)")[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1).replace("ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']", "ARGS = ['BCL']")
NS = {'__name__': 'b'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, NS)
G = NS['G']; full = NS['run']('BCL', 1.4, 8, 9999, .5, False)[0]; gp = {i: k for k, i in enumerate(G.id.values)}
M1 = np.array([full[gp[i]] for i in ids])
FIN = .25 * M1 + .75 * np.where(np.isfinite(M2), M2, M1)
D2 = dict(D); D2['FIN'] = FIN; D2['HB'] = FIN
pickle.dump(D2, open('bcl_engine_preds_live.pkl', 'wb'))
print('ok')
