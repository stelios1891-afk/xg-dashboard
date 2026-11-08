# -*- coding: utf-8 -*-
"""ec_totals_bias_test.py — EuroCup ΣΥΝΟΛΑ: ΕΧΕΙ ΤΟ ΜΟΝΤΕΛΟ ΑΞΙΑ ΠΕΡΑ ΑΠΟ ΤΟ «ΑΝΟΙΓΜΑ ΧΑΜΗΛΑ» ΤΗΣ ΑΓΟΡΑΣ; (5/10/2026, Στελιος).
Μοντελο = το LIVE (ec_totals_deep_test ΤΕΛΙΚΟ: Β* + φιλικα κT .25). Αγορα = Crown ανοιγμα/κλεισιμο U2020-25.
1. ΔΙΟΡΘΩΜΕΝΗ ΑΓΟΡΑ: μεροληψια αγορας (πραγματικο − αγορα ανοιγματος) ανα φαση (αγων 1-3 / 4-6 / 7-10 / 11+), μετρημενη στις ΑΛΛΕΣ 5 σεζον (LOSO),
   προστιθεται στην αγορα → «αγορα + γνωστη ταση».
   ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): το μοντελο εχει αξια ΠΕΡΑ απο την ταση αν Κ2 vs ΔΙΟΡΘΩΜΕΝΟ ανοιγμα b ≥ .15 ΚΑΙ t ≥ 2 ΚΑΙ θετικο ≥4/6,
   ξεχωριστα για αγων 1-6 και 7+.
   ROI (αναφορα): (α) ΜΟΝΟ η ταση: picks οπου η διορθωμενη αγορα δινει edge ≥ κατωφλι («τυφλα over με φιλτρο»)
                  (β) μοντελο μιξη 50/50 με την ΩΜΗ αγορα (σημερα live) · (γ) μοντελο μιξη 50/50 με τη ΔΙΟΡΘΩΜΕΝΗ αγορα.
2. ΑΓΩΝ 7+ ΧΩΡΙΣ ΜΙΞΗ: μοντελο μονο του (w 1) και w .75 / .5, σ 16.7, κατωφλια 4/6/8/10/12% — ROI over/under ανα σεζον (αναφορα).
Εξοδος: ec_totals_bias_out.txt"""
import sys, math, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'b'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
FIN, TOT, GN, seasn, MKT, cov, EVM, k2 = (NS[k] for k in ('FIN', 'TOT', 'GN', 'seasn', 'MKT', 'cov', 'EVM', 'k2'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
ii = np.array([i for i in MKT if seasn[i] in EVM and np.isfinite(FIN[i])])
PH = lambda g: 0 if g <= 2 else (1 if g <= 5 else (2 if g <= 9 else 3))
PHL = ['αγων 1-3', 'αγων 4-6', 'αγων 7-10', 'αγων 11+']
ph = np.array([PH(GN[i]) for i in ii]); ss = seasn[ii]
mo = np.array([MKT[i]['o'][1] for i in ii]); mc = np.array([MKT[i]['c'][1] for i in ii]); a = TOT[ii]; m = FIN[ii]
# ---- LOSO μεροληψια ανα φαση ----
bias = np.zeros(len(ii)); bias_c = np.zeros(len(ii))
for Y in EVM:
    te = ss == Y
    for k in range(4):
        tr = (ss != Y) & (ph == k)
        bias[te & (ph == k)] = np.mean((a - mo)[tr]); bias_c[te & (ph == k)] = np.mean((a - mc)[tr])
P('μεροληψια αγορας ανοιγματος ανα φαση (ολες οι σεζον): ' + ' · '.join(f'{PHL[k]} {np.mean((a - mo)[ph == k]):+.2f}' for k in range(4))
  + ' · κλεισιμο: ' + ' · '.join(f'{PHL[k]} {np.mean((a - mc)[ph == k]):+.2f}' for k in range(4)))
mo_adj = mo + bias; mc_adj = mc + bias_c
P(''); P('################ 1. ΑΞΙΑ ΠΕΡΑ ΑΠΟ ΤΗΝ ΤΑΣΗ (Κ2) ################')
for lab, sel in (('αγων 1-6', ph <= 1), ('αγων 7+', ph >= 2), ('ολη η σεζον', ph >= 0)):
    rows = []
    for nm, base in (('ΩΜΟ ανοιγμα', mo), ('ΔΙΟΡΘΩΜΕΝΟ ανοιγμα', mo_adj), ('ΩΜΟ κλεισιμο', mc), ('ΔΙΟΡΘΩΜΕΝΟ κλεισιμο', mc_adj)):
        x, z = (m - base)[sel], (a - base)[sel]; b, t = k2(x, z)
        per = [np.polyfit(x[ss[sel] == Y], z[ss[sel] == Y], 1)[0] for Y in EVM if (ss[sel] == Y).sum() > 20]
        ok = b >= .15 and t >= 2 and sum(p > 0 for p in per) >= 4
        rows.append(f'{nm} b {b:+.2f} (t {t:+.1f}, θετ. {sum(p > 0 for p in per)}/{len(per)})' + (' ✓' if ok else ' ✗'))
        if nm == 'ΔΙΟΡΘΩΜΕΝΟ ανοιγμα': verdict = ok
    rm = lambda v: float(np.sqrt(np.mean((a[sel] - v[sel]) ** 2)))
    P(f'  [{lab}] n {sel.sum()} · λαθος: μοντελο {rm(m):.2f} · ανοιγμα {rm(mo):.2f} · διορθ. ανοιγμα {rm(mo_adj):.2f} · κλεισιμο {rm(mc):.2f} · διορθ. κλεισιμο {rm(mc_adj):.2f}')
    P('     ' + ' · '.join(rows))
    P(f'     → ΠΡΟ-ΔΗΛΩΜΕΝΟ: το μοντελο {"ΕΧΕΙ" if verdict else "ΔΕΝ ΕΧΕΙ (αποδεδειγμενη)"} αξια περα απο την ταση της αγορας')
def picks(mu_fn, thr, sel_fn, st=16.7):
    R = []
    for k, i in enumerate(ii):
        if not sel_fn(ph[k]): continue
        T, mk, oo, ou = MKT[i]['o']; mu = mu_fn(k, mk)
        po, pq, pu = cov(mu, T, st); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
        if max(eo, eu) >= thr:
            ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
            R.append(((od - 1) if q > 0 else (0 if q == 0 else -1), ss[k], ov))
    return R
def fmt(R):
    if not R: return '—'
    A = np.array([x[0] for x in R]); pos = sum(1 for Y in EVM if [x for x in R if x[1] == Y] and np.mean([x[0] for x in R if x[1] == Y]) > 0)
    no = sum(1 for x in R if x[2]); return f'{A.mean()*100:+.1f}% ({len(R)}: over {no}/under {len(R) - no}, {A.sum():+.1f}u, {pos}/{len({x[1] for x in R})})'
P(''); P('################ ROI ανοιγμα (Crown) ################')
for lab, sf in (('αγων 1-6', lambda p: p <= 1), ('αγων 7+', lambda p: p >= 2), ('ολη', lambda p: True)):
    P(f'  [{lab}]')
    P(f'     τυφλο over (ολα τα ματς)                    {fmt(picks(lambda k, mk: mk + 99, 0.0, sf))}')
    for thr in (.03, .06):
        P(f'     ≥{thr:.0%} (α) ΜΟΝΟ ταση (διορθ. αγορα)          {fmt(picks(lambda k, mk: mk + bias[k], thr, sf))}')
        P(f'     ≥{thr:.0%} (β) μοντελο μιξη με ΩΜΗ αγορα (live)  {fmt(picks(lambda k, mk: mk + .5 * (m[k] - mk), thr, sf))}')
        P(f'     ≥{thr:.0%} (γ) μοντελο μιξη με ΔΙΟΡΘ. αγορα      {fmt(picks(lambda k, mk: (mk + bias[k]) + .5 * (m[k] - mk - bias[k]), thr, sf))}')
# ---- 2. αγων 7+ χωρις μιξη ----
P(''); P('################ 2. ΑΓΩΝ 7+ — ΜΟΝΤΕΛΟ ΧΩΡΙΣ ΜΙΞΗ (w 1) vs w .75 / .5 ################')
for w in (1.0, .75, .5):
    for thr in (.04, .06, .08, .10, .12):
        R = picks(lambda k, mk, w=w: mk + w * (m[k] - mk), thr, lambda p: p >= 2)
        ov = [x for x in R if x[2]]; un = [x for x in R if not x[2]]
        per = {Y: np.mean([x[0] for x in R if x[1] == Y]) * 100 for Y in EVM if any(x[1] == Y for x in R)}
        P(f'  w {w:.2f} ≥{thr:.0%}: ΟΛΑ {fmt(R)} · over {fmt(ov)} · under {fmt(un)} · ανα σεζον ' + ' '.join(f'{Y[-2:]}:{v:+.0f}' for Y, v in per.items()))
open('ec_totals_bias_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
