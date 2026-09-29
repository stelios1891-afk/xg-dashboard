# -*- coding: utf-8 -*-
"""flashscore_bk_domestic.py — BOX SCORES εγχωριων πρωταθληματων απο Flashscore (30/9/2026, προταση Στελιου).
Λιστα ματς: σελιδα results της σεζον (cjs.initialFeeds, ~120 ματς) + feed «show more»
  global.flashscore.ninja/2/x/feed/tr_3_{country}_{tournament}_{seasonId}_{page}_3_en_1 (header x-fsign: SW9D1eZo).
Στατιστικα ματς: feed df_st_1_{matchId} → «Match»: 2Π/3Π/βολες (ευστ./προσπ.), ριμπαουντ, λαθη κτλ.
Λιγκες: ACB GBL TBL LBA ISR LNB BBL LKL ABA VTB · σεζον 2020-21 … 2026-27 (τρεχουσα).
Ευγενικα: ~0.7 δευτ. ανα αιτημα. Συνεχιζει απο εκει που εμεινε.
Εξοδος: fs_bk_games.json (λιστα ματς ανα λιγκα-σεζον) · fs_bk_stats.jsonl (στατιστικα ανα ματς)."""
import sys, os, re, json, time
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}
HF = {**H, 'x-fsign': 'SW9D1eZo', 'Referer': 'https://www.flashscore.com/'}
C = {'ACB': 'spain/acb', 'GBL': 'greece/basket-league', 'TBL': 'turkey/super-lig', 'LBA': 'italy/lega-a', 'ISR': 'israel/super-league',
     'LNB': 'france/lnb', 'BBL': 'germany/bbl', 'LKL': 'lithuania/lkl', 'ABA': 'europe/aba-league', 'VTB': 'russia/vtb-united-league',
     # 30/9: ευρωπαικες διοργανωσεις — συνδεουν τα πρωταθληματα (κοινη κλιμακα, «Elo» μπασκετ)
     'EL': 'europe/euroleague', 'EC': 'europe/eurocup', 'BCL': 'europe/champions-league', 'FEC': 'europe/fiba-europe-cup'}
YEARS = list(range(2020, 2027))
GF, SF = 'fs_bk_games.json', 'fs_bk_stats.jsonl'
S = requests.Session()

def get(u, headers):
    for a in range(5):
        try:
            time.sleep(0.7)
            r = S.get(u, headers=headers, timeout=30)
            if r.status_code == 200: return r.text
            if r.status_code in (403, 429): print(f'  {r.status_code} → παυση', flush=True); time.sleep(60 * (a + 1))
            else: return None
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def events(txt):
    out, stage = [], ''
    for rec in txt.split('~'):
        f = dict(x.split('÷', 1) for x in rec.split('¬') if '÷' in x)
        if 'ZA' in f: stage = f['ZA']
        if 'AA' in f and 'AE' in f:
            out.append(dict(id=f['AA'], ts=int(f.get('AD', 0) or 0), home=f.get('AE'), away=f.get('AF'),
                            hid=f.get('PX'), aid=f.get('PY'),              # 30/9: σταθερος κωδικος ομαδας Flashscore (ιδιος σε ολες τις διοργανωσεις)
                            hs=f.get('AG'), as_=f.get('AH'), stage=stage))
    return out

games = json.load(open(GF, encoding='utf-8')) if os.path.exists(GF) else {}
for k, p in C.items():
    for y in YEARS:
        key = f'{k}_{y}'
        if key in games and y < 2026 and games[key] and 'hid' in games[key][0]: continue
        u = f'https://www.flashscore.com/basketball/{p}-{y}-{y + 1}/results/' if y < 2026 else f'https://www.flashscore.com/basketball/{p}/results/'
        t = get(u, H)
        if not t: print(key, 'χωρις σελιδα', flush=True); continue
        m = re.search(r'initialFeeds\["summary-results"\] = \{\s*data: `(.*?)`', t, re.S)
        ev = {e['id']: e for e in events(m.group(1))} if m else {}
        tid = re.search(r'ZEE÷([A-Za-z0-9]+)', t); cid = re.search(r'ZB÷(\d+)', t); sid = re.search(r'seasonId:\s*(\d+)', t)
        tot = re.search(r'allEventsCount:\s*(\d+)', t)
        page = 0                                   # 30/9: η σελιδοποιηση ξεκινα απο 0 (η αρχικη σελιδα εχει μονο ~13)
        while tid and cid and sid and page < 30:
            x = get(f'https://global.flashscore.ninja/2/x/feed/tr_3_{cid.group(1)}_{tid.group(1)}_{sid.group(1)}_{page}_3_en_1', HF)
            new = events(x) if x else []
            if not new: break
            for e in new: ev[e['id']] = e
            page += 1
        games[key] = list(ev.values())
        print(f'{key}: {len(ev)} ματς (συνολο σελιδας {tot.group(1) if tot else "?"})', flush=True)
        json.dump(games, open(GF, 'w', encoding='utf-8'), ensure_ascii=False)

done = set()
if os.path.exists(SF):
    for ln in open(SF, encoding='utf-8'):
        try: done.add(json.loads(ln)['id'])
        except Exception: pass
todo = [(k, e) for k, L in games.items() for e in L if e['id'] not in done and e.get('hs') not in (None, '')]
print(f'στατιστικα: {len(done)} ετοιμα · {len(todo)} για κατεβασμα', flush=True)
import threading
from concurrent.futures import ThreadPoolExecutor
LOCK = threading.Lock(); CNT = [0]
def one(item):                                     # 30/9: 3 παραλληλα (το καθενα με την ιδια παυση 0.7")
    k, e = item
    x = get(f'https://global.flashscore.ninja/2/x/feed/df_st_1_{e["id"]}', HF)
    st = {}
    if x:
        sec = None
        for rec in x.split('~'):
            f = dict(z.split('÷', 1) for z in rec.split('¬') if '÷' in z)
            if 'SE' in f: sec = f['SE']
            if sec == 'Match' and 'SG' in f: st[f['SG']] = (f.get('SH'), f.get('SI'))
    with LOCK:
        with open(SF, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(dict(id=e['id'], lg=k, stats=st), ensure_ascii=False) + '\n')
        CNT[0] += 1
        if CNT[0] % 250 == 0: print(f'  {CNT[0]}/{len(todo)}', flush=True)
with ThreadPoolExecutor(3) as ex:
    list(ex.map(one, todo))
print('ΤΕΛΟΣ')
