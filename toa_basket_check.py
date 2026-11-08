# -*- coding: utf-8 -*-
"""toa_basket_check.py — ελεγχος καλυψης ΜΠΑΣΚΕΤ στο The Odds API (24/9/2026, project Ευρωλιγκας).
Τρεχει ΜΟΝΟ στο GitHub (TOA_KEY secret). Κοστος ~150 credits max.
 1) /sports?all=true (δωρεαν): ολα τα basketball keys (ενεργα + ανενεργα)
 2) /events Ευρωλιγκας (δωρεαν): ποια ματς εχει τωρα
 3) /odds τωρα (h2h,spreads,totals · eu): ποια βιβλια, αν υπαρχει Pinnacle, γραμμες
 4) /historical σε 5 ημερομηνιες 2020-2026: ποσο πισω πανε τα ιστορικα, με ποια βιβλια
Εξοδος: toa_basket_check_out.txt"""
import os, sys, json
import requests
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY λειπει (τρεχει μονο στο GitHub)'); sys.exit(0)
B = 'https://api.the-odds-api.com/v4'
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

def get(path, **params):
    params['apiKey'] = KEY
    r = requests.get(B + path, params=params, timeout=40)
    P(f'  [{r.status_code}] {path} · credits: used {r.headers.get("x-requests-used")} / left {r.headers.get("x-requests-remaining")} (κοστος {r.headers.get("x-requests-last")})')
    try:
        return r.json()
    except Exception:
        return None

P('=== 1. ΟΛΑ ΤΑ BASKETBALL KEYS ===')
sp = get('/sports', all='true') or []
bk = [s for s in sp if isinstance(s, dict) and s.get('group', '').lower() == 'basketball']
for s in bk:
    P(f"  {s['key']:40s} {s['title']:30s} active={s['active']} outrights={s['has_outrights']}")

keys = [s['key'] for s in bk if 'euroleague' in s['key'] or 'eurocup' in s['key']]
EL = 'basketball_euroleague' if 'basketball_euroleague' in [s['key'] for s in bk] else (keys[0] if keys else None)
if not EL:
    P('ΚΑΝΕΝΑ euroleague key'); open('toa_basket_check_out.txt', 'w', encoding='utf-8').write('\n'.join(out)); sys.exit(0)

P(f'\n=== 2. EVENTS {EL} (δωρεαν) ===')
ev = get(f'/sports/{EL}/events') or []
P(f'  {len(ev)} events')
for e in ev[:12]:
    P(f"  {e['commence_time']}  {e['home_team']} - {e['away_team']}")

P(f'\n=== 3. ΤΡΕΧΟΥΣΕΣ ΑΠΟΔΟΣΕΙΣ {EL} (h2h,spreads,totals · eu+uk) ===')
od = get(f'/sports/{EL}/odds', regions='eu,uk', markets='h2h,spreads,totals', oddsFormat='decimal') or []
books = {}
for g in od if isinstance(od, list) else []:
    for b in g.get('bookmakers', []):
        books.setdefault(b['key'], set()).update(m['key'] for m in b.get('markets', []))
P(f'  ματς με αποδοσεις: {len(od) if isinstance(od, list) else od}')
for k, v in sorted(books.items()):
    P(f'  {k:20s} {sorted(v)}')
if isinstance(od, list) and od:
    g = od[0]
    P(f"  παραδειγμα: {g['home_team']} - {g['away_team']} {g['commence_time']}")
    for b in g['bookmakers']:
        if b['key'] in ('pinnacle', 'betfair_ex_eu', 'bet365', 'unibet_eu', 'marathonbet'):
            for m in b['markets']:
                P(f"    {b['key']:14s} {m['key']:8s} " + ' | '.join(f"{o['name']} {o.get('point', '')} @{o['price']}" for o in m['outcomes']))

P(f'\n=== 4. ΙΣΤΟΡΙΚΑ {EL} (spreads,totals · eu) ===')
for d in ('2020-12-10T12:00:00Z', '2022-01-12T12:00:00Z', '2023-11-08T12:00:00Z', '2025-01-15T12:00:00Z', '2026-03-05T12:00:00Z'):
    h = get(f'/historical/sports/{EL}/odds', regions='eu', markets='spreads,totals', oddsFormat='decimal', date=d)
    data = (h or {}).get('data') if isinstance(h, dict) else None
    if not data:
        P(f'  {d}: ΤΙΠΟΤΑ ({(h or {}).get("message", "") if isinstance(h, dict) else h})'); continue
    bb = sorted({b['key'] for g in data for b in g.get('bookmakers', [])})
    pin = sum(1 for g in data if any(b['key'] == 'pinnacle' for b in g.get('bookmakers', [])))
    P(f"  {d}: snapshot {h.get('timestamp')} · {len(data)} ματς · Pinnacle σε {pin} · βιβλια: {bb}")

open('toa_basket_check_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
P('\n-> toa_basket_check_out.txt')
