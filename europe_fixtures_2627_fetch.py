# -*- coding: utf-8 -*-
"""
europe_fixtures_2627_fetch.py -- TEMP script (agent-generated, δεν αγγιζει europe_fetch.py)
Κατεβαζει το προγραμμα 2026/27 (League Phase) UCL/UEL/UECL, ΟΛΑ τα ματς
(προγραμματισμενα + τελειωμενα), ιδιο σχημα με europe_fixtures.json.
Εξοδος: europe_fixtures_2627.json
"""
import sys, json, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from discover import get, season_url

COMPS = {'ChampionsLeague': 42, 'EuropaLeague': 73, 'ConferenceLeague': 10216}
SEA = '2627'
OUT = 'europe_fixtures_2627.json'

import os
try:
    OLD = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
except Exception:
    OLD = {}
store = {}
for comp, lid in COMPS.items():
    key = f'{comp}_{SEA}'
    url = f'https://www.fotmob.com/api/data/leagues?id={lid}&season={season_url(SEA)}'
    # 16/10/2026: στο cloud το αρχειο δεν ανανεωνοταν απο 26/9 (σφαλμα που κρυβοταν απο continue-on-error) → ανα διοργανωση:
    # αν αποτυχει, κραταμε τις παλιες γραμμες της (το europe_2627_shots_fetch συμπληρωνει τα τελειωμενα απο το matchDetails)
    try:
        d = json.loads(get(url))
        am = d.get('fixtures', {}).get('allMatches', [])
        if not am:
            raise ValueError('κενη λιστα allMatches')
    except Exception as e:
        print(f'  ⚠ {key}: {type(e).__name__}: {e} — κραταω το παλιο προγραμμα ({len(OLD.get(key, []))} ματς)')
        if OLD.get(key):
            store[key] = OLD[key]
        continue
    rows = []
    for m in am:
        st = m.get('status', {})
        if st.get('cancelled'):
            continue
        rows.append(dict(mid=str(m['id']), utc=st.get('utcTime', ''),
                         hid=int(m['home']['id']), hname=m['home']['name'],
                         aid=int(m['away']['id']), aname=m['away']['name'],
                         score=st.get('scoreStr', ''),
                         finished=bool(st.get('finished')),
                         round=str(m.get('round', ''))))
    store[key] = rows
    fin = sum(1 for r in rows if r['finished'])
    print(f'  {key}: {len(rows)} ματς συνολο ({fin} τελειωμενα, {len(rows)-fin} προγραμματισμενα)')
    time.sleep(1.0)

json.dump(store, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('\nΓραφτηκε', OUT)
for k, v in store.items():
    teams = set()
    for r in v:
        teams.add(r['hname']); teams.add(r['aname'])
    print(f'{k}: {len(v)} ματς, {len(teams)} ομαδες')
    print('  ', sorted(teams))
