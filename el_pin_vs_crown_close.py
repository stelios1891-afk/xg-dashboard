# -*- coding: utf-8 -*-
"""el_pin_vs_crown_close.py — 17/10/2026: ποιο ΚΛΕΙΣΙΜΟ ειναι πιο ακριβες στην Ευρωλιγκα: Pinnacle (TOA, 5′ πριν) ή Crown / Bet365 / SBOBET (Nowgoal);
Ιδια ματς. MSE = μεσο τετραγωνικο σφαλμα (αποτελεσμα − δικαιη τιμη κλεισιματος), μικροτερο = πιο ακριβες.
+ ROI στην Pinnacle-κλεισιμο οταν το κλεισιμο ενος αλλου βιβλιου διαφωνει ≥1 / ≥2 π. (ποντος προς τη μερια του αλλου βιβλιου).
Ελεγχος για το ευρημα el_steam_pinnacle (ακολουθωντας κινησεις στην Pinnacle +12.5% στα συνολα)."""
import sys, io, contextlib, json, glob
import numpy as np, pandas as pd
_src = open('el_steam_events.py', encoding='utf-8').read().split('W = 3600; EV = []')[0]
exec(_src)
_p = open('el_steam_pinnacle.py', encoding='utf-8').read().split('EV = json.load')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
exec(_p)
sys.stdout.reconfigure(encoding='utf-8')
G = [(ng, g) for (c, ng), g in S.items() if c == 'EL']
R = []
for l in open('toa_el_closing.jsonl', encoding='utf-8'):
    r = json.loads(l); ct = ts_(r['commence'])
    c = [(ng, g) for ng, g in G if abs(g['tip'] - ct) <= 1500]
    best, bs = None, 0
    for ng, g in c:
        s = difflib.SequenceMatcher(None, norm(r['home']), norm(g['home'])).ratio() + difflib.SequenceMatcher(None, norm(r['away']), norm(g['away'])).ratio()
        if s > bs: best, bs = (ng, g), s
    if not best or bs < 0.9: continue
    ng, g = best
    for mk, t in (('spreads', 21), ('totals', 23)):
        q = fair(r, mk)
        if not q: continue
        y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']
        rec = dict(sea=SERIES.get(('EL', ng, t, 3), ('?',))[0], mk=mk, y=y, pin=q['F'], pL=q['L'], pd1=q['d1'], pd2=q['d2'])
        for cid, nm in ((3, 'Crown'), (8, 'Bet365'), (31, 'SBOBET'), (10, 'WH')):
            sr = SERIES.get(('EL', ng, t, cid))
            rec[nm] = sr[1][-1][4] if sr else np.nan
        R.append(rec)
D = pd.DataFrame(R)
for mk, nm in (('spreads', 'ΧΑΝΤΙΚΑΠ'), ('totals', 'ΣΥΝΟΛΑ')):
    y0 = D[D.mk == mk]
    print(f'\n== {nm} · Ευρωλιγκα · ματς με Pinnacle κλεισιμο: {len(y0)} ==')
    for bk in ('Crown', 'Bet365', 'SBOBET', 'WH'):
        y = y0[y0[bk].notna()]
        if len(y) < 50: continue
        a = (y.y - y.pin) ** 2; b = (y.y - y[bk]) ** 2; d = b - a
        print(f'   ιδια ματς Pinnacle vs {bk:7s} n {len(y):4d} · MSE Pinnacle {a.mean():7.2f} · {bk} {b.mean():7.2f} · διαφορα {d.mean():+6.2f} ± {d.std() / np.sqrt(len(d)):.2f}'
              f'  (+ = Pinnacle πιο ακριβης) · μεση διαφορα τιμων |Pin−{bk}| {np.mean(np.abs(y.pin - y[bk])):.2f}')
    for bk in ('Crown', 'Bet365', 'SBOBET'):
        y = y0[y0[bk].notna()].copy(); gap = y[bk] - y.pin
        for th in (1, 2):
            z = y[np.abs(gap) >= th]; sd = np.sign(gap[np.abs(gap) >= th])
            p = [settle(r.y, r.pL, r.pd1 if s > 0 else r.pd2, s) for r, s in zip(z.itertuples(), sd)]
            z = z.assign(p=p); ps = z.groupby('sea').p.mean()
            print(f'   Pinnacle-κλεισιμο προς τη μερια του {bk:7s} οταν διαφωνει ≥{th}: n {len(z):4d} · ROI {100 * np.mean(p):+6.1f}% · θετικες σεζον {int((ps > 0).sum())}/{len(ps)}')
