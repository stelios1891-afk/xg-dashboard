# -*- coding: utf-8 -*-
"""bcl_totals_test.py — BCL ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ (6/10/2026, Στελιος «ναι ξεκινα» — συνολα BCL δεν ειχαν μοντελο).
Δυο μηχανες συνολου (ιδια λογικη με το χαντικαπ):
  Τ1 ΜΟΝΟ BCL (dom_bk_totals_test: κατοχες × (επιθ.+αμυνα)/100): τυχη {ωμο, .5, .25} × περσι {.35, .7, 1, 1.4} × επιπεδο λιγκας μ_w {5, 50} → + ρυθμος ανα ομαδα λp {20, 8}
  Τ2 ΚΟΙΝΗ ΚΛΙΜΑΚΑ ΣΥΝΟΛΩΝ (bcl_common.run_tot): συνολο = μ_διοργανωσης + s_γηπ + s_φιλ απο ΟΛΑ τα ματς·
     περσι {.5, .8, 1} × λ {2.5, 5, 10} × βαρος εγχωριων wo {1, 1.5} × φιλικα kf {0, .5}
  ΜΙΞΗ b·Τ2 + (1−b)·Τ1, b {0, .25, .5, .75, 1} · ΚΑΜΠΥΛΗ σεζον (υπολοιπο ~ a + b·αριθμος ματς BCL της ομαδας).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση):
  επιλογες ΜΟΝΟ LOSO 2021-25 (RMSE συνολου ολων των ματς BCL)· καθε βημα (ρυθμος, κοινη κλιμακα, καμπυλη) ΜΠΑΙΝΕΙ αν καλυτερο σε ≥4/5.
  ΑΓΟΡΑ (Nowgoal t23, Crown + Bet365): Κ2 vs κλεισιμο b ≥ .15, t ≥ 2, θετικο ≥4/5 · ROI over/under: μοντελο ≥8% / μιξη 50/50 ≥6%, ανοιγμα & κλεισιμο.
  Προταση για LIVE picks μονο αν Κ2 ✓ ΚΑΙ ROI ανοιγματος > 0 ΚΑΙ στα δυο βιβλια (ο κανονας που περασε).
Εξοδος: bcl_totals_test_out.txt · bcl_totals_preds.pkl"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, json, math, pickle, itertools, collections, contextlib
import numpy as np, pandas as pd
from multiprocessing import Pool
from statistics import NormalDist

def _t2(cfg):
    import bcl_common as B
    return cfg, B.run_tot(B.load(pre=True), cfg[0], cfg[1], kf=cfg[3], wo=cfg[2])

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    src = open('dom_bk_totals_test.py', encoding='utf-8').read()
    src = src.split("BASE = {'ACB': (.7, 8, 9999, .5, -8)")[0].replace("ARGS = ['ACB', 'LBA']", "ARGS = ['BCL']").replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
    NS = {'__name__': 'tt'}
    argv0 = list(sys.argv)
    with contextlib.redirect_stdout(io.StringIO()): exec(src, NS)
    sys.argv = argv0
    G, runT, EV = NS['G'], NS['runT'], [2021, 2022, 2023, 2024, 2025]
    NS['EFF'][.1] = NS['NS']['effs'](.1)          # τυχη .1 (επεκταση)
    BI = np.where(G.lg.values == 'BCL')[0]
    ids, ys = G.id.values[BI], G.y.values[BI]; TOT = (G.hs + G.as_).values.astype(float)[BI]; HID = G.hid.values[BI]; TT = G.t.values[BI]
    gno = np.zeros(len(BI), int); cnt = collections.Counter()
    for i in np.argsort(TT): cnt[(ys[i], HID[i])] += 1; gno[i] = cnt[(ys[i], HID[i])]
    def rm(v, yy, m=None):
        k = np.isin(ys, yy) & np.isfinite(v) & (m if m is not None else True); return float(np.sqrt(np.mean((TOT - v)[k] ** 2)))
    def nested(D_):
        held = np.full(len(BI), np.nan); ch = {}
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(D_, key=lambda k: rm(D_[k], tr)); ch[Y] = k; held[ys == Y] = D_[k][ys == Y]
        return held, ch
    def verdict(new, old, lab):
        d = [rm(new, [Y]) - rm(old, [Y]) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
        P(f'  {lab}: {rm(old, EV):.3f} → {rm(new, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
        return ok
    P(f'BCL ματς: {len(BI)} · μεσο συνολο ανα σεζον: ' + ' '.join(f'{y}: {TOT[ys == y].mean():.1f}' for y in sorted(set(ys))))
    # ---- Τ1 ----
    T1 = {}
    for luck in (None, .5, .25, .1):          # 6/10 επεκταση: τυχη .25 & περσι .35 βγηκαν στο ακρο
        for car in (.1, .2, .35, .7, 1.0, 1.4):
            for muw in (5.0, 50.0):
                T1[(luck, car, muw, None)] = runT('BCL', car, 8, 9999, luck, muw, None, 0)[0][BI]
    P(''); P('################ Τ1 ΜΟΝΟ BCL ################')
    P('  in-sample (καλυτερες 6): ' + ' · '.join(f'{k[:3]}: {rm(v, EV):.3f}' for k, v in sorted(T1.items(), key=lambda kv: rm(kv[1], EV))[:6]))
    H1, c1 = nested(T1)
    P('  LOSO επιλογες: ' + ' · '.join(f'{Y}: {c1[Y][:3]}' for Y in EV) + f' · {rm(H1, EV):.3f}')
    best1 = collections.Counter(c1.values()).most_common(1)[0][0]
    T1p = dict(T1)
    for lp in (20, 8, 3):
        T1p[best1[:3] + (lp,)] = runT('BCL', best1[1], 8, 9999, best1[0], best1[2], lp, 0)[0][BI]
    H1p, c1p = nested({k: v for k, v in T1p.items() if k[:3] == best1[:3]})
    okp = verdict(H1p, T1[best1], 'ρυθμος ανα ομαδα (πανω στη βαση Τ1)')
    T1use = {k: v for k, v in T1p.items() if (k[3] is not None) == okp} if okp else T1
    # ---- Τ2 ----
    P(''); P('################ Τ2 ΚΟΙΝΗ ΚΛΙΜΑΚΑ ΣΥΝΟΛΩΝ ################')
    cache = 'bcl_tot_cache.pkl'
    C2 = pickle.load(open(cache, 'rb')) if os.path.exists(cache) else {}
    cfgs = [c for c in list(itertools.product((.5, .8, 1.0), (2.5, 5.0, 10.0), (1.0, 1.5), (0.0, .5))) + list(itertools.product((.2, .35, .5), (10.0, 20.0, 40.0), (.75, 1.0), (.5, 1.0))) if c not in C2]   # 6/10 επεκταση: περσι .5 & λ 10 στο ακρο
    if cfgs:
        with Pool(20) as pool:
            for cfg, pr in pool.imap_unordered(_t2, cfgs):
                C2[cfg] = pr; pickle.dump(C2, open(cache, 'wb'))
    pos = {i: k for k, i in enumerate(ids)}
    T2 = {}
    for cfg, pr in C2.items():
        v = np.full(len(BI), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        T2[cfg] = v
    P('  in-sample (καλυτερες 8): ' + ' · '.join(f'{k}: {rm(v, EV):.3f}' for k, v in sorted(T2.items(), key=lambda kv: rm(kv[1], EV))[:8]))
    for nm, f in (('εγχωρια ×1', lambda k: k[2] == 1.0), ('εγχωρια ×1.5', lambda k: k[2] == 1.5), ('χωρις φιλικα', lambda k: k[3] == 0), ('με φιλικα', lambda k: k[3] > 0)):
        b_ = min((k for k in T2 if f(k)), key=lambda k: rm(T2[k], EV)); P(f'    {nm}: καλυτερη {b_} {rm(T2[b_], EV):.3f}')
    # ---- ΜΙΞΗ ----
    top1 = sorted(T1use, key=lambda k: rm(T1use[k], EV))[:6]
    BL = {}
    for k1 in top1:
        for k2 in T2:
            for bb in (0, .25, .5, .75, 1.0):
                if bb == 0 and k2 != next(iter(T2)): continue
                BL[(k1, k2, bb)] = (1 - bb) * T1use[k1] + bb * np.where(np.isfinite(T2[k2]), T2[k2], T1use[k1])
    HB, cb = nested(BL)
    P(''); P('################ ΜΙΞΗ Τ1/Τ2 (LOSO) ################')
    for Y in EV: P(f'  {Y}: Τ1 {cb[Y][0]} | Τ2 {cb[Y][1]} | b {cb[Y][2]}')
    H1b, _ = nested({k: v for k, v in T1use.items()})
    okB = verdict(HB, H1b, 'κοινη κλιμακα συνολων (μιξη vs μονο Τ1)')
    FIN = HB if okB else H1b
    kbest = min(BL, key=lambda k: rm(BL[k], EV)); P(f'  ΕΠΙΛΟΓΗ ΓΙΑ LIVE (ολες οι σεζον): Τ1 {kbest[0]} | Τ2 {kbest[1]} | b {kbest[2]} · {rm(BL[kbest], EV):.3f}')
    # ---- ΚΑΜΠΥΛΗ ----
    P(''); P('################ ΚΑΜΠΥΛΗ ΣΕΖΟΝ ################')
    P('  υπολοιπο (πραγμ − μοντ) ανα ματς BCL της ομαδας γηπ.: ' + ' · '.join(f'{a}-{b}: {np.nanmean((TOT - FIN)[(gno >= a) & (gno <= b) & np.isin(ys, EV)]):+.2f}' for a, b in ((1, 2), (3, 4), (5, 6), (7, 10), (11, 20))))
    CUR = FIN.copy(); coef = {}
    for Y in EV:
        tr = np.isin(ys, [x for x in EV if x != Y]) & np.isfinite(FIN); te = ys == Y
        c_ = np.polyfit(np.minimum(gno[tr], 14), (TOT - FIN)[tr], 1); coef[Y] = c_; CUR[te] = FIN[te] + np.polyval(c_, np.minimum(gno[te], 14))
    P('  συντελεστες (κλιση, σταθερα) ανα σεζον: ' + ' · '.join(f'{Y}: ({c[0]:+.2f}, {c[1]:+.2f})' for Y, c in coef.items()))
    okC = verdict(CUR, FIN, 'καμπυλη')
    if okC: FIN = CUR
    pickle.dump(dict(id=ids, y=ys, tot=TOT, gno=gno, FIN=FIN, kbest=kbest, okB=okB, okC=okC, coef=coef, okp=okp), open('bcl_totals_preds.pkl', 'wb'))
    # ---- ΑΓΟΡΑ ----
    P(''); P('################ ΑΓΟΡΑ (Nowgoal συνολα) ################')
    NN = NormalDist(); Phi = NN.cdf
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    sc = {e['id']: (int(e['hs']), int(e['as_'])) for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    idx = collections.defaultdict(list)
    for i, mid in enumerate(ids):
        if mid in sc: idx[sc[mid]].append(i)
    ROWS = collections.defaultdict(dict)
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    MK = {}
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
            for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
                for i in idx.get(key, []):
                    if abs((pd.Timestamp(TT[i]) - tip).total_seconds()) <= 26 * 3600: hit = i; break
                if hit is not None: break
            if hit is None: continue
            rec = {c: dict(o=(float(R[0][1]), 1 + R[0][2], 1 + R[0][3]), c=(float(R[-1][1]), 1 + R[-1][2], 1 + R[-1][3])) for c, R in ROWS[g['ngid']].items() if R}
            if rec: MK[hit] = rec
    ii = [i for i in MK if ys[i] in EV and np.isfinite(FIN[i]) and 3 in MK[i]]
    SIG = float(np.std([TOT[i] - MK[i][3]['c'][0] for i in ii]))
    def mexp(T, oo, ou):
        po = (1 / oo) / (1 / oo + 1 / ou); return T + SIG * NN.inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
    mo = {i: mexp(*MK[i][3]['o']) for i in ii}; mc = {i: mexp(*MK[i][3]['c']) for i in ii}
    a = np.array([TOT[i] for i in ii]); m = np.array([FIN[i] for i in ii]); yy = np.array([ys[i] for i in ii])
    P(f'  ματς {len(ii)} · σ (πραγμ − κλεισιμο) {SIG:.1f} · λαθος μοντελο {np.sqrt(np.mean((a - m) ** 2)):.2f} · ανοιγμα {np.sqrt(np.mean((a - np.array([mo[i] for i in ii])) ** 2)):.2f} · '
      f'κλεισιμο {np.sqrt(np.mean((a - np.array([mc[i] for i in ii])) ** 2)):.2f} · μεση διαφορα μοντ. − κλεισ. {np.mean(m - np.array([mc[i] for i in ii])):+.2f}')
    def k2(sel, ref):
        x = np.array([FIN[i] - ref[i] for i in sel]); z = np.array([TOT[i] - ref[i] for i in sel])
        c = np.polyfit(x, z, 1); r_ = z - np.polyval(c, x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return c[0], c[0] / se
    for ref, lab in ((mc, 'κλεισιμο'), (mo, 'ανοιγμα')):
        b, t = k2(ii, ref); per = [k2([i for i in ii if ys[i] == Y], ref)[0] for Y in EV]
        ok = b >= .15 and t >= 2 and sum(q > 0 for q in per) >= 4
        P(f'  Κ2 vs {lab}: b {b:+.2f} (t {t:+.1f}) · ανα σεζον ' + ' '.join(f'{q:+.2f}' for q in per) + (('  ✓' if ok else '  ✗') if lab == 'κλεισιμο' else ''))
    for lab, f in (('ματς 1-3', lambda i: gno[i] <= 3), ('ματς 4+', lambda i: gno[i] > 3)):
        s = [i for i in ii if f(i)]; b, t = k2(s, mc)
        P(f'    {lab}: n {len(s)} · Κ2 vs κλεισιμο b {b:+.2f} (t {t:+.1f}) · υπολοιπο αγορας (πραγμ − κλεισ.) {np.mean([TOT[i] - mc[i] for i in s]):+.2f}')
    P('  ΤΥΦΛΑ (χωρις μοντελο — μονο η ταση της αγορας):')
    for bk, bn in ((3, 'Crown'), (8, 'Bet365')):
        for wh, wn in (('o', 'ανοιγμα'), ('c', 'κλεισιμο')):
            R = [(((MK[i][bk][wh][2] - 1) if TOT[i] < MK[i][bk][wh][0] else (0 if TOT[i] == MK[i][bk][wh][0] else -1)), int(ys[i])) for i in ii if bk in MK[i]]
            u = np.array([r[0] for r in R]); pos_ = sum(1 for Y in EV if np.mean([r[0] for r in R if r[1] == Y]) > 0)
            P(f'    τυφλο UNDER {bn} {wn}: {u.mean() * 100:+.1f}% ({len(u)}, {pos_}/5) · πραγμ − γραμμη {np.mean([TOT[i] - MK[i][bk][wh][0] for i in ii if bk in MK[i]]):+.2f}')
    def cov(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = Phi((mu - T - .5) / SIG); pu = Phi((T - mu - .5) / SIG); return po, 1 - po - pu, pu
        po = Phi((mu - T) / SIG); return po, 0.0, 1 - po
    def bets(sel, book, wh, wm, thr):
        R = []
        for i in sel:
            if book not in MK[i]: continue
            T, oo, ou = MK[i][book][wh]; mk_ = mexp(T, oo, ou); mu = mk_ + wm * (FIN[i] - mk_)
            po, pq, pu = cov(mu, T); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
            if max(eo, eu) < thr: continue
            ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
            R.append(((od - 1) if q > 0 else (0 if q == 0 else -1), int(ys[i]), 'over' if ov else 'under'))
        return R
    def cell(R):
        if not R: return '—'
        u = np.array([q[0] for q in R]); pos_ = sum(1 for Y in EV if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
        return f'{u.mean() * 100:+.1f}% ({len(R)}, {u.sum():+.1f}u, {pos_}/5)'
    for rl, wm, thr in (('μοντελο ≥8%', 1.0, .08), ('μιξη 50/50 ≥6%', .5, .06)):
        P(f'  [{rl}]')
        for book, bn in ((3, 'Crown'), (8, 'Bet365')):
            for wh, wn in (('o', 'ανοιγμα'), ('c', 'κλεισιμο')):
                R = bets(ii, book, wh, wm, thr)
                P(f'    {bn} {wn:9s}: ολα {cell(R)} · over {cell([q for q in R if q[2] == "over"])} · under {cell([q for q in R if q[2] == "under"])}')
        for lab, f in (('ματς 1-3', lambda i: gno[i] <= 3), ('ματς 4+', lambda i: gno[i] > 3)):
            s = [i for i in ii if f(i)]
            P(f'    {lab} (ανοιγμα): Crown {cell(bets(s, 3, "o", wm, thr))} · Bet365 {cell(bets(s, 8, "o", wm, thr))}')
    open('bcl_totals_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
