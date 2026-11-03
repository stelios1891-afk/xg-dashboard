"""NFL μηχανη v2 — ολα τα βαρη ρυθμιζομενα (για κοινο LOSO πλεγμα, nfl_grid.py).

Ratings ανα εβδομαδα με σταθμισμενη ridge (οπως nfl_model), με επιπλεον:
  lam_o / lam_d : ΧΩΡΙΣΤΟ μαζεμα επιθεσης και αμυνας (NBA: επιθεση .5 / αμυνα .25 στα συνολα)
  sos           : None = πληρης διορθωση αντιπαλου (ridge)· αριθμος s → μερικη (y − s·δυναμη αντιπαλου), δευτερο βημα
  win           : ορια garbage time για EPA/SR ('cl' 0.1-0.9, 'c05' 0.05-0.95, 'c20' 0.2-0.8, 'all' ολες οι φασεις)
  ramp          : None = εκθετικο σβησιμο σε ολες τις σεζον· K → φετινο rating (μονο φετινα ματς) με βαρος n/(n+K)
                  και τελικο περσινο × PREV με K/(n+K) (ποδοσφαιρο K=8)
QB: target='actual' (QB που ξεκινησε) ή 'open' (QB του προηγουμενου ματς της ομαδας = γνωστος στο ανοιγμα εβδομαδας).
"""
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q

WIN = {'cl': ('cl_epa', 'cl_sr'), 'c05': ('c05_epa', 'c05_sr'), 'c20': ('c20_epa', 'c20_sr'), 'all': ('epa', 'sr')}


def _solve(x, w, stat, teams, lam_o, lam_d, home=True):
    ix = {k: i for i, k in enumerate(teams)}
    n, m = len(x), len(teams)
    y = x[stat].values.astype(float)
    ok = ~np.isnan(y)
    X = np.zeros((n, 2 + 2 * m))
    X[:, 0] = 1
    X[:, 1] = x.home.values if home else 0
    X[np.arange(n), 2 + x.team.map(ix).values] = 1
    X[np.arange(n), 2 + m + x.opp.map(ix).values] = 1
    sw = np.sqrt(w)
    A, b = X[ok] * sw[ok, None], y[ok] * sw[ok]
    P = np.diag([0, 1e-6] + [lam_o] * m + [lam_d] * m)
    beta = np.linalg.solve(A.T @ A + P, A.T @ b)
    return beta, ix, y, ok


def fit(off, t_now, S, HL=16, PREV=0.6, lam_o=3, lam_d=3, stats=('cl_epa', 'pts', 'plays', 'cl_sr', 'st_net'),
        sos=None, ramp=None):
    x = off[(off.t < t_now) & (off.season >= S - 2)]
    if ramp is not None:
        cur = x[x.season == S]
        prev = x[x.season < S]
        return _ramp(cur, prev, t_now, S, HL, PREV, lam_o, lam_d, stats, sos, ramp)
    w = (0.5 ** ((t_now - x.t) / HL) * PREV ** (S - x.season)).values
    return _fit_block(x, w, stats, lam_o, lam_d, sos)


def _fit_block(x, w, stats, lam_o, lam_d, sos):
    teams = sorted(set(x.team) | set(x.opp))
    out = {}
    for s in stats:
        beta, ix, y, ok = _solve(x, w, s, teams, lam_o, lam_d)
        m = len(teams)
        mu, h = beta[0], beta[1]
        O, Dd = beta[2:2 + m], beta[2 + m:]
        if sos is not None:
            # μερικη διορθωση αντιπαλου: μεσος (y − μ − εδρα − s·αντιπαλος), μαζεμενος με λ
            ti, oi = x.team.map(ix).values, x.opp.map(ix).values
            res = y - mu - h * x.home.values
            ww = np.where(ok, w, 0)
            rr = np.where(ok, res, 0)
            O2 = np.bincount(ti, ww * (rr - sos * Dd[oi]), m) / (np.bincount(ti, ww, m) + lam_o)
            D2 = np.bincount(oi, ww * (rr - sos * O[ti]), m) / (np.bincount(oi, ww, m) + lam_d)
            O, Dd = O2, D2
        out[s] = (mu, h, dict(zip(teams, O)), dict(zip(teams, Dd)))
    return out


_PREV_CACHE = {}


def _ramp(cur, prev, t_now, S, HL, PREV, lam_o, lam_d, stats, sos, K):
    key = (S, HL, PREV, lam_o, lam_d, stats, sos)
    if key not in _PREV_CACHE:
        # τελικο περσινο rating (ολα τα ματς της περσινης σεζον, με σβησιμο απο το τελος της)
        p = prev[prev.season == S - 1]
        tend = p.t.max() + 1
        _PREV_CACHE[key] = _fit_block(p, (0.5 ** ((tend - p.t) / HL)).values, stats, lam_o, lam_d, sos)
    R0 = _PREV_CACHE[key]
    if len(cur) == 0:
        return {s: (mu, h, {k: v * PREV for k, v in O.items()}, {k: v * PREV for k, v in Dd.items()})
                for s, (mu, h, O, Dd) in R0.items()}
    R1 = _fit_block(cur, (0.5 ** ((t_now - cur.t) / HL)).values, stats, lam_o, lam_d, sos)
    n = cur.groupby('team').size().to_dict()
    out = {}
    for s in stats:
        mu1, h1, O1, D1 = R1[s]
        mu0, h0, O0, D0 = R0[s]
        teams = set(O1) | set(O0)
        a = {k: n.get(k, 0) / (n.get(k, 0) + K) for k in teams}
        O = {k: a[k] * O1.get(k, 0) + (1 - a[k]) * PREV * O0.get(k, 0) for k in teams}
        Dd = {k: a[k] * D1.get(k, 0) + (1 - a[k]) * PREV * D0.get(k, 0) for k in teams}
        out[s] = (mu1, h1, O, Dd)
    return out


def build(g, off, cfg, win='cl'):
    """Χαρακτηριστικα πριν απο καθε ματς 2016+ για μια ρυθμιση cfg (dict για fit)."""
    e, s = WIN[win]
    o = off.copy()
    o['EPA'], o['SR'] = o[e], o[s]
    res = []
    gg = g[(g.season >= 2016) & (g.result.notna() | (g.season == g.season.max()))]
    stats = ('EPA', 'pts', 'plays', 'SR', 'st_net')
    for t_now, wk in gg.groupby('t'):
        R = fit(o, t_now, int(wk.season.iloc[0]), stats=stats, **cfg)
        for r in wk.itertuples():
            f = M.features(R, r.home_team, r.away_team, r.neutral)
            f['game_id'] = r.game_id
            res.append(f)
    return pd.DataFrame(res)


def qb_open_targets(g):
    """QB «γνωστος στο ανοιγμα»: ο QB που ξεκινησε στο ΠΡΟΗΓΟΥΜΕΝΟ ματς της ομαδας την ιδια σεζον
    (1η αγωνιστικη: ο πραγματικος — συνηθως γνωστος απο το καλοκαιρι)."""
    lg = pd.concat([g[['game_id', 'season', 't', 'home_team', 'home_qb_id']].set_axis(['game_id', 'season', 't', 'team', 'qb'], axis=1),
                    g[['game_id', 'season', 't', 'away_team', 'away_qb_id']].set_axis(['game_id', 'season', 't', 'team', 'qb'], axis=1)])
    lg = lg.sort_values('t')
    lg['prev_qb'] = lg.groupby(['season', 'team']).qb.shift(1)
    lg['q'] = lg.prev_qb.fillna(lg.qb)
    return lg.set_index(['game_id', 'team']).q.to_dict()
