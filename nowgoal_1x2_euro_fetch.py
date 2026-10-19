# -*- coding: utf-8 -*-
"""nowgoal_1x2_euro_fetch.py — 19/10/2026: 1Χ2 ανοιγμα/κλεισιμο (Pinnacle, αλλιως Bet365, Crown, SBOBET) για τα ΕΥΡΩΠΑΙΚΑ ματς 2021-26
(UCL/UEL/UECL) απο 1x2.nowgoal26.com/{ng}.js — για το τεστ «απλη νικη / εκτος ζωνης». Αντιστοιχιση mid→ng απο nowgoal_odds/*_{UCL,UEL,UECL}.jsonl.
Ιδια συναρτηση με nowgoal_1x2_fetch. Εξοδος: nowgoal_1x2_euro.jsonl (resumable)."""
import sys, os, json, re, gzip, time, glob, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8')
H = 'https://1x2.nowgoal26.com'; OUT = 'nowgoal_1x2_euro.jsonl'
MAP = {}
for f in glob.glob('nowgoal_odds/*_UCL.jsonl') + glob.glob('nowgoal_odds/*_UEL.jsonl') + glob.glob('nowgoal_odds/*_UECL.jsonl'):
    for l in open(f, encoding='utf-8'):
        try: r = json.loads(l); MAP.setdefault(str(r['mid']), int(r['ng']))
        except Exception: pass
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding='utf-8'):
        try: done.add(json.loads(l)['mid'])
        except Exception: pass
todo = [m for m in MAP if m not in done]
print(f'ευρωπαικα με Nowgoal id {len(MAP)} · ηδη {len(done)} · προς κατεβασμα {len(todo)}', flush=True)
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
import collections
print(f'ΤΕΛΟΣ: {len(rows)} · με τιμες {sum(1 for r in rows if r.get("book"))} · βιβλια {dict(collections.Counter(r.get("book") for r in rows))}')
