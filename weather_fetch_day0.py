"""
weather_fetch_day0.py — 6/10/2026: ΠΡΟΓΝΩΣΗ ΙΔΙΑΣ ΜΕΡΑΣ («day0» του Open-Meteo previous-runs = η τελευταια προγνωση πριν απο την ωρα του ματς,
οριζοντας 0-24 ωρες) + 1 μερα πριν, για βροχη/ριπες. Resumable, ιδια ορια με weather_fetch.py.
  CORE7  : ανα γηπεδο-σεζον (2024+) → weather_cache/fc0_{lat}_{lon}_{sea}.json
  ΕΥΡΩΠΗ : ανα ματς (1 μερα) απο weather_euro_stadiums.json → weather_cache/eu_{mid}.json (και πραγματικος καιρος ERA5 στο ιδιο αιτημα δεν υπαρχει → μονο προγνωσεις)
Σημ.: το day0 για ωρα Χ ερχεται απο run που ξεκινησε την ιδια μερα (μπορει και λιγες ωρες πριν τη σεντρα) — κοντα σε αυτο που βλεπει κανεις λιγο πριν το ματς.
"""
import os, sys, json, time
sys.stdout.reconfigure(encoding='utf-8')
import weather_fetch_common as C
WHAT = sys.argv[1] if len(sys.argv) > 1 else 'core7'
V = 'precipitation,wind_gusts_10m,wind_speed_10m,precipitation_previous_day1,wind_gusts_10m_previous_day1,precipitation_previous_day3'
done = 0
if WHAT == 'core7':
    ST = json.load(open('weather_stadiums.json', encoding='utf-8'))
    jobs = {}
    for lg in C.LG:
        for sea in ('2324', '2425', '2526', '2627'):
            try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
            except FileNotFoundError: continue
            for mid, m in d.items():
                if m.get('hs') is None: continue
                s = ST.get(f'{lg}|{sea}|{m["home"]["id"]}') or {}
                if s.get('lat') is None: continue
                day = C.day_of(m['date'])
                if day < '2024-01-15': continue
                jobs.setdefault((round(float(s['lat']), 2), round(float(s['lon']), 2), sea), set()).add(day)
    PRI = {'2526': 0, '2425': 1, '2324': 2, '2627': 3}
    for (la, lo, sea), days in sorted(jobs.items(), key=lambda z: (PRI[z[0][2]], z[0])):
        f = os.path.join(C.CD, f'fc0_{la}_{lo}_{sea}.json')
        if os.path.exists(f): continue
        u = f'https://previous-runs-api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&start_date={min(days)}&end_date={max(days)}&hourly={V}&timezone=UTC'
        if not C.save(u, f, days): break
        done += 1
        if done % 25 == 0: print(f'  day0 CORE7: {done} αρχεια ({sea})', flush=True)
else:
    ES = json.load(open('weather_euro_stadiums.json', encoding='utf-8'))
    for mid, s in sorted(ES.items(), key=lambda z: z[1].get('day', ''), reverse=True):
        if s.get('lat') is None or s['day'] < '2024-01-15': continue
        f = os.path.join(C.CD, f'eu_{mid}.json')
        if os.path.exists(f): continue
        la, lo = round(float(s['lat']), 2), round(float(s['lon']), 2)
        u = f'https://previous-runs-api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&start_date={s["day"]}&end_date={s["day"]}&hourly={V}&timezone=UTC'
        if not C.save(u, f, {s['day']}): break
        done += 1
        if done % 100 == 0: print(f'  day0 ΕΥΡΩΠΗ: {done} ματς', flush=True)
print(f'ΤΕΛΟΣ day0 {WHAT}: {done} νεα αρχεια')
