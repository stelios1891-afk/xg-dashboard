# -*- coding: utf-8 -*-
"""bcl_experts2024_check.py — BCL 2024-25 (η μονη σεζον με γνωμη ειδικων: επισημα power rankings) — η live φορμουλα ΜΕ vs ΧΩΡΙΣ ειδικους
(κx · z στην αφετηρια, οπως φετος με τις αποδοσεις νικητη)· picks χαντικαπ ≥8% ανα ζωνη (8/10/2026, Στελιος «τρεξτο ναι»). Μια σεζον = μονο κατευθυνση."""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections, math
import numpy as np
from statistics import NormalDist
from multiprocessing import Pool
Phi = NormalDist().cdf
def _job(kx):
    import bcl_common as B
    z = json.load(open('bcl_expert_z.json', encoding='utf-8'))
    adj = {2024: {t: kx * v for t, v in z['2024'].items()}} if kx else None
    return kx, B.run(B.load(pre=True), 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, prior_adj=adj)
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    with Pool(4) as p: R = dict(p.map(_job, [0, 2.0, 4.5, 7.0]))
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
    ids, ys = D['id'], D['y']; pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (pp, y) in pr.items():
            if mid in pos: v[pos[mid]] = pp
        return v
    A0 = arr(R[0]); M1 = (D['FIN'] - .75 * A0) / .25
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    cnt = collections.Counter(); GN = {}
    for e in sorted([x for x in FG['BCL_2024'] if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        cnt[e['hid']] += 1; cnt[e['aid']] += 1; GN[e['id']] = max(cnt[e['hid']], cnt[e['aid']])
    def cover(m_, L, s=12.0):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    print('BCL 2024-25 · live φορμουλα · κx = ποντοι ανα z ειδικων (φετος με αποδοσεις: 4.5)')
    for kx, pr in R.items():
        v = .25 * M1 + .75 * arr(pr); res = collections.defaultdict(list); err = collections.defaultdict(list)
        for k, i in enumerate(ids):
            if int(ys[k]) != 2024 or i not in E or not np.isfinite(v[k]): continue
            act = int(E[i]['hs']) - int(E[i]['as_']); z = '1-3' if GN.get(i, 9) <= 3 else '4+'
            err[z].append((act - v[k]) ** 2)
            if i not in MK: continue
            us = []
            for b in (3, 8):
                o = MK[i].get(b, {}).get('o')
                if not o: continue
                L, mu, o1, o2 = o; pw, pp, pl = cover(v[k], L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e >= .08: x = (act + L) * side; us.append((od - 1) if x > 0 else (0 if x == 0 else -1))
            if us: res[z].append(np.mean(us))
        print(f'  κx {kx:<4g} · ' + ' · '.join(f"αγων {z}: λαθος {math.sqrt(np.mean(err[z])):.2f} · picks {len(res[z])} · {sum(res[z]):+.1f}μ ({np.mean(res[z])*100 if res[z] else 0:+.1f}%)" for z in ('1-3', '4+')))
