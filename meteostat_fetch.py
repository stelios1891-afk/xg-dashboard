"""
meteostat_fetch.py — 5/10/2026: ΔΕΥΤΕΡΗ ΠΗΓΗ καιρου (μετρησεις σταθμων — αεροδρομια) για το τεστ καιρου CORE7.
Γιατι: το Open-Meteo (ERA5) εχει ημερησιο οριο (~2 μερες για ολα)· το Meteostat δινει ολο το ιστορικο ενος σταθμου σε 1 αρχειο, χωρις ορια.
Οριο: τα αρχεια Meteostat φτανουν ως ~11/3/2026 → η 2526 μενει μιση, η 2627 απουσιαζει (εκει μονο Open-Meteo).
Για καθε γηπεδο: οι 3 κοντινοτεροι σταθμοι (≤40 km) με ωριαια δεδομενα· κραταμε αυτον με τα πληρεστερα βροχη/ριπες στις ωρες των ματς.
Εξοδος: weather_ms_match.csv (mid, temp, rhum, rain, rain_pre, wind, gust, coco, station, km) — ιδιοι οροι με weather_test (ωρα σεντρας + επομενη).
"""
import os, sys, json, gzip, math, time, urllib.request
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEAS = ['2122', '2223', '2324', '2425', '2526']
CD = 'meteostat_cache'; os.makedirs(CD, exist_ok=True)
def dl(u, f):
    if not os.path.exists(f):
        for i in range(4):
            try:
                urllib.request.urlretrieve(u, f); break
            except Exception as e:
                if i == 3: raise
                time.sleep(3 + 3 * i)
    return f
ST = json.load(gzip.open(dl('https://bulk.meteostat.net/v2/stations/lite.json.gz', os.path.join(CD, 'stations.json.gz'))))
ST = [s for s in ST if (s['inventory']['hourly']['end'] or '') >= '2025-06-01' and (s['inventory']['hourly']['start'] or '9') <= '2021-08-01']
def km(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
STAD = json.load(open('weather_stadiums.json', encoding='utf-8'))
# ματς
M = []
for lg in LG:
    for sea in SEAS:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for mid, m in d.items():
            if m.get('hs') is None: continue
            s = STAD.get(f'{lg}|{sea}|{m["home"]["id"]}') or {}
            if s.get('lat') is None: continue
            ko = pd.to_datetime(m['date'].replace(' UTC', ''), format='%a, %b %d, %Y, %H:%M')
            M.append((str(mid), round(float(s['lat']), 2), round(float(s['lon']), 2), ko.floor('h')))
M = pd.DataFrame(M, columns=['mid', 'lat', 'lon', 'h0'])
LOCS = M[['lat', 'lon']].drop_duplicates().values.tolist()
print(f'ματς {len(M)} · θεσεις γηπεδων {len(LOCS)}', flush=True)
COLS = 'date hour temp dwpt rhum prcp snow wdir wspd wpgt pres tsun coco'.split()
CACHE = {}
def station(sid):
    if sid not in CACHE:
        d = pd.read_csv(dl(f'https://bulk.meteostat.net/v2/hourly/{sid}.csv.gz', os.path.join(CD, f'{sid}.csv.gz')), header=None, names=COLS)
        d = d[d.date >= '2021-07-01']
        d.index = pd.to_datetime(d.date) + pd.to_timedelta(d.hour, unit='h'); CACHE[sid] = d[['temp', 'rhum', 'prcp', 'wspd', 'wpgt', 'coco']]
    return CACHE[sid]
out = []
for k, (la, lo) in enumerate(LOCS):
    near = sorted(((km(la, lo, s['location']['latitude'], s['location']['longitude']), s['id']) for s in ST))[:3]
    near = [x for x in near if x[0] <= 40] or near[:1]
    mm = M[(M.lat == la) & (M.lon == lo)]
    best = None
    for dkm, sid in near:
        try: W = station(sid)
        except Exception as e: print('  σφαλμα', sid, str(e)[:60]); continue
        hrs = W.reindex(mm.h0)
        score = hrs.prcp.notna().mean() + hrs.wpgt.notna().mean() + hrs.temp.notna().mean() - dkm / 200
        if best is None or score > best[0]: best = (score, sid, dkm, W)
    if best is None: continue
    _, sid, dkm, W = best
    for r in mm.itertuples():
        w2 = W.reindex([r.h0, r.h0 + pd.Timedelta(hours=1)]); w6 = W.reindex(pd.date_range(r.h0 - pd.Timedelta(hours=6), periods=6, freq='h'))
        f = lambda s, fn: fn(s.dropna()) if s.notna().any() else np.nan
        out.append(dict(mid=r.mid, temp=f(w2.temp, np.mean), rhum=f(w2.rhum, np.mean), rain=f(w2.prcp, np.sum), rain_pre=f(w6.prcp, np.sum),
                        wind=f(w2.wspd, np.mean), gust=f(w2.wpgt, np.max), coco=f(w2.coco, np.max), station=sid, km=round(dkm, 1)))
    if (k + 1) % 25 == 0: print(f'  θεσεις {k + 1}/{len(LOCS)}', flush=True)
O = pd.DataFrame(out); O.to_csv('weather_ms_match.csv', index=False)
print(f'ΤΕΛΟΣ: {len(O)} ματς · πληροτητα ' + ' · '.join(f'{c} {O[c].notna().mean():.0%}' for c in ('temp', 'rain', 'wind', 'gust', 'coco')) + f' · μεσος σταθμος {O.km.mean():.0f} km')
