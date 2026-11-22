"""NFL επιπλεον δεδομενα για το τεστ 8 (αφετηρια + τυχη).

  python nfl_extra.py   → nfl_data/sb_odds.csv, nfl_data/roster_cont.csv, nfl_data/luck_games.csv

1) Αποδοσεις Super Bowl πριν τη σεζον (sportsoddshistory nfl-main, τελευταια στηλη «Preseason»):
   p = 1/αποδοση κανονικοποιημενο στη σεζον · sb = ln(p) − μεσος ln(p) της σεζον.
2) Συνεχεια ροστερ απο snap counts (nflverse):  για ομαδα T σεζον S, με τους παικτες του 1ου φετινου ματς της T:
   ret_o / ret_d = ποσοστο των περσινων φασεων επιθεσης/αμυνας της T που επαιξαν παικτες που ΕΙΝΑΙ ακομα στην T
   inc_o / inc_d = περσινες φασεις (σε αλλη ομαδα) των νεων παικτων, ως ποσοστο των περσινων φασεων της T
   (το ροστερ του 1ου ματς ειναι γνωστο λιγο πριν — προσεγγιση του «ροστερ πρεμιερας» του NBA W1)
3) Τυχη ανα ομαδα-ματς (pbp): κλεψιματα (int/att), κοκκινη ζωνη (drives που εφτασαν ≤20 γιαρδες → TD),
   field goals (ευστοχα/προσπαθειες) — της ομαδας ΚΑΙ του αντιπαλου απεναντι της.
"""
import html, os, re, time, urllib.request
import numpy as np
import pandas as pd
import nfl_fetch as F
import nfl_model as M
import nfl_wintotals as W

D = M.D


def sb_odds():
    rows = []
    for y in range(2015, 2027):
        s = urllib.request.urlopen(urllib.request.Request(
            f'https://www.sportsoddshistory.com/nfl-main/?y={y}&sa=nfl&a=sb', headers={'User-Agent': 'Mozilla/5.0'}),
            timeout=60).read().decode('utf-8', 'ignore')
        t = re.findall(r'<table.*?</table>', s, re.S)[0]
        for r in re.findall(r'<tr.*?</tr>', t, re.S)[2:]:
            c = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, re.S)]
            if not c or c[0] not in W.NAMES:
                continue
            odds = [x for x in c[1:] if re.fullmatch(r'[+-]\d+', x)]
            if not odds:
                continue
            a = float(odds[-1])
            dec = 1 + a / 100 if a > 0 else 1 + 100 / abs(a)
            rows.append(dict(season=y, team=W.NAMES[c[0]], sb_odds=odds[-1], p_raw=1 / dec))
        time.sleep(2)
    d = pd.DataFrame(rows)
    d['p'] = d.p_raw / d.groupby('season').p_raw.transform('sum')
    d['sb'] = np.log(d.p) - d.groupby('season').p.transform(lambda v: np.log(v).mean())
    d.to_csv(os.path.join(D, 'sb_odds.csv'), index=False)
    print('SB odds:', d.groupby('season').size().to_dict())


def roster_cont():
    sn = pd.concat([pd.read_csv(os.path.join(D, 'cache', 'snaps', f'snap_{y}.csv')) for y in range(2015, 2027)])
    sn = sn[sn.game_type == 'REG']
    sn['team'] = sn.team.replace(M.RENAME)
    tot = sn.groupby(['season', 'team'])[['offense_snaps', 'defense_snaps']].sum()
    ps = sn.groupby(['season', 'pfr_player_id', 'team'])[['offense_snaps', 'defense_snaps']].sum().reset_index()
    first_wk = sn.groupby(['season', 'team']).week.min().rename('w0')
    s1 = sn.merge(first_wk, on=['season', 'team'])
    s1 = s1[s1.week == s1.w0][['season', 'team', 'pfr_player_id']].drop_duplicates()
    rows = []
    for (S, T), grp in s1.groupby(['season', 'team']):
        if (S - 1, T) not in tot.index:
            continue
        ids = set(grp.pfr_player_id)
        last = ps[ps.season == S - 1]
        same = last[(last.team == T) & last.pfr_player_id.isin(ids)]
        new = last[(last.team != T) & last.pfr_player_id.isin(ids - set(last[last.team == T].pfr_player_id))]
        to, td = tot.loc[(S - 1, T)]
        rows.append(dict(season=S, team=T, ret_o=same.offense_snaps.sum() / to, ret_d=same.defense_snaps.sum() / td,
                         inc_o=new.offense_snaps.sum() / to, inc_d=new.defense_snaps.sum() / td))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(D, 'roster_cont.csv'), index=False)
    print('συνεχεια ροστερ:', d.groupby('season').size().to_dict())
    print(d.describe().round(3).loc[['mean', 'std', 'min', 'max']])


def luck_games():
    cols = ['game_id', 'posteam', 'defteam', 'drive', 'yardline_100', 'touchdown', 'td_team', 'interception',
            'pass_attempt', 'field_goal_result', 'play_type', 'sack']
    parts = []
    for y in range(2015, 2027):
        p = pd.read_csv(os.path.join(F.CACHE, f'pbp_{y}.csv.gz'), usecols=cols, low_memory=False)
        p = p[p.posteam.notna()]
        pa = p[(p.pass_attempt == 1) & (p.sack != 1)].groupby(['game_id', 'posteam']).agg(
            att=('pass_attempt', 'size'), ints=('interception', 'sum'))
        fg = p[p.play_type == 'field_goal'].groupby(['game_id', 'posteam']).agg(
            fga=('field_goal_result', 'size'), fgm=('field_goal_result', lambda s: (s == 'made').sum()))
        dr = p.groupby(['game_id', 'posteam', 'drive']).agg(minyd=('yardline_100', 'min'),
                                                            td=('td_team', lambda s: 0))
        tdd = p[(p.touchdown == 1) & (p.td_team == p.posteam)].groupby(['game_id', 'posteam', 'drive']).size().rename('tdn')
        dr = dr.join(tdd).fillna({'tdn': 0})
        rz = dr[dr.minyd <= 20].groupby(['game_id', 'posteam']).agg(rz=('minyd', 'size'), rz_td=('tdn', lambda s: (s > 0).sum()))
        a = pa.join(fg, how='outer').join(rz, how='outer').fillna(0).reset_index().rename(columns={'posteam': 'team'})
        a.insert(1, 'season', y)
        parts.append(a)
    d = pd.concat(parts)
    d['team'] = d.team.replace(M.RENAME)
    # αντιπαλος απεναντι: οτι εκανε ο αντιπαλος στο ιδιο ματς
    g = pd.read_csv(os.path.join(D, 'team_games.csv'))[['game_id', 'team', 'opp']]
    g['team'], g['opp'] = g.team.replace(M.RENAME), g.opp.replace(M.RENAME)
    d = d.merge(g, on=['game_id', 'team'], how='left')
    o = d[['game_id', 'team', 'att', 'ints', 'fga', 'fgm', 'rz', 'rz_td']].rename(
        columns=lambda c: c if c == 'game_id' else ('opp' if c == 'team' else 'o_' + c))
    d = d.merge(o, on=['game_id', 'opp'], how='left')
    d.to_csv(os.path.join(D, 'luck_games.csv'), index=False)
    print('τυχη:', len(d), 'ομαδα-ματς · μεσα: INT %.3f RZ-TD %.3f FG %.3f' % (
        d.ints.sum() / d.att.sum(), d.rz_td.sum() / d.rz.sum(), d.fgm.sum() / d.fga.sum()))


if __name__ == '__main__':
    sb_odds()
    roster_cont()
    luck_games()
