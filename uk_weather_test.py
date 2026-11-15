"""
uk_weather_test.py — 6/10/2026 (Στελιος «τρεξε το τεστ πρωτα»): ΕΠΑΝΑΛΗΨΗ του ευρηματος «βροχη → γηπεδουχος κατω απο τη γραμμη» σε ΑΝΕΞΑΡΤΗΤΑ δεδομενα:
Championship / League One / League Two / Σκωτια Premiership-Championship-League One (football-data, 1920-2627).
Χωρις xG: μετραμε μονο ΓΚΟΛ vs ΓΡΑΜΜΗ — «γηπ − γραμμη» = διαφορα γκολ γηπεδουχου + χαντικαπ κλεισιματος (AHCh) → 0 = οσο ελεγε η γραμμη.
ROI: τυφλο χαντικαπ φιλοξενουμενου στο κλεισιμο Pinnacle (PCAHA) και Bet365 (B365CAHA).
Γηπεδα: πολη ανα ομαδα (χειροκινητος πινακας, ακριβεια ~πολης· ο σταθμος ειναι 10-20 km ετσι κι αλλιως). Ωρα football-data = ωρα Αγγλιας → UTC.
Καιρος: Meteostat (σταθμος, κοντινοτεροι 3 ≤40 km) — ιδια λογικη με CORE7· προγνωση 1 μερα πριν απο weather_cache/uk_fc_* αν υπαρχει (2024+).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ ΕΠΑΝΑΛΗΨΗΣ (βροχη ≥2mm στις 2 ωρες του ματς, σεζον ΜΕ κοσμο):
 (α) γηπ − γραμμη < 0 κατα ≥2 SE · (β) ιδια φορα στις περισσοτερες σεζον με κοσμο · (γ) χαντικαπ φιλοξ θετικο σε Pinnacle ΚΑΙ Bet365 ·
 (δ) ιδια φορα με προγνωση 1 μερα πριν ≥2mm (2024+).
ΜΗΧΑΝΙΣΜΟΣ: 6/2020-5/2021 χωρις κοσμο → αν η αιτια ειναι ο κοσμος, εκει η επιδραση πρεπει να χανεται.
"""
import os, sys, json, gzip, math, time, glob, urllib.request
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
TOWN = {  # ομαδα → (lat, lon) γηπεδου/πολης
 'AFC Wimbledon': (51.43, -0.19), 'Accrington': (53.77, -2.37), 'Barnet': (51.60, -0.29), 'Barnsley': (53.55, -1.47), 'Barrow': (54.12, -3.23),
 'Birmingham': (52.48, -1.87), 'Blackburn': (53.73, -2.49), 'Blackpool': (53.80, -3.05), 'Bolton': (53.58, -2.54), 'Bournemouth': (50.74, -1.84),
 'Bradford': (53.80, -1.76), 'Brentford': (51.49, -0.29), 'Bristol City': (51.44, -2.62), 'Bristol Rvs': (51.49, -2.58), 'Bromley': (51.39, 0.02),
 'Burnley': (53.79, -2.23), 'Burton': (52.82, -1.63), 'Cambridge': (52.21, 0.15), 'Cardiff': (51.47, -3.20), 'Carlisle': (54.90, -2.91),
 'Charlton': (51.49, 0.04), 'Cheltenham': (51.91, -2.06), 'Chesterfield': (53.25, -1.43), 'Colchester': (51.92, 0.90), 'Coventry': (52.45, -1.50),
 'Crawley Town': (51.10, -0.20), 'Crewe': (53.09, -2.44), 'Derby': (52.92, -1.45), 'Doncaster': (53.51, -1.11), 'Exeter': (50.73, -3.52),
 'Fleetwood Town': (53.92, -3.01), 'Forest Green': (51.69, -2.22), 'Fulham': (51.47, -0.22), 'Gillingham': (51.38, 0.56), 'Grimsby': (53.57, -0.05),
 'Harrogate': (53.99, -1.53), 'Hartlepool': (54.69, -1.22), 'Huddersfield': (53.65, -1.77), 'Hull': (53.75, -0.37), 'Ipswich': (52.05, 1.14),
 'Leeds': (53.78, -1.57), 'Leicester': (52.62, -1.14), 'Leyton Orient': (51.56, -0.01), 'Lincoln': (53.22, -0.54), 'Luton': (51.88, -0.43),
 'Macclesfield': (53.24, -2.13), 'Mansfield': (53.14, -1.20), 'Middlesbrough': (54.58, -1.22), 'Millwall': (51.49, -0.05), 'Milton Keynes Dons': (52.01, -0.73),
 'Morecambe': (54.06, -2.87), 'Newport County': (51.59, -2.99), 'Northampton': (52.24, -0.93), 'Norwich': (52.62, 1.31), "Nott'm Forest": (52.94, -1.13),
 'Notts County': (52.94, -1.14), 'Oldham': (53.56, -2.13), 'Oxford': (51.72, -1.21), 'Peterboro': (52.56, -0.24), 'Plymouth': (50.39, -4.15),
 'Port Vale': (53.05, -2.19), 'Portsmouth': (50.80, -1.06), 'Preston': (53.77, -2.69), 'QPR': (51.51, -0.23), 'Reading': (51.42, -0.98),
 'Rochdale': (53.62, -2.18), 'Rotherham': (53.43, -1.36), 'Salford': (53.51, -2.34), 'Scunthorpe': (53.59, -0.69), 'Sheffield United': (53.37, -1.47),
 'Sheffield Weds': (53.41, -1.50), 'Shrewsbury': (52.69, -2.75), 'Southampton': (50.91, -1.39), 'Southend': (51.55, 0.70), 'Stevenage': (51.89, -0.19),
 'Stockport': (53.40, -2.15), 'Stoke': (52.99, -2.18), 'Sunderland': (54.91, -1.39), 'Sutton': (51.36, -0.19), 'Swansea': (51.64, -3.93),
 'Swindon': (51.56, -1.77), 'Tranmere': (53.37, -3.03), 'Walsall': (52.57, -2.00), 'Watford': (51.65, -0.40), 'West Brom': (52.51, -1.96),
 'West Ham': (51.54, -0.02), 'Wigan': (53.55, -2.65), 'Wolves': (52.59, -2.13), 'Wrexham': (53.05, -3.00), 'Wycombe': (51.63, -0.80), 'York': (53.98, -1.05),
 'Aberdeen': (57.16, -2.09), 'Airdrie Utd': (55.86, -3.98), 'Alloa': (56.12, -3.79), 'Annan Athletic': (54.99, -3.26), 'Arbroath': (56.56, -2.59),
 'Ayr': (55.47, -4.62), 'Celtic': (55.85, -4.21), 'Clyde': (55.95, -3.99), 'Cove Rangers': (57.10, -2.11), 'Dumbarton': (55.94, -4.56),
 'Dundee': (56.47, -2.97), 'Dundee United': (56.47, -2.97), 'Dunfermline': (56.08, -3.44), 'East Fife': (56.18, -3.00), 'East Kilbride': (55.76, -4.18),
 'Edinburgh City': (55.96, -3.16), 'FC Edinburgh': (55.96, -3.16), 'Falkirk': (56.01, -3.75), 'Forfar': (56.64, -2.89), 'Hamilton': (55.78, -4.06),
 'Hearts': (55.94, -3.23), 'Hibernian': (55.96, -3.17), 'Inverness C': (57.49, -4.22), 'Kelty Hearts': (56.13, -3.38), 'Kilmarnock': (55.60, -4.51),
 'Livingston': (55.89, -3.52), 'Montrose': (56.71, -2.47), 'Morton': (55.94, -4.75), 'Motherwell': (55.78, -3.98), 'Partick': (55.88, -4.27),
 'Peterhead': (57.51, -1.80), 'Queen of Sth': (55.07, -3.61), 'Queens Park': (55.83, -4.25), 'Raith Rvs': (56.11, -3.17), 'Rangers': (55.85, -4.31),
 'Ross County': (57.60, -4.43), 'St Johnstone': (56.40, -3.48), 'St Mirren': (55.85, -4.44), 'Stenhousemuir': (56.03, -3.81), 'Stirling': (56.12, -3.93),
 'Stranraer': (54.90, -5.02)}
LGN = {'E1': 'Championship', 'E2': 'League One', 'E3': 'League Two', 'SC0': 'Σκωτια Prem', 'SC1': 'Σκωτια Champ', 'SC2': 'Σκωτια L1'}
# ---- ματς ----
M = []
for f in sorted(glob.glob('raw_fd_uk/*.csv')):
    lg, sea = os.path.basename(f)[:-4].split('_')
    try: d = pd.read_csv(f, encoding='latin-1')
    except Exception: continue
    need = ['Date', 'Time', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'AHCh', 'PCAHH', 'PCAHA', 'B365CAHH', 'B365CAHA']
    if not all(c in d.columns for c in need): print('  λειπουν στηλες', f); continue
    d = d[need].dropna(subset=['Date', 'Time', 'HomeTeam', 'FTHG'])
    for r in d.itertuples(index=False):
        if r.HomeTeam not in TOWN: print('  αγνωστη ομαδα', r.HomeTeam); continue
        try: ko = pd.to_datetime(f'{r.Date} {r.Time}', dayfirst=True).tz_localize('Europe/London', ambiguous='NaT', nonexistent='NaT').tz_convert('UTC').tz_localize(None)
        except Exception: continue
        if pd.isna(ko): continue
        la, lo = TOWN[r.HomeTeam]
        M.append(dict(lg=lg, sea=sea, home=r.HomeTeam, ko=ko, h0=ko.floor('h'), lat=la, lon=lo, gd=r.FTHG - r.FTAG, L=r.AHCh,
                      pin_oh=r.PCAHH, pin_oa=r.PCAHA, b365_oh=r.B365CAHH, b365_oa=r.B365CAHA))
M = pd.DataFrame(M)
M['nocrowd'] = (M.ko >= '2020-06-01') & (M.ko < '2021-06-01')
print(f'ματς: {len(M)} · με γραμμη κλεισιματος {M.L.notna().sum()} · χωρις κοσμο {int(M.nocrowd.sum())}', flush=True)
# ---- Meteostat ----
MC = 'meteostat_cache'
STN = json.load(gzip.open(os.path.join(MC, 'stations.json.gz')))
STN = [s for s in STN if s['country'] == 'GB' and (s['inventory']['hourly']['end'] or '') >= '2024-06-01' and (s['inventory']['hourly']['start'] or '9') <= '2019-07-01']
def km(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
COLS = 'date hour temp dwpt rhum prcp snow wdir wspd wpgt pres tsun coco'.split()
def station(sid):
    f = os.path.join(MC, f'{sid}.csv.gz')
    if not os.path.exists(f):
        for i in range(4):
            try: urllib.request.urlretrieve(f'https://bulk.meteostat.net/v2/hourly/{sid}.csv.gz', f); break
            except Exception:
                if i == 3: raise
                time.sleep(3)
    d = pd.read_csv(f, header=None, names=COLS); d = d[d.date >= '2019-07-01']
    d.index = pd.to_datetime(d.date) + pd.to_timedelta(d.hour, unit='h'); return d[['temp', 'prcp', 'wspd', 'wpgt', 'coco']]
WF = 'uk_weather_rows2.pkl'
if os.path.exists(WF):
    W = pd.read_pickle(WF)
else:
    out = []
    for k, ((la, lo), mm) in enumerate(M.groupby(['lat', 'lon'])):
        near = [x for x in sorted(((km(la, lo, s['location']['latitude'], s['location']['longitude']), s['id']) for s in STN))[:3] if x[0] <= 40]
        best = None
        for dkm, sid in near:
            try: S = station(sid)
            except Exception as e: print('  σταθμος σφαλμα', sid, str(e)[:50]); continue
            h = S.reindex(mm.h0); sc = h.prcp.notna().mean() + h.wpgt.notna().mean() - dkm / 200
            if best is None or sc > best[0]: best = (sc, sid, dkm, S)
        if best is None: continue
        _, sid, dkm, S = best
        for i, r in mm.iterrows():
            w2 = S.reindex([r.h0, r.h0 + pd.Timedelta(hours=1)])
            f_ = lambda s, fn: fn(s.dropna()) if s.notna().any() else np.nan
            out.append(dict(idx=i, rain=f_(w2.prcp, np.sum), gust=f_(w2.wpgt, np.max), wind=f_(w2.wspd, np.mean), temp=f_(w2.temp, np.mean), coco=f_(w2.coco, np.max), km=round(dkm, 1)))
        if (k + 1) % 20 == 0: print(f'  γηπεδα καιρου {k + 1}', flush=True)
    W = pd.DataFrame(out).set_index('idx'); W.to_pickle(WF)
X = M.join(W, how='left')
X['rain_mm'] = X.rain
HEAVY = X.coco.isin([8, 9, 18, 25, 26]); LIGHTDRY = X.coco.isin([1, 2, 3, 4, 5])
X['rain'] = np.where(X.rain_mm.notna(), X.rain_mm, np.where(HEAVY, 2.5, np.where(LIGHTDRY, 0.0, np.nan)))
X['rain_src'] = np.where(X.rain_mm.notna(), 'mm', np.where(X.rain.notna(), 'κωδικας', ''))
# προγνωση 1 μερα πριν (αν εχει κατεβει: uk_weather_fc.py)
FC = {}
for f in glob.glob('weather_cache/ukfc_*.json'):
    d = json.load(open(f, encoding='utf-8')); key = tuple(os.path.basename(f)[5:-5].split('_')[:2])
    FC[key] = ({t: i for i, t in enumerate(d['time'])}, d)
def fc1(r):
    z = FC.get((f'{r.lat}', f'{r.lon}'))
    if not z: return np.nan
    t = r.h0.strftime('%Y-%m-%dT%H:00')
    if t not in z[0]: return np.nan
    i = z[0][t]; v = [z[1]['precipitation_previous_day1'][j] for j in (i, i + 1) if j < len(z[1]['time']) and z[1]['precipitation_previous_day1'][j] is not None]
    return sum(v) if v else np.nan
X['f1_rain'] = [fc1(r) for r in X.itertuples()] if FC else np.nan
X = X[X.L.notna()].copy(); X['sres'] = X.gd + X.L
X.to_pickle('uk_weather_X.pkl')
def ah(d, bk):
    y = d.dropna(subset=[f'{bk}_oa'])
    if len(y) < 15: return '   —  ', ''
    p = pd.Series([picks.settle(g, -1, -L, oa) for g, L, oa in zip(y.gd, y.L, y[f'{bk}_oa'])], index=y.index)
    ps = p.groupby(y.sea).mean(); return f'{100 * p.mean():+6.1f}%', f'{int((ps > 0).sum())}/{len(ps)}'
def row(d, lab):
    if len(d) < 15: return f'   {lab:38s} n{len(d):5d}'
    se = d.sres.std() / np.sqrt(len(d)); ps = d.groupby('sea').sres.mean(); r = [ah(d, b) for b in ('pin', 'b365')]
    return (f'   {lab:38s} n{len(d):5d} · γηπ−γραμμη {d.sres.mean():+.3f} ±{se:.3f} (t {d.sres.mean() / se:+.1f}) ({int((ps < 0).sum())}/{ps.notna().sum()} σεζον <0)'
            f' · ΦΙΛΟΞ. AH: Pinnacle {r[0][0]} ({r[0][1]}) · Bet365 {r[1][0]} ({r[1][1]})')
C = X[~X.nocrowd]; N = X[X.nocrowd]
print(f'\nΣΤΑΘΜΟΣ: πληροτητα βροχης {X.rain.notna().mean():.0%} · μεσος σταθμος {X.km.mean():.0f} km')
print('\n=== ΜΕ ΚΟΣΜΟ — δοση-αποκριση (βροχη στις 2 ωρες του ματς) ===')
print(row(C, 'ολα'))
print(row(C[C.rain < 0.2], 'στεγνο'))
for lo, hi in ((0.2, 1), (1, 2), (2, 4), (4, 99)): print(row(C[(C.rain >= lo) & (C.rain < hi)], f'{lo}-{hi} mm'))
R = C[C.rain >= 2]
print(row(R, '>>> ΒΡΟΧΗ ≥2 mm (mm ή κωδικας)'))
print(row(R[R.rain_src == 'mm'], '     μονο με μετρηση mm'))
print(row(R[R.rain_src == 'κωδικας'], '     μονο απο κωδικα καιρου'))
print('   — ανα σεζον'); [print(row(g, '     ' + s)) for s, g in R.groupby('sea')]
print('   — ανα κατηγορια'); [print(row(g, '     ' + LGN[s])) for s, g in R.groupby('lg')]
print('   — ποιος φαβορι'); print(row(R[R.L <= -0.25], '     γηπεδουχος φαβορι')); print(row(R[R.L.abs() < 0.25], '     ισορροπο')); print(row(R[R.L >= 0.25], '     φιλοξενουμενος φαβορι'))
print(row(C[C.gust >= 55], 'ριπες ≥55'))
print(row(C[(C.gust >= 55) & (C.rain < 2)], 'ριπες ≥55 χωρις βροχη'))
print(row(C[C.temp < 2], 'κρυο <2'))
print('\n=== ΧΩΡΙΣ ΚΟΣΜΟ (6/2020-5/2021) — ελεγχος μηχανισμου ===')
print(row(N, 'ολα'))
print(row(N[N.rain < 0.2], 'στεγνο'))
print(row(N[N.rain >= 2], 'ΒΡΟΧΗ ≥2 mm'))
print(row(N[N.rain >= 1], 'βροχη ≥1 mm'))
if X.f1_rain.notna().any():
    F = C[C.f1_rain.notna()]
    print(f'\n=== ΠΡΟΓΝΩΣΗ 1 ΜΕΡΑ ΠΡΙΝ (2024+, n{len(F)}) ===')
    print(row(F[F.f1_rain < 0.2], 'στεγνο'))
    for t in (1, 2, 4): print(row(F[F.f1_rain >= t], f'≥{t} mm'))
# ---- κριτηρια ----
se = R.sres.std() / np.sqrt(len(R)); ps = R.groupby('sea').sres.mean()
pin = ah(R, 'pin')[0]; b3 = ah(R, 'b365')[0]
ca = R.sres.mean() / se <= -2; cb = (ps < 0).sum() > (ps >= 0).sum(); cg = pin.strip().startswith('+') and b3.strip().startswith('+')
if X.f1_rain.notna().any():
    FF = C[C.f1_rain >= 2]; cd = FF.sres.mean() < 0 if len(FF) >= 15 else None
else: cd = None
print(f'\nΚΡΙΤΗΡΙΑ ΕΠΑΝΑΛΗΨΗΣ: (α) ≥2 SE {"✓" if ca else "✗"} · (β) σεζον {int((ps < 0).sum())}/{len(ps)} {"✓" if cb else "✗"} · (γ) Pinnacle {pin} & Bet365 {b3} {"✓" if cg else "✗"} · (δ) προγνωση {"—" if cd is None else ("✓" if cd else "✗")}')
