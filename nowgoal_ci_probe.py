# -*- coding: utf-8 -*-
"""nowgoal_ci_probe.py — ΕΦΑΠΑΞ: απαντα η Nowgoal οταν τη ρωταει το GitHub; (1/10/2026, EuroCup live τιμες — το Odds API δεν εχει EuroCup).
Ελεγχει: προγραμμα EuroCup (c21.js) · τρεχουσες τιμες επερχομενου ματς (χαντικαπ/συνολο/νικητης, Crown & Bet365).
Εξοδος: nowgoal_ci_probe_out.txt"""
import requests, gzip, re, sys, time, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s): print(s, flush=True); out.append(str(s))
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
P(f'ωρα UTC {dt.datetime.utcnow():%Y-%m-%d %H:%M}')
up = []
try:
    r = S.get('https://basketball.nowgoal26.com/jsData/matchResult/26-27/c21.js', headers={'Referer': 'https://basketball.nowgoal26.com/'}, timeout=30)
    t = r.content
    try: t = gzip.decompress(t)
    except Exception: pass
    t = t.decode('utf-8-sig', 'ignore')
    games = re.findall(r"\[(\d{6,8}),-?\d+,'(20\d\d-\d\d-\d\d \d\d:\d\d)',(\d+),(\d+),(-?\d*),(-?\d*),", t)
    up = [g for g in games if g[4] in ('', '-1')]
    P(f'προγραμμα EuroCup: HTTP {r.status_code} · {len(t)} bytes · ματς {len(games)} · επερχομενα {len(up)}')
except Exception as e:
    P(f'προγραμμα EuroCup: ΣΦΑΛΜΑ {e}')
for g in sorted(up, key=lambda g: g[1])[:2]:
    ng = g[0]; ref = f'https://live11.nowgoal26.com/oddscompbasket/{ng}'
    try: rr = S.get(ref, timeout=30); P(f'σελιδα ματς {ng} ({g[1]} Πεκινο): HTTP {rr.status_code} · {len(rr.text)} bytes')
    except Exception as e: P(f'σελιδα ματς {ng}: ΣΦΑΛΜΑ {e}')
    for tt, nm in ((21, 'χαντικαπ'), (23, 'συνολο'), (22, 'νικητης')):
        for cid in (3, 8):
            time.sleep(0.6)
            try:
                x = S.get(f'https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={ng}&ot=6&t={tt}&cid={cid}', headers={'Referer': ref}, timeout=30)
                L = (x.json().get('Data') or {}).get('oddsList') or []
                P(f'  {nm} cid {cid}: HTTP {x.status_code} · {len(L)} τιμες · τελευταια {L[-1] if L else "-"}')
            except Exception as e:
                P(f'  {nm} cid {cid}: ΣΦΑΛΜΑ {str(e)[:120]}')
open('nowgoal_ci_probe_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
