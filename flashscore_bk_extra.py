# -*- coding: utf-8 -*-
"""flashscore_bk_extra.py — ΕΠΙΠΛΕΟΝ ΕΓΧΩΡΙΑ ΠΡΩΤΑΘΛΗΜΑΤΑ για το EuroCup (1/10/2026, Στελιος: «πρεπει πρωτα να βρεις ολα τα δεδομενα για ολες
τις ομαδες»). Πολωνια, Ρουμανια, Αγγλια, Βελγιο-Ολλανδια (BNXT απο 2021, πριν Βελγιο), Λετονια-Εσθονια, Ουκρανια — σεζον 2016-17 … τρεχουσα.
Ιδια μεθοδος με flashscore_bk_domestic.py (σελιδα results + feed tr_… απο page 0, κωδικος ομαδας PX/PY). Μονο αποτελεσματα (οχι στατιστικα).
Εξοδος: fs_bk_extra.json {"{LG}_{Y}": [ματς]}"""
import sys, os, re, json, time
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}
HF = {**H, 'x-fsign': 'SW9D1eZo', 'Referer': 'https://www.flashscore.com/'}
C = {'PLK': ['poland/basket-liga'], 'ROM': ['romania/divizia-a'], 'GBR': ['united-kingdom/slb'],
     'BNX': ['europe/bnxt-league', 'belgium/pro-basketball-league'], 'LEL': ['europe/latvian-estonian-league'], 'UKR': ['ukraine/superleague']}
from el_season import Y as CUR
OF = 'fs_bk_extra.json'
S = requests.Session()
def get(u, h):
    for a in range(4):
        try:
            time.sleep(0.7); r = S.get(u, headers=h, timeout=30)
            if r.status_code == 200: return r.text
            if r.status_code in (403, 429): time.sleep(60 * (a + 1))
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
            out.append(dict(id=f['AA'], ts=int(f.get('AD', 0) or 0), home=f.get('AE'), away=f.get('AF'), hid=f.get('PX'), aid=f.get('PY'),
                            hs=f.get('AG'), as_=f.get('AH'), stage=stage))
    return out
res = json.load(open(OF, encoding='utf-8')) if os.path.exists(OF) else {}
for k, paths in C.items():
    for y in range(2016, CUR + 1):
        key = f'{k}_{y}'
        if key in res and res[key] and y < CUR: continue
        t = None
        for p in paths:
            for u in ([f'https://www.flashscore.com/basketball/{p}/results/'] if y == CUR else []) + [f'https://www.flashscore.com/basketball/{p}-{y}-{y + 1}/results/']:
                t = get(u, H)
                if t and 'allEventsCount' in t: break
                t = None
            if t: break
        if not t: print(f'{key}: —', flush=True); continue
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
        res[key] = list(ev.values())
        print(f'{key}: {len(ev)} ματς', flush=True)
        json.dump(res, open(OF, 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(res, open(OF, 'w', encoding='utf-8'), ensure_ascii=False)
print('ΤΕΛΟΣ')
