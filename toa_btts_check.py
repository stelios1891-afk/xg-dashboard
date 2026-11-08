# -*- coding: utf-8 -*-
"""toa_btts_check.py — ONE-OFF (17/9): ποια βιβλια δινουν BTTS στο TOA για τα σημερινα
UEL ματς; regions=eu ΧΩΡΙΣ φιλτρο bookmaker (κοστος: 1 credit/διοργανωση). Γραφει
toa_btts_check_out.txt με bookmaker/yes/no ανα ματς — για να διαλεξουμε πηγη του GG/NG."""
import os, sys, json
import requests

sys.stdout.reconfigure(encoding='utf-8')
K = os.environ.get('TOA_KEY')
if not K:
    print('TOA_KEY δεν υπαρχει τοπικα — τρεχει μονο στο workflow.')
    sys.exit(0)

OUT = []
for sport in ('soccer_uefa_europa_league', 'soccer_uefa_europa_conference_league',
              'soccer_uefa_champs_league', 'soccer_epl'):
    r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                     params=dict(apiKey=K, regions='eu', markets='btts', oddsFormat='decimal'),
                     timeout=45)
    OUT.append(f'== {sport}: HTTP {r.status_code} · cost {r.headers.get("x-requests-last")} '
               f'· remaining {r.headers.get("x-requests-remaining")}')
    if r.status_code != 200:
        OUT.append('   ' + r.text[:300])
        continue
    for g in r.json():
        bks = []
        for b in g.get('bookmakers', []):
            for m in b.get('markets', []):
                if m.get('key') == 'btts':
                    pr = {str(o.get('name', '')).lower(): o.get('price') for o in m.get('outcomes', [])}
                    bks.append(f"{b['key']}({pr.get('yes')}/{pr.get('no')})")
        OUT.append(f"  {g.get('commence_time', '')[:16]} {g.get('home_team')} - {g.get('away_team')}: "
                   + (' '.join(bks) if bks else 'ΚΑΝΕΝΑ βιβλιο με btts'))

txt = chr(10).join(OUT)
print(txt)
with open('toa_btts_check_out.txt', 'w', encoding='utf-8') as fh:
    fh.write(txt + chr(10))
