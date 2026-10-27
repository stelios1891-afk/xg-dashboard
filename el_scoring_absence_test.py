# -*- coding: utf-8 -*-
"""el_scoring_absence_test.py — EUROLEAGUE ΣΥΝΟΛΑ: «ΧΑΜΕΝΟ ΣΚΟΡΑΡΙΣΜΑ» ΑΠΟΝΤΩΝ αντι για on/off (27/10/2026, Στελιος «παμε πρωτα στα τεστ
να δουμε τι μπορουμε να βρουμε» — αφορμη: Ολυμπιακος−Μπεσικτας χωρις Φουρνιε/Μιλουτινοφ/Μοντερο/Ντορσει, on/off δινει +0.6 στο συνολο).
Στησιμο ΙΔΙΟ με el_absence_onoff_test.py (1.563 ματς E2021-25, live μοντελο el_newmodel_preds, picks συνολων ≥8% ανοιγμα Crown, LOSO, ridge 1,
ιδιος ορισμος απουσιας: ≥3/10 φετινα, λεπτα ≥10′, k 1-3 πληρες / 4-10 μισο· w = λεπτα/40 × βαρος).
ΝΕΟ ΧΑΡΑΚΤΗΡΙΣΤΙΚΟ: ποντοι ανα 40′ του αποντα (τα 15 τελευταια ματς του σε Ευρωλιγκα/EuroCup ΠΡΙΝ το ματς, καθε σεζον) → «χαμενο σκοραρισμα».
  ΕΚΔΟΧΕΣ (ποντοι ομαδας − μοντελο): S1 [δικα λεπτα, δικα λεπτα×ποντοι/40] · S2 = S1 + W4 on/off · S3 [δικα λεπτα, δικα λεπτα×usage (περσι, 3Steps)].
  Αναμενομενο: συντελεστης «λεπτα×ποντοι/40» < 0 (λειπει σκορερ → η ομαδα βαζει λιγοτερους απο οσους λεει το μοντελο).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ιδια με το on/off τεστ): ΠΕΡΝΑ αν LOSO RMSE συνολου καλυτερο απο «χωρις διορθωση» σε ≥4/5 ΚΑΙ ο νεος συντελεστης ιδιο προσημο
  (<0) ≥4/5 ΚΑΙ μοναδες picks συνολων ≥ «χωρις» ΚΑΙ ΕΠΙΒΕΒΑΙΩΣΗ EuroCup 2021-25: σωστο προσημο ≥4/5 & t ≤ −2. + συγκριση με το live (W4 on/off).
ΑΓΟΡΑ (πληροφορια): κινηση γραμμης ανοιγμα→κλεισιμο και (πραγματικο − κλεισιμο) πανω στο χαμενο σκοραρισμα → «το εχει η αγορα;».
Εξοδος: el_scoring_absence_out.txt"""
import sys, io, contextlib, collections
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_absence_onoff_test.py', encoding='utf-8').read().split("open('el_absence_onoff_out.txt'")[0]
rep = [("        res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))",
        "        res.append(dict(w=w, pid=pid, ts=ts, **(pr or dict(onO=0.0, onD=0.0, usg=None))))"),
       ("def P(s=''): print(s, flush=True); out.append(str(s))", "def P(s=''): pass")]
for a, b in rep:
    assert src.count(a) == 1, a[:50]; src = src.replace(a, b)
ns = {}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows, HELD, YT, YH, YA, ys, SE, EC, tpicks, rmse, PL = (ns[k] for k in ('rows', 'HELD', 'YT', 'YH', 'YA', 'ys', 'SE', 'EC', 'tpicks', 'rmse', 'PL'))
SD, zf = ns['SD'], ns['zf']
# ---- ποντοι/40 ανα παικτη πριν απο καθε ματς ----
PP = collections.defaultdict(list)
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side in ('ph', 'pa'):
        for p in g[side]:
            if (p[3] or 0) > 0: PP[p[0]].append((ts, float(p[3]), float(p[4] or 0)))
for v in PP.values(): v.sort()
LG = float(np.sum([x[2] for v in PP.values() for x in v]) / np.sum([x[1] for v in PP.values() for x in v]) * 40)
# απλο μαζεμα προς τον μεσο της λιγκας: (Σποντοι·40 + 5·LG)/(Σλεπτα + 5)  (≈ 5 λεπτα «μεσου» παικτη)
def pts40(pid, ts):
    h = [x for x in PP.get(pid, []) if x[0] < ts - 3600][-15:]
    m = sum(x[1] for x in h); p = sum(x[2] for x in h)
    return (40 * p + 5 * LG) / (m + 5) if m > 0 else LG
def feats(own):
    return np.array([sum(p['w'] for p in own), sum(p['w'] * (pts40(p['pid'], p['ts']) - LG) for p in own),
                     sum(p['w'] * ((p['usg'] or 0) - 0) for p in own)])
FH = np.array([feats(r['ah']) for r in rows]); FA = np.array([feats(r['aa']) for r in rows])
W4H = np.array([[sum(p['w'] * zf(p, 'onO') for p in r['ah']), sum(p['w'] * zf(p, 'onD') for p in r['aa'])] for r in rows])
W4A = np.array([[sum(p['w'] * zf(p, 'onO') for p in r['aa']), sum(p['w'] * zf(p, 'onD') for p in r['ah'])] for r in rows])
XH = {'S1 λεπτα + ποντοι/40': FH[:, [0, 1]], 'S2 S1 + on/off': np.c_[FH[:, [0, 1]], W4H], 'S3 λεπτα + usage': FH[:, [0, 2]]}
XA = {'S1 λεπτα + ποντοι/40': FA[:, [0, 1]], 'S2 S1 + on/off': np.c_[FA[:, [0, 1]], W4A], 'S3 λεπτα + usage': FA[:, [0, 2]]}
NEWCOL = {'S1 λεπτα + ποντοι/40': 1, 'S2 S1 + on/off': 1, 'S3 λεπτα + usage': 1}
ALL = np.ones(len(rows), bool)
def fit(nm, tr):
    X = np.r_[XH[nm][tr], XA[nm][tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(X.shape[1]), X.T @ y)
P(f'Ευρωλιγκα 2021-25: ματς {len(rows)} · μεσος ποντοι/40 λιγκας {LG:.1f} · απουσιες {sum(len(r["ah"]) + len(r["aa"]) for r in rows)}')
allp = [p for r in rows for p in r['ah'] + r['aa']]
v40 = np.array([pts40(p['pid'], p['ts']) for p in allp])
P(f'  ποντοι/40 αποντων: μεσος {v40.mean():.1f} · 10% {np.percentile(v40, 10):.1f} · 90% {np.percentile(v40, 90):.1f}')
u0, s0 = tpicks(np.zeros(len(rows))); uL, sL = tpicks(HELD['W4 μονο on/off'])
P(f'\n## ΒΑΣΕΙΣ · LOSO RMSE συνολου: χωρις {rmse(YT, ALL):.3f} · live W4 on/off {rmse(YT - HELD["W4 μονο on/off"], ALL):.3f}')
P(f'  χωρις διορθωση     {s0}'); P(f'  live (W4 on/off)   {sL}')
P('\n## ΕΚΔΟΧΕΣ (συντελεστες: ποντοι ΟΜΑΔΑΣ ανα 40′ απουσιας · «×ποντοι/40» ανα 1 ποντο/40 πανω απο τον μεσο)')
RES = {}
for nm in XH:
    b = fit(nm, ALL); per = {s: fit(nm, ys == s) for s in SE}; j = NEWCOL[nm]
    same = sum(1 for s in SE if np.sign(per[s][j]) == np.sign(b[j]))
    h = np.zeros(len(rows))
    for Yr in SE:
        bb = fit(nm, ys != Yr); m = ys == Yr; h[m] = XH[nm][m] @ bb + XA[nm][m] @ bb
    d0 = [rmse(YT - h, ys == s) - rmse(YT, ys == s) for s in SE]; dL = [rmse(YT - h, ys == s) - rmse(YT - HELD['W4 μονο on/off'], ys == s) for s in SE]
    u, s_ = tpicks(h)
    ok = sum(x < 0 for x in d0) >= 4 and same >= 4 and b[j] < 0 and u >= u0
    RES[nm] = (ok, h, b[j])
    P(f'  {nm}: συντελεστες ' + ' · '.join(f'{x:+.3f}' for x in b) + f' · νεος (στηλη {j}) ανα σεζον ' + ' '.join(f'{s[-2:]}:{per[s][j]:+.3f}' for s in SE) + f' (ιδιο προσημο {same}/5)')
    P(f'     RMSE {rmse(YT - h, ALL):.3f} · vs χωρις ' + ' '.join(f'{x:+.3f}' for x in d0) + f' → {sum(x < 0 for x in d0)}/5 · vs live ' + ' '.join(f'{x:+.3f}' for x in dL) + f' → {sum(x < 0 for x in dL)}/5')
    P(f'     {s_}')
# ---- EuroCup επιβεβαιωση (απλη βαση του on/off τεστ) ----
er, EY, Ey = ns['er'], ns['EY'], ns['Ey']
EXs = np.array([[1, e[2], *feats(e[3])[:2]] for e in er])
def ols(m, X):
    Xm, Ym = X[m], EY[m]; b = np.linalg.lstsq(Xm, Ym, rcond=None)[0]; r_ = Ym - Xm @ b
    se = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(Ym) - Xm.shape[1]) * np.linalg.inv(Xm.T @ Xm))); return b, se
b, se = ols(np.ones(len(EY), bool), EXs); ok_s = sum(ols(Ey == s, EXs)[0][3] < 0 for s in EC)
EC_OK = ok_s >= 4 and b[3] / se[3] <= -2
P(f'\n## ΕΠΙΒΕΒΑΙΩΣΗ EuroCup 2021-25 · ομαδα-ματς {len(EY)} · λεπτα {b[2]:+.2f} · λεπτα×ποντοι/40 {b[3]:+.3f} (t {b[3] / se[3]:+.1f}) · σωστο προσημο {ok_s}/5 → '
  + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if EC_OK else 'ΔΕΝ επιβεβαιωνεται'))
# ---- ΑΓΟΡΑ ----
LS = np.array([sum(p['w'] * (pts40(p['pid'], p['ts']) - LG) for p in r['ah'] + r['aa']) for r in rows])
MW = np.array([sum(p['w'] for p in r['ah'] + r['aa']) for r in rows])
mv = np.array([r['cl'][1] - r['op'][1] for r in rows]); ac = np.array([r['hs'] + r['as_'] - r['cl'][1] for r in rows]); ao = np.array([r['hs'] + r['as_'] - r['op'][1] for r in rows])
X2 = np.c_[np.ones(len(rows)), MW, LS]
for lab, y in (('κινηση γραμμης ανοιγμα→κλεισιμο', mv), ('πραγματικο − ανοιγμα', ao), ('πραγματικο − κλεισιμο', ac), ('πραγματικο − μοντελο (χωρις διορθωση)', YT)):
    bb = np.linalg.lstsq(X2, y, rcond=None)[0]; r_ = y - X2 @ bb; se_ = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(y) - 3) * np.linalg.inv(X2.T @ X2)))
    P(f'  ΑΓΟΡΑ · {lab:38s}: ανα 40′ απουσιας {bb[1]:+.2f} (t {bb[1] / se_[1]:+.1f}) · ανα 40′×(ποντοι/40 − μεσος) {bb[2]:+.3f} (t {bb[2] / se_[2]:+.1f})')
big = LS >= np.percentile(LS, 90)
P(f'  ματς με το 10% μεγαλυτερο χαμενο σκοραρισμα ({int(big.sum())}): πραγμ − μοντελο {YT[big].mean():+.2f} · πραγμ − ανοιγμα {ao[big].mean():+.2f} · πραγμ − κλεισιμο {ac[big].mean():+.2f} · κινηση γραμμης {mv[big].mean():+.2f}')
# ---- παραδειγμα ----
P('\n## ΠΑΡΑΔΕΙΓΜΑ (ποντοι/40 φετινα, ως το 15 τελευταια ματς):')
NAME = ns['NAME']; inv = {v: k for k, v in NAME.items()}
for nm in ('FOURNIER, EVAN', 'MILUTINOV, NIKOLA', 'MONTERO, JEAN', 'DORSEY, TYLER'):
    pid = inv.get(nm); P(f'   {nm:18s} ' + (f'{pts40(pid, 2e9):.1f} ποντοι/40' if pid else 'δεν βρεθηκε'))
P('\nΑΠΟΦΑΣΗ (προ-δηλωμενα): ' + ' · '.join(f'{nm}: EL {"✓" if v[0] else "✗"}' for nm, v in RES.items()) + f' · EuroCup {"✓" if EC_OK else "✗"}')
open('el_scoring_absence_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
