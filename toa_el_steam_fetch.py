# -*- coding: utf-8 -*-
"""toa_el_steam_fetch.py — 17/10/2026: τιμες PINNACLE (TOA historical, regions eu) γυρω απο τις κινησεις της Ευρωλιγκας (el_steam_events.json).
Ενα snapshot ανα (αγορα, 5λεπτο) — μονο η αγορα της κινησης (spreads ή totals = 10 credits). Προτεραιοτητα 1 (κινηση ≥2) πρωτα, μετα 2.
Κραταει τα ματς του snapshot που ξεκινουν ±25′ απο το τζαμπολ καποιου γεγονοτος του slot (ολα τα βιβλια).
Resumable (toa_el_steam_state.json) · δικλιδα: σταματα αν credits < TOA_FLOOR. Τρεχει ΜΟΝΟ στο GitHub (TOA_KEY). Εξοδος: toa_el_steam.jsonl"""
import os, sys, json, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.environ.get('TOA_KEY')
if not KEY: print('TOA_KEY λειπει (μονο GitHub)'); sys.exit(0)
FLOOR = int(os.environ.get('TOA_FLOOR', '30000')); MAXP = int(os.environ.get('MAX_PRIO') or (open('el_steam_trigger.txt').read().split('MAX_PRIO=')[1].split()[0] if os.path.exists('el_steam_trigger.txt') and 'MAX_PRIO=' in open('el_steam_trigger.txt').read() else '2'))
OUT, ST = 'toa_el_steam.jsonl', 'toa_el_steam_state.json'
done = set(json.load(open(ST))) if os.path.exists(ST) else set()
EV = json.load(open('el_steam_events.json', encoding='utf-8'))
slots = {}
for e in EV:
    if e['prio'] > MAXP: continue
    for s in e['snaps']:
        k = f"{e['mk']}|{s // 300}"
        d = slots.setdefault(k, dict(mk=e['mk'], ts=s, prio=e['prio'], tips=set()))
        d['prio'] = min(d['prio'], e['prio']); d['tips'].add(e['tip']); d['ts'] = max(d['ts'], s)
todo = sorted((k for k in slots if k not in done), key=lambda k: (slots[k]['prio'], slots[k]['ts']))
print(f'slots {len(slots)} · εκκρεμουν {len(todo)} · floor {FLOOR}', flush=True)
n = 0; left = None
with open(OUT, 'a', encoding='utf-8') as fo:
    for k in todo:
        d = slots[k]; snap = dt.datetime.fromtimestamp(d['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            r = requests.get('https://api.the-odds-api.com/v4/historical/sports/basketball_euroleague/odds',
                             params=dict(apiKey=KEY, regions='eu', markets=d['mk'], oddsFormat='decimal', date=snap), timeout=40)
        except Exception as e:
            print(f'  {snap}: {type(e).__name__}'); continue
        left = int(r.headers.get('x-requests-remaining') or 0)
        if r.status_code != 200:
            print(f'  {snap}: HTTP {r.status_code} {r.text[:120]}')
            if r.status_code in (401, 429): break
            continue
        j = r.json(); kept = 0
        for g in j.get('data') or []:
            ct = dt.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00')).timestamp()
            if any(abs(ct - tp) <= 1500 for tp in d['tips']):
                fo.write(json.dumps(dict(slot=k, req=snap, snap_ts=j.get('timestamp'), mk=d['mk'], id=g['id'], commence=g['commence_time'],
                                         home=g['home_team'], away=g['away_team'], bookmakers=g.get('bookmakers', [])), ensure_ascii=False) + '\n'); kept += 1
        done.add(k); n += 1
        if n % 50 == 0:
            fo.flush(); json.dump(sorted(done), open(ST, 'w')); print(f'  {n}/{len(todo)} · credits left {left}', flush=True)
        if left is not None and left < FLOOR: print(f'ΔΙΚΛΙΔΑ: credits {left} < {FLOOR} — σταματω'); break
json.dump(sorted(done), open(ST, 'w'))
print(f'ΤΕΛΟΣ: {n} snapshots τωρα · συνολο {len(done)} · credits left {left}')
