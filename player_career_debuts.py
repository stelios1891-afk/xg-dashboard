# -*- coding: utf-8 -*-
"""
player_career.py — Career ιστορικο (σεζον × διοργανωση: εμφανισεις + μεση βαθμολογια)
για τους παικτες του backfill με λιγα ματς στο 12μηνο (<10 βαθμολογημενα).
Εξοδος: player_career_debuts.jsonl — {pid, s: [[seasonName, leagueId, leagueName, apps, rating, isFriendly], ...]}
"""
import sys, os, json, time, random
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
import build_data

OUT = 'player_career_debuts.jsonl'
import json as _j
targets = [(pid, str(pid)) for pid in _j.load(open('debut_targets.json'))]
done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding='utf-8'):
        try:
            done.add(json.loads(line)['pid'])
        except Exception:
            pass
todo = [t for t in targets if t[0] not in done]
print(f'career προς κατεβασμα: {len(todo)} (ηδη: {len(done)})', flush=True)

t0 = time.time(); ok = err = 0
with open(OUT, 'a', encoding='utf-8') as fh:
    for i, (pid, nm) in enumerate(todo):
        try:
            j = build_data._fotmob(f'https://www.fotmob.com/api/data/playerData?id={pid}')
            seasons = []
            for grp in ('senior',):
                g = ((j.get('careerHistory') or {}).get('careerItems') or {}).get(grp) or {}
                for se in (g.get('seasonEntries') or []):
                    for ts in (se.get('tournamentStats') or []):
                        try:
                            rt = (ts.get('rating') or {}).get('rating')
                            seasons.append([ts.get('seasonName'), ts.get('leagueId'), ts.get('leagueName'),
                                            int(ts.get('appearances') or 0),
                                            float(rt) if rt not in (None, '', '-') else None,
                                            bool(ts.get('isFriendly'))])
                        except (TypeError, ValueError):
                            continue
            fh.write(json.dumps(dict(pid=pid, nm=nm, s=seasons), ensure_ascii=False) + '\n')
            ok += 1
        except Exception as e:
            err += 1
            print(f'  ερρ {pid} {nm}: {type(e).__name__}', flush=True)
            time.sleep(3)
        if (i + 1) % 100 == 0:
            fh.flush(); el = time.time() - t0
            print(f'  {i+1}/{len(todo)} · ok {ok} · err {err} · ETA {(len(todo)-i-1)/((i+1)/el)/60:.0f} λεπτα', flush=True)
        time.sleep(0.35 + random.random() * 0.4)
print(f'ΤΕΛΟΣ debuts: ok {ok} · err {err} · {(time.time()-t0)/60:.0f} λεπτα', flush=True)
