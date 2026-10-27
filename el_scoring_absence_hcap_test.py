# -*- coding: utf-8 -*-
"""el_scoring_absence_hcap_test.py — EUROLEAGUE ΧΑΝΤΙΚΑΠ: «ΧΑΜΕΝΟ ΣΚΟΡΑΡΙΣΜΑ» ΑΠΟΝΤΩΝ ΠΑΝΩ απο το live (27/10/2026, Στελιος «ναι τρεξτο ετσι»).
Ιδιο στησιμο με το χαντικαπ του el_absence_onoff_test.py: 1.563 ματς E2021-25, live μοντελο el_newmodel_preds, LIVE απουσιες = 0.922·λεπτα
(φιλ − γηπ), picks χαντικαπ ≥8% ανοιγμα Crown, σ 11.5. ΝΕΟ: x = Σ φιλ w·(ποντοι/40 − μεσος) − Σ γηπ w·(ποντοι/40 − μεσος)
(ποντοι/40 = τα 15 τελευταια ματς του αποντα, μαζεμα 5′ προς τον μεσο 16.2· ιδιο με el_scoring_absence_test).
c = επιπλεον ποντοι διαφορας ανα μοναδα x, ridge 1 πανω στο υπολοιπο του LIVE, LOSO. Αναμενομενο c > 0 (λειπει σκορερ του φιλοξ. → γηπ. καλυτερα).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ιδια με το on/off χαντικαπ): ΠΕΡΝΑ αν LOSO RMSE διαφορας καλυτερο απο LIVE ≥4/5 ΚΑΙ c ιδιο προσημο ≥4/5 ΚΑΙ μοναδες picks ≥8% ≥ LIVE
  ΚΑΙ επιβεβαιωση EuroCup (ιδια με το τεστ συνολων: ποντοι ομαδας ~ δικα λεπτα×ποντοι/40, <0 ≥4/5, t ≤ −2 — εκει ΗΔΗ ✗).
Εξοδος: el_scoring_absence_hcap_out.txt"""
import sys, io, contextlib, collections
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_scoring_absence_test.py', encoding='utf-8').read().split("FH = np.array([feats(r['ah'])")[0]
_a = "def P(s=''): print(s, flush=True); out.append(str(s))"; _i = src.rfind(_a); src = src[:_i] + "def P(s=''): pass" + src[_i + len(_a):]
ns = {}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
inner = ns['ns']; rows, YH, YA, ys, SE, rmse, pts40, LG = inner['rows'], inner['YH'], inner['YA'], inner['ys'], inner['SE'], inner['rmse'], ns['pts40'], ns['LG']
hpicks = inner['hpicks']
YM = YH - YA
xl = np.array([sum(p['w'] for p in r['aa']) - sum(p['w'] for p in r['ah']) for r in rows]); live = 0.922 * xl
xs = np.array([sum(p['w'] * (pts40(p['pid'], p['ts']) - LG) for p in r['aa']) - sum(p['w'] * (pts40(p['pid'], p['ts']) - LG) for p in r['ah']) for r in rows])
R0 = YM - live; ALL = np.ones(len(rows), bool)
cfit = lambda m: float((xs[m] @ R0[m]) / (xs[m] @ xs[m] + 1.0))
call = cfit(ALL); per = {s: cfit(ys == s) for s in SE}; same = sum(1 for v in per.values() if np.sign(v) == np.sign(call))
hh = np.zeros(len(rows))
for Y in SE: hh[ys == Y] = cfit(ys != Y) * xs[ys == Y]
d = [rmse(R0 - hh, ys == s) - rmse(R0, ys == s) for s in SE]
P(f'Ευρωλιγκα 2021-25 · ματς {len(rows)} · x μη μηδενικο σε {int((np.abs(xs) > 1e-9).sum())} · 90% μεταξυ {np.percentile(xs, 5):+.1f} και {np.percentile(xs, 95):+.1f}')
P(f'\n## c (ποντοι διαφορας ανα μοναδα χαμενου σκοραρισματος, πανω απο το LIVE) {call:+.3f} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{v:+.3f}' for s, v in per.items()) + f' (ιδιο προσημο {same}/5, αναμενομενο >0)')
P(f'## LOSO RMSE διαφορας: χωρις {rmse(YM, ALL):.3f} · LIVE {rmse(R0, ALL):.3f} · LIVE + χαμενο σκοραρισμα {rmse(R0 - hh, ALL):.3f} · vs LIVE ' + ' '.join(f'{x:+.3f}' for x in d) + f' → καλυτερο {sum(x < 0 for x in d)}/5')
# αντι για τα λεπτα: μονο χαμενο σκοραρισμα (χωρις το 0.922·λεπτα)
c2 = lambda m: np.linalg.solve(np.c_[xl[m], xs[m]].T @ np.c_[xl[m], xs[m]] + np.eye(2), np.c_[xl[m], xs[m]].T @ YM[m])
b2 = c2(ALL); h2 = np.zeros(len(rows))
for Y in SE: bb = c2(ys != Y); m = ys == Y; h2[m] = np.c_[xl[m], xs[m]] @ bb
d2 = [rmse(YM - h2, ys == s) - rmse(R0, ys == s) for s in SE]
P(f'## ΕΝΑΛΛΑΚΤΙΚΗ: λεπτα + χαμενο σκοραρισμα ΜΑΖΙ (ξαναυπολογισμενα): λεπτα {b2[0]:+.3f} · σκοραρισμα {b2[1]:+.3f} · RMSE {rmse(YM - h2, ALL):.3f} · vs LIVE ' + ' '.join(f'{x:+.3f}' for x in d2) + f' → {sum(x < 0 for x in d2)}/5')
P('\n## PICKS χαντικαπ ≥8% ανοιγμα')
_, s0 = hpicks(np.zeros(len(rows))); uL, sL = hpicks(live); u1, s1 = hpicks(live + hh); u2, s2 = hpicks(h2)
P(f'   χωρις απουσιες          {s0}'); P(f'   LIVE (λεπτα)            {sL}'); P(f'   LIVE + χαμενο σκοραρ.   {s1}'); P(f'   λεπτα+σκοραρ. μαζι      {s2}')
OK = sum(x < 0 for x in d) >= 4 and same >= 4 and call > 0 and u1 >= uL
P(f'\nΚΡΙΤΗΡΙΑ: RMSE {sum(x < 0 for x in d)}/5 (≥4) · προσημο {same}/5 & >0 · μοναδες {u1:+.1f} vs LIVE {uL:+.1f} · EuroCup ✗ (απο το τεστ συνολων) → ' + ('ΠΕΡΝΑΕΙ στην EL (EuroCup ✗)' if OK else 'ΔΕΝ ΠΕΡΝΑΕΙ'))
# παραδειγμα: Ολυμπιακος (φιλοξ.) στη Μπεσικτας χωρις τους 4 (φετινα ποντοι/40)
NAME = inner['NAME']; inv = {v: k for k, v in NAME.items()}; xo = 0.0
for nm, mn in (('FOURNIER, EVAN', 24), ('MILUTINOV, NIKOLA', 19), ('MONTERO, JEAN', 26), ('DORSEY, TYLER', 18)):
    pid = inv.get(nm)
    if pid: xo += mn / 40 * (pts40(pid, 2e9) - LG)
P(f'\n## ΠΑΡΑΔΕΙΓΜΑ Μπεσικτας−Ολυμπιακος 28/10: x = +{xo:.1f} (χανει ο φιλοξ.) → επιπλεον {call * xo:+.1f} ποντοι υπερ Μπεσικτας πανω απο το live')
open('el_scoring_absence_hcap_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
