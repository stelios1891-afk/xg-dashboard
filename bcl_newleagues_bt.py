# -*- coding: utf-8 -*-
"""bcl_newleagues_bt.py — BCL backtest ΜΕ vs ΧΩΡΙΣ τα νεα πρωταθληματα Τσεχιας (CZE) & Φινλανδιας (FIN) (7/10/2026, Στελιος «τρεξε το backtest στα νεα πρωταθληματα»).
Ιδια live φορμουλα: χαντικαπ 0.25·Μ1 (μονο BCL) + 0.75·κοινη κλιμακα (περσι 1.3, λ 1.5, φιλικα .5, εγχωρια ×1.5) · συνολα κοινη κλιμακα συνολων (περσι .35, λ 20,
φιλικα ×1, τυχη .1). Μονη διαφορα: τα ματς CZE/FIN μεσα στην κοινη κλιμακα ή οχι.
Ομαδα ενδιαφεροντος: ματς BCL με ομαδα που επαιξε στο τσεχικο/φινλανδικο πρωταθλημα (ιδια ή προηγουμενη σεζον).
Μετρα: λαθος (πραγματικο − προβλεψη), λαθος αγορας, ROI picks ≥8% στο ανοιγμα (Crown, Bet365). Και ελεγχος ΟΛΩΝ των αλλων ματς (να μη χαλασε κατι).
Εξοδος: bcl_newleagues_bt_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
from multiprocessing import Pool

def _job(a):
    kind, new = a
    import bcl_common as B
    rows = B.load(pre=True)
    if not new: rows = [r for r in rows if r[1] not in ('CZE', 'FIN')]
    if kind == 'h': return a, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5)
    return a, B.run_tot(rows, .35, 20.0, kf=1.0, wo=1.0, tmap=B.luck_totals(.1))

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']
    pos = {i: k for k, i in enumerate(ids)}
    with Pool(4) as pool: R = dict(pool.map(_job, [('h', False), ('h', True), ('t', False), ('t', True)]))
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    # Μ1 (μονο BCL) = ιδιο και στις δυο εκδοχες: απο την παλια live προβλεψη, Μ1 = (FIN − .75·Μ2_παλιο)/.25
    M2o, M2n = arr(R[('h', False)]), arr(R[('h', True)])
    M1 = (D['FIN'] - .75 * M2o) / .25
    H = {False: .25 * M1 + .75 * M2o, True: .25 * M1 + .75 * M2n}
    T = {False: arr(R[('t', False)]), True: arr(R[('t', True)])}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8')); XT = json.load(open('fs_bk_extra.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    import bcl_common as B
    peri = collections.defaultdict(set)
    for k, L in XT.items():
        lg, y = k.rsplit('_', 1)
        if lg in ('CZE', 'FIN'):
            for e in L:
                for t in (e['hid'], e['aid']): peri[B.ALIAS.get(t, t)].add((lg, int(y)))
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    tot = np.array([(int(E[i]['hs']) + int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    who = []
    sub = np.zeros(len(ids), bool)
    for k, i in enumerate(ids):
        if i not in E: continue
        y = int(ys[k]); tm = [B.ALIAS.get(E[i]['hid'], E[i]['hid']), B.ALIAS.get(E[i]['aid'], E[i]['aid'])]
        hit = [(t, lg) for t in tm for lg, yy in peri.get(t, ()) if yy in (y, y - 1)]
        if hit: sub[k] = True; who.append((y, E[i]['home'] if hit[0][0] == tm[0] else E[i]['away'], hit[0][1]))
    EV = [2021, 2022, 2023, 2024, 2025]
    ev = np.isin(ys, EV)
    c = collections.Counter((lg, n) for y, n, lg in who if y in EV)
    P(f'Ματς BCL 2021-26 με ομαδα τσεχικου/φινλανδικου πρωταθληματος: {int((sub & ev).sum())} · ομαδες: ' + ' · '.join(f'{n} ({lg}) {v}' for (lg, n), v in c.most_common()))
    # αγορα: χαντικαπ απο bcl_mk.pkl · συνολα απο Nowgoal t23
    MKH = pickle.load(open('bcl_mk.pkl', 'rb'))
    ND = NormalDist(); Phi = ND.cdf
    ROWS = collections.defaultdict(dict)
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    idx = collections.defaultdict(list)
    for k, i in enumerate(ids):
        if i in E: idx[(int(E[i]['hs']), int(E[i]['as_']))].append(k)
    MKT = {}
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
            for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
                for k in idx.get(key, []):
                    if abs(E[ids[k]]['ts'] - tip) <= 26 * 3600: hit = k; break
                if hit is not None: break
            if hit is not None:
                MKT[ids[hit]] = {cid: dict(o=(float(R_[0][1]), 1 + R_[0][2], 1 + R_[0][3]), c=(float(R_[-1][1]), 1 + R_[-1][2], 1 + R_[-1][3])) for cid, R_ in ROWS[g['ngid']].items() if R_}
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def roi(kind, v, msk, book):
        U = collections.defaultdict(list)
        for k, i in enumerate(ids):
            if not msk[k] or not np.isfinite(v[k]): continue
            if kind == 'h':
                mk = (MKH.get(i) or {}).get(book)
                if not mk: continue
                L, _, o1, o2 = mk['o']; pw, pp, pl = cover(v[k], L, 12.0); x = act[k] + L
            else:
                mk = (MKT.get(i) or {}).get(book)
                if not mk: continue
                L, o1, o2 = mk['o']; pw, pp, pl = cover(v[k], -L, 17.3); x = tot[k] - L
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < .08: continue
            q = x * s_; U[int(ys[k])].append((od - 1) if q > 0 else (0 if q == 0 else -1))
        u = [z for v_ in U.values() for z in v_]
        return f'{np.mean(u)*100:+.1f}% ({len(u)}, {sum(u):+.1f}u, θετ {sum(1 for Y in EV if U.get(Y) and np.mean(U[Y]) > 0)}/{sum(1 for Y in EV if U.get(Y))})' if u else '—'
    def rmse(v, tgt, msk): m = msk & np.isfinite(v) & np.isfinite(tgt); return float(np.sqrt(np.mean((tgt - v)[m] ** 2))), int(m.sum())
    for lab, msk in (('ΜΑΤΣ ΜΕ ΟΜΑΔΑ CZE/FIN', sub & ev), ('ΟΛΑ ΤΑ ΑΛΛΑ ΜΑΤΣ', (~sub) & ev)):
        P(''); P(f'################ {lab} ################')
        for kind, V, tgt, nm in (('h', H, act, 'ΧΑΝΤΙΚΑΠ'), ('t', T, tot, 'ΣΥΝΟΛΑ')):
            mc = np.array([((MKH.get(i) or {}).get(3) or {}).get('c', (None, np.nan))[1] if kind == 'h' else
                           (lambda m: (m['c'][0] + 17.3 * ND.inv_cdf(min(max((1 / m['c'][1]) / (1 / m['c'][1] + 1 / m['c'][2]), 1e-4), 1 - 1e-4))) if m else np.nan)((MKT.get(i) or {}).get(3)) for i in ids], float)
            eo, n = rmse(V[False], tgt, msk); en, _ = rmse(V[True], tgt, msk); em, nm_ = rmse(mc, tgt, msk & np.isfinite(V[True]))
            P(f'  {nm}: λαθος ΧΩΡΙΣ {eo:.2f} → ΜΕ {en:.2f} (n {n}) · αγορα κλεισιμο {em:.2f} (n {nm_}) · μεση αλλαγη προβλεψης {np.nanmean(np.abs(V[True] - V[False])[msk]):.2f} π.')
            for book, bn in ((3, 'Crown'), (8, 'Bet365')):
                P(f'     ROI ≥8% ανοιγμα {bn}: ΧΩΡΙΣ {roi(kind, V[False], msk, book)} → ΜΕ {roi(kind, V[True], msk, book)}')
    open('bcl_newleagues_bt_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
