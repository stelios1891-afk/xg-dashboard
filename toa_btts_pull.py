# -*- coding: utf-8 -*-
"""toa_btts_pull.py — ONE-OFF (εντολη 11/9): closing τιμη Goal/No Goal (BTTS)
για το Bayern München - Bodø/Glimt (UCL 1η αγωνιστικη, KO 2026-09-10T19:00Z).

Historical event-odds απο The Odds API (το BTTS ειναι additional market => μονο
μεσω event endpoint). Snapshot στις 18:58Z (2' προ σεντρας). Κοστος ~20 credits.
Τρεχει στο GitHub Actions (TOA_KEY secret) μεσω toa-btts.yml → commit toa_btts_out.txt.
Τοπικα χωρις κλειδι: graceful exit.
"""
import sys, os, json
import requests
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — τιποτα δεν εγινε')
    raise SystemExit(0)

SPORT = 'soccer_uefa_champs_league'
EID = 'ce224016de80ab3f7101a6c7cde3a5c7'   # Bayern München - Bodø/Glimt (απο euro_odds_latest)
SNAP = '2026-09-10T18:58:00Z'
OUT = 'toa_btts_out.txt'

r = requests.get(f'https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{EID}/odds',
                 params=dict(apiKey=KEY, date=SNAP, markets='btts',
                             regions='eu,uk', oddsFormat='decimal'),
                 timeout=45)
lines = [f'HTTP {r.status_code} · snapshot ζητηθηκε {SNAP} · used {r.headers.get("x-requests-used")} '
         f'· remaining {r.headers.get("x-requests-remaining")}']
if r.status_code == 200:
    js = r.json()
    d = js.get('data') or {}
    lines.append(f'snapshot επεστραφη: {js.get("timestamp")} · '
                 f'{d.get("home_team")} - {d.get("away_team")} · KO {d.get("commence_time")}')
    for b in d.get('bookmakers', []):
        for m in b.get('markets', []):
            if m.get('key') != 'btts':
                continue
            pr = {o.get('name'): o.get('price') for o in m.get('outcomes', [])}
            lines.append(f'  {b.get("key"):>14s} (upd {m.get("last_update", "")[11:16]}Z): '
                         f'Goal(Yes) {pr.get("Yes")} · No Goal(No) {pr.get("No")}')
    if len(lines) == 2:
        lines.append('  (κανενας bookmaker δεν εδωσε btts στο snapshot)')
else:
    lines.append(r.text[:300])
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
