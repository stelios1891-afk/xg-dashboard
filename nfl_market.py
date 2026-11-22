"""NFL «δυναμεις της αγορας»: ratings ομαδων απο τις γραμμες ΚΛΕΙΣΙΜΑΤΟΣ των ΠΡΟΗΓΟΥΜΕΝΩΝ ματς (γνωστα στο ανοιγμα).

  χαντικαπ: spread_line = εδρα + R_γηπ − R_φιλ        (ridge, βαρος 0.5^(εβδομαδες/HLm) × PREVm ανα σεζον πισω)
  συνολα  : total_line  = μ + T_γηπ + T_φιλ
Για καθε ματς 2016+: mk_d = γραμμη που «θα εβαζε» η αγορα με τις δυναμεις της ως την προηγουμενη εβδομαδα,
mk_t = το ιδιο για συνολο. ΔΕΝ χρησιμοποιει τη γραμμη του ιδιου του ματς.
"""
import numpy as np
import pandas as pd


def market_feats(g, HLm=8, PREVm=0.6, lam=1.0):
    gg = g[g.spread_line.notna() & g.total_line.notna()].copy()
    teams = sorted(set(gg.home_team) | set(gg.away_team))
    ix = {k: i for i, k in enumerate(teams)}
    m = len(teams)
    out = []
    for t_now, wk in g[g.season >= 2016].groupby('t'):
        S = int(wk.season.iloc[0])
        x = gg[(gg.t < t_now) & (gg.season >= S - 1)]
        w = (0.5 ** ((t_now - x.t) / HLm) * PREVm ** (S - x.season)).values
        n = len(x)
        hi, ai = x.home_team.map(ix).values, x.away_team.map(ix).values
        hf = 1 - x.neutral.values
        sw = np.sqrt(w)
        # χαντικαπ
        X = np.zeros((n, 1 + m)); X[:, 0] = hf; X[np.arange(n), 1 + hi] += 1; X[np.arange(n), 1 + ai] -= 1
        A = X * sw[:, None]
        b = np.linalg.solve(A.T @ A + np.diag([1e-6] + [lam] * m), A.T @ (x.spread_line.values * sw))
        # συνολα
        Xt = np.zeros((n, 1 + m)); Xt[:, 0] = 1; Xt[np.arange(n), 1 + hi] += 1; Xt[np.arange(n), 1 + ai] += 1
        At = Xt * sw[:, None]
        bt = np.linalg.solve(At.T @ At + np.diag([1e-6] + [lam] * m), At.T @ (x.total_line.values * sw))
        for r in wk.itertuples():
            h, a = ix.get(r.home_team), ix.get(r.away_team)
            if h is None or a is None:
                continue
            out.append(dict(game_id=r.game_id, mk_d=b[0] * (1 - r.neutral) + b[1 + h] - b[1 + a],
                            mk_t=bt[0] + bt[1 + h] + bt[1 + a]))
    return pd.DataFrame(out)
