# -*- coding: utf-8 -*-
"""bk_steam_lag_speed.py — 17/10/2026 (Στελιος: «τα 15 λεπτα ειναι πολλα»). Συνεχεια bk_steam_lag: ποσο ΓΡΗΓΟΡΑ ακολουθει το αργο βιβλιο
και τι ROI μενει αν μπεις στο 0′ / 1′ / 2′ / 5′ / 15′. «Δεν ακολουθησε» οριζεται ΤΩΡΑ στη στιγμη του alert (οχι στο +5′).
Χρονος ακολουθησης = πρωτη αλλαγη του αργου βιβλιου που καλυπτει ≥½ της κινησης. Εξοδος: bk_steam_lag_speed_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
_src = open('bk_steam_follow.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1).split("for cid in (3, 8):\n    print(f'\n{\"#\"")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(_src)
sys.stdout.reconfigure(encoding='utf-8')
DL = (('0′', 0), ('1′', 60), ('2′', 120), ('5′', 300), ('15′', 900))
def run(src, dst, X=1.5, W=3600):
    out = []
    for (c, ng, t, cb), (sea, rows) in SERIES.items():
        if cb != src: continue
        oth = SERIES.get((c, ng, t, dst))
        if not oth: continue
        orows = oth[1]; g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']; t0 = rows[0][0]
        for i in range(1, len(rows)):
            ts = rows[i][0]
            if ts - W < t0: continue
            dF = rows[i][4] - at(rows, ts - W)[4]
            if abs(dF) < X: continue
            sd = 1 if dF > 0 else -1
            ob = at(orows, ts - W); o0 = at(orows, ts)
            if ob is None or o0 is None: break
            if sd * (o0[4] - ob[4]) >= 0.5 * abs(dF): break      # ηδη ακολουθησε → εκτος
            fol = next((q[0] - ts for q in orows if q[0] > ts and sd * (q[4] - ob[4]) >= 0.5 * abs(dF)), None)
            rec = dict(comp=c, sea=sea, t=t, follow_s=fol, hrs=(g['tip'] - ts) / 3600)
            for lab, d in DL:
                q = at(orows, ts + d) if ts + d < g['tip'] else None
                rec[lab] = np.nan if q is None else settle(y, q[1], q[2] if sd == 1 else q[3], sd)
            out.append(rec); break
    return pd.DataFrame(out)
def roi(v):
    v = v.dropna(); return f'{100 * v.mean():+6.1f}% ({len(v)})' if len(v) >= 8 else '—'
for src, dst in ((3, 8), (8, 3)):
    A = run(src, dst)
    print(f'\n{"#" * 120}\nALERT {BOOK[src]} ≥1.5 π. σε 60′ → ποντος στο {BOOK[dst]} (που ΔΕΝ ειχε ακολουθησει τη στιγμη του alert)')
    for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
        y = A[A.t == t]; f = y.follow_s
        n = len(y); p = lambda s: 100 * ((f.notna()) & (f <= s)).sum() / n
        print(f'\n== {nm} · {n} alerts ==')
        print(f'   ποτε ακολουθησε το {BOOK[dst]}: ≤1′ {p(60):.0f}% · ≤2′ {p(120):.0f}% · ≤5′ {p(300):.0f}% · ≤15′ {p(900):.0f}% · ≤60′ {p(3600):.0f}% · ποτε {100 * f.isna().mean():.0f}%'
              + (f' · διαμεσος (οσοι ακολουθησαν) {f.dropna().median() / 60:.0f}′' if f.notna().any() else ''))
        print('   ' + f'{"":14s}' + ''.join(f'{l:>15s}' for l, _ in DL))
        for lab, yy in [('ΟΛΑ', y)] + [(cn, y[y.comp == c]) for c, cn, _ in COMPS]:
            print(f'   {lab:14s}' + ''.join(f'{roi(yy[l]):>15s}' for l, _ in DL))
