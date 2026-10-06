# -*- coding: utf-8 -*-
"""nba_live_roster.py — NBA ΑΛΛΑΓΗ ΡΟΣΤΕΡ για την τρεχουσα σεζον (6/10/2026) — ιδια μεθοδος με nba_roster_adj2 «V0|W1» (περασε στο καθαρο τεστ).
Αξια παικτη = μεσος περσινων DARKO / LEBRON / BPM μαζεμενος × λεπτα/(λεπτα+500) · αγνωστοι (ροκι, απο αλλου) −1 με 15′.
ΝΕΟ ρόστερ: οσοι επαιξαν στο 1ο ματς κανονικης περιοδου (ESPN)· ΠΡΙΝ ξεκινησει η σεζον: επισημο ρόστερ ESPN, μονο παικτες με
  περσινα λεπτα NBA ή φετινοι draft (οι αγνωστοι του training camp δεν παιζουν στο 1ο ματς — ιδιο νοημα με το τεσταρισμενο «W1»).
Βαρος = περσινα λεπτα/ματς. ΠΑΛΙΟ ρόστερ = περσινη ομαδα με τα περσινα λεπτα. Δ = νεο − παλιο (π./100 στη διαφορα).
Εξοδος: nba_roster_live.json {season, src, delta: {ομαδα: Δ}, roster: {ομαδα: [ονοματα]}}"""
import sys, re, json, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
CUR = 2027                                   # ετος ληξης τρεχουσας σεζον (ετησια ενημερωση)
src = open('nba_roster_adj2.py', encoding='utf-8').read().split('OUT = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace('for y in range(2020, 2026):', f'for y in range(2020, {CUR}):')
NS = {}; exec(src, NS)
nk, NAME2PID, A, shrunk, team_value = NS['nk'], NS['NAME2PID'], NS['A'], NS['shrunk'], NS['team_value']
GM = json.load(open('nba_espn_games.json', encoding='utf-8'))
by_team = collections.defaultdict(list)
for g in sorted(GM.values(), key=lambda g: g['utc']):
    for t in (g['home'], g['away']): by_team[t].append(g)
prev = A[A.s == CUR - 1]
import urllib.request
_H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
_get = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=_H), timeout=40).read())
_AB = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
ESPN_ROSTER = {}
try:
    for tm in _get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams')['sports'][0]['leagues'][0]['teams']:
        tm = tm['team']; ab = _AB.get(tm['abbreviation'], tm['abbreviation'])
        ESPN_ROSTER[ab] = [a['displayName'] for a in _get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tm['id']}/roster").get('athletes', [])]
except Exception as e:
    print('ΠΡΟΣΟΧΗ: ρόστερ ESPN —', e)
OUT, ROS, SRC = {}, {}, {}
for t in sorted(set(prev.team)):
    pt = prev[prev.team == t].groupby('pid').MIN.sum()
    old = float(np.sum(5 * pt.values / pt.values.sum() * np.array([shrunk(p, CUR - 1) if shrunk(p, CUR - 1) is not None else -1.0 for p in pt.index])))
    reg = [g for g in by_team.get(t, []) if g['stype'] == 2]
    if reg:
        names = [n for _, n, mn in reg[0]['players'].get(t, []) if mn > 0]; SRC[t] = '1ο ματς'
    else:
        names = [n for n in ESPN_ROSTER.get(t, []) if NAME2PID.get(nk(n)) and (NAME2PID[nk(n)], CUR - 1) in NS['MPT'] or (NS['PJ']['draft'].get(nk(n)) or [0])[0] == CUR - 1]
        SRC[t] = 'ρόστερ ESPN (με περσινα λεπτα ή draft)'
    if not names: continue
    pids = [NAME2PID.get(nk(n), 'NEW:' + nk(n)) for n in names]
    OUT[t] = round(team_value(pids, CUR, 'V0') - old, 3); ROS[t] = names
json.dump(dict(season=CUR, src=SRC, delta=OUT, roster=ROS), open('nba_roster_live.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'ροστερ {CUR}: {len(OUT)} ομαδες · ' + ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(OUT.items(), key=lambda kv: -kv[1])[:6]) + ' … ' +
      ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(OUT.items(), key=lambda kv: kv[1])[:4]) + f' · χωρις δεδομενα: {sorted(set(prev.team) - set(OUT))}')
