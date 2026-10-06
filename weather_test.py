"""
weather_test.py — 5/10/2026 (Στελιος «τρεξε το πληρες τεστ»): ΚΑΙΡΟΣ στις CORE7 (2122-2526 + φετινα).
Καιρος στο γηπεδο (weather_fetch.py): ωρα σεντρας + επομενη ωρα (μεσος ανεμου/θερμοκρασιας, αθροισμα βροχης) + βροχη 6 ωρες πριν (βρεγμενο γηπεδο).
Γηπεδα με κλειστη/πτυσσομενη οροφη → χωριστα (ελεγχος).
(1) ΤΙ ΚΑΝΕΙ ΣΤΟ ΜΑΤΣ: γκολ, xG, σουτ, xG/σουτ, «μακρινα» σουτ (xG<0.04), στατικες φασεις — ΚΑΙ πανω απο τη γραμμη αγορας (συνολο Crown κλεισιμο → αναμενομενα γκολ).
(2) ΤΙΜΟΛΟΓΕΙ Η ΑΓΟΡΑ; γκολ − αναμενομενα αγορας ανα κατηγορια · τυφλο OVER/UNDER: Crown κλεισιμο & ανοιγμα, Bet365 κλεισιμο, Pinnacle 2.5 κλεισιμο.
(3) ΕΔΡΑ σε ακραιο καιρο: διαφορα γκολ − υπεροχη τελικης γραμμης Pinnacle.
(4) ΠΡΟΓΝΩΣΗ (2024+): προγνωση 3 & 1 μερα πριν → κινειται η γραμμη συνολου ανοιγμα→κλεισιμο; αξια στο ανοιγμα αν η προγνωση λεει «κακος καιρος»;
Κριτηρια ΠΡΟ-ΔΗΛΩΜΕΝΑ: μια κατηγορια καιρου «μετραει για στοιχημα» μονο αν (α) γκολ − αγορα ≥ 2 SE, (β) ιδιο προσημο σε ≥3/4 σεζον 2223-2526,
(γ) ιδιο προσημο και στις ΔΥΟ πηγες καιρου (Open-Meteo ERA5 & Meteostat σταθμοι), (δ) τυφλο under/over θετικο σε Crown ΚΑΙ Bet365 κλεισιμο. Τιποτα live χωρις νεα αποφαση.
"""
import os, sys, io, json, glob, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEAS = ['2122', '2223', '2324', '2425', '2526', '2627']
ST = json.load(open('weather_stadiums.json', encoding='utf-8'))
SRC = os.environ.get('WX_SRC', 'om')     # om = Open-Meteo (ERA5) · ms = Meteostat (σταθμοι)
MS = pd.read_csv('weather_ms_match.csv', dtype={'mid': str}).set_index('mid').to_dict('index') if SRC == 'ms' else {}
ROOF = ('johan cruijff', 'gelredome', 'deutsche bank park', 'veltins', 'pierre-mauroy', 'pierre mauroy', 'bernab')
WX = {}
def wx(kind, la, lo, sea):
    k = (kind, la, lo, sea)
    if k not in WX:
        f = f'weather_cache/{kind}_{la}_{lo}_{sea}.json'
        WX[k] = None
        if os.path.exists(f):
            d = json.load(open(f, encoding='utf-8')); WX[k] = (dict((t, i) for i, t in enumerate(d['time'])), d)
    return WX[k]
# ---- αγορα συνολων: Nowgoal (Crown 3, Bet365 8) ----
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
OU = {}; AHN = {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    b = os.path.basename(f)
    if '_U' in b or '_deep' in b or not any(lg in b for lg in LG): continue
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8): continue
        ah = []
        for t, u, gl, dn in (r.get('ah') or []):
            L = pl(gl)
            try: ah.append((int(t), -L, float(u) + 1, float(dn) + 1))
            except (TypeError, ValueError): pass
        if ah: AHN[(str(r['mid']), r['cid'])] = sorted(x for x in ah if x[1] is not None)
        if not r.get('ou'): continue
        rows = []
        for t, o, gl, u in r['ou']:
            L = pl(gl)
            try: rows.append((int(t), L, float(o) + 1, float(u) + 1))
            except (TypeError, ValueError): pass
        if rows: OU[(str(r['mid']), r['cid'])] = sorted(x for x in rows if x[1] is not None)
# Pinnacle: αναμενομενα γκολ απο 2.5 (κλεισιμο T_mkt / ανοιγμα T_open) — core7_goals_gap_rows (md6+)
GG = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str}).drop_duplicates('mid').set_index('mid')
PIN = GG[['T_mkt', 'T_open', 's_mkt', 'md', 'L', 'ah', 'aa']].to_dict('index')
import picks
# ---- βοηθοι ----
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
def p_over(lam, line):
    pr = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(15)]; c = 0.
    for L in parts(line):
        w = sum(p for k, p in enumerate(pr) if k - L > .01); q = sum(p for k, p in enumerate(pr) if abs(k - L) < .01)
        c += (w + 0.5 * q) / len(parts(line))
    return c
def lam_from(line, ov, un):
    tgt = (1 / ov) / (1 / ov + 1 / un); lo, hi = 0.5, 6.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if p_over(mid, line) < tgt: lo = mid
        else: hi = mid
    return (lo + hi) / 2
def settle_ou(tg, line, odds, over):
    s = 0.
    for L in parts(line):
        m = (tg - L) if over else (L - tg); s += ((odds - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts(line))
    return s
# ---- ματς ----
rows = []
for lg in LG:
    for sea in SEAS:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for mid, m in d.items():
            if m.get('hs') is None or not m.get('shots'): continue
            H = str(m['home']['id']); s = ST.get(f'{lg}|{sea}|{H}') or {}
            if s.get('lat') is None: continue
            la, lo = round(float(s['lat']), 2), round(float(s['lon']), 2)
            ko = pd.to_datetime(m['date'].replace(' UTC', ''), format='%a, %b %d, %Y, %H:%M')
            h0 = ko.floor('h').strftime('%Y-%m-%dT%H:00')
            vl = lambda W, k, js, f: f([W[k][j] for j in js if W[k][j] is not None]) if any(W[k][j] is not None for j in js) else np.nan
            if SRC == 'ms':
                w = MS.get(str(mid))
                if w is None: continue
                wd = dict(rain=w['rain'], rain_pre=w['rain_pre'], wind=w['wind'], gust=w['gust'], temp=w['temp'], hum=w['rhum'],
                          snow=1.0 if w['coco'] in (12, 13, 14, 15, 16, 19, 20, 21, 22) else 0.0, km=w['km'])
            else:
                A = wx('act', la, lo, sea)
                if A is None or h0 not in A[0]: continue
                idx, W = A; i = idx[h0]; rng = [j for j in (i, i + 1) if j < len(W['time'])]; pre6 = [j for j in range(max(0, i - 6), i)]
                wd = dict(rain=vl(W, 'precipitation', rng, sum), rain_pre=vl(W, 'precipitation', pre6, sum) if pre6 else 0.,
                          wind=vl(W, 'wind_speed_10m', rng, np.mean), gust=vl(W, 'wind_gusts_10m', rng, max), temp=vl(W, 'temperature_2m', rng, np.mean),
                          hum=vl(W, 'relative_humidity_2m', rng, np.mean), snow=vl(W, 'snowfall', rng, sum))
            rec = dict(lg=lg, sea=sea, mid=str(mid), ko=ko, stadium=s.get('name'), roof=any(r in (s.get('name') or '').lower() for r in ROOF),
                       surface=s.get('surface'), hg=m['hs'], ag=m['as'], **wd)
            sh = [x for x in m['shots'] if x.get('xg') is not None]
            rec['tg'] = m['hs'] + m['as']; rec['gd'] = m['hs'] - m['as']
            rec['txg'] = sum(x['xg'] for x in sh if x.get('sit') != 'Penalty'); rec['shots'] = len(sh)
            rec['long_sh'] = sum(1 for x in sh if x['xg'] < 0.04) / max(len(sh), 1)
            rec['setp'] = sum(1 for x in sh if x.get('sit') in ('FromCorner', 'SetPiece', 'FreeKick', 'ThrowInSetPiece')) / max(len(sh), 1)
            Hn = m['home']['id']; rec['hxg'] = sum(x['xg'] for x in sh if x.get('sit') != 'Penalty' and x['tid'] == Hn); rec['axg'] = rec['txg'] - rec['hxg']
            rec['xgps'] = rec['txg'] / max(sum(1 for x in sh if x.get('sit') != 'Penalty'), 1)
            # προγνωση
            F = wx('fc', la, lo, sea)
            if F and h0 in F[0]:
                fi = F[0][h0]; fr = [j for j in (fi, fi + 1) if j < len(F[1]['time'])]
                for dd in (1, 3):
                    rec[f'f{dd}_rain'] = vl(F[1], f'precipitation_previous_day{dd}', fr, sum)
                    rec[f'f{dd}_wind'] = vl(F[1], f'wind_speed_10m_previous_day{dd}', fr, np.mean)
                    rec[f'f{dd}_gust'] = vl(F[1], f'wind_gusts_10m_previous_day{dd}', fr, max)
                    rec[f'f{dd}_temp'] = vl(F[1], f'temperature_2m_previous_day{dd}', fr, np.mean)
            # αγορα συνολων
            kos = int(ko.tz_localize('UTC').timestamp())
            for cid, bk in ((3, 'cr'), (8, 'b365')):
                q = [x for x in OU.get((str(mid), cid), []) if x[0] <= kos + 900]
                if not q: continue
                for nm, x in (('close', q[-1]), ('open', q[0])):
                    if bk == 'b365' and nm == 'open': continue
                    rec[f'{bk}_{nm}_line'] = x[1]; rec[f'{bk}_{nm}_ov'] = x[2]; rec[f'{bk}_{nm}_un'] = x[3]
            if 'cr_close_line' in rec:
                rec['lam_close'] = lam_from(rec['cr_close_line'], rec['cr_close_ov'], rec['cr_close_un'])
            if 'cr_open_line' in rec:
                rec['lam_open'] = lam_from(rec['cr_open_line'], rec['cr_open_ov'], rec['cr_open_un'])
            pp = PIN.get(str(mid), {}); rec['smk'] = pp.get('s_mkt'); rec['pin_close'] = pp.get('T_mkt'); rec['pin_open'] = pp.get('T_open'); rec['md'] = pp.get('md')
            if pp.get('L') == pp.get('L') and pp.get('L') is not None: rec['pin_L'], rec['pin_oh'], rec['pin_oa'] = pp['L'], pp['ah'], pp['aa']
            for cid, bk in ((3, 'cr'), (8, 'b365')):
                q = [x for x in AHN.get((str(mid), cid), []) if x[0] <= kos + 900]
                if q: rec[f'{bk}_L'], rec[f'{bk}_oh'], rec[f'{bk}_oa'] = q[-1][1:]; rec[f'{bk}_Lopen'] = q[0][1]
            rows.append(rec)
X = pd.DataFrame(rows)
X.to_pickle(f'weather_rows_{SRC}.pkl')
print(f'ΠΗΓΗ ΚΑΙΡΟΥ: {"Meteostat (σταθμοι)" if SRC == "ms" else "Open-Meteo (ERA5)"}'); print(f'ματς με καιρο: {len(X)} · με γραμμη συνολου (Crown κλεισιμο): {X.lam_close.notna().sum()} · με προγνωση: {X.f1_rain.notna().sum() if "f1_rain" in X else 0} · σκεπαστα: {int(X.roof.sum())}')
print('ανα σεζον: ' + ' '.join(f'{s}:{n}' for s, n in X.groupby('sea').size().items()))
O = X[~X.roof].copy()
for c in ('lam_close',):
    O['res'] = O.tg - O.lam_close; O['res_x'] = O.txg - O.lam_close; O['res_p'] = O.tg - O.pin_close
# ---- κατηγοριες ----
CAT = {
    'ΒΡΟΧΗ (2 ωρες ματς)': [('ξερο (<0.2mm, ουτε πριν)', (O.rain < 0.2) & (O.rain_pre < 0.5)), ('βρεγμενο/ψιλη (0.2-2)', (O.rain >= 0.2) & (O.rain < 2)),
                             ('βροχη (2-6)', (O.rain >= 2) & (O.rain < 6)), ('δυνατη βροχη (≥6)', O.rain >= 6)],
    'ΑΝΕΜΟΣ (μεσος, km/h)': [('<15', O.wind < 15), ('15-25', (O.wind >= 15) & (O.wind < 25)), ('25-35', (O.wind >= 25) & (O.wind < 35)), ('≥35', O.wind >= 35)],
    'ΡΙΠΕΣ (max, km/h)': [('<40', O.gust < 40), ('40-55', (O.gust >= 40) & (O.gust < 55)), ('≥55', O.gust >= 55)],
    'ΘΕΡΜΟΚΡΑΣΙΑ (°C)': [('<2', O.temp < 2), ('2-8', (O.temp >= 2) & (O.temp < 8)), ('8-22', (O.temp >= 8) & (O.temp < 22)), ('22-28', (O.temp >= 22) & (O.temp < 28)), ('≥28', O.temp >= 28)],
    'ΧΙΟΝΙ': [('χιονι >0', O.snow > 0)],
    'ΕΠΙΦΑΝΕΙΑ': [('συνθετικο', O.surface.fillna('').str.contains('artific|hybrid', case=False) & ~O.surface.fillna('').str.contains('hybrid', case=False))],
}
def roi(d, bk, nm, over):
    y = d.dropna(subset=[f'{bk}_{nm}_line'])
    if len(y) < 20: return np.nan, len(y), ''
    p = np.array([settle_ou(t, L, o if over else u, over) for t, L, o, u in zip(y.tg, y[f'{bk}_{nm}_line'], y[f'{bk}_{nm}_ov'], y[f'{bk}_{nm}_un'])])
    ps = pd.Series(p, index=y.index).groupby(y.sea).mean()
    return p.mean(), len(y), f'{int((ps > 0).sum())}/{len(ps)}'
def line(d, lab):
    if len(d) < 25: return f'   {lab:30s} n{len(d):5d}'
    r = d.res.dropna(); se = r.std() / np.sqrt(len(r)) if len(r) > 2 else np.nan; ps = d.groupby('sea').res.mean()
    u1 = roi(d, 'cr', 'close', False); u2 = roi(d, 'b365', 'close', False); u3 = roi(d, 'cr', 'open', False); o1 = roi(d, 'cr', 'close', True); o2 = roi(d, 'b365', 'close', True)
    return (f'   {lab:30s} n{len(d):5d} · γκολ {d.tg.mean():.2f} · xG {d.txg.mean():.2f} · σουτ {d.shots.mean():.1f} · xG/σουτ {d.xgps.mean():.3f} · μακρινα {100*d.long_sh.mean():.0f}% · στατικες {100*d.setp.mean():.0f}%'
            f' || ΓΚΟΛ − ΑΓΟΡΑ Crown {r.mean():+.2f} ±{se:.2f} (σεζον θετ. {int((ps > 0).sum())}/{ps.notna().sum()}) · Pinnacle {d.res_p.mean():+.2f} · xG − αγορα {d.res_x.mean():+.2f}'
            f' · UNDER: Crown κλεισ {100*u1[0]:+.1f}% ({u1[2]}) · B365 {100*u2[0]:+.1f}% ({u2[2]}) · Crown ανοιγ {100*u3[0]:+.1f}% ({u3[2]})'
            f' · OVER: Crown κλεισ {100*o1[0]:+.1f}% ({o1[2]}) · B365 {100*o2[0]:+.1f}% ({o2[2]})')
print('\n(1)+(2) ΤΙ ΚΑΝΕΙ Ο ΚΑΙΡΟΣ & ΤΙΜΟΛΟΓΕΙ Η ΑΓΟΡΑ; (ανοιχτα γηπεδα· «ΓΚΟΛ − ΑΓΟΡΑ» = γκολ − αναμενομενα απο τη γραμμη συνολου Crown στο κλεισιμο)')
print(line(O, 'ΟΛΑ (αναφορα)'))
for title, cats in CAT.items():
    print(f'  {title}')
    for lab, cond in cats: print(line(O[cond], lab))
print(f'  ΣΚΕΠΑΣΤΑ ΓΗΠΕΔΑ (ελεγχος):'); print(line(X[X.roof].assign(res=X.tg - X.lam_close, res_x=X.txg - X.lam_close, res_p=X.tg - X.pin_close), 'σκεπαστα'))
# συνδυασμος «κακος καιρος» = βροχη ≥2 ή ανεμος ≥25 ή ριπες ≥55
BAD = (O.rain >= 2) | (O.wind >= 25) | (O.gust >= 55)
print('  ΣΥΝΔΥΑΣΜΟΣ «κακος καιρος» (βροχη ≥2 ή ανεμος ≥25 ή ριπες ≥55):'); print(line(O[BAD], 'κακος καιρος')); print(line(O[~BAD], 'κανονικος'))
# παλινδρομηση
R = O.dropna(subset=['res', 'rain', 'wind', 'temp'])
A = np.c_[np.ones(len(R)), R.rain.clip(upper=10), R.wind.clip(upper=50) / 10, (R.temp - 15) / 10, ((R.temp - 15) / 10) ** 2]
for tgt in ('res', 'res_x'):
    y = R[tgt].values; b, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ b
    se = np.sqrt(np.diag(np.linalg.inv(A.T @ A)) * (e @ e) / (len(y) - A.shape[1]))
    print(f'  ΠΑΛΙΝΔΡΟΜΗΣΗ {"γκολ" if tgt == "res" else "xG"} − αγορα: ' + ' · '.join(f'{n} {b[i]:+.3f} (t {b[i]/se[i]:+.1f})' for i, n in enumerate(['σταθ', 'βροχη/mm', 'ανεμος/10km/h', 'θερμ/10°C', 'θερμ²'])))
# ---- (3) εδρα ----
print('\n(3) ΕΔΡΑ σε ακραιο καιρο: διαφορα γκολ γηπεδουχου − υπεροχη τελικης γραμμης Pinnacle')
O['sres'] = O.gd - O.smk
for lab, cond in (('ολα', O.index == O.index), ('κακος καιρος', BAD), ('κανονικος', ~BAD), ('ζεστη ≥28', O.temp >= 28), ('κρυο <2', O.temp < 2), ('ανεμος ≥35', O.wind >= 35)):
    x = O[cond].sres.dropna()
    if len(x) >= 25: print(f'   {lab:14s} n{len(x):5d} · {x.mean():+.3f} ±{x.std()/np.sqrt(len(x)):.3f}')
# ---- (3β) τυφλο χαντικαπ ΦΙΛΟΞΕΝΟΥΜΕΝΗΣ σε κακο καιρο (κλεισιμο) ----
def ahroi(d, bk, side):
    y = d.dropna(subset=[f'{bk}_L'])
    if len(y) < 20: return (np.nan, len(y), '')
    p = pd.Series([picks.settle(g_, side, L if side == 1 else -L, oh if side == 1 else oa) for g_, L, oh, oa in zip(y.gd, y[f'{bk}_L'], y[f'{bk}_oh'], y[f'{bk}_oa'])], index=y.index)
    ps = p.groupby(y.sea).mean(); return (p.mean(), len(y), f'{int((ps > 0).sum())}/{len(ps)}')
print('\n(3β) ΤΥΦΛΟ ΧΑΝΤΙΚΑΠ ΦΙΛΟΞΕΝΟΥΜΕΝΗΣ (κλεισιμο) — ROI (σεζον θετικες)')
O['fav_home'] = O.pin_L < 0
for lab, cond in (('ολα', O.index == O.index), ('κακος καιρος', BAD), ('  βροχη ≥2', O.rain >= 2), ('  ανεμος ≥25', O.wind >= 25), ('  ριπες ≥55', O.gust >= 55),
                  ('  κακος & γηπεδ. φαβορι', BAD & O.fav_home), ('  κακος & φιλοξ. φαβορι', BAD & ~O.fav_home & O.pin_L.notna()),
                  ('κρυο <2', O.temp < 2), ('ζεστη ≥28', O.temp >= 28), ('κανονικος', ~BAD)):
    x = O[cond]; r_ = [ahroi(x, b, -1) for b in ('pin', 'cr', 'b365')]
    ps = x.groupby('sea').sres.mean()
    print(f'   {lab:26s} n{len(x):5d} · γκολ γηπ. − γραμμη {x.sres.mean():+.3f} (σεζον <0: {int((ps < 0).sum())}/{ps.notna().sum()}) · '
          + ' · '.join(f'{nm} {100*v[0]:+.1f}% n{v[1]} ({v[2]})' for nm, v in zip(('Pinnacle', 'Crown', 'Bet365'), r_)))
# ---- (4) προγνωση ----
if 'f3_rain' in O:
    F = O.dropna(subset=['f3_rain', 'lam_open', 'lam_close']).copy()
    print(f'\n(4) ΠΡΟΓΝΩΣΗ (2024+, n{len(F)}): ποσο σωστη; κινει τη γραμμη; αξια στο ανοιγμα;')
    for v in ('rain', 'wind', 'temp'):
        print(f'   συσχετιση προγνωσης με πραγματικο {v}: 3 μερες {F[f"f3_{v}"].corr(F[v]):.2f} · 1 μερα {F[f"f1_{v}"].corr(F[v]):.2f}')
    F['mv'] = F.lam_close - F.lam_open
    FB3 = (F.f3_rain >= 2) | (F.f3_wind >= 25) | (F.f3_gust >= 55)
    FB1 = (F.f1_rain >= 2) | (F.f1_wind >= 25) | (F.f1_gust >= 55)
    for lab, cond in (('προγνωση 3 μερες: κακος', FB3), ('προγνωση 3 μερες: κανονικος', ~FB3), ('προγνωση 1 μερα: κακος', FB1), ('προγνωση 1 μερα: κανονικος', ~FB1),
                      ('χειροτερευσε (3μ καλος → 1μ κακος)', ~FB3 & FB1), ('καλυτερευσε (3μ κακος → 1μ καλος)', FB3 & ~FB1)):
        x = F[cond]
        if len(x) < 20: print(f'   {lab:36s} n{len(x)}'); continue
        uo = roi(x, 'cr', 'open', False); uc = roi(x, 'cr', 'close', False)
        print(f'   {lab:36s} n{len(x):4d} · κινηση γραμμης {x.mv.mean():+.3f} γκολ · γκολ − ανοιγμα {(x.tg - x.lam_open).mean():+.2f} · γκολ − κλεισιμο {(x.tg - x.lam_close).mean():+.2f}'
              f' · UNDER ανοιγμα {100*uo[0]:+.1f}% ({uo[2]}) · κλεισιμο {100*uc[0]:+.1f}% ({uc[2]})')
