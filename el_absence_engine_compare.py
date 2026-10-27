# -*- coding: utf-8 -*-
"""el_absence_engine_compare.py — EUROLEAGUE ΣΥΝΟΛΑ: ΠΟΙΑ ΔΙΟΡΘΩΣΗ ΑΠΟΥΣΙΩΝ ΑΝΤΙΚΑΘΙΣΤΑ ΤΟ ON/OFF; ΠΛΗΡΗΣ ΣΥΓΚΡΙΣΗ (27/10/2026, Στελιος «προχωρα σε
LOSO και τα υπολοιπα που ειχαμε τεσταρει, ωστε να βρουμε την καλυτερη μηχανη»).
ΜΗΧΑΝΕΣ (διορθωση ποντων ομαδας, ridge 1): 0 χωρις · W4 on/off (live) · S1 ολες οι απουσιες [λεπτα, λεπτα×(ποντοι/40 − 16.2)] ·
  N2 νεες (1-3 ματς) [λεπτα×(ποντοι/40 − 16.2)] · N1 νεες [λεπτα, λεπτα×(ποντοι/40 − 16.2)].
ΒΑΣΗ: 1.563 ματς E2021-25 (live μηχανη συνολων el_newmodel_preds), picks συνολων ≥8% ανοιγμα Crown, σ 16.7.
ΕΛΕΓΧΟΙ (προ-δηλωμενοι): 1 LOSO RMSE ανα σεζον (vs χωρις & vs on/off) · 2 ζευγαρωτη t (τετραγ. σφαλμα ανα ματς) · 3 picks: μοναδες, θετ. σεζον, CLV ·
  4 WALK-FORWARD (συντελεστες ΜΟΝΟ απο προηγουμενες σεζον, απο τη 2η) · 5 BOOTSTRAP εβδομαδων: P(μοναδες > on/off) · 6 PLACEBO: ανακατεμα των
  απουσιων μεταξυ ματς ιδιας σεζον (200 φορες) → P(placebo ≥ πραγματικες μοναδες) · 7 πινακας στα ματς με σημαντικους απουσες (≥12 πμ).
ΚΡΙΤΗΡΙΟ: νικητρια = περναει τα περισσοτερα 1-6 απεναντι στο on/off, με ΕΛΑΧΙΣΤΑ: μοναδες ≥ on/off, CLV οχι χειροτερο (−0.02), walk-forward ≥ on/off, placebo < 10%.
Εξοδος: el_absence_engine_compare_out.txt"""
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
inner = g['inner']; rows, YH, YA, YT, ys, SE = (inner[k] for k in ('rows', 'YH', 'YA', 'YT', 'ys', 'SE'))
TOT, T0, pick_res, REC_ = g['TOT'], g['T0'], g['pick_res'], g['REC_']
FHn, FAn = g['FH'], g['FA']                                       # νεες: [λεπτα, σκοραρισμα]
XHs, XAs = g['g']['XH']['S1 λεπτα + ποντοι/40'], g['g']['XA']['S1 λεπτα + ποντοι/40']   # ολες
W4H, W4A = g['g']['W4H'], g['g']['W4A']
FEAT = {'on/off (live)': (W4H, W4A), 'S1 ολες': (XHs, XAs), 'N2 νεες σκοραρ.': (FHn[:, [1]], FAn[:, [1]]), 'N1 νεες λεπτα+σκοραρ.': (FHn, FAn)}
def fit(XH, XA, tr):
    X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]; return np.linalg.solve(X.T @ X + np.eye(X.shape[1]), X.T @ y)
def loso(XH, XA):
    h = np.zeros(len(rows))
    for Y in SE:
        b = fit(XH, XA, ys != Y); m = ys == Y; h[m] = XH[m] @ b + XA[m] @ b
    return h
def wf(XH, XA):
    h = np.zeros(len(rows)); ok = np.zeros(len(rows), bool)
    for i, Y in enumerate(SE[1:], 1):
        b = fit(XH, XA, np.isin(ys, SE[:i])); m = ys == Y; h[m] = XH[m] @ b + XA[m] @ b; ok |= m
    return h, ok
H = {'χωρις': np.zeros(len(rows))}; WF = {'χωρις': np.zeros(len(rows))}
for k, (a, b) in FEAT.items(): H[k] = loso(a, b); WF[k], WFOK = wf(a, b)
OPF = np.array([r['op'][1] for r in rows]); CLF = np.array([r['cl'][1] for r in rows])
day = pd.to_datetime([pd.Timestamp(r['op'][0], unit='s') for r in rows]).normalize(); wk = ((day - day.min()).days // 7).values
def picks(adj):
    sd, rs = pick_res(adj); u = np.where(sd != 0, np.nan_to_num(rs), 0.0); clv = np.where(sd != 0, sd * (CLF - OPF), np.nan); return sd, u, clv
PK = {k: picks(v) for k, v in H.items()}
rm = lambda e, m: float(np.sqrt(np.mean(e[m] ** 2)))
ALL = np.ones(len(rows), bool); rng = np.random.default_rng(11)
REF = 'on/off (live)'
P(f'el_absence_engine_compare · Ευρωλιγκα 2021-25 · ματς {len(rows)} · picks συνολων ≥8% ανοιγμα Crown')
P('\n## 1-3 LOSO: σφαλμα · ανα σεζον vs χωρις / vs on/off · ζευγαρωτη t vs on/off · picks · CLV')
SUM = {}
for k, h in H.items():
    e = YT - h; per0 = [rm(e, ys == s) - rm(YT, ys == s) for s in SE]; perR = [rm(e, ys == s) - rm(YT - H[REF], ys == s) for s in SE]
    d = (YT - H[REF]) ** 2 - e ** 2; t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if k != REF else 0.0
    sd, u, clv = PK[k]; ps = pd.Series(u[sd != 0]).groupby(ys[sd != 0]).sum()
    SUM[k] = dict(u=u.sum(), clv=np.nanmean(clv), t=t, b0=sum(x < 0 for x in per0), bR=sum(x < 0 for x in perR))
    P(f'  {k:22s} σφαλμα {rm(e, ALL):.3f} · vs χωρις {sum(x < 0 for x in per0)}/5 · vs on/off {sum(x < 0 for x in perR)}/5 · t vs on/off {t:+.2f} · picks {int((sd != 0).sum())} · μοναδες {u.sum():+6.1f} · θετ {int((ps > 0).sum())}/5 · CLV {np.nanmean(clv):+.3f} · '
      + ' '.join(f'{s[-2:]}:{ps.get(s, 0):+.1f}' for s in SE))
P('\n## 4 WALK-FORWARD (2022-23 … 2025-26, μονο προηγουμενες σεζον)')
for k, h in WF.items():
    sd, u, clv = picks(h); m = WFOK if k != 'χωρις' else np.isin(ys, SE[1:]); SUM[k]['wf'] = u[m].sum()
    P(f'  {k:22s} σφαλμα {rm(YT - h, m):.3f} · μοναδες {u[m].sum():+6.1f} · picks {int(((sd != 0) & m).sum())} · CLV {np.nanmean(clv[m]):+.3f}')
P('\n## 5 BOOTSTRAP εβδομαδων (2000): P(μοναδες μηχανης > on/off)')
uR = PK[REF][1]; W_ = np.unique(wk)
for k in H:
    if k == REF: continue
    dw = pd.Series(PK[k][1] - uR).groupby(wk).sum().reindex(W_, fill_value=0).values
    bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(2000)]); SUM[k]['boot'] = (bs > 0).mean()
    P(f'  {k:22s} Δμοναδες {dw.sum():+6.1f} · P {100 * (bs > 0).mean():.0f}% · 90% [{np.percentile(bs, 5):+.1f}, {np.percentile(bs, 95):+.1f}]')
P('\n## 6 PLACEBO (απουσιες ανακατεμενες μεταξυ ματς ιδιας σεζον, 200 φορες): P(placebo μοναδες ≥ πραγματικες)')
for k, (a, b) in FEAT.items():
    real = SUM[k]['u']; cnt = 0; vals = []
    for _ in range(200):
        pa, pb = a.copy(), b.copy()
        for Y in SE:
            idx = np.where(ys == Y)[0]; pm = rng.permutation(idx); pa[idx] = a[pm]; pb[idx] = b[pm]
        u = picks(loso(pa, pb))[1].sum(); vals.append(u); cnt += u >= real
    SUM[k]['plc'] = cnt / 200
    P(f'  {k:22s} πραγματικες {real:+.1f} · placebo μεσος {np.mean(vals):+.1f} (90%: {np.percentile(vals, 95):+.1f}) · P {100 * cnt / 200:.1f}%')
P('\n## 7 ΣΤΑ ΜΑΤΣ ΜΕ ΣΗΜΑΝΤΙΚΟΥΣ ΑΠΟΥΣΕΣ (≥12 πμ): διορθωση · picks (ROI, n, μοναδες)')
f = np.array([x['flags']['Γ'] for x in REC_]); nw = np.array([x['new']['Γ'] for x in REC_])
for lab, m in (('0 σημαντικοι', f == 0), ('1 σημαντικος', f == 1), ('2+ σημαντικοι', f >= 2), ('≥1 νεα απουσια', (f >= 1) & (nw >= 1)), ('≥1 μονο μακροχρονια', (f >= 1) & (nw == 0))):
    P(f'  {lab:20s} ({int(m.sum())}, επιδραση {np.mean(TOT[m] - T0[m]):+.2f}): ' + ' │ '.join(
        f"{k} {np.mean(H[k][m]):+.2f}, {100 * PK[k][1][m & (PK[k][0] != 0)].mean() if (m & (PK[k][0] != 0)).any() else 0:+.1f}% ({int((m & (PK[k][0] != 0)).sum())}, {PK[k][1][m].sum():+.1f}μ)" for k in H))
P('\n## ΚΡΙΣΗ απεναντι στο on/off (live)')
for k in FEAT:
    if k == REF: continue
    s = SUM[k]; R = SUM[REF]
    tests = {'σφαλμα ≥4/5 vs on/off': s['bR'] >= 4, 'ζευγ. t > 0': s['t'] > 0, 'μοναδες ≥ on/off': s['u'] >= R['u'], 'CLV οχι χειροτερο': s['clv'] >= R['clv'] - 0.02,
             'walk-forward ≥ on/off': s['wf'] >= R['wf'], 'bootstrap P ≥ 70%': s['boot'] >= .7, 'placebo < 10%': s['plc'] < .10}
    must = tests['μοναδες ≥ on/off'] and tests['CLV οχι χειροτερο'] and tests['walk-forward ≥ on/off'] and tests['placebo < 10%']
    P(f'  {k:22s} περνα {sum(tests.values())}/7 · ' + ' · '.join(f"{n} {'✓' if v else '✗'}" for n, v in tests.items()) + f" → {'ΥΠΟΨΗΦΙΑ' if must else 'οχι'}")
open('el_absence_engine_compare_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
