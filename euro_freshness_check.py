# -*- coding: utf-8 -*-
"""euro_freshness_check.py — 19/10/2026 (Στελιος: «μεχρι Δευτερα πρωι τα αποτελεσματα των ομαδων που αγωνιζονται στην Ευρωπη ΠΡΕΠΕΙ να εχουν
περασει — αναγκαιο, οχι διαπραγματευσιμο»). Τρεχει στο τελος του euro-refresh (μετα τις προβλεψεις).
Για καθε ευρωπαικο ματς των επομενων 7 ημερων (euro_projections.json) → λιγκες των 2 ομαδων (lg_h / lg_a) → FotMob: ολα τα ΤΕΛΕΙΩΜΕΝΑ ματς
της λιγκας (πανω απο 3ω πριν) ΠΡΕΠΕΙ να υπαρχουν στο data_{λιγκα}_{σεζον}.json. Για τις 9 λιγκες του Ben ελεγχεται και ποσα ματς μπηκαν απο
FotMob (συμπληρωμα, euro_live_projections). Αν λειπει ΕΣΤΩ ενα ματς ομαδας της Ευρωπης → ειδοποιηση στο info bot (Telegram).
Εξοδος: euro_freshness.json (για ελεγχο/ιστορικο)."""
import os, sys, json, gzip, time, datetime as dt, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
IDS = {'EPL': 47, 'LaLiga': 87, 'SerieA': 55, 'Bundesliga': 54, 'Ligue1': 53, 'Eredivisie': 57, 'PrimeiraLiga': 61}
try:
    import euro_refresh as ER
    IDS.update(ER.FM_SPLIT); IDS.update(ER.FM_CAL)
    SEA_SPLIT, SEA_CAL = ER.SEA_SPLIT, ER.SEA_CAL
except Exception as e:
    print(f'euro_refresh import απετυχε ({type(e).__name__}) — μονο CORE7'); SEA_SPLIT, SEA_CAL = '2627', '2026'
CAL = set(getattr(sys.modules.get('euro_refresh'), 'FM_CAL', {}) or {})


def get(url):
    for i in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read()
            return gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
        except Exception:
            if i == 2: raise
            time.sleep(2)


def season_of(lg):
    return SEA_CAL if lg in CAL else SEA_SPLIT


def fm_param(sea):
    return f'20{sea[:2]}%2F20{sea[2:]}' if len(sea) == 4 and int(sea[:2]) < 30 and sea != '2026' else sea


now = dt.datetime.now(dt.timezone.utc)
P = json.load(open('euro_projections.json', encoding='utf-8'))
M = [m for v in P.values() if isinstance(v, list) and v and isinstance(v[0], dict) and 'mid' in v[0] for m in v]
up = [m for m in M if not m.get('finished') and now <= dt.datetime.fromisoformat(m['utc'].replace('Z', '+00:00')) <= now + dt.timedelta(days=7)]
teams = {}                       # λιγκα -> {ονομα ομαδας}
for m in up:
    for side in ('h', 'a'):
        lg = m.get(f'lg_{side}')
        if lg: teams.setdefault(lg, set()).add(m['home'] if side == 'h' else m['away'])
report, missing_all = {}, []
for lg in sorted(teams):
    if lg not in IDS:
        report[lg] = dict(status='χωρις FotMob id (γκολ+Elo ή αλλη πηγη) — δεν ελεγχεται'); continue
    sea = season_of(lg); path = f'data_{lg}_{sea}.json'
    try:
        d = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={IDS[lg]}&season={fm_param(sea)}'))
    except Exception as e:
        report[lg] = dict(status=f'FotMob σφαλμα {type(e).__name__}'); missing_all.append(f'{lg}: FotMob δεν απαντησε'); continue
    arr = d.get('fixtures', {}).get('allMatches') or d.get('matches', {}).get('allMatches') or []
    fin = []
    for x in arr:
        st = x.get('status', {})
        if not st.get('finished') or st.get('cancelled') or st.get('awarded'): continue
        try: t = dt.datetime.fromisoformat(st.get('utcTime', '').replace('Z', '+00:00'))
        except Exception: continue
        if t <= now - dt.timedelta(hours=3): fin.append((str(x['id']), t, x.get('home', {}).get('name'), x.get('away', {}).get('name')))
    have = set(json.load(open(path, encoding='utf-8'))) if os.path.exists(path) else set()
    miss = [f for f in fin if f[0] not in have]
    euro_miss = [f for f in miss if f[2] in teams[lg] or f[3] in teams[lg]]
    last = max((f[1] for f in fin), default=None)
    report[lg] = dict(status='OK' if not euro_miss else 'ΛΕΙΠΟΥΝ', finished=len(fin), in_file=len(fin) - len(miss), missing=len(miss),
                      missing_euro_teams=[f'{f[1]:%d/%m} {f[2]}-{f[3]}' for f in euro_miss], last_finished=f'{last:%d/%m %H:%M}' if last else '-')
    for f in euro_miss: missing_all.append(f'{lg}: {f[1]:%d/%m} {f[2]} - {f[3]}')
    time.sleep(0.4)
ben = {}
if os.path.exists('euro_ben_fallback.json'):
    try: ben = json.load(open('euro_ben_fallback.json', encoding='utf-8'))
    except Exception: ben = {}
out = dict(checked=now.isoformat(timespec='minutes'), upcoming_matches=len(up), leagues=report, ben_fallback=ben, missing=missing_all)
json.dump(out, open('euro_freshness.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for lg, r in report.items():
    print(f'{lg:28s} {r["status"]:8s} ' + (f'τελειωμενα {r["finished"]:3d} · στο αρχειο {r["in_file"]:3d} · τελευταιο {r["last_finished"]}' if 'finished' in r else ''))
if missing_all:
    msg = ('⚠️ ΕΥΡΩΠΗ — ΛΕΙΠΟΥΝ αποτελεσματα ομαδων που παιζουν Ευρωπη (τα ratings τους ΔΕΝ ειναι ενημερωμενα):\n' +
           '\n'.join(missing_all[:25]))
    print(msg)
    try:
        import notify; notify.send(msg, channel='info')
    except Exception as e:
        print(f'notify απετυχε: {type(e).__name__}')
else:
    print(f'ΟΛΑ ΟΚ: {len(up)} ευρωπαικα ματς σε 7 μερες · ολα τα τελειωμενα ματς πρωταθληματος των ομαδων τους εχουν περασει')
