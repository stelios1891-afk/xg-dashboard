# -*- coding: utf-8 -*-
"""el_steam_events.py — 17/10/2026: λιστα στιγμων για Pinnacle (TOA historical) γυρω απο τις ΚΙΝΗΣΕΙΣ («steam») της Ευρωλιγκας.
Για καθε ματς / αγορα / βιβλιο (Crown 3, Bet365 8 και, αν υπαρχουν, SBOBET 31 / William Hill 10 απο odds_extra.jsonl): η ΠΡΩΤΗ κινηση
δικαιης τιμης ≥1.5 π. μεσα σε 60′ (ιδιο με bk_steam_follow). Στιγμες Pinnacle: −60′ (πριν), +5′ (αμεσως μετα), +60′.
Προτεραιοτητα: κινηση ≥2 → 1, 1.5-2 → 2. Εξοδος: el_steam_events.json (το διαβαζει το toa_el_steam_fetch.py στο GitHub)."""
import sys, io, contextlib, json, os
import numpy as np, pandas as pd
_src = open('bk_steam_follow.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1).split("for cid in (3, 8):\n    print(f'\n{\"#\"")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(_src)
sys.stdout.reconfigure(encoding='utf-8')
from statistics import NormalDist
IQ = NormalDist().inv_cdf
# επιπλεον βιβλια (αν εχουν κατεβει)
if os.path.exists('nowgoal_el/odds_extra.jsonl'):
    for l in open('nowgoal_el/odds_extra.jsonl', encoding='utf-8'):
        r = json.loads(l); g = S.get(('EL', r['ngid']))
        if not g: continue
        sg = SIG[('EL', r['t'])]; rows = []
        for q in r['rows']:
            if len(q) < 5: continue
            q = [q[0] + SHIFT] + list(q[1:])
            if q[4] != 2 or q[0] >= g['tip'] or not q[1] or not q[2] or q[2] <= 0 or q[3] <= 0: continue
            d1, d2 = q[2] + 1, q[3] + 1; p1 = (1 / d1) / (1 / d1 + 1 / d2)
            rows.append((q[0], q[1], d1, d2, q[1] + sg * IQ(min(max(p1, 1e-4), 1 - 1e-4))))
        rows.sort()
        if len(rows) >= 2: SERIES[('EL', r['ngid'], r['t'], r['cid'])] = (r['sea'], rows)
W = 3600; EV = []
for (c, ng, t, cb), (sea, rows) in SERIES.items():
    if c != 'EL': continue
    g = S[(c, ng)]; t0 = rows[0][0]
    for i in range(1, len(rows)):
        ts = rows[i][0]
        if ts - W < t0: continue
        dF = rows[i][4] - at(rows, ts - W)[4]
        if abs(dF) < 1.5: continue
        snaps = [ts - 3600, ts + 300, ts + 3600]
        EV.append(dict(ngid=ng, sea=sea, mk='spreads' if t == 21 else 'totals', bk=cb, ts=ts, dF=round(dF, 2), tip=g['tip'],
                       home=g['home'], away=g['away'], prio=1 if abs(dF) >= 2 else 2,
                       snaps=[int(s) for s in snaps if s < g['tip'] - 120]))
        break
json.dump(EV, open('el_steam_events.json', 'w', encoding='utf-8'), ensure_ascii=False)
U = {}
for e in EV:
    for s in e['snaps']: U.setdefault((e['mk'], s // 300), e['prio']); U[(e['mk'], s // 300)] = min(U[(e['mk'], s // 300)], e['prio'])
n1 = sum(1 for v in U.values() if v == 1); n2 = len(U) - n1
print(f'γεγονοτα {len(EV)} (βιβλια {sorted({e["bk"] for e in EV})}) · μοναδικα snapshots: προτ.1 {n1} · προτ.2 {n2} · κοστος 10/snapshot → {10 * n1} + {10 * n2} credits')
