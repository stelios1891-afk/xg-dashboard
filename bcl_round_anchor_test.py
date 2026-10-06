# -*- coding: utf-8 -*-
"""bcl_round_anchor_test.py — BCL γυρος 3 (6/10/2026, Στελιος «εγχωρια βοηθανε; μεχρι ποια αγωνιστικη; αγκυρες;»).
Α. ΕΓΧΩΡΙΑ ΑΝΑ ΑΓΩΝΙΣΤΙΚΗ: Μ1 (μονο BCL) vs Μ2 (κοινη κλιμακα = εγχωρια + Ευρωπη + BCL), live ρυθμισεις, ανα αριθμο ματς BCL της ομαδας γηπ.
   {1-3, 4-6, 7-10, 11+}: λαθος καθε μιας + βαρος μιξης a επιλεγμενο LOSO ανα ζωνη (a {0,.25,.5,.75,.9,1}).
Β. ΒΑΡΟΣ ΕΓΧΩΡΙΩΝ/ΕΥΡΩΠΗΣ στην κοινη κλιμακα: wo {.5, .75, 1, 1.5, 2} (1 = ιδιο με BCL), live ρυθμιση Μ2.
Γ. ΑΓΚΥΡΑ (μιξη με την αγορα): προβλεψη = αγορα + w·(μοντελο − αγορα), w {1, .75, .5, .25} × οριο {4, 6, 8, 12, 16%} × «μονο τα πρωτα Ν ματς» Ν {3, 6, ολα}.
   Κανονας επιλεγεται LOSO (μοναδες στις αλλες 4 σεζον, Crown ανοιγμα) → αποτελεσμα στη σεζον που λειπει.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
   Α: η μιξη ανα ζωνη μπαινει αν LOSO καλυτερη απο την ενιαια a σε ≥4/5 σεζον.
   Β: wo ≠ 1 μπαινει αν καλυτερο σε ≥4/5 σεζον (ιδια ρυθμιση αλλιως).
   Γ: ο LOSO κανονας μπαινει αν (i) μοναδες > σημερινου κανονα (μοντελο ≥8%, ολα) ΚΑΙ καλυτερος σε ≥4/5 σεζον ΚΑΙ (ii) Bet365 ανοιγμα με τους ιδιους κανονες επισης > σημερινου.
Εξοδος: bcl_round_anchor_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, json, math, pickle, itertools, collections
import numpy as np
from statistics import NormalDist
from multiprocessing import Pool
M1_LIVE = (1.4, 8, 9999, .5)
M2_LIVE = (1.3, 1.5, 9999.0, 25.0, 0.5)
A_LIVE = .75

def _m2(wo):
    import bcl_common as B
    rows = B.load(pre=True); return wo, B.run(rows, *M2_LIVE[:4], kf=M2_LIVE[4], wo=wo)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    D = pickle.load(open('bcl_engine_preds2f.pkl', 'rb'))
    ids, ys, act, T, HID = D['id'], D['y'], D['act'], D['t'], D['hid']
    EV = [2021, 2022, 2023, 2024, 2025]
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    # Μ1 live
    src = open('dom_bk_engine_test.py', encoding='utf-8').read().split("LIVE = (.7, 8, 9999, .5, False)")[0]
    src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1).replace("ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']", "ARGS = ['BCL']")
    NS = {'__name__': 'b'}
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()): exec(src, NS)
    G = NS['G']; full = NS['run']('BCL', *M1_LIVE, False)[0]
    gp = {i: k for k, i in enumerate(G.id.values)}
    M1 = np.array([full[gp[i]] for i in ids])
    C2 = pickle.load(open('bcl_m2_cache2.pkl', 'rb')); M2 = arr(C2[M2_LIVE])
    gno = np.zeros(len(ids), int); cnt = collections.Counter()
    for i in np.argsort(T): cnt[(ys[i], HID[i])] += 1; gno[i] = cnt[(ys[i], HID[i])]
    ZN = [('1-3', 1, 3), ('4-6', 4, 6), ('7-10', 7, 10), ('11+', 11, 99)]
    zone = np.array([next(k for k, (l, a, b) in enumerate(ZN) if a <= g <= b) for g in gno])
    def rm(v, m): m = m & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
    AS = (0, .25, .5, .75, .9, 1.0)
    P('################ Α. ΕΓΧΩΡΙΑ (κοινη κλιμακα) ΑΝΑ ΑΓΩΝΙΣΤΙΚΗ ################')
    P('  λαθος (ποντοι): ζωνη · n · μονο BCL (Μ1) · κοινη κλιμακα (Μ2) · μιξη live a .75 · καλυτερο a (ολες οι σεζον)')
    for k, (lab, a, b) in enumerate(ZN):
        m = zone == k
        best = min(AS, key=lambda x: rm((1 - x) * M1 + x * M2, m))
        P(f'  {lab:5s} n {m.sum():4d} · Μ1 {rm(M1, m):.2f} · Μ2 {rm(M2, m):.2f} · μιξη {rm((1 - A_LIVE) * M1 + A_LIVE * M2, m):.2f} · καλυτερο a {best} ({rm((1 - best) * M1 + best * M2, m):.2f})')
        P('        ανα σεζον Μ2 − Μ1: ' + ' '.join(f'{Y}: {rm(M2, m & (ys == Y)) - rm(M1, m & (ys == Y)):+.2f}' for Y in EV))
    # LOSO: ενιαιο a vs a ανα ζωνη
    h1, hz = np.full(len(ids), np.nan), np.full(len(ids), np.nan)
    for Y in EV:
        tr = np.isin(ys, [x for x in EV if x != Y]); te = ys == Y
        a1 = min(AS, key=lambda x: rm((1 - x) * M1 + x * M2, tr)); h1[te] = ((1 - a1) * M1 + a1 * M2)[te]
        for k in range(len(ZN)):
            ak = min(AS, key=lambda x: rm((1 - x) * M1 + x * M2, tr & (zone == k))); mm = te & (zone == k); hz[mm] = ((1 - ak) * M1 + ak * M2)[mm]
    d = [rm(hz, ys == Y) - rm(h1, ys == Y) for Y in EV]
    P(f'  LOSO a ανα ζωνη vs ενιαιο: ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΕΙ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
    P(''); P('################ Β. ΒΑΡΟΣ ΕΓΧΩΡΙΩΝ/ΕΥΡΩΠΗΣ (wo) ################')
    WO = (.5, .75, 1.5, 2.0)
    with Pool(len(WO)) as pool: R = dict(pool.map(_m2, WO))
    R[1.0] = C2[M2_LIVE]
    base = (1 - A_LIVE) * M1 + A_LIVE * M2
    for wo in sorted(R):
        v = (1 - A_LIVE) * M1 + A_LIVE * arr(R[wo])
        dd = [rm(v, ys == Y) - rm(base, ys == Y) for Y in EV]
        P(f'  wo {wo:4}: ολα {rm(v, np.isin(ys, EV)):.3f} · ' + ' · '.join(f'{lab} {rm(v, zone == k):.2f}' for k, (lab, a, b) in enumerate(ZN)) + ' · vs wo 1: ' + ' '.join(f'{x:+.3f}' for x in dd) + f' ({sum(x < 0 for x in dd)}/5)')
    P(''); P('################ Γ. ΑΓΚΥΡΑ / ΜΙΞΗ ΜΕ ΑΓΟΡΑ (LOSO) ################')
    nd = NormalDist(); Phi = nd.cdf
    MKp = pickle.load(open('bcl_mk.pkl', 'rb'))
    FIN = D['FIN']
    ii = [k for k, i in enumerate(ids) if i in MKp and 3 in MKp[i] and np.isfinite(FIN[k]) and ys[k] in EV]
    SIG = float(np.std([act[k] - MKp[ids[k]][3]['c'][1] for k in ii]))
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def units(rule, book, wh='o'):
        w, thr, gmax = rule; U = collections.defaultdict(list)
        for k in ii:
            if gno[k] > gmax or book not in MKp[ids[k]]: continue
            L, mk, o1, o2 = MKp[ids[k]][book][wh]; pw, pp, pl = cover(mk + w * (FIN[k] - mk), L, SIG + (0.1 if w < 1 else 0))
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < thr: continue
            xx = (act[k] + L) * s_; U[int(ys[k])].append((od - 1) if xx > 0 else (0 if xx == 0 else -1))
        return U
    RULES = list(itertools.product((1.0, .75, .5, .25), (.04, .06, .08, .12, .16), (3, 6, 99)))
    CUR = (1.0, .08, 99)
    UC = {r: units(r, 3) for r in RULES}; UB = {r: units(r, 8) for r in RULES}
    tot = lambda U, ys_: sum(sum(U[y]) for y in ys_)
    P('  in-sample (ολες οι σεζον, Crown ανοιγμα) — καλυτεροι 10 κανονες (w, οριο, πρωτα Ν ματς):')
    for r in sorted(RULES, key=lambda r: -tot(UC[r], EV))[:10]:
        n = sum(len(UC[r][y]) for y in EV)
        P(f'    {r}: {tot(UC[r], EV):+.1f}u (n {n}, ROI {tot(UC[r], EV) / max(n, 1) * 100:+.1f}%) · Bet365 {tot(UB[r], EV):+.1f}u · θετικες σεζον {sum(sum(UC[r][y]) > 0 for y in EV)}/5')
    P(f'  σημερινος κανονας {CUR}: Crown {tot(UC[CUR], EV):+.1f}u (n {sum(len(UC[CUR][y]) for y in EV)}) · Bet365 {tot(UB[CUR], EV):+.1f}u')
    held_c, held_b, ch = {}, {}, {}
    for Y in EV:
        tr = [x for x in EV if x != Y]; r = max(RULES, key=lambda r: tot(UC[r], tr)); ch[Y] = r
        held_c[Y] = UC[r][Y]; held_b[Y] = UB[r][Y]
    P('  LOSO επιλογες: ' + ' · '.join(f'{Y}: {ch[Y]}' for Y in EV))
    for lab, H, U0 in (('Crown ανοιγμα', held_c, UC[CUR]), ('Bet365 ανοιγμα', held_b, UB[CUR])):
        P(f'  {lab}: LOSO κανονας ' + ' '.join(f'{Y}: {sum(H[Y]):+.1f}u/{len(H[Y])}' for Y in EV) + f' = {sum(sum(H[Y]) for Y in EV):+.1f}u (n {sum(len(H[Y]) for Y in EV)})')
        P(f'  {"":{len(lab)}}  σημερινος   ' + ' '.join(f'{Y}: {sum(U0[Y]):+.1f}u/{len(U0[Y])}' for Y in EV) + f' = {sum(sum(U0[Y]) for Y in EV):+.1f}u (n {sum(len(U0[Y]) for Y in EV)})')
    better = sum(sum(held_c[Y]) > sum(UC[CUR][Y]) for Y in EV)
    ok = sum(sum(held_c[Y]) for Y in EV) > tot(UC[CUR], EV) and better >= 4 and sum(sum(held_b[Y]) for Y in EV) > tot(UB[CUR], EV)
    P(f'  ΚΡΙΣΗ: καλυτερος σε {better}/5 σεζον · ' + ('✓ ΜΠΑΙΝΕΙ' if ok else '✗ ΔΕΝ ΜΠΑΙΝΕΙ'))
    open('bcl_round_anchor_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
