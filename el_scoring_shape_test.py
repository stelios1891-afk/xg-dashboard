# -*- coding: utf-8 -*-
"""el_scoring_shape_test.py — EUROLEAGUE ΣΥΝΟΛΑ: N2 («χαμενο σκοραρισμα» νεων απουσιων) — ΠΟΛΛΑΠΛΑΣΙΑΣΤΗΣ & ΚΑΜΠΥΛΗ (27/10/2026, Στελιος «τρεξτα»).
Βαση: el_scoring_new_absence_test (N2: διορθωση ποντων ομαδας = c·S, S = Σ νεων αποντων (λεπτα/40)·(ποντοι/40 − 16.2), c ≈ −0.18, LOSO).
1 ΠΟΛΛΑΠΛΑΣΙΑΣΤΗΣ: m·c·S, m ∈ {1, 1.5, 2, 3} · + LOSO επιλογη m απο το σφαλμα των αλλων σεζον.
2 ΚΑΜΠΥΛΗ: c1·S + c2·max(S, 0)² ανα ομαδα (πολλοι σκορερ εκτος «πονανε» περισσοτερο απο το αθροισμα) · c1, c2 LOSO (ridge 1).
ΚΡΙΤΗΡΙΟ (προ-δηλωμενο, ΜΟΝΟ Ευρωλιγκα — EuroCup εκτος κατα Στελιο): μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ το N2 αν LOSO RMSE συνολου καλυτερο απο N2 σε ≥4/5
  ΚΑΙ μοναδες picks συνολων (≥8% ανοιγμα) ≥ N2. + πινακας στα ματς με σημαντικους απουσες & Ολυμπιακος 28/10.
Εξοδος: el_scoring_shape_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_scoring_new_absence_test.py', encoding='utf-8').read().split("open('el_scoring_new_absence_out.txt'")[0]
_a = "def P(s=''): print(s, flush=True); out.append(str(s))"; _i = src.rfind(_a); src = src[:_i] + "def P(s=''): pass" + src[_i + len(_a):]
g = {}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows, YH, YA, YT, ys, SE, rmse, tpicks, FH, FA = (g[k] for k in ('rows', 'YH', 'YA', 'YT', 'ys', 'SE', 'rmse', 'tpicks', 'FH', 'FA'))
TOT, T0, pick_res, REC_ = g['TOT'], g['T0'], g['pick_res'], g['REC_']
Sh, Sa = FH[:, 1], FA[:, 1]
def fit_lin(tr):
    X = np.r_[Sh[tr], Sa[tr]][:, None]; y = np.r_[YH[tr], YA[tr]]; return float(np.linalg.solve(X.T @ X + np.eye(1), X.T @ y)[0])
def fit_curve(tr):
    s = np.r_[Sh[tr], Sa[tr]]; X = np.c_[s, np.maximum(s, 0) ** 2]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + np.eye(2), X.T @ y)
MS = (1.0, 1.5, 2.0, 3.0)
H = {}
for mm in MS:
    h = np.zeros(len(rows))
    for Y in SE:
        c = fit_lin(ys != Y); m = ys == Y; h[m] = mm * c * (Sh[m] + Sa[m])
    H[f'N2 ×{mm:g}'] = h
hc = np.zeros(len(rows)); CC = {}
for Y in SE:
    c1, c2 = fit_curve(ys != Y); CC[Y] = (c1, c2); m = ys == Y
    hc[m] = c1 * (Sh[m] + Sa[m]) + c2 * (np.maximum(Sh[m], 0) ** 2 + np.maximum(Sa[m], 0) ** 2)
H['καμπυλη (S + S²)'] = hc
# LOSO επιλογη πολλαπλασιαστη
hl = np.zeros(len(rows)); chm = []
for Y in SE:
    oth = ys != Y; best = min(MS, key=lambda mm: rmse(YT - H[f'N2 ×{mm:g}'], oth)); chm.append(f'{Y[-2:]}:×{best:g}'); hl[ys == Y] = H[f'N2 ×{best:g}'][ys == Y]
H['N2 × (LOSO επιλογη)'] = hl
ALL = np.ones(len(rows), bool); base = H['N2 ×1']
u0, s0 = tpicks(np.zeros(len(rows))); uB, sB = tpicks(base)
c_all = fit_lin(ALL); c1a, c2a = fit_curve(ALL)
P(f'el_scoring_shape · Ευρωλιγκα 2021-25 · ματς {len(rows)} · N2 c = {c_all:+.3f} · καμπυλη c1 = {c1a:+.3f}, c2 = {c2a:+.4f} (ανα σεζον c2: ' + ' '.join(f'{Y[-2:]}:{CC[Y][1]:+.4f}' for Y in SE) + ')')
P(f'  S ανα ομαδα: μη μηδενικο {int((np.r_[Sh, Sa] != 0).sum())} · 90% {np.percentile(np.r_[Sh, Sa], 90):.1f} · 99% {np.percentile(np.r_[Sh, Sa], 99):.1f} · μεγιστο {np.r_[Sh, Sa].max():.1f}')
P(f'  LOSO επιλογες πολλαπλασιαστη: {" · ".join(chm)}')
P(f'\n  χωρις διορθωση      RMSE {rmse(YT, ALL):.3f} · {s0}')
for k, h in H.items():
    d = [rmse(YT - h, ys == s) - rmse(YT - base, ys == s) for s in SE]; u, s_ = tpicks(h)
    ok = k != 'N2 ×1' and sum(x < 0 for x in d) >= 4 and u >= uB
    P(f'  {k:20s} RMSE {rmse(YT - h, ALL):.3f} · vs N2 ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · {s_}' + ('  → ΑΝΤΙΚΑΘΙΣΤΑ ΤΟ N2' if ok else ''))
f = np.array([x['flags']['Γ'] for x in REC_]); nw = np.array([x['new']['Γ'] for x in REC_]); ysA = ys
def roi(sd, rs, m):
    m = m & (sd != 0)
    if not m.any(): return '—'
    ps = pd.Series(rs[m]).groupby(ysA[m]).sum(); return f'{100 * np.nanmean(rs[m]):+6.1f}% ({int(m.sum())}, {np.nansum(rs[m]):+.1f}μ, {int((ps > 0).sum())}/{len(ps)})'
P('\n## ΣΤΑ ΜΑΤΣ ΜΕ ΣΗΜΑΝΤΙΚΟΥΣ ΑΠΟΥΣΕΣ (≥12 πμ) — διορθωση & picks')
for lab, m in (('0 σημαντικοι', f == 0), ('1 σημαντικος', f == 1), ('2+ σημαντικοι', f >= 2), ('≥1 νεα απουσια', (f >= 1) & (nw >= 1))):
    P(f'  {lab:16s} ({int(m.sum())} ματς, πραγματικη επιδραση {np.mean(TOT[m] - T0[m]):+.2f}):')
    for k in ('N2 ×1', 'N2 ×2', 'N2 ×3', 'καμπυλη (S + S²)'):
        sd, rs = pick_res(H[k]); P(f'     {k:18s} διορθ. {np.mean(H[k][m]):+5.2f} · picks {roi(sd, rs, m)} · Over {roi(sd, rs, m & (sd == 1))} · Under {roi(sd, rs, m & (sd == -1))}')
# Ολυμπιακος 28/10 (S = 16.6 απο το el_scoring_absence παραδειγμα· ξαναυπολογισμος)
NAME = g['inner']['NAME']; inv = {v: k for k, v in NAME.items()}; pts40, LG = g['pts40'], g['LG']
So = sum(mn / 40 * (pts40(inv[nm], 2e9) - LG) for nm, mn in (('FOURNIER, EVAN', 24), ('MILUTINOV, NIKOLA', 19), ('MONTERO, JEAN', 26), ('DORSEY, TYLER', 18)) if nm in inv)
P(f'\n## Ολυμπιακος 28/10: S = {So:.1f} → N2 ×1 {c_all * So:+.1f} · ×2 {2 * c_all * So:+.1f} · ×3 {3 * c_all * So:+.1f} · καμπυλη {c1a * So + c2a * So ** 2:+.1f} ποντοι στο συνολο')
open('el_scoring_shape_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
