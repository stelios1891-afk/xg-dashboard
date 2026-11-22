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


def _solve(x, w, stat, teams, lam_o, lam_d, home=True, pri=None, venue=False):
    covs = venue if isinstance(venue, (list, tuple)) else (['dome'] if venue else [])
    """pri: (dict ομαδα→στοχος επιθεσης, dict ομαδα→στοχος αμυνας) — μαζεμα προς αυτους αντι για 0."""
    ix = {k: i for i, k in enumerate(teams)}
    n, m = len(x), len(teams)
    y = x[stat].values.astype(float)
    ok = ~np.isnan(y)
    X = np.zeros((n, 2 + 2 * m + len(covs)))
    X[:, 0] = 1
    X[:, 1] = x.home.values if home else 0
    X[np.arange(n), 2 + x.team.map(ix).values] = 1
    X[np.arange(n), 2 + m + x.opp.map(ix).values] = 1
    for j, c in enumerate(covs):                     # γηπεδο/καιρος: ξεχωριστοι οροι → οι δυναμεις «καθαριζουν»
        X[:, 2 + 2 * m + j] = x[c].values
    sw = np.sqrt(w)
    A, b = X[ok] * sw[ok, None], y[ok] * sw[ok]
    P = np.diag([0, 1e-6] + [lam_o] * m + [lam_d] * m + [1e-6] * len(covs))
    rhs = A.T @ b
    if pri is not None:
        tgt = np.r_[0, 0, [pri[0].get(t, 0) for t in teams], [pri[1].get(t, 0) for t in teams], [0] * len(covs)]
        rhs = rhs + P @ tgt
    beta = np.linalg.solve(A.T @ A + P, rhs)
    return beta, ix, y, ok


def fit(off, t_now, S, HL=16, PREV=0.6, lam_o=3, lam_d=3, stats=('cl_epa', 'pts', 'plays', 'cl_sr', 'st_net'),
        sos=None, ramp=None, post=True, nseas=2, HLp=None, home=True, prior=None, teamw=None, venue=False):
    """post: μετρανε τα playoffs · nseas: ποσες προηγουμενες σεζον · HLp: ξεχωριστο σβησιμο των ΠΕΡΣΙΝΩΝ καθως
    προχωραει η φετινη (None = ιδιο με τα φετινα) · home=False: χωρις εδρα στα ratings (σταθερη εδρα μονο στον τελικο)."""
    x = off[(off.t < t_now) & (off.season >= S - nseas)]
    if not post:
        x = x[(x.t - (x.season - 2015) * 30) <= 18]
    if ramp is not None:
        cur = x[x.season == S]
        prev = x[x.season < S]
        return _ramp(cur, prev, t_now, S, HL, PREV, lam_o, lam_d, stats, sos, ramp)
    if HLp is None:
        w = (0.5 ** ((t_now - x.t) / HL) * PREV ** (S - x.season)).values
    else:
        t0 = (S - 2015) * 30 + 1                                   # αρχη φετινης σεζον
        tend = (x.season - 2015) * 30 + 22                         # τελος της σεζον του καθε ματς
        cur = (x.season == S).values
        wp = PREV ** (S - x.season) * 0.5 ** ((tend - x.t) / HL) * 0.5 ** (max(0, t_now - t0) / HLp)
        w = np.where(cur, 0.5 ** ((t_now - x.t) / HL), wp)
    w = np.asarray(w, float)
    if teamw is not None:
        # βαρος ΠΡΟΗΓΟΥΜΕΝΩΝ σεζον ανα ομαδα: × πολλαπλασιαστης επιθεσης της ομαδας × αμυνας του αντιπαλου
        tw = teamw(S)
        if tw:
            old = (x.season < S).values
            mo = x.team.map(tw['o']).fillna(1.0).values
            md = x.opp.map(tw['d']).fillna(1.0).values
            w = np.where(old, w * mo * md, w)
    return _fit_block(x, w, stats, lam_o, lam_d, sos, home, prior(S) if callable(prior) else prior, venue)


def _fit_block(x, w, stats, lam_o, lam_d, sos, home=True, prior=None, venue=False):
    """prior: {stat: (dict επιθ., dict αμυν.)} — στοχοι μαζεματος (π.χ. απο win totals)· None = προς 0."""
    teams = sorted(set(x.team) | set(x.opp))
    out = {}
    for s in stats:
        pri = prior.get(s) if prior else None
        beta, ix, y, ok = _solve(x, w, s, teams, lam_o, lam_d, home, pri, venue)
        m = len(teams)
        mu, h = beta[0], beta[1]
        O, Dd = beta[2:2 + m], beta[2 + m:2 + 2 * m]
        covs = venue if isinstance(venue, (list, tuple)) else (['dome'] if venue else [])
        cadj = sum(beta[2 + 2 * m + j] * x[c].values for j, c in enumerate(covs)) if covs else 0
        if sos is not None:
            # μερικη διορθωση αντιπαλου: μεσος (y − μ − εδρα − s·αντιπαλος), μαζεμενος με λ
            ti, oi = x.team.map(ix).values, x.opp.map(ix).values
            res = y - mu - h * x.home.values - cadj
            ww = np.where(ok, w, 0)
            rr = np.where(ok, res, 0)
            po = np.array([pri[0].get(t, 0) for t in teams]) if pri else 0
            pd_ = np.array([pri[1].get(t, 0) for t in teams]) if pri else 0
            O2 = (np.bincount(ti, ww * (rr - sos * Dd[oi]), m) + lam_o * po) / (np.bincount(ti, ww, m) + lam_o)
            D2 = (np.bincount(oi, ww * (rr - sos * O[ti]), m) + lam_d * pd_) / (np.bincount(oi, ww, m) + lam_d)
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
