# -*- coding: utf-8 -*-
"""anchor_timing_grid.py — ΑΓΚΥΡΩΣΗ ΣΤΗΝ ΑΓΟΡΑ ΣΤΙΣ ΣΤΙΓΜΕΣ ΠΟΥ ΠΑΙΖΕΙ Ο ΣΤΕΛΙΟΣ (21/10/2026: «στο bcl παιζω καποιες ωρες πριν… στο eurocup 1 ωρα πριν»).
Χρηση: python anchor_timing_grid.py BCL | EC. Υποδομη = bcl_timing_test / ec_timing_factors_test (ολο το ιστορικο γραμμης Nowgoal, Crown & Bet365).
Σε καθε στιγμη (ανοιγμα · 12ω · 6ω · 3ω · 1ω · κλεισιμο): προβλεψη = αγορα ΕΚΕΙΝΗΣ της στιγμης + w·(μοντελο − αγορα),
w ∈ {1 (σημερινο live: σ live), .7, .5, .3, .2 (σ μιξης)} × κατωφλι {4, 6, 8, 10}% → ROI (picks, μοναδες, θετικες σεζον).
+ LOSO ανα στιγμη: (w, κατωφλι) με μοναδες στις αλλες σεζον → εφαρμογη στην αφαιρεμενη. Περιγραφικο / καθοδηγητικο (οχι προ-δηλωμενο κριτηριο).
Εξοδος: anchor_timing_grid_{BCL|EC}_out.txt"""
import sys, collections
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'BCL').upper()
if MODE == 'BCL':
    src = open('bcl_timing_test.py', encoding='utf-8').read().split("RULES = {")[0]
else:
    src = open('ec_timing_factors_test.py', encoding='utf-8').read().split("RULES = {")[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", "")
exec(src)
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
out2 = []
def P2(s=''): print(s, flush=True); out2.append(str(s))
if MODE == 'BCL':
    MOD = PRED['Α live φορμουλα']['FIN']; SEAS = YS; SIG_LIVE, SIG_MIX = 12.0, 12.1
    BOOKS = {'Crown': (HIST[3], ('open', 3, 1, 'close')), 'Bet365': (HIST[8], ('open', 12, 6, 3, 1, 'close'))}
    atb = lambda H, i, cp: at(H, i, cp)
else:
    MOD = MODEL; SEAS = seasn; SIG_LIVE, SIG_MIX = 11.5, 12.3
    BOOKS = {'Crown': (HIST, ('open', 12, 6, 3, 1, 'close'))}
    atb = lambda H, i, cp: at(i, cp)
WS = (1.0, .7, .5, .3, .2); THR = (.04, .06, .08, .10)
def run(H, cp, w, thr):
    R = []
    for i in H:
        if not np.isfinite(MOD[i]): continue
        x = atb(H, i, cp)
        if x is None: continue
        _, L, mk, o1, o2 = x; sg = SIG_LIVE if w == 1.0 else SIG_MIX; m_ = mk + w * (MOD[i] - mk)
        pw, pp, pl = cover(m_, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= thr: R.append((settle(i, s, L, od), str(SEAS[i])))
    return R
def cell(R):
    if not R: return '—'
    a = np.array([q[0] for q in R]); ps = collections.defaultdict(float)
    for q in R: ps[q[1]] += q[0]
    return f'{100 * a.mean():+5.1f}% ({len(a):4d}, {a.sum():+6.1f}μ, {sum(v > 0 for v in ps.values())}/{len(ps)})'
P2(f'{MODE} · ΑΓΚΥΡΩΣΗ ΑΝΑ ΣΤΙΓΜΗ · w = ποσοστο της διαφωνιας μας (1 = σημερινο live) · κελι: ROI (picks, μοναδες, θετικες σεζον)')
for bk, (H, CPS) in BOOKS.items():
    for cp in CPS:
        lab = cp if isinstance(cp, str) else f'{cp}ω πριν'
        P2(''); P2(f'=== {bk} · {lab} ===')
        G = {(w, th): run(H, cp, w, th) for w in WS for th in THR}
        for w in WS: P2(f'  w {w:<4} ' + ' | '.join(f'{int(th * 100)}%: {cell(G[(w, th)])}' for th in THR))
        seas = sorted({q[1] for R in G.values() for q in R}); held = []; ch = []
        for s in seas:
            best = max(G, key=lambda k: sum(q[0] for q in G[k] if q[1] != s)); ch.append(best); held += [q for q in G[best] if q[1] == s]
        P2(f'  LOSO (μοναδες): {cell(held)} · επιλογες {collections.Counter(ch).most_common(3)} · σημερινο live (w 1, 8%): {cell(G[(1.0, .08)])}')
open(f'anchor_timing_grid_{MODE}_out.txt', 'w', encoding='utf-8').write('\n'.join(out2))
