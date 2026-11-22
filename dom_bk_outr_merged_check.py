# -*- coding: utf-8 -*-
"""dom_bk_outr_merged_check.py — αποδοσεις νικητη που ελειπαν (ACB 2023-24 +13 μερες, TBL 2025-26 +12 μερες απο dom_outrights_new) μεσα στη
FINAL μηχανη: RMSE αγων 1-10 / ολα των ΣΥΓΚΕΚΡΙΜΕΝΩΝ σεζον πριν → μετα (10/10/2026). Αναφορα, οχι νεο κριτηριο (το κx εχει ηδη περασει σε ACB/TBL)."""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, pickle
import numpy as np
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = (_src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
        .replace("open('dom_outrights.json'", "open('dom_outrights_merged.json'").split("KX = (0, 1, 2, 3, 4, 6)")[0])
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
FINAL = {'ACB': (.7, 12, 9999, .5, False, -8, 2), 'TBL': (1.0, 4, 60, .5, True, -8, 1)}
def _job(lg): return lg, run(lg, *FINAL[lg])[:2]
if __name__ == '__main__':
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    with Pool(2) as p: res = dict(p.map(_job, ['ACB', 'TBL']))
    R = pickle.load(open('dom_bk_audit_R.pkl', 'rb'))
    for lg, y in (('ACB', 2023), ('TBL', 2025)):
        pr, gn = res[lg]; x = R[(R.lg == lg) & (R.y == y)]
        new = pr[x.i.values]; old = x.pf.values; a = x.act.values; e = gn[x.i.values] <= 10
        r = lambda v, m: np.sqrt(np.mean((a - v)[m] ** 2))
        print(f'{lg} {y}: αγων 1-10 {r(old, e):.3f} → {r(new, e):.3f} · ολα {r(old, e | ~e):.3f} → {r(new, e | ~e):.3f} · κλεισιμο ολα {np.sqrt(np.mean((a - x.mc.values) ** 2)):.3f}')
