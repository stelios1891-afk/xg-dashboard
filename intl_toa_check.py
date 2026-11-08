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

# 4) (25/9) Pinnacle vs Betfair Exchange: ποιες αγορες εχει το καθε βιβλιο + γκανιοτα (overround) ανα αγορα. 3 credits.
import statistics as st
r = requests.get(f'{B}/sports/{SPORT}/odds', params=dict(apiKey=K, regions='eu', markets='h2h,spreads,totals',
                 bookmakers='pinnacle,betfair_ex_eu', oddsFormat='decimal'), timeout=45)
od = r.json() if r.status_code == 200 else []
print(f"\n=== 4) Pinnacle vs Betfair Exchange (h2h/spreads/totals): {len(od)} ματς  [status {r.status_code}, credits left {r.headers.get('x-requests-remaining')}, κοστος {r.headers.get('x-requests-last')}] ===")
mg = {}
def over(outs):
    ps = [o.get('price') for o in outs if o.get('price')]
    return sum(1 / p for p in ps) - 1 if len(ps) >= 2 else None
for e in sorted(od, key=lambda x: x.get('commence_time', '')):
    line = f"  {e.get('commence_time','')[:16]}  {e.get('home_team')} - {e.get('away_team')}:"
    for b in e.get('bookmakers', []):
        parts = []
        for m in b.get('markets', []):
            v = over(m.get('outcomes', []))
            pt = ''
            if m['key'] == 'spreads':
                pt = f" {[o.get('point') for o in m['outcomes'] if o.get('name') == e.get('home_team')]}"
            elif m['key'] == 'totals':
                pt = f" {m['outcomes'][0].get('point')}"
            parts.append(f"{m['key']}{pt} {v*100:+.1f}%" if v is not None else m['key'])
            if v is not None:
                mg.setdefault((b['key'], m['key']), []).append(v)
        line += f"  [{b['key']}: {', '.join(parts)}]"
    print(line)
print('\n=== ΜΕΣΗ ΓΚΑΝΙΟΤΑ (overround) ανα βιβλιο/αγορα ===')
for (bk, mk), vs in sorted(mg.items()):
    print(f"  {bk:14s} {mk:8s} n={len(vs):2d}  μεση {st.mean(vs)*100:5.2f}%  διαμεσος {st.median(vs)*100:5.2f}%  min {min(vs)*100:5.2f}%  max {max(vs)*100:5.2f}%")
