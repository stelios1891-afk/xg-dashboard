# -*- coding: utf-8 -*-
"""nowgoal_bk_domestic_fill.py — ΣΥΜΠΛΗΡΩΣΗ εγχωριων σκορ (30/9/2026) στο bk_domestic.json.
Κενα που βρεθηκαν: (1) ΚΑΝΕΝΑ πλει-οφ (το παλιο script εψαχνε kind 2 σε Οκτ-Δεκ)· τα πλει-οφ ειναι στο
  jsData/matchResult/{YY-YY}/l{league}_2.js (χωρις μηνα) · (2) ABA 25-26 σταματουσε 9/2 (το ymList αλλαζει μεσα στη σεζον) ·
  (3) η τρεχουσα σεζον 26-27 δεν υπηρχε.
Κανει: πλει-οφ ολων των σεζον 17-18…25-26 · κανονικη περιοδος ΞΑΝΑ για 24-25, 25-26, 26-27 (ενωση ολων των ymList) ·
ιδια μορφη εγγραφων [ngid, utc_iso, home, away, hs, as, kind]. Ξανατρεχει με ασφαλεια (αντικαθιστα μονο οσα ξαναφερνει)."""
import sys, os, re, json, time, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36', 'Referer': 'https://basketball.nowgoal26.com/'}
LEAGUES = {20: 'ACB', 17: 'GBL', 25: 'TBL', 16: 'LBA', 24: 'ISR', 19: 'LNB', 22: 'BBL', 142: 'LKL', 18: 'ABA', 23: 'VTB'}
from el_season import Y as _CY, NG as _CUR    # 1/10: τρεχουσα σεζον αυτοματα
ALL = [f'{y % 100:02d}-{(y + 1) % 100:02d}' for y in range(2017, _CY + 1)]
RS_AGAIN = ['24-25', '25-26', _CUR]
if '--current' in sys.argv:                  # 30/9: καθημερινα στο euro-refresh — μονο η τρεχουσα σεζον (για el_domestic_live)
    ALL = RS_AGAIN = [_CUR]
OUT = 'bk_domestic.json'
db = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
BASE = 'https://basketball.nowgoal26.com/jsData/matchResult'

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
    teams = {}
    ta = re.search(r'var arrTeam = (\[.*?\]);', t, re.S)
    if ta:
        for m in re.finditer(r"\[(\d+),'[^']*','[^']*','([^']*)'", ta.group(1)): teams[int(m.group(1))] = m.group(2)
    ym = [tuple(map(int, x)) for x in re.findall(r'\[(\d{4}),(\d{1,2})\]', (re.search(r'var ymList = (\[.*?\]);', t, re.S) or [None, ''])[1])]
    rows = []
    data = re.search(r'var arrData = (\[.*?\]);', t, re.S)
    src = data.group(1) if data else t
    for m in re.finditer(r"\[(\d+),\d+,'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})',(\d+),(\d+),([^,]*),([^,]*)", src):
        bj = dt.datetime.strptime(m.group(2), '%Y-%m-%d %H:%M') - dt.timedelta(hours=8)
        rows.append([int(m.group(1)), bj.isoformat(), int(m.group(3)), int(m.group(4)), m.group(5).strip("'"), m.group(6).strip("'")])
    return teams, ym, rows

log = []
for lid, ln in LEAGUES.items():
    for sea in ALL:
        key = f'{ln}_{sea}'
        rec = db.get(key, dict(teams={}, games=[]))
        y0 = 2000 + int(sea[:2])
        changed = False
        if sea in RS_AGAIN:
            games, teams, months, done = {}, {}, set(), set()
            for mo in (9, 10, 11, 12):
                t = get(f'{BASE}/{sea}/l{lid}_1_{y0}_{mo}.js')
                if t and 'arrData' in t:
                    tm, ym, rows = parse(t); teams.update(tm); months.update(ym); done.add((y0, mo))
                    for r in rows: games[r[0]] = r + [1]
                    break
            while months - done:
                yy, mm = sorted(months - done)[0]; done.add((yy, mm))
                t = get(f'{BASE}/{sea}/l{lid}_1_{yy}_{mm}.js')
                if not t: continue
                tm, ym, rows = parse(t); teams.update(tm); months.update(ym)
                for r in rows: games[r[0]] = r + [1]
            if games:
                old_po = [g for g in rec['games'] if g[-1] == 2]
                rec = dict(teams={**rec['teams'], **{str(k): v for k, v in teams.items()}}, games=list(games.values()) + old_po); changed = True
        t = get(f'{BASE}/{sea}/l{lid}_2.js')
        if t and ('pfData' in t or 'arrData' in t):     # τα πλει-οφ ειναι στο pfData (ιδια μορφη γραμμης)
            tm, _, rows = parse(t)
            po = {r[0]: r + [2] for r in rows}
            rs = [g for g in rec['games'] if g[-1] != 2 and g[0] not in po]
            rec = dict(teams={**rec['teams'], **{str(k): v for k, v in tm.items()}}, games=rs + list(po.values())); changed = True
        if changed:
            db[key] = rec
            n1 = sum(1 for g in rec['games'] if g[-1] == 1); n2 = sum(1 for g in rec['games'] if g[-1] == 2)
            done_ = sum(1 for g in rec['games'] if str(g[4]).strip() not in ('', '-1'))
            last = max((g[1] for g in rec['games']), default='')[:10]
            print(f'{key}: κανονικη {n1} · πλει-οφ {n2} · με σκορ {done_} · τελευταιο {last}', flush=True)
            json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('ΤΕΛΟΣ')
