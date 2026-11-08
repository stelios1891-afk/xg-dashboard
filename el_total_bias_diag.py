# -*- coding: utf-8 -*-
"""el_total_bias_diag.py — ΔΙΑΓΝΩΣΗ (οχι τεστ): απο πού ερχεται το «σύνολο χαμηλά» (+1.8 π.) του v2 (25/9/2026).
Σπαει το (πραγματικο − μοντελο) σε: παρατασεις (το μοντελο προβλεπει 40′) · ρυθμος (κατοχες) · ευστοχια (ποντοι/κατοχη).
Εξοδος: el_total_bias_diag_out.txt"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
src = open('el_loso_totals.py', encoding='utf-8').read().split('GRID = list(')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
T2 = run_t(0.25, 9999, 0.7, 50.0, 0.0)
gmin = D.gmin.values[IDX]; ot = gmin > 40.5
poss_act = D.poss.values[IDX]; pace_act = D.pace.values[IDX]
P(f'ματς με closing {len(IDX)} (κανονικη περιοδος {RS.sum()})')
P(f'{"σεζον":7s} {"ματς":>5s} {"παρατ%":>7s} {"π/παρατ":>8s} {"πραγμ−μοντ":>11s} {"χωρις παρατ":>12s} {"πραγμ−αγορα":>12s} {"αγορα χ.παρατ":>13s}')
for s in EVAL + ['ΟΛΑ']:
    m = RS & ((SE == s) if s != 'ΟΛΑ' else True)
    if m.sum() < 30: continue
    r = TOT - T2; q = TOT - MT
    otp = ((TOT - TOT * 40 / gmin))[m & ot].mean() if (m & ot).any() else 0
    P(f'{s[-4:]:7s} {m.sum():5d} {ot[m].mean()*100:6.1f}% {otp:8.1f} {r[m].mean():+11.2f} {r[m & ~ot].mean():+12.2f} {q[m].mean():+12.2f} {q[m & ~ot].mean():+13.2f}')
P('')
P('μεσο (πραγμ − μοντελο) που εξηγουν οι παρατασεις = ποσοστο παρατασης × ποντοι ανα παρατ. (αναλογικα με τα λεπτα)')
m = RS
ot_contrib = np.where(ot, TOT - TOT * 40 / gmin, 0.0)
P(f'  συνολο: {ot_contrib[m].mean():+.2f} π. απο τις παρατασεις · υπολοιπο {(TOT - T2 - ot_contrib)[m].mean():+.2f}')
P('')
P('ΣΠΑΣΙΜΟ ΤΟΥ ΥΠΟΛΟΙΠΟΥ (κανονικος χρονος, 40′): ρυθμος vs ευστοχια — χρειαζεται η προβλεψη ρυθμου του μοντελου')
