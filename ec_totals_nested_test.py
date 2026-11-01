# -*- coding: utf-8 -*-
"""ec_totals_nested_test.py — EuroCup ΣΥΝΟΛΑ: «ΚΑΘΑΡΟ» BACKTEST (5/10/2026, Στελιος: «τα ROI ειναι πανω στα ιδια δεδομενα — δεν φουσκωνουν;»).
Για ΚΑΘΕ σεζον-ελεγχου Y (U2020-25) ΟΛΕΣ οι επιλογες γινονται ΜΟΝΟ με τις αλλες σεζον:
  (1) μηχανη/βαρη (216 συνδυασμοι ec_totals_mech_test: μηχανη × εγχωρια κd × επιπεδο κl × καμπυλη) — ελαχιστο RMSE στις αλλες 7 (U2018-25)
  (2) φιλικα κT {0, .1, .25, .4} — RMSE στις αλλες 7
  (3) κανονας picks αγων 1-6 και 7+ ξεχωριστα: βαρος μοντελου w {.5, .75, 1} × κατωφλι {4, 6, 8, 10, 12}% — μοναδες στις αλλες 5 σεζον με αγορα
  (4) εδρα: v απο τα υπολοιπα των ΠΡΟΗΓΟΥΜΕΝΩΝ σεζον (ιδιες «καθαρες» προβλεψεις), ±1 → συμφωνει/διαφωνει
Μετρο: ROI στην ανοιγμα Crown ΜΟΝΟ στη σεζον-ελεγχου· συγκριση με τα «φουσκωμενα» (ιδια δεδομενα) του live κανονα.
Εξοδος: ec_totals_nested_out.txt"""
import sys, itertools, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'n'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
M = NS['M']; PRED = M['PRED']; FRT = NS['FRT']; FIN = NS['FIN']
D, TOT, GN, MKT, cov, EVM, EV8 = (NS[k] for k in ('D', 'TOT', 'GN', 'MKT', 'cov', 'EVM', 'EV8'))
seasn = np.asarray(NS['seasn'])
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def rm(v, ys):
    m = np.isin(seasn, ys) & np.isfinite(v); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
MI = [i for i in MKT if seasn[i] in EVM]
def picks(v, w, thr, early, ys):
    R = []
    for i in MI:
        if seasn[i] not in ys or (GN[i] <= 5) != early or not np.isfinite(v[i]): continue
        T, mk, oo, ou = MKT[i]['o']; po, pq, pu = cov(mk + w * (v[i] - mk), T, 16.7); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
        if max(eo, eu) < thr: continue
        ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
        R.append(((od - 1) if q > 0 else (0 if q == 0 else -1), seasn[i], ov, i))
    return R
RULES = list(itertools.product((.5, .75, 1.0), (.04, .06, .08, .10, .12)))
HELD = np.full(len(D), np.nan); ALL = []; LOG = []
for Y in EVM:
    tr8 = [x for x in EV8 if x != Y]; tr5 = [x for x in EVM if x != Y]
    g = min(PRED, key=lambda k: rm(PRED[k], tr8))
    kt = min((0, .1, .25, .4), key=lambda k: rm(PRED[g] + k * FRT, tr8))
    v = PRED[g] + kt * FRT
    m = seasn == Y; HELD[m] = v[m]
    re = max(RULES, key=lambda r: sum(x[0] for x in picks(v, r[0], r[1], True, tr5)))
    rl = max(RULES, key=lambda r: sum(x[0] for x in picks(v, r[0], r[1], False, tr5)))
    Re = picks(v, re[0], re[1], True, [Y]); Rl = picks(v, rl[0], rl[1], False, [Y])
    ALL += [(x, 'early') for x in Re] + [(x, 'late') for x in Rl]
    u = [x[0] for x in Re + Rl]
    LOG.append(f'  {Y}: μηχανη {g} · κT {kt} · αγων 1-6 w {re[0]} ≥{re[1]:.0%} · 7+ w {rl[0]} ≥{rl[1]:.0%} → '
               f'{len(u)} picks · ROI {np.mean(u)*100 if u else 0:+.1f}% · {sum(u):+.1f}u (1-6: {len(Re)} {sum(x[0] for x in Re):+.1f}u · 7+: {len(Rl)} {sum(x[0] for x in Rl):+.1f}u)')
P('################ «ΚΑΘΑΡΟ» BACKTEST — επιλογες ανα σεζον-ελεγχου ################')
for l in LOG: P(l)
def summ(L, lab):
    a = np.array([x[0][0] for x in L]); pos = sum(1 for Y in EVM if [x for x in L if x[0][1] == Y] and np.mean([x[0][0] for x in L if x[0][1] == Y]) > 0)
    P(f'  {lab:28s} {len(a):4d} picks · ROI {a.mean()*100 if len(a) else 0:+.1f}% · {a.sum():+.1f}u · θετικες σεζον {pos}/{len({x[0][1] for x in L})}')
P(''); P('=== ΣΥΝΟΛΟ «ΚΑΘΑΡΟ» ===')
summ(ALL, 'ολα'); summ([x for x in ALL if x[1] == 'early'], 'αγων 1-6'); summ([x for x in ALL if x[1] == 'late'], 'αγων 7+')
# συγκριση με τον live κανονα πανω στα ιδια δεδομενα (φουσκωμενο)
LIVE = [(x, 'early') for x in picks(FIN, .5, .06, True, EVM)] + [(x, 'late') for x in picks(FIN, 1.0, .06, False, EVM)]
P('=== ΓΙΑ ΣΥΓΚΡΙΣΗ: live κανονας πανω στα ιδια δεδομενα («φουσκωμενο») ===')
summ(LIVE, 'ολα'); summ([x for x in LIVE if x[1] == 'early'], 'αγων 1-6'); summ([x for x in LIVE if x[1] == 'late'], 'αγων 7+')
# ---- εδρα πανω στα «καθαρα» picks ----
P(''); P('=== ΕΔΡΑ πανω στα «καθαρα» picks (v απο προηγουμενες σεζον, ιδιες καθαρες προβλεψεις) ===')
R = TOT - HELD; SY = np.array([int(s[1:]) for s in seasn]); HOME = D.home.values
def veff(c, Y):
    msk = (HOME == c) & (SY < Y) & np.isfinite(R); n = msk.sum()
    return R[msk].sum() / (n + 15) if n else 0.0
G = collections.defaultdict(list)
for x, ph in ALL:
    u, Y, ov, i = x; v = veff(HOME[i], SY[i])
    grp = 'ΣΥΜΦΩΝΕΙ' if (ov and v >= 1) or (not ov and v <= -1) else ('ΔΙΑΦΩΝΕΙ' if (ov and v <= -1) or (not ov and v >= 1) else 'ουδετερη')
    G[grp].append((u, Y))
per = {}
for gname in ('ΣΥΜΦΩΝΕΙ', 'ουδετερη', 'ΔΙΑΦΩΝΕΙ'):
    L = G.get(gname, [])
    if not L: continue
    a = np.array([x[0] for x in L]); per[gname] = {Y: np.mean([x[0] for x in L if x[1] == Y]) for Y in EVM if any(x[1] == Y for x in L)}
    P(f'  {gname:9s} n {len(a):4d} · ROI {a.mean()*100:+.1f}% · {a.sum():+.1f}u · ' + ' '.join(f'{Y[-2:]}:{v*100:+.0f}' for Y, v in per[gname].items()))
both = [Y for Y in EVM if Y in per.get('ΣΥΜΦΩΝΕΙ', {}) and Y in per.get('ΔΙΑΦΩΝΕΙ', {})]
nb = sum(per['ΣΥΜΦΩΝΕΙ'][Y] > per['ΔΙΑΦΩΝΕΙ'][Y] for Y in both)
P(f'  → ΣΥΜΦΩΝΕΙ > ΔΙΑΦΩΝΕΙ σε {nb}/{len(both)} σεζον')
open('ec_totals_nested_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
