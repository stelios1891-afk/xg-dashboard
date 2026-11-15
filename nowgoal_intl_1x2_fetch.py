"""
nowgoal_intl_1x2_fetch.py — ΙΣΤΟΡΙΚΟ 1Χ2 ΠΡΙΝ ΤΗ ΣΕΝΤΡΑ (Crown & SBOBET) για τα διεθνη ματς του nowgoal_intl_map.json (2/10/2026).
Αφορμη: το 'op' του nowgoal_intl_odds_fetch (soccerajax type=14) ειναι ~95% in-play. Η σωστη πηγη (Στελιος: «το nowgoal εχει 1Χ2»):
  https://1x2.nowgoal26.com/{ng}.js → game = Array("cid|oddsId|Ονομα|αρχ1|αρχX|αρχ2|...|τελ1|τελX|τελ2|...") ·
  gameDetail = Array("oddsId^1|X|2|MM-DD HH:MM|...;..."  — ΟΛΕΣ οι pre-match αλλαγες, ωρα UTC+8, νεοτερη πρωτη).
Εξοδος: nowgoal_intl_1x2.jsonl {mid, ng, book, open:[1,X,2], close:[1,X,2], rows:[[unix_utc, 1, X, 2], ...] (χρονολογικα)} · resumable.
Χρηση: python nowgoal_intl_1x2_fetch.py
"""
import os, re, sys, json, time, random, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
OF = 'nowgoal_intl_1x2.jsonl'
BOOKS = {'Crown': 'Crown', 'Sbobet': 'SBOBET'}
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'})
MAP = json.load(open('nowgoal_intl_map.json', encoding='utf-8'))
done = set()
if os.path.exists(OF):
    for ln in open(OF, encoding='utf-8'):
        try: done.add(json.loads(ln)['mid'])
        except Exception: pass

def parse(txt, match_date):
    game = re.search(r'var game\s*=\s*Array\((.*?)\);', txt, re.S); det = re.search(r'var gameDetail\s*=\s*Array\((.*?)\);', txt, re.S)
    if not game or not det: return {}
    rows = re.findall(r'"([^"]*)"', game.group(1)); dets = dict(x.split('^', 1) for x in re.findall(r'"([^"]*)"', det.group(1)) if '^' in x)
    y0 = int(match_date[:4]); m0 = int(match_date[5:7]); out = {}
    for r in rows:
        f = r.split('|')
        if len(f) < 13 or f[2] not in BOOKS: continue
        try: op_, cl_ = [float(x) for x in f[3:6]], [float(x) for x in f[10:13]]
        except ValueError: continue
        hist = []
        for it in dets.get(f[1], '').split(';'):
            p = it.split('|')
            if len(p) < 4: continue
            try:
                mo, dd = int(p[3][:2]), int(p[3][3:5]); hh, mi = int(p[3][6:8]), int(p[3][9:11])
                yr = y0 - 1 if mo > m0 + 6 else (y0 + 1 if mo < m0 - 6 else y0)
                t = dt.datetime(yr, mo, dd, hh, mi, tzinfo=dt.timezone.utc) - dt.timedelta(hours=8)        # UTC+8 → UTC
                hist.append([int(t.timestamp()), float(p[0]), float(p[1]), float(p[2])])
            except (ValueError, IndexError):
                continue
        hist.sort()
        out[BOOKS[f[2]]] = dict(open=op_, close=cl_, rows=hist)
    return out

n = err = 0
with open(OF, 'a', encoding='utf-8') as fo:
    for mid, m in MAP.items():
        if mid in done: continue
        ng = m['ng']
        for attempt in range(3):
            try:
                r = S.get(f'https://1x2.nowgoal26.com/{ng}.js', headers={'Referer': f'https://live11.nowgoal26.com/1x2-odds/{ng}'}, timeout=30)
                res = parse(r.text, m.get('date', '2020-01-01')); break
            except Exception as e:
                res = None; time.sleep(3 + 3 * attempt)
        if res is None:
            err += 1; continue
        for bk, v in res.items():
            fo.write(json.dumps(dict(mid=mid, ng=ng, book=bk, **v), ensure_ascii=False) + '\n')
        fo.flush(); n += 1
        if n % 100 == 0: print(f'{n} ματς · σφαλματα {err}', flush=True)
        time.sleep(0.6 + random.random() * 0.6)
print(f'ΤΕΛΟΣ: {n} ματς · σφαλματα {err}', flush=True)
