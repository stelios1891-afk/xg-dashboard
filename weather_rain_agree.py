"""
weather_rain_agree.py — 6/10/2026: βροχη & εδρα — ΣΥΜΦΩΝΙΑ ΤΩΝ 2 ΠΗΓΩΝ + ΠΡΟΓΝΩΣΗ (αυτο που θα ηξερες πριν τη σεντρα).
Ενωνει weather_rows_ms.pkl (σταθμοι) και weather_rows_om.pkl (ERA5). Κατηγοριες: βροχη ≥2mm και στις δυο / μονο σταθμος / μονο ERA5.
Προγνωση Open-Meteo 1 & 3 μερες πριν (2024+): τυφλο χαντικαπ φιλοξενουμενου οταν η προγνωση λεει βροχη.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
A = pd.read_pickle('weather_rows_ms.pkl'); B = pd.read_pickle('weather_rows_om.pkl')
B = B[~B.roof & B.smk.notna()].copy()
B = B.merge(A[['mid', 'rain', 'gust', 'km']].rename(columns={'rain': 'rain_ms', 'gust': 'gust_ms'}), on='mid', how='left')
B['sres'] = B.gd - B.smk
def ah(d, bk):
    y = d.dropna(subset=[f'{bk}_L'])
    if len(y) < 15: return '   —   ', ''
    p = pd.Series([picks.settle(g, -1, -L, oa) for g, L, oa in zip(y.gd, y[f'{bk}_L'], y[f'{bk}_oa'])], index=y.index)
    ps = p.groupby(y.sea).mean()
    return f'{100 * p.mean():+6.1f}%', f'{int((ps > 0).sum())}/{len(ps)}'
def row(d, lab):
    if len(d) < 15: return f'   {lab:44s} n{len(d):5d}'
    se = d.sres.std() / np.sqrt(len(d)); ps = d.groupby('sea').sres.mean()
    r = [ah(d, b) for b in ('pin', 'cr', 'b365')]
    return (f'   {lab:44s} n{len(d):5d} · γκολ γηπ.−γραμμη {d.sres.mean():+.3f} ±{se:.3f} ({int((ps < 0).sum())}/{ps.notna().sum()} σεζον <0) · ΦΙΛΟΞ. AH: '
            + ' · '.join(f'{nm} {v[0]} ({v[1]})' for nm, v in zip(('Pin', 'Crown', 'B365'), r)))
H = B[B.rain_ms.notna()]
print(f'ΣΥΜΦΩΝΙΑ ΠΗΓΩΝ (ματς με βροχη και απο τις 2 πηγες: {len(H)}, 2223-2526)')
print(f'   συσχετιση βροχης σταθμος vs ERA5: {H.rain.corr(H.rain_ms):.2f} · ριπες: {H.gust.corr(H.gust_ms):.2f}')
ms2, om2 = H.rain_ms >= 2, H.rain >= 2
print(row(H[~ms2 & ~om2 & (H.rain_ms < 0.2) & (H.rain < 0.2)], 'στεγνο και στις 2'))
print(row(H[ms2 & om2], 'ΒΡΟΧΗ ≥2 ΚΑΙ ΣΤΙΣ 2'))
print(row(H[ms2 & ~om2], 'μονο σταθμος ≥2'))
print(row(H[~ms2 & om2], 'μονο ERA5 ≥2'))
print(row(H[(H.rain_ms >= 1) & (H.rain >= 1)], 'βροχη ≥1 και στις 2'))
print(row(H[(H.gust_ms >= 55) & (H.gust >= 55)], 'ριπες ≥55 και στις 2'))
F = B.dropna(subset=['f1_rain'])
print(f'\nΠΡΟΓΝΩΣΗ (Open-Meteo, 2024+, n{len(F)} ματς) — αυτο που θα ηξερες ΠΡΙΝ τη σεντρα')
for dd in (1, 3):
    for thr in (1, 2, 4):
        print(row(F[F[f'f{dd}_rain'] >= thr], f'προγνωση {dd} μερα/ες πριν: βροχη ≥{thr}mm'))
print(row(F[F.f1_rain < 0.2], 'προγνωση 1 μερα: στεγνο'))
if 'f0_rain' in B:
    F0 = B.dropna(subset=['f0_rain'])
    print(f'\nΠΡΟΓΝΩΣΗ ΙΔΙΑΣ ΜΕΡΑΣ (day0, λιγες ωρες πριν, n{len(F0)})')
    print(f'   συσχετιση με πραγματικη βροχη: σταθμος {F0.f0_rain.corr(F0.rain_ms):.2f} · ERA5 {F0.f0_rain.corr(F0.rain):.2f} (1 μερα πριν: σταθμος {F0.f1_rain.corr(F0.rain_ms):.2f})')
    for thr in (0.5, 1, 2, 4): print(row(F0[F0.f0_rain >= thr], f'ιδια μερα: βροχη ≥{thr}mm'))
    print(row(F0[F0.f0_rain < 0.2], 'ιδια μερα: στεγνο'))
    print(row(F0[(F0.f0_rain >= 1) & (F0.f1_rain < 1)], 'ιδια μερα ≥1 ενω 1 μερα πριν <1'))
    print(row(F0[F0.f0_gust >= 55], 'ιδια μερα: ριπες ≥55'))
print(row(F[(F.f1_rain >= 2) & (F.rain_ms >= 2)], 'προγνωση ≥2 & επεσε (σταθμος ≥2)'))
print(row(F[(F.f1_rain >= 2) & (F.rain_ms < 2)], 'προγνωση ≥2 αλλα δεν επεσε (σταθμος)'))
