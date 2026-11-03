"""NFL δεδομενα (nflverse, δωρεαν).

  python nfl_fetch.py            → ολες οι σεζον 2015..τρεχουσα (pbp cache: δεν ξανακατεβαζει παλιες)
  python nfl_fetch.py 2026       → μονο μια σεζον (φρεσκο κατεβασμα)

Βγαζει:
  nfl_data/games.csv        προγραμμα/σκορ/γραμμες κλεισιματος (spread_line = ποντοι υπερ γηπεδουχου), QB, ξεκουραση, καιρος
  nfl_data/team_games.csv   μια γραμμη ανα ομαδα-ματς: EPA/φαση επιθεσης & αμυνας (pass+run, χωρις kneel/spike),
                            success rate, EPA πασας/τρεξιματος, και 'cl' εκδοχες μονο με wp 0.1-0.9 (χωρις garbage time)
"""
import io, os, sys, urllib.request
import pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
CACHE = os.path.join(D, 'cache')
GAMES_URL = 'https://github.com/nflverse/nfldata/raw/master/data/games.csv'
PBP_URL = 'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{y}.csv.gz'
COLS = ['game_id', 'season', 'season_type', 'week', 'posteam', 'defteam', 'play_type', 'epa', 'success',
        'pass', 'rush', 'qb_kneel', 'qb_spike', 'wp', 'fumble', 'fumble_lost']


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def pbp(y, fresh=False):
    f = os.path.join(CACHE, f'pbp_{y}.csv.gz')
    if fresh or not os.path.exists(f):
        open(f, 'wb').write(get(PBP_URL.format(y=y)))
    return pd.read_csv(f, usecols=COLS, low_memory=False)


def agg(p):
    p = p[p.play_type.isin(['pass', 'run']) & (p.qb_kneel != 1) & (p.qb_spike != 1) & p.epa.notna()].copy()
    p['cl'] = p.wp.between(0.1, 0.9)
    # «χωρις τυχη φαμπλ»: ολες οι φασεις με φαμπλ παιρνουν τον ιδιο μεσο EPA (ποιος παιρνει την μπαλα ≈ κορονα-γραμματα)
    fum = p.fumble == 1
    p['nf_epa'] = p.epa.where(~fum, p.loc[fum, 'epa'].mean())
    p['p_epa'] = p.epa.where(p['pass'] == 1)
    p['r_epa'] = p.epa.where(p['rush'] == 1)
    g = p.groupby(['game_id', 'posteam', 'defteam'])
    o = g.agg(plays=('epa', 'size'), epa=('epa', 'mean'), sr=('success', 'mean'),
              p_epa=('p_epa', 'mean'), r_epa=('r_epa', 'mean'), n_pass=('pass', 'sum'),
              nf_epa=('nf_epa', 'mean')).reset_index()
    c = p[p.cl].groupby(['game_id', 'posteam']).agg(cl_plays=('epa', 'size'), cl_epa=('epa', 'mean'),
                                                    cl_sr=('success', 'mean'),
                                                    cl_nf_epa=('nf_epa', 'mean'), cl_p_epa=('p_epa', 'mean'),
                                                    cl_r_epa=('r_epa', 'mean')).reset_index()
    o = o.merge(c, on=['game_id', 'posteam'], how='left')
    o = o.rename(columns={'posteam': 'team', 'defteam': 'opp'})
    # αμυνα = η επιθεση του αντιπαλου στο ιδιο ματς
    d = o[['game_id', 'team', 'plays', 'epa', 'sr', 'p_epa', 'r_epa', 'cl_plays', 'cl_epa', 'cl_sr', 'nf_epa',
           'cl_nf_epa', 'cl_p_epa', 'cl_r_epa']].rename(
        columns=lambda k: k if k == 'game_id' else ('opp' if k == 'team' else 'd_' + k))
    return o.merge(d, on=['game_id', 'opp'], how='left')


def main():
    os.makedirs(CACHE, exist_ok=True)
    g = pd.read_csv(io.BytesIO(get(GAMES_URL)), low_memory=False)
    g.to_csv(os.path.join(D, 'games.csv'), index=False)
    cur = int(g.loc[g.result.notna(), 'season'].max())
    years = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(2015, cur + 1))
    out = os.path.join(D, 'team_games.csv')
    old = pd.read_csv(out) if os.path.exists(out) and len(sys.argv) > 1 else None
    parts = []
    for y in years:
        a = agg(pbp(y, fresh=(y == cur or len(sys.argv) > 1)))
        a.insert(1, 'season', y)
        parts.append(a)
        print(y, len(a), 'ομαδα-ματς')
    tg = pd.concat(parts)
    if old is not None:
        tg = pd.concat([old[~old.season.isin(years)], tg])
    tg.sort_values(['season', 'game_id', 'team']).to_csv(out, index=False)
    print('games', len(g), '· team_games', len(tg))


if __name__ == '__main__':
    main()
