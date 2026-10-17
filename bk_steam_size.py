# -*- coding: utf-8 -*-
"""bk_steam_size.py — 17/10/2026 (Στελιος: «αν καναμε alert για τετοιες κινησεις, απο ποσο και πανω θα ημασταν αισιοδοξοι οτι σημαινει κατι;»).
Ενα γεγονος ανα ματς/αγορα/βιβλιο = η ΜΕΓΑΛΥΤΕΡΗ κινηση δικαιης τιμης μεσα σε 60′ (pre-match). Ανα μεγεθος κινησης:
  ΚΡΑΤΑΕΙ = ποσο % της κινησης υπαρχει ακομα στο κλεισιμο · ΣΚΟΡ = ποσο % της κινησης «επιβεβαιωσε» το τελικο σκορ (μ. ορος (αποτελεσμα − τιμη ΠΡΙΝ
  την κινηση) προς την πλευρα της κινησης / μεγεθος) — 100% = η κινηση ηταν ακριβως σωστη, >100% = λιγη (αξιζει ακολουθηση), <100% = υπερβολη ·
  ROI ακολουθησης στην τιμη ΑΜΕΣΩΣ μετα: στο ιδιο βιβλιο και στο αλλο (αν αυτο δεν ειχε ακολουθησει ≥½). Εξοδος: bk_steam_size_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
_src = open('bk_steam_follow.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1).split("for cid in (3, 8):\n    print(f'\n{\"#\"")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(_src)
sys.stdout.reconfigure(encoding='utf-8')
W = 3600; R = []
for (c, ng, t, cb), (sea, rows) in SERIES.items():
    g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']; t0 = rows[0][0]; best = None
    for i in range(1, len(rows)):
        if rows[i][0] - W < t0: continue
        b = at(rows, rows[i][0] - W); d = rows[i][4] - b[4]
        if best is None or abs(d) > abs(best[0]): best = (d, i, b)
    if best is None or abs(best[0]) < 0.25: continue
    d, i, b = best; sd = 1 if d > 0 else -1; ts = rows[i][0]; q = rows[i]
    rec = dict(comp=c, sea=sea, t=t, bk=cb, mv=abs(d), hrs=(g['tip'] - ts) / 3600,
               keep=sd * (rows[-1][4] - b[4]) / abs(d), real=sd * (y - b[4]) / abs(d), realpts=sd * (y - b[4]),
               same=settle(y, q[1], q[2] if sd == 1 else q[3], sd))
    o = SERIES.get((c, ng, t, 11 - cb))     # 3↔8
    rec['oth'] = np.nan
    if o:
        ob = at(o[1], ts - W); o0 = at(o[1], ts)
        if ob and o0 and sd * (o0[4] - ob[4]) < 0.5 * abs(d): rec['oth'] = settle(y, o0[1], o0[2] if sd == 1 else o0[3], sd)
    R.append(rec)
D = pd.DataFrame(R)
BINS = ((0.5, 1), (1, 1.5), (1.5, 2), (2, 2.5), (2.5, 3), (3, 4), (4, 99))
def roi(v):
    v = v.dropna(); return f'{100 * v.mean():+6.1f}% ({len(v):4d})' if len(v) >= 15 else f'{"—":>7s} ({len(v):4d})'
def pos(y, col):
    s = y.groupby('sea')[col].mean()[y.groupby('sea')[col].count() >= 5]; return f'{int((s > 0).sum())}/{len(s)}'
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
    for bk in (3, 8):
        y0 = D[(D.t == t) & (D.bk == bk)]
        print(f'\n== {nm} · {BOOK[bk]} · {len(y0)} ματς (μεγαλυτερη κινηση σε 60′ ανα ματς) ==')
        print(f'   {"κινηση":8s} {"ματς":>5s} {"% ματς":>6s} │ {"ΚΡΑΤΑΕΙ":>8s} │ {"ΣΚΟΡ επιβεβ.":>12s} {"(±)":>6s} │ {"ROI ιδιο βιβλιο":>16s} {"θετ":>4s} │ {"ROI στο " + BOOK[11 - bk]:>16s} {"θετ":>4s}')
        for lo, hi in BINS:
            y = y0[(y0.mv >= lo) & (y0.mv < hi)]
            if len(y) < 15: continue
            se = y.realpts.std() / np.sqrt(len(y)) / y.mv.mean()
            lab = f'{lo:g}-{hi:g}' if hi < 99 else f'≥{lo:g}'
            print(f'   {lab:8s} {len(y):5d} {100 * len(y) / len(y0):5.0f}% │ {100 * y.keep.mean():7.0f}% │ {100 * y.real.mean():11.0f}% {100 * se:5.0f}% │ {roi(y.same):>16s} {pos(y, "same"):>4s} │ {roi(y.oth):>16s} {pos(y, "oth"):>4s}')
        for lo in (1.5, 2, 3):
            y = y0[y0.mv >= lo]; se = y.realpts.std() / np.sqrt(len(y)) / y.mv.mean()
            print(f'   ≥{lo:<7g} {len(y):5d} {100 * len(y) / len(y0):5.0f}% │ {100 * y.keep.mean():7.0f}% │ {100 * y.real.mean():11.0f}% {100 * se:5.0f}% │ {roi(y.same):>16s} {pos(y, "same"):>4s} │ {roi(y.oth):>16s} {pos(y, "oth"):>4s}')
D.to_pickle('bk_steam_size.pkl')
