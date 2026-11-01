# -*- coding: utf-8 -*-
"""
player_backfill.py — Προσωπικο ιστορικο (FotMob playerData) για τους παικτες
χωρις δικο μας ιστορικο (new=True στο lineup_lab.json): τελευταια ~40 ματς
με rating/λεπτα/πρωταθλημα, απο ΟΠΟΙΑ λιγκα κι αν επαιζαν.

Εξοδος: player_backfill.jsonl — {pid, nm, m: [[ημ/νια, leagueId, leagueName, λεπτα, rating], ...]}
Resumable (done-set). ~0.6s/αιτημα.
"""
import sys, os, json, time, random
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
import build_data

OUT = 'player_backfill.jsonl'
LAB = json.load(open('lineup_lab.json', encoding='utf-8'))
targets = {}
for t in LAB['teams'].values():
    for p in t['players']:
        if p['new']:
            targets[p['id']] = p['nm']
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding='utf-8'):
        try:
            done.add(json.loads(line)['pid'])
        except Exception:
            pass
todo = [(pid, nm) for pid, nm in targets.items() if pid not in done]
print(f'παικτες προς κατεβασμα: {len(todo)} (ηδη: {len(done)})', flush=True)

t0 = time.time(); ok = err = empty = 0
with open(OUT, 'a', encoding='utf-8') as fh:
    for i, (pid, nm) in enumerate(todo):
        try:
            j = build_data._fotmob(f'https://www.fotmob.com/api/data/playerData?id={pid}')
            rm = j.get('recentMatches') or []
            if isinstance(rm, dict):
                rm = rm.get('all') or []
            ms = []
            for m in rm:
                try:
                    rt = m.get('ratingProps') or {}
                    r = float(rt.get('rating')) if rt.get('rating') not in (None, '', '-') else None
                    dt = ((m.get('matchDate') or {}).get('utcTime') or '')[:10]
                    ms.append([dt, m.get('leagueId'), m.get('leagueName'), m.get('minutesPlayed'), r])
                except (TypeError, ValueError):
                    continue
            fh.write(json.dumps(dict(pid=pid, nm=nm, m=ms), ensure_ascii=False) + '\n')
            ok += 1
            if not ms:
                empty += 1
        except Exception as e:
            err += 1
            print(f'  ερρ {pid} {nm}: {type(e).__name__}', flush=True)
            time.sleep(3)
        if (i + 1) % 150 == 0:
            fh.flush()
            el = time.time() - t0
            print(f'  {i+1}/{len(todo)} · ok {ok} (κενα {empty}) · err {err} · ETA {(len(todo)-i-1)/((i+1)/el)/60:.0f} λεπτα', flush=True)
        time.sleep(0.35 + random.random() * 0.4)
print(f'ΤΕΛΟΣ backfill: ok {ok} (κενα {empty}) · err {err} · {(time.time()-t0)/60:.0f} λεπτα', flush=True)
