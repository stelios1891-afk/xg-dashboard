# -*- coding: utf-8 -*-
"""nba_br_fetch.py — NBA: στατιστικα ομαδας ανα ματς (και του αντιπαλου) απο Basketball-Reference team game logs (26/9/2026).
URL: basketball-reference.com/teams/{TM}/{YYYY}/gamelog/ (YYYY = ετος ληξης). 30 ομαδες × σεζον 2021..2026.
Κραταμε ΟΛΑ τα data-stat πεδια καθε γραμμης + σε ποιον πινακα ανηκει (κανονικη περιοδος / playoffs).
ΣΕΒΑΣΜΟΣ ορου B-R: 4 δευτ. αναμονη. Cache: bbref_cache/nba_gl_*.html. Εξοδος: nba_gamelogs.csv"""
import os, re, sys, time, html, urllib.request, urllib.error
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'
CACHE = 'bbref_cache'; os.makedirs(CACHE, exist_ok=True)
TEAMS = 'ATL BOS BRK CHO CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHO POR SAC SAS TOR UTA WAS'.split()
YEARS = range(2021, 2027)
def get(url, fn):
    p = os.path.join(CACHE, fn)
    if os.path.exists(p) and os.path.getsize(p) > 1000: return open(p, encoding='utf-8').read()
    for a in range(4):
        try:
            time.sleep(4.0)
            t = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read().decode('utf-8', 'replace')
            open(p, 'w', encoding='utf-8').write(t); return t
        except urllib.error.HTTPError as e:
            if e.code == 404: return ''
            print(f'  HTTP {e.code} {url}', flush=True); time.sleep(90 if e.code == 429 else 10)
        except Exception as e:
            print(f'  {e}', flush=True); time.sleep(10)
    return ''
rows = []
for yr in YEARS:
    for tm in TEAMS:
        t = get(f'https://www.basketball-reference.com/teams/{tm}/{yr}/gamelog/', f'nba_gl_{tm}_{yr}.html')
        if not t: continue
        t = re.sub(r'<!--|-->', '', t)
        for tb in re.finditer(r'<table[^>]*?\sid="([^"]+)"[^>]*>(.*?)</table>', t, flags=re.S):
            tid, body = tb.group(1), tb.group(2)
            if 'game_log' not in tid and 'gamelog' not in tid: continue
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', body, flags=re.S):
                cells = dict((k, html.unescape(re.sub(r'<[^>]+>', '', v)).strip()) for k, v in re.findall(r'data-stat="([a-z_0-9]+)"[^>]*>(.*?)</t[dh]>', tr, flags=re.S))
                if not cells.get('date') or cells.get('date') == 'Date': continue
                cells.update(team=tm, season_end=yr, table=tid); rows.append(cells)
    df = pd.DataFrame(rows)
    df.to_csv('nba_gamelogs.csv', index=False)
    print(f'{yr}: γραμμες ως τωρα {len(df)} · πινακες {df[df.season_end == yr].table.value_counts().to_dict()}', flush=True)
print('ΤΕΛΟΣ')
