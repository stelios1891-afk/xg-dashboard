# -*- coding: utf-8 -*-
"""nowgoal_bk_extra_fetch.py — 17/10/2026: ΕΠΙΠΛΕΟΝ ΒΙΒΛΙΑ στο ιστορικο γραμμων μπασκετ (για το τεστ steam bk_steam_lag).
Ιδιο endpoint με nowgoal_el_fetch (basketballajax type=18, ot=6, t=21 χαντικαπ / 23 συνολο). Βιβλια: 31 = SBOBET, 10 = William Hill
(το Nowgoal μπασκετ ΔΕΝ εχει Pinnacle· λιστα σελιδας: 8 Bet365, 3 Crown, 31 Sbobet, 2 Easybet, 1 Macauslot, 9 Vcbet, 10 William Hill, 19 Interwetten, 20 Ladbrokes).
Euroleague / EuroCup / BCL, ολες οι σεζον των sched_*.json. Εξοδος: nowgoal_{el,ec,bcl}/odds_extra.jsonl (ιδια μορφη με odds.jsonl) — resumable."""
import os, sys, json, glob, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
CIDS = [int(x) for x in os.environ.get('CIDS', '31,10').split(',')]
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
for d in os.environ.get('DIRS', 'nowgoal_el,nowgoal_ec,nowgoal_bcl').split(','):
    OF = f'{d}/odds_extra.jsonl'; done = set()
    if os.path.exists(OF):
        for ln in open(OF, encoding='utf-8'):
            try: r = json.loads(ln); done.add((r['ngid'], r['t'], r['cid']))
            except Exception: pass
    games = []
    for f in sorted(glob.glob(f'{d}/sched_*.json')):
        sea = f.split('sched_')[1][:5]
        games += [(sea, g) for g in json.load(open(f, encoding='utf-8')) if g.get('hs') is not None]
    print(f'{d}: {len(games)} ματς · ηδη {len(done)}', flush=True)
    errs = n = 0
    for sea, g in games:
        todo = [(t, c) for t in (21, 23) for c in CIDS if (g['ngid'], t, c) not in done]
        if not todo: continue
        ref = f"https://live11.nowgoal26.com/oddscompbasket/{g['ngid']}"
        try: S.get(ref, timeout=30)
        except Exception: pass
        for tt, cid in todo:
            try:
                time.sleep(0.4 + random.random() * 0.3)
                r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={g['ngid']}&ot=6&t={tt}&cid={cid}", headers={'Referer': ref}, timeout=30)
                L = r.json()['Data']['oddsList'] or []
                rows = [[x['ut'], x.get('g'), x.get('u'), x.get('d'), x.get('t'), x.get('hs'), x.get('gs')] for x in L]
                with open(OF, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(dict(ngid=g['ngid'], sea=sea, ot=6, t=tt, cid=cid, rows=rows)) + '\n')
                done.add((g['ngid'], tt, cid)); errs = 0; n += 1
            except Exception as e:
                errs += 1; print(f'  σφαλμα {g["ngid"]} t{tt} cid{cid}: {str(e)[:80]}', flush=True)
                if errs >= 8: print('  8 συνεχομενα σφαλματα → παυση 5′', flush=True); time.sleep(300); errs = 0
        if n and n % 400 == 0: print(f'  {d} {sea}: {n} αιτηματα', flush=True)
    print(f'{d} ΤΕΛΟΣ {len(done)}', flush=True)
print('ΟΛΑ ΤΕΛΟΣ')
