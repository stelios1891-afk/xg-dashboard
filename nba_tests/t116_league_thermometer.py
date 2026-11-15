# -*- coding: utf-8 -*-
"""t116_league_thermometer.py — ΣΥΝΟΛΑ NBA: «ΘΕΡΜΟΜΕΤΡΟ ΛΙΓΚΑΣ» (27/10/2026, Στελιος «τρεξτο» · ορισμος εγκριθηκε).
ΑΦΟΡΜΗ (t115): σε 2023-24 & 2025-26 το σκοραρισμα επεσε αποτομα τον Ιανουαριο (ρυθμος + βολες) και μοντελο & αγορα αργησαν.
ΘΕΡΜΟΜΕΤΡΟ τη μερα d = μεσο (πραγματικο συνολο − προβλεψη μοντελου) ολων των ματς της ιδιας σεζον στις W προηγουμενες μερες (μονο τελειωμενα)·
  αν ματς στο παραθυρο < 30 → 0. ΝΕΑ προβλεψη = μοντελο + c·θερμομετρο. c ∈ {0 = live, .25, .5, .75, 1} · W ∈ {7, 14, 21}. ΟΛΟΙ οι μηνες.
PICKS: LIVE μηχανη συνολων (_t104_totals_live.csv: eng − .5·LO + 1.0·LD), ανοιγμα Crown, σ 18, edge ≥8%, 5 σεζον.
ΕΠΙΛΟΓΗ: LOSO (c, W) απο το ΣΦΑΛΜΑ των αλλων 4 σεζον · walk-forward (μονο προηγουμενες).
ΚΡΙΤΗΡΙΟ: σφαλμα καλυτερο σε ≥4/5 σεζον ΚΑΙ μοναδες ≥ live ΚΑΙ CLV οχι χειροτερο.
Εξοδος: nba_tests/t116_league_thermometer_out.txt"""
import os, sys
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
ND = NormalDist(); SIG = 18.0
X = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv')); X['day'] = pd.to_datetime(X.date).dt.normalize()
X = X.sort_values('day').reset_index(drop=True); X['r'] = X.tot - X.mu
CS = (0.0, .25, .5, .75, 1.0); WS = (7, 14, 21)
TH = {}
for W in WS:
    th = np.zeros(len(X)); nwin = np.zeros(len(X))
    for s, d in X.groupby('sea'):
        days = d.day.values; r = d.r.values; idx = d.index.values
        for j, k in enumerate(idx):
            m = (days < days[j]) & (days >= days[j] - np.timedelta64(W, 'D'))
            nwin[k] = m.sum(); th[k] = r[m].mean() if m.sum() >= 30 else 0.0
    TH[W] = th
TOT, TL, OO, OU, FA, CF = (X[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
def picks(mu):
    u, c, sd_ = np.zeros(len(X)), np.full(len(X), np.nan), np.zeros(len(X))
    for j in range(len(X)):
        T = TL[j]
        if abs(T - round(T)) < 1e-9: po = ND.cdf((mu[j] - T - .5) / SIG); pu = ND.cdf((T - mu[j] - .5) / SIG); pp = 1 - po - pu
        else: po = ND.cdf((mu[j] - T) / SIG); pp = 0.0; pu = 1 - po
        eo, eu = po * OO[j] + pp - 1, pu * OU[j] + pp - 1
        sd, e, od = (1, eo, OO[j]) if eo >= eu else (-1, eu, OU[j])
        if e < .08: continue
        x = (TOT[j] - T) * sd; u[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c[j] = sd * (CF[j] - FA[j]); sd_[j] = sd
    return u, c, sd_
V = {}
for W in WS:
    for c in CS:
        if c == 0 and W != 14: continue
        k = 'live' if c == 0 else f'c {c} · W {W}'
        mu = X.mu.values + c * TH[W]; u, cl, sd = picks(mu); V[k] = (mu, u, cl, sd, c, W)
ys = X.sea.values; mon = X.mon.values; SE = sorted(set(ys))
rm = lambda k, m: float(np.sqrt(np.mean((TOT[m] - V[k][0][m]) ** 2)))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
U = lambda k: V[k][1]
P(f't116 · ΘΕΡΜΟΜΕΤΡΟ ΛΙΓΚΑΣ · ΣΥΝΟΛΑ NBA · Crown ανοιγμα · 5 σεζον · ματς {len(X)} · live: {U("live").sum():+.1f}μ ({int((U("live") != 0).sum())} picks) (t104 +143.2)')
P('\nεκδοχη          │ σφαλμα ολο (ανα σεζον) καλυτερο │ μοναδες · picks · CLV │ Over / Under (ROI) │ ROI Ιαν │ ROI Απρ')
for k in V:
    u, cl, sd = V[k][1], V[k][2], V[k][3]
    per = [rm(k, ys == s) for s in SE]; perL = [rm('live', ys == s) for s in SE]; bet = sum(a < b - 1e-9 for a, b in zip(per, perL))
    ok = k != 'live' and bet >= 4 and u.sum() >= U('live').sum() and np.nanmean(cl) >= np.nanmean(V['live'][2]) - 1e-9
    f = lambda m: f"{100 * u[m & (u != 0)].mean():+5.1f}%" if (m & (u != 0)).any() else '—'
    P(f"  {k:15s} │ {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{x:.3f}' for s, x in zip(SE, per)) + f") {bet}/5 │ {u.sum():+6.1f} · {int((u != 0).sum())} · {np.nanmean(cl):+.2f}"
      + f" │ {f(sd == 1)} / {f(sd == -1)} │ {f(mon == 1)} │ {f(mon == 4)}" + ('  → ΠΕΡΝΑΕΙ' if ok else ''))
keys = list(V)
ch, uo, ul, eb = [], 0.0, 0.0, 0
for s in SE:
    oth = ys != s; cur = ys == s; b = min(keys, key=lambda k: rm(k, oth)); ch.append(f'{s % 100}:{b}')
    uo += U(b)[cur].sum(); ul += U('live')[cur].sum(); eb += rm(b, cur) < rm('live', cur) - 1e-9
P(f'\nLOSO (επιλογη απο σφαλμα): {" · ".join(ch)} → μοναδες {uo:+.1f} vs live {ul:+.1f} · σφαλμα καλυτερο {eb}/5')
ch, uo, ul = [], 0.0, 0.0
for s in SE[2:]:
    prev = ys < s; cur = ys == s; b = min(keys, key=lambda k: rm(k, prev)); ch.append(f'{s % 100}:{b}'); uo += U(b)[cur].sum(); ul += U('live')[cur].sum()
P(f'walk-forward: {" · ".join(ch)} → μοναδες {uo:+.1f} vs live {ul:+.1f}')
best = min([k for k in keys if k != 'live'], key=lambda k: rm(k, ys == ys))
P(f'\nΑΝΑ ΜΗΝΑ (live vs καλυτερη στο σφαλμα: {best}) · μεροληψια = πραγμ − προβλεψη · σφαλμα · ROI picks')
for m, nm in ((10, 'Οκτ'), (11, 'Νοε'), (12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ'), (3, 'Μαρ'), (4, 'Απρ')):
    mm = mon == m
    g = lambda k: f"μεροληψια {np.mean(TOT[mm] - V[k][0][mm]):+.2f} · σφαλμα {rm(k, mm):.2f} · ROI {100 * U(k)[mm & (U(k) != 0)].mean():+5.1f}% ({int((mm & (U(k) != 0)).sum())})"
    P(f'  {nm}: live {g("live")}  │  νεα {g(best)}')
P('\nΕΛΕΓΧΟΣ: θερμομετρο (W 14) σε γνωστες στιγμες:')
for d0 in ('2025-12-29', '2026-01-08', '2026-01-15', '2026-01-25', '2024-01-10', '2024-02-01', '2024-02-20', '2024-03-15'):
    m = X.day == pd.Timestamp(d0)
    if not m.any(): m = (X.day >= pd.Timestamp(d0)) & (X.day <= pd.Timestamp(d0) + pd.Timedelta(days=3))
    if m.any(): j = np.where(m)[0][0]; P(f'   {str(X.day.values[j])[:10]}: θερμομετρο {TH[14][j]:+.2f}π · μεση γραμμη ανοιγματος της μερας {X[X.day == X.day.values[j]]["T"].mean():.1f}')
open(os.path.join(SC, 't116_league_thermometer_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
