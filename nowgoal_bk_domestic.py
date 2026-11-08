# -*- coding: utf-8 -*-
"""nowgoal_bk_domestic.py — προγραμμα ΕΓΧΩΡΙΩΝ πρωταθληματων μπασκετ απο Nowgoal (25/9/2026).
Σκοπος: ημερομηνια + εντος/εκτος των εγχωριων ματς των ομαδων Ευρωλιγκας (κουραση πριν απο διαβολοβδομαδες).
Πηγη: basketball.nowgoal26.com/jsData/matchResult/{YY-YY}/l{league}_{kind}_{year}_{month}.js (kind 1 = κανονικη περιοδος, 2 = πλει-οφ).
Γραμμη arrData: [ngid, ?, 'YYYY-MM-DD HH:MM' (ωρα Πεκινου UTC+8), homeId, awayId, hs, as, ...]
Εξοδος: bk_domestic.json {"{league}_{season}": {"teams": {id: name}, "games": [[ngid, utc_iso, home, away, hs, as, kind]]}}"""
import sys, os, re, json, time, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36', 'Referer': 'https://basketball.nowgoal26.com/'}
LEAGUES = {20: 'ACB', 17: 'GBL', 25: 'TBL', 16: 'LBA', 24: 'ISR', 19: 'LNB', 22: 'BBL', 142: 'LKL', 18: 'ABA', 23: 'VTB'}
SEASONS = [f'{y % 100:02d}-{(y + 1) % 100:02d}' for y in range(2017, 2026)]
OUT = 'bk_domestic.json'
db = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}

def get(u):
    for a in range(4):
        try:
            time.sleep(0.6)
            r = requests.get(u, headers=H, timeout=30)
            if r.status_code == 404: return None
            return r.content.decode('utf-8-sig', 'replace')
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def parse(t):
    teams = {int(m.group(1)): m.group(2) for m in re.finditer(r"\[(\d+),'[^']*','[^']*','([^']*)'", t.split('var ymList')[0])}
    ym = [tuple(map(int, x)) for x in re.findall(r'\[(\d{4}),(\d{1,2})\]', (re.search(r'var ymList = (\[.*?\]);', t, re.S) or [None, ''])[1])]
    data = re.search(r'var arrData = (\[.*?\]);', t, re.S)
    rows = []
    if data:
        for m in re.finditer(r"\[(\d+),\d+,'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})',(\d+),(\d+),([^,]*),([^,]*)", data.group(1)):
            bj = dt.datetime.strptime(m.group(2), '%Y-%m-%d %H:%M') - dt.timedelta(hours=8)
            rows.append([int(m.group(1)), bj.isoformat(), int(m.group(3)), int(m.group(4)), m.group(5), m.group(6)])
    return teams, ym, rows

for lid, lname in LEAGUES.items():
    for sea in SEASONS:
        key = f'{lname}_{sea}'
        if key in db: continue
        y0 = 2000 + int(sea[:2])
        rec = dict(teams={}, games=[])
        for kind in (1, 2):
            first = None
            for mo in (10, 11, 9, 12):
                t = get(f'https://basketball.nowgoal26.com/jsData/matchResult/{sea}/l{lid}_{kind}_{y0}_{mo}.js')
                if t and 'arrData' in t:
                    first = (mo, t); break
            if not first:
                continue
            teams, ym, rows = parse(first[1]); rec['teams'].update({str(k): v for k, v in teams.items()})
            seen = {first[0] if y0 else None}
            rec['games'] += [r + [kind] for r in rows]
            for (yy, mm) in ym:
                if yy == y0 and mm == first[0]: continue
                t = get(f'https://basketball.nowgoal26.com/jsData/matchResult/{sea}/l{lid}_{kind}_{yy}_{mm}.js')
                if not t: continue
                tm, _, rows = parse(t); rec['teams'].update({str(k): v for k, v in tm.items()})
                rec['games'] += [r + [kind] for r in rows]
        db[key] = rec
        print(f'{key}: ομαδες {len(rec["teams"])} · ματς {len(rec["games"])}', flush=True)
        json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('ΟΚ', len(db))
