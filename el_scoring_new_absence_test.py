# -*- coding: utf-8 -*-
"""el_scoring_new_absence_test.py — EUROLEAGUE ΣΥΝΟΛΑ: «ΧΑΜΕΝΟ ΣΚΟΡΑΡΙΣΜΑ» ΜΟΝΟ ΓΙΑ ΝΕΕΣ ΑΠΟΥΣΙΕΣ (27/10/2026, Στελιος «οκ για δες το»).
Αφορμη (el_star_absence_methods): το S1 (ολες οι απουσιες) διορθωνει −1.7 οταν η πραγματικη επιδραση με 2+ σημαντικους ειναι −5.5· οι
μακροχρονιες (≥4 ματς) εχουν ~0 επιδραση (ηδη στη βαθμολογια) και «αραιωνουν» τον συντελεστη.
ΝΕΟ: μονο απουσιες που κρατανε 1-3 ματς (το live βαρος «πληρες») · N1 [λεπτα, λεπτα×(ποντοι/40 − μεσος)] · N2 μονο [λεπτα×(ποντοι/40 − μεσος)].
Στησιμο/κριτηρια ΙΔΙΑ με el_scoring_absence_test (1.563 ματς E2021-25, LOSO, ridge 1, picks συνολων ≥8% ανοιγμα Crown):
  ΠΕΡΝΑ αν LOSO RMSE συνολου καλυτερο απο «χωρις» ≥4/5 ΚΑΙ ο συντελεστης σκοραρισματος <0 ≥4/5 ΚΑΙ μοναδες ≥ «χωρις» ΚΑΙ EuroCup (<0 ≥4/5, t ≤ −2).
  + συγκριση με live on/off (W4) και με S1 (ολες οι απουσιες) · + πινακας στα ματς με σημαντικους απουσες (ορισμος Γ ≥12 πμ).
Εξοδος: el_scoring_new_absence_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
sc = open('el_scoring_absence_test.py', encoding='utf-8').read().split("open('el_scoring_absence_out.txt'")[0]
_a = "def P(s=''): print(s, flush=True); out.append(str(s))"; _i = sc.rfind(_a); sc = sc[:_i] + "def P(s=''): pass" + sc[_i + len(_a):]
g = {}
with contextlib.redirect_stdout(_B()): exec(sc, g)
st = open('el_star_absence_totals.py', encoding='utf-8').read()
st = "ns = {'ns': ns}" + chr(10) + st.split("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", 1)[1].split("def roi(m):")[0]
with contextlib.redirect_stdout(_B()): exec(st, g)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
inner = g['ns']['ns'] if 'ns' in g['ns'] else g['ns']
rows, YH, YA, YT, ys, SE, EC, rmse, tpicks, HELD = (inner[k] for k in ('rows', 'YH', 'YA', 'YT', 'ys', 'SE', 'EC', 'rmse', 'tpicks', 'HELD'))
pts40, LG, PH = g['pts40'], g['LG'], inner['PH']
def is_new(p):
    h = [m for t_, m in PH[p['pid']] if t_ < p['ts'] - 3600][-10:]
    return bool(h) and p['w'] >= np.mean(h) / 40 - 1e-9
def feats(own):
    nw = [p for p in own if is_new(p)]
    return np.array([sum(p['w'] for p in nw), sum(p['w'] * (pts40(p['pid'], p['ts']) - LG) for p in nw)])
FH = np.array([feats(r['ah']) for r in rows]); FA = np.array([feats(r['aa']) for r in rows])
VAR = {'N1 νεες: λεπτα + σκοραρισμα': [0, 1], 'N2 νεες: μονο σκοραρισμα': [1]}
ALL = np.ones(len(rows), bool)
def fit(cols, tr):
    X = np.r_[FH[tr][:, cols], FA[tr][:, cols]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(len(cols)), X.T @ y)
u0, s0 = tpicks(np.zeros(len(rows))); uL, sL = tpicks(HELD['W4 μονο on/off']); S1 = g['RES']['S1 λεπτα + ποντοι/40'][1]; uS, sS = tpicks(S1)
P(f'Ευρωλιγκα 2021-25 · ματς {len(rows)} · ΝΕΕΣ απουσιες (1-3 ματς) {sum(1 for r in rows for p in r["ah"] + r["aa"] if is_new(p))} απο {sum(len(r["ah"]) + len(r["aa"]) for r in rows)}')
P(f'\n## ΒΑΣΕΙΣ (LOSO RMSE συνολου)\n  χωρις διορθωση   {rmse(YT, ALL):.3f} · {s0}\n  live on/off      {rmse(YT - HELD["W4 μονο on/off"], ALL):.3f} · {sL}\n  S1 ολες απουσιες {rmse(YT - S1, ALL):.3f} · {sS}')
HN = {}
for nm, cols in VAR.items():
    b = fit(cols, ALL); per = {s: fit(cols, ys == s) for s in SE}; j = cols.index(1)
    same = sum(1 for s in SE if np.sign(per[s][j]) == np.sign(b[j]))
    h = np.zeros(len(rows))
    for Yr in SE:
        bb = fit(cols, ys != Yr); m = ys == Yr; h[m] = FH[m][:, cols] @ bb + FA[m][:, cols] @ bb
    d0 = [rmse(YT - h, ys == s) - rmse(YT, ys == s) for s in SE]; dL = [rmse(YT - h, ys == s) - rmse(YT - HELD['W4 μονο on/off'], ys == s) for s in SE]
    u, s_ = tpicks(h); ok = sum(x < 0 for x in d0) >= 4 and same >= 4 and b[j] < 0 and u >= u0; HN[nm] = (h, ok)
    P(f'\n## {nm}: συντελεστες ' + ' · '.join(f'{x:+.3f}' for x in b) + ' · σκοραρισμα ανα σεζον ' + ' '.join(f'{s[-2:]}:{per[s][j]:+.3f}' for s in SE) + f' (ιδιο προσημο {same}/5)')
    P(f'   RMSE {rmse(YT - h, ALL):.3f} · vs χωρις ' + ' '.join(f'{x:+.3f}' for x in d0) + f' → {sum(x < 0 for x in d0)}/5 · vs on/off ' + ' '.join(f'{x:+.3f}' for x in dL) + f' → {sum(x < 0 for x in dL)}/5')
    P(f'   {s_}')
# EuroCup
er, EY, Ey = inner['er'], inner['EY'], inner['Ey']
EX = np.array([[1, e[2], *feats(e[3])] for e in er])
def ols(m):
    Xm, Ym = EX[m], EY[m]; b = np.linalg.lstsq(Xm, Ym, rcond=None)[0]; r_ = Ym - Xm @ b
    se = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(Ym) - Xm.shape[1]) * np.linalg.inv(Xm.T @ Xm))); return b, se
b, se = ols(np.ones(len(EY), bool)); okc = sum(ols(Ey == s)[0][3] < 0 for s in EC); EC_OK = okc >= 4 and b[3] / se[3] <= -2
P(f'\n## EuroCup 2021-25 (νεες απουσιες): λεπτα {b[2]:+.2f} · σκοραρισμα {b[3]:+.3f} (t {b[3] / se[3]:+.1f}) · σωστο προσημο {okc}/5 → ' + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if EC_OK else 'ΔΕΝ επιβεβαιωνεται'))
# πινακας στα ματς με σημαντικους απουσες
TOT, T0, pick_res, REC_ = g['TOT'], g['T0'], g['pick_res'], g['REC_']
f = np.array([x['flags']['Γ'] for x in REC_]); nw = np.array([x['new']['Γ'] for x in REC_])
METH = {'live on/off': HELD['W4 μονο on/off'], 'S1 ολες': S1, 'N1 νεες': HN['N1 νεες: λεπτα + σκοραρισμα'][0]}
PK = {k: pick_res(v) for k, v in METH.items()}
def roi(sd, rs, m):
    m = m & (sd != 0)
    if not m.any(): return '—'
    ps = pd.Series(rs[m]).groupby(ys[m]).sum(); return f'{100 * np.nanmean(rs[m]):+6.1f}% ({int(m.sum())}, {np.nansum(rs[m]):+.1f}μ, {int((ps > 0).sum())}/{len(ps)})'
P('\n## ΣΤΑ ΜΑΤΣ ΜΕ ΣΗΜΑΝΤΙΚΟΥΣ ΑΠΟΥΣΕΣ (≥12 πμ): πραγματικη επιδραση · διορθωση καθε μεθοδου · picks')
for lab, m in (('1 σημαντικος', f == 1), ('2+ σημαντικοι', f >= 2), ('≥1 νεα απουσια', (f >= 1) & (nw >= 1)), ('≥1 μονο μακροχρονια', (f >= 1) & (nw == 0)), ('ΟΛΑ', f >= 0)):
    P(f'  {lab:20s} ({int(m.sum())} ματς, πραγμ − μοντελο {np.mean(TOT[m] - T0[m]):+.2f}): ' + ' │ '.join(f'{k} διορθ. {np.mean(v[m]):+.2f}, picks {roi(*PK[k], m)}' for k, v in METH.items()))
P('\nΑΠΟΦΑΣΗ (προ-δηλωμενα): ' + ' · '.join(f'{nm}: EL {"✓" if v[1] else "✗"}' for nm, v in HN.items()) + f' · EuroCup {"✓" if EC_OK else "✗"}')
open('el_scoring_new_absence_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
