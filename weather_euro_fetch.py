"""
weather_euro_fetch.py — 6/10/2026: καιρος για τα ΕΥΡΩΠΑΙΚΑ κυπελλα (UCL/UEL/UECL, data_Europe_2122-2526). Resumable.
1. Γηπεδο ΑΝΑ ΜΑΤΣ (FotMob infoBox — πιανει και ουδετερα γηπεδα/τελικους) → weather_euro_stadiums.json {mid: name, lat, lon, day, h0}
2. Μετρηση σταθμου (Meteostat, κοντινοτεροι 3 ≤40 km, ιδια λογικη με meteostat_fetch.py) → weather_euro_ms.csv
Οι προγνωσεις (day0/day1/day3) κατεβαινουν με: python weather_fetch_day0.py euro
"""
import os, sys, json, math, time
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import weather_fetch_common as C
F = 'weather_euro_stadiums.json'
ES = json.load(open(F, encoding='utf-8')) if os.path.exists(F) else {}
H = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
n = 0
for sea in ('2526', '2425', '2324', '2223', '2122'):
    d = json.load(open(f'data_Europe_{sea}.json', encoding='utf-8'))
    for mid, m in d.items():
        if m.get('hs') is None or mid in ES: continue
        try:
            s = (C.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}', H)['content']['matchFacts'].get('infoBox') or {}).get('Stadium') or {}
            ko = pd.to_datetime(m['date'].replace(' UTC', ''), format='%a, %b %d, %Y, %H:%M')
            ES[mid] = dict(sea=sea, name=s.get('name'), lat=s.get('lat'), lon=s.get('long'), day=ko.strftime('%Y-%m-%d'), h0=ko.floor('h').strftime('%Y-%m-%dT%H:00'))
            n += 1
        except Exception as e:
            print('  σφαλμα', mid, str(e)[:60], flush=True)
        if n and n % 200 == 0:
            json.dump(ES, open(F, 'w', encoding='utf-8'), ensure_ascii=False); print(f'  γηπεδα: {len(ES)}', flush=True)
        time.sleep(0.25)
json.dump(ES, open(F, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'γηπεδα Ευρωπης: {len(ES)} ματς · με συντεταγμενες {sum(1 for v in ES.values() if v.get("lat"))}', flush=True)
# ---- Meteostat ----
import gzip
MC = 'meteostat_cache'
STN = json.load(gzip.open(os.path.join(MC, 'stations.json.gz')))
STN = [s for s in STN if (s['inventory']['hourly']['end'] or '') >= '2022-06-01' and (s['inventory']['hourly']['start'] or '9') <= '2021-08-01']
def km(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
def dl(sid):
    f = os.path.join(MC, f'{sid}.csv.gz')
    if not os.path.exists(f):
        import urllib.request
        for i in range(4):
            try: urllib.request.urlretrieve(f'https://bulk.meteostat.net/v2/hourly/{sid}.csv.gz', f); break
            except Exception:
                if i == 3: raise
                time.sleep(3)
    return f
COLS = 'date hour temp dwpt rhum prcp snow wdir wspd wpgt pres tsun coco'.split()
CACHE = {}
def station(sid):
    if sid not in CACHE:
        d = pd.read_csv(dl(sid), header=None, names=COLS); d = d[d.date >= '2021-07-01']
        d.index = pd.to_datetime(d.date) + pd.to_timedelta(d.hour, unit='h'); CACHE[sid] = d[['temp', 'prcp', 'wspd', 'wpgt', 'coco']]
        if len(CACHE) > 40: CACHE.pop(next(iter(CACHE)))
    return CACHE[sid]
M = pd.DataFrame([dict(mid=k, lat=round(float(v['lat']), 2), lon=round(float(v['lon']), 2), h0=pd.Timestamp(v['h0'])) for k, v in ES.items() if v.get('lat') is not None])
out = []
for k, ((la, lo), mm) in enumerate(M.groupby(['lat', 'lon'])):
    near = sorted(((km(la, lo, s['location']['latitude'], s['location']['longitude']), s['id']) for s in STN))[:3]
    near = [x for x in near if x[0] <= 40]
    best = None
    for dkm, sid in near:
        try: W = station(sid)
        except Exception as e: print('  σταθμος σφαλμα', sid, str(e)[:50]); continue
        hrs = W.reindex(mm.h0); score = hrs.prcp.notna().mean() + hrs.wpgt.notna().mean() + hrs.temp.notna().mean() - dkm / 200
        if best is None or score > best[0]: best = (score, sid, dkm, W)
    if best is None: continue
    _, sid, dkm, W = best
    for r in mm.itertuples():
        w2 = W.reindex([r.h0, r.h0 + pd.Timedelta(hours=1)])
        f = lambda s, fn: fn(s.dropna()) if s.notna().any() else np.nan
        out.append(dict(mid=r.mid, temp=f(w2.temp, np.mean), rain=f(w2.prcp, np.sum), wind=f(w2.wspd, np.mean), gust=f(w2.wpgt, np.max), station=sid, km=round(dkm, 1)))
    if (k + 1) % 50 == 0: print(f'  σταθμοι: θεση {k + 1}', flush=True)
O = pd.DataFrame(out); O.to_csv('weather_euro_ms.csv', index=False)
print(f'ΤΕΛΟΣ: {len(O)} ματς με σταθμο · βροχη {O.rain.notna().mean():.0%} · μεσος σταθμος {O.km.mean():.0f} km')
