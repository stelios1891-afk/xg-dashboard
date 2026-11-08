"""NFL τεστ 1: μηχανη ομαδων (EPA + ποντοι + ρυθμος) vs γραμμη κλεισιματος, LOSO 2016-2025 (+2026 εκτος).

Για καθε σεζον-εξεταση: παραμετροι (HL/PREV/λ) ΚΑΙ συντελεστες χαντικαπ/συνολου μετριουνται ΜΟΝΟ στις αλλες σεζον.
Μετραμε: RMSE μοντελου vs αγορας · b = κλιση (πραγμ − γραμμη) πανω στο (μοντελο − γραμμη) · ROI picks με edge ≥ X ποντους
(πραγματικες αποδοσεις κλεισιματος nflverse, push = 0).  Μονο κανονικη περιοδος.
"""
import itertools, json, sys
import numpy as np
import pandas as pd
import nfl_model as M

GRID = [dict(HL=hl, PREV=pv, LAM=dict(cl_epa=lm, pts=lm, plays=lm))
        for hl, pv, lm in itertools.product([16, 26, 40], [0.6, 0.8], [1, 3])]
FM = ['cl_epa_diff', 'pts_diff']
FT = ['pts_sum', 'cl_epa_sum', 'plays_sum']
THR = dict(spread=[1.5, 2.5, 3.5], total=[2, 3, 4])


def dec(a):
    a = np.where(pd.isna(a), -110, a)
    return np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))


def ols(df, F, y):
    X = np.c_[np.ones(len(df)), df[F].values]
    return np.linalg.lstsq(X, df[y].values, rcond=None)[0]


def pred(df, F, c):
    return np.c_[np.ones(len(df)), df[F].values] @ c


def roi(edge, actual_minus_line, odds_pos, odds_neg, thr):
    """edge>0 → ποντος στη θετικη πλευρα (γηπεδουχος / over)."""
    out = {}
    for t in thr:
        pick = np.abs(edge) >= t
        side = np.sign(edge[pick])
        r = actual_minus_line[pick] * side
        o = np.where(side > 0, odds_pos[pick], odds_neg[pick])
        pl = np.where(r > 0, o - 1, np.where(r < 0, -1, 0))
        out[t] = (int(pick.sum()), float(pl.sum()))
    return out


def evaluate(te, mp, tp):
    m_line, t_line = te.spread_line.values, te.total_line.values
    res, tot = te.result.values, te.total.values
    e = {}
    e['rmse_m'] = np.sqrt(np.mean((res - mp) ** 2)); e['rmse_m_mkt'] = np.sqrt(np.mean((res - m_line) ** 2))
    e['rmse_t'] = np.sqrt(np.mean((tot - tp) ** 2)); e['rmse_t_mkt'] = np.sqrt(np.mean((tot - t_line) ** 2))
    e['b_m'] = np.polyfit(mp - m_line, res - m_line, 1)[0]
    e['b_t'] = np.polyfit(tp - t_line, tot - t_line, 1)[0]
    e['roi_m'] = roi(mp - m_line, res - m_line, dec(te.home_spread_odds), dec(te.away_spread_odds), THR['spread'])
    e['roi_t'] = roi(tp - t_line, tot - t_line, dec(te.over_odds), dec(te.under_odds), THR['total'])
    e['n'] = len(te)
    return e


def main():
    g, off = M.load()
    feats = []
    for i, p in enumerate(GRID):
        f = M.build(g, off, **p)
        f = f[(f.game_type == 'REG') & f.spread_line.notna()]
        feats.append(f)
        print('config', i, p['HL'], p['PREV'], p['LAM']['pts'], len(f), file=sys.stderr)
    seasons = list(range(2016, 2027))
    rows, preds = [], []
    for S in seasons:
        best = None
        for i, f in enumerate(feats):
            tr = f[(f.season != S) & (f.season <= 2025)]
            cm, ct = ols(tr, FM, 'result'), ols(tr, FT, 'total')
            # επιλογη παραμετρων με RMSE εντος των αλλων σεζον (χαντικαπ+συνολο)
            sc = np.mean((tr.result - pred(tr, FM, cm)) ** 2) + np.mean((tr.total - pred(tr, FT, ct)) ** 2)
            if best is None or sc < best[0]:
                best = (sc, i, cm, ct)
        _, i, cm, ct = best
        te = feats[i][feats[i].season == S]
        te = te.assign(mp=pred(te, FM, cm), tp=pred(te, FT, ct))
        preds.append(te[['game_id', 'season', 'wk', 'home_team', 'away_team', 'spread_line', 'total_line', 'result', 'total',
                         'home_spread_odds', 'away_spread_odds', 'over_odds', 'under_odds', 'mp', 'tp']])
        e = evaluate(te, te.mp.values, te.tp.values)
        e['season'], e['cfg'] = S, i
        rows.append(e)
    pd.concat(preds).to_csv('nfl_data/test1_preds.csv', index=False)
    json.dump(rows, open('nfl_data/test1_results.json', 'w'), default=float, indent=1)
    print(f"{'σεζον':6} {'n':>4} {'cfg':>3} | ΧΑΝΤΙΚΑΠ RMSE μοντ/αγορ   b  | ΣΥΝΟΛΑ RMSE μοντ/αγορ   b")
    for e in rows:
        print(f"{e['season']:6} {e['n']:4} {e['cfg']:3} | {e['rmse_m']:6.2f} {e['rmse_m_mkt']:6.2f} {e['b_m']:+.2f} |"
              f" {e['rmse_t']:6.2f} {e['rmse_t_mkt']:6.2f} {e['b_t']:+.2f}")
    for k, lab in (('roi_m', 'ΧΑΝΤΙΚΑΠ'), ('roi_t', 'ΣΥΝΟΛΑ')):
        for t in THR['spread' if k == 'roi_m' else 'total']:
            per = [(e['season'], *e[k][t]) for e in rows]
            ten = [p for p in per if p[0] <= 2025]
            n, pl = sum(p[1] for p in ten), sum(p[2] for p in ten)
            n5, pl5 = sum(p[1] for p in ten[-5:]), sum(p[2] for p in ten[-5:])
            pos5 = sum(p[2] > 0 for p in ten[-5:])
            s26 = per[-1]
            print(f"{lab} edge≥{t}: 2016-25 {n} picks ROI {100 * pl / max(n, 1):+.1f}% · 2021-25 {n5} ROI "
                  f"{100 * pl5 / max(n5, 1):+.1f}% ({pos5}/5 θετικες) · 2026 {s26[1]} picks {s26[2]:+.1f}μ  | ανα σεζον: "
                  + ' '.join(f"{p[0] % 100}:{100 * p[2] / max(p[1], 1):+.0f}%" for p in per))


if __name__ == '__main__':
    main()
