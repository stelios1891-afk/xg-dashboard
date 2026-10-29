# -*- coding: utf-8 -*-
"""el_total_vs_close.py — ΕΥΡΩΛΙΓΚΑ: ποσο κοντα στη γραμμη ΚΛΕΙΣΙΜΑΤΟΣ συνολου (Crown) τελειωνει ενα ματς; (29/10/2026, Στελιος)
Κανονικη περιοδος E2021-E2025, ΧΩΡΙΣ παρατασεις (el_box min > 200 ή ισοπαλια στο 40′ → εκτος).
Εξοδος: el_total_vs_close_out.txt"""
import sys, io, json, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
LT = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split('ATH = ')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), LT)
sys.stdout.reconfigure(encoding='utf-8')
D, REC, TOT, SE5 = LT['D'], LT['REC'], LT['TOT'], LT['SE5']
BOX = json.load(open('el_box.json', encoding='utf-8'))
idx = {}
for b in BOX.values(): idx[(b['season'], b['hs'], b['as_'], b['utc'][:10])] = b
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows = []; n_ot = 0; n_nobox = 0
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]; tt = pd.Timestamp(D.t.values[pos])
    b = None
    for dd in (0, -1, 1):
        b = idx.get((sea, int(D.hs.values[pos]), int(D.as_.values[pos]), str((tt + pd.Timedelta(days=dd)).date())))
        if b: break
    if b is None: n_nobox += 1; continue
    if b.get('min', 200) > 200.5: n_ot += 1; continue
    c = d_[0]; L = float(c[2])
    rows.append(dict(sea=sea, L=L, mu=float(c[1]), tot=TOT[pos], d=TOT[pos] - L))
X = pd.DataFrame(rows)
P(f'ματς: {len(X)} (χωρις παραταση) · παρατασεις που βγηκαν: {n_ot} · χωρις box: {n_nobox}')
d = X.d.values
P(f'\n(τελικο − γραμμη κλεισιματος), ποντοι:')
P(f'  μεσος ορος {d.mean():+.2f} · διαμεσος {np.median(d):+.1f} · τυπικη αποκλιση {d.std():.1f} · μεση ΑΠΟΛΥΤΗ αποσταση {np.abs(d).mean():.1f}')
P(f'  over {np.mean(d > 0) * 100:.1f}% · under {np.mean(d < 0) * 100:.1f}% · ακριβως στη γραμμη {np.mean(d == 0) * 100:.1f}%')
for k in (2.5, 5, 10, 15, 20, 25, 30):
    P(f'  μεσα σε ±{k:>4}: {np.mean(np.abs(d) <= k) * 100:5.1f}%')
P('\nκατανομη (ποντοι πανω/κατω απο τη γραμμη):')
bins = [-99, -30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 30, 99]
lab = ['≤−30', '−30…−20', '−20…−15', '−15…−10', '−10…−5', '−5…0', '0…+5', '+5…+10', '+10…+15', '+15…+20', '+20…+30', '≥+30']
h = np.histogram(d, bins=bins)[0]
for l, c in zip(lab, h): P(f'  {l:>10}: {c:4d} ({c / len(d) * 100:4.1f}%) ' + '█' * int(round(c / len(d) * 200)))
P('\nανα σεζον: μεσος (τελικο − γραμμη) · τυπ. αποκλιση · μεση απολυτη')
for s in sorted(X.sea.unique()):
    z = X[X.sea == s].d.values; P(f'  {s}: n {len(z)} · {z.mean():+.2f} · {z.std():.1f} · {np.abs(z).mean():.1f}')
open('el_total_vs_close_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ΜΙΣΑ: ισορροπει το 2ο ημιχρονο; (ByQuarter απο el_pbp) ----
import os
key_of = {}
for k, b in BOX.items(): key_of[(b['season'], b['hs'], b['as_'], b['utc'][:10])] = k
H = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]; tt = pd.Timestamp(D.t.values[pos]); k = None
    for dd in (0, -1, 1):
        k = key_of.get((sea, int(D.hs.values[pos]), int(D.as_.values[pos]), str((tt + pd.Timedelta(days=dd)).date())))
        if k: break
    if not k or BOX[k].get('min', 200) > 200.5 or not os.path.exists(f'el_pbp/{k}.json'): continue
    bq = json.load(open(f'el_pbp/{k}.json', encoding='utf-8'))['box'].get('ByQuarter') or []
    if len(bq) != 2: continue
    q = [sum(int(t.get(f'Quarter{j}') or 0) for t in bq) for j in (1, 2, 3, 4)]
    if sum(q) != TOT[pos]: continue
    H.append(dict(sea=sea, L=float(d_[0][2]), q1=q[0], h1=q[0] + q[1], h2=q[2] + q[3], tot=TOT[pos]))
H = pd.DataFrame(H)
sh1 = (H.h1 / H.tot).mean(); sq1 = (H.q1 / H.tot).mean()
P(f'\n=== ΜΙΣΑ (ματς με σκορ ανα περιοδο: {len(H)}) ===')
P(f'μεριδιο ποντων: 1η περιοδος {sq1 * 100:.1f}% · 1ο ημιχρονο {sh1 * 100:.1f}% · 2ο ημιχρονο {(1 - sh1) * 100:.1f}%')
H['e1'] = H.h1 - sh1 * H.L; H['e2'] = H.h2 - (1 - sh1) * H.L; H['eQ'] = H.q1 - sq1 * H.L; H['erest'] = (H.tot - H.q1) - (1 - sq1) * H.L
def reg(x, y):
    b = np.polyfit(x, y, 1)[0]; r = np.corrcoef(x, y)[0, 1]; se = np.sqrt((1 - r * r) / (len(x) - 2)) * np.std(y) / np.std(x); return b, b / se
b, t = reg(H.e1.values, H.e2.values)
P(f'1ο ημιχρονο vs αναμενομενο (μεριδιο × γραμμη κλεισιματος) → 2ο ημιχρονο vs αναμενομενο: κλιση {b:+.3f} (t {t:+.1f})')
P('   (κλιση 0 = το 2ο ημιχρονο ειναι «κανονικο», ουτε ισορροπει ουτε συνεχιζει · <0 = ισορροπει/αντισταθμιζει · >0 = συνεχιζει στο ιδιο)')
b, t = reg(H.eQ.values, H.erest.values)
P(f'1η περιοδος → υπολοιπο ματς (Q2-Q4): κλιση {b:+.3f} (t {t:+.1f})')
P('\nανα ζωνη αποκλισης 1ου ημιχρονου (ποντοι vs αναμενομενο): ματς · μεσο 2ο ημιχρονο vs αναμενομενο · τελικο vs γραμμη · % over')
for lo, hi, lab in ((-99, -12, '≤−12 (πολυ λιγοι)'), (-12, -6, '−12…−6'), (-6, 6, '−6…+6'), (6, 12, '+6…+12'), (12, 99, '≥+12 (πολυ πολλοι)')):
    z = H[(H.e1 > lo) & (H.e1 <= hi)]
    P(f'  {lab:>18}: {len(z):4d} · 2ο ημιχ {z.e2.mean():+5.2f} · τελικο−γραμμη {(z.tot - z.L).mean():+6.2f} · over {np.mean(z.tot > z.L) * 100:4.1f}%')
open('el_total_vs_close_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
