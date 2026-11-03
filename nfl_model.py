"""NFL μηχανη δυναμεων ομαδων (EPA ≈ το xG του NFL).

Για καθε εβδομαδα: σταθμισμενη ridge παλινδρομηση σε ΟΛΑ τα προηγουμενα ματς (χωρις διαρροη):
    y(ομαδα T επιτιθεται στην D) = μ + Επ_T + Αμ_D + εδρα
για 3 μεγεθη: EPA/φαση (χωρις garbage time), ποντοι, φασεις (ρυθμος).
Βαρος ματς = 0.5^(εβδομαδες πισω / HL) × PREV για καθε σεζον πισω.
Τα ratings μετατρεπονται σε χαντικαπ/συνολο με γραμμικους συντελεστες που μετριουνται σε αλλες σεζον (nfl_test.py).
"""
import os
import numpy as np
import pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
RENAME = {'OAK': 'LV', 'SD': 'LAC', 'STL': 'LA'}
POST_WEEK = {'WC': 19, 'DIV': 20, 'CON': 21, 'SB': 22}
STATS = ('cl_epa', 'pts', 'plays')


def load():
    g = pd.read_csv(os.path.join(D, 'games.csv'), low_memory=False)
    g = g[g.season >= 2015].copy()
    for c in ('home_team', 'away_team'):
        g[c] = g[c].replace(RENAME)
    g['wk'] = np.where(g.game_type == 'REG', g.week, g.game_type.map(POST_WEEK))
    g['t'] = (g.season - 2015) * 30 + g.wk          # χρονος σε «εβδομαδες» (8 κενες στο καλοκαιρι)
    g['neutral'] = (g.location == 'Neutral').astype(int)
    tg = pd.read_csv(os.path.join(D, 'team_games.csv'))
    for c in ('team', 'opp'):
        tg[c] = tg[c].replace(RENAME)
    # μια γραμμη ανα επιθεση: ομαδα, αντιπαλος, εδρα, EPA, ποντοι, φασεις
    rows = []
    for side, oth in (('home', 'away'), ('away', 'home')):
        x = g[['game_id', 'season', 't', 'neutral', f'{side}_team', f'{oth}_team', f'{side}_score']].copy()
        x.columns = ['game_id', 'season', 't', 'neutral', 'team', 'opp', 'pts']
        x['home'] = (1 - x.neutral) * (1 if side == 'home' else -1)
        rows.append(x)
    off = pd.concat(rows).merge(tg[['game_id', 'team', 'cl_epa', 'plays', 'epa']], on=['game_id', 'team'], how='left')
    off = off[off.pts.notna()]
    return g, off


def fit(off, t_now, season_now, HL=8.0, PREV=0.5, LAM=None):
    """Ratings με ματς πριν το t_now. Επιστρεφει {stat: (mu, h, {team: off}, {team: def})}."""
    LAM = LAM or dict(cl_epa=4.0, pts=4.0, plays=4.0)
    x = off[(off.t < t_now) & (off.season >= season_now - 2)]
    w = 0.5 ** ((t_now - x.t) / HL) * PREV ** (season_now - x.season)
    teams = sorted(set(x.team) | set(x.opp))
    ix = {k: i for i, k in enumerate(teams)}
    n, m = len(x), len(teams)
    X = np.zeros((n, 2 + 2 * m))
    X[:, 0] = 1
    X[:, 1] = x.home.values
    X[np.arange(n), 2 + x.team.map(ix).values] = 1
    X[np.arange(n), 2 + m + x.opp.map(ix).values] = 1
    sw = np.sqrt(w.values)
    out = {}
    for s in STATS:
        y = x[s].values.astype(float)
        ok = ~np.isnan(y)
        A = X[ok] * sw[ok, None]
        b = y[ok] * sw[ok]
        # ridge μονο στις ομαδες, κλιμακα με τη διασπορα του μεγεθους
        P = np.diag([0, 0] + [LAM[s]] * (2 * m)) * 1.0
        beta = np.linalg.solve(A.T @ A + P, A.T @ b)
        out[s] = (beta[0], beta[1], dict(zip(teams, beta[2:2 + m])), dict(zip(teams, beta[2 + m:])))
    return out


def features(R, home, away, neutral):
    """Αναμενομενα ανα πλευρα για ενα ματς απο τα ratings."""
    f = {}
    hf = 0 if neutral else 1
    for s, (mu, h, O, Dd) in R.items():
        eh = mu + h * hf + O.get(home, 0) + Dd.get(away, 0)
        ea = mu - h * hf + O.get(away, 0) + Dd.get(home, 0)
        f[f'{s}_diff'], f[f'{s}_sum'] = eh - ea, eh + ea
    return f


def build(g, off, **kw):
    """Χαρακτηριστικα (pre-match) για ολα τα ματς 2016+ — ενα fit ανα εβδομαδα."""
    res = []
    gg = g[(g.season >= 2016) & g.result.notna()]
    for t_now, wk in gg.groupby('t'):
        R = fit(off, t_now, int(wk.season.iloc[0]), **kw)
        for r in wk.itertuples():
            f = features(R, r.home_team, r.away_team, r.neutral)
            f['game_id'] = r.game_id
            res.append(f)
    return gg.merge(pd.DataFrame(res), on='game_id')
