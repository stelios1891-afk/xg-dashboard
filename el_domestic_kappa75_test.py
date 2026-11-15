# -*- coding: utf-8 -*-
"""el_domestic_kappa75_test.py — ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ: βαρος κ 0.5 (live) → 0.75; (1/10/2026, Στελιος «τρεξε το 2»).
Ιδιο μοντελο με el_domestic_league_test (εκδοχη α, ιδιο βαρος για ολες τις λιγκες, ταβανι 20) — στα ματς 11+ ειναι ακριβως ο live κανονας.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: RMSE διαφορας αγων 11+ (κανονικη περιοδος) καλυτερο απο κ 0.5 σε ≥4/5 σεζον (2021-22…2025-26).
Αναφορα: b vs Pinnacle closing, ROI χαντικαπ ≥8% / ≥5% (αγων 11+). Εξοδος: el_domestic_kappa75_test_out.txt"""
import sys, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_domestic_league_test.py', encoding='utf-8').read().split("PRED = {}\nfor var in")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, NS)
D, SE5, GN, IDX, PRC, ACT, SE, RS, run = (NS[k] for k in ('D', 'SE5', 'GN', 'IDX', 'PRC', 'ACT', 'SE', 'RS', 'run'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
PRED = {k: run(k, 'a') for k in (0.5, 0.75, 1.0)}
ACTD = (D.hs - D.as_).values.astype(float); SEASD = D.season.values; M11 = (D.phase.values == 'RS') & (GN > 10)
def rm(v, ss): m = M11 & np.isin(SEASD, ss); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; GJ = GN[IDX[jj]]; MK = -L_
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, thr):
    m = v[IDX][jj]; msk = GJ > 10
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; pr = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0)); sel = (e >= thr) & msk
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and pr[sel & (SJ == s)].mean() > 0)
    return f'{pr[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5'
P('=== ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ, αγων 11+ : κ 0.5 (live) vs 0.75 vs 1.0 ===')
for k, v in PRED.items():
    b = np.polyfit((v[IDX][jj] - MK)[GJ > 10], (AC - MK)[GJ > 10], 1)[0]
    diffs = [rm(v, [Y]) - rm(PRED[0.5], [Y]) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
    P(f'  κ {k:4}: RMSE 11+ {rm(v, SE5):.3f} · ανα σεζον vs 0.5 ' + ' '.join(f'{d:+.3f}' for d in diffs)
      + (f' → καλυτερο {w_}/5 → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if k != 0.5 else '') + f' · b {b:+.3f} · ROI ≥8% {roi(v, .08)} · ≥5% {roi(v, .05)}')
open('el_domestic_kappa75_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
