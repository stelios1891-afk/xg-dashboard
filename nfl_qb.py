"""NFL στρωμα QB.

  python nfl_qb.py      → nfl_data/qb_games.csv (ανα ματς-ομαδα-παικτη: φασεις QB & αθροισμα qb_epa, 2010+)

Φαση QB = καθε dropback (πασα, σακ, scramble) + σχεδιασμενο τρεξιμο του ιδιου του QB. qb_epa = EPA της φασης
(στις πασες μετραει και το YAC). Αξια QB πριν το ματς = σταθμισμενος μεσος EPA/φαση ολων των προηγουμενων φασεων του
(μισο βαρος καθε HLQ εβδομαδες), μαζεμενος προς «αναπληρωματικο» επιπεδο M0 με N0 φασεις.
Διορθωση ματς = αξια QB που ξεκιναει − μεση αξια των QB που ξεκινησαν στα ματς απ' οπου βγηκε το rating της ομαδας.
"""
import os
import numpy as np
import pandas as pd
import nfl_fetch as F
import nfl_model as M

QB_COLS = ['game_id', 'season', 'season_type', 'week', 'posteam', 'play_type', 'qb_dropback', 'qb_kneel', 'qb_spike',
           'id', 'rusher_player_id', 'qb_epa', 'wp']


def build_qb_games():
    parts = []
    for y in range(2010, 2027):
        f = os.path.join(F.CACHE, f'pbp_{y}.csv.gz')
        if not os.path.exists(f):
            open(f, 'wb').write(F.get(F.PBP_URL.format(y=y)))
        p = pd.read_csv(f, usecols=QB_COLS, low_memory=False)
        p = p[p.qb_epa.notna() & (p.qb_kneel != 1) & (p.qb_spike != 1)]
        db = p[p.qb_dropback == 1]
        qbs = set(db.id.dropna())
        run = p[(p.play_type == 'run') & (p.qb_dropback != 1) & p.rusher_player_id.isin(qbs)].copy()
        run['id'] = run.rusher_player_id
        x = pd.concat([db, run])
        x = x[x.id.notna()]
        a = x.groupby(['game_id', 'posteam', 'id']).agg(n=('qb_epa', 'size'), epa=('qb_epa', 'sum')).reset_index()
        a.insert(1, 'season', y)
        parts.append(a)
        print(y, len(a))
    q = pd.concat(parts).rename(columns={'posteam': 'team', 'id': 'qb'})
    q['team'] = q.team.replace(M.RENAME)
    q.to_csv(os.path.join(M.D, 'qb_games.csv'), index=False)


def load_qb():
    q = pd.read_csv(os.path.join(M.D, 'qb_games.csv'))
    g = pd.read_csv(os.path.join(M.D, 'games.csv'), low_memory=False, usecols=['game_id', 'season', 'game_type', 'week'])
    g['wk'] = np.where(g.game_type == 'REG', g.week, g.game_type.map(M.POST_WEEK))
    g['t'] = (g.season - 2015) * 30 + g.wk
    return q.merge(g[['game_id', 't']], on='game_id')


def qb_values(q, t_now, HLQ, N0, M0):
    x = q[q.t < t_now]
    w = 0.5 ** ((t_now - x.t) / HLQ)
    s = pd.DataFrame({'qb': x.qb, 'we': w * x.epa, 'wn': w * x.n}).groupby('qb').sum()
    v = (s.we + N0 * M0) / (s.wn + N0)
    return v.to_dict()


def qb_features(g, q, HLQ=40, N0=200, M0=-0.10, HL=16, PREV=0.6, target=None):
    """Για καθε ματς 2016+: διορθωση QB γηπεδουχου/φιλοξενουμενου (EPA/φαση· ο μετασχηματισμος σε ποντους στο τεστ).
    target: {(game_id, ομαδα): qb_id} για να χρησιμοποιηθει αλλος QB απο αυτον που ξεκινησε (π.χ. «γνωστος στο ανοιγμα»)."""
    starts = pd.concat([g[['game_id', 'season', 't', 'home_team', 'home_qb_id']].set_axis(['game_id', 'season', 't', 'team', 'qb'], axis=1),
                        g[['game_id', 'season', 't', 'away_team', 'away_qb_id']].set_axis(['game_id', 'season', 't', 'team', 'qb'], axis=1)])
    starts = starts[starts.qb.notna()]
    played = starts[starts.game_id.isin(g.loc[g.result.notna(), 'game_id'])]
    res = []
    for t_now, wk in g[(g.season >= 2016)].groupby('t'):
        S = int(wk.season.iloc[0])
        V = qb_values(q, t_now, HLQ, N0, M0)
        win = played[(played.t < t_now) & (played.season >= S - 2)]
        ww = 0.5 ** ((t_now - win.t) / HL) * PREV ** (S - win.season)
        base = pd.DataFrame({'team': win.team, 'w': ww, 'wv': ww * win.qb.map(lambda k: V.get(k, M0))}).groupby('team').sum()
        base = (base.wv / base.w).to_dict()
        for r in wk.itertuples():
            f = {'game_id': r.game_id}
            for side in ('home', 'away'):
                tm, qb = getattr(r, f'{side}_team'), getattr(r, f'{side}_qb_id')
                if target is not None:
                    qb = target.get((r.game_id, tm), qb)
                v = V.get(qb, M0) if isinstance(qb, str) else np.nan
                f[f'{side}_qbv'], f[f'{side}_qbadj'] = v, v - base.get(tm, M0)
            res.append(f)
    return pd.DataFrame(res)


if __name__ == '__main__':
    build_qb_games()
