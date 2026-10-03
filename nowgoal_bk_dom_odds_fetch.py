# -*- coding: utf-8 -*-
"""nowgoal_bk_dom_odds_fetch.py — ΙΣΤΟΡΙΚΕΣ ΑΠΟΔΟΣΕΙΣ ΕΓΧΩΡΙΩΝ ΜΠΑΣΚΕΤ απο Nowgoal (2/10/2026, Στελιος «κατεβασε»).
Ματς = bk_domestic.json (Nowgoal id = 1ο πεδιο, κανονικη περιοδος + πλει-οφ, μονο παιγμενα).
Ανα ματς: χαντικαπ (t 21) & συνολο (t 23), Crown (cid 3) + Bet365 (cid 8), ΚΑΘΕ αλλαγη τιμης (ιδια μορφη με nowgoal_ec/odds.jsonl:
rows = [ut, γραμμη, u, d, σημαια(2 = πριν το ματς, 3 = live), σκορ γηπ, σκορ φιλ], ut + 8ω = UTC).
Σειρα: ΠΙΟ ΠΡΟΣΦΑΤΗ σεζον πρωτα (για γρηγορο δειγμα). Resumable. Χρηση: python nowgoal_bk_dom_odds_fetch.py ACB LBA
Εξοδος: nowgoal_dom/odds.jsonl {ngid, lg, sea, t, cid, rows}"""
import os, sys, json, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
LGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']
SEAS = ['25-26', '24-25', '23-24', '22-23', '21-22', '20-21']
OUT = 'nowgoal_dom'; os.makedirs(OUT, exist_ok=True); OF = f'{OUT}/odds.jsonl'
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
D = json.load(open('bk_domestic.json', encoding='utf-8'))
done = set()
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: r = json.loads(ln); done.add((r['ngid'], r['t'], r['cid']))
        except Exception: pass
JOBS = [(21, 3), (21, 8), (23, 3), (23, 8)]
n = errs = 0
with open(OF, 'a', encoding='utf-8') as fo:
    for sea in SEAS:
        for lg in LGS:
            G = [g for g in (D.get(f'{lg}_{sea}') or {}).get('games', []) if str(g[4]).strip() not in ('', '-1', 'None')]
            print(f'{lg} {sea}: {len(G)} ματς', flush=True)
            for g in G:
                ngid = int(g[0])
                todo = [(t, c) for t, c in JOBS if (ngid, t, c) not in done]
                if not todo: continue
                ref = f"https://live11.nowgoal26.com/oddscompbasket/{ngid}"
                try: S.get(ref, timeout=30)
                except Exception: pass
                for tt, cid in todo:
                    try:
                        time.sleep(0.35 + random.random() * 0.3)
                        r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={ngid}&ot=6&t={tt}&cid={cid}", headers={'Referer': ref}, timeout=30)
                        L = (r.json().get('Data') or {}).get('oddsList') or []
                        rows = [[x.get('ut'), x.get('g'), x.get('u'), x.get('d'), x.get('t'), x.get('hs'), x.get('gs')] for x in L]
                        fo.write(json.dumps(dict(ngid=ngid, lg=lg, sea=sea, t=tt, cid=cid, rows=rows)) + '\n')
                        done.add((ngid, tt, cid)); n += 1; errs = 0
                        if n % 200 == 0: print(f'  {n} …', flush=True); fo.flush()
                    except Exception as e:
                        errs += 1; time.sleep(5 * errs)
                        if errs > 20: print('πολλα σφαλματα — σταματω', e); sys.exit(1)
            fo.flush()
            print(f'  ΤΕΛΟΣ {lg} {sea}', flush=True)
print(f'ΤΕΛΟΣ: {n} νεα · συνολο {len(done)}')
