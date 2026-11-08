# -*- coding: utf-8 -*-
"""dom_bk_step2.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ, βημα 2 μετα τον ελεγχο (10/10/2026, Στελιος «τρεξτα ολα»).
Βαση: dom_bk_audit_R.pkl (FINAL + διορθωση εδρας Β1 οπου ΠΕΡΑΣΕ: Ισπανια, Γερμανια).
 (α) ΑΠΟ ΠΟΥ ΕΡΧΕΤΑΙ η αποσταση απο το κλεισιμο: RMSE μοντελο vs κλεισιμο σε ολα / χωρις ματς με τεραστια διαφωνια (|μοντ − ανοιγμα| ≥ 10, ≥ 15).
 (β) PICKS ανα μεγεθος διαφωνιας με το ΑΝΟΙΓΜΑ (<3 / 3-6 / 6-10 / ≥10 π.): μοντελο μονο ≥8% και μιξη 50/50 ≥6%, ανοιγμα & κλεισιμο.
 ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση) για «ταβανι διαφωνιας» Χ (5, 6, 8, 10): χωρις pick οταν |μοντ − ανοιγμα| ≥ Χ.
   ΠΕΡΝΑ αν τα κομμενα picks ειναι αρνητικα και χειροτερα απο τα υπολοιπα σε ≥4/5 σεζον (ολα τα πρωταθληματα μαζι) ΚΑΙ σε ≥4/6 πρωταθληματα.
Εξοδος: dom_bk_step2_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, pickle, math, collections
import numpy as np
from statistics import NormalDist
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
sys.stdout.reconfigure(encoding='utf-8')
O = []
def W(s=''): print(s, flush=True); O.append(str(s))
R = pickle.load(open('dom_bk_audit_R.pkl', 'rb'))
B1 = {'ACB', 'BBL'}
R['m'] = np.where(R.lg.isin(B1), R.pb, R.pf)
Phi = NormalDist().cdf
def pick(m, L, o1, o2, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / s); pl = Phi((-m - L - .5) / s)
    else: pw = Phi((m + L) / s); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
rows = []
for r in R.itertuples():
    mk = MK.get(r.i)
    if not mk: continue
    for when in ('op', 'cl'):
        L, o1, o2 = mk[when]; mm = mk['mo' if when == 'op' else 'mc']
        for rule, mu, s, thr in (('μοντελο ≥8%', r.m, 12.2, .08), ('μιξη 50/50 ≥6%', mm + .5 * (r.m - mm), 12.3, .06)):
            sd, e, od = pick(mu, L, o1, o2, s)
            if e < thr: continue
            v = (r.act + L) * sd
            rows.append(dict(lg=r.lg, y=r.y, when=when, rule=rule, u=(od - 1) if v > 0 else (0 if v == 0 else -1), dis=abs(r.m - r.mo)))
import pandas as pd
P_ = pd.DataFrame(rows)
# ---- (α) ----
W('=== (α) ΑΠΟΣΤΑΣΗ ΑΠΟ ΤΟ ΚΛΕΙΣΙΜΟ: ολα / χωρις τεραστιες διαφωνιες με το ανοιγμα ===')
for lg in LGS + ['ΟΛΑ']:
    x = R if lg == 'ΟΛΑ' else R[R.lg == lg]
    cells = []
    for X in (99, 15, 10):
        z = x[(x.m - x.mo).abs() < X]
        cells.append(f'{"ολα" if X == 99 else f"<{X}"}: {np.sqrt(np.mean((z.act - z.m) ** 2)):.2f} vs {np.sqrt(np.mean((z.act - z.mc) ** 2)):.2f} (n {len(z)})')
    W(f'  {NAME.get(lg, lg):9s} ' + ' · '.join(cells))
# ---- (β) ----
W(''); W('=== (β) PICKS ανα διαφωνια μοντελου με το ΑΝΟΙΓΜΑ (ROI · n · μοναδες) ===')
BK = [(0, 3), (3, 6), (6, 10), (10, 99)]
for rule in ('μοντελο ≥8%', 'μιξη 50/50 ≥6%'):
    for when in ('op', 'cl'):
        z = P_[(P_.rule == rule) & (P_.when == when)]
        W(f'  {rule} · {"ανοιγμα" if when == "op" else "κλεισιμο"} · ολα {z.u.mean()*100:+.1f}% ({len(z)}, {z.u.sum():+.1f}μ) · ' +
          ' · '.join(f'{a}-{b if b < 99 else "+"}: {z[(z.dis >= a) & (z.dis < b)].u.mean()*100:+.1f}% ({((z.dis >= a) & (z.dis < b)).sum()})' for a, b in BK))
        for lg in LGS:
            q = z[z.lg == lg]
            W(f'      {NAME[lg]:9s} ολα {q.u.mean()*100:+6.1f}% ({len(q):3d}) · ' + ' · '.join(f'{a}-{b if b < 99 else "+"}: {q[(q.dis >= a) & (q.dis < b)].u.mean()*100 if ((q.dis >= a) & (q.dis < b)).any() else 0:+.0f}% ({((q.dis >= a) & (q.dis < b)).sum()})' for a, b in BK))
# ---- ταβανι διαφωνιας (προ-δηλωμενο) ----
W(''); W('=== ΤΑΒΑΝΙ ΔΙΑΦΩΝΙΑΣ: χωρις pick οταν |μοντ − ανοιγμα| ≥ Χ (κριτηριο: κομμενα αρνητικα & χειροτερα σε ≥4/5 σεζον ΚΑΙ ≥4/6 πρωταθληματα) ===')
for rule in ('μοντελο ≥8%', 'μιξη 50/50 ≥6%'):
    for when in ('op', 'cl'):
        z = P_[(P_.rule == rule) & (P_.when == when)]
        for X in (5, 6, 8, 10):
            cut, keep = z[z.dis >= X], z[z.dis < X]
            sy = sum(1 for y in EV if (cut.y == y).sum() >= 3 and cut[cut.y == y].u.mean() < 0 and cut[cut.y == y].u.mean() < keep[keep.y == y].u.mean())
            sl = sum(1 for lg in LGS if (cut.lg == lg).sum() >= 3 and cut[cut.lg == lg].u.mean() < 0 and cut[cut.lg == lg].u.mean() < keep[keep.lg == lg].u.mean())
            ok = sy >= 4 and sl >= 4
            W(f'  {rule:15s} {"ανοιγμα " if when == "op" else "κλεισιμο"} Χ {X:2d}: κοβει {cut.u.mean()*100:+6.1f}% ({len(cut):3d}, {cut.u.sum():+6.1f}μ) · μενουν {keep.u.mean()*100:+5.1f}% ({len(keep)}, {keep.u.sum():+6.1f}μ, θετ σεζον {sum(1 for y in EV if keep[keep.y == y].u.mean() > 0)}/5) · σεζον {sy}/5 · λιγκες {sl}/6' + ('  <- ΠΕΡΝΑ' if ok else '  ✗'))
            if ok:
                W('        μενουν ανα πρωταθλημα: ' + ' · '.join(f'{NAME[lg]} {keep[keep.lg == lg].u.mean()*100:+.1f}% ({(keep.lg == lg).sum()}, θετ {sum(1 for y in EV if keep[(keep.lg == lg) & (keep.y == y)].u.mean() > 0)}/5)' for lg in LGS))
open('dom_bk_step2_out.txt', 'w', encoding='utf-8').write('\n'.join(O))
