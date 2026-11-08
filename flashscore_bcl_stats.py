# -*- coding: utf-8 -*-
"""flashscore_bcl_stats.py — BOX SCORES Basketball Champions League απο Flashscore (6/10/2026, Στελιος «BCL σημερα»).
Ιδια μεθοδος με flashscore_bk_domestic.py (feed df_st_1_{matchId}, header x-fsign). Πρωτα ανανεωνει τη λιστα ματς BCL της τρεχουσας σεζον.
Εξοδος: προσθηκη στο fs_bk_stats.jsonl (lg = BCL_{ετος}) · fs_bk_games.json (BCL τρεχουσας σεζον)."""
import sys, re, json, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
src = open('flashscore_bk_domestic.py', encoding='utf-8').read().split("games = json.load(open(GF, encoding='utf-8'))")[0]
NS = {}; exec(src, NS)
get, events, H, HF, CUR = NS['get'], NS['events'], NS['H'], NS['HF'], NS['CUR']
GF, SF = 'fs_bk_games.json', 'fs_bk_stats.jsonl'
games = json.load(open(GF, encoding='utf-8'))
# τρεχουσα σεζον BCL (αποτελεσματα ως τωρα)
t = get('https://www.flashscore.com/basketball/europe/champions-league/results/', H)
if t:
    m = re.search(r'initialFeeds\["summary-results"\] = \{\s*data: `(.*?)`', t, re.S)
    ev = {e['id']: e for e in events(m.group(1))} if m else {}
    tid = re.search(r'ZEE÷([A-Za-z0-9]+)', t); cid = re.search(r'ZB÷(\d+)', t); sid = re.search(r'seasonId:\s*(\d+)', t)
    page = 0
    while tid and cid and sid and page < 30:
        x = get(f'https://global.flashscore.ninja/2/x/feed/tr_3_{cid.group(1)}_{tid.group(1)}_{sid.group(1)}_{page}_3_en_1', HF)
        new = events(x) if x else []
        if not new: break
        for e in new: ev[e['id']] = e
        page += 1
    old = {e['id']: e for e in games.get(f'BCL_{CUR}', [])}; old.update(ev)
    games[f'BCL_{CUR}'] = list(old.values()); json.dump(games, open(GF, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'BCL_{CUR}: {len(old)} ματς', flush=True)
done = set()
for ln in open(SF, encoding='utf-8'):
    try:
        r = json.loads(ln)
        if r.get('stats'): done.add(r['id'])
    except Exception: pass
todo = [(k, e) for k, L in games.items() if k.startswith('BCL_') for e in L if e['id'] not in done and e.get('hs') not in (None, '')]
print(f'BCL στατιστικα για κατεβασμα: {len(todo)}', flush=True)
LOCK = threading.Lock(); CNT = [0]
def one(item):
    k, e = item
    x = get(f'https://global.flashscore.ninja/2/x/feed/df_st_1_{e["id"]}', HF)
    st = {}; sec = None
    if x:
        for rec in x.split('~'):
            f = dict(z.split('÷', 1) for z in rec.split('¬') if '÷' in z)
            if 'SE' in f: sec = f['SE']
            if sec == 'Match' and 'SG' in f: st[f['SG']] = (f.get('SH'), f.get('SI'))
    with LOCK:
        with open(SF, 'a', encoding='utf-8') as fh: fh.write(json.dumps(dict(id=e['id'], lg=k, stats=st), ensure_ascii=False) + '\n')
        CNT[0] += 1
        if CNT[0] % 100 == 0: print(f'  {CNT[0]}/{len(todo)}', flush=True)
with ThreadPoolExecutor(4) as ex: list(ex.map(one, todo))
print('ΤΕΛΟΣ')
