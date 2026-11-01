"""
weather_rain_home.py — 5/10/2026: ΕΜΒΑΘΥΝΣΗ στο ευρημα του weather_test: «σε βροχη ο γηπεδουχος παιζει κατω απο τη γραμμη».
Διαβαζει weather_rows_{WX_SRC}.pkl (τρεξε πρωτα weather_test.py με την ιδια πηγη).
Ελεγχοι: δοση-αποκριση (ποσοτητα βροχης) · ανα σεζον · ανα λιγκα · φαβορι εντος/εκτος · βροχη ΠΡΙΝ αλλα στεγνο στο ματς ·
σταθμος κοντα (≤15 km) · xG: πεφτει ο γηπεδουχος ή ανεβαινει ο φιλοξενουμενος; · κινηση γραμμης ανοιγμα→κλεισιμο (το βλεπει η αγορα;)
"""
import os, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
SRC = os.environ.get('WX_SRC', 'ms')
X = pd.read_pickle(f'weather_rows_{SRC}.pkl')
X = X[~X.roof & X.smk.notna()].copy()
X['sres'] = X.gd - X.smk
# αναμενομενη υπεροχη σε xG: αναγωγη της γραμμης στην κλιμακα xG με παλινδρομηση σε ξερα ματς
DRY = (X.rain < 0.2) & (X.rain_pre < 0.5)
X['xsup'] = X.hxg - X.axg
b = np.polyfit(X[DRY].smk, X[DRY].xsup, 1); X['xres'] = X.xsup - np.polyval(b, X.smk)
bt = np.polyfit(X[DRY].pin_close.dropna(), X[DRY].dropna(subset=['pin_close']).txg, 1)
X['hres_x'] = X.hxg - (np.polyval(bt, X.pin_close) + np.polyval(b, X.smk)) / 2
X['ares_x'] = X.axg - (np.polyval(bt, X.pin_close) - np.polyval(b, X.smk)) / 2
def ah(d, bk):
    y = d.dropna(subset=[f'{bk}_L'])
    if len(y) < 15: return '    —     '
    p = np.array([picks.settle(g, -1, -L, oa) for g, L, oa in zip(y.gd, y[f'{bk}_L'], y[f'{bk}_oa'])])
    return f'{100 * p.mean():+6.1f}%'
def row(d, lab):
    if len(d) < 15: return f'   {lab:34s} n{len(d):5d}'
    se = d.sres.std() / np.sqrt(len(d)); ps = d.groupby('sea').sres.mean()
    mv = (d.cr_L - d.cr_Lopen).mean() if 'cr_Lopen' in d else np.nan
    return (f'   {lab:34s} n{len(d):5d} · γκολ γηπ.−γραμμη {d.sres.mean():+.3f} ±{se:.3f} ({int((ps < 0).sum())}/{ps.notna().sum()} σεζον <0)'
            f' · xG υπεροχη−αναμ. {d.xres.mean():+.3f} [γηπ {d.hres_x.mean():+.3f} / φιλ {d.ares_x.mean():+.3f}]'
            f' · κινηση γραμμης Crown {mv:+.3f} · ΦΙΛΟΞ. AH: Pin {ah(d, "pin")} Crown {ah(d, "cr")} B365 {ah(d, "b365")}')
print(f'ΠΗΓΗ: {SRC} · ματς με γραμμη Pinnacle: {len(X)} (σεζον {sorted(X.sea.unique())})')
print('\nΔΟΣΗ-ΑΠΟΚΡΙΣΗ (βροχη στις 2 ωρες απο τη σεντρα, mm)')
print(row(X[DRY], 'ξερο (και πριν)'))
print(row(X[(X.rain < 0.2) & (X.rain_pre >= 0.5)], 'στεγνο στο ματς, βροχη 6ω πριν'))
for lo, hi in ((0.2, 1), (1, 2), (2, 4), (4, 99)):
    print(row(X[(X.rain >= lo) & (X.rain < hi)], f'{lo}-{hi} mm'))
R = X.rain >= 2
print('\nΒΡΟΧΗ ≥2 mm — ανα σεζον')
for s, g in X[R].groupby('sea'): print(row(g, s))
print('\nΒΡΟΧΗ ≥2 mm — ανα λιγκα')
for s, g in X[R].groupby('lg'): print(row(g, s))
print('\nΒΡΟΧΗ ≥2 mm — ποιος ειναι φαβορι')
print(row(X[R & (X.smk > 0.25)], 'γηπεδουχος φαβορι (>0.25)'))
print(row(X[R & (X.smk.abs() <= 0.25)], 'ισορροπο'))
print(row(X[R & (X.smk < -0.25)], 'φιλοξενουμενος φαβορι'))
if 'km' in X:
    print('\nΣΤΑΘΜΟΣ ΚΟΝΤΑ (≤15 km)'); print(row(X[R & (X.km <= 15)], 'βροχη ≥2, σταθμος ≤15 km'))
print('\nΚΡΥΟ <2°C (δευτερο ευρημα)')
print(row(X[X.temp < 2], 'κρυο <2'))
print(row(X[(X.temp < 2) & (X.rain < 0.2)], 'κρυο <2 χωρις βροχη'))
for s, g in X[X.temp < 2].groupby('sea'): print(row(g, '  ' + s))
print('\nΡΙΠΕΣ ≥55 χωρις βροχη ≥2')
print(row(X[(X.gust >= 55) & ~R], 'ριπες ≥55, οχι βροχη'))
