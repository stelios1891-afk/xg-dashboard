"""nowgoal_1x2_fetch.py — 16/10/2026: κλεισιμο 1Χ2 (Pinnacle, αλλιως Bet365, αλλιως Crown) απο 1x2.nowgoal26.com/{ng}.js για τα εγχωρια ματς
που χρειαζεται το travel_fatigue_full (επομενο ματς χωρις αγορα χαντικαπ/συνολων — το soccerajax του Nowgoal δεν δινει πια AH/OU απο ~6/10).
Εισοδος: travel_fatigue_B.pkl (mids) · χαρτες nowgoal_map_extra.json + nowgoal_map.json. Εξοδος: nowgoal_1x2.jsonl (resumable)."""
import sys, os, json, re, gzip, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
H = 'https://1x2.nowgoal26.com'
OUT = 'nowgoal_1x2.jsonl'
MAP = {}
for f in ('nowgoal_map.json', 'nowgoal_map_extra.json'):
    if os.path.exists(f):
        for k, v in json.load(open(f, encoding='utf-8')).items():
            if v.get('ng'): MAP.setdefault(str(k), int(v['ng']))
B = pd.read_pickle('travel_fatigue_B.pkl')
need = [m for m in B[(B.kind == 'dom') & B.rc.isna()].mid.unique() if str(m) in MAP]
extra = sys.argv[1:]                     # προαιρετικα επιπλεον mids (π.χ. δειγμα επικυρωσης)
need = list(dict.fromkeys(list(need) + [m for m in extra if m in MAP]))
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding='utf-8'):
        try: done.add(json.loads(l)['mid'])
        except Exception: pass
todo = [m for m in need if m not in done]
print(f'χρειαζονται {len(need)} · ηδη {len(need) - len(todo)} · προς κατεβασμα {len(todo)}', flush=True)
def one(mid):
    ng = MAP[mid]
    for i in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(f'{H}/{ng}.js', headers={'User-Agent': 'Mozilla/5.0', 'Referer': H}), timeout=25).read()
            if r[:2] == b'\x1f\x8b': r = gzip.decompress(r)
            t = r.decode('utf-8', 'replace')
            m = re.search(r'var game\s*=\s*Array\((.*?)\);', t, re.S)
            rows = re.findall(r'"([^"]*)"', m.group(1)) if m else []
            best = {}
            for x in rows:
                p = x.split('|')
                if len(p) < 13: continue
                try: best[p[0]] = dict(book=p[2], open=[float(p[3]), float(p[4]), float(p[5])], close=[float(p[10]), float(p[11]), float(p[12])])
                except ValueError: pass
            for cid in ('177', '281', '545', '474'):
                if cid in best: return dict(mid=mid, ng=ng, **best[cid])
            return dict(mid=mid, ng=ng, book=None)
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None
n = 0
with open(OUT, 'a', encoding='utf-8') as fh, ThreadPoolExecutor(max_workers=4) as ex:
    for f in as_completed([ex.submit(one, m) for m in todo]):
        r = f.result(); n += 1
        if r: fh.write(json.dumps(r, ensure_ascii=False) + chr(10))
        if n % 250 == 0: print(f'  {n}/{len(todo)}', flush=True)
rows = [json.loads(l) for l in open(OUT, encoding='utf-8')]
print(f'ΤΕΛΟΣ: {len(rows)} εγγραφες · με τιμες {sum(1 for r in rows if r.get("book"))} · βιβλια ' +
      str(pd.Series([r.get('book') for r in rows]).value_counts().to_dict()))
