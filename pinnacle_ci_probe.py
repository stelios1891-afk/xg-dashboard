# -*- coding: utf-8 -*-
"""pinnacle_ci_probe.py — ΕΦΑΠΑΞ (1/10/2026): απαντα η δημοσια υπηρεσια της Pinnacle (guest.api.arcadia, χωρις λογαριασμο) στο GitHub;
Στοχος: οριο πονταρισματος (maxRiskStake) + τιμες Ευρωλιγκας (league 382) & EuroCup (377). Εξοδος: pinnacle_ci_probe_out.txt"""
import requests, sys, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s): print(s, flush=True); out.append(str(s))
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json',
     'Referer': 'https://www.pinnacle.com/', 'Origin': 'https://www.pinnacle.com'}
B = 'https://guest.api.arcadia.pinnacle.com/0.1'
P(f'ωρα UTC {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M}')
for lid, nm in ((382, 'Euroleague'), (377, 'EuroCup')):
    try:
        r = requests.get(f'{B}/leagues/{lid}/matchups', headers=H, timeout=30); P(f'{nm} matchups: HTTP {r.status_code} · {len(r.text)} bytes')
        r2 = requests.get(f'{B}/leagues/{lid}/markets/straight', headers=H, timeout=30); P(f'{nm} markets: HTTP {r2.status_code} · {len(r2.text)} bytes')
        mk = r2.json() if r2.status_code == 200 else []
        ex = [x for x in mk if x.get('period') == 0 and not x.get('isAlternate') and x.get('type') == 'spread'][:2]
        for x in ex: P(f"   spread {[(p.get('points'), p.get('price')) for p in x['prices']]} οριο {x.get('limits')}")
    except Exception as e:
        P(f'{nm}: ΣΦΑΛΜΑ {e}')
open('pinnacle_ci_probe_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
