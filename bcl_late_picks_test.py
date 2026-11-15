# -*- coding: utf-8 -*-
"""bcl_late_picks_test.py — BCL: ΑΡΓΑ PICKS (γεννιουνται ΜΕΤΑ το ανοιγμα) ΣΕ ΧΑΝΤΙΚΑΠ & ΣΥΝΟΛΑ (27/10/2026, Στελιος «τρεξτο» · αφορμη
Bamberg−Varese Under 169.5: 4.2% στο ανοιγμα → 10.8% 5ω πριν, μονο τιμη, αγορα +1.1π προς Over). Ιδιο σχημα με NBA t108-t110. ΠΕΡΙΓΡΑΦΙΚΟ.
ΔΕΔΟΜΕΝΑ: Nowgoal Crown (cid 3, ανοιγει ~9ω πριν) & Bet365 (cid 8, ~32ω πριν), καθε αλλαγη με ωρα, BCL 2021-22 … 2025-26.
ΜΟΝΤΕΛΟ (ιδιο ολη τη μερα — το BCL δεν εχει ειδησεις απουσιων → ολα τα αργα ειναι «καθαρη κινηση αγορας»):
  ΧΑΝΤΙΚΑΠ: live φορμουλα (bcl_engine_preds_live.pkl), σ 12, edge ≥8% · ΣΥΝΟΛΑ: live μηχανη (run_tot .35/λ20/τυχη .1/προκριματικα own), σ 17.3, ≥8%.
ΣΤΙΓΜΕΣ: Τ−36,−30,−24,−18,−12,−9,−6,−4,−3,−2,−1,−0.5ω (μονο μετα το ανοιγμα του βιβλιου). ΑΡΓΟ = πρωτη στιγμη που μια πλευρα φτανει 8% ενω
  ΔΕΝ ηταν pick στο ανοιγμα. Αποτελεσμα στην τιμη της στιγμης · CLV = δικαιη γραμμη κλεισιματος − της στιγμης, προς εμας (ποντοι).
ΟΜΑΔΕΣ: μπλοκ ωρων (>12 · 12-6 · 6-3 · 3-1 · <1ω) · κινηση αγορας ΚΟΝΤΡΑ απο το ανοιγμα (<1 · 1-2 · ≥2π) · edge ανοιγματος (6-8% · 4-6% · <4%).
ΚΡΙΤΗΡΙΟ (ιδιο με NBA): ομαδα «σαν τα picks ανοιγματος» μονο αν ROI > 0, ≥4/5 σεζον, CLV > 0, n ≥ 80 — χωριστα ανα βιβλιο.
Εξοδος: bcl_late_picks_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import bcl_common as B
    NN = NormalDist(); Phi = NN.cdf
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    EV = [2021, 2022, 2023, 2024, 2025]; HS = (36, 30, 24, 18, 12, 9, 6, 4, 3, 2, 1, 0.5)
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    ROWS = {21: collections.defaultdict(dict), 23: collections.defaultdict(dict)}
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] in (21, 23) and r['cid'] in (3, 8): ROWS[r['t']][r['ngid']][r['cid']] = r['rows']
    SCH = [g for f in sorted(os.listdir('nowgoal_bcl')) if f.startswith('sched_') for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')) if g.get('hs') is not None]
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def block(h): return '>12ω' if h > 12 else ('12-6ω' if h > 6 else ('6-3ω' if h > 3 else ('3-1ω' if h > 1 else '<1ω')))
    REC = []
    # ---------------- ΧΑΝΤΙΚΑΠ ----------------
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, YS, T, FIN = D['id'], D['y'], D['t'], D['FIN']
    sc = {mid: (int(e['hs']), int(e['as_'])) for mid, e in E.items()}
    idx = collections.defaultdict(list)
    for i, mid in enumerate(ids):
        if mid in sc: idx[sc[mid]].append(i)
    for g in SCH:
        if g['ngid'] not in ROWS[21]: continue
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
        for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
            for i in idx.get((a_, b_), []):
                if abs((pd.Timestamp(T[i]) - tip).total_seconds()) <= 26 * 3600: hit, sw = i, swp; break
            if hit is not None: break
        if hit is None or int(YS[hit]) not in EV or not np.isfinite(FIN[hit]): continue
        act = sc[ids[hit]][0] - sc[ids[hit]][1]; tp = tip.timestamp()
        for cid in (3, 8):
            rows = sorted([x for x in ROWS[21][g['ngid']].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tp + 600], key=lambda x: x[0])
            if not rows: continue
            def conv(x):
                o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 12.0 * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                return (x[0] + 8 * 3600,) + ((-L, -mu, o2, o1) if sw else (L, mu, o1, o2))
            H = [conv(x) for x in rows]
            def at(ts): c = [x for x in H if x[0] <= ts]; return c[-1] if c else None
            def edges(x): _, L, mk, o1, o2 = x; pw, pp, pl = cover(FIN[hit], L, 12.0); return {1: (pw * o1 + pp - 1, o1), -1: (pl * o2 + pp - 1, o2)}, L
            x0 = H[0]; xc = H[-1]; E0, _ = edges(x0); seen = set()
            for sd in (1, -1):
                if E0[sd][0] >= .08:
                    v = (act + x0[1]) * sd
                    REC.append(dict(mkt='χαντικαπ', bk=cid, sea=int(YS[hit]), kind='ανοιγμα', res=(E0[sd][1] - 1) if v > 0 else (0.0 if v == 0 else -1.0), clv=sd * (xc[2] - x0[2])))
            for h in HS:
                ts = tp - h * 3600
                if ts <= x0[0]: continue
                x = at(ts); Ex, L = edges(x)
                for sd in (1, -1):
                    if Ex[sd][0] < .08 or E0[sd][0] >= .08 or sd in seen: continue
                    seen.add(sd); v = (act + L) * sd
                    REC.append(dict(mkt='χαντικαπ', bk=cid, sea=int(YS[hit]), kind='αργο', bl=block(h), hrs=h, e0=E0[sd][0], e=Ex[sd][0], move=sd * (x0[2] - x[2]), dline=sd * (L - x0[1]),
                                    res=(Ex[sd][1] - 1) if v > 0 else (0.0 if v == 0 else -1.0), clv=sd * (xc[2] - x[2]), ex=f"{g['ngid']}"))
    # ---------------- ΣΥΝΟΛΑ ----------------
    preds = B.run_tot(B.load(pre=True), .35, 20.0, kf=1.0, wo=1.0, tmap=B.luck_totals(.1), qmode='own')
    byscore = collections.defaultdict(list)
    for i, e in E.items():
        if 'Qualif' in (e.get('stage') or ''): continue
        byscore[(int(e['hs']), int(e['as_']))].append(i)
    for g in SCH:
        if g['ngid'] not in ROWS[23]: continue
        tp = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
        for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
            for i in byscore.get(key, []):
                if abs(E[i]['ts'] - tp) <= 26 * 3600: hit = i; break
            if hit: break
        if not hit or hit not in preds: continue
        m, y = preds[hit]
        if y not in EV: continue
        tot = int(E[hit]['hs']) + int(E[hit]['as_'])
        for cid in (3, 8):
            rows = sorted([x for x in ROWS[23][g['ngid']].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tp + 600], key=lambda x: x[0])
            if not rows: continue
            H = []
            for x in rows:
                Tl, oo, ou = float(x[1]), 1 + x[2], 1 + x[3]; po = (1 / oo) / (1 / oo + 1 / ou)
                H.append((x[0] + 8 * 3600, Tl, Tl + 17.3 * NN.inv_cdf(min(max(po, 1e-4), 1 - 1e-4)), oo, ou))
            def at(ts): c = [x for x in H if x[0] <= ts]; return c[-1] if c else None
            def edges(x):
                _, Tl, mk, oo, ou = x; po, pq, pu = cover(m, -Tl, 17.3)
                return {1: (po * oo + pq - 1, oo), -1: (pu * ou + pq - 1, ou)}, Tl
            x0 = H[0]; xc = H[-1]; E0, _ = edges(x0); seen = set()
            for sd in (1, -1):
                if E0[sd][0] >= .08:
                    v = (tot - x0[1]) * sd
                    REC.append(dict(mkt='συνολα', bk=cid, sea=int(y), kind='ανοιγμα', side=sd, res=(E0[sd][1] - 1) if v > 0 else (0.0 if v == 0 else -1.0), clv=sd * (xc[2] - x0[2])))
            for h in HS:
                ts = tp - h * 3600
                if ts <= x0[0]: continue
                x = at(ts); Ex, Tl = edges(x)
                for sd in (1, -1):
                    if Ex[sd][0] < .08 or E0[sd][0] >= .08 or sd in seen: continue
                    seen.add(sd); v = (tot - Tl) * sd
                    REC.append(dict(mkt='συνολα', bk=cid, sea=int(y), kind='αργο', side=sd, bl=block(h), hrs=h, e0=E0[sd][0], e=Ex[sd][0], move=sd * (x0[2] - x[2]), dline=sd * (Tl - x0[1]),
                                    res=(Ex[sd][1] - 1) if v > 0 else (0.0 if v == 0 else -1.0), clv=sd * (xc[2] - x[2])))
    X = pd.DataFrame(REC)
    def cell(d):
        if not len(d): return '—'
        ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum()); ok = d.res.mean() > 0 and pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
        return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}, CLV {d.clv.mean():+.2f}π)' + (' ✓' if ok else '')
    P('bcl_late_picks_test · BCL ΑΡΓΑ PICKS · Nowgoal Crown/Bet365 · 2021-22 … 2025-26 · live μοντελα · edge ≥8% · κελι = ROI (picks, μοναδες, θετ. σεζον, CLV) · ✓ = κριτηριο')
    for mkt in ('χαντικαπ', 'συνολα'):
        for bk, bn in ((3, 'Crown'), (8, 'Bet365')):
            D_ = X[(X.mkt == mkt) & (X.bk == bk)]; O = D_[D_.kind == 'ανοιγμα']; L_ = D_[D_.kind == 'αργο']
            P(f'\n################ {mkt.upper()} · {bn} ################')
            P(f'  PICKS ΑΝΟΙΓΜΑΤΟΣ: {cell(O)}')
            P(f'  ΟΛΑ ΤΑ ΑΡΓΑ:      {cell(L_)}' + (f' · Over {cell(L_[L_.side == 1])} · Under {cell(L_[L_.side == -1])}' if mkt == 'συνολα' else ''))
            P('  ανα μπλοκ ωρων:')
            for b in ('>12ω', '12-6ω', '6-3ω', '3-1ω', '<1ω'): P(f'    {b:6s} {cell(L_[L_.bl == b])}')
            P('  ανα κινηση αγορας ΚΟΝΤΡΑ μας απο το ανοιγμα (δικαιη γραμμη):')
            for nm, lo, hi in (('<1π', -99, 1), ('1-2π', 1, 2), ('≥2π', 2, 99)): P(f'    {nm:5s} {cell(L_[(L_.move >= lo) & (L_.move < hi)])}')
            P('  ανα edge ανοιγματος (κινηση <1π = «οριακα, μονο τιμη») / ολα:')
            for nm, lo, hi in (('6-8%', .06, .08), ('4-6%', .04, .06), ('<4%', -9, .04)):
                d = L_[(L_.e0 >= lo) & (L_.e0 < hi)]; P(f'    {nm:5s} κινηση <1π {cell(d[d.move < 1])} │ ολα {cell(d)}')
            if mkt == 'συνολα':
                d = L_[(L_.side == -1) & (L_.move < 1.5) & (L_.hrs <= 6) & (L_.hrs > 3)]
                P(f'  ΤΥΠΟΣ BAMBERG (Under, 6-3ω πριν, κινηση κοντρα <1.5π): {cell(d)}')
    P('\n  ΣΗΜ.: στο BCL ΔΕΝ υπαρχει χρονικη πληροφορια απουσιων → ολα τα αργα = καθαρη κινηση αγορας (οπως τα «καθαρα» του NBA t109/t110).')
    X.to_csv('_bcl_late_picks.csv', index=False)
    open('bcl_late_picks_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
