"""
intl_importance_combo.py — ΣΥΝΔΥΑΣΜΟΙ ΜΕΤΡΩΝ ΣΗΜΑΣΙΑΣ ΠΑΙΚΤΗ (25/9/2026, Στελιος: «μηπως καποιος συνδυασμος αποδιδε καλυτερα;»).
Πανω στα ιδια δεδομενα/δειγμα με intl_importance_test.py. ΠΡΟ-ΔΗΛΩΣΗ (ΠΡΙΝ τρεξει, ΜΙΑ εκτελεση), κριτηριο: RPS < LIVE ΚΑΙ ≥4/6 σεζον:
  Σ1 ολοι μαζι (W1..W5 ως ξεχωριστα χαρακτηριστικα, βαρη απο το logit) · Σ2 συμμετοχες + rating · Σ3 συμμετοχες + αρχηγος ·
  Σ4 ενα βαρος = συμμετοχες × max(rating−6,0.2) × (1+2·αρχηγος) · Σ5 αξια 2 ετων (V_full) + συνδυασμος W5 αντι για αξια αποστολης.
"""
import sys, io, contextlib, os
import numpy as np, pandas as pd
src = open('intl_importance_test.py', encoding='utf-8').read()
src = src.replace("W = {k: {} for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5')}", "W = {k: {} for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6')}")
src = src.replace("W['W5'][p] = mn * rq * (1 + 2 * cs)", "W['W5'][p] = mn * rq * (1 + 2 * cs); W['W6'][p] = (min(caps.get(p, 0), 80) / 80) * rq * (1 + 2 * cs)")
src = src.replace("feats = {k: ([], []) for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5')}", "feats = {k: ([], []) for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6')}")
src = src.replace("LAB = {'W0': 'βασικος (αναφορα)',", "LAB = {'W6': 'Σ4', 'W0': 'βασικος (αναφορα)',")
for _a in ("W = {k: {} for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6')}", "W['W6'][p]", "for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6')}"):
    assert _a in src, _a
cut = src.index("SEAS = ['2021'")
g = {'__name__': 'combo'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:cut], g)
sys.stdout.reconfigure(encoding='utf-8')
C, fit_ol_multi, probs_multi, rps = g['C'], g['fit_ol_multi'], g['probs_multi'], g['rps']
C = C.copy(); C['lv_full'] = np.log(C.vf_h / C.vf_a); C = C.replace([np.inf, -np.inf], np.nan).dropna(subset=['lv_full', 'dW6'])
SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
F = {'LIVE (diff + αξια αποστολης)': ['diff', 'lv_own'], 'Σ1 ολοι μαζι': ['diff', 'lv_own', 'dW1', 'dW2', 'dW3', 'dW4', 'dW5'],
     'Σ2 συμμετοχες + rating': ['diff', 'lv_own', 'dW2', 'dW3'], 'Σ3 συμμετοχες + αρχηγος': ['diff', 'lv_own', 'dW2', 'dW4'],
     'Σ4 συμμετοχες×rating×αρχηγος': ['diff', 'lv_own', 'dW6'], 'Σ5 αξια 2 ετων + συνδυασμος': ['diff', 'lv_full', 'dW5']}
rows = []
for name, fs in F.items():
    row = dict(variant=name); allP = []; ally = []
    for s in SEAS:
        tr = C[C.season != s]; te = C[C.season == s]
        b, c1, c2 = fit_ol_multi(tr[fs].values.astype(float), tr['y'].values); Pm = probs_multi(te[fs].values.astype(float), b, c1, c2)
        row[s] = round(rps(Pm, te['y'].values), 4); allP.append(Pm); ally.append(te['y'].values)
    row['ALL'] = round(rps(np.vstack(allP), np.concatenate(ally)), 5); row['n'] = sum(len(y) for y in ally); rows.append(row)
T = pd.DataFrame(rows).set_index('variant'); pd.set_option('display.width', 220); print(T.to_string())
ref = T.iloc[0]; outl = [T.to_string(), '']
for v in T.index[1:]:
    better = sum(1 for s in SEAS if T.loc[v, s] < ref[s]); ok = T.loc[v, 'ALL'] < ref['ALL'] and better >= 4
    l = f'  {v:30s}: ΔRPS {T.loc[v, "ALL"] - ref["ALL"]:+.5f} · καλυτερο σε {better}/6 · {"ΠΕΡΝΑ" if ok else "—"}'; print(l); outl.append(l)
open('intl_importance_combo_out.txt', 'w', encoding='utf-8').write('\n'.join(outl))
