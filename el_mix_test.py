# -*- coding: utf-8 -*-
"""el_mix_test.py — ΕΥΡΩΛΙΓΚΑ: ΜΙΞΗ μοντελου με την αγορα; (5/10/2026, Στελιος: «η μιξη την εχουμε τεσταρει στην ευρωλιγκα;» — ΟΧΙ ως τωρα).
Ιδιο τεστ με το EuroCup (ec_sigma_edge_test γ): μ = αγορα + w·(μοντελο − αγορα), πιθανοτητα καλυψης με σ.
Μοντελο = live (el_newmodel_preds: χαντικαπ h_new, συνολο t_new) · Crown (Nowgoal) E2021-E2025 κανονικη περιοδος, ΑΝΟΙΓΜΑ & ΚΛΕΙΣΙΜΟ.
Σημερα live: w 1 (μοντελο μονο του), σ 11.5 χαντικαπ / 16.7 συνολα, edge ≥8%.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα αγορα: log-loss καλυψης στη γραμμη ΑΝΟΙΓΜΑΤΟΣ (push εξω), πλεγμα w {.2,.3,.4,.5,.6,.8,1} ×
  σ (χαντικαπ {10.5,11.5,12.3,13.5,14.5} · συνολα {15,16.7,18,19.5}) · LOSO 5 σεζον → ΑΛΛΑΓΗ αν καλυτερο απο το σημερινο σε ≥4/5.
  Αναφορα: ROI picks ανοιγματος σημερινος κανονας (≥8%) vs μιξη στα κατωφλια {4,6,8}%.
Εξοδος: el_mix_test_out.txt"""
import sys, math
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, D, SE5, ACT, TOT = (NS[k] for k in ('REC', 'PR', 'key', 'D', 'SE5', 'ACT', 'TOT'))
Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def probs(t, m, L, s):
    thr = -L if t == 21 else L          # νικα η «πρωτη» πλευρα (γηπ / over) αν αποτελεσμα > thr
    if abs(L - round(L)) < 1e-9: p1 = 1 - Phi((thr + .5 - m) / s); p2 = Phi((thr - .5 - m) / s)
    else: p1 = 1 - Phi((thr - m) / s); p2 = 1 - p1
    return p1, 1 - p1 - p2, p2
def outcome(t, p, L):
    v = (ACT[p] + L) if t == 21 else (TOT[p] - L); return np.sign(v)
CUR = {21: (1.0, 11.5), 23: (1.0, 16.7)}
SIG = {21: (10.5, 11.5, 12.3, 13.5, 14.5), 23: (15.0, 16.7, 18.0, 19.5)}
WS = (.2, .3, .4, .5, .6, .8, 1.0)
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
    items = []
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(('h_' if t == 21 else 't_') + 'new')
        if m is None or not np.isfinite(m) or D.season.values[p] not in SE5: continue
        items.append((p, m, r['open'], r[0], D.season.values[p]))
    P(''); P(f'################ {nm} · {len(items)} ματς ################')
    LL = {}
    for w in WS:
        for s in SIG[t]:
            arr = []
            for p, m, ro, rc, Y in items:
                _, mk, L, o1, o2 = ro; v = outcome(t, p, L)
                if v == 0: continue
                p1, pp, p2 = probs(t, mk + w * (m - mk), L, s); q = p1 / (p1 + p2) if v > 0 else p2 / (p1 + p2)
                arr.append((-math.log(max(q, 1e-9)), Y))
            LL[(w, s)] = arr
    mean = lambda k, ys: float(np.mean([q[0] for q in LL[k] if q[1] in ys]))
    cur = CUR[t]
    P(f'  log-loss ανοιγματος: σημερα (w 1, σ {cur[1]}) {mean(cur, SE5):.4f} · μαντεψια .6931 · αγορα μονη (w .2 καλυτερο σ) {min(mean((.2, s), SE5) for s in SIG[t]):.4f}')
    P('  ανα w (καλυτερο σ): ' + ' · '.join(f'{w}: {min(mean((w, s), SE5) for s in SIG[t]):.4f}/σ{min(SIG[t], key=lambda s: mean((w, s), SE5))}' for w in WS))
    ch, d = [], []
    for Y in SE5:
        tr = [x for x in SE5 if x != Y]; k = min(LL, key=lambda k: mean(k, tr)); ch.append(k); d.append(mean(k, [Y]) - mean(cur, [Y]))
    P(f'  LOSO επιλογες {ch} · ' + ' '.join(f'{Y[-2:]}:{x:+.4f}' for Y, x in zip(SE5, d)) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
    from collections import Counter
    wb, sb = Counter(ch).most_common(1)[0][0]
    for when, idx in (('ανοιγμα', 2), ('κλεισιμο', 3)):
        cells = []
        for lab, (w, s), thr in (('σημερα ≥8%', cur, .08), (f'μιξη w{wb}/σ{sb} ≥4%', (wb, sb), .04), (f'μιξη ≥6%', (wb, sb), .06), (f'μιξη ≥8%', (wb, sb), .08)):
            R = []
            for it in items:
                p, m, Y = it[0], it[1], it[4]; _, mk, L, o1, o2 = it[idx]
                p1, pp, p2 = probs(t, mk + w * (m - mk), L, s); e1, e2 = p1 * o1 + pp - 1, p2 * o2 + pp - 1
                side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e >= thr:
                    v = outcome(t, p, L) * side; R.append(((od - 1) if v > 0 else (0 if v == 0 else -1), Y))
            a = np.array([q[0] for q in R]); pos = sum(1 for Y in SE5 if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
            cells.append(f'{lab} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/5)')
        P(f'  ROI {when}: ' + ' · '.join(cells))
open('el_mix_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
