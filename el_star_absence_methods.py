# -*- coding: utf-8 -*-
"""el_star_absence_methods.py — ΣΤΑ ΙΔΙΑ ΜΑΤΣ (απουσια σημαντικου σκορερ) ΠΩΣ ΘΑ ΔΟΥΛΕΥΑΝ: χωρις διορθωση · live on/off (W4) · «χαμενο σκοραρισμα» S1
(27/10/2026, Στελιος «στα ιδια ματς μπορεις να μου δειξεις πως θα λειτουργουσε το on/off και η εκδοχη που σκεφτηκαμε προηγουμενως;»). ΠΕΡΙΓΡΑΦΙΚΟ.
Ομαδες ματς = el_star_absence_totals.py (ορισμος Γ: ≥12 ποντοι/ματς). Διορθωσεις = LOSO (εκτος δειγματος) απο el_absence_onoff_test (W4) &
el_scoring_absence_test (S1: λεπτα + λεπτα×ποντοι/40). Picks συνολων ≥8% ανοιγμα Crown. Εξοδος: el_star_absence_methods_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# 1) πληρες τεστ «χαμενου σκοραρισματος» (σιωπηλα) → RES (LOSO διορθωσεις)
sc = open('el_scoring_absence_test.py', encoding='utf-8').read().split("open('el_scoring_absence_out.txt'")[0]
_a = "def P(s=''): print(s, flush=True); out.append(str(s))"; _i = sc.rfind(_a); sc = sc[:_i] + "def P(s=''): pass" + sc[_i + len(_a):]
nsS = {}
with contextlib.redirect_stdout(_B()): exec(sc, nsS)
# 2) ομαδες ματς του el_star_absence_totals (με το ιδιο namespace)
st = open('el_star_absence_totals.py', encoding='utf-8').read()
st = st.split("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", 1)[1].split("def roi(m):")[0]
st = "ns = {'ns': ns}" + chr(10) + st
with contextlib.redirect_stdout(_B()): exec(st, nsS)
sys.stdout.reconfigure(encoding='utf-8')
g = nsS; rows, ys, SE, TOT, T0, OP, CL, OU, LIN = (g[k] for k in ('rows', 'ys', 'SE', 'TOT', 'T0', 'OP', 'CL', 'OU', 'LIN'))
W4 = g['HELD']['W4 μονο on/off']; S1 = g['RES']['S1 λεπτα + ποντοι/40'][1]; pick_res = g['pick_res']; REC_ = g['REC_']
METH = {'χωρις διορθωση': np.zeros(len(rows)), 'live on/off': W4, 'χαμενο σκοραρισμα': S1}
PK = {k: pick_res(v) for k, v in METH.items()}
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
f = np.array([x['flags']['Γ'] for x in REC_]); nw = np.array([x['new']['Γ'] for x in REC_])
GR = (('0 σημαντικοι απουσες', f == 0), ('1 σημαντικος', f == 1), ('2+ σημαντικοι', f >= 2), ('≥1 ΝΕΑ απουσια (1-3 ματς)', (f >= 1) & (nw >= 1)), ('≥1 μονο μακροχρονια', (f >= 1) & (nw == 0)))
def roi(sd, rs, m):
    m = m & (sd != 0)
    if not m.any(): return '   —            '
    ps = pd.Series(rs[m]).groupby(ys[m]).sum(); return f'{100 * np.nanmean(rs[m]):+6.1f}% ({int(m.sum()):3d}, {np.nansum(rs[m]):+5.1f}μ, {int((ps > 0).sum())}/{len(ps)})'
P('el_star_absence_methods · Ευρωλιγκα 2021-25 · ορισμος σημαντικου: ≥12 ποντοι/ματς (10 τελευταια, ≥3 συμμ., ≥20′) · διορθωσεις LOSO · picks ≥8% ανοιγμα Crown')
for lab, m in GR:
    P(f'\n=== {lab} · {int(m.sum())} ματς · πραγματικο − μοντελο (χωρις διορθωση) {np.mean(TOT[m] - T0[m]):+.2f} ===')
    P('  μεθοδος              │ μεση διορθωση συνολου │ υπολοιπο (πραγμ − μοντελο+διορθ.) │ σφαλμα │ picks ολα · Over · Under')
    for k, v in METH.items():
        sd, rs = PK[k]; e = TOT[m] - T0[m] - v[m]
        P(f'  {k:20s} │ {np.mean(v[m]):+6.2f} │ {np.mean(e):+6.2f} │ {np.sqrt(np.mean(e ** 2)):6.2f} │ {roi(sd, rs, m)} · Over {roi(sd, rs, m & (sd == 1))} · Under {roi(sd, rs, m & (sd == -1))}')
P('\n=== ΟΛΑ ΤΑ ΜΑΤΣ (για μετρο) ===')
for k, v in METH.items():
    sd, rs = PK[k]; e = TOT - T0 - v; m = np.ones(len(rows), bool)
    P(f'  {k:20s} │ σφαλμα {np.sqrt(np.mean(e ** 2)):6.2f} │ picks {roi(sd, rs, m)} · Over {roi(sd, rs, sd == 1)} · Under {roi(sd, rs, sd == -1)}')
# παραδειγμα: ο Ολυμπιακος−Φενερ 23/10 δεν ειναι στο δειγμα (2026-27)· δειχνουμε τα 5 ματς με τη μεγαλυτερη S1 διορθωση
P('\n=== ΠΑΡΑΔΕΙΓΜΑΤΑ: τα 6 ματς με τη μεγαλυτερη αρνητικη διορθωση «χαμενου σκοραρισματος» ===')
TEAMS = g['TEAMS']
for j in np.argsort(S1)[:6]:
    sea, hc, ac, ts = TEAMS[j]
    P(f'  {sea} {pd.Timestamp(ts, unit="s"):%d/%m/%Y} {hc}-{ac} · γραμμη {LIN[j]:.1f} · μοντελο {T0[j]:.1f} · on/off {W4[j]:+.1f} · σκοραρισμα {S1[j]:+.1f} · πραγματικο {TOT[j]:.0f}')
open('el_star_absence_methods_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
