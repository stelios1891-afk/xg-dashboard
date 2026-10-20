# -*- coding: utf-8 -*-
"""nba_live_roster.py — NBA ΑΛΛΑΓΗ ΡΟΣΤΕΡ για την τρεχουσα σεζον (6/10/2026· 20/10/2026 τρεχει ΚΑΙ στο cloud).
Ιδια μεθοδος με nba_roster_adj2 «V0|W1» (περασε στο καθαρο τεστ). Αξιες: nba_roster_base.json (nba_roster_base_build.py, τοπικα, ετησια).
ΝΕΟ ρόστερ:
  • μετα το 1ο ματς κανονικης της ομαδας: οσοι επαιξαν σε αυτο (W1 — roster_test 20/10: +4.2% Οκτ-Δεκ, ενω «ολο το ρόστερ» +2.1% ≈ χωρις ροστερ)
  • πριν: ρόστερ ESPN, μονο παικτες με αξια (περσι ή προπερσι) και ΟΧΙ «Out» στη λιστα ESPN (≈ W1: ο τραυματιας δεν παιζει το 1ο ματς·
    π.χ. GSW Butler/Porzingis — ως 20/10 μετρουσαν ως παροντες και το συστημα απουσιων δεν τους επιανε γιατι δεν εχουν φετινο ματς).
  Επιστροφες: οποιος δεν επαιξε περσι μετραει με την προπερσινη αξια (μεσα στη βαση).
Βαρος = λεπτα/ματς · αγνωστοι (rookies κλπ) −1 με 15′. ΠΑΛΙΟ ρόστερ = περσινη ομαδα (βαση). Δ = νεο − παλιο (π./100 στη διαφορα).
core = οι 5 με τα περισσοτερα περσινα λεπτα (ρόστερ ESPN χωρις «Out») — για το βαρος των φιλικων στο nba_refresh (friendly_test 20/10).
Εξοδος: nba_roster_live.json {season, src, delta, roster, core}"""
import sys, re, json, unicodedata, collections, urllib.request
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
B = json.load(open('nba_roster_base.json', encoding='utf-8'))
CUR, PL, OLD = B['season'], B['players'], B['old']
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
def team_value(names):
    vals = [PL.get(nk(n), [-1.0, 15.0, 0.0])[:2] for n in names]
    w = np.array([x[1] for x in vals]); w = 5 * w / w.sum()
    return float(np.sum(w * np.array([x[0] for x in vals])))
GM = json.load(open('nba_espn_games.json', encoding='utf-8'))
by_team = collections.defaultdict(list)
for g in sorted(GM.values(), key=lambda g: g['utc']):
    for t in (g['home'], g['away']): by_team[t].append(g)
try:
    OUTL = {(v.get('code'), nk(x[0])) for v in json.load(open('nba_injuries.json', encoding='utf-8')).get('teams', {}).values()
            for x in v.get('players', []) if str(x[1] or '').strip().lower() == 'out'}
except Exception:
    OUTL = set()
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
try: PREV = json.load(open('nba_roster_live.json', encoding='utf-8'))
except Exception: PREV = {}
OUT, ROS, SRC, CORE = {}, {}, {}, {}
for t in sorted(OLD):
    avail = [n for n in ESPN_ROSTER.get(t, []) if nk(n) in PL and (t, nk(n)) not in OUTL]
    reg = [g for g in by_team.get(t, []) if g['stype'] == 2]
    if reg:
        names = [n for _, n, mn in reg[0]['players'].get(t, []) if mn > 0]; SRC[t] = '1ο ματς'
    else:
        names = avail; SRC[t] = 'ρόστερ ESPN χωρις «Out» (με αξια περσι/προπερσι)'
    if avail: CORE[t] = sorted(avail, key=lambda n: -PL[nk(n)][2])[:5]
    elif t in PREV.get('core', {}): CORE[t] = PREV['core'][t]
    if not names:
        if t in PREV.get('delta', {}): OUT[t], ROS[t], SRC[t] = PREV['delta'][t], PREV['roster'].get(t, []), PREV.get('src', {}).get(t, 'προηγουμενο')
        continue
    OUT[t] = round(team_value(names) - OLD[t], 3); ROS[t] = names
json.dump(dict(season=CUR, src=SRC, delta=OUT, roster=ROS, core=CORE), open('nba_roster_live.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
n1 = sum(1 for v in SRC.values() if v == '1ο ματς')
print(f'ροστερ {CUR}: {len(OUT)} ομαδες ({n1} απο 1ο ματς) · ' + ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(OUT.items(), key=lambda kv: -kv[1])[:6]) + ' … ' +
      ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(OUT.items(), key=lambda kv: kv[1])[:4]) + f' · χωρις δεδομενα: {sorted(set(OLD) - set(OUT))}')
