# -*- coding: utf-8 -*-
"""nba_gap_fatigue_test.py — NBA «ΠΟΥ ΕΙΝΑΙ Η ΔΙΑΦΟΡΑ ΜΕ ΤΗΝ ΑΓΟΡΑ»: ΚΟΥΡΑΣΗ · ΤΑΞΙΔΙ · ΚΙΝΗΤΡΟ (28/9/2026).
Βαση: (α) μοντελο ομαδων · (β) το καλυτερο «τελειας πληροφοριας» (ολοι οι δεικτες + δικη μας αξια + ομαδα, nba_metrics_oracle_test).
Χαρακτηριστικα καθε ματς (γνωστα ΠΡΙΝ το ματς):
  κουραση: ματς χθες (B2B) γηπ/φιλ · 3ο ματς σε 4 βραδια · διαφορα ημερων ξεκουρασης (0-3+)
  ταξιδι: χλμ απο το προηγουμενο ματς (φιλ/γηπ) · ζωνες ωρας προς ανατολη (φιλ) · ποσοστο ματς στη σειρα εκτος (φιλ) ·
          1ο ματς στην εδρα μετα απο ≥3 εκτος (γηπ) · υψομετρο (γηπ DEN/UTA)
  κινητρο: «χωρις ελπιδα» (≥50 ματς & ≥6 νικες πισω απο 10η θεση περιφερειας) γηπ/φιλ · τελευταια 5 ματς & κορυφη (≥.62) γηπ/φιλ
Τρεις πολυμεταβλητες παλινδρομησεις στις 5 σεζον με closing:
  [1] αγορα − μοντελο (τι βαζει η αγορα που δεν εχουμε) · [2] πραγματικο − μοντελο (τι ισχυει στην πραγματικοτητα)
  [3] πραγματικο − αγορα (το τιμολογει σωστα η αγορα;) + ποσες σεζον ιδιο προσημο.
Μετα: προσθηκη στο μοντελο (βαρη LOSO) → RMSE, b, ROI. Εξοδος: nba_gap_fatigue_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_metrics_oracle_test.py', encoding='utf-8').read().split("EV = [s for s")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
BASES = {'μοντελο ομαδων': V['μοντελο ομαδων'], 'καλυτερο «τελειας πληροφοριας»': V['ΟΛΟΙ + δικη μας + ομαδα']}

ARENA = {'ATL': (33.757, -84.396, -5), 'BOS': (42.366, -71.062, -5), 'BRK': (40.683, -73.975, -5), 'CHO': (35.225, -80.839, -5),
         'CHI': (41.881, -87.674, -6), 'CLE': (41.496, -81.688, -5), 'DAL': (32.790, -96.810, -6), 'DEN': (39.749, -105.008, -7),
         'DET': (42.341, -83.055, -5), 'GSW': (37.768, -122.388, -8), 'HOU': (29.751, -95.362, -6), 'IND': (39.764, -86.155, -5),
         'LAC': (34.0, -118.3, -8), 'LAL': (34.043, -118.267, -8), 'MEM': (35.138, -90.051, -6), 'MIA': (25.781, -80.188, -5),
         'MIL': (43.045, -87.917, -6), 'MIN': (44.979, -93.276, -6), 'NOP': (29.949, -90.082, -6), 'NYK': (40.751, -73.993, -5),
         'OKC': (35.463, -97.515, -6), 'ORL': (28.539, -81.384, -5), 'PHI': (39.901, -75.172, -5), 'PHO': (33.446, -112.071, -7),
         'POR': (45.532, -122.667, -8), 'SAC': (38.580, -121.500, -8), 'SAS': (29.427, -98.438, -6), 'TOR': (43.643, -79.379, -5),
         'UTA': (40.768, -111.901, -7), 'WAS': (38.898, -77.021, -5)}
EAST = {'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS'}
bad = set(G.home) - set(ARENA)
assert not bad, bad
def km(a, b):
    (la1, lo1, _), (la2, lo2, _) = ARENA[a], ARENA[b]
    p1, p2 = math.radians(la1), math.radians(la2); dl = math.radians(lo2 - lo1)
    return 6371 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))

n = len(G); FT = {}
for k in ['h_b2b', 'a_b2b', 'h_3in4', 'a_3in4', 'rest_diff', 'a_km', 'h_km', 'a_tz_east', 'a_trip', 'h_back_home', 'alt',
          'h_tank', 'a_tank', 'h_late_top', 'a_late_top']:
    FT[k] = np.zeros(n)
last = {}                                         # team -> (season, date, location, list of recent dates, road streak)
rec = {}                                          # (season, team) -> [W, L]
NGAMES = G.groupby('season').size().to_dict()
for s, gs in G.groupby('season', sort=True):
    tot_team = 2 * len(gs) / 30
    for d, blk in gs.groupby('date', sort=True):
        # βαθμολογια ΠΡΙΝ απο τη μερα
        stand = {}
        for conf in (EAST, set(ARENA) - EAST):
            rows = sorted(((rec.get((s, t), [0, 0])[0], rec.get((s, t), [0, 0])[1], t) for t in conf),
                          key=lambda x: -(x[0] / max(1, x[0] + x[1])))
            w10, l10 = rows[9][0], rows[9][1]
            for w, l, t in rows: stand[t] = (w, l, ((w10 - w) + (l - l10)) / 2)
        for i, r in blk.iterrows():
            loc = r.home
            for side, t in (('h', r.home), ('a', r.away)):
                L = last.get(t)
                if L and L[0] == s:
                    rest = (d - L[1]).days
                    FT[f'{side}_b2b'][i] = rest == 1
                    FT[f'{side}_3in4'][i] = sum(1 for x in L[3][-2:] if (d - x).days <= 3) == 2
                    dist = km(L[2], loc)
                    if side == 'a':
                        FT['a_km'][i] = dist / 1000; FT['a_tz_east'][i] = ARENA[loc][2] - ARENA[L[2]][2]
                        FT['a_trip'][i] = min(L[4] + 1, 6)
                    else:
                        FT['h_km'][i] = dist / 1000; FT['h_back_home'][i] = L[4] >= 3
                    FT['rest_diff'][i] += (1 if side == 'h' else -1) * min(rest - 1, 3)
                w, l, gb = stand[t]; gp = w + l
                FT[f'{side}_tank'][i] = gp >= 50 and gb >= 6
                FT[f'{side}_late_top'][i] = gp >= tot_team - 5 and w / max(1, gp) >= 0.62
            FT['alt'][i] = r.home in ('DEN', 'UTA')
        for i, r in blk.iterrows():
            hw = r.hs > r.as_
            for t, won, road in ((r.home, hw, False), (r.away, not hw, True)):
                L = last.get(t); prev_dates = L[3] if L and L[0] == s else []
                streak = (L[4] + 1 if (L and L[0] == s) else 1) if road else 0
                last[t] = (s, d, r.home, (prev_dates + [d])[-3:], streak)
                rr = rec.setdefault((s, t), [0, 0]); rr[0 if won else 1] += 1
NAMES = {'h_b2b': 'γηπ. ματς χθες', 'a_b2b': 'φιλ. ματς χθες', 'h_3in4': 'γηπ. 3ο σε 4 βραδια', 'a_3in4': 'φιλ. 3ο σε 4 βραδια',
         'rest_diff': 'διαφ. ημερων ξεκουρ. (γ−φ)', 'a_km': 'φιλ. ταξιδι (1000 χλμ)', 'h_km': 'γηπ. ταξιδι (1000 χλμ)',
         'a_tz_east': 'φιλ. ζωνες ωρας προς ανατ.', 'a_trip': 'φιλ. ν-οστο ματς εκτος', 'h_back_home': 'γηπ. 1ο σπιτι μετα ≥3 εκτος',
         'alt': 'υψομετρο (DEN/UTA)', 'h_tank': 'γηπ. χωρις ελπιδα', 'a_tank': 'φιλ. χωρις ελπιδα',
         'h_late_top': 'γηπ. κορυφη, τελ. 5 ματς', 'a_late_top': 'φιλ. κορυφη, τελ. 5 ματς'}
KEYS = list(FT)
XF = np.column_stack([FT[k].astype(float) for k in KEYS])
EV = [s for s in TS if s in EVAL]
mm = np.isin(SE, EV)
Xe = np.column_stack([np.ones(mm.sum()), XF[IDX][mm]])
def ols(y):
    c, *_ = np.linalg.lstsq(Xe, y, rcond=None); r = y - Xe @ c
    cov = np.linalg.inv(Xe.T @ Xe) * (r @ r) / (len(y) - Xe.shape[1]); return c, c / np.sqrt(np.diag(cov))
P(f'5 σεζον · {mm.sum()} ματς με closing · συχνοτητα: ' + ' · '.join(f'{k} {XF[IDX][mm][:, j].mean():.2f}' for j, k in enumerate(KEYS)))
for bn, base in BASES.items():
    P('')
    P(f'=== ΒΑΣΗ: {bn} — πολυμεταβλητη, πποντοι ανα μοναδα (t) ===')
    c1, t1 = ols((MM - base[IDX])[mm]); c2, t2 = ols((ACT - base[IDX])[mm])
    P(f'  {"χαρακτηριστικο":28s} {"[1] αγορα−μοντ.":>16s} {"[2] πραγμ.−μοντ.":>17s}')
    for j, k in enumerate(KEYS):
        P(f'  {NAMES[k]:28s} {c1[j+1]:+6.2f} ({t1[j+1]:+5.1f})   {c2[j+1]:+6.2f} ({t2[j+1]:+5.1f})')
    d0 = np.var((MM - base[IDX])[mm]); r1 = (MM - base[IDX])[mm] - Xe @ c1
    P(f'  → ποσο απο τη διαφορα αγορα−μοντελο εξηγουν ολα μαζι: {1 - np.var(r1) / d0:.1%}')
P('')
P('=== [3] ΠΡΑΓΜΑΤΙΚΟ − ΑΓΟΡΑ: τα τιμολογει σωστα η αγορα; (πποντοι, t, σεζον με ιδιο προσημο) ===')
c3, t3 = ols((ACT - MM)[mm])
for j, k in enumerate(KEYS):
    sg = 0
    for s in EV:
        ms = SE[mm] == s; Xs = Xe[ms]
        if np.linalg.matrix_rank(Xs) < Xs.shape[1]: continue
        cs = np.linalg.lstsq(Xs, (ACT - MM)[mm][ms], rcond=None)[0]; sg += np.sign(cs[j + 1]) == np.sign(c3[j + 1])
    P(f'  {NAMES[k]:28s} {c3[j+1]:+6.2f} ({t3[j+1]:+5.1f})  {sg}/{len(EV)}')

P('')
P('=== ΠΡΟΣΘΗΚΗ ΣΤΟ ΜΟΝΤΕΛΟ (βαρη LOSO) ===')
P(f'  αγορα Crown RMSE {np.sqrt(np.mean((ACT - MM)[mm] ** 2)):.2f}')
def rep(nm, m):
    e = ACT - m[IDX]; b = np.polyfit((m[IDX] - MM)[mm], (ACT - MM)[mm], 1)[0]
    cells = []
    for thr in (0.05, 0.08, 0.10):
        Rr = roi(m, thr, EV); pos = sum(1 for s in EV if len(Rr[Rr.season == s]) and Rr[Rr.season == s].p.mean() > 0)
        cells.append(f'≥{thr*100:.0f}%: {Rr.p.mean()*100:+.1f}% ({len(Rr)}) {pos}/{len(EV)}')
    P(f'  {nm:44s} RMSE {np.sqrt(np.mean(e[mm] ** 2)):.2f} · b {b:+.3f} | ' + ' | '.join(cells))
FAT = [KEYS.index(k) for k in ('h_b2b', 'a_b2b', 'h_3in4', 'a_3in4', 'rest_diff')]
TRV = [KEYS.index(k) for k in ('a_km', 'h_km', 'a_tz_east', 'a_trip', 'h_back_home', 'alt')]
MOT = [KEYS.index(k) for k in ('h_tank', 'a_tank', 'h_late_top', 'a_late_top')]
for bn, base in BASES.items():
    rep(f'{bn}', base)
    for gn, cols in (('+ κουραση', FAT), ('+ ταξιδι', TRV), ('+ κινητρο', MOT), ('+ ΟΛΑ', FAT + TRV + MOT)):
        rep(f'  {gn}', loso([base] + [XF[:, j] for j in cols]))
open('nba_gap_fatigue_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
