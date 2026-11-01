"""
trendline.py — rolling average xGF/xGA/xGD ανα ομαδα (window 5 ή 10), + linear trend.

Πηγη: teamgame_inputs.csv (xg_model = xG ομαδας/ματς) + data json (id->name).
xGF = xg_model της ομαδας· xGA = xg_model του αντιπαλου στο ιδιο ματς (pairing on mid).
Σεζον: τελευταια πληρης (2526)· ανανεωση μολις μπουν φετινα αποτελεσματα.
"""
import os, json
import numpy as np
import pandas as pd
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASON_DEFAULT = '2526'

def _id2name(league, season):
    with open(os.path.join(ROOT, f'data_{league}_{season}.json'), encoding='utf-8') as fh:
        d = json.load(fh)
    m = {}
    for x in d.values():
        m[x['home']['id']] = x['home']['name']; m[x['away']['id']] = x['away']['name']
    return m

def team_matches(league, season=SEASON_DEFAULT):
    """{team_name: dict(tid, xgf=[...], xga=[...])} σε χρονολογικη σειρα."""
    TG = pd.read_csv(os.path.join(ROOT, 'teamgame_inputs.csv'))
    TG['season'] = TG['season'].astype(str)
    TG = TG[(TG.league == league) & (TG.season == season)]
    id2n = _id2name(league, season)
    # np_raw = καθαρο ασυμπιεστο non-penalty xG (ταιριαζει με teamslab· η συμπιεση+πεναλτι
    # μενουν στο xg_model της μηχανης στοιχηματος, οχι στα περιγραφικα γραφηματα).
    XG = 'np_raw'
    mid_xg = defaultdict(dict)
    for _, r in TG.iterrows():
        mid_xg[r['mid']][r['team']] = r[XG]
    byteam = defaultdict(list)
    for _, r in TG.iterrows():
        opps = [t for t in mid_xg[r['mid']] if t != r['team']]
        xga = mid_xg[r['mid']][opps[0]] if opps else np.nan
        byteam[r['team']].append((r['date'], float(r[XG]), float(xga)))
    out = {}
    for tid, lst in byteam.items():
        lst.sort()
        out[id2n.get(tid, str(tid))] = dict(tid=tid,
                                             xgf=[x for _, x, _ in lst],
                                             xga=[a for _, _, a in lst])
    return out

def team_names(league, season=SEASON_DEFAULT):
    return sorted(team_matches(league, season).keys())

def _roll(vals, w):
    return [float(np.mean(vals[i - w + 1:i + 1])) for i in range(w - 1, len(vals))]

def _trend(xs, ys):
    if len(xs) < 2:
        return ys[:] if ys else []
    s, b = np.polyfit(xs, ys, 1)
    return [float(s * x + b) for x in xs]

def series(team_data, window):
    """Επιστρεφει x (game index), rolling xgf/xga + trends + differential + averages."""
    xgf, xga = team_data['xgf'], team_data['xga']
    rf = _roll(xgf, window); ra = _roll(xga, window)
    x = list(range(window, window + len(rf)))
    tf = _trend(x, rf); ta = _trend(x, ra)
    diff = [f - a for f, a in zip(rf, ra)]
    lf = rf[-1] if rf else float('nan'); laa = ra[-1] if ra else float('nan')
    import numpy as _np
    season_f = float(_np.mean(xgf)) if xgf else float('nan')
    season_a = float(_np.mean(xga)) if xga else float('nan')
    return dict(x=x, xgf=rf, xga=ra, trend_f=tf, trend_a=ta, diff=diff,
                last_xgf=lf, last_xga=laa, last_xgd=lf - laa,
                season_xgf=season_f, season_xga=season_a, season_xgd=season_f - season_a)

if __name__ == '__main__':
    import sys
    lg = sys.argv[1] if len(sys.argv) > 1 else 'EPL'
    tm = sys.argv[2] if len(sys.argv) > 2 else 'Arsenal'
    data = team_matches(lg)
    print(lg, '| ομαδες:', len(data))
    s = series(data[tm], 10)
    print(f'{tm}: latest 10-game xGF {s["last_xgf"]:.2f}  xGA {s["last_xga"]:.2f}  xGD {s["last_xgd"]:+.2f}')
    print('x:', s['x'][:5], '...', s['x'][-3:])
    print('xgf roll:', [round(v, 2) for v in s['xgf'][:5]], '...')
