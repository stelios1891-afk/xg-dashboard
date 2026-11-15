# -*- coding: utf-8 -*-
"""nba_roster_adj.py — NBA: ΑΛΛΑΓΗ ΡΟΣΤΕΡ καθε ομαδας καθε καλοκαιρι (πποντοι/100 κατοχες) για την αφετηρια της σεζον (28/9/2026).
Αξια παικτη (γνωστη ΠΡΙΝ τη σεζον) = μεσος ορος των διαθεσιμων περσινων DARKO / LEBRON / BPM, μαζεμενος × mp/(mp+500) (περσινα λεπτα).
  Χωρις καμια τιμη (ροκι, απο αλλο πρωταθλημα) = −1.0 (σταθερο, επιλεγμενο απο πριν).
ΝΕΟ ρόστερ (σεζον s) = οσοι επαιξαν στα 3 πρωτα ματς της ομαδας· βαρος = περσινα λεπτα/ματς (ροκι/χωρις περσινα: 15′), κανονικα σε 5 θεσεις.
ΠΑΛΙΟ ρόστερ (σεζον s−1) = πραγματικα λεπτα καθε παικτη για την ομαδα, κανονικα σε 5 θεσεις.
Δ = Σ(βαρος × αξια) νεο − παλιο (ιδιες αξιες s−1) → nba_roster_adj.json {"season|team": Δ, ...} + ROSTER_ABS (νεο απολυτο).
"""
import sys, re, json, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
A = pd.read_csv('nba_player_games.csv', usecols=['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE', 'MIN', 'season', 'stype'])
A = A[A.stype == 'RS'].copy()
A['MIN'] = pd.to_numeric(A.MIN, errors='coerce').fillna(0); A = A[A.MIN > 0]
A['team'] = A.TEAM_ABBREVIATION.replace(AB); A['s'] = A.season.str[:4].astype(int) + 1; A['pid'] = A.PLAYER_ID.astype(str)
A['date'] = pd.to_datetime(A.GAME_DATE)
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
NAME2PID = A.assign(k=A.PLAYER_NAME.map(nk)).drop_duplicates('k').set_index('k').pid.to_dict()
MPT = A.groupby(['pid', 's']).MIN.sum().to_dict(); GPT = A.groupby(['pid', 's']).GAME_ID.nunique().to_dict()
def load(f): return json.load(open(f'nba_rapm/{f}.json', encoding='utf-8'))
M = {}
M['DARKO'] = {(str(r['nba_id']), int(r['season'])): r['dpm'] for r in load('DARKO') if r.get('dpm') is not None}
M['LEBRON'] = {(str(r['nba_id']), int(r['year'])): r['LEBRON'] for r in load('lebron') if r.get('LEBRON') is not None}
rows = []
for y in range(2020, 2026):
    try: t = open(f'bbref_cache/NBA_{y}_advanced.html', encoding='utf-8', errors='ignore').read()
    except FileNotFoundError: continue
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and b and mp: rows.append((nk(nm.group(1)), y, float(b.group(1)), int(mp.group(1))))
br = pd.DataFrame(rows, columns=['k', 'y', 'bpm', 'mp']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
M['BPM'] = {(NAME2PID[k], y): v for k, y, v in zip(br.k, br.y, br.bpm) if k in NAME2PID}
UNK = -1.0
def value(p, y):
    vs = [D[(p, y)] for D in M.values() if (p, y) in D]
    if not vs: return UNK
    mp = MPT.get((p, y), 0.0)
    return float(np.mean(vs)) * mp / (mp + 500)                # μαζεμα προς 0 (μεσος παικτης)
OUT, ABS = {}, {}
for s in sorted(A.s.unique()):
    if s - 1 not in set(A.s): continue
    cur = A[A.s == s]; prev = A[A.s == s - 1]
    for t in sorted(cur.team.unique()):
        g3 = cur[cur.team == t].sort_values(['date', 'GAME_ID']).GAME_ID.drop_duplicates().iloc[:3]
        ros = cur[(cur.team == t) & cur.GAME_ID.isin(g3)].pid.unique()
        w = np.array([MPT[(p, s - 1)] / GPT[(p, s - 1)] if (p, s - 1) in MPT else 15.0 for p in ros]); w = 5 * w / w.sum()
        new = float(np.sum(w * np.array([value(p, s - 1) for p in ros])))
        pt = prev[prev.team == t].groupby('pid').MIN.sum()
        wo = 5 * pt.values / pt.values.sum(); old = float(np.sum(wo * np.array([value(p, s - 1) for p in pt.index])))
        OUT[f'{s}|{t}'] = new - old; ABS[f'{s}|{t}'] = new
json.dump(dict(delta=OUT, abs=ABS), open('nba_roster_adj.json', 'w', encoding='utf-8'), indent=0)
for s in sorted({int(k.split('|')[0]) for k in OUT}):
    d = {k.split('|')[1]: v for k, v in OUT.items() if k.startswith(f'{s}|')}
    top = sorted(d.items(), key=lambda x: x[1])
    print(f'{s}: sd Δ {np.std(list(d.values())):.2f} · χειροτερα {", ".join(f"{t} {v:+.1f}" for t, v in top[:3])} · καλυτερα {", ".join(f"{t} {v:+.1f}" for t, v in top[-3:])}')
