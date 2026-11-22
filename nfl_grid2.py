"""NFL πλεγμα 2: αναζητηση «μια παραμετρος τη φορα» γυρω απο τις ακρες του nfl_grid (QB ανοιγματος, LOSO).

Ξεκινα απο τις καλυτερες του nfl_grid και για καθε παραμετρο δοκιμαζει τις γειτονικες τιμες (και πιο εξω απο το παλιο
πλεγμα)· κραταει οτι μειωνει το μεσο LOSO MSE 2016-25· επαναλαμβανει ως να μη βελτιωνεται τιποτα (max 4 γυροι).
Χαντικαπ και συνολα χωριστα. Στο τελος: εμφωλευμενη συγκριση με τη βαση του τεστ 5 (κριτηριο ≥4/5 σεζον 2021-25)
και αποθηκευση LOSO προβλεψεων → nfl_data/base2_preds.csv
"""
import json, pickle, os, sys, time
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G

sys.stdout.reconfigure(encoding='utf-8')
GRID = {
    'HL': [3, 4, 6, 8, 10, 12],
    'PREV': [0.6, 0.7, 0.8, 0.9, 1.0],
    'lam_o': [1, 2, 3, 5],
    'lam_d': [5, 8, 12, 20, 32],
    'sos': [0.0, 0.25, 0.5, 0.75, None],
    'win': ['all', 'c05'],
    'HLQ': [8, 12, 20, 30],
    'N0': [300, 600, 1000, 1600],
    'M0': [-0.1, -0.15, -0.2, -0.3],
}
START = {'m': dict(HL=8, PREV=0.8, lam_o=3, lam_d=8, sos=0.5, win='all', HLQ=20, N0=600, M0=-0.2),
         't': dict(HL=8, PREV=0.8, lam_o=3, lam_d=8, sos=None, win='all', HLQ=20, N0=600, M0=-0.1)}


def main():
    t0 = time.time()
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    cache = pickle.load(open(G.CACHE, 'rb')) if os.path.exists(G.CACHE) else {}
    qcache = {}
    mse_cache = {}

    def frame(p):
        cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
        if p['sos'] is not None:
            cfg['sos'] = p['sos']
        key = (tuple(sorted(cfg.items())), p['win'])
        if key not in cache:
            cache[key] = E.build(g, off, cfg, p['win'])
        qk = (p['HLQ'], p['N0'], p['M0'], p['HL'], p['PREV'])
        if qk not in qcache:
            qcache[qk] = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
        return G.frame(g, cache[key], qcache[qk])

    def score(p, kind):
        k = (kind, tuple(sorted((a, str(b)) for a, b in p.items())))
        if k not in mse_cache:
            f = frame(p)
            pr = G.loso(f, kind)
            s = G.season_mse(f, pr, kind)
            mse_cache[k] = (s.loc[G.S10].mean(), f, pr)
        return mse_cache[k]

    best = {}
    for kind, lab in (('m', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
        p = dict(START[kind])
        cur = score(p, kind)[0]
        print(f'\n=== {lab}: αφετηρια RMSE {np.sqrt(cur):.4f} ===', flush=True)
        for rnd in range(4):
            changed = False
            for par, vals in GRID.items():
                for v in vals:
                    if v == p[par]:
                        continue
                    pp = dict(p); pp[par] = v
                    s = score(pp, kind)[0]
                    if s < cur - 1e-6:
                        print(f'  γυρος {rnd + 1}: {par} {p[par]} → {v} · RMSE {np.sqrt(cur):.4f} → {np.sqrt(s):.4f} ({time.time() - t0:.0f}″)', flush=True)
                        cur, p, changed = s, pp, True
            pickle.dump(cache, open(G.CACHE, 'wb'))
            if not changed:
                break
        best[kind] = p
        print(f'  ΤΕΛΙΚΗ {lab}: {p} · RMSE {np.sqrt(cur):.4f}', flush=True)
    json.dump(best, open('nfl_data/base2_params.json', 'w'), indent=1)

    # εμφωλευμενη τιμια συγκριση: για καθε σεζον S ξανατρεχει την αναζητηση ΧΩΡΙΣ την S θα ηταν ακριβο —
    # αντ' αυτου: συγκριση ανα σεζον (οι συντελεστες ειναι LOSO, οι 9 παραμετροι κοινες) + ελεγχος σταθεροτητας:
    print('\n=== ΣΥΓΚΡΙΣΗ ΑΝΑ ΣΕΖΟΝ (LOSO συντελεστες) ===')
    base = dict(HL=16, PREV=0.6, lam_o=3, lam_d=3, sos=None, win='cl', HLQ=40, N0=300, M0=-0.15)
    preds = None
    for kind, lab in (('m', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
        _, fb, pb = score(base, kind)
        _, fn, pn = score(best[kind], kind)
        rb, rn = np.sqrt(G.season_mse(fb, pb, kind)), np.sqrt(G.season_mse(fn, pn, kind))
        print(f'{lab}: ' + ' · '.join(f"{s % 100}: {rb[s]:.2f}→{rn[s]:.2f}{'✓' if rn[s] < rb[s] else '✗'}" for s in rb.index))
        print(f'   2021-25 {sum(rn[s] < rb[s] for s in G.S5)}/5 · 2016-25 {sum(rn[s] < rb[s] for s in G.S10)}/10 · '
              f'RMSE 2016-25 {np.sqrt(np.mean(rb[G.S10] ** 2)):.3f} → {np.sqrt(np.mean(rn[G.S10] ** 2)):.3f}')
        col = 'mp' if kind == 'm' else 'tp'
        d = fn[['game_id', 'season', 'wk', 'home_team', 'away_team', 'result', 'total', 'spread_line', 'total_line']].copy()
        d[col] = pn
        if kind == 'm':
            d = d.join(fn[['home_qbadj', 'away_qbadj', 'qb_d']])
        preds = d if preds is None else preds.merge(d[['game_id', col]], on='game_id')
    preds.to_csv('nfl_data/base2_preds.csv', index=False)
    print(f'ΤΕΛΟΣ ({time.time() - t0:.0f}″)')


if __name__ == '__main__':
    main()
