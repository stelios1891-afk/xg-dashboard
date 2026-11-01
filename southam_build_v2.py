"""southam_build_v2.py — 5/10/2026: χτιζει τη v2 μηχανη Βραζιλιας/MLS (ρυθμισεις που περασαν) με επιλογη κοκκινων.
Χρηση: python southam_build_v2.py <red> <out.csv>   (red: live | none | emps)"""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import southam_tune as T
RED = {'live': True, 'none': False}.get(sys.argv[1], sys.argv[1]); OUT = sys.argv[2]
old = pd.read_csv('southam_preds.csv', dtype={'mid': str}).set_index('mid')
def loso_conv(P, frac):
    P = P.copy(); R = P[P.stage == 'regular']
    rs = R.groupby(['league', 'season']).apply(lambda g: (g.hg + g.ag).sum() / (g.lh + g.la).sum(), include_groups=False)
    for (lg, s), _ in rs.items():
        c = np.mean([rs[(lg, o)] for (l2, o) in rs.index if l2 == lg and o != s]) ** frac
        k = (P.league == lg) & (P.season == s); P.loc[k, 'lh'] *= c; P.loc[k, 'la'] *= c
    return P
B = T.split_run({'red': RED}, {'blend': 0.8, 'red': RED}); B = B[B.league == 'Brazil']
sup = T.run({'hfa': 'roll', 'hfa_K': 300, 'prior_reg': 0.3, 'red': RED}).set_index('mid')
tot = loso_conv(T.run({'red': RED}), 0.5).set_index('mid')
s = sup.lh - sup.la; t = (tot.lh + tot.la).reindex(sup.index)
sup['lh'] = ((t + s) / 2).clip(lower=.05); sup['la'] = ((t - s) / 2).clip(lower=.05)
Mx = sup.reset_index(); Mx = Mx[Mx.league == 'MLS']
P = pd.concat([B, Mx], ignore_index=True).rename(columns={'lh': 'lh_base', 'la': 'la_base', 'hx': 'h_xg_act', 'ax': 'a_xg_act'})
P['newc_h'] = P.mid.map(old.newc_h).fillna(False); P['newc_a'] = P.mid.map(old.newc_a).fillna(False)
P.to_csv(OUT, index=False); print(OUT, len(P))
