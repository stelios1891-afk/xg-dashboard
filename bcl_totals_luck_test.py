# -*- coding: utf-8 -*-
"""bcl_totals_luck_test.py — BCL ΣΥΝΟΛΑ: ΔΙΟΡΘΩΣΗ ΤΥΧΗΣ στην κοινη κλιμακα συνολων (6/10/2026, Στελιος «τρεξε τη διορθωση τυχης»).
Καθε ματς με box score (12 διοργανωσεις: ACB BBL LNB LBA ABA LKL BCL TBL GBL ISR EL VTB) μπαινει στη μηχανη με συνολο «χωρις τυχη»:
ποσοστα τριποντων/βολων κρατιουνται κατα w {.1, .25, .5} και τα υπολοιπα γινονται ο μεσος της διοργανωσης (ματς χωρις box → σκετο σκορ).
Πανω στην καλυτερη ρυθμιση του bcl_totals_test (περσι .2/.35, λ 10/20, εγχωρια ×1, φιλικα ×1).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO 2021-25 (RMSE πραγματικου συνολου ολων των ματς BCL)· ΜΠΑΙΝΕΙ αν καλυτερο απο το «χωρις διορθωση» σε ≥4/5.
Αγορα: ιδια αξιολογηση με bcl_totals_test (bcl_totals_market.evaluate). Εξοδος: bcl_totals_luck_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, itertools
import numpy as np
from multiprocessing import Pool
BASE = list(itertools.product((.2, .35), (10.0, 20.0)))          # (περσι, λ)
WS = (None, .1, .25, .5)

def _job(a):
    (car, lam), w = a
    import bcl_common as B
    tm = B.luck_totals(w) if w is not None else None
    return a, B.run_tot(B.load(pre=True), car, lam, kf=1.0, wo=1.0, tmap=tm)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    D = pickle.load(open('bcl_totals_preds.pkl', 'rb'))
    ids, ys, TOT, gno = D['id'], D['y'], D['tot'], D['gno']
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    tsm = {e['id']: e['ts'] for k, L in FG.items() if k.startswith('BCL_') for e in L}
    import pandas as pd
    TT = np.array([pd.Timestamp(tsm.get(i, 0), unit='s') for i in ids])
    EV = [2021, 2022, 2023, 2024, 2025]
    jobs = [(b, w) for b in BASE for w in WS]
    with Pool(len(jobs)) as pool: R = dict(pool.map(_job, jobs))
    pos = {i: k for k, i in enumerate(ids)}
    V = {}
    for key, pr in R.items():
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        V[key] = v
    def rm(v, yy):
        m = np.isin(ys, yy) & np.isfinite(v); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
    P('in-sample RMSE (περσι, λ) × τυχη w (None = χωρις διορθωση):')
    for b in BASE: P(f'  {b}: ' + ' · '.join(f'w {w}: {rm(V[(b, w)], EV):.3f}' for w in WS))
    def nested(keys):
        held = np.full(len(ids), np.nan); ch = {}
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(keys, key=lambda k: rm(V[k], tr)); ch[Y] = k; held[ys == Y] = V[k][ys == Y]
        return held, ch
    H0, c0 = nested([k for k in V if k[1] is None]); H1, c1 = nested(list(V))
    P(''); P('LOSO επιλογες: χωρις ' + ' · '.join(f'{Y}: {c0[Y]}' for Y in EV)); P('              με τυχη ' + ' · '.join(f'{Y}: {c1[Y]}' for Y in EV))
    d = [rm(H1, [Y]) - rm(H0, [Y]) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
    P(f'ΔΙΟΡΘΩΣΗ ΤΥΧΗΣ: {rm(H0, EV):.3f} → {rm(H1, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
    kb = min(V, key=lambda k: rm(V[k], EV)); P(f'ΕΠΙΛΟΓΗ ΓΙΑ LIVE (ολες οι σεζον): {kb} · {rm(V[kb], EV):.3f}')
    import bcl_totals_market as TM
    for lab, F in (('ΧΩΡΙΣ διορθωση (LOSO)', H0), ('ΜΕ διορθωση τυχης (LOSO)', H1)):
        P(''); P(f'################ ΑΓΟΡΑ — {lab} ################')
        TM.evaluate(ids, ys, TOT, TT, gno, F, P)
    pickle.dump(dict(id=ids, y=ys, H0=H0, H1=H1, c1=c1, ok=ok, kb=kb), open('bcl_totals_luck_preds.pkl', 'wb'))
    open('bcl_totals_luck_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
