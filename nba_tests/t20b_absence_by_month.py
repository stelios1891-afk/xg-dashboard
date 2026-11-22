# -*- coding: utf-8 -*-
"""t20b_absence_by_month.py — ΚΟΣΤΟΣ ΑΠΟΥΣΙΩΝ ΑΝΑ ΠΕΡΙΟΔΟ ΜΕ ΤΙΣ ΠΡΑΓΜΑΤΙΚΕΣ ΑΠΟΥΣΙΕΣ (21/10/2026, Στελιος: «γιατι δεν κοιτας ποιοι επαιξαν;»).
Στο t19 το «πραγματικο κοστος ανα δικο μας ποντο» βγηκε 0.6 Νοε-Φεβ και 1.0 τον Μαρτιο — με «γνωστο εκτος» = εχασε τα 2 προηγουμενα ματς
(καποιοι επιστρεφουν). Εδω: απουσια = παικτης ρολου (≥20′) που ΔΕΝ επαιξε στο ματς (box score — εκ των υστερων, ιδιο με t10).
Παλινδρομηση (πραγματικο − μηχανη χωρις απουσιες) πανω στη live διορθωση 0.75·(αξια+2)·λεπτα/48: 1.00 = σωστο κοστος.
Και για συγκριση η ιδια μετρηση με το «εχασε 2 προηγουμενα» (οπως το t19). Εξοδος: t20b_absence_by_month_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't10_absence_system.py'), encoding='utf-8').read().split("P('NBA · ΕΙΝΑΙ ΚΑΛΟ ΤΟ ΣΥΣΤΗΜΑ ΑΠΟΥΣΙΩΝ;")[0]
ns = {'__file__': os.path.join(SC, 't10_absence_system.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; ACT = ns['ACT']; M0 = ns['M0']; CLS = ns['CLS']; m0 = ns['m0']; cost = ns['cost']
GL = ns['GL']; inner = ns['ns']
X_post = np.array([cost(i, K=0.75, REP=-2.0) for i in range(len(GL))])      # εκ των υστερων (δεν επαιξαν)
LH, LA = None, None
inner['REP'] = -2.0
LHk = np.zeros(len(G)); LAk = np.zeros(len(G)); dD = inner['dD']
for i in range(len(G)):
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    LHk[i], _ = inner['team_loss'](h, d, 2); LAk[i], _ = inner['team_loss'](a, d, 2)
X_k2 = 0.75 * (LHk - LAk)                                                   # «εχασε 2 προηγουμενα» (οπως backtests/t19)
MON = G.date.dt.month.values
PER = np.array(['Οκτ' if m == 10 else 'Νοε-Δεκ' if m in (11, 12) else 'Ιαν-Φεβ' if m in (1, 2) else 'Μαρ' if m == 3 else 'Απρ' for m in MON])
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def slope(y, x, m):
    m = m & (np.abs(x) > 0) & np.isfinite(y)
    if m.sum() < 80: return np.nan, np.nan, int(m.sum())
    X = np.c_[np.ones(m.sum()), x[m]]; c, *_ = np.linalg.lstsq(X, y[m], rcond=None)
    r = y[m] - X @ c; s2 = r.var() * m.sum() / (m.sum() - 2); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return c[1], se[1], int(m.sum())
P('NBA · ΠΡΑΓΜΑΤΙΚΟ ΚΟΣΤΟΣ ΑΠΟΥΣΙΩΝ ανα ΔΙΚΟ ΜΑΣ ΠΟΝΤΟ, ανα περιοδο · 1.00 = η φορμουλα ειναι σωστη (αντικ. −2)')
P(f'  {"περιοδος":10s} | {"ΠΡΑΓΜΑΤΙΚΕΣ απουσιες (δεν επαιξαν)":38s} | {"«εχασε 2 προηγουμενα» (οπως t19)":36s} | αγορα κλεισ. (πραγμ.)')
for p in ('Οκτ', 'Νοε-Δεκ', 'Ιαν-Φεβ', 'Μαρ', 'Απρ'):
    mm = m0 & (PER == p)
    a, sa, na = slope(ACT - M0, X_post, mm); b, sb, nb = slope(ACT - (M0 + X_k2 * 0) , X_k2, mm); c, sc, nc = slope(CLS - M0, X_post, mm)
    P(f'  {p:10s} | {a:5.2f} ± {sa:.2f} (ματς {na:4d}, μ.ο. |διορθ.| {np.abs(X_post[mm]).mean():.2f})     | {b:5.2f} ± {sb:.2f} (ματς {nb:4d})              | {c:5.2f} ± {sc:.2f}')
P('  (η αγορα: ποσο τιμολογει στο κλεισιμο ανα δικο μας ποντο τις ΠΡΑΓΜΑΤΙΚΕΣ απουσιες)')
open(os.path.join(SC, 't20b_absence_by_month_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
