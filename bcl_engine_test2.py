# -*- coding: utf-8 -*-
"""bcl_engine_test2.py — BCL ΜΗΧΑΝΗ γυρος 2 (6/10/2026, Στελιος «ολες οι ρυθμισεις πριν τα συμπερασματα + φιλικα + ειδικοι/αποδοσεις»).
Το v2 (bcl_engine_test.py) διαλεξε Μ2 στο ΑΚΡΟ του πλεγματος (περσι 1.0, λ 2.5) → επεκταση:
  Μ2 κοινη κλιμακα: περσι {1.0, 1.15} × λ {1, 1.5, 2.5} × ψαλιδι {25, 35} × ΦΙΛΙΚΑ kf {0, .25, .5, 1} (HL ∞)
     φιλικα/Super Cups (fs_bk_preseason.json) = ματς με βαρος kf, ουδετερη εδρα.
  Μ1 μονο BCL: v1 πλεγμα + περσι {1.0, 1.2} × λ {2, 3, 4} (HL ∞, τυχη .5).
  ΜΙΞΗ a {0, .25, .5, .75, .9, 1}.
  ΕΙΔΙΚΟΙ/ΑΠΟΔΟΣΕΙΣ (αν υπαρχει bcl_power_rankings.json): μετατοπιση αφετηριας κx·z (z = μεσος Φ⁻¹ θεσης), κx {0, 2, 4, 6} — πανω στη Μ2 που διαλεγεται.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση):
  επιλογη ΜΟΝΟ με LOSO (ρυθμιση απο τις αλλες 4 σεζον, RMSE ολων των ματς BCL 2021-25).
  καθε προσθηκη (φιλικα kf>0, ειδικοι κx>0) ΜΠΑΙΝΕΙ μονο αν το LOSO με αυτη ειναι καλυτερο απο το LOSO χωρις αυτη σε ≥4/5 σεζον.
  αγορα: bcl_market_check.py πανω στις τελικες LOSO προβλεψεις (Κ2 b ≥ .15, t ≥ 2, ≥4/5 · ROI ≥8% Crown ανοιγμα >0 σε ≥4/5 + Bet365 ανοιγμα >0).
Εξοδος: bcl_engine_test2_out.txt · bcl_engine_preds2.pkl (ιδια μορφη με bcl_engine_preds.pkl)"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'   # 6/10: 8 διεργασιες × πολλα νηματα BLAS = 10× πιο αργο
import sys, io, json, math, pickle, itertools, collections
import numpy as np, pandas as pd
from multiprocessing import Pool

def _m2(cfg):
    import bcl_common as B
    rows = B.load(pre=True); return cfg, B.run(rows, *cfg[:4], kf=cfg[4])

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    src = open('dom_bk_engine_test.py', encoding='utf-8').read().split("LIVE = (.7, 8, 9999, .5, False)")[0]
    src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1).replace("ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']", "ARGS = ['BCL']")
    NS = {'__name__': 'b'}
    exec(src, NS)
    G, run = NS['G'], NS['run']
    act = (G.hs - G.as_).values.astype(float); YS = G.y.values; EV = [2021, 2022, 2023, 2024, 2025]
    bmask = (G.lg.values == 'BCL'); BI = np.where(bmask)[0]
    M1 = {}
    for g in list(itertools.product((.2, .5, .7, 1.0), (4, 8), (60, 9999), (.5, None))) + [(c, l, 9999, .5) for c in (1.0, 1.2) for l in (2, 3, 4)] + [(1.4, l, 9999, .5) for l in (3, 4, 6, 8)] + [(1.2, 6, 9999, .5)]:
        if g not in M1: M1[g] = run('BCL', g[0], g[1], g[2], g[3], False)[0][BI]
    P(f'Μ1: {len(M1)} εκδοχες')
    cache = 'bcl_m2_cache2.pkl'
    M2raw = pickle.load(open(cache, 'rb')) if os.path.exists(cache) else {}
    for cfg, pr in pickle.load(open('bcl_m2_cache.pkl', 'rb')).items():    # v2 (χωρις φιλικα)
        M2raw.setdefault(tuple(cfg) + (0.0,), pr)
    cfgs = [c for c in list(itertools.product((1.0, 1.15), (1.0, 1.5, 2.5), (9999.0,), (25.0, 35.0), (0.0, .25, .5, 1.0))) + list(itertools.product((1.3, 1.5), (1.5, 2.5, 4.0), (9999.0,), (25.0, 35.0), (0.0, .5))) if c not in M2raw]   # 2η επεκταση: περσι 1.15 στο ακρο
    if cfgs:
        with Pool(20) as pool:
            for cfg, pr in pool.imap_unordered(_m2, cfgs):
                M2raw[cfg] = pr; pickle.dump(M2raw, open(cache, 'wb')); print('  Μ2', cfg, flush=True)
    idpos = {i: k for k, i in enumerate(G.id.values[BI])}
    M2 = {}
    for cfg, pr in M2raw.items():
        v = np.full(len(BI), np.nan)
        for mid, (p, y) in pr.items():
            if mid in idpos: v[idpos[mid]] = p
        M2[cfg] = v
    P(f'Μ2: {len(M2)} εκδοχες')
    a_ = act[BI]; ys = YS[BI]
    def rm(v, yy):
        m = np.isin(ys, yy) & np.isfinite(v); return float(np.sqrt(np.mean((a_ - v)[m] ** 2)))
    P('  in-sample Μ2 (καλυτερες 12): ' + ' · '.join(f'{k}: {rm(v, EV):.3f}' for k, v in sorted(M2.items(), key=lambda kv: rm(kv[1], EV))[:12]))
    for kf in (0.0, .25, .5, 1.0):
        best = min((k for k in M2 if k[4] == kf), key=lambda k: rm(M2[k], EV)); P(f'  φιλικα kf {kf}: καλυτερη {best[:4]} {rm(M2[best], EV):.3f}')
    def blends(m2keys):
        BL = {}
        for k1, v1 in M1.items():
            for k2 in m2keys:
                v2 = np.where(np.isfinite(M2[k2]), M2[k2], v1)
                for a in (0, .25, .5, .75, .9, 1.0):
                    if a == 0 and k2 != m2keys[0]: continue
                    BL[(k1, k2, a)] = (1 - a) * v1 + a * v2
        return BL
    def nested(D_):
        held = np.full(len(BI), np.nan); ch = {}
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(D_, key=lambda k: rm(D_[k], tr)); ch[Y] = k; held[ys == Y] = D_[k][ys == Y]
        return held, ch
    H1, c1 = nested(M1)
    for lab, BLx in (('χωρις φιλικα', blends([k for k in M2 if k[4] == 0])), ('με φιλικα', blends([k for k in M2 if k[4] > 0]))):
        kb = min(BLx, key=lambda k: rm(BLx[k], EV)); P(f'  ΕΠΙΛΟΓΗ ΓΙΑ LIVE ({lab}, ολες οι 5 σεζον): Μ1 {kb[0]} | Μ2 {kb[1]} | a {kb[2]} · {rm(BLx[kb], EV):.3f}')
    H0, c0 = nested(blends([k for k in M2 if k[4] == 0]))
    HF, cf = nested(blends(list(M2)))
    P(''); P('################ LOSO ################')
    for Y in EV: P(f'  {Y}: χωρις φιλικα {c0[Y][0]} | {c0[Y][1]} | a {c0[Y][2]}   ·   με φιλικα {cf[Y][0]} | {cf[Y][1]} | a {cf[Y][2]}')
    P(f'  Μ1 μονη {rm(H1, EV):.3f} · μιξη χωρις φιλικα {rm(H0, EV):.3f} · με φιλικα (αν διαλεχτουν) {rm(HF, EV):.3f}')
    d = [rm(HF, [Y]) - rm(H0, [Y]) for Y in EV]; okF = sum(x < 0 for x in d) >= 4
    P(f'  φιλικα: ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΟΥΝ' if okF else '  <- ✗'))
    FIN, cfin = (HF, cf) if okF else (H0, c0)
    # ---- ειδικοι ----
    if os.path.exists('bcl_power_rankings.json'):
        P(''); P('(ειδικοι: βλ. bcl_expert_test.py — τρεχει πανω στις επιλογες αυτου του τεστ)')
    pickle.dump(dict(id=G.id.values[BI], y=ys, home=G.home.values[BI], away=G.away.values[BI], hid=G.hid.values[BI], aid=G.aid.values[BI], t=G.t.values[BI], act=a_,
                     H1=H1, HB=FIN, FIN=FIN, H0=H0, HF=HF, c1=c1, cb=cfin, c0=c0, cf=cf, ok=True, okF=okF), open('bcl_engine_preds2.pkl', 'wb'))
    for Y in EV: P(f'  {Y}: λαθος τελικη {rm(FIN, [Y]):.3f} (v2 χωρις επεκταση: βλ. bcl_engine_test_out.txt)')
    open('bcl_engine_test2_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
