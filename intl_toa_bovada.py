# -*- coding: utf-8 -*-
"""intl_toa_bovada.py — ΔΙΑΓΝΩΣΤΙΚΟ (25/9): γραμμες Bovada (AH/OU/1Χ2) ανα ματς NL, για συγκριση με Pinnacle οπου υπαρχει. ~3 credits."""
import os, sys, datetime, requests
sys.stdout.reconfigure(encoding='utf-8')
K = os.environ['TOA_KEY']; now = datetime.datetime.now(datetime.timezone.utc)
r = requests.get('https://api.the-odds-api.com/v4/sports/soccer_uefa_nations_league/odds',
                 params=dict(apiKey=K, regions='eu', bookmakers='bovada,pinnacle', markets='h2h,spreads,totals', oddsFormat='decimal'), timeout=60)
print(f"status {r.status_code} · credits left {r.headers.get('x-requests-remaining')} · κοστος {r.headers.get('x-requests-last')}")
def mk(b, e):
    o = {}
    for m in b['markets']:
        if m['key'] == 'h2h':
            d = {x['name']: x['price'] for x in m['outcomes']}; o['x12'] = f"{d.get(e['home_team'])}/{d.get('Draw')}/{d.get(e['away_team'])}"
        elif m['key'] == 'spreads':
            h = [x for x in m['outcomes'] if x['name'] == e['home_team']]; a = [x for x in m['outcomes'] if x['name'] == e['away_team']]
            if h and a: o['ah'] = f"{h[0]['point']:+g} {h[0]['price']}/{a[0]['price']}"
        elif m['key'] == 'totals':
            ov = [x for x in m['outcomes'] if x['name'] == 'Over']; un = [x for x in m['outcomes'] if x['name'] == 'Under']
            if ov and un: o['ou'] = f"{ov[0]['point']:g} {ov[0]['price']}/{un[0]['price']}"
    return o
nb = 0; nbd = 0
for e in sorted(r.json(), key=lambda x: x['commence_time']):
    if datetime.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')) <= now: continue
    bk = {b['key']: mk(b, e) for b in e['bookmakers']}
    grp = 'A ' if 'pinnacle' in bk else 'BD'
    bv = bk.get('bovada', {}); pn = bk.get('pinnacle', {})
    nb += bool(bv.get('ah')); nbd += bool(bv.get('ah')) and grp == 'BD'
    print(f"{e['commence_time'][:16]} {grp} {e['home_team']:>22} - {e['away_team']:<22} BOV 1Χ2 {bv.get('x12','—'):>16}  AH {bv.get('ah','—'):>16}  OU {bv.get('ou','—'):>14}"
          + (f"   | PIN AH {pn.get('ah','—')}  OU {pn.get('ou','—')}" if pn else ''))
print(f'\nBovada με AH: {nb} ματς (απο αυτα B-D: {nbd})')
