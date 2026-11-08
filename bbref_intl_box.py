# -*- coding: utf-8 -*-
"""bbref_intl_box.py — BOX SCORES απο Basketball-Reference (international) για τα κενα του Flashscore (30/9/2026, προταση Στελιου).
Κενα: Τουρκια 2022-23 & 2024-25 · Ισραηλ 2020-21 & 2021-22.
Προγραμμα: /international/{league}/{Y}-schedule.html (Y = ετος ληξης) → συνδεσμοι /international/boxscores/{ημερ}-{ομαδα}.html
Box: πινακες box-score-visitor / box-score-home → «Team Totals» (fg, fga, fg3, fg3a, ft, fta, orb, drb, tov, pts…).
Ευγενικα: 3.5 δευτ. ανα αιτημα (οριο B-R ~20/λεπτο) · cache bbref_cache/intl_box/ · συνεχιζει απο εκει που εμεινε.
Εξοδος: bbref_intl_box.jsonl {league, season, url, date, visitor, home, v:{…}, h:{…}}"""
import sys, os, re, json, time
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}
TARGETS = [('turkey-super-league', 2025, 'TBL'), ('turkey-super-league', 2023, 'TBL'), ('israel-super-league', 2021, 'ISR'), ('israel-super-league', 2022, 'ISR')]
C = 'bbref_cache/intl_box'; os.makedirs(C, exist_ok=True)
OUT = 'bbref_intl_box.jsonl'

def get(url, fn):
    if os.path.exists(fn) and os.path.getsize(fn) > 1000: return open(fn, encoding='utf-8', errors='ignore').read()
    for a in range(4):
        time.sleep(3.5)
        try:
            r = requests.get(url, headers=H, timeout=40)
            if r.status_code == 200:
                open(fn, 'w', encoding='utf-8').write(r.text); return r.text
            if r.status_code == 429: print('  429 → παυση 2 λεπτα', flush=True); time.sleep(120)
            else: return None
        except Exception:
            time.sleep(10)
    return None

def totals(t, tid):
    m = re.search(rf'<table[^>]*id="{tid}".*?<tfoot>(.*?)</tfoot>', t, re.S)
    if not m: return None
    return {k: v for k, v in re.findall(r'data-stat="([a-z0-9_]+)"[^>]*>([^<]*)<', m.group(1)) if k != 'player'}

done = set()
if os.path.exists(OUT):
    for ln in open(OUT, encoding='utf-8'):
        try: done.add(json.loads(ln)['url'])
        except Exception: pass
for lg, y, code in TARGETS:
    t = get(f'https://www.basketball-reference.com/international/{lg}/{y}-schedule.html', f'{C}/_{lg}_{y}_schedule.html')
    if not t: print(lg, y, 'χωρις προγραμμα', flush=True); continue
    links = list(dict.fromkeys(re.findall(r'href="(/international/boxscores/[^"]+\.html)"', t)))
    print(f'{code} {y - 1}-{str(y)[2:]}: {len(links)} ματς', flush=True)
    for k, u in enumerate(links):
        if u in done: continue
        b = get('https://www.basketball-reference.com' + u, f'{C}/{u.split("/")[-1]}')
        if not b: continue
        ttl = re.search(r'<title>[^-]*-\s*(.*?) at (.*?), ([A-Z][a-z]{2} \d+, \d{4})', b)
        rec = dict(league=code, season=f'{y - 1}-{str(y)[2:]}', url=u, date=u.split('/')[-1][:10],
                   visitor=ttl.group(1).strip() if ttl else None, home=ttl.group(2).strip() if ttl else None,
                   v=totals(b, 'box-score-visitor'), h=totals(b, 'box-score-home'))
        with open(OUT, 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        if (k + 1) % 50 == 0: print(f'  {k + 1}/{len(links)}', flush=True)
print('ΤΕΛΟΣ')
