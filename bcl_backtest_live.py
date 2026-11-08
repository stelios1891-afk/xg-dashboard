# -*- coding: utf-8 -*-
"""bcl_backtest_live.py — BCL: BACKTEST ΤΗΣ ΜΗΧΑΝΗΣ ΠΟΥ ΤΡΕΧΕΙ ΣΗΜΕΡΑ (8/10/2026, Στελιος «τα σωστα backtest νουμερα»).
ΧΑΝΤΙΚΑΠ: live φορμουλα (0.25·μονο BCL + 0.75·κοινη κλιμακα, χωρις Τσεχια/Φινλανδια) · σ 12 · edge ≥8% · ματς BCL 2021-26 (και προκριματικα).
ΣΥΝΟΛΑ: live μηχανη συνολων (κοινη κλιμακα, περσι .35, λ 20, τυχη .1, προκριματικα με ΔΙΚΟ τους επιπεδο) · σ 17.3 · edge ≥8% · μονο κανονικη περιοδος.
Αγορα: Crown & Bet365 (Nowgoal), ανοιγμα & κλεισιμο· αποτελεσμα = ΜΕΣΟΣ των δυο βιβλιων (1 μοναδα ανα pick).
ΣΗΜ.: ιστορικα ΔΕΝ υπαρχουν αποδοσεις νικητη (φετος ναι) — αλλιως ιδια μηχανη. Εξοδος: bcl_backtest_live_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
Phi = NormalDist().cdf
EV = [2021, 2022, 2023, 2024, 2025]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    import bcl_common as B
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    cnt = collections.Counter(); GN = {}
    for k, L in FG.items():
        if not k.startswith('BCL_'): continue
        y = int(k.split('_')[1])
        for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
            cnt[(y, e['hid'])] += 1; cnt[(y, e['aid'])] += 1; GN[e['id']] = max(cnt[(y, e['hid'])], cnt[(y, e['aid'])])
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def pick(m, L, o1, o2, x, s):
        pw, pp, pl = cover(m, L, s); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: return None
        v = x * side; return (od - 1) if v > 0 else (0 if v == 0 else -1)
    # ---------- ΧΑΝΤΙΚΑΠ ----------
    H = collections.defaultdict(lambda: collections.defaultdict(list))      # (when, ζωνη) → y → [μεσο κερδος ανα ματς]
    for k, i in enumerate(D['id']):
        y = int(D['y'][k])
        if y not in EV or i not in E or i not in MK or not np.isfinite(D['FIN'][k]): continue
        act = int(E[i]['hs']) - int(E[i]['as_']); z = '1-3' if GN.get(i, 0) <= 3 else '4+'
        for when in ('o', 'c'):
            us = []
            for b in (3, 8):
                v = MK[i].get(b, {}).get(when)
                if not v: continue
                L, mu, o1, o2 = v; u = pick(float(D['FIN'][k]), L, o1, o2, act + L, 12.0)
                if u is not None: us.append(u)
            if us:
                for zz in (z, 'ολα'): H[(when, zz)][y].append(float(np.mean(us)))
    def row(d):
        a = [u for v in d.values() for u in v]
        return (f"{len(a):4d} picks · {sum(a):+6.1f} μ · ROI {np.mean(a)*100:+5.1f}% · θετικες σεζον {sum(1 for Y in EV if d.get(Y) and np.mean(d[Y]) > 0)}/5 · "
                + ' '.join(f"{Y % 100}:{np.mean(d[Y])*100:+.0f}%({len(d[Y])})" for Y in EV if d.get(Y)))
    P('############ ΧΑΝΤΙΚΑΠ (live φορμουλα, edge ≥8%, μεσος Crown/Bet365) ############')
    for when, lab in (('o', 'ΑΝΟΙΓΜΑ'), ('c', 'ΚΛΕΙΣΙΜΟ')):
        for zz in ('ολα', '1-3', '4+'):
            P(f'  {lab:8s} {("ολα τα ματς" if zz == "ολα" else "αγων " + zz):12s} {row(H[(when, zz)])}')
    # ---------- ΣΥΝΟΛΑ ----------
    rows = B.load(pre=True)
    preds = B.run_tot(rows, .35, 20.0, kf=1.0, wo=1.0, tmap=B.luck_totals(.1), qmode='own')
    ROWS = collections.defaultdict(dict)
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 23 and r['cid'] in (3, 8):
            ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    byscore = collections.defaultdict(list)
    for i, e in E.items():
        if 'Qualif' in (e.get('stage') or ''): continue
        byscore[(int(e['hs']), int(e['as_']))].append(i)
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
            for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
                for i in byscore.get(key, []):
                    if abs(E[i]['ts'] - tip) <= 26 * 3600: hit = i; break
                if hit: break
            if not hit or hit not in preds: continue
            m, y = preds[hit]
            if y not in EV: continue
            tot = int(E[hit]['hs']) + int(E[hit]['as_']); z = '1-3' if GN.get(hit, 0) <= 3 else '4+'
            for when in ('o', 'c'):
                us = []
                for cid, R_ in ROWS[g['ngid']].items():
                    if not R_: continue
                    x = R_[0] if when == 'o' else [r_ for r_ in R_ if r_[0] + 8 * 3600 <= tip + 600][-1] if [r_ for r_ in R_ if r_[0] + 8 * 3600 <= tip + 600] else None
                    if not x: continue
                    L, o1, o2 = float(x[1]), 1 + x[2], 1 + x[3]
                    u = pick(m, -L, o1, o2, tot - L, 17.3)
                    if u is not None: us.append(u)
                if us:
                    for zz in (z, 'ολα'): T[(when, zz)][y].append(float(np.mean(us)))
    P(''); P('############ ΣΥΝΟΛΑ (live μηχανη, προκριματικα με δικο τους επιπεδο, edge ≥8%, μεσος Crown/Bet365, κανονικη περιοδος) ############')
    for when, lab in (('o', 'ΑΝΟΙΓΜΑ'), ('c', 'ΚΛΕΙΣΙΜΟ')):
        for zz in ('ολα', '1-3', '4+'):
            P(f'  {lab:8s} {("ολα τα ματς" if zz == "ολα" else "αγων " + zz):12s} {row(T[(when, zz)])}')
    open('bcl_backtest_live_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
