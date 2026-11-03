"""NFL κοινο LOSO πλεγμα ΟΛΩΝ των βαρων της βασης (μηχανη v2 nfl_engine), QB «γνωστος στο ανοιγμα» (χωρις διαρροη).

Φασεις (καθε μια πανω στην καλυτερη της προηγουμενης):
  A  HL × PREV × λ επιθεσης × λ αμυνας                       (σβησιμο, περσινο, μαζεμα)
  B  SoS (πληρης / 0.5 / 0.75 / 1.0 δυο-βηματων) × garbage time (cl/c05/c20/all) × ραμπα (−/4/8/16)
  C  QB: HLQ × N0 × M0
Αξιολογηση εκδοχης: συντελεστες τελικου μετασχηματισμου + K των win totals μετριουνται στις ΑΛΛΕΣ σεζον (LOSO 2016-25).
Επιλογη εκδοχης για τη σεζον S: με το LOSO σφαλμα των ΑΛΛΩΝ σεζον (εμφωλευμενο) → τιμιο σφαλμα ανα σεζον.
Χαντικαπ και συνολα επιλεγονται ΧΩΡΙΣΤΑ (οπως NBA: ξεχωριστη μηχανη συνολων).
Συγκριση με τη σημερινη βαση (τεστ 5, ιδιος QB ανοιγματος). Κριτηριο: RMSE καλυτερη σε ≥4/5 σεζον 2021-25.
  python nfl_grid.py          → ολες οι φασεις, αποτελεσματα σε nfl_data/grid_*.csv
"""
import itertools, pickle, os, sys, time
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_test as T
import nfl_test5 as T5

S10, S5 = list(range(2016, 2026)), list(range(2021, 2026))
KS = T5.KS
CACHE = 'nfl_data/cache/grid_feats.pkl'
sys.stdout.reconfigure(encoding='utf-8')


def frame(g, feats, qbf):
    cols = ['game_id', 'season', 'wk', 't', 'game_type', 'home_team', 'away_team', 'neutral', 'result', 'total',
            'spread_line', 'total_line', 'home_coach', 'away_coach', 'home_spread_odds', 'away_spread_odds',
            'over_odds', 'under_odds']
    f = g[cols].merge(feats, on='game_id').merge(qbf, on='game_id', how='left')
    f = f[(f.game_type == 'REG') & f.spread_line.notna()].copy()
    f['qb_d'] = f.home_qbadj.fillna(0) - f.away_qbadj.fillna(0)
    f['qb_s'] = f.home_qbadj.fillna(0) + f.away_qbadj.fillna(0)
    return T5.add_feats(f, g)


FM0 = ['EPA_diff', 'pts_diff', 'qb_d', 'SR_diff', 'st_net_diff']
FT0 = ['pts_sum', 'EPA_sum', 'plays_sum', 'qb_s', 'SR_sum']


def loso(f, kind):
    """LOSO προβλεψεις μιας εκδοχης (K win totals εμφωλευμενο για χαντικαπ). Επιστρεφει Series προβλεψεων."""
    y = 'result' if kind == 'm' else 'total'
    out = pd.Series(np.nan, index=f.index)
    hist = f[f.season <= 2025]
    for S in range(2016, 2027):
        tr = hist[hist.season != S]
        te = f.season == S
        if kind == 'm':
            best = None
            for K in KS:
                F = FM0 + [f'wt_d_{K}']
                c = T.ols(tr, F, y)
                sc = np.mean((tr[y] - T.pred(tr, F, c)) ** 2)
                if best is None or sc < best[0]:
                    best = (sc, F, c)
            _, F, c = best
        else:
            F = FT0
            c = T.ols(tr, F, y)
        out[te] = T.pred(f[te], F, c)
    return out


def season_mse(f, pred, kind):
    y = f['result'] if kind == 'm' else f['total']
    e = (y - pred) ** 2
    return e.groupby(f.season).mean()


def nested(results, kind):
    """results: {name: (f, pred)}. Για καθε σεζον διαλεγει εκδοχη με το μεσο LOSO MSE των αλλων σεζον."""
    mse = pd.DataFrame({k: season_mse(f, p, kind) for k, (f, p) in results.items()})
    pick, rm = {}, {}
    for S in mse.index:
        other = [s for s in S10 if s != S]
        k = mse.loc[other].mean().idxmin()
        pick[S] = k
        rm[S] = np.sqrt(mse.loc[S, k])
    return pd.Series(rm), pick, mse


def show(lab, base_rm, rm, pick):
    b5 = sum(rm[s] < base_rm[s] for s in S5)
    b10 = sum(rm[s] < base_rm[s] for s in S10)
    tot = lambda r, ss: np.sqrt(np.mean([r[s] ** 2 for s in ss]))
    print(f'  {lab}: RMSE 2016-25 {tot(base_rm, S10):.3f} → {tot(rm, S10):.3f} · καλυτερη 2021-25 {b5}/5 · 2016-25 {b10}/10 · 2026 {base_rm.get(2026, np.nan):.3f} → {rm.get(2026, np.nan):.3f}')
    picks = pd.Series(pick).value_counts()
    print(f'     επιλογες: {dict(picks.head(3))}')


def main():
    t0 = time.time()
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    qb_default = Q.qb_features(g, q, HLQ=40, N0=300, M0=-0.15, target=tg)
    cache = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else {}

    def get(cfg, win='cl'):
        key = (tuple(sorted(cfg.items())), win)
        if key not in cache:
            cache[key] = E.build(g, off, cfg, win)
        return cache[key]

    def evaluate(cfgs, qbf=qb_default):
        R = {}
        for name, (cfg, win) in cfgs.items():
            f = frame(g, get(cfg, win), qbf)
            R[name] = (f, loso(f, 'm'), loso(f, 't'))
        pickle.dump(cache, open(CACHE, 'wb'))
        return R

    # σημερινη βαση (τεστ 5) με QB ανοιγματος
    base_cfg = dict(HL=16, PREV=0.6, lam_o=3, lam_d=3)
    RB = evaluate({'base': (base_cfg, 'cl')})
    fb, pm_b, pt_b = RB['base']
    base_m = np.sqrt(season_mse(fb, pm_b, 'm'))
    base_t = np.sqrt(season_mse(fb, pt_b, 't'))
    print(f'ΒΑΣΗ (τεστ 5, QB ανοιγματος): χαντ RMSE 2016-25 {np.sqrt(np.mean(base_m[S10] ** 2)):.3f} · συνολα {np.sqrt(np.mean(base_t[S10] ** 2)):.3f}', flush=True)

    # ---- Φαση A
    A = {}
    for hl, pv, lo, ld in itertools.product([8, 12, 16, 24, 32], [0.4, 0.6, 0.8], [1, 3, 8], [1, 3, 8]):
        A[f'HL{hl}_P{pv}_o{lo}_d{ld}'] = (dict(HL=hl, PREV=pv, lam_o=lo, lam_d=ld), 'cl')
    RA = evaluate(A)
    print(f'\n=== ΦΑΣΗ A: {len(A)} εκδοχες ({time.time() - t0:.0f}″) ===', flush=True)
    out = {}
    for kind, base_rm, lab in (('m', base_m, 'ΧΑΝΤΙΚΑΠ'), ('t', base_t, 'ΣΥΝΟΛΑ')):
        rm, pick, mse = nested({k: (v[0], v[1] if kind == 'm' else v[2]) for k, v in RA.items()}, kind)
        show(lab, base_rm, rm, pick)
        best = mse.loc[S10].mean().idxmin()
        print(f'     καλυτερη συνολικα: {best} · top5:', list(mse.loc[S10].mean().sort_values().index[:5]))
        mse.to_csv(f'nfl_data/grid_A_{kind}.csv')
        out[kind] = (best, rm, pick)
    # ---- Φαση B πανω στην καλυτερη A (χωριστα για χαντ/συνολα)
    for kind, lab in (('m', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
        bcfg = A[out[kind][0]][0]
        B = {}
        for sos, win, ramp in itertools.product([None, 0.5, 0.75, 1.0], ['cl', 'c05', 'c20', 'all'], [None, 4, 8, 16]):
            c = dict(bcfg)
            if sos is not None:
                c['sos'] = sos
            if ramp is not None:
                c['ramp'] = ramp
            B[f'sos{sos}_{win}_r{ramp}'] = (c, win)
        RBB = evaluate(B)
        rm, pick, mse = nested({k: (v[0], v[1] if kind == 'm' else v[2]) for k, v in RBB.items()}, kind)
        print(f'\n=== ΦΑΣΗ B {lab}: {len(B)} εκδοχες πανω σε {out[kind][0]} ({time.time() - t0:.0f}″) ===', flush=True)
        show(lab, base_m if kind == 'm' else base_t, rm, pick)
        best = mse.loc[S10].mean().idxmin()
        print(f'     καλυτερη: {best} · top5:', list(mse.loc[S10].mean().sort_values().index[:5]))
        # συνεισφορα καθε παραγοντα (μεσο MSE ανα τιμη)
        m = mse.loc[S10].mean()
        for fac, pos in (('SoS', 0), ('garbage', 1), ('ραμπα', 2)):
            grp = m.groupby([k.split('_')[pos] for k in m.index]).min()
            print(f'     {fac}: ' + ' · '.join(f'{k} {np.sqrt(v):.3f}' for k, v in grp.items()))
        mse.to_csv(f'nfl_data/grid_B_{kind}.csv')
        out[kind] = (best, B[best], rm, pick)
    # ---- Φαση C: QB πανω στις καλυτερες B
    for kind, lab in (('m', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
        cfg, win = out[kind][1]
        C = {}
        for hq, n0, m0 in itertools.product([20, 40, 80], [150, 300, 600], [-0.10, -0.15, -0.20]):
            qbf = Q.qb_features(g, q, HLQ=hq, N0=n0, M0=m0, HL=cfg['HL'], PREV=cfg['PREV'], target=tg)
            f = frame(g, get(cfg, win), qbf)
            C[f'Q{hq}_{n0}_{m0}'] = (f, loso(f, kind))
        rm, pick, mse = nested(C, kind)
        print(f'\n=== ΦΑΣΗ C {lab}: QB {len(C)} εκδοχες ({time.time() - t0:.0f}″) ===', flush=True)
        show(lab, base_m if kind == 'm' else base_t, rm, pick)
        best = mse.loc[S10].mean().idxmin()
        print(f'     καλυτερη: {best}')
        mse.to_csv(f'nfl_data/grid_C_{kind}.csv')
        out[kind] = out[kind][:2] + (best, rm)
    pickle.dump({k: v[:3] for k, v in out.items()}, open('nfl_data/grid_best.pkl', 'wb'))
    print(f'\nΤΕΛΟΣ ({time.time() - t0:.0f}″): χαντ {out["m"][:3]} · συνολα {out["t"][:3]}')


if __name__ == '__main__':
    main()
