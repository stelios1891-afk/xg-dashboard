# -*- coding: utf-8 -*-
"""nba_base_grid3.py — NBA ΑΦΕΤΗΡΙΑ ΑΠΟ ΡΟΣΤΕΡ v2 (28/9/2026): ηλικια · ρουκι · παραθυρο ρόστερ.
Σταθερα (απο nba_base_grid): εδρα 2 · HL 60 · τυχη 0.75 · κοινη εδρα.
Εκδοχες (nba_roster_adj2.json): αξια {V0 = v1, AGE, ROOK, BOTH} × παραθυρο {W1, W3, W5, W10, ROLL}.
Για καθε εκδοχη πλεγμα περσι {.8,.9,1} × K {8,12} × beta {.75,1,1.5}· LOSO: ρυθμιση απο τις ΑΛΛΕΣ σεζον (ελαχιστο RMSE Οκτ-Δεκ).
ΚΡΙΣΗ (προ-δηλωμενη): εκδοχη ΠΕΡΝΑ αν το εκτος-δειγματος RMSE Οκτ-Δεκ ειναι καλυτερο απο V0|W3 (= σημερινη νεα βαση) σε ≥4/5 σεζον.
  Επισης: ολη η σεζον · κλιση b · picks Οκτ-Δεκ ≥5/8%. Σημ.: W3/W5/W10 κοιτανε λιγο μπροστα (ρόστερ ματς που δεν παιχτηκαν ακομα)·
  W1 και ROLL = μονο οτι ειναι γνωστο στο τζαμπολ. Εξοδος: nba_base_grid3_out.txt"""
import sys, os
import numpy as np
from multiprocessing import Pool

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import nba_base_core as C
    out = []
    def P(s=''):
        print(s, flush=True); out.append(str(s))
    IDX, ACT, MM, SE, G = C.IDX, C.ACT, C.MM, C.SE, C.G
    EV = [int(s) for s in C.EVAL]
    MON = G.date.dt.month.values[IDX]; OD = np.isin(MON, [10, 11, 12])
    VARS = [f'{v}|{w}' for v in ('V0', 'AGE', 'ROOK', 'BOTH') for w in ('W1', 'W3', 'W5', 'W10', 'ROLL')]
    cfgs = [dict(h=2.0, lam=l, HL=60, carry=c, lw=0.75, beta=b, radj=v) for v in VARS for c in (0.8, 0.9, 1.0) for l in (8, 12) for b in (0.75, 1.0, 1.5)]
    key = lambda c: (c['radj'], c['carry'], c['lam'], c['beta'])
    CACHE = 'nba_base_grid3_cache.npz'; PRED = {}
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); PRED = {tuple(k): v for k, v in zip(z['keys'].tolist(), z['vals'])}
        PRED = {(k[0], float(k[1]), int(k[2]), float(k[3])): v for k, v in PRED.items()}
    todo = [c for c in cfgs if key(c) not in PRED]
    P(f'τρεξιμο {len(todo)} ρυθμισεων…')
    if todo:
        with Pool(16) as pool:
            for k, (c, pr) in enumerate(pool.imap_unordered(C.job, todo, chunksize=2)):
                PRED[key(c)] = pr
                if (k + 1) % 60 == 0: P(f'  {k + 1}/{len(todo)}')
        np.savez(CACHE, keys=np.array(list(PRED.keys()), dtype=object), vals=np.array(list(PRED.values())))
    def rm(p, s, msk): k = (SE == s) & msk; return float(np.sqrt(np.mean((ACT - p[IDX])[k] ** 2)))
    held = {}
    for v in VARS:
        ks = [key(c) for c in cfgs if c['radj'] == v]
        p = np.full(len(G), np.nan); ch = []
        for Y in EV:
            best = min(ks, key=lambda k: np.mean([rm(PRED[k], s, OD) for s in EV if s != Y]))
            p[G.season.values == Y] = PRED[best][G.season.values == Y]; ch.append(best)
        held[v] = (p, ch)
    base = held['V0|W3'][0]
    def roi_od(p, thr):
        mm = p.copy(); mm[IDX[~OD]] = MM[~OD]
        R = C.roi(mm, thr, EV); pos = sum(1 for s in EV if len(R[R.season == s]) and R[R.season == s].p.mean() > 0)
        return f'{R.p.mean()*100:+.1f}% ({len(R)}) {pos}/5'
    P(f'αγορα: Οκτ-Δεκ RMSE {np.sqrt(np.mean((ACT - MM)[np.isin(SE, EV) & OD] ** 2)):.3f} · ολη {np.sqrt(np.mean((ACT - MM)[np.isin(SE, EV)] ** 2)):.3f}')
    P(f'{"εκδοχη":11s} | {"Οκτ-Δεκ":8s} | vs V0|W3 ανα σεζον (Οκτ-Δεκ)            | κρ. | {"ολη":7s} | b Οκτ-Δεκ | picks Οκτ-Δεκ ≥5% | ≥8% | συνηθης επιλογη')
    for v in VARS:
        p, ch = held[v]
        od_all = np.sqrt(np.mean((ACT - p[IDX])[np.isin(SE, EV) & OD] ** 2)); full = np.sqrt(np.mean((ACT - p[IDX])[np.isin(SE, EV)] ** 2))
        diffs = [rm(p, s, OD) - rm(base, s, OD) for s in EV]; wins = sum(d < 0 for d in diffs)
        k = np.isin(SE, EV) & OD; b = np.polyfit((p[IDX] - MM)[k], (ACT - MM)[k], 1)[0]
        from collections import Counter
        cc = Counter((c[1], c[2], c[3]) for c in ch).most_common(1)[0][0]
        P(f'{v:11s} | {od_all:.3f}   | ' + ' '.join(f'{d:+.3f}' for d in diffs) + f' | {"ΠΕΡΝΑ" if wins >= 4 and v != "V0|W3" else ("—" if v == "V0|W3" else "✗"):5s} | {full:.3f} | {b:+.3f}    | '
          f'{roi_od(p, 0.05)} | {roi_od(p, 0.08)} | περσι {cc[0]} K {cc[1]} beta {cc[2]}')
    open('nba_base_grid3_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
