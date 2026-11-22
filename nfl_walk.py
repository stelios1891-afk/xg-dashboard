"""NFL WALK-FORWARD μηχανης: για καθε σεζον S (2021-2026) ΟΛΑ διαλεγονται μονο απο τις σεζον < S.

Μια παραμετρος τη φορα (2 γυροι), απο την αρχικη ρυθμιση, με κριτηριο το LOSO σφαλμα ΜΕΣΑ στις προηγουμενες σεζον:
  χαντικαπ: HL, περσινο, σβησιμο περσινου, μαζεμα επιθ/αμυνας, SoS, φασεις, εδρα, QB (HLQ, N0, M0), K win totals
  συνολα  : HL, περσινο, μαζεμα, SoS, φασεις, QB
Μετα: συντελεστες απο τις σεζον < S → προβλεψεις για τη S. Για την τιμολογηση κρατιουνται και οι LOSO προβλεψεις των
προηγουμενων σεζον (απο τις οποιες βγαινουν σ, κλειδια, κατανομη, β).
ΔΕΝ καθαριζεται: το ΠΟΙΟΙ μηχανισμοι μπηκαν στη μηχανη (αποφασιστηκαν βλεποντας ολες τις σεζον).
  python nfl_walk.py  → nfl_data/walk_preds.csv, walk_prior.csv, walk_params.json
"""
import json, sys, time
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test as T
import nfl_test8 as T8
import nfl_test16 as T16

sys.stdout.reconfigure(encoding='utf-8')
KS = T8.KS
GRID = {
    'm': {'HL': [6, 10, 16], 'PREV': [0.3, 0.6], 'HLp': [3, None], 'lam_o': [2, 3], 'lam_d': [3, 8], 'sos': [0.0, None],
          'win': ['all', 'cl'], 'home': [False, True], 'HLQ': [8, 20, 40], 'N0': [300, 1600], 'M0': [-0.15, -0.3]},
    't': {'HL': [6, 10, 16], 'PREV': [0.6, 0.8], 'lam_o': [2, 3], 'lam_d': [3, 8], 'sos': [0.0, None],
          'win': ['all', 'cl'], 'HLQ': [8, 12, 40], 'N0': [300, 1000], 'M0': [-0.1, -0.15]},
}
START = {'m': dict(HL=16, PREV=0.6, HLp=None, lam_o=3, lam_d=3, sos=None, win='cl', home=True, HLQ=40, N0=300, M0=-0.15),
         't': dict(HL=16, PREV=0.6, lam_o=3, lam_d=3, sos=None, win='cl', HLQ=40, N0=300, M0=-0.15)}
Y = {'m': 'result', 't': 'total'}
FT = G.FT0 + ['v_fixed', 'v_retr', 'v_turf', 'v_den']


def main():
    t0 = time.time()
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    fcache, bcache, qcache = {}, {}, {}

    def frame(p):
        key = tuple(sorted((k, str(v)) for k, v in p.items()))
        if key in fcache:
            return fcache[key]
        cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
        for k in ('sos', 'HLp'):
            if p.get(k) is not None:
                cfg[k] = p[k]
        if 'home' in p:
            cfg['home'] = p['home']
        bk = (tuple(sorted(cfg.items())), p['win'])
        if bk not in bcache:
            bcache[bk] = E.build(g, off, cfg, p['win'])
        qk = (p['HLQ'], p['N0'], p['M0'], p['HL'], p['PREV'])
        if qk not in qcache:
            qcache[qk] = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
        f = T16.venue_feats(G.frame(g, bcache[bk], qcache[qk]), g)
        keep = ['game_id', 'season', 'wk', 'result', 'total'] + G.FM0 + [f'wt_d_{K}' for K in KS] + FT
        f = f[list(dict.fromkeys(keep))].reset_index(drop=True)
        fcache[key] = f
        return f

    def fset(kind):
        return [G.FM0 + [f'wt_d_{K}'] for K in KS] if kind == 'm' else [FT]

    def loso_prior(f, kind, S):
        """LOSO μεσα στις σεζον < S. Επιστρεφει (MSE, Series προβλεψεων)."""
        y = Y[kind]
        h = f[f.season < S]
        pr = pd.Series(np.nan, index=h.index)
        for s in sorted(h.season.unique()):
            tr = h[h.season != s]
            best = None
            for F in fset(kind):
                c = T.ols(tr, F, y)
                sc = np.mean((tr[y] - T.pred(tr, F, c)) ** 2)
                if best is None or sc < best[0]:
                    best = (sc, F, c)
            te = h.season == s
            pr[te] = T.pred(h[te], best[1], best[2])
        return np.mean((h[y] - pr) ** 2), pr

    params, preds, priors = {}, [], []
    for kind in ('m', 't'):
        y = Y[kind]
        for S in range(2021, 2027):
            p = dict(START[kind])
            cur = loso_prior(frame(p), kind, S)[0]
            for rnd in range(2):
                ch = False
                for par, vals in GRID[kind].items():
                    for v in vals:
                        if v == p[par]:
                            continue
                        pp = dict(p); pp[par] = v
                        s = loso_prior(frame(pp), kind, S)[0]
                        if s < cur - 1e-6:
                            cur, p, ch = s, pp, True
                if not ch:
                    break
            f = frame(p)
            _, pr = loso_prior(f, kind, S)
            tr = f[f.season < S]
            best = None
            for F in fset(kind):
                c = T.ols(tr, F, y)
                sc = np.mean((tr[y] - T.pred(tr, F, c)) ** 2)
                if best is None or sc < best[0]:
                    best = (sc, F, c)
            te = f[f.season == S].copy()
            te['pred'] = T.pred(te, best[1], best[2])
            preds.append(te[['game_id', 'season', 'wk', 'result', 'total', 'pred']].assign(kind=kind))
            priors.append(f.loc[pr.index, ['game_id', 'season', 'result', 'total']].assign(pred=pr.values, kind=kind, S=S))
            params[f'{kind}{S}'] = {k: v for k, v in p.items()}
            r = np.sqrt(np.mean((te[y] - te.pred) ** 2)) if te[y].notna().any() else np.nan
            print(f'{kind} {S}: {p} · LOSO παρελθον {np.sqrt(cur):.3f} · RMSE σεζον {r:.3f} ({time.time() - t0:.0f}″)', flush=True)
    pd.concat(preds).to_csv('nfl_data/walk_preds.csv', index=False)
    pd.concat(priors).to_csv('nfl_data/walk_prior.csv', index=False)
    json.dump(params, open('nfl_data/walk_params.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'ΤΕΛΟΣ {time.time() - t0:.0f}″')


if __name__ == '__main__':
    main()
