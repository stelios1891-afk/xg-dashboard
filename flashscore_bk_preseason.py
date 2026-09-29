# -*- coding: utf-8 -*-
"""flashscore_bk_preseason.py — ΦΙΛΙΚΑ & SUPER CUPS μπασκετ απο Flashscore (30/9/2026, ιδεα Στελιου: πληροφορια προετοιμασιας).
Διοργανωσεις (ετος = ετος εναρξης σεζον· η τρεχουσα χωρις ετος στο URL): world/club-friendly (ημερολογιακο ετος),
  spain/supercopa-acb, italy/lega-a-super-cup, france/lnb-super-cup, greece/super-cup, turkey/super-cup, israel/super-cup,
  europe/aba-supercup, europe/euroleague-super-cup, world/dbb-supercup.
Ιδια μεθοδος με flashscore_bk_domestic.py (σελιδα results + feed tr_… απο page 0, κωδικος ομαδας PX/PY).
Εξοδος: fs_bk_preseason.json {"{comp}_{Y}": [ματς]}"""
import sys, re, json, time
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}
HF = {**H, 'x-fsign': 'SW9D1eZo', 'Referer': 'https://www.flashscore.com/'}
COMPS = {'FRIENDLY': 'world/club-friendly', 'SC_ACB': 'spain/supercopa-acb', 'SC_LBA': 'italy/lega-a-super-cup', 'SC_LNB': 'france/lnb-super-cup',
         'SC_GBL': 'greece/super-cup', 'SC_TBL': 'turkey/super-cup', 'SC_ISR': 'israel/super-cup', 'SC_ABA': 'europe/aba-supercup',
         'SC_EL': 'europe/euroleague-super-cup', 'SC_DBB': 'world/dbb-supercup'}
S = requests.Session()
def get(u, h):
    for a in range(4):
        try:
            time.sleep(0.8); r = S.get(u, headers=h, timeout=30)
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
res = {}
for k, p in COMPS.items():
    for y in range(2021, 2027):
        t = None
        for u in ([f'https://www.flashscore.com/basketball/{p}/results/'] if y == 2026 else []) + \
                 [f'https://www.flashscore.com/basketball/{p}-{y}/results/', f'https://www.flashscore.com/basketball/{p}-{y}-{y + 1}/results/']:
            t = get(u, H)
            if t and 'allEventsCount' in t: break
            t = None
        if not t: print(f'{k}_{y}: —', flush=True); continue
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
        res[f'{k}_{y}'] = list(ev.values())
        print(f'{k}_{y}: {len(ev)} ματς', flush=True)
json.dump(res, open('fs_bk_preseason.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('ΤΕΛΟΣ')
