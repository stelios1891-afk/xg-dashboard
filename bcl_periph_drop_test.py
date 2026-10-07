# -*- coding: utf-8 -*-
"""bcl_periph_drop_test.py — BCL: ποια ΑΛΛΑ «μικρα» πρωταθληματα βλαπτουν οπως Τσεχια/Φινλανδια; (7/10/2026, Στελιος «βγαλ' τες, οσες ειναι σαν αυτες»)
Βαση = live κοινη κλιμακα ΧΩΡΙΣ Τσεχια/Φινλανδια (1.3 / λ 1.5 / φιλικα .5 / εγχωρια ×1.5). Δοκιμη: αφαιρεση ΕΝΟΣ πρωταθληματος καθε φορα
(Πολωνια PLK, Ρουμανια ROM, BNXT, Λετονια-Εσθονια LEL, Ουκρανια UKR, Αγγλια GBR) και ολων μαζι.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): ενα πρωταθλημα ΒΓΑΙΝΕΙ αν, στα ματς BCL ομαδων του (ιδια/προηγουμενη σεζον), το λαθος πεφτει σε ≥4/5 σεζον
(ή σε ολες οσες εχουν ≥5 ματς, ελαχιστο 3) ΚΑΙ τα υπολοιπα ματς δεν χειροτερευουν > 0.01 π. Εξοδος: bcl_periph_drop_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np
from multiprocessing import Pool
LGS = ['PLK', 'ROM', 'BNX', 'LEL', 'UKR', 'GBR']

def _job(drop):
    import bcl_common as B
    rows = [r for r in B.load(pre=True) if r[1] not in drop]
    return tuple(sorted(drop)), B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    jobs = [set()] + [{l} for l in LGS] + [set(LGS)]
    with Pool(len(jobs)) as pool: R = dict(pool.map(_job, jobs))
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    base = arr(R[()])
    M1 = (D['FIN'] - .75 * base) / .25                     # Μ1 (μονο BCL): ιδιο παντου (η βαση ειναι η παλια live χωρις CZE/FIN)
    H = {k: .25 * M1 + .75 * arr(v) for k, v in R.items()}
    import bcl_common as B
    rows = B.load(pre=False); by_y = collections.defaultdict(list)
    for r in rows: by_y[r[0]].append(r)
    MC = {y: B._main_comp(v) for y, v in by_y.items()}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    EV = [2021, 2022, 2023, 2024, 2025]; ev = np.isin(ys, EV)
    def lg_mask(l):
        m = np.zeros(len(ids), bool)
        for k, i in enumerate(ids):
            if i not in E: continue
            y = int(ys[k])
            if any((MC.get(y, {}).get(t) or MC.get(y - 1, {}).get(t)) == l for t in (E[i]['hid'], E[i]['aid'])): m[k] = True
        return m
    def rm(v, m): m = m & np.isfinite(v) & np.isfinite(act); return float(np.sqrt(np.mean((act - v)[m] ** 2))) if m.any() else np.nan
    allm = np.zeros(len(ids), bool)
    P('πρωταθλημα · ματς BCL ομαδων του · λαθος ΜΕ → ΧΩΡΙΣ · ανα σεζον (− = καλυτερα χωρις) · υπολοιπα ματς')
    for l in LGS:
        m = lg_mask(l) & ev; allm |= m; k = (l,)
        per = [(Y, rm(H[k], m & (ys == Y)) - rm(H[()], m & (ys == Y)), int((m & (ys == Y)).sum())) for Y in EV]
        valid = [d for Y, d, n in per if n >= 5]; need = 4 if len(valid) >= 5 else max(3, len(valid))
        better = sum(1 for d in valid if d < 0); drest = rm(H[k], ~m & ev) - rm(H[()], ~m & ev)
        ok = len(valid) >= 3 and better >= need and drest <= .01
        P(f'  {l}: n {int(m.sum()):3d} · {rm(H[()], m):.2f} → {rm(H[k], m):.2f} · ' + ' '.join(f'{Y}:{d:+.2f}({n})' for Y, d, n in per)
          + f' · καλυτερα σε {better}/{len(valid)} · υπολοιπα {drest:+.3f}' + ('  <- ΒΓΑΙΝΕΙ' if ok else '  <- μενει'))
    k = tuple(sorted(LGS))
    P(f'  ΟΛΑ μαζι εκτος: ματς {int(allm.sum())} · {rm(H[()], allm):.2f} → {rm(H[k], allm):.2f} · υπολοιπα {rm(H[k], ~allm & ev) - rm(H[()], ~allm & ev):+.3f}')
    open('bcl_periph_drop_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
