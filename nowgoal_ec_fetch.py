# -*- coding: utf-8 -*-
"""nowgoal_ec_fetch.py — ΙΣΤΟΡΙΚΟ ΓΡΑΜΜΩΝ EuroCup απο Nowgoal (1/10/2026, Στελιος: EuroCup βημα 2).
Nowgoal league id 21 (ULEB EuroCup) · σεζον 20-21 … 25-26 · ανα ματς: χαντικαπ (t 21) & συνολο (t 23) Crown (cid 3) + Bet365 (cid 8),
  νικητης (t 22) Crown. Ιδια μορφη με nowgoal_el/odds.jsonl & ml.jsonl (ut +8ω = UTC). Resumable.
Εξοδος: nowgoal_ec/sched_{YY-YY}.json · nowgoal_ec/odds.jsonl {ngid, sea, ot, t, cid, rows}."""
import os, sys, json, gzip, re, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'nowgoal_ec'; os.makedirs(OUT, exist_ok=True); OF = f'{OUT}/odds.jsonl'
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
SEAS = ['20-21', '21-22', '22-23', '23-24', '24-25', '25-26']
def sched(sea):
    fn = f'{OUT}/sched_{sea}.json'
    if os.path.exists(fn): return json.load(open(fn, encoding='utf-8'))
    r = S.get(f'https://basketball.nowgoal26.com/jsData/matchResult/{sea}/c21.js', headers={'Referer': 'https://basketball.nowgoal26.com/'}, timeout=30)
    t = r.content
    try: t = gzip.decompress(t)
    except Exception: pass
    t = t.decode('utf-8-sig', 'ignore')
    teams = {m.group(1): m.group(4) for m in re.finditer(r"\[(\d+),'([^']*)','([^']*)','([^']*)'", t.split('var arrQualify')[0])}
    games = []
    for m in re.finditer(r"\[(\d{6,8}),-?\d+,'(20\d\d-\d\d-\d\d \d\d:\d\d)',(\d+),(\d+),(-?\d*),(-?\d*),[^\]]*?\]", t):
        games.append(dict(ngid=int(m.group(1)), bj=m.group(2), hid=m.group(3), aid=m.group(4), home=teams.get(m.group(3)), away=teams.get(m.group(4)),
                          hs=int(m.group(5)) if m.group(5) not in ('', '-1') else None, as_=int(m.group(6)) if m.group(6) not in ('', '-1') else None))
    games = list({g['ngid']: g for g in games}.values())
    json.dump(games, open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
    return games
done = set()
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: r = json.loads(ln); done.add((r['ngid'], r['t'], r['cid']))
        except Exception: pass
JOBS = [(21, 3), (21, 8), (23, 3), (23, 8), (22, 3)]
n = errs = 0
with open(OF, 'a', encoding='utf-8') as fo:
    for sea in SEAS:
        games = sched(sea); print(f'{sea}: {len(games)} ματς', flush=True)
        for g in games:
            if g.get('hs') is None: continue
            todo = [(t, c) for t, c in JOBS if (g['ngid'], t, c) not in done]
            if not todo: continue
            ref = f"https://live11.nowgoal26.com/oddscompbasket/{g['ngid']}"
            try: S.get(ref, timeout=30)
            except Exception: pass
            for tt, cid in todo:
                try:
                    time.sleep(0.4 + random.random() * 0.3)
                    r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={g['ngid']}&ot=6&t={tt}&cid={cid}", headers={'Referer': ref}, timeout=30)
                    L = (r.json().get('Data') or {}).get('oddsList') or []
                    rows = ([[x.get('ut'), x.get('hw'), x.get('gw')] for x in L] if tt == 22 else
                            [[x.get('ut'), x.get('g'), x.get('u'), x.get('d'), x.get('t'), x.get('hs'), x.get('gs')] for x in L])
                    fo.write(json.dumps(dict(ngid=g['ngid'], sea=sea, ot=6, t=tt, cid=cid, rows=rows)) + '\n')
                    done.add((g['ngid'], tt, cid)); n += 1; errs = 0
                    if n % 250 == 0: print(f'  {n} …', flush=True); fo.flush()
                except Exception as e:
                    errs += 1; time.sleep(5 * errs)
                    if errs > 20: print('πολλα σφαλματα — σταματω', e); sys.exit(1)
print(f'ΤΕΛΟΣ: {n} νεα · συνολο {len(done)}')
