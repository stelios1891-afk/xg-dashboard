# -*- coding: utf-8 -*-
"""el_pbp_fetch.py — ΕΥΡΩΛΙΓΚΑ: πληρες box score + play-by-play ολων των ματς E2016…E2026 (22/10/2026, Στελιος «οκ ξεκινα»:
δεικτες παικτη τυπου BPM / RAPM για την Ευρωλιγκα).
Πηγες: api-live.euroleague.net/v2 (προγραμμα) · live.euroleague.net/api/Boxscore & PlaybyPlay.
Εξοδος: el_pbp/{season}_{code}.json = {box, pbp} (ενα αρχειο ανα ματς· οσα υπαρχουν ηδη παραλειπονται → συνεχιζει απο οπου σταματησε).
Log: el_pbp_fetch.log. Χρηση: python -I el_pbp_fetch.py [E2016 E2017 …]"""
import os, sys, json, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'el_pbp'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0'}; SLEEP = 1.0
def J(u, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if k == tries - 1: print('  σφαλμα', u, type(e).__name__, flush=True); return None
            time.sleep(5 * (k + 1))
SEASONS = sys.argv[1:] or [f'E{y}' for y in range(2016, 2027)]
for s in SEASONS:
    g = J(f'https://api-live.euroleague.net/v2/competitions/E/seasons/{s}/games')
    games = sorted({x['gameCode'] for x in (g or {}).get('data', []) if x.get('played')})
    have = sum(1 for c in games if os.path.exists(os.path.join(OUT, f'{s}_{c}.json')))
    print(f'{s}: παιγμενα {len(games)} · ηδη {have}', flush=True)
    for n, c in enumerate(games, 1):
        fn = os.path.join(OUT, f'{s}_{c}.json')
        if os.path.exists(fn): continue
        b = J(f'https://live.euroleague.net/api/Boxscore?gamecode={c}&seasoncode={s}'); time.sleep(SLEEP)
        p = J(f'https://live.euroleague.net/api/PlaybyPlay?gamecode={c}&seasoncode={s}'); time.sleep(SLEEP)
        if b is None or p is None: continue
        json.dump(dict(season=s, code=c, box=b, pbp=p), open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
        if n % 50 == 0: print(f'  {s}: {n}/{len(games)}', flush=True)
print('ΤΕΛΟΣ', flush=True)
