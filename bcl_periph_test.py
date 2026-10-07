# -*- coding: utf-8 -*-
"""bcl_periph_test.py — BCL: ΠΩΣ ΝΑ ΜΕΤΡΑΝΕ ΤΑ «ΠΕΡΙΦΕΡΕΙΑΚΑ» ΠΡΩΤΑΘΛΗΜΑΤΑ (7/10/2026, Στελιος «αντι να τις αφαιρεσουμε, backtests για το πως θα
υπολογιζονταν καλυτερα»). Περιφερειακα = τα πρωταθληματα του fs_bk_extra (λιγες ευρωπαϊκες συνδεσεις): Πολωνια, Ρουμανια, Αγγλια, BNXT,
Λετονια-Εσθονια, Ουκρανια, Τσεχια, Φινλανδια.
ΔΟΚΙΜΕΣ (κοινη κλιμακα, live ρυθμιση 1.3 / λ 1.5 / φιλικα .5 / αλλα εγχωρια ×1.5):
  βαρος περιφερειακων w {0.25, 0.5, 1, 1.5} × ψαλιδι νικων c {10, 15, 25} × νεες ομαδες απο τον μεσο της λιγκας τους {οχι, ναι}
  + «χωρις Τσεχια/Φινλανδια» + σημερινο live (w 1.5, c 25, οχι). Συνολα: βαρος περιφερειακων {0.25, 0.5, 1, 1.5}.
ΑΞΙΟΛΟΓΗΣΗ: ματς BCL 2021-26 με ομαδα περιφερειακου πρωταθληματος (ιδια ή προηγουμενη σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): ρυθμιση LOSO (λαθος στα ματς-στοχος των αλλων 4 σεζον)· ΜΠΑΙΝΕΙ αν καλυτερη απο το σημερινο live σε ≥4/5
  σεζον ΚΑΙ τα υπολοιπα ματς δεν χειροτερευουν > 0.01 π. Εξοδος: bcl_periph_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, pickle, itertools, collections
import numpy as np
from multiprocessing import Pool
EXT = {'PLK', 'ROM', 'GBR', 'BNX', 'LEL', 'UKR', 'CZE', 'FIN'}
CF = {'CZE', 'FIN'}   # γυρος 2: ρυθμισεις ΜΟΝΟ για Τσεχια/Φινλανδια (τα αλλα περιφερειακα ως εχουν)

def _job(cfg):
    import bcl_common as B
    rows = B.load(pre=True)
    kind = cfg[0]
    if cfg[1] == 'noCF': rows = [r for r in rows if r[1] not in ('CZE', 'FIN')]
    if kind == 'h':
        if cfg[1] in ('live', 'noCF'): return cfg, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5)
        if cfg[1] == 'CF':
            _, _, w, c, lp = cfg
            return cfg, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, ext=CF, ext_w=w, ext_clip=c, lgprior=lp)
        _, w, c, lp = cfg
        return cfg, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, ext=EXT, ext_w=w, ext_clip=c, lgprior=lp)
    tm = B.luck_totals(.1)
    if cfg[1] in ('live', 'noCF'): return cfg, B.run_tot(rows, .35, 20.0, kf=1.0, wo=1.0, tmap=tm)
    return cfg, B.run_tot(rows, .35, 20.0, kf=1.0, wo=1.0, tmap=tm, ext=EXT, ext_w=cfg[1])

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    cfgs = [('h', 'live'), ('h', 'noCF')] + [('h', w, c, lp) for w in (.25, .5, 1.0, 1.5) for c in (10.0, 15.0, 25.0) for lp in (False, True)]         + [('h', 'CF', w, c, lp) for w in (.05, .1, .25, .5) for c in (5.0, 10.0, 15.0) for lp in (False, True)] \
        + [('t', 'live'), ('t', 'noCF')] + [('t', w) for w in (.25, .5, 1.5)]
    with Pool(20) as pool: R = dict(pool.map(_job, cfgs))
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    import bcl_common as B
    rows = B.load(pre=False)
    # Μ1 (μονο BCL) απο την παλια live προβλεψη (χωρις CZE/FIN): Μ1 = (FIN − .75·Μ2_noCF)/.25 — ιδιο σε ολες τις εκδοχες
    M1 = (D['FIN'] - .75 * arr(R[('h', 'noCF')])) / .25
    H = {k: .25 * M1 + .75 * arr(v) for k, v in R.items() if k[0] == 'h'}
    T = {k: arr(v) for k, v in R.items() if k[0] == 't'}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    tot = np.array([(int(E[i]['hs']) + int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    by_y = collections.defaultdict(list)
    for r in rows: by_y[r[0]].append(r)
    MC = {y: B._main_comp(v) for y, v in by_y.items()}
    sub = np.zeros(len(ids), bool); lgs = collections.Counter()
    for k, i in enumerate(ids):
        if i not in E: continue
        y = int(ys[k])
        for t in (B.ALIAS.get(E[i]['hid'], E[i]['hid']), B.ALIAS.get(E[i]['aid'], E[i]['aid'])):
            lg = MC.get(y, {}).get(t) or MC.get(y - 1, {}).get(t)
            if lg in EXT: sub[k] = True; lgs[lg] += 1
    EV = [2021, 2022, 2023, 2024, 2025]
    ev = np.isin(ys, EV)
    P(f'ματς-στοχος (BCL 2021-26 με ομαδα περιφερειακου πρωταθληματος): {int((sub & ev).sum())} · ' + ' · '.join(f'{k} {v}' for k, v in lgs.most_common()))
    def rm(v, tgt, m): m = m & np.isfinite(v) & np.isfinite(tgt); return float(np.sqrt(np.mean((tgt - v)[m] ** 2)))
    for nm, V, tgt, base in (('ΧΑΝΤΙΚΑΠ', H, act, ('h', 'live')), ('ΣΥΝΟΛΑ', T, tot, ('t', 'live'))):
        P(''); P(f'################ {nm} ################')
        P(f'  σημερινο live {base}: στοχος {rm(V[base], tgt, sub & ev):.3f} · υπολοιπα {rm(V[base], tgt, ~sub & ev):.3f}')
        k0 = (base[0], 'noCF'); P(f'  χωρις Τσεχια/Φινλανδια: στοχος {rm(V[k0], tgt, sub & ev):.3f} · υπολοιπα {rm(V[k0], tgt, ~sub & ev):.3f}')
        P('  in-sample (καλυτερες 8 στα ματς-στοχος):')
        for k in sorted(V, key=lambda k: rm(V[k], tgt, sub & ev))[:8]:
            P(f'    {k}: στοχος {rm(V[k], tgt, sub & ev):.3f} · υπολοιπα {rm(V[k], tgt, ~sub & ev):.3f}')
        held = np.full(len(ids), np.nan); ch = {}
        for Y in EV:
            tr = sub & np.isin(ys, [x for x in EV if x != Y])
            k = min(V, key=lambda k: rm(V[k], tgt, tr)); ch[Y] = k; m = ys == Y; held[m] = V[k][m]
        d = [rm(held, tgt, sub & (ys == Y)) - rm(V[base], tgt, sub & (ys == Y)) for Y in EV]
        drest = rm(held, tgt, ~sub & ev) - rm(V[base], tgt, ~sub & ev)
        ok = sum(x < 0 for x in d) >= 4 and drest <= .01
        P('  LOSO επιλογες: ' + ' · '.join(f'{Y}: {ch[Y]}' for Y in EV))
        P(f'  LOSO στοχος {rm(V[base], tgt, sub & ev):.3f} → {rm(held, tgt, sub & ev):.3f} · ανα σεζον ' + ' '.join(f'{x:+.2f}' for x in d)
          + f' → {sum(x < 0 for x in d)}/5 · υπολοιπα {drest:+.3f}' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
        best = collections.Counter(ch.values()).most_common(1)[0][0]
        P(f'  πιο συχνη επιλογη: {best}')
    pickle.dump(dict(H={str(k): v for k, v in H.items()}, T={str(k): v for k, v in T.items()}, sub=sub, ids=ids, ys=ys), open('bcl_periph_preds.pkl', 'wb'))
    open('bcl_periph_test2_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
