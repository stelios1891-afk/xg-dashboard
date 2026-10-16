"""venue_fetch_all.py — 16/10/2026: συντεταγμενες γηπεδου για ΟΛΕΣ τις ομαδες του ημερολογιου ευρωπαικων ομαδων (ευρωπαικα + προκριματικα
+ ΟΛΑ τα εγχωρια data_<λιγκα>_<σεζον>.json) — το venues.json ειχε 301 (52% των ευρωπαικων ομαδων χωρις). Ιδια μεθοδος με venue_fetch.py."""
import sys, os, json, glob, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
from discover import get
ids = set()
for f in ['europe_fixtures.json', 'europe_fixtures_2627.json', 'euq_fixtures.json']:
    if os.path.exists(f):
        for rows in json.load(open(f, encoding='utf-8')).values():
            for m in rows:
                for k in ('hid', 'aid'):
                    try: ids.add(int(m[k]))
                    except Exception: pass
for f in glob.glob('data_*_*.json'):
    try: D = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for m in (D.values() if isinstance(D, dict) else D):
        try: ids.add(int(m['home']['id'])); ids.add(int(m['away']['id']))
        except Exception: pass
OUT = 'venues.json'
cache = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
todo = [t for t in sorted(ids) if str(t) not in cache or not (cache[str(t)] or {}).get('lat')]
print('ομαδες: %d · cache: %d · προς κατεβασμα: %d' % (len(ids), len(cache), len(todo)), flush=True)
def one(tid):
    for i in range(3):
        try:
            d = json.loads(get(f'https://www.fotmob.com/api/data/teams?id={tid}'))
            w = ((d.get('overview') or {}).get('venue') or {}).get('widget') or {}
            loc = w.get('location') or [None, None]
            return tid, dict(name=(d.get('details') or {}).get('name') or '', stadium=w.get('name'), city=w.get('city'),
                             lat=float(loc[0]) if loc[0] else None, lon=float(loc[1]) if loc[1] else None)
        except Exception:
            time.sleep(0.8 * (i + 1))
    return tid, None
done = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    for f in as_completed([ex.submit(one, t) for t in todo]):
        tid, rec = f.result()
        if rec or str(tid) not in cache: cache[str(tid)] = rec
        done += 1
        if done % 200 == 0:
            print('  %d/%d' % (done, len(todo)), flush=True); json.dump(cache, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(cache, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
ok = sum(1 for v in cache.values() if v and v.get('lat'))
print('ΤΕΛΟΣ: %d ομαδες · με συντεταγμενες %d (%.0f%%)' % (len(cache), ok, ok / len(cache) * 100))
