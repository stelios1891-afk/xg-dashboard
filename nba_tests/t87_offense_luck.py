# -*- coding: utf-8 -*-
"""t87_offense_luck.py — ΣΥΝΟΛΑ NBA: ΤΥΧΗ ΕΠΙΘΕΣΗΣ με αμυνα .25 (25/10/2026, Στελιος «ναι»).
Ερωτημα: ειναι σωστο το .5 στην επιθεση; Επιθεση ∈ {.25, .375, .5, .75} · αμυνα .25 · βαση = LIVE (.5/.5) και (.5/.25) του t85/t86.
Ιδια μηχανη/αγορα/picks με t85. Ελεγχοι (στανταρ απο t86): ανα σεζον RMSE & μοναδες · WALK-FORWARD (επιλογη απο τις προηγουμενες σεζον
μεταξυ των 4) · ΖΕΥΓΑΡΩΤΗ vs (.5/.25) και vs LIVE · BOOTSTRAP μοναδων · PLACEBO.
Εξοδος: nba_tests/t87_offense_luck_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import t85_luck_split as T
K = [(0.25, 0.25), (0.375, 0.25), (0.5, 0.25), (0.75, 0.25), (0.5, 0.5)]
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    z = np.load(os.path.join(SC, '_t86_cache.npz')); RES = {k: (z[f'm{i}'], z[f't{i}']) for i, k in enumerate(T.COMBOS)}
    new = [k for k in K if k not in RES]
    with Pool(len(new), initializer=T.F._init) as pool:
        for k, mg, tt in pool.map(T.run_split, new): RES[k] = (mg, tt)
    T.F._init(); G = T.F._W['C'].G
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O.date, O.home, O.away)]; O = O[O.g.notna()].copy(); O['g'] = O.g.astype(int)
    O = O[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.g, O.tot)]].reset_index(drop=True)
    O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
    gi = O.g.values; ys = O.sea.values; SE = sorted(set(ys)); ND = NormalDist(); base = RES[(0.5, 0.5)][1][gi]
    TOT, TL, OO, OU, FA, CF = (O[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    MU = {k: O.mu.values + (RES[k][1][gi] - base) for k in K}
    def pick_u(mu):
        po = np.array([1 - ND.cdf((t - m) / 18) for t, m in zip(TL, mu)]); eo = po * OO - 1; eu = (1 - po) * OU - 1
        sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd > 0, OO, OU)
        x = (TOT - TL) * sd; u = np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0))
        return np.where(e >= .08, u, 0.0), np.where(e >= .08, sd * (CF - FA), np.nan)
    U = {k: pick_u(MU[k]) for k in K}
    rm = lambda k, m: float(np.sqrt(((TOT[m] - MU[k][m]) ** 2).mean()))
    uS = lambda k, m: float(U[k][0][m].sum())
    nm = lambda k: f'επ {k[0]}/αμ {k[1]}'
    LIVE, REF = (0.5, 0.5), (0.5, 0.25)
    P('=== ΑΝΑ ΕΚΔΟΧΗ (5 σεζον, picks συνολων ≥8% ανοιγμα Crown) ===')
    for k in K:
        n = int((U[k][0] != 0).sum()); P(f"  {nm(k):15s}{'(LIVE)' if k == LIVE else '      '} RMSE {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(k, ys == s):.3f}' for s in SE)
          + f') · μοναδες {uS(k, ys == ys):+6.1f} (' + ' '.join(f'{s % 100}:{uS(k, ys == s):+.0f}' for s in SE) + f') · picks {n} · CLV {np.nanmean(U[k][1]):+.2f}')
    cand = [k for k in K if k != LIVE]
    P('\n=== WALK-FORWARD: επιλογη επιθεσης απο τις προηγουμενες σεζον (αμυνα .25) ===')
    for crit, f in (('με RMSE', lambda k, m: -rm(k, m)), ('με μοναδες', lambda k, m: uS(k, m))):
        tot = [0, 0, 0]
        for s in SE[2:]:
            prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = max(cand, key=lambda k: f(k, prev))
            tot[0] += uS(b, cur); tot[1] += uS(REF, cur); tot[2] += uS(LIVE, cur)
            P(f'   {crit:10s} {s}: διαλεγει {nm(b):15s} μοναδες {uS(b, cur):+6.1f} · (.5/.25) {uS(REF, cur):+6.1f} · live {uS(LIVE, cur):+6.1f}')
        P(f'   {crit:10s} ΣΥΝΟΛΟ: {tot[0]:+.1f} · (.5/.25) {tot[1]:+.1f} · live {tot[2]:+.1f}')
    rng = np.random.default_rng(11); W = np.unique(wk)
    for ref in (REF, LIVE):
        P(f'\n=== ΖΕΥΓΑΡΩΤΗ / BOOTSTRAP / PLACEBO vs {nm(ref)} ===')
        for k in cand:
            if k == ref: continue
            d = (TOT - MU[ref]) ** 2 - (TOT - MU[k]) ** 2; dd = pd.Series(d).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
            dw = pd.Series(U[k][0] - U[ref][0]).groupby(wk).sum().reindex(W, fill_value=0).values
            bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(3000)])
            dlt = MU[k] - MU[ref]; real = dw.sum(); res = []
            for _ in range(400):
                perm = dlt.copy()
                for s in SE:
                    m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
                res.append(pick_u(MU[ref] + perm)[0].sum() - uS(ref, ys == ys))
            res = np.array(res)
            P(f'   {nm(k):15s} ζευγαρωτη t {t:+.2f} · μοναδες {real:+6.1f} (P bootstrap {100 * (bs > 0).mean():.0f}%, 90% [{np.percentile(bs, 5):+.0f}, {np.percentile(bs, 95):+.0f}])'
              f' · placebo ≥ πραγματικο {100 * (res >= real).mean():.1f}%')
    open(os.path.join(SC, 't87_offense_luck_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
