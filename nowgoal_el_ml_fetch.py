# -*- coding: utf-8 -*-
"""nowgoal_el_ml_fetch.py — ΙΣΤΟΡΙΚΟ ΑΠΟΔΟΣΕΩΝ ΝΙΚΗΤΗ (moneyline) Ευρωλιγκας απο Nowgoal (1/10/2026, Στελιος «τρεξε και νικητη»).
live11.nowgoal26.com/ajax/basketballajax?type=18&id={ngid}&ot=6&t=22&cid={3=Crown | 8=Bet365} → oddsList [{hw, gw, ut}] (δεκαδικες, ut +8ω = UTC).
Σεζον 21-22 … 25-26 (ιδιο προγραμμα με nowgoal_el_fetch.py). Resumable. Εξοδος: nowgoal_el/ml.jsonl {ngid, sea, cid, rows [[ut, hw, gw]]}."""
import os, sys, json, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'nowgoal_el'; OF = f'{OUT}/ml.jsonl'
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
SEAS = ['21-22', '22-23', '23-24', '24-25', '25-26']
done = set()
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: r = json.loads(ln); done.add((r['ngid'], r['cid']))
        except Exception: pass
n = errs = 0
with open(OF, 'a', encoding='utf-8') as fo:
    for sea in SEAS:
        games = json.load(open(f'{OUT}/sched_{sea}.json', encoding='utf-8'))
        print(f'{sea}: {len(games)} ματς', flush=True)
        for g in games:
            if g.get('hs') is None: continue
            todo = [c for c in (3, 8) if (g['ngid'], c) not in done]
            if not todo: continue
            ref = f"https://live11.nowgoal26.com/oddscompbasket/{g['ngid']}"
            try: S.get(ref, timeout=30)
            except Exception: pass
            for cid in todo:
                try:
                    time.sleep(0.4 + random.random() * 0.3)
                    r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={g['ngid']}&ot=6&t=22&cid={cid}", headers={'Referer': ref}, timeout=30)
                    L = (r.json().get('Data') or {}).get('oddsList') or []
                    fo.write(json.dumps(dict(ngid=g['ngid'], sea=sea, cid=cid, rows=[[x.get('ut'), x.get('hw'), x.get('gw')] for x in L])) + '\n')
                    done.add((g['ngid'], cid)); n += 1; errs = 0
                    if n % 200 == 0: print(f'  {n} …', flush=True); fo.flush()
                except Exception as e:
                    errs += 1; time.sleep(5 * errs)
                    if errs > 20: print('πολλα σφαλματα — σταματω', e); sys.exit(1)
print(f'ΤΕΛΟΣ: {n} νεα · συνολο {len(done)}')
