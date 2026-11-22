# -*- coding: utf-8 -*-
"""player_xgi_fetch.py — 21/10/2026 (Στελιος: «αφου οι επιθετικοι δινουν σημα, ισως αξιζει να δοκιμασουμε και το xGI ενος παικτη»).
Για καθε ματς CORE7 (core7_squads + squads_2627): ανα παικτη [λεπτα, xG, xA] απο το FotMob matchDetails (playerStats).
Συνεχιζει απο εκει που σταματησε (player_xgi.jsonl, μια γραμμη ανα ματς). 6 παραλληλα αιτηματα."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intl_fetch
OUT = 'player_xgi.jsonl'


def stats_of(v):
    st = v.get('stats'); blk = st if isinstance(st, list) else [st]; out = {}
    for b in blk:
        sk = b.get('stats') if isinstance(b, dict) and isinstance(b.get('stats'), dict) else b
        if isinstance(sk, dict):
            for k, x in sk.items():
                if isinstance(x, dict) and isinstance(x.get('stat'), dict): out[k] = x['stat'].get('value')
    return out


def one(mid):
    for i in range(3):
        try:
            d = json.loads(intl_fetch.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
            ps = (d.get('content') or {}).get('playerStats') or {}
            rows = {}
            for pid, v in ps.items():
                if not isinstance(v, dict): continue
                s = stats_of(v)
                rows[str(pid)] = [s.get('Minutes played') or 0, s.get('Expected goals (xG)') or 0.0, s.get('Expected assists (xA)') or 0.0]
            return mid, rows
        except Exception:
            time.sleep(1.5 * (i + 1))
    return mid, None


if __name__ == '__main__':
    mids = list(json.load(open('core7_squads.json', encoding='utf-8')))
    try: mids += list(json.load(open('squads_2627.json', encoding='utf-8')))
    except Exception: pass
    have = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding='utf-8'):
            try: have.add(json.loads(l)['mid'])
            except Exception: pass
    todo = [m for m in dict.fromkeys(mids) if m not in have]
    print(f'ματς {len(set(mids))} · ηδη {len(have)} · για κατεβασμα {len(todo)}', flush=True)
    t0 = time.time(); n = err = 0
    with open(OUT, 'a', encoding='utf-8') as out, ThreadPoolExecutor(6) as ex:
        for mid, rows in ex.map(one, todo):
            n += 1
            if rows is None: err += 1; continue
            out.write(json.dumps({'mid': mid, 'p': rows}, ensure_ascii=False) + '\n')
            if n % 500 == 0:
                out.flush(); r = n / (time.time() - t0)
                print(f'  {n}/{len(todo)} · σφαλματα {err} · {r:.1f}/s · ETA {(len(todo) - n) / max(r, .1) / 60:.0f}′', flush=True)
    print(f'ΤΕΛΟΣ {n} · σφαλματα {err} · {(time.time() - t0) / 60:.0f}′')
