"""
weather_fetch.py — 5/10/2026 (Στελιος «τρεξε το πληρες τεστ καιρου»): ΣΥΛΛΟΓΗ για τον καιρο στις CORE7. Resumable.
1. ΓΗΠΕΔΑ: FotMob matchDetails → infoBox.Stadium (ονομα, lat, long, επιφανεια) για 1 εντος ματς ανα ομαδα-σεζον → weather_stadiums.json
2. ΚΑΙΡΟΣ ΠΟΥ ΕΚΑΝΕ: Open-Meteo archive (ERA5, ωριαιος) ανα γηπεδο, ΜΟΝΟ τις μερες εντος ματς (ενα αιτημα ανα γηπεδο-σεζον: απο την 1η ως την τελευταια μερα)
   → weather_cache/act_{lat}_{lon}_{sea}.json
3. ΠΡΟΓΝΩΣΗ: Open-Meteo previous-runs (προγνωση 1 και 3 ημερες πριν) — μονο 2024+ → weather_cache/fc_{lat}_{lon}_{sea}.json
Ορια Open-Meteo (δωρεαν): σε 429 περιμενει· αν συνεχιζει, σταματα ησυχα — ξανατρεξε αργοτερα, συνεχιζει απ' οπου εμεινε.
"""
import os, sys, json, gzip, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEAS = ['2122', '2223', '2324', '2425', '2526', '2627']
ST_F = 'weather_stadiums.json'; CD = 'weather_cache'; os.makedirs(CD, exist_ok=True)
H = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
def get(u, hdr=H, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=hdr), timeout=60).read()
            return json.loads(gzip.decompress(r) if r[:2] == b'\x1f\x8b' else r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 65 if i < 2 else 900
                print(f'  429 (ορια) — αναμονη {w}s', flush=True); time.sleep(w); continue
            if i == tries - 1: raise
            time.sleep(2 + 2 * i)
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 + 2 * i)
    raise RuntimeError('429 επιμενει')
# ---- 1. γηπεδα ----
ST = json.load(open(ST_F, encoding='utf-8')) if os.path.exists(ST_F) else {}
DAYS = {}                                                # (lg, sea, team_id) -> λιστα ημερομηνιων εντος
for lg in LG:
    for sea in SEAS:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        first = {}
        for mid, m in d.items():
            if m.get('hs') is None: continue
            t = str(m['home']['id']); day = time.strftime('%Y-%m-%d', time.strptime(m['date'].replace(' UTC', ''), '%a, %b %d, %Y, %H:%M'))
            DAYS.setdefault((lg, sea, t), []).append(day); first.setdefault(t, mid)
        n = 0
        for t, mid in first.items():
            k = f'{lg}|{sea}|{t}'
            if k in ST: continue
            try:
                ib = get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')['content']['matchFacts'].get('infoBox', {})
                s = ib.get('Stadium') or {}
                ST[k] = dict(name=s.get('name'), lat=s.get('lat'), lon=s.get('long'), surface=s.get('surface'), city=s.get('city'))
                n += 1
            except Exception as e:
                print('  γηπεδο σφαλμα', k, str(e)[:60])
            time.sleep(0.3)
        if n:
            json.dump(ST, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0); print(f'γηπεδα {lg} {sea}: +{n}', flush=True)
json.dump(ST, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(f'γηπεδα: {len(ST)} ομαδες-σεζον · με συντεταγμενες {sum(1 for v in ST.values() if v.get("lat"))}', flush=True)
# ---- 2-3. καιρος ανα γηπεδο-σεζον ----
VARS = 'temperature_2m,relative_humidity_2m,precipitation,snowfall,wind_speed_10m,wind_gusts_10m'
FVARS = ','.join(f'{v}_previous_day{d}' for v in ('temperature_2m', 'precipitation', 'wind_speed_10m', 'wind_gusts_10m') for d in (1, 3))
jobs = {}
for (lg, sea, t), days in DAYS.items():
    s = ST.get(f'{lg}|{sea}|{t}') or {}
    if s.get('lat') is None: continue
    key = (round(float(s['lat']), 2), round(float(s['lon']), 2), sea)
    jobs.setdefault(key, set()).update(days)
done = 0; fail = 0
PRI = {'2526': 0, '2425': 1, '2324': 2, '2223': 3, '2627': 4, '2122': 5}     # σεζον με γραμμες αγορας πρωτα· μετα προγνωσεις
ORDER = sorted(((kind, k) for k in jobs for kind in ('act', 'fc')), key=lambda z: (z[0] != 'act', PRI[z[1][2]], z[1]))
for kind, (la, lo, sea) in ORDER:
    days = jobs[(la, lo, sea)]; a, b = min(days), max(days)
    if True:
        if kind == 'fc' and b < '2024-01-15': continue
        f = os.path.join(CD, f'{kind}_{la}_{lo}_{sea}.json')
        if os.path.exists(f): continue
        aa = max(a, '2024-01-15') if kind == 'fc' else a
        u = (f'https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}&start_date={aa}&end_date={b}&hourly={VARS}&timezone=UTC'
             if kind == 'act' else
             f'https://previous-runs-api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&start_date={aa}&end_date={b}&hourly={FVARS}&timezone=UTC')
        try:
            x = get(u, {'User-Agent': 'Mozilla/5.0'})
            hh = x['hourly']; keep = [i for i, tm in enumerate(hh['time']) if tm[:10] in days]
            json.dump({k: [v[i] for i in keep] for k, v in hh.items()}, open(f, 'w', encoding='utf-8'))
            done += 1
            if done % 25 == 0: print(f'  καιρος: {done} αρχεια ({kind} {sea})', flush=True)
        except Exception as e:
            fail += 1; print('  καιρος σφαλμα', kind, la, lo, sea, str(e)[:80], flush=True)
            if 'επιμενει' in str(e): print('ΣΤΑΜΑΤΩ — ορια Open-Meteo· ξανατρεξε αργοτερα'); sys.exit(0)
        time.sleep(0.4)
print(f'ΤΕΛΟΣ καιρου: {done} νεα αρχεια · σφαλματα {fail} · συνολο θεσεων-σεζον {len(jobs)}')
