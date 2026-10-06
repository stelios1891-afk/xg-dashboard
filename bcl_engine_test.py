# -*- coding: utf-8 -*-
"""bcl_engine_test.py — BASKETBALL CHAMPIONS LEAGUE: ΜΗΧΑΝΗ «ΑΠΟ ΤΗΝ ΑΡΧΗ» (6/10/2026, Στελιος «BCL σημερα, ματς αποψε»).
Δυο μηχανες, ιδια σεζον-τεστ 2021-22…2025-26 (Flashscore):
  Μ1 ΜΟΝΟ BCL (ιδια με EuroCup/εγχωρια: box Flashscore, κατοχες, τυχη 3P/FT, ridge): περσι {.2,.5,.7,1} × λ {4,8} × HL {60,∞} × τυχη {.5, ωμο}
  Μ2 ΚΟΙΝΗ ΚΛΙΜΑΚΑ (bcl_common): rating απο ΟΛΑ τα ματς (εγχωρια + Ευρωπη), walk-forward: περσι {.5,.8} × λ {5,15} × HL {60,∞}
  ΜΙΞΗ: (1−a)·Μ1 + a·Μ2, a {0,.25,.5,.75,1}
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO (ρυθμιση απο τις ΑΛΛΕΣ 4 σεζον, RMSE ολων των ματς BCL)· η Μ2/μιξη ΜΠΑΙΝΕΙ αν καλυτερη απο τη Μ1 σε ≥4/5.
ΑΓΟΡΑ (Nowgoal Crown/Bet365, αν εχει κατεβει): Κ2 vs κλεισιμο (b ≥ .15, t ≥ 2, ≥4/5) · ROI χαντικαπ (καθαρο): μοντελο ≥8% / μιξη 50/50 ≥6%, ανοιγμα & κλεισιμο.
Εξοδος: bcl_engine_test_out.txt · bcl_engine_preds.pkl"""
import sys, os, io, json, math, pickle, itertools, contextlib, collections
import numpy as np, pandas as pd
from multiprocessing import Pool

def _m2(cfg):
    import bcl_common as B
    rows = B.load(); return cfg, B.run(rows, *cfg)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    src = open('dom_bk_engine_test.py', encoding='utf-8').read().split("LIVE = (.7, 8, 9999, .5, False)")[0]
    src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1).replace("ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']", "ARGS = ['BCL']")
    NS = {'__name__': 'b'}
    exec(src, NS)
    G, run, EFF = NS['G'], NS['run'], NS['EFF']
    act = (G.hs - G.as_).values.astype(float); YS = G.y.values; EV = [2021, 2022, 2023, 2024, 2025]
    bmask = (G.lg.values == 'BCL')
    P(f'BCL ματς: {bmask.sum()} · με box {G.ok.values[bmask].mean():.0%} · ' + ' '.join(f'{y}: {((YS == y) & bmask).sum()}' for y in sorted(set(YS[bmask]))))
    # Μ1
    M1 = {}
    for g in itertools.product((.2, .5, .7, 1.0), (4, 8), (60, 9999), (.5, None)):
        M1[g] = run('BCL', g[0], g[1], g[2], g[3], False)[0]
    P(f'Μ1: {len(M1)} εκδοχες')
    # Μ2
    cache = 'bcl_m2_cache.pkl'
    if os.path.exists(cache): M2raw = pickle.load(open(cache, 'rb'))
    else:
        cfgs = list(itertools.product((.5, .8, 1.0), (2.5, 5.0, 15.0), (60.0, 9999.0), (25.0,)))   # 6/10: επεκταση (επιλογη στο ακρο .8/5)
        with Pool(8) as pool: M2raw = dict(pool.map(_m2, cfgs))
        pickle.dump(M2raw, open(cache, 'wb'))
    idpos = {i: k for k, i in enumerate(G.id.values)}
    M2 = {}
    for cfg, pr in M2raw.items():
        v = np.full(len(G), np.nan)
        for mid, (p, y) in pr.items():
            if mid in idpos: v[idpos[mid]] = p
        M2[cfg] = v
    P(f'Μ2: {len(M2)} εκδοχες · καλυψη {np.isfinite(next(iter(M2.values()))[bmask]).mean():.0%}')
    def rm(v, ys):
        m = bmask & np.isin(YS, ys) & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
    P('  in-sample RMSE 2021-26 — Μ1 καλυτερα: ' + ' · '.join(f'{k}: {rm(v, EV):.3f}' for k, v in sorted(M1.items(), key=lambda kv: rm(kv[1], EV))[:4]))
    P('  in-sample RMSE 2021-26 — Μ2: ' + ' · '.join(f'{k[:3]}: {rm(v, EV):.3f}' for k, v in sorted(M2.items(), key=lambda kv: rm(kv[1], EV))))
    BL = {}
    for k1, v1 in M1.items():
        for k2, v2 in M2.items():
            for a in (0, .25, .5, .75, .9, 1.0):
                if a == 0 and k2 != next(iter(M2)): continue
                BL[(k1, k2, a)] = (1 - a) * v1 + a * np.where(np.isfinite(v2), v2, v1)
    def nested(D_):
        held = np.full(len(G), np.nan); ch = {}
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(D_, key=lambda k: rm(D_[k], tr)); ch[Y] = k; held[YS == Y] = D_[k][YS == Y]
        return held, ch
    H1, c1 = nested(M1); HB, cb = nested(BL)
    d = [rm(HB, [Y]) - rm(H1, [Y]) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
    P(''); P('################ LOSO ################')
    for Y in EV: P(f'  {Y}: Μ1 {c1[Y]} · μιξη {cb[Y][0]} | Μ2 {cb[Y][1][:3]} | a {cb[Y][2]}')
    P(f'  Μ1 μονη {rm(H1, EV):.3f} → με κοινη κλιμακα {rm(HB, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
    FIN = HB if ok else H1
    pickle.dump(dict(id=G.id.values, y=YS, home=G.home.values, away=G.away.values, hid=G.hid.values, aid=G.aid.values, t=G.t.values, act=act, H1=H1, HB=HB, FIN=FIN,
                     M1=M1, M2=M2, c1=c1, cb=cb, ok=ok), open('bcl_engine_preds.pkl', 'wb'))
    # ---------- αγορα ----------
    if not os.path.exists('nowgoal_bcl/odds.jsonl'):
        P('(αποδοσεις Nowgoal BCL δεν εχουν κατεβει ακομα — αγορα στο επομενο τρεξιμο)')
    else:
        from statistics import NormalDist
        nd = NormalDist(); Phi = nd.cdf
        ROWS = collections.defaultdict(dict)
        for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
            r = json.loads(ln)
            if r['t'] == 21: ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
        idx = collections.defaultdict(list)
        for i in np.where(bmask)[0]: idx[(int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
        MK = {}
        for f in sorted(os.listdir('nowgoal_bcl')):
            if not f.startswith('sched_'): continue
            for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
                if g.get('hs') is None or g['ngid'] not in ROWS: continue
                tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
                for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
                    for i in idx.get((a_, b_), []):
                        if abs((pd.Timestamp(G.t.values[i]) - tip).total_seconds()) <= 26 * 3600: hit, sw = i, swp; break
                    if hit is not None: break
                if hit is None: continue
                rec = {}
                for cid in (3, 8):
                    R = ROWS[g['ngid']].get(cid)
                    if not R: continue
                    def cv(x):
                        o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 12.0 * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                        return (-L, -mu, o2, o1) if sw else (L, mu, o1, o2)
                    rec[cid] = dict(o=cv(R[0]), c=cv(R[-1]))
                if rec: MK[hit] = rec
        P(''); P(f'################ ΑΓΟΡΑ (Nowgoal): {len(MK)} ματς · ' + ' '.join(f'{y}: {sum(1 for i in MK if YS[i] == y)}' for y in EV) + ' ################')
        ii = [i for i in MK if YS[i] in EV and 3 in MK[i]]
        SIG = float(np.std([act[i] - MK[i][3]['c'][1] for i in ii])); P(f'  σ (πραγματικο − κλεισιμο) {SIG:.1f}')
        def cover(m_, L, s):
            if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
            pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
        for lab, v in (('Μ1 (μονο BCL)', H1), ('ΤΕΛΙΚΗ' + (' (με κοινη κλιμακα)' if ok else ''), FIN)):
            mc = np.array([MK[i][3]['c'][1] for i in ii]); mo = np.array([MK[i][3]['o'][1] for i in ii]); a = act[ii]; m = v[ii]; ss = YS[ii]
            fin_ = np.isfinite(m); x, z = (m - mc)[fin_], (a - mc)[fin_]
            b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
            per = [np.polyfit(x[ss[fin_] == Y], z[ss[fin_] == Y], 1)[0] for Y in EV if (ss[fin_] == Y).sum() > 20]
            P(f'  [{lab}] λαθος μοντελο {np.sqrt(np.mean((a - m)[fin_] ** 2)):.2f} · ανοιγμα {np.sqrt(np.mean((a - mo) ** 2)):.2f} · κλεισιμο {np.sqrt(np.mean((a - mc) ** 2)):.2f} · '
              f'Κ2 b {b:+.2f} (t {b/se:+.1f}, θετ. {sum(q > 0 for q in per)}/{len(per)})' + (' ✓' if b >= .15 and b / se >= 2 and sum(q > 0 for q in per) >= 4 else ' ✗'))
            for rl, w, thr, sg in (('μοντελο ≥8%', 1.0, .08, SIG), ('μιξη 50/50 ≥6%', .5, .06, SIG + .1)):
                cells = []
                for book, wh in ((3, 'o'), (3, 'c'), (8, 'o')):
                    R = []
                    for i in ii:
                        if book not in MK[i] or not np.isfinite(v[i]): continue
                        L, mk, o1, o2 = MK[i][book][wh]; pw, pp, pl = cover(mk + w * (v[i] - mk), L, sg)
                        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                        if e < thr: continue
                        xx = (act[i] + L) * s_; R.append(((od - 1) if xx > 0 else (0 if xx == 0 else -1), YS[i]))
                    u = np.array([q[0] for q in R]) if R else np.zeros(1); pos = sum(1 for Y in EV if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
                    cells.append(f'{"Crown" if book == 3 else "Bet365"} {"ανοιγμα" if wh == "o" else "κλεισιμο"} {u.mean()*100:+.1f}% ({len(R)}, {u.sum():+.1f}u, {pos}/5)')
                P(f'      {rl:16s} ' + ' · '.join(cells))
    open('bcl_engine_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
