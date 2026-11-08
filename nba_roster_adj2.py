# -*- coding: utf-8 -*-
"""nba_roster_adj2.py — NBA ΑΛΛΑΓΗ ΡΟΣΤΕΡ v2 (28/9/2026): εκδοχες για το τεστ «ποσο καλυτερη/χειροτερη εγινε καθε ομαδα».
Αξια παικτη ΝΕΟΥ ρόστερ:
  V0   = οπως v1 (περσινη αξια μαζεμενη mp/(mp+500), αγνωστοι −1, λεπτα αγνωστων 15′)
  AGE  = + προβολη ηλικιας/παλινδρομησης (nba_player_proj.json: a + b·v + ηλικια — μετρημενη ΜΟΝΟ 2015-21)
  ROOK = ρουκι/νεοι με αξια & λεπτα ανα θεση draft (nba_player_proj.json)
  BOTH = AGE + ROOK
ΠΑΛΙΟ ρόστερ = περσινη ομαδα με τις περσινες αξιες (αυτο που ηδη «ξερει» το rating).
Παραθυρα ρόστερ: W1/W3/W5/W10 = παικτες των Ν πρωτων ματς (W3.. κοιτανε λιγο μπροστα) · ROLL = σε καθε ματς, οσοι επαιξαν στα
  τελευταια 5 ματς της ομαδας ΜΕΧΡΙ και το τρεχον (γνωστο στο τζαμπολ).
Εξοδος: nba_roster_adj2.json {"V0|W3": {"2023|UTA": Δ}, "BOTH|ROLL": {"2023|UTA|2022-10-19": Δ}, …}"""
import sys, re, json, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
A = pd.read_csv('nba_player_games.csv', usecols=['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE', 'MIN', 'season', 'stype'])
A = A[A.stype == 'RS'].copy()
A['MIN'] = pd.to_numeric(A.MIN, errors='coerce').fillna(0); A = A[A.MIN > 0]
A['team'] = A.TEAM_ABBREVIATION.replace(AB); A['s'] = A.season.str[:4].astype(int) + 1; A['pid'] = A.PLAYER_ID.astype(str)
A['date'] = pd.to_datetime(A.GAME_DATE).dt.strftime('%Y-%m-%d')
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
A['k'] = A.PLAYER_NAME.map(nk)
NAME2PID = A.drop_duplicates('k').set_index('k').pid.to_dict(); PID2NAME = A.drop_duplicates('pid').set_index('pid').k.to_dict()
MPT = A.groupby(['pid', 's']).MIN.sum().to_dict(); GPT = A.groupby(['pid', 's']).GAME_ID.nunique().to_dict()
def load(f): return json.load(open(f'nba_rapm/{f}.json', encoding='utf-8'))
M = {'DARKO': {(str(r['nba_id']), int(r['season'])): r['dpm'] for r in load('DARKO') if r.get('dpm') is not None},
     'LEBRON': {(str(r['nba_id']), int(r['year'])): r['LEBRON'] for r in load('lebron') if r.get('LEBRON') is not None}}
rows = []
for y in range(2020, 2026):
    t = open(f'bbref_cache/NBA_{y}_advanced.html', encoding='utf-8', errors='ignore').read()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and b and mp: rows.append((nk(nm.group(1)), y, float(b.group(1)), int(mp.group(1))))
br = pd.DataFrame(rows, columns=['k', 'y', 'bpm', 'mp']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
M['BPM'] = {(NAME2PID[k], y): v for k, y, v in zip(br.k, br.y, br.bpm) if k in NAME2PID}
PJ = json.load(open('nba_player_proj.json', encoding='utf-8'))
AGE = {tuple(k.split('|')): v for k, v in PJ['ages'].items()}
def age_of(p, s):
    a0 = AGE.get((p, str(s - 1)))
    return a0 + 1 if a0 is not None else AGE.get((p, str(s)))
def raw(p, y):
    vs = [D[(p, y)] for D in M.values() if (p, y) in D]
    return float(np.mean(vs)) if vs else None
def shrunk(p, y):
    v = raw(p, y)
    if v is None: return None
    mp = MPT.get((p, y), 0.0); return v * mp / (mp + 500)
def proj(v, age):
    if age is None: return v
    j = next(n for n, (lo, hi) in enumerate(PJ['age_bins']) if lo <= age < hi)
    return PJ['a'] + PJ['b'] * v + PJ['age_coef'][j]
def rookie(p, s):
    dr = PJ['draft'].get(PID2NAME.get(p, ''))
    if dr and dr[0] == s - 1:
        pk = dr[1]; lab = '1-3' if pk <= 3 else '4-10' if pk <= 10 else '11-20' if pk <= 20 else '21-30' if pk <= 30 else '2ος γυρος'
    else:
        lab = 'χωρις draft'
    return PJ['rookie'][lab]
def new_value(p, s, var):
    """(αξια, λεπτα/ματς) ενος παικτη του νεου ρόστερ."""
    v = shrunk(p, s - 1)
    mpg = MPT[(p, s - 1)] / GPT[(p, s - 1)] if (p, s - 1) in MPT else None
    if var == 'V0':                                      # ακριβως οπως v1
        return (v if v is not None else -1.0), (mpg if mpg is not None else 15.0)
    if mpg is None and (p, s - 2) in MPT:                # χαμενη περσινη σεζον (τραυματισμος) → προπερσινη αξια
        v = shrunk(p, s - 2); mpg = MPT[(p, s - 2)] / GPT[(p, s - 2)]
    if v is None or mpg is None:
        if var in ('ROOK', 'BOTH'):
            r = rookie(p, s); return r['v'], r['mpg']
        return -1.0, 15.0
    if var in ('AGE', 'BOTH'): v = proj(v, age_of(p, s))
    return v, mpg
def team_value(players, s, var):
    vals = [new_value(p, s, var) for p in players]
    w = np.array([x[1] for x in vals]); w = 5 * w / w.sum()
    return float(np.sum(w * np.array([x[0] for x in vals])))
OUT = {}
seasons = sorted(A.s.unique())
for s in seasons:
    if s - 1 not in seasons: continue
    cur = A[A.s == s]; prev = A[A.s == s - 1]
    for t in sorted(cur.team.unique()):
        pt = prev[prev.team == t].groupby('pid').MIN.sum()
        old = float(np.sum(5 * pt.values / pt.values.sum() * np.array([shrunk(p, s - 1) if shrunk(p, s - 1) is not None else -1.0 for p in pt.index])))
        tg = cur[cur.team == t].sort_values(['date', 'GAME_ID'])
        gids = tg.GAME_ID.drop_duplicates().tolist(); gdate = tg.drop_duplicates('GAME_ID').set_index('GAME_ID').date.to_dict()
        for var in ('V0', 'AGE', 'ROOK', 'BOTH'):
            for W in (1, 3, 5, 10):
                ros = tg[tg.GAME_ID.isin(gids[:W])].pid.unique()
                OUT.setdefault(f'{var}|W{W}', {})[f'{s}|{t}'] = team_value(ros, s, var) - old
            for j, g in enumerate(gids):
                ros = tg[tg.GAME_ID.isin(gids[max(0, j - 4):j + 1])].pid.unique()
                OUT.setdefault(f'{var}|ROLL', {})[f'{s}|{t}|{gdate[g]}'] = team_value(ros, s, var) - old
json.dump(OUT, open('nba_roster_adj2.json', 'w', encoding='utf-8'))
for k in ('V0|W3', 'AGE|W3', 'ROOK|W3', 'BOTH|W3'):
    d = OUT[k]; v = np.array(list(d.values()))
    ex = {t: d.get(f'2026|{t}') for t in ('OKC', 'SAS', 'BOS', 'LAL', 'GSW')}
    print(f'{k:8s}: sd {v.std():.2f} · μεσος {v.mean():+.2f} · 2025-26: ' + ' '.join(f'{t} {x:+.1f}' for t, x in ex.items() if x is not None))
