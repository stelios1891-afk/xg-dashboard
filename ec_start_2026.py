# -*- coding: utf-8 -*-
"""ec_start_2026.py — ΑΦΕΤΗΡΙΑ EuroCup 2026-27 με ΤΡΕΙΣ γνωμες: Eurohoops + Taking The Charge + αποδοσεις νικητη (broker, μετα 1η)
(1/10/2026, Στελιος: «στο φετινο βαλε και 3η γνωμη αυτη των αποδοσεων»). Χρηση: python ec_start_2026.py [carry] [κ_x]  (προεπιλογη .7 3).
z καθε γνωμης μεσα στις 32 (καταταξεις: κανονικο σκορ θεσης · αποδοσεις: −ln τυποποιημενο) → μεσος → κ_x·z.
Αφετηρια = carry × περσινο EuroCup (παλιες) / 0 (νεες) + κ_x·z. Εξοδος: ec_start_2026_out.txt"""
import json, math, sys, io, contextlib
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
CARRY = float(sys.argv[1]) if len(sys.argv) > 1 else .7
KX = float(sys.argv[2]) if len(sys.argv) > 2 else 3
NS = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('ec_newcomers_2026.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '')
         .replace("open('ec_newcomers_2026_out.txt', 'w'", "open('_unused_nc.txt', 'w'"), NS)
res = {r[0]: r for r in NS['res']}; EH, TT, RKT = NS['EH'], NS['TT'], NS['RKT']
OD = json.load(open('ec_outrights.json', encoding='utf-8'))['U2026']['odds']
nd = NormalDist(); names = list(res)
lo = {n: -math.log(OD[n]) for n in names}; m_, s_ = np.mean(list(lo.values())), np.std(list(lo.values()))
out = []
P = lambda s='': (out.append(s), print(s))
P(f'=== ΑΦΕΤΗΡΙΑ EuroCup 2026-27 · περσι ×{CARRY} · ειδικοι ×{KX} · 3 γνωμες (Eurohoops / TTC / αποδοσεις νικητη) ===')
P('  ομαδα | περσι (×carry) | EH θεση→z | TTC θεση→z | αποδοση→z | μεσος z | ειδικοι ποντοι | ΑΦΕΤΗΡΙΑ | (με 2 γνωμες)')
rows = []
for n in names:
    r = res[n]; isnew = r[2] is None or r[6]
    prev = 0.0 if isnew else r[4] / 0.7 * CARRY          # r[4] = 0.7 × περσινο
    z1 = nd.inv_cdf(1 - (EH.index(n) + .5) / len(EH)); z2 = nd.inv_cdf(1 - (RKT[n] - .5) / len(TT)) if RKT[n] else None
    z3 = (lo[n] - m_) / s_
    zs = [z for z in (z1, z2, z3) if z is not None]; z = float(np.mean(zs)); z_old = float(np.mean([z for z in (z1, z2) if z is not None]))
    rows.append((prev + KX * z, n, isnew, prev, z1, z2, z3, z, prev + KX * z_old))
for st, n, isnew, prev, z1, z2, z3, z, st2 in sorted(rows, reverse=True):
    P(f'  {"🆕" if isnew else "  "} {n:34s} | {("νεα" if isnew else f"{prev:+.1f}"):>5s} | {EH.index(n) + 1:2d}→{z1:+.2f} | {RKT[n]:2d}→{z2:+.2f} | {OD[n]:6.2f}→{z3:+.2f} | {z:+.2f} | {KX * z:+5.1f} | {st:+5.1f} | ({st2:+5.1f})'
      if z2 is not None else f'  {n}')
P('')
nw = [r for r in rows if r[2]]; od = [r for r in rows if not r[2]]
P(f'  νεες {np.mean([r[0] for r in nw]):+.1f} · παλιες {np.mean([r[0] for r in od]):+.1f} (με 2 γνωμες: {np.mean([r[8] for r in nw]):+.1f} / {np.mean([r[8] for r in od]):+.1f})')
open('ec_start_2026_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
