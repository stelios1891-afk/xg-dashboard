# -*- coding: utf-8 -*-
"""t119_whistle_thermometer.py — ΣΥΝΟΛΑ NBA: «ΘΕΡΜΟΜΕΤΡΟ ΣΦΥΡΙΓΜΑΤΟΣ» + ΤΥΦΛΟ OVER/UNDER ΑΝΑ ΣΕΖΟΝ (27/10/2026, Στελιος «τρεξε αυτο που
προτεινεις» + «δειξε πως αποδιδει καθε χρονια το τυφλο over/under τον Ιανουαριο — αν οι γραμμες ανεβαινουν ισως αξια στα under»).
Α. ΤΥΦΛΟ Over / Under (ΟΛΑ τα ματς, ανοιγμα Crown) ανα σεζον: Δεκ · Ιαν · Φεβ + μεση γραμμη ανοιγματος & μεσο πραγματικο.
Β. ΘΕΡΜΟΜΕΤΡΟ ΣΦΥΡΙΓΜΑΤΟΣ τη μερα d = μεσες βολες (FTA, 2 ομαδες) της λιγκας στις W προηγουμενες μερες − μεσες βολες ολων των
   προηγουμενων ματς της σεζον (πριν το παραθυρο)· αν < 30 ματς στο παραθυρο ή < 100 πριν → 0.
   ΝΕΑ προβλεψη = μοντελο + c·θερμομετρο, c (ποντοι ανα 1 βολη) ∈ {0 = live, .2, .4, .6, .8} · W ∈ {7, 14, 21}. ΟΛΟΙ οι μηνες.
   Picks: LIVE μηχανη (_t104), ανοιγμα Crown, σ 18, ≥8%. LOSO/walk-forward απο σφαλμα.
   ΚΡΙΤΗΡΙΟ: σφαλμα καλυτερο ≥4/5 σεζον ΚΑΙ μοναδες ≥ live ΚΑΙ CLV οχι χειροτερο.
Εξοδος: nba_tests/t119_whistle_thermometer_out.txt"""
import os, sys
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC); sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
ND = NormalDist(); SIG = 18.0
X = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv')); X['day'] = pd.to_datetime(X.date).dt.normalize(); X = X.sort_values('day').reset_index(drop=True)
TOT, TL, OO, OU, FA, CF = (X[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
def res(sd, L, od):
    x = (TOT - L) * sd; return np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0))
X['bo'] = res(1, TL, OO); X['bu'] = res(-1, TL, OU)
P('t119 · ΣΥΝΟΛΑ NBA · Crown ανοιγμα · 5 σεζον')
P('\n=== Α. ΤΥΦΛΟ Over / Under (ΟΛΑ τα ματς) ανα σεζον · μηνας: Over ROI · Under ROI · % Over που βγηκαν · μεση γραμμη · μεσο πραγματικο ===')
for s in sorted(X.sea.unique()):
    row = []
    for m, nm in ((12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ')):
        d = X[(X.sea == s) & (X.mon == m)]; dec = d[d.tot != d['T']]
        row.append(f"{nm}: Over {100 * d.bo.mean():+5.1f}% · Under {100 * d.bu.mean():+5.1f}% · {100 * (dec.tot > dec['T']).mean():.0f}% Over · γραμμη {d['T'].mean():.1f} · πραγμ {d.tot.mean():.1f}")
    P(f'  {s - 1}-{s % 100:02d}:  ' + '  │  '.join(row))
for m, nm in ((12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ')):
    d = X[X.mon == m]; P(f'  5 σεζον {nm}: Over {100 * d.bo.mean():+.1f}% · Under {100 * d.bu.mean():+.1f}% ({len(d)} ματς) · θετικο Under σε {sum(X[(X.sea == s) & (X.mon == m)].bu.mean() > 0 for s in sorted(X.sea.unique()))}/5 σεζον')
P('  ΣΗΜ.: τυφλο = χανει το περιθωριο (~−4…−5%) · ROI > 0 σε τυφλο = πραγματικη μεροληψια της αγορας.')
# ---- Β
B = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['GAME_ID', 'GAME_DATE', 'FTA', 'stype'])
B = B[B.stype == 'RS']; GF = B.groupby(['GAME_ID', 'GAME_DATE']).FTA.sum().reset_index(); GF['day'] = pd.to_datetime(GF.GAME_DATE).dt.normalize()
GF['sea'] = GF.day.map(lambda d: d.year + (1 if d.month >= 7 else 0)); GF = GF.sort_values('day')
WS = (7, 14, 21); CS = (0.0, .2, .4, .6, .8); TH = {}
for W in WS:
    th = np.zeros(len(X))
    for s in X.sea.unique():
        g = GF[GF.sea == s]; gd = g.day.values; gf = g.FTA.values
        for j in np.where(X.sea.values == s)[0]:
            d = X.day.values[j]; win = (gd < d) & (gd >= d - np.timedelta64(W, 'D')); bef = gd < d - np.timedelta64(W, 'D')
            th[j] = gf[win].mean() - gf[bef].mean() if win.sum() >= 30 and bef.sum() >= 100 else 0.0
    TH[W] = th
def picks(mu):
    u, c = np.zeros(len(X)), np.full(len(X), np.nan); sdv = np.zeros(len(X))
    for j in range(len(X)):
        T = TL[j]
        if abs(T - round(T)) < 1e-9: po = ND.cdf((mu[j] - T - .5) / SIG); pu = ND.cdf((T - mu[j] - .5) / SIG); pp = 1 - po - pu
        else: po = ND.cdf((mu[j] - T) / SIG); pp = 0.0; pu = 1 - po
        eo, eu = po * OO[j] + pp - 1, pu * OU[j] + pp - 1
        sd, e, od = (1, eo, OO[j]) if eo >= eu else (-1, eu, OU[j])
        if e < .08: continue
        x = (TOT[j] - T) * sd; u[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c[j] = sd * (CF[j] - FA[j]); sdv[j] = sd
    return u, c, sdv
V = {}
for W in WS:
    for cc in CS:
        if cc == 0 and W != 14: continue
        k = 'live' if cc == 0 else f'c {cc} · W {W}'; mu = X.mu.values + cc * TH[W]; V[k] = (mu,) + picks(mu)
ys = X.sea.values; mon = X.mon.values; SE = sorted(set(ys))
rm = lambda k, m: float(np.sqrt(np.mean((TOT[m] - V[k][0][m]) ** 2)))
P(f'\n=== Β. ΘΕΡΜΟΜΕΤΡΟ ΣΦΥΡΙΓΜΑΤΟΣ · live {V["live"][1].sum():+.1f}μ ({int((V["live"][1] != 0).sum())} picks) (t104 +143.2) ===')
P('  εκδοχη          │ σφαλμα ολο (ανα σεζον) καλυτερο │ μοναδες · picks · CLV │ Over / Under ROI │ ROI Ιαν │ σφαλμα Ιαν')
for k in V:
    u, cl, sd = V[k][1], V[k][2], V[k][3]
    per = [rm(k, ys == s) for s in SE]; bet = sum(rm(k, ys == s) < rm('live', ys == s) - 1e-9 for s in SE)
    ok = k != 'live' and bet >= 4 and u.sum() >= V['live'][1].sum() and np.nanmean(cl) >= np.nanmean(V['live'][2]) - 1e-9
    f = lambda m: f"{100 * u[m & (u != 0)].mean():+5.1f}%" if (m & (u != 0)).any() else '—'
    P(f"  {k:15s} │ {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{x:.3f}' for s, x in zip(SE, per)) + f") {bet}/5 │ {u.sum():+6.1f} · {int((u != 0).sum())} · {np.nanmean(cl):+.2f}"
      + f" │ {f(sd == 1)} / {f(sd == -1)} │ {f(mon == 1)} │ {rm(k, mon == 1):.3f}" + ('  → ΠΕΡΝΑΕΙ' if ok else ''))
keys = list(V); ch, uo, ul, eb = [], 0.0, 0.0, 0
for s in SE:
    b = min(keys, key=lambda k: rm(k, ys != s)); ch.append(f'{s % 100}:{b}'); uo += V[b][1][ys == s].sum(); ul += V['live'][1][ys == s].sum(); eb += rm(b, ys == s) < rm('live', ys == s) - 1e-9
P(f'  LOSO: {" · ".join(ch)} → μοναδες {uo:+.1f} vs live {ul:+.1f} · σφαλμα καλυτερο {eb}/5')
ch, uo, ul = [], 0.0, 0.0
for s in SE[2:]:
    b = min(keys, key=lambda k: rm(k, ys < s)); ch.append(f'{s % 100}:{b}'); uo += V[b][1][ys == s].sum(); ul += V['live'][1][ys == s].sum()
P(f'  walk-forward: {" · ".join(ch)} → μοναδες {uo:+.1f} vs live {ul:+.1f}')
P('\n  ΕΛΕΓΧΟΣ θερμομετρο σφυριγματος (W 14, βολες/ματς πανω-κατω απο τη σεζον ως τοτε): ' + ' · '.join(
    f"{d0}: {TH[14][np.searchsorted(X.day.values, np.datetime64(d0))]:+.1f}" for d0 in ('2023-12-20', '2024-01-20', '2024-02-10', '2024-02-25', '2025-12-28', '2026-01-10', '2026-01-20', '2025-03-10')))
P('  πριν απο ποιο μηνα κανει σημα; συσχετιση θερμομετρου (W 14) με μεροληψια μοντελου των ΕΠΟΜΕΝΩΝ 14 μερων: ' + ' · '.join(
    f"{s % 100}: {np.corrcoef(TH[14][(ys == s) & (TH[14] != 0)], (X.tot - X.mu).rolling(1).mean()[(ys == s) & (TH[14] != 0)])[0, 1]:+.2f}" for s in SE))
open(os.path.join(SC, 't119_whistle_thermometer_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
