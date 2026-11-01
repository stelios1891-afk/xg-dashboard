# -*- coding: utf-8 -*-
"""nowgoal_nba_fetch.py — NBA: προγραμμα + ιστορικο γραμμων Crown απο Nowgoal (δωρεαν, 26/9/2026).
Προγραμμα: basketball.nowgoal26.com/jsData/matchResult/{YY-YY}/l1_{kind}_{Y}_{M}.js (kind 1 = κανονικη περιοδος, 2 = playoffs·
  gzip+BOM, ωρα Πεκινου UTC+8)· arrTeam για ονοματα· καθε ματς [ngid, ?, 'ωρα', hid, aid, hs, as, …].
Ιστορικο: live11.nowgoal26.com/ajax/basketballajax?type=18&id={ngid}&ot=6&t={21 χαντικαπ | 23 συνολο}&cid=3 (Crown)
  (init session απο oddscompbasket/{ngid} + Referer). Σειρα: νεοτερες σεζον πρωτα (για να ξεκινησει νωρις το τεστ).
Εξοδος: nowgoal_nba/sched_{YY-YY}.json · nowgoal_nba/odds.jsonl — resumable."""
import os, sys, json, gzip, re, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'nowgoal_nba'; os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
SEAS = ['25-26', '24-25', '23-24', '22-23', '21-22', '20-21']

def get_js(u):
    try:
        t = S.get(u, headers={'Referer': 'https://basketball.nowgoal26.com/'}, timeout=30).content
    except Exception:
        return ''
    try: t = gzip.decompress(t)
    except Exception: pass
    return t.decode('utf-8-sig', 'ignore')

def sched(sea):
    fn = f'{OUT}/sched_{sea}.json'
    if os.path.exists(fn): return json.load(open(fn, encoding='utf-8'))
    y0 = 2000 + int(sea[:2]); games, teams = {}, {}
    months = [(y0, m) for m in (10, 11, 12)] + [(y0 + 1, m) for m in range(1, 8)]
    for kind in (1, 2):
        for (y, m) in months:
            t = get_js(f'https://basketball.nowgoal26.com/jsData/matchResult/{sea}/l1_{kind}_{y}_{m}.js'); time.sleep(0.3)
            if 'arrData' not in t and 'arrTeam' not in t: continue
            for mm in re.finditer(r"\[(\d+),'([^']*)','([^']*)','([^']*)'", t.split('arrData')[0]):
                teams[mm.group(1)] = mm.group(4)
            for mm in re.finditer(r"\[(\d{6,8}),-?\d+,'(20\d\d-\d\d-\d\d \d\d:\d\d)',(\d+),(\d+),(-?\d*),(-?\d*)", t):
                games[int(mm.group(1))] = dict(ngid=int(mm.group(1)), bj=mm.group(2), hid=mm.group(3), aid=mm.group(4), kind=kind,
                                               hs=int(mm.group(5)) if mm.group(5) not in ('', '-1') else None,
                                               as_=int(mm.group(6)) if mm.group(6) not in ('', '-1') else None)
    G = list(games.values())
    for g in G: g['home'] = teams.get(g['hid']); g['away'] = teams.get(g['aid'])
    json.dump(G, open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
    return G

for sea in SEAS:
    G = sched(sea); print(f'{sea}: {len(G)} ματς (κανονικη {sum(g["kind"] == 1 for g in G)} · playoffs {sum(g["kind"] == 2 for g in G)})', flush=True)
done = set(); OF = f'{OUT}/odds.jsonl'
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: r = json.loads(ln); done.add((r['ngid'], r['t']))
        except Exception: pass
errs = 0; n = 0
for sea in SEAS:
    for g in sched(sea):
        if g['hs'] is None: continue
        todo = [t for t in (21, 23) if (g['ngid'], t) not in done]
        if not todo: continue
        ref = f"https://live11.nowgoal26.com/oddscompbasket/{g['ngid']}"
        try: S.get(ref, timeout=30)
        except Exception: pass
        for tt in todo:
            try:
                time.sleep(0.4 + random.random() * 0.3)
                r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={g['ngid']}&ot=6&t={tt}&cid=3", headers={'Referer': ref}, timeout=30)
                L = r.json()['Data']['oddsList']
                rows = [[x['ut'], x.get('g'), x.get('u'), x.get('d'), x.get('t')] for x in L if x.get('t') == 2]
                with open(OF, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(dict(ngid=g['ngid'], sea=sea, t=tt, rows=rows)) + '\n')
                done.add((g['ngid'], tt)); errs = 0; n += 1
            except Exception as e:
                errs += 1; print(f'  σφαλμα {g["ngid"]} t{tt}: {str(e)[:80]}', flush=True)
                if errs >= 8: print('  8 συνεχομενα σφαλματα → παυση 5′', flush=True); time.sleep(300); errs = 0
        if n and n % 500 == 0: print(f'  {sea}: {n} αιτηματα', flush=True)
print('ΤΕΛΟΣ', len(done))
