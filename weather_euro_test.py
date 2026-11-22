"""
weather_euro_test.py — 6/10/2026: ΒΡΟΧΗ & ΕΔΡΑ στα ΕΥΡΩΠΑΙΚΑ κυπελλα (UCL/UEL/UECL 2122-2526) — ιδιο τεστ με CORE7.
Γραμμες: Nowgoal Crown (3) & SBOBET (31), κλεισιμο (τελευταια πριν τη σεντρα) & ανοιγμα. Pinnacle δεν εχουμε εδω.
«γηπ − γραμμη» = διαφορα γκολ γηπεδουχου + χαντικαπ γηπεδουχου (κλεισιμο Crown) → 0 = ακριβως οσο ελεγε η γραμμη.
Βροχη: σταθμος (Meteostat, ως ~3/2026) · προγνωση 1 μερα πριν & ιδιας μερας (Open-Meteo, 2024+).
Κριτηρια (ιδια με CORE7): ≥2 SE · ιδια φορα στις περισσοτερες σεζον · θετικο Crown ΚΑΙ SBOBET. Τιποτα live.
"""
import os, sys, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
ES = json.load(open('weather_euro_stadiums.json', encoding='utf-8'))
MS = pd.read_csv('weather_euro_ms.csv', dtype={'mid': str}).set_index('mid').to_dict('index') if os.path.exists('weather_euro_ms.csv') else {}
AH = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 31): continue
        q = []
        for t, u, gl, dn in (r.get('ah') or []):
            L = pl(gl)
            try: q.append((int(t), -L, float(u) + 1, float(dn) + 1))
            except (TypeError, ValueError): pass
        if q: AH[(str(r['mid']), r['cid'])] = sorted(x for x in q if x[1] is not None)
rows = []
for sea in ('2122', '2223', '2324', '2425', '2526'):
    d = json.load(open(f'data_Europe_{sea}.json', encoding='utf-8'))
    for mid, m in d.items():
        if m.get('hs') is None: continue
        s = ES.get(mid) or {}
        ko = pd.to_datetime(m['date'].replace(' UTC', ''), format='%a, %b %d, %Y, %H:%M'); kos = int(ko.tz_localize('UTC').timestamp())
        rec = dict(mid=mid, sea=sea, comp=m.get('comp'), gd=m['hs'] - m['as'], tg=m['hs'] + m['as'])
        w = MS.get(mid)
        if w: rec.update(rain_st=w['rain'], gust_st=w['gust'], temp_st=w['temp'])
        fp = f'weather_cache/eu_{mid}.json'
        if os.path.exists(fp) and s.get('h0'):
            W = json.load(open(fp, encoding='utf-8')); idx = {t: i for i, t in enumerate(W['time'])}
            if s['h0'] in idx:
                i = idx[s['h0']]; js = [j for j in (i, i + 1) if j < len(W['time'])]
                sm = lambda k: sum(W[k][j] for j in js if W[k][j] is not None) if any(W[k][j] is not None for j in js) else np.nan
                rec.update(f0_rain=sm('precipitation'), f1_rain=sm('precipitation_previous_day1'), f3_rain=sm('precipitation_previous_day3'),
                           f0_gust=max([W['wind_gusts_10m'][j] for j in js if W['wind_gusts_10m'][j] is not None] or [np.nan]))
        for cid, bk in ((3, 'cr'), (31, 'sbo')):
            q = [x for x in AH.get((mid, cid), []) if x[0] <= kos + 900]
            if q: rec[f'{bk}_L'], rec[f'{bk}_oh'], rec[f'{bk}_oa'] = q[-1][1:]; rec[f'{bk}_Lo'] = q[0][1]
        rows.append(rec)
X = pd.DataFrame(rows)
X = X[X.cr_L.notna()].copy(); X['sres'] = X.gd + X.cr_L
print(f'ΕΥΡΩΠΗ: {len(X)} ματς με γραμμη Crown · με σταθμο {X.rain_st.notna().sum() if "rain_st" in X else 0} · με προγνωση {X.f1_rain.notna().sum() if "f1_rain" in X else 0}')
def ah(d, bk):
    y = d.dropna(subset=[f'{bk}_L'])
    if len(y) < 12: return '   —  ', ''
    p = pd.Series([picks.settle(g, -1, -L, oa) for g, L, oa in zip(y.gd, y[f'{bk}_L'], y[f'{bk}_oa'])], index=y.index)
    ps = p.groupby(y.sea).mean(); return f'{100 * p.mean():+6.1f}%', f'{int((ps > 0).sum())}/{len(ps)}'
def row(d, lab):
    if len(d) < 12: return f'   {lab:40s} n{len(d):5d}'
    se = d.sres.std() / np.sqrt(len(d)); ps = d.groupby('sea').sres.mean(); mv = (d.cr_L - d.cr_Lo).mean()
    r = [ah(d, b) for b in ('cr', 'sbo')]
    return (f'   {lab:40s} n{len(d):5d} · γηπ−γραμμη {d.sres.mean():+.3f} ±{se:.3f} ({int((ps < 0).sum())}/{ps.notna().sum()} σεζον <0) · κινηση γραμμης {mv:+.3f}'
            f' · ΦΙΛΟΞ. AH: Crown {r[0][0]} ({r[0][1]}) · SBOBET {r[1][0]} ({r[1][1]})')
print(row(X, 'ΟΛΑ'))
if 'rain_st' in X:
    S = X[X.rain_st.notna()]
    print('\nΣΤΑΘΜΟΣ (εγινε)')
    print(row(S[S.rain_st < 0.2], 'στεγνο'))
    for lo, hi in ((0.2, 1), (1, 2), (2, 4), (4, 99)): print(row(S[(S.rain_st >= lo) & (S.rain_st < hi)], f'{lo}-{hi} mm'))
    print(row(S[S.rain_st >= 2], 'βροχη ≥2 (ολα)'))
    for c, g_ in S[S.rain_st >= 2].groupby('comp'): print(row(g_, f'   {c}'))
    print(row(S[S.gust_st >= 55], 'ριπες ≥55'))
if 'f1_rain' in X:
    F = X[X.f1_rain.notna()]
    print(f'\nΠΡΟΓΝΩΣΗ (2024+, n{len(F)})')
    print(row(F[F.f1_rain < 0.2], '1 μερα πριν: στεγνο'))
    for t in (1, 2, 4): print(row(F[F.f1_rain >= t], f'1 μερα πριν: ≥{t}mm'))
    for t in (1, 2, 4): print(row(F[F.f0_rain >= t], f'ιδια μερα: ≥{t}mm'))
    print(row(F[F.f3_rain >= 2], '3 μερες πριν: ≥2mm'))
    print(row(F[F.f0_gust >= 55], 'ιδια μερα: ριπες ≥55'))
