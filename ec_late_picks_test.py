# -*- coding: utf-8 -*-
"""ec_late_picks_test.py — EuroCup: picks που «γεννιουνται» κοντα στο κλεισιμο (6/10/2026, Στελιος «σημεια που εφαγαν κοντρα και ανεβηκαν, και τα επιασε το μοντελο»).
Ιδιο τεστ με NBA (nba_more_tests Τ8 β/γ). Crown (Nowgoal) ανοιγμα & κλεισιμο, U2020-25, καθαρες προβλεψεις:
  χαντικαπ = ec_fresh_market.pkl 'held' (LOSO) · κανονας live: μοντελο μονο του, σ 11.5, edge ≥8%
  συνολα  = ec_totals_fin.pkl FIN (live μηχανη) · κανονας live: αγων 1-6 μιξη 50/50, 7+ μοντελο μονο του, edge ≥6%, σ 16.7
ΚΑΤΗΓΟΡΙΕΣ: (Α) pick στο ανοιγμα → ROI στην τιμη ανοιγματος, χωρισμενο κατα την κινηση της γραμμης ως το κλεισιμο (υπερ / ουδετερη / κοντρα ≥1.5 π.)
  (Β) «ΑΡΓΟ» pick: υπαρχει στο κλεισιμο, ΔΕΝ υπηρχε στο ανοιγμα (ιδια πλευρα) → ROI στην τιμη κλεισιματος· (Γ) pick ΚΑΙ στα δυο (ιδια πλευρα) → ROI στο κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: κανονας «ΟΧΙ αργα picks» ΠΕΡΝΑ αν τα αργα picks ειναι αρνητικα σε ≥5/6 σεζον (ή ≥4/6 με συνολο < −5%).
Εξοδος: ec_late_picks_out.txt"""
import sys, math, pickle, collections
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
D = pickle.load(open('ec_fresh_market.pkl', 'rb')); T = pickle.load(open('ec_totals_fin.pkl', 'rb'))
S = np.asarray(D['seasn']); GN = np.asarray(D['GN']); ACT = D['act']; HM = D['held']
FIN, TOT = T['FIN'], T['TOT']
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def pick_h(i, wh):
    L, mk, o1, o2 = D['MK'][i][wh]; pw, pp, pl = cover(HM[i], L, 11.5)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    x = (ACT[i] + L) * s_; return s_, (od - 1) if x > 0 else (0 if x == 0 else -1), L
def pick_t(i, wh):
    Tl, mk, oo, ou = T['MKT'][i][wh]; w, thr = (.5, .06) if GN[i] <= 5 else (1.0, .06)
    mu = mk + w * (FIN[i] - mk); po, pq, pu = cover(mu, -Tl, 16.7)
    eo, eu = po * oo + pq - 1, pu * ou + pq - 1; s_, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
    if e < thr: return None
    x = (TOT[i] - Tl) * s_; return s_, (od - 1) if x > 0 else (0 if x == 0 else -1), Tl
def cell(R):
    if not R: return '—'
    u = [x for v in R.values() for x in v]; pos = sum(1 for Y in EVM if R.get(Y) and np.mean(R[Y]) > 0); ny = sum(1 for Y in EVM if R.get(Y))
    return f'{np.mean(u) * 100:+.1f}% ({len(u)}, {sum(u):+.1f}u, θετ {pos}/{ny})'
for kind, MK, pk, ok_ in (('ΧΑΝΤΙΚΑΠ', D['MK'], pick_h, lambda i: np.isfinite(HM[i])), ('ΣΥΝΟΛΑ', T['MKT'], pick_t, lambda i: np.isfinite(FIN[i]))):
    A = collections.defaultdict(lambda: collections.defaultdict(list)); LATE = collections.defaultdict(list); BOTH = collections.defaultdict(list); LATE_mv = []
    for i in MK:
        if S[i] not in EVM or not ok_(i): continue
        po, pc = pk(i, 'o'), pk(i, 'c')
        Lo, Lc = MK[i]['o'][0], MK[i]['c'][0]
        if po:
            # κινηση κοντρα μας: χαντικαπ (γραμμη γηπ. L): pick γηπ. (s=1) → L↑ = κοντρα · συνολα: over (s=1) → T↓ = κοντρα
            ag = (Lc - Lo) * po[0] if kind == 'ΧΑΝΤΙΚΑΠ' else (Lo - Lc) * po[0]
            cat = 'γραμμη ΚΟΝΤΡΑ μας ≥1.5' if ag >= 1.5 else ('γραμμη ΥΠΕΡ μας ≥1.5' if ag <= -1.5 else 'μικρη κινηση (<1.5)')
            A[cat][S[i]].append(po[1]); A['ΟΛΑ'][S[i]].append(po[1])
        if pc and not (po and po[0] == pc[0]):
            LATE[S[i]].append(pc[1]); LATE_mv.append(((Lc - Lo) * pc[0]) if kind == 'ΧΑΝΤΙΚΑΠ' else ((Lo - Lc) * pc[0]))
        if pc and po and po[0] == pc[0]: BOTH[S[i]].append(pc[1])
    P(''); P(f'################ {kind} ################')
    P(f'  (Α) picks ΑΝΟΙΓΜΑΤΟΣ (τιμη ανοιγματος):')
    for cat in ('ΟΛΑ', 'γραμμη ΥΠΕΡ μας ≥1.5', 'μικρη κινηση (<1.5)', 'γραμμη ΚΟΝΤΡΑ μας ≥1.5'):
        P(f'     {cat:26s} {cell(A[cat])}')
    P(f'  (Β) «ΑΡΓΑ» picks (στο κλεισιμο, ΟΧΙ στο ανοιγμα — τιμη κλεισιματος): {cell(LATE)} · μεση κινηση γραμμης κοντρα στην πλευρα τους {np.mean(LATE_mv) if LATE_mv else 0:+.2f} π.')
    P('        ανα σεζον: ' + ' · '.join(f'{Y} {sum(LATE[Y]):+.1f}u/{len(LATE[Y])}' for Y in EVM))
    neg = sum(1 for Y in EVM if LATE[Y] and sum(LATE[Y]) < 0); u = [x for v in LATE.values() for x in v]
    okR = neg >= 5 or (neg >= 4 and u and np.mean(u) < -.05)
    P(f'      κανονας «ΟΧΙ αργα picks»: αρνητικα σε {neg}/6 σεζον' + (' → ΠΕΡΝΑ' if okR else ' → ✗'))
    P(f'  (Γ) picks ΚΑΙ στο ανοιγμα ΚΑΙ στο κλεισιμο (τιμη κλεισιματος): {cell(BOTH)}')
open('ec_late_picks_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
