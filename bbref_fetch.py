# -*- coding: utf-8 -*-
"""bbref_fetch.py — στατιστικα παικτων (συνολα σεζον) απο Basketball-Reference για τους παικτες που ερχονται στην Ευρωλιγκα
απο αλλα πρωταθληματα (25/9/2026, αξια παικτων v2 — «κενο» ~16-23% των λεπτων καθε σεζον = παικτες χωρις EL/EC περσι).
Πρωταθληματα: NBA + G League + 11 διεθνη του B-R (ACB, Ιταλια, Γαλλια, Ελλαδα, Τουρκια, Ισραηλ, ABA, EuroCup, Ευρωλιγκα, Κινα, Αυστραλια).
Σεζον: ετος ληξης 2017..2026 (2025 = 2024-25). ΣΕΒΑΣΜΟΣ ορου B-R: ≤20 αιτηματα/λεπτο → 4 δευτ. αναμονη. Cache ανα σελιδα (bbref_cache/).
Εξοδος: bbref_totals.csv (league, season_end, player, pid, team, g, mp, fg2, fg2a, fg3, fg3a, ft, fta, orb, drb, ast, stl, blk, tov, pf, pts)"""
import os, re, sys, time, html, urllib.request, urllib.error
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'
CACHE = 'bbref_cache'; os.makedirs(CACHE, exist_ok=True)
INTL = ['spain-liga-acb', 'italy-basket-serie-a', 'france-lnb-pro-a', 'greek-basket-league', 'turkey-super-league', 'israel-super-league',
        'aba-adriatic', 'eurocup', 'euroleague', 'cba-china', 'nbl-australia']
YEARS = range(2017, 2027)

def get(url, fn):
    p = os.path.join(CACHE, fn)
    if os.path.exists(p): return open(p, encoding='utf-8').read()
    for a in range(4):
        try:
            time.sleep(4.0)
            t = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read().decode('utf-8', 'replace')
            open(p, 'w', encoding='utf-8').write(t); return t
        except urllib.error.HTTPError as e:
            if e.code == 404: open(p, 'w', encoding='utf-8').write(''); return ''
            print(f'  HTTP {e.code} {url} — αναμονη', flush=True); time.sleep(90 if e.code == 429 else 10)
        except Exception as e:
            print(f'  {e} {url}', flush=True); time.sleep(10)
    return None

NUM = ['g', 'mp', 'fg2', 'fg2a', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts']
def parse(t, league, yr):
    t = re.sub(r'<!--|-->', '', t)                    # το B-R κρυβει πινακες σε σχολια
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, flags=re.S):
        cells = dict(re.findall(r'data-stat="([a-z_0-9]+)"[^>]*>(.*?)</t[dh]>', tr, flags=re.S))
        pc = cells.get('player') or cells.get('name_display')
        if not pc: continue
        m = re.search(r"href=['\"]([^'\"]+)['\"]", pc)
        name = html.unescape(re.sub(r'<[^>]+>', '', pc)).strip()
        if not m or not name: continue
        r = dict(league=league, season_end=yr, player=name, pid=m.group(1),
                 team=re.sub(r'<[^>]+>', '', cells.get('team_name') or cells.get('team_name_abbr') or cells.get('team_id') or '').strip())
        g = cells.get('g') if 'g' in cells else cells.get('games')
        cells['g'] = g
        for k in NUM:
            v = re.sub(r'<[^>]+>', '', cells.get(k) or '').strip()
            try: r[k] = float(v)
            except ValueError: r[k] = None
        rows.append(r)
    return rows

allr = []
for yr in YEARS:
    t = get(f'https://www.basketball-reference.com/leagues/NBA_{yr}_totals.html', f'NBA_{yr}.html')
    if t: allr += parse(t, 'NBA', yr)
    t = get(f'https://www.basketball-reference.com/gleague/years/gleague_{yr}_totals.html', f'gleague_{yr}.html')
    if t: allr += parse(t, 'gleague', yr)
    for lg in INTL:
        t = get(f'https://www.basketball-reference.com/international/{lg}/{yr}_totals.html', f'{lg}_{yr}.html')
        if t: allr += parse(t, lg, yr)
    df = pd.DataFrame(allr)
    print(f'{yr}: συνολο γραμμων {len(df)} · ' + ' '.join(f'{k}:{v}' for k, v in df[df.season_end == yr].league.value_counts().items()), flush=True)
    df.to_csv('bbref_totals.csv', index=False)
print('ΤΕΛΟΣ')
