"""
intl_imp_s4_export.py — εξαγωγη Σ4 (σημασια παικτη = συμμετοχες×rating×αρχηγος, intl_importance_combo) ανα ματς + συντελεστης LOSO ανα σεζον,
για το τεστ παραθυρου 72ω (intl_window_test.py IMP_S4=1). 25/9/2026, εντολη Στελιου.
Συντελεστης (Elo ανα μοναδα dW6 = απουσια γηπ − απουσια φιλοξ): ordered logit στα αγωνιστικα των ΑΛΛΩΝ σεζον·
  Μ1/Μ3 (με αξια): χαρακτηριστικα [diff H3, ln V_full, dW6] (ιδια αξια με τα diffs του backtest) · Μ2 (αγκυρα, χωρις αξια): [diff H3, dW6].
Εξοδος: intl_imp_s4.csv (mid, dW6) · intl_imp_s4_coef.json {σεζον: {M1, M2, M3}}
"""
import sys, os, json, contextlib
import numpy as np, pandas as pd
src = open('intl_importance_combo.py', encoding='utf-8').read(); cut = src.index('rows = []')
g = {'__name__': 's4x'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:cut], g)
sys.stdout.reconfigure(encoding='utf-8')
gi = g['g']; E = gi['E']; C = g['C']; fit = g['fit_ol_multi']
E[['mid', 'dW6']].dropna().to_csv('intl_imp_s4.csv', index=False)
SEAS = sorted(set(C.season)) + ['2627']
coef = {}
for s in SEAS:
    tr = C[C.season != s]
    b1 = fit(tr[['diff', 'lv_full', 'dW6']].values.astype(float), tr['y'].values)[0]; b2 = fit(tr[['diff', 'dW6']].values.astype(float), tr['y'].values)[0]
    coef[s] = dict(M1=float(b1[2] / b1[0]), M3=float(b1[2] / b1[0]), M2=float(b2[1] / b2[0]))
json.dump(coef, open('intl_imp_s4_coef.json', 'w', encoding='utf-8'), indent=1)
print(f"intl_imp_s4.csv: {int(E.dW6.notna().sum())} ματς · συντελεστες (Elo ανα 10% απουσια): " + ' · '.join(f"{s}: M1 {c['M1'] * .1:+.1f} / M2 {c['M2'] * .1:+.1f}" for s, c in coef.items()))
