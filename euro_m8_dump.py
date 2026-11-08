# -*- coding: utf-8 -*-
"""euro_m8_dump.py — 5/11/2026: τρεχει το euro_adj_methods (Κ1 δικαιοσυνη / Κ2 RPS / Κ3 ROI του 9/10) πανω στο διορθωμενο harness (κοκκινες emps) και κρατα τις προβλεψεις
χωρις/με Μ8 για το euro_m8_rejudge. Χρηση: python euro_m8_dump.py 0.6|0.8 → euro_adj_methods_emps<μιξη>_out.txt + euro_m8_dump_<μιξη>.pkl.
ΔΕΝ γραφει το euro_m8_coef.json (το live μενει ως εχει): οι νεοι συντελεστες μπαινουν μονο στο pkl."""
import sys, io, json, pickle, contextlib
import numpy as np
BL = float(sys.argv[1])
import picks
picks.BLEND = BL; picks._BLEND_D = (picks.BLEND_EARLY - BL) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
io.StringIO = _Q
g = {'__name__': 'md'}
buf = _Q()
with contextlib.redirect_stdout(buf):
    exec(open('euro_adj_methods.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
open(f'euro_adj_methods_emps{BL}_out.txt', 'w', encoding='utf-8').write(buf.getvalue())
assert abs(g['b_bl'] - BL) < 1e-9
G, F, pois = g['g'], g['F'], g['pois']
Xa = np.c_[np.ones(len(F)), np.log(F.l0F), np.log(F.l0A), F.Dt, F.home]; Xd = np.c_[np.ones(len(F)), np.log(F.l0A), np.log(F.l0F), -F.Dt, -F.home]
full = pois(np.r_[Xa, Xd], np.r_[F.ya.values, F.yd.values])
INS = g['RES']['M8'][0][0.5][0]; BASE = g['BASE']; M4 = g['RES']['M4'][0][0.5][0]
pickle.dump(dict(MIDS=[str(m) for m in G['MIDS']], SEA=list(g['SEA']), COMP=list(G['COMP']), GD=np.asarray(G['GD'], float), FM=np.asarray(G['FMm']),
                 BASE=(np.asarray(BASE[0]), np.asarray(BASE[1])), INS=(np.asarray(INS[0]), np.asarray(INS[1])), M4=(np.asarray(M4[0]), np.asarray(M4[1])), COEF8={k: list(v) for k, v in g['COEF8'].items()}, full=list(full), n_obs=len(F)),
            open(f'euro_m8_dump_{BL}.pkl', 'wb'))
sys.__stdout__.write(f'ok {BL} {len(G["MIDS"])}\n')
