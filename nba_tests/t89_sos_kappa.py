# -*- coding: utf-8 -*-
"""t89_sos_kappa.py — NBA: ΔΥΝΑΜΗ ΔΙΟΡΘΩΣΗΣ ΑΝΤΙΠΑΛΟΥ (SoS) κ (25/10/2026, Στελιος «ναι — σημαντικο να μετρηθει χωρις να ξερουμε το μελλον»).
Προελεγχος (περιγραφικος, με ΜΕΛΛΟΝ): ομαδες με ευκολο προγραμμα πηγαν +0.8 π. πανω απο το μοντελο, με δυσκολο −0.7 (κλιση −0.69, t −4)
→ το μοντελο ισως διορθωνει ΥΠΕΡΒΟΛΙΚΑ για τον αντιπαλο.
ΜΗΧΑΝΗ: ιδια με το live (nba_full_clean_test.run_all). Καθε μερα: κοινη λυση (μ, επιθεση O, αμυνα D) απο ΤΑ ΜΕΧΡΙ ΤΟΤΕ ματς.
  κ: ξαναλυνουμε O με D αντιπαλων σταθερη αλλα πολλαπλασιασμενη ×κ, και D με O αντιπαλων ×κ (ιδιο ridge προς την αφετηρια).
  κ = 1 → ιδιο με live (ελεγχος) · κ = 0 → σκετος μεσος ορος χωρις αντιπαλο. κ ∈ {0.5, 0.75, 1.0, 1.25}.
ΑΓΟΡΕΣ: ΧΑΝΤΙΚΑΠ (CFG_H live · picks πανω στο αντιγραφο live του t22/t84 + Δ μηχανης) και ΣΥΝΟΛΑ (CFG_T live, _t35 + Δ).
ΔΥΣΚΟΛΙΑ ΠΡΟΓΡΑΜΜΑΤΟΣ ΧΩΡΙΣ ΜΕΛΛΟΝ: μεσος ορος της βαθμολογιας (διαφορα) που ειχε ΚΑΘΕ αντιπαλος ΤΗ ΜΕΡΑ του ματς.
ΚΡΙΤΗΡΙΑ (εγκριθηκαν πριν): σφαλμα καλυτερο σε ≥4/5 σεζον ΚΑΙ picks ≥8% (ανοιγμα) μοναδες & CLV οχι χειροτερα
  + στανταρ: walk-forward, ζευγαρωτη t, bootstrap, placebo.
Εξοδος: nba_tests/t89_sos_kappa_out.txt · cache nba_tests/_t89_cache.npz"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import nba_full_clean_test as F
KAP = (0.5, 0.75, 1.0, 1.25)
CFG_H = (0.8, 8, 60, .75, 5.0, 1.0, .75, .25); CFG_T = (0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0)
CACHE = os.path.join(SC, '_t89_cache.npz')

def refit(hi, ai, eh, ea, hb, w, n, O, D, mu, o0, d0, lam, k):
    """O' με D αντιπαλου ×κ σταθερη · D' με O αντιπαλου ×κ σταθερη (ιδιο ridge lam προς o0/d0)."""
    yo = np.r_[eh - hb - mu - k * D[ai], ea + hb - mu - k * D[hi]]; io = np.r_[hi, ai]; ww = np.r_[w, w]
    O2 = (np.bincount(io, ww * yo, n) + lam * o0) / (np.bincount(io, ww, n) + lam)
    yd = np.r_[eh - hb - mu - k * O[hi], ea + hb - mu - k * O[ai]]; idd = np.r_[ai, hi]
    D2 = (np.bincount(idd, ww * yd, n) + lam * d0) / (np.bincount(idd, ww, n) + lam)
    return O2, D2

def run_k(args):
    cfg, k = args
    if 'C' not in F._W: F._init()
    C = F._W['C']; Z = F._W['Z']; G = C.G
    carry, lam, HL, lw, muw, beta, kx, kp = cfg; h = 2.0
    if lw not in C.EHA: C.EHA[lw] = C.luck_eff(lw)
    EH, EA = C.EHA[lw]; R2 = C._radj2()['V0|W1']
    mg = np.full(len(G), np.nan); tt = np.full(len(G), np.nan); onh = np.full(len(G), np.nan); ona = np.full(len(G), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(G.pace.mean())
    for s in C.SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        adj = np.array([beta * R2.get(f'{s}|{t}', 0.0) + kx * Z['C'].get(f'{s}|{t}', 0.0) + kp * Z['P'].get(f'{s}|{t}', 0.0) for t in teams])
        o0 = carry * np.array([prior.get(t, (0, 0, 0))[0] for t in teams]) + adj / 2
        d0 = carry * np.array([prior.get(t, (0, 0, 0))[1] for t in teams]) - adj / 2
        p0 = carry * np.array([prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        nt = (~G.neutral.values[sidx]).astype(float); hb = nt * h / 2; dn = C.dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = G.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = F.fit_mu(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0, muw)
                if k != 1.0: O, Dd = refit(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, O, Dd, mu, o0, d0, lam, k)
                pm, Pc = C.fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100; tt[sidx[cur]] = poss * (e_h + e_a) / 100
            onh[sidx[cur]] = O[aa] - Dd[aa]; ona[sidx[cur]] = O[hh] - Dd[hh]          # βαθμολογια ΑΝΤΙΠΑΛΟΥ εκεινη τη μερα (π./100)
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = F.fit_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, muw)
        if k != 1.0: O, Dd = refit(hi, ai, eh, ea, hb, w, n, O, Dd, mu, o0, d0, lam, k)
        pm, Pc = C.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return (cfg, k), mg.astype(np.float32), tt.astype(np.float32), onh.astype(np.float32), ona.astype(np.float32)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    JOBS = [(c, k) for c in (CFG_H, CFG_T) for k in KAP]
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); RES = {JOBS[i]: tuple(z[f'a{i}_{j}'] for j in range(4)) for i in range(len(JOBS))}
    else:
        with Pool(len(JOBS), initializer=F._init) as pool: R = pool.map(run_k, JOBS)
        RES = {key: (mg, tt, oh, oa) for key, mg, tt, oh, oa in R}
        np.savez(CACHE, keys=np.array([str(j) for j in JOBS]), **{f'a{i}_{j}': RES[JOBS[i]][j] for i in range(len(JOBS)) for j in range(4)})
    F._init(); C = F._W['C']; G = C.G
    _, mg1, tt1, _ = F.run_all(CFG_T)
    P(f'ελεγχος κ=1 vs live run_all (συνολα): μεγ. διαφορα {np.nanmax(np.abs(RES[(CFG_T, 1.0)][1] - tt1)):.3f} π.')
    ND = NormalDist(); rng = np.random.default_rng(3)
    def std_checks(lab, Y, MU, U, CL, ys, day, wk, base_k=1.0):
        """Y πραγματικο, MU {κ: προβλεψη}, U {κ: μοναδες ανα ματς (0 αν οχι pick)}, CL {κ: CLV ανα pick ή nan}"""
        SE = sorted(set(ys)); rm = lambda k, m: float(np.sqrt(np.nanmean((Y[m] - MU[k][m]) ** 2)))
        P(f'\n################ {lab} ################')
        for k in KAP:
            n = int((U[k] != 0).sum())
            P(f"  κ {k:4.2f}{' (LIVE)' if k == base_k else '       '} σφαλμα {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(k, ys == s):.3f}' for s in SE)
              + f") · μοναδες {U[k].sum():+6.1f} (" + ' '.join(f'{s % 100}:{U[k][ys == s].sum():+.0f}' for s in SE) + f') · picks {n} · CLV {np.nanmean(CL[k]):+.2f}')
        cand = [k for k in KAP if k != base_k]
        for k in cand:
            bet = sum(rm(k, ys == s) < rm(base_k, ys == s) for s in SE)
            d = (Y - MU[base_k]) ** 2 - (Y - MU[k]) ** 2; dd = pd.Series(d).groupby(day).sum().dropna().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
            dw = pd.Series(U[k] - U[base_k]).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(3000)])
            ok = bet >= 4 and U[k].sum() >= U[base_k].sum() and np.nanmean(CL[k]) >= np.nanmean(CL[base_k])
            P(f'  κ {k}: σφαλμα καλυτερο {bet}/5 · ζευγαρωτη t {t:+.2f} · μοναδες {dw.sum():+.1f} (bootstrap P {100 * (bs > 0).mean():.0f}%) → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
        tot = [0.0, 0.0]
        for s in SE[2:]:
            prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = min(KAP, key=lambda k: rm(k, prev))
            tot[0] += U[b][cur].sum(); tot[1] += U[base_k][cur].sum(); P(f'  walk-forward {s}: διαλεγει κ {b} · μοναδες {U[b][cur].sum():+.1f} vs live {U[base_k][cur].sum():+.1f}')
        P(f'  walk-forward ΣΥΝΟΛΟ: {tot[0]:+.1f} vs live {tot[1]:+.1f}')
    # ================= ΣΥΝΟΛΑ =================
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O.date, O.home, O.away)]; O = O[O.g.notna()].copy(); O['g'] = O.g.astype(int)
    O = O[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.g, O.tot)]].reset_index(drop=True)
    O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
    gi = O.g.values; ys = O.sea.values; TOT, TL, OO, OU, FA, CF = (O[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    base = RES[(CFG_T, 1.0)][1][gi]; MU = {k: O.mu.values + (RES[(CFG_T, k)][1][gi] - base) for k in KAP}
    U, CL = {}, {}
    for k in KAP:
        po = np.array([1 - ND.cdf((t - m) / 18) for t, m in zip(TL, MU[k])]); eo = po * OO - 1; eu = (1 - po) * OU - 1
        sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd > 0, OO, OU); x = (TOT - TL) * sd
        u = np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0)); U[k] = np.where(e >= .08, u, 0.0); CL[k] = np.where(e >= .08, sd * (CF - FA), np.nan)
    std_checks('ΣΥΝΟΛΑ (CFG_T live, ανοιγμα Crown, edge ≥8%)', TOT, MU, U, CL, ys, day, wk)
    # ================= ΧΑΝΤΙΚΑΠ (αντιγραφο live t22 + Δ μηχανης) =================
    class _B(io.StringIO):
        def reconfigure(self, **k): pass
    _src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(_src, g)
    sys.stdout.reconfigure(encoding='utf-8')
    G2, VNO, SER, SHIFT, line_at, cover_, SIG_, abs_cost, W_B, EV, ACT2, SEAS2, dD2, REPS = (g[x] for x in (
        'G', 'VNO', 'SER', 'SHIFT', 'line_at', 'cover_', 'SIG_', 'abs_cost', 'W_B', 'EV', 'ACT', 'SEAS_G', 'dD', 'REP_SEASONS'))
    GI2 = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    HR = []
    for i, (sw, tip, r21, _) in SER.items():
        s = int(SEAS2[i])
        if s not in EV or s not in REPS or not np.isfinite(VNO[i]): continue
        k0 = GI2.get((str(dD2[i])[:10], G2.home.values[i], G2.away.values[i]))
        if k0 is None: continue
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
        if not rows: continue
        ln = line_at(rows, rows[0][0], sw); cl = line_at(rows, tip, sw)
        if not ln or not cl: continue
        h, a, d = G2.home.values[i], G2.away.values[i], dD2[i]
        m0 = VNO[i] - abs_cost(h, d, s, rows[0][0], W_B)[0] + abs_cost(a, d, s, rows[0][0], W_B)[0]
        HR.append((i, k0, s, str(d)[:10], m0, ln[0], ln[1], ln[2], ln[3], cl[3], float(ACT2[i])))
    H = pd.DataFrame(HR, columns=['i', 'k', 'sea', 'date', 'm0', 'L', 'oh', 'oa', 'fair', 'cfair', 'act'])
    kk = H.k.values; hb_ = RES[(CFG_H, 1.0)][0][kk]
    MUH = {k: H.m0.values + (RES[(CFG_H, k)][0][kk] - hb_) for k in KAP}
    UH, CH = {}, {}
    for k in KAP:
        u_, c_ = np.zeros(len(H)), np.full(len(H), np.nan)
        for j, r in enumerate(H.itertuples(index=False)):
            pw, pp, pl = cover_(MUH[k][j], r.L, SIG_); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
            sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
            if e < .08: continue
            x = (r.act + r.L) * sd; u_[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c_[j] = sd * (r.cfair - r.fair)
        UH[k], CH[k] = u_, c_
    dayh = pd.to_datetime(H.date).values.astype('datetime64[D]'); wkh = (dayh - dayh.min()).astype(int) // 7
    std_checks('ΧΑΝΤΙΚΑΠ (αντιγραφο live + Δ μηχανης CFG_H, ανοιγμα Crown, edge ≥8%)', H.act.values, MUH, UH, CH, H.sea.values, dayh, wkh)
    # ================= ΔΥΣΚΟΛΙΑ ΠΡΟΓΡΑΜΜΑΤΟΣ ΧΩΡΙΣ ΜΕΛΛΟΝ (χαντικαπ) =================
    P('\n################ ΔΥΣΚΟΛΙΑ ΠΡΟΓΡΑΜΜΑΤΟΣ (βαθμολογια αντιπαλων ΤΗ ΜΕΡΑ του ματς) — υπολοιπο πραγματικο − προβλεψη ################')
    _, _, onh, ona = RES[(CFG_H, 1.0)]
    hist = {}; SOS = np.full((len(G), 2), np.nan); NG = np.zeros((len(G), 2))
    for k in np.argsort(G.date.values, kind='stable'):
        for j, t, o in ((0, G.home.values[k], onh[k]), (1, G.away.values[k], ona[k])):
            key = (G.season.values[k], t); L = hist.setdefault(key, [])
            if len(L) >= 10: SOS[k, j] = np.mean(L); NG[k, j] = len(L)
            if np.isfinite(o): L.append(float(o))
    for k in (1.0, 0.75, 0.5):
        rr = []
        for j, r in enumerate(H.itertuples(index=False)):
            for side, sg in ((0, 1), (1, -1)):
                sv = SOS[r.k, side]
                if np.isfinite(sv): rr.append((sv, sg * (r.act - MUH[k][j])))
        A = np.array(rr); sd_ = A[:, 0].std(); q = np.digitize(A[:, 0], [-sd_ * 1.3, sd_ * 1.3])
        b = np.polyfit(A[:, 0], A[:, 1], 1)[0]
        P(f'  κ {k}: κλιση {b:+.3f} π. ανα π./100 δυσκολιας · ευκολο {A[q == 0, 1].mean():+.2f} ({(q == 0).sum()}) · μεσαιο {A[q == 1, 1].mean():+.2f} · δυσκολο {A[q == 2, 1].mean():+.2f} ({(q == 2).sum()})')
    open(os.path.join(SC, 't89_sos_kappa_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
