"""NFL τεστ 2: μηχανη ομαδων (τεστ 1) + στρωμα QB που ξεκιναει, LOSO 2016-2025 (+2026 εκτος).

Χαρακτηριστικα: qb_d = διορθωση QB γηπ − φιλοξ (χαντικαπ), qb_s = αθροισμα (συνολα). Συντελεστες + παραμετροι QB
(HLQ/N0/M0) μετριουνται ΜΟΝΟ στις αλλες σεζον. Βαση ομαδων σταθερη = ρυθμιση που επελεξε το τεστ 1 σε ολες τις σεζον.
Δειχνει διπλα: τεστ 1 (χωρις QB) · τεστ 2 (με QB) · και μονο τα ματς «αλλαγης QB» (|διορθωση| ≥ 0.05 σε μια πλευρα).
"""
import itertools, json
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_test as T

BASE = dict(HL=16, PREV=0.6, LAM=dict(cl_epa=3, pts=3, plays=3))
QGRID = [dict(HLQ=h, N0=n, M0=m) for h, n, m in itertools.product([20, 40, 80], [100, 300], [-0.15, -0.05])]
FM2 = T.FM + ['qb_d']
FT2 = T.FT + ['qb_s']
CHG = 0.05


def run(feats, FMx, FTx, seasons):
    rows, preds = [], []
    for S in seasons:
        best = None
        for i, f in enumerate(feats):
            tr = f[(f.season != S) & (f.season <= 2025)]
            cm, ct = T.ols(tr, FMx, 'result'), T.ols(tr, FTx, 'total')
            sc = np.mean((tr.result - T.pred(tr, FMx, cm)) ** 2) + np.mean((tr.total - T.pred(tr, FTx, ct)) ** 2)
            if best is None or sc < best[0]:
                best = (sc, i, cm, ct)
        _, i, cm, ct = best
        te = feats[i][feats[i].season == S]
        te = te.assign(mp=T.pred(te, FMx, cm), tp=T.pred(te, FTx, ct), cfg=i)
        preds.append(te)
        rows.append((S, i, cm))
    return pd.concat(preds), rows


def summary(p, lab):
    out = []
    for S, d in p.groupby('season'):
        e = T.evaluate(d, d.mp.values, d.tp.values)
        e['season'] = S
        out.append(e)
    print(f'\n=== {lab} ===')
    print(f"{'σεζον':6} {'n':>4} | ΧΑΝΤ RMSE μοντ/αγορ  b   | ΣΥΝ RMSE μοντ/αγορ  b")
    for e in out:
        print(f"{e['season']:6} {e['n']:4} | {e['rmse_m']:6.2f} {e['rmse_m_mkt']:6.2f} {e['b_m']:+.2f} |"
              f" {e['rmse_t']:6.2f} {e['rmse_t_mkt']:6.2f} {e['b_t']:+.2f}")
    a = p[p.season <= 2025]
    e = T.evaluate(a, a.mp.values, a.tp.values)
    print(f"2016-25 ολα: ΧΑΝΤ RMSE {e['rmse_m']:.2f} vs αγορα {e['rmse_m_mkt']:.2f} b {e['b_m']:+.2f} · "
          f"ΣΥΝ RMSE {e['rmse_t']:.2f} vs {e['rmse_t_mkt']:.2f} b {e['b_t']:+.2f}")
    for k, lab2, thr in (('roi_m', 'ΧΑΝΤ', T.THR['spread']), ('roi_t', 'ΣΥΝ', T.THR['total'])):
        for t in thr:
            per = [(e['season'], *e[k][t]) for e in out]
            ten = [x for x in per if x[0] <= 2025]
            n, pl = sum(x[1] for x in ten), sum(x[2] for x in ten)
            n5, pl5 = sum(x[1] for x in ten[-5:]), sum(x[2] for x in ten[-5:])
            pos5 = sum(x[2] > 0 for x in ten[-5:])
            s26 = [x for x in per if x[0] == 2026]
            s26 = f"2026 {s26[0][1]} picks {s26[0][2]:+.1f}μ" if s26 else ''
            print(f"  {lab2} edge≥{t}: 2016-25 {n} ROI {100 * pl / max(n, 1):+.1f}% · 2021-25 {n5} ROI "
                  f"{100 * pl5 / max(n5, 1):+.1f}% ({pos5}/5) · {s26} | "
                  + ' '.join(f"{x[0] % 100}:{100 * x[2] / max(x[1], 1):+.0f}%" for x in per))


def main():
    g, off = M.load()
    q = Q.load_qb()
    base = M.build(g, off, **BASE)
    base = base[(base.game_type == 'REG') & base.spread_line.notna()]
    feats = []
    for p in QGRID:
        qf = Q.qb_features(g, q, HL=BASE['HL'], PREV=BASE['PREV'], **p)
        f = base.merge(qf, on='game_id', how='left')
        f['qb_d'] = f.home_qbadj.fillna(0) - f.away_qbadj.fillna(0)
        f['qb_s'] = f.home_qbadj.fillna(0) + f.away_qbadj.fillna(0)
        f['chg'] = (f[['home_qbadj', 'away_qbadj']].abs().max(axis=1) >= CHG)
        feats.append(f)
    seasons = list(range(2016, 2027))
    p1, _ = run([feats[0]], T.FM, T.FT, seasons)      # τεστ 1 (QB στηλες αγνοουνται)
    p2, rows = run(feats, FM2, FT2, seasons)
    print('επιλογες QB ανα σεζον:', [(S, QGRID[i]) for S, i, _ in rows][:1], '... ',
          sorted(set(i for _, i, _ in rows)))
    print('συντελεστες χαντικαπ (σταθ, epa, ποντοι, QB) 2025 fold:', np.round(rows[-2][2], 2))
    summary(p1, 'ΤΕΣΤ 1 — χωρις QB')
    summary(p2, 'ΤΕΣΤ 2 — με QB')
    ch = p2.chg.values
    summary(p1[ch], 'ΤΕΣΤ 1 — μονο ματς αλλαγης QB')
    summary(p2[ch], 'ΤΕΣΤ 2 — μονο ματς αλλαγης QB')
    p2.to_csv('nfl_data/test2_preds.csv', index=False)
    a = p2[p2.season <= 2025]
    print('\nβαρη [αγορα, μοντελο] χαντ:', np.linalg.lstsq(np.c_[a.spread_line, a.mp], a.result, rcond=None)[0].round(2),
          ' · ματς αλλαγης QB:', ch[p2.season <= 2025].sum(), 'απο', len(a))


if __name__ == '__main__':
    main()
