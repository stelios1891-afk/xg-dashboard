# -*- coding: utf-8 -*-
"""intl_toa_check.py — ΔΙΑΓΝΩΣΤΙΚΟ (25/9/2026, ερωτηση Στελιου: «εισαι σιγουρος οτι δεν τραβαει τα υπολοιπα του Nations League;»).
1) /sports (δωρεαν): ολα τα keys που θυμιζουν Nations League / εθνικες.
2) /events (δωρεαν): ΟΛΑ τα ματς που εχει το Odds API στο soccer_uefa_nations_league (οχι μονο οσα εχουν Pinnacle).
3) /odds h2h, regions eu+uk, ΧΩΡΙΣ φιλτρο βιβλιων (2 credits): ποια βιβλια εχουν καθε ματς.
Τρεχει στο GitHub Actions (intl-toa-check.yml)· TOA_KEY μονο απο secrets.
"""
import os, sys, requests
sys.stdout.reconfigure(encoding='utf-8')
B = 'https://api.the-odds-api.com/v4'
K = os.environ['TOA_KEY']
SPORT = 'soccer_uefa_nations_league'

r = requests.get(f'{B}/sports/', params=dict(apiKey=K, all='true'), timeout=30)
print('=== 1) sport keys (εθνικες) ===')
for s in r.json():
    k = s.get('key', ''); t = (s.get('title', '') + ' ' + s.get('description', '')).lower()
    if k.startswith('soccer') and any(w in k + ' ' + t for w in ('nation', 'international', 'friendl', 'qualif', 'africa', 'afcon', 'world_cup', 'euro_')):
        print(f"  {k} | {s.get('title')} | {s.get('description')} | active={s.get('active')}")

r = requests.get(f'{B}/sports/{SPORT}/events', params=dict(apiKey=K), timeout=30)
ev = r.json() if r.status_code == 200 else []
print(f'\n=== 2) events στο {SPORT} (δωρεαν): {len(ev)} ματς ===  [status {r.status_code}]')
for e in sorted(ev, key=lambda x: x.get('commence_time', '')):
    print(f"  {e.get('commence_time','')[:16]}  {e.get('home_team')} - {e.get('away_team')}")

r = requests.get(f'{B}/sports/{SPORT}/odds', params=dict(apiKey=K, regions='eu,uk', markets='h2h', oddsFormat='decimal'), timeout=45)
od = r.json() if r.status_code == 200 else []
print(f"\n=== 3) odds h2h eu+uk χωρις φιλτρο βιβλιων: {len(od)} ματς με αποδοσεις ===  [status {r.status_code}, credits left {r.headers.get('x-requests-remaining')}, κοστος {r.headers.get('x-requests-last')}]")
for e in sorted(od, key=lambda x: x.get('commence_time', '')):
    bks = sorted(b['key'] for b in e.get('bookmakers', []))
    pin = 'PIN' if 'pinnacle' in bks else '---'
    mbk = 'MBK' if 'matchbook' in bks else '---'
    print(f"  {e.get('commence_time','')[:16]}  {pin} {mbk}  {len(bks):2d} βιβλια  {e.get('home_team')} - {e.get('away_team')}   [{', '.join(bks[:8])}{' …' if len(bks) > 8 else ''}]")
