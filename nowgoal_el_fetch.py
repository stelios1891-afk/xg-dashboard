# -*- coding: utf-8 -*-
"""nowgoal_el_fetch.py — ΙΣΤΟΡΙΚΟ ΓΡΑΜΜΩΝ Ευρωλιγκας απο Nowgoal (δωρεαν, 25/9/2026, προταση Στελιου αντι TOA credits).
Προγραμμα: basketball.nowgoal26.com/jsData/matchResult/{YY-YY}/c7.js (gzip, ωρα Πεκινου UTC+8)·
  jh["G..."] = [[ngid, ?, 'YYYY-MM-DD HH:MM', home_id, away_id, hs, as, …, line, total, …]] · arrTeam = [[id, cn, tw, en, …]]
Ιστορικο: live11.nowgoal26.com/ajax/basketballajax?type=18&id={ngid}&ot=6(ολο το ματς· 3=ημιχρονο)&t={21=χαντικαπ | 23=συνολο}&cid={3=Crown | 8=Bet365}
  (ΔΙΟΡΘΩΣΗ 25/9: το πρωτο περασμα κατεβαζε ot=3 t=21 = χαντικαπ ΗΜΙΧΡΟΝΟΥ — αγνοειται· συνολο = t=23)
  → Data.oddsList [{ut: unix, hs, gs, u, g(γραμμη), d, close, t(2=pre-match)}]· Crown ~60 σειρες/≈20h πριν, Bet365 λιγοτερες/≈2 μερες.
  Session init απο τη σελιδα του ματς (oddscompbasket/{ngid}) + Referer.
Εξοδος: nowgoal_el/sched_{YY-YY}.json (ματς) · nowgoal_el/odds.jsonl (ngid, ot, cid, rows [ut, g, u, d, t, hs, gs]) — resumable."""
import os, sys, json, gzip, re, time, random
import requests
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'nowgoal_el'; os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
SEAS = ['20-21', '21-22', '22-23', '23-24', '24-25', '25-26']

def sched(sea):
    fn = f'{OUT}/sched_{sea}.json'
    if os.path.exists(fn): return json.load(open(fn, encoding='utf-8'))
    r = S.get(f'https://basketball.nowgoal26.com/jsData/matchResult/{sea}/c7.js', headers={'Referer': 'https://basketball.nowgoal26.com/'}, timeout=30)
    t = r.content
    try: t = gzip.decompress(t)
    except Exception: pass
    t = t.decode('utf-8-sig', 'ignore')
    teams = {m.group(1): m.group(4) for m in re.finditer(r"\[(\d+),'([^']*)','([^']*)','([^']*)'", t.split('var arrQualify')[0])}
    games = []
    for m in re.finditer(r"\[(\d{6,8}),-?\d+,'(20\d\d-\d\d-\d\d \d\d:\d\d)',(\d+),(\d+),(-?\d*),(-?\d*),[^\]]*?\]", t):
        g = dict(ngid=int(m.group(1)), bj=m.group(2), hid=m.group(3), aid=m.group(4), home=teams.get(m.group(3)), away=teams.get(m.group(4)),
                 hs=int(m.group(5)) if m.group(5) not in ('', '-1') else None, as_=int(m.group(6)) if m.group(6) not in ('', '-1') else None)
        games.append(g)
    games = list({g['ngid']: g for g in games}.values())
    json.dump(games, open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
    return games

done = set()
OF = f'{OUT}/odds.jsonl'
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: r = json.loads(ln); done.add((r['ngid'], r['ot'], r.get('t', 21), r['cid']))
        except Exception: pass
errs = 0; n = 0
for sea in SEAS:
    games = sched(sea); print(f'{sea}: {len(games)} ματς', flush=True)
    for g in games:
        if g['hs'] is None: continue
        todo = [(6, t, cid) for t in (21, 23) for cid in (3, 8) if (g['ngid'], 6, t, cid) not in done]
        if not todo: continue
        ref = f"https://live11.nowgoal26.com/oddscompbasket/{g['ngid']}"
        try: S.get(ref, timeout=30)
        except Exception: pass
        for ot, tt, cid in todo:
            try:
                time.sleep(0.45 + random.random() * 0.3)
                r = S.get(f"https://live11.nowgoal26.com/ajax/basketballajax?type=18&id={g['ngid']}&ot={ot}&t={tt}&cid={cid}", headers={'Referer': ref}, timeout=30)
                L = r.json()['Data']['oddsList']
                rows = [[x['ut'], x.get('g'), x.get('u'), x.get('d'), x.get('t'), x.get('hs'), x.get('gs')] for x in L]
                with open(OF, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(dict(ngid=g['ngid'], sea=sea, ot=ot, t=tt, cid=cid, rows=rows)) + '\n')
                done.add((g['ngid'], ot, tt, cid)); errs = 0; n += 1
            except Exception as e:
                errs += 1; print(f'  σφαλμα {g["ngid"]} t{tt} cid{cid}: {str(e)[:80]}', flush=True)
                if errs >= 8: print('  8 συνεχομενα σφαλματα → παυση 5′', flush=True); time.sleep(300); errs = 0
        if n and n % 200 == 0: print(f'  {sea}: {n} αιτηματα', flush=True)
print('ΤΕΛΟΣ', len(done))
