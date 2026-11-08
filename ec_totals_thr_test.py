# -*- coding: utf-8 -*-
"""ec_totals_thr_test.py — EuroCup ΣΥΝΟΛΑ αγων 7+, μοντελο ΜΟΝΟ ΤΟΥ (w 1, σ 16.7): ΚΑΤΩΦΛΙ 6% ή 8%; (5/10/2026, Στελιος «δοκιμασε αλλο τεστ»).
Μοντελο = live (ec_totals_deep_test ΤΕΛΙΚΟ) · Crown ανοιγμα U2020-25 · μονο αγων 7+.
ΤΕΣΤ (ΠΡΟ-ΔΗΛΩΜΕΝΑ, ΠΡΙΝ την εκτελεση):
  Τ1 LOSO κατωφλιου: για καθε σεζον, κατωφλι ∈ {4,5,6,7,8,9,10,12}% με τις περισσοτερες ΜΟΝΑΔΕΣ στις αλλες 5 → αποτελεσμα στην 6η.
     Αποφαση: αν η LOSO επιλογη ειναι ≤6% σε ≥4/6 σεζον → 6%· αν ≥8% σε ≥4/6 → 8%· αλλιως Τ2/Τ3.
  Τ2 ΖΩΝΗ 6-8% (τα picks που προσθετει το 6%): ROI, μοναδες, θετικες σεζον, κινηση γραμμης ανοιγμα→κλεισιμο προς εμας (CLV, ποντοι),
     bootstrap 5000 (ανα ματς): πιθανοτητα οι μοναδες της ζωνης να ειναι > 0. Αποδεκτη αν P ≥ 0.8 ΚΑΙ CLV > 0.
  Τ3 ΒΑΘΜΟΝΟΜΗΣΗ: ανα ζωνη edge (4-6, 6-8, 8-10, 10-12, 12-15, 15+): δηλωμενο edge vs πραγματικο ROI· κλιση ROI/edge
     (1 = το edge «βγαινει» ολοκληρο)· log-loss καλυψης για σ {14, 15, 16.7, 18, 20, 23} (αν σ > 16.7 καλυτερο → το μοντελο «φουσκωνει»).
Εξοδος: ec_totals_thr_out.txt · ec_totals_fin.pkl (για επομενα τεστ χωρις 10′ ξανατρεξιμο)"""
import sys, math, pickle, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 't'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
FIN, TOT, GN, seasn, MKT, cov, EVM = (NS[k] for k in ('FIN', 'TOT', 'GN', 'seasn', 'MKT', 'cov', 'EVM'))
pickle.dump(dict(FIN=FIN, TOT=TOT, GN=GN, seasn=np.asarray(seasn), MKT=MKT, EVM=EVM), open('ec_totals_fin.pkl', 'wb'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
ii = [i for i in MKT if seasn[i] in EVM and np.isfinite(FIN[i]) and GN[i] >= 6]
REC = []   # (season, edge, unit result, CLV ποντοι, over?)
for i in ii:
    T, mk, oo, ou = MKT[i]['o']; Tc, mkc, _, _ = MKT[i]['c']
    po, pq, pu = cov(FIN[i], T, 16.7); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
    ov = eo >= eu; e = max(eo, eu); q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
    REC.append((seasn[i], e, (od - 1) if q > 0 else (0 if q == 0 else -1), (mkc - mk) * (1 if ov else -1), ov))
S = np.array([r[0] for r in REC]); E = np.array([r[1] for r in REC]); U = np.array([r[2] for r in REC]); CLV = np.array([r[3] for r in REC])
P(f'αγων 7+: {len(REC)} ματς με αγορα')
TH = (.04, .05, .06, .07, .08, .09, .10, .12)
units = lambda thr, ys: float(U[(E >= thr) & np.isin(S, ys)].sum())
P(''); P('=== Τ1 LOSO ΚΑΤΩΦΛΙΟΥ (μοναδες) ===')
P('  μοναδες ανα σεζον: ' + ' | '.join(f'≥{t:.0%}: ' + ' '.join(f'{Y[-2:]}:{units(t, [Y]):+.1f}' for Y in EVM) + f' = {units(t, EVM):+.1f}' for t in TH))
ch, got, got6, got8 = [], 0, 0, 0
for Y in EVM:
    tr = [x for x in EVM if x != Y]; t = max(TH, key=lambda t: units(t, tr)); ch.append(t); got += units(t, [Y])
    got6 += units(.06, [Y]); got8 += units(.08, [Y])
P(f'  LOSO επιλογες {[f"{t:.0%}" for t in ch]} · μοναδες στις σεζον-ελεγχου {got:+.1f} (σταθερο 6%: {got6:+.1f} · σταθερο 8%: {got8:+.1f})')
n6 = sum(t <= .06 for t in ch); n8 = sum(t >= .08 for t in ch)
P(f'  → ΠΡΟ-ΔΗΛΩΜΕΝΟ: ≤6% σε {n6}/6 · ≥8% σε {n8}/6 → ' + ('6%' if n6 >= 4 else ('8%' if n8 >= 4 else 'αναποφασιστο (Τ2/Τ3)')))
P(f'  σεζον οπου το 6% εβγαλε περισσοτερες μοναδες απο το 8%: {sum(units(.06, [Y]) > units(.08, [Y]) for Y in EVM)}/6')
P(''); P('=== Τ2 ΖΩΝΗ 6-8% (τα picks που προσθετει το 6%) ===')
z = (E >= .06) & (E < .08)
rng = np.random.default_rng(7); idx = np.where(z)[0]
bs = np.array([U[rng.choice(idx, len(idx))].sum() for _ in range(5000)])
pos = sum(1 for Y in EVM if (z & (S == Y)).any() and U[z & (S == Y)].sum() > 0)
P(f'  n {z.sum()} · ROI {U[z].mean()*100:+.1f}% · μοναδες {U[z].sum():+.1f} · θετικες σεζον {pos}/{len(set(S[z]))} · over {int(np.sum([r[4] for r, k in zip(REC, z) if k]))}/{z.sum()}')
P(f'  CLV: γραμμη κινηθηκε προς εμας {CLV[z].mean():+.2f} π. (υπερ {np.mean(CLV[z] > .05):.0%} / κατα {np.mean(CLV[z] < -.05):.0%}) · για συγκριση ≥8%: {CLV[E >= .08].mean():+.2f} π. · <6%: {CLV[E < .06].mean():+.2f}')
P(f'  bootstrap: P(μοναδες ζωνης > 0) = {np.mean(bs > 0):.2f} · 90% ευρος [{np.percentile(bs, 5):+.1f}, {np.percentile(bs, 95):+.1f}]')
ok2 = np.mean(bs > 0) >= .8 and CLV[z].mean() > 0
P(f'  → ΠΡΟ-ΔΗΛΩΜΕΝΟ: η ζωνη 6-8% {"ΑΞΙΖΕΙ" if ok2 else "ΔΕΝ αποδεικνυεται"}')
P(''); P('=== Τ3 ΒΑΘΜΟΝΟΜΗΣΗ (μοντελο μονο του, σ 16.7) ===')
xs, ys = [], []
for lo, hi in ((.0, .04), (.04, .06), (.06, .08), (.08, .10), (.10, .12), (.12, .15), (.15, 1)):
    b = (E >= lo) & (E < hi)
    if b.sum() < 10: continue
    pos = sum(1 for Y in EVM if (b & (S == Y)).any() and U[b & (S == Y)].sum() > 0)
    P(f'  edge {lo:.0%}-{hi:.0%}: n {b.sum():4d} · δηλωμενο {E[b].mean()*100:+.1f}% · πραγματικο ROI {U[b].mean()*100:+.1f}% · CLV {CLV[b].mean():+.2f} π. · θετ. {pos}/{len(set(S[b]))}')
    xs.append(E[b].mean()); ys.append(U[b].mean())
sel = E >= .0
P(f'  κλιση ROI πανω στο edge (ανα ματς): {np.polyfit(E[sel], U[sel], 1)[0]:+.2f} (1 = το edge βγαινει ολοκληρο)')
LL = {}
for s in (14.0, 15.0, 16.7, 18.0, 20.0, 23.0):
    arr = []
    for i in ii:
        T, mk, oo, ou = MKT[i]['o']; v = TOT[i] - T
        if v == 0: continue
        po, pq, pu = cov(FIN[i], T, s); q = po / (po + pu) if v > 0 else pu / (po + pu); arr.append(-math.log(max(q, 1e-9)))
    LL[s] = np.mean(arr)
P('  log-loss καλυψης ανα σ: ' + ' · '.join(f'σ {s}: {v:.4f}' for s, v in LL.items()) + f' · καλυτερο σ {min(LL, key=LL.get)}')
open('ec_totals_thr_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
