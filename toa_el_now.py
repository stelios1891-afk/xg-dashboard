# -*- coding: utf-8 -*-
"""toa_el_now.py — τρεχουσες γραμμες Ευρωλιγκας (spreads+totals, eu, ολα τα βιβλια) -> toa_el_now.json. ~2 credits. Μονο GitHub."""
import os, sys, json, requests
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY λειπει'); sys.exit(0)
r = requests.get('https://api.the-odds-api.com/v4/sports/basketball_euroleague/odds',
                 params=dict(apiKey=KEY, regions='eu', markets='spreads,totals', oddsFormat='decimal'), timeout=40)
print(r.status_code, 'credits left', r.headers.get('x-requests-remaining'))
json.dump(dict(fetched=r.headers.get('date'), data=r.json()), open('toa_el_now.json', 'w', encoding='utf-8'), ensure_ascii=False)
