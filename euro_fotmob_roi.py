# -*- coding: utf-8 -*-
"""euro_fotmob_roi.py — ROI στα ΚΑΘΑΡΑ FotMob-xG ευρωπαικα ματς (και οι 2 πλευρες shots),
v6 δειγμα, Crown closing. ΔΥΟ μετρησεις με ΣΩΣΤΟ quarter-aware cover (οχι το live quarter-bug):
  - OUTSIDERS (η πλευρα που παιρνει το χαντικαπ)
  - ΦΑΒΟΡΙ (η πλευρα που το δινει)
edge = pw·(o−1)·(1−MARGIN) − (1−pw−pp)· φιλτρο αποδοσεων 1.70-2.10 και στα δυο (συγκρισιμοτητα).
Καθαρα περιγραφικο — μια εκτελεση.
"""
import json, glob, pickle, math, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'dashboard')
import picks
import lines_common as lc

V = pickle.load(open('euro_v6_preds.pkl', 'rb'))
MIDS = V['mids']; LH = np.array(V['lh']); LA = np.array(V['la'])
GD = np.array(V['gd']); SEA = np.array(V['sea'])
FM = np.array([(h == 'shots' and a == 'shots') for h, a in zip(V['src_h'], V['src_a'])])

def parse_line(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None

SNAP = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r['cid'] != 3:
            continue
        rows = []
        for mt, u, g, dn in r.get('ah') or []:
            gl = parse_line(g)
            try:
                oh = float(u) + 1; oa = float(dn) + 1
            except (TypeError, ValueError):
                continue
            if gl is None or mt is None:
                continue
            rows.append((int(mt), -gl, oh, oa))
        if rows:
            rows.sort(); SNAP[str(r['mid'])] = rows[-1]

MARGIN = picks.MARGIN; OMIN, OMAX = picks.OMIN, picks.OMAX

bets = {'dog': [], 'fav': []}
for i, mid in enumerate(MIDS):
    if not FM[i]:
        continue
    s = SNAP.get(mid)
    if not s:
        continue
    _, lf, oh, oa = s
    dist = picks.gd_dist(max(LH[i], 0.05), max(LA[i], 0.05))
    # πλευρες: home line=lf, away line=-lf. fav = οποιος δινει (line<0), dog = ο αλλος.
    for side, ln, o in ((1, lf, oh), (-1, -lf, oa)):
        role = 'fav' if ln < 0 else ('dog' if ln > 0 else ('fav' if o < 2.0 else 'dog'))
        pw, pp = lc.cover_q(dist, side, ln)
        if pw <= 0:
            continue
        edge = pw * (o - 1) * (1 - MARGIN) - (1 - pw - pp)
        if not (OMIN <= o <= OMAX):
            continue
        pnl = picks.settle(GD[i], side, ln, o)
        bets[role].append(dict(sea=SEA[i], edge=edge, pnl=pnl, o=o, ln=ln))

n_fm = int(FM.sum())
print(f'ΚΑΘΑΡΑ FotMob+FotMob ματς v6: {n_fm}  (με Crown closing: '
      f'{sum(1 for i,m in enumerate(MIDS) if FM[i] and m in SNAP)})')
print(f'φιλτρο αποδοσεων {OMIN}-{OMAX} και στις 2 πλευρες · quarter-aware cover · MARGIN 3%')
print()
for role, lbl in (('dog', 'OUTSIDERS (παιρνουν χαντικαπ)'), ('fav', 'ΦΑΒΟΡΙ (δινουν χαντικαπ)')):
    B = bets[role]
    print(f'=== {lbl} — συνολο αξιολογημενων πλευρων: {len(B)}')
    print(f'  {"edge>=":>7s} {"n":>5s} {"ROI%±SE":>15s} {"μοναδες":>8s}')
    for thr in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10):
        b = [x['pnl'] for x in B if x['edge'] >= thr]
        if len(b) < 3:
            print(f'  {thr*100:6.0f}% {len(b):5d} {"-":>15s}')
            continue
        m_ = np.mean(b); se = np.std(b, ddof=1) / math.sqrt(len(b))
        print(f'  {thr*100:6.0f}% {len(b):5d} {m_*100:+7.2f}±{se*100:5.2f} {np.sum(b):+7.1f}u')
    # τυφλο (ολες οι πλευρες του ρολου στο φιλτρο αποδοσεων)
    b = [x['pnl'] for x in B]
    if b:
        print(f'  τυφλο ολα: {np.mean(b)*100:+.2f}% (n={len(b)})')
    thr = 0.04 if role == 'fav' else 0.10
    print(f'  ανα σεζον @edge>={thr*100:.0f}%: ' + '  '.join(
        f'{s}: {np.mean([x["pnl"] for x in B if x["sea"]==s and x["edge"]>=thr])*100:+.1f}%'
        f'({sum(1 for x in B if x["sea"]==s and x["edge"]>=thr)})'
        for s in ('2223', '2324', '2425', '2526')
        if sum(1 for x in B if x['sea'] == s and x['edge'] >= thr) > 0))
    print()
