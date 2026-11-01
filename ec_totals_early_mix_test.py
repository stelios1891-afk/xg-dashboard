# -*- coding: utf-8 -*-
"""ec_totals_early_mix_test.py — EuroCup ΣΥΝΟΛΑ αγων 1-6: ΒΟΗΘΑΕΙ Η ΜΙΞΗ; (5/10/2026, Στελιος: «η μιξη ηταν το βασικο επιχειρημα»).
Προβλεψεις = «καθαρες» (ec_totals_nested_test: μηχανη/βαρη/φιλικα επιλεγμενα ΜΟΝΟ απο τις αλλες σεζον).
ΣΤΑΘΕΡΟΙ κανονες (κανενας δεν επιλεγεται απο τα δεδομενα): βαρος μοντελου w {.5 (live), .75, 1} × κατωφλι {4, 6, 8, 10}% · ανοιγμα Crown U2020-25.
+ log-loss καλυψης (ακριβεια πιθανοτητας) ανα w στις αγων 1-6 και 7+.
Εξοδος: ec_totals_early_mix_out.txt"""
import sys, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'e'}
exec(open('ec_totals_nested_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_nested_out.txt', 'w', encoding='utf-8')", "open('_unused_nest.txt', 'w', encoding='utf-8')"), NS)
HELD, picks, EVM, MI, MKT, TOT, GN, cov = (NS[k] for k in ('HELD', 'picks', 'EVM', 'MI', 'MKT', 'TOT', 'GN', 'cov'))
seasn = NS['seasn']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
for lab, early in (('ΑΓΩΝ 1-6', True), ('ΑΓΩΝ 7+ (για συγκριση)', False)):
    P(f'################ {lab} — σταθεροι κανονες πανω στις «καθαρες» προβλεψεις ################')
    for w in (.5, .75, 1.0):
        for thr in (.04, .06, .08, .10):
            R = picks(HELD, w, thr, early, EVM)
            a = np.array([x[0] for x in R]); ps = {Y: np.mean([x[0] for x in R if x[1] == Y]) for Y in EVM if any(x[1] == Y for x in R)}
            no = sum(1 for x in R if x[2])
            P(f'  w {w:.2f} ≥{thr:.0%}: {len(a):3d} picks (over {no}) · ROI {a.mean()*100 if len(a) else 0:+6.1f}% · {a.sum():+6.1f}u · θετ. {sum(v > 0 for v in ps.values())}/{len(ps)} · '
              + ' '.join(f'{Y[-2:]}:{v*100:+.0f}' for Y, v in ps.items()))
    LL = {}
    for w in (.3, .5, .75, 1.0):
        arr = []
        for i in MI:
            if (GN[i] <= 5) != early or not np.isfinite(HELD[i]): continue
            T, mk, oo, ou = MKT[i]['o']; v = TOT[i] - T
            if v == 0: continue
            po, pq, pu = cov(mk + w * (HELD[i] - mk), T, 16.7); q = po / (po + pu) if v > 0 else pu / (po + pu); arr.append(-math.log(max(q, 1e-9)))
        LL[w] = np.mean(arr)
    P('  log-loss καλυψης (μικροτερο = πιο σωστη πιθανοτητα· κορωνα-γραμματα .6931): ' + ' · '.join(f'w {w}: {v:.4f}' for w, v in LL.items()))
    P('')
open('ec_totals_early_mix_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
