# -*- coding: utf-8 -*-
"""t106_abs_slope_by_month.py — ΚΛΙΣΗ ΔΙΟΡΘΩΣΗΣ ΑΠΟΥΣΙΩΝ ΣΤΑ ΧΑΝΤΙΚΑΠ ΑΝΑ ΜΗΝΑ με την ΤΩΡΙΝΗ live εκδοχη (26/10/2026, Στελιος «μετρα το παλι
με τη νεα εκδοση»). ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει τιποτα. Συνεχεια του t105 Υ3 (εκει: μοντελο t19, Νοε-Φεβ .43-.73, Μαρ .99).
Στησιμο = t65_bet (i) (t62 εκδοχη 4: περσινο DARKO+LEBRON, κοστος w·0.75·(v+2)·λεπτα/48, ανοιγμα Crown, σ 13.5), σεζον 2023-26:
  ΠΡΙΝ (live ως 23/10) = φετινο κομματι box t59 με M 500 · ΤΩΡΑ (live απο 24/10) = «δικο μας box Β» με M 250.
Κλιση = OLS (πραγμ. − μοντελο χωρις απουσιες) πανω στη διορθωση απουσιων, ΜΟΝΟ ματς με διορθωση ≠ 0 (1.00 = σωστο, <1 = υπερβαλλουμε).
Εξοδος: nba_tests/t106_abs_slope_by_month_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't65_bet.py'), encoding='utf-8').read().split("P(''); P('  ΠΙΝΑΚΑΣ Χ1")[0]
g = {'__file__': os.path.join(SC, 't65_bet.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, D, VERS, ys, ACT, M0, TEST = g['np'], g['pd'], g['D'], g['VERS'], g['ys'], g['ACT'], g['M0'], g['TEST']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
MON = pd.to_datetime(D.date).dt.month.values
MN = ((10, 'Οκτ'), (11, 'Νοε'), (12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ'), (3, 'Μαρ'), (4, 'Απρ'))
def sl(adj, mk):
    x = adj[mk]; y = (ACT - M0)[mk]
    if len(x) < 50: return np.nan, np.nan, len(x), np.nan
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (e @ e) / (len(y) - 2)
    return b[1], np.sqrt(cov[1, 1]), len(x), float(np.abs(x).mean())
VV = (('ΠΡΙΝ (box t59, M 500)', 'ΣΗΜΕΡΙΝΗ (4, box M=500)'), ('ΤΩΡΑ (Β, M 250)', 'δικο μας box M=250'))
P('t106 · κλιση διορθωσης απουσιων ΧΑΝΤΙΚΑΠ ανα μηνα · σεζον 2022-23 … 2025-26 (4) · 1.00 = σωστο, <1 = υπερβαλλουμε, >1 = υποτιμαμε')
P('  στηλες: κλιση ± σφαλμα · ματς με διορθωση · μεση |διορθωση| (ποντοι διαφορας)')
TM = np.isin(ys, TEST)
for nm_v, key in VV:
    adj = VERS[key][1]; nz = np.abs(adj) > 1e-9
    P(f'\n  {nm_v}')
    for m, nm in MN:
        b, se, n, a = sl(adj, TM & nz & (MON == m))
        P(f'    {nm}: {b:5.2f} ± {se:.2f} · {n:4d} ματς · |διορθ.| {a:.2f}π')
    for lab, ms in (('Νοε-Φεβ', [11, 12, 1, 2]), ('Μαρ-Απρ', [3, 4]), ('ΟΛΗ', list(range(1, 13)))):
        b, se, n, a = sl(adj, TM & nz & np.isin(MON, ms))
        P(f'    {lab}: {b:5.2f} ± {se:.2f} · {n:4d} ματς · |διορθ.| {a:.2f}π')
    P('    ανα σεζον (ολη η σεζον): ' + ' · '.join(f"{s - 1}-{s % 100:02d} {sl(adj, nz & (ys == s))[0]:.2f}±{sl(adj, nz & (ys == s))[1]:.2f}" for s in TEST))
    P('    Νοε-Φεβ ανα σεζον: ' + ' · '.join(f"{s - 1}-{s % 100:02d} {sl(adj, nz & (ys == s) & np.isin(MON, [11, 12, 1, 2]))[0]:.2f}" for s in TEST))
# ισοτητα μηνων (χ²) για ΤΩΡΑ
adj = VERS['δικο μας box M=250'][1]; nz = np.abs(adj) > 1e-9
bs = [sl(adj, TM & nz & (MON == m))[:2] for m, _ in MN]; bs = [(b, s) for b, s in bs if np.isfinite(b)]
w = np.array([1 / s ** 2 for _, s in bs]); bb = np.array([b for b, _ in bs]); mu = (w * bb).sum() / w.sum()
from scipy.stats import chi2
c = float((w * (bb - mu) ** 2).sum())
P(f'\n  ΤΩΡΑ: ιδια κλιση ολους τους μηνες; σταθμ. μεσος {mu:.2f} · χ² {c:.1f} με {len(bs) - 1} β.ε. · p {1 - chi2.cdf(c, len(bs) - 1):.2f} (μικρο p = οι μηνες διαφερουν πραγματικα)')
open(os.path.join(SC, 't106_abs_slope_by_month_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
