"""
xgstats.py — per-team avg npxG For/Against/Diff + actual GD, ανα Overall/Home/Away.
Πηγη: teamgame_inputs.csv (np_raw = καθαρο npxG, ιδιο με scatter/trendline) + gf (γκολ).
"""
import os
import numpy as np
import pandas as pd
from collections import defaultdict
import trendline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASON_DEFAULT = '2526'
VENUES = ['total', 'home', 'away']

def compute(league, season=SEASON_DEFAULT):
    """{venue: [rows]} · row: team, tid, xgf, xga, xgd, gf, ga, gd (ολα per-game avg)."""
    TG = pd.read_csv(os.path.join(ROOT, 'teamgame_inputs.csv'))
    TG['season'] = TG['season'].astype(str)
    TG = TG[(TG.league == league) & (TG.season == season)]
    id2n = trendline._id2name(league, season)
    mid = defaultdict(dict)
    for _, r in TG.iterrows():
        mid[r['mid']][r['team']] = (float(r['np_raw']), float(r['gf']))
    acc = {v: defaultdict(lambda: dict(xgf=[], xga=[], gf=[], ga=[])) for v in VENUES}
    for _, r in TG.iterrows():
        opp = [t for t in mid[r['mid']] if t != r['team']]
        if not opp:
            continue
        oxg, og = mid[r['mid']][opp[0]]
        for v in ('total', 'home' if r['is_home'] else 'away'):
            a = acc[v][r['team']]
            a['xgf'].append(float(r['np_raw'])); a['xga'].append(oxg)
            a['gf'].append(float(r['gf'])); a['ga'].append(og)
    out = {}
    for v in VENUES:
        rows = []
        for tid, a in acc[v].items():
            if not a['xgf']:
                continue
            xgf, xga = np.mean(a['xgf']), np.mean(a['xga'])
            gf, ga = np.mean(a['gf']), np.mean(a['ga'])
            rows.append(dict(team=id2n.get(tid, str(tid)), tid=tid, gp=len(a['xgf']),
                             xgf=float(xgf), xga=float(xga), xgd=float(xgf - xga),
                             gf=float(gf), ga=float(ga), gd=float(gf - ga)))
        out[v] = rows
    return out

if __name__ == '__main__':
    import sys
    lg = sys.argv[1] if len(sys.argv) > 1 else 'EPL'
    d = compute(lg)['total']
    print(f'{lg} — XG Stats (Overall), {len(d)} ομαδες')
    for r in sorted(d, key=lambda x: -x['xgf'])[:5]:
        print(f"  {r['team']:20s} xGF {r['xgf']:.2f}  xGA {r['xga']:.2f}  xGD {r['xgd']:+.2f}  GD {r['gd']:+.2f}")
