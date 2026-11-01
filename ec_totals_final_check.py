# -*- coding: utf-8 -*-
"""ec_totals_final_check.py — ΤΕΛΙΚΟ μοντελο συνολων EuroCup (Β* + φιλικα κT .25) πριν το live (5/10/2026):
ROI picks (μιξη 50/50, σ 16.7, edge ≥6%, ανοιγμα Crown) ανα περιοδο (αγων 1-3 / 4-6 / 7+) και σταθερες καμπυλης για το live (ολες οι σεζον).
Εξοδος: ec_totals_final_check_out.txt"""
import sys, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'f'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
TP, FT, FL, FRT, TOT, GN, seasn, MKT, cov, EVM = (NS[k] for k in ('TP', 'FT', 'FL', 'FRT', 'TOT', 'GN', 'seasn', 'MKT', 'cov', 'EVM'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
raw = TP['v2 λ8'] + .4 * FT + .25 * FL
allm = np.isfinite(raw) & np.isin(seasn, ['U2017'] + NS['EV8'])
b, a = np.polyfit(GN[allm], (TOT - raw)[allm], 1)
P(f'ΚΑΜΠΥΛΗ (ολες οι σεζον U2017-25): συνολο += {a:.3f} + {b:.4f} × αριθμος αγωνα (0 = 1ος) · αγων 1: {a:+.2f} · αγων 18: {a + 17 * b:+.2f}')
FIN = NS['FIN']
for per, f in (('αγων 1-3', lambda g: g <= 2), ('αγων 4-6', lambda g: (g >= 3) & (g <= 5)), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6), ('ολη', lambda g: g >= 0)):
    for thr in (.06,):
        R = {'over': [], 'under': []}
        for i in MKT:
            if seasn[i] not in EVM or not np.isfinite(FIN[i]) or not f(GN[i]): continue
            T, mk, oo, ou = MKT[i]['o']; po, pq, pu = cov(mk + .5 * (FIN[i] - mk), T, 16.7); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
            if max(eo, eu) >= thr:
                ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
                R['over' if ov else 'under'].append(((od - 1) if q > 0 else (0 if q == 0 else -1), seasn[i]))
        allr = R['over'] + R['under']
        cells = []
        for s_, L in (('ΟΛΑ', allr), ('over', R['over']), ('under', R['under'])):
            A = np.array([x[0] for x in L]); pos = sum(1 for Y in EVM if [x for x in L if x[1] == Y] and np.mean([x[0] for x in L if x[1] == Y]) > 0)
            cells.append(f'{s_} {A.mean()*100 if len(A) else 0:+.1f}% ({len(A)}, {A.sum():+.1f}u, {pos}/{len({x[1] for x in L})})')
        P(f'  {per:9s} μιξη ≥6% ανοιγμα: ' + ' · '.join(cells))
# τυφλο over ιδιες περιοδοι (για συγκριση)
for per, f in (('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
    L = []
    for i in MKT:
        if seasn[i] not in EVM or not f(GN[i]): continue
        T, mk, oo, ou = MKT[i]['o']; q = TOT[i] - T; L.append((oo - 1) if q > 0 else (0 if q == 0 else -1))
    P(f'  (τυφλο over {per}: {np.mean(L)*100:+.1f}% σε {len(L)})')
open('ec_totals_final_check_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
