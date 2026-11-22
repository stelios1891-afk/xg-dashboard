# -*- coding: utf-8 -*-
"""bcl_bigedge_2024.py — BCL 2024-25 (η μονη σεζον με γνωμη ειδικων = ισοδυναμο των φετινων αποδοσεων νικητη, κx 4.5): picks χαντικαπ ≥8%
ανα ΜΕΓΕΘΟΣ διαφωνιας μοντελου−αγορας × αγων 1-3 / 4+, ΜΕ (κx 4.5) και ΧΩΡΙΣ (κx 0) ειδικους· ανοιγμα & κλεισιμο, μεσος Crown/Bet365
(13/10/2026, Στελιος «ο πινακας ειναι τη χρονια που σου ανεφερα;»). Μια σεζον = μονο κατευθυνση (κx 4.5 διαλεχτηκε σε αυτη). Εξοδος: bcl_bigedge_2024_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np
from statistics import NormalDist
from multiprocessing import Pool
Phi = NormalDist().cdf
def _job(kx):
    import bcl_common as B
    z = json.load(open('bcl_expert_z.json', encoding='utf-8'))
    adj = {2024: {t: kx * v for t, v in z['2024'].items()}} if kx else None
    return kx, B.run(B.load(pre=True), 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, prior_adj=adj)
BANDS = [(0, 4, '<4 π.'), (4, 7, '4-7 π.'), (7, 10, '7-10 π.'), (10, 99, '≥10 π.')]
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    with Pool(2) as p: R = dict(p.map(_job, [0, 4.5]))
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
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    P('BCL 2024-25 ΜΟΝΟ · live φορμουλα · picks χαντικαπ ≥8% στο ανοιγμα · μεσος Crown/Bet365 · ROI (picks)')
    for kx in (4.5, 0):
        v = .25 * M1 + .75 * arr(R[kx]); res = collections.defaultdict(list)
        for k, i in enumerate(ids):
            if int(ys[k]) != 2024 or i not in E or i not in MK or not np.isfinite(v[k]): continue
            act = int(E[i]['hs']) - int(E[i]['as_']); z = '1-3' if GN.get(i, 9) <= 3 else '4+'
            vo = [MK[i].get(b, {}).get('o') for b in (3, 8)]; vo = [x for x in vo if x]
            if not vo: continue
            band = next(lab for lo, hi, lab in BANDS if lo <= abs(v[k] + np.mean([x[0] for x in vo])) < hi)
            uo, uc = [], []
            for b in (3, 8):
                o = MK[i].get(b, {}).get('o')
                if not o: continue
                L, mu, o1, o2 = o; pw, pp, pl = cover(v[k], L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e < .08: continue
                x = (act + L) * side; uo.append((od - 1) if x > 0 else (0 if x == 0 else -1))
                c = MK[i].get(b, {}).get('c')
                if c:
                    oc = c[2] if side == 1 else c[3]; xc = (act + c[0]) * side; uc.append((oc - 1) if xc > 0 else (0 if xc == 0 else -1))
            if uo: res[('o', z, band)].append(np.mean(uo)); res[('o', z, 'ΟΛΑ')].append(np.mean(uo))
            if uc: res[('c', z, band)].append(np.mean(uc)); res[('c', z, 'ΟΛΑ')].append(np.mean(uc))
        c_ = lambda a: f'{np.mean(a)*100:+6.1f}% ({len(a):2d})' if a else f'{"—":>12}'
        P(''); P(f'##### {"ΜΕ ειδικους (κx 4.5 = σαν φετος)" if kx else "ΧΩΡΙΣ ειδικους (κx 0)"} #####')
        for z in ('1-3', '4+'):
            P(f'  αγων {z}:')
            for lab in [b[2] for b in BANDS] + ['ΟΛΑ']:
                P(f'    {lab:8s} ανοιγμα {c_(res[("o", z, lab)])} · κλεισιμο {c_(res[("c", z, lab)])}')
    open('bcl_bigedge_2024_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
