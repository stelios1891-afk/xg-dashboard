"""NFL προγνωση καιρου ανα ματς (Open-Meteo previous-runs, δωρεαν, 2024+) → nfl_data/weather_fc.csv

  python nfl_weather.py

Για καθε ματς σε ΑΝΟΙΧΤΟ γηπεδο (outdoors/open — τα κλειστα και με συρομενη σκεπη μετρανε 0) 2024→σημερα:
μεσος ορος 3 ωρων απο την εναρξη για ανεμο (mph), ριπες (mph), θερμοκρασια (°F) και αθροισμα βροχης (mm),
οπως τα εβλεπε η προγνωση: d3 = 3 μερες πριν, d1 = 1 μερα πριν, d0 = η πιο προσφατη (ιδια μερα).
"""
import json, os, time, urllib.request
import numpy as np
import pandas as pd
import nfl_model as M

D = M.D
CACHE = os.path.join(D, 'cache', 'weather')
COORD = {
    'BAL00': (39.278, -76.623), 'BOS00': (42.091, -71.264), 'BUF00': (42.774, -78.787), 'BUF01': (42.774, -78.787),
    'CAR00': (35.226, -80.853), 'CHI98': (41.862, -87.617), 'CIN00': (39.095, -84.516), 'CLE00': (41.506, -81.699),
    'DEN00': (39.744, -105.020), 'GNB00': (44.501, -88.062), 'JAX00': (30.324, -81.637), 'KAN00': (39.049, -94.484),
    'MIA00': (25.958, -80.239), 'NAS00': (36.166, -86.771), 'NYC01': (40.813, -74.074), 'PHI00': (39.901, -75.168),
    'PIT00': (40.447, -80.016), 'SEA00': (47.595, -122.332), 'SFO01': (37.403, -121.970), 'TAM00': (27.976, -82.503),
    'WAS00': (38.908, -76.864), 'LON00': (51.556, -0.280), 'LON02': (51.604, -0.066), 'FRA00': (50.069, 8.645),
    'GER00': (48.219, 11.625), 'MEX00': (19.303, -99.150), 'SAO00': (-23.545, -46.474), 'RIO00': (-22.912, -43.230),
    'ATL97': (33.755, -84.401), 'DAL00': (32.748, -97.093), 'HOU00': (29.685, -95.411), 'IND00': (39.760, -86.164),
    'PHO00': (33.528, -112.263), 'MAD01': (40.453, -3.688), 'DUB00': (53.335, -6.228),
}
BASEV = ['temperature_2m', 'precipitation', 'wind_speed_10m', 'wind_gusts_10m']
VARS = BASEV + [f'{v}_previous_day{d}' for v in BASEV for d in (1, 3)]


def fetch(sid, start, end):
    f = os.path.join(CACHE, f'{sid}_{start}_{end}.json')
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    la, lo = COORD[sid]
    u = (f'https://previous-runs-api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&start_date={start}'
         f'&end_date={end}&hourly={",".join(VARS)}&timezone=UTC&wind_speed_unit=mph&temperature_unit=fahrenheit')
    for k in range(6):
        try:
            x = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=90).read())
            json.dump(x['hourly'], open(f, 'w', encoding='utf-8'))
            time.sleep(0.5)
            return x['hourly']
        except Exception as e:
            print('  σφαλμα', sid, start, str(e)[:80], flush=True)
            time.sleep(10 * (k + 1))
    return None


def main():
    os.makedirs(CACHE, exist_ok=True)
    g = pd.read_csv(os.path.join(D, 'games.csv'), low_memory=False)
    g = g[(g.season >= 2024) & g.gametime.notna()].copy()
    g['ko'] = pd.to_datetime(g.gameday + ' ' + g.gametime).dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    g = g[g.ko < pd.Timestamp.now(tz='UTC') + pd.Timedelta(days=3)]
    out = []
    for (sid, S), x in g.groupby(['stadium_id', 'season']):
        if sid not in COORD:
            print('  χωρις συντεταγμενες:', sid, x.stadium.iloc[0]); continue
        start = (x.ko.min() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        end = (x.ko.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        h = fetch(sid, start, end)
        if h is None:
            continue
        t = pd.to_datetime(h['time']).tz_localize('UTC')
        H = pd.DataFrame({k: v for k, v in h.items() if k != 'time'}, index=t)
        for r in x.itertuples():
            w = H[(H.index >= r.ko.floor('h')) & (H.index < r.ko.floor('h') + pd.Timedelta(hours=3))]
            rec = {'game_id': r.game_id, 'roof': r.roof}
            for lab, suf in (('d0', ''), ('d1', '_previous_day1'), ('d3', '_previous_day3')):
                rec[f'wind_{lab}'] = w[f'wind_speed_10m{suf}'].mean()
                rec[f'gust_{lab}'] = w[f'wind_gusts_10m{suf}'].mean()
                rec[f'temp_{lab}'] = w[f'temperature_2m{suf}'].mean()
                rec[f'rain_{lab}'] = w[f'precipitation{suf}'].sum(min_count=1)
            out.append(rec)
        print(sid, S, len(x), flush=True)
    d = pd.DataFrame(out)
    d.to_csv(os.path.join(D, 'weather_fc.csv'), index=False)
    print('ματς', len(d), '· με d1:', d.wind_d1.notna().sum(), '· με d3:', d.wind_d3.notna().sum())


if __name__ == '__main__':
    main()
