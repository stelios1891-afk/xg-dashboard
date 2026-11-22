# -*- coding: utf-8 -*-
"""el_absence_metrics.py — EUROLEAGUE: η διορθωση απουσιων («μονο λεπτα», γ .5, LOSO) σε ΟΛΑ τα μετρα, οχι μονο ROI (9/10/2026, Στελιος).
Μετρα (E2021-25, 1.481 ματς): RMSE vs αποτελεσμα · Κ2 (πραγμ − κλεισιμο = a + b·(μοντ − κλεισιμο)), και vs ανοιγμα · log-loss καλυψης ανοιγματος
(σ 11.5) · αποσταση απο κλεισιμο · CLV των picks (κινηση ανοιγμα→κλεισιμο προς εμας, % προς/κοντρα). Ανα σεζον: ποσες σεζον καλυτερα."""
import sys, io, contextlib, collections, math
import numpy as np
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
G_ = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_player_absence_value.py', encoding='utf-8').read().split("P(''); P('## ΟΛΑ ΤΑ ΔΕΔΟΜΕΝΑ")[0], G_)
sys.stdout.reconfigure(encoding='utf-8')
rows, SE, Y, ys, fit = (G_[k] for k in ('rows', 'SE', 'Y', 'ys', 'fit'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
held = np.zeros(len(Y))
for Yr in SE:
    b, X = fit(.5, np.array([1, 0, 0, 0]), [s for s in SE if s != Yr]); held[ys == Yr] = (X @ b)[ys == Yr]
act = np.array([r['act'] for r in rows]); m0 = np.array([r['m'] for r in rows]); m1 = m0 + held
mo = np.array([r['mo'] for r in rows]); mc = np.array([r['mc'] for r in rows])
Phi = NormalDist().cdf
def k2(m, ref, msk):
    x = m[msk] - ref[msk]; z = act[msk] - ref[msk]; b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x)
    se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return b, b / se
def ll(m, msk):
    v = []
    for r, mm in zip(np.array(rows)[msk], m[msk]):
        L, o1, o2 = r['op']; x = r['act'] + L
        if abs(L - round(L)) < 1e-9: pw = Phi((mm + L - .5) / 11.5); pl = Phi((-mm - L - .5) / 11.5)
        else: pw = Phi((mm + L) / 11.5); pl = 1 - pw
        p = pw if x > 0 else (pl if x < 0 else max(1 - pw - pl, 1e-6)); v.append(-math.log(max(p, 1e-6)))
    return float(np.mean(v))
def clv(m, msk):
    mv = []
    for r, mm, a_o, a_c in zip(np.array(rows)[msk], m[msk], mo[msk], mc[msk]):
        L, o1, o2 = r['op']; pw = Phi((mm + L) / 11.5); pl = 1 - pw; e1, e2 = pw * o1 - 1, pl * o2 - 1
        sd, e = (1, e1) if e1 >= e2 else (-1, e2)
        if e >= .08: mv.append((a_c - a_o) * sd)
    mv = np.array(mv); return mv.mean(), np.mean(mv >= .5), np.mean(mv <= -.5), len(mv)
ALL = np.ones(len(Y), bool)
P('μετρο                         | σημερα            | με απουσιες       | καλυτερα σε')
def row(nm, f, better_low=True, fmt='{:.3f}'):
    a, b = f(m0, ALL), f(m1, ALL)
    per = [f(m1, ys == s) < f(m0, ys == s) if better_low else f(m1, ys == s) > f(m0, ys == s) for s in SE]
    P(f'{nm:30s}| {fmt.format(a):17s} | {fmt.format(b):17s} | {sum(per)}/5')
row('RMSE vs αποτελεσμα', lambda m, k: float(np.sqrt(np.mean((act[k] - m[k]) ** 2))))
row('log-loss καλυψης (ανοιγμα)', ll, fmt='{:.4f}')
row('αποσταση απο κλεισιμο (RMSE)', lambda m, k: float(np.sqrt(np.mean((mc[k] - m[k]) ** 2))))
for nm, ref in (('κλεισιμο', mc), ('ανοιγμα', mo)):
    b0, t0 = k2(m0, ref, ALL); b1, t1 = k2(m1, ref, ALL)
    per = [k2(m1, ref, ys == s)[0] > k2(m0, ref, ys == s)[0] for s in SE]
    P(f'{"Κ2 b vs " + nm:30s}| {b0:+.3f} (t {t0:+.1f})   | {b1:+.3f} (t {t1:+.1f})   | {sum(per)}/5 (μεγαλυτερο b)')
c0, c1 = clv(m0, ALL), clv(m1, ALL)
P(f'{"CLV picks ≥8% (μ.ο. π.)":30s}| {c0[0]:+.2f} ({c0[3]})       | {c1[0]:+.2f} ({c1[3]})       | ' + f'{sum(clv(m1, ys == s)[0] > clv(m0, ys == s)[0] for s in SE)}/5')
P(f'{"  % προς εμας / κοντρα":30s}| {c0[1]:.0%} / {c0[2]:.0%}         | {c1[1]:.0%} / {c1[2]:.0%}         |')
open('el_absence_metrics_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
