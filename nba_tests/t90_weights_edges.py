# -*- coding: utf-8 -*-
"""t90_weights_edges.py — NBA: ΑΝΟΙΓΜΑ ΤΩΝ ΑΚΡΩΝ ΤΟΥ ΠΛΕΓΜΑΤΟΣ ΒΑΡΩΝ + SoS ΜΟΝΟ ΝΩΡΙΣ (25/10/2026, Στελιος «οκ τρεξτο» + «το SoS μενει ολη
τη σεζον; ισως αξιζει νωρις και μετα δεν χρειαζεται»).
Στο πλεγμα 1.152 (6/10) πολλες επιλογες επεσαν ΣΤΗΝ ΑΚΡΗ: K 8 (μικροτερο), HL 60 (μικροτερο), ειδικοι .75 (μεγαλυτερο), φιλικα .25 (μεγαλυτερο).
ΕΝΑΣ ΜΗΧΑΝΙΣΜΟΣ ΤΗ ΦΟΡΑ (τα υπολοιπα = live):
  ΧΑΝΤΙΚΑΠ (CFG_H): K {4, 6, 8} · HL {30, 45, 60} · ειδικοι {.75, 1.0, 1.25} · φιλικα {.25, .4}
  ΣΥΝΟΛΑ   (CFG_T): K {4, 6, 8} · HL {30, 45, 60}
  SoS ΜΟΝΟ ΝΩΡΙΣ (και στα δυο): πληρης διορθωση αντιπαλου (κ 1) ως τον 20ο αγωνα της σεζον, μετα κ_late ∈ {.5, .75}.
Περιγραφικο: μεροληψια προγραμματος (κλιση υπολοιπου ως προς δυσκολια, βαθμολογια αντιπαλων τη μερα του ματς) ανα φαση σεζον, κ 1 vs .5.
ΚΡΙΤΗΡΙΑ (ιδια με t89): σφαλμα καλυτερο ≥4/5 σεζον ΚΑΙ μοναδες & CLV οχι χειροτερα + walk-forward, ζευγαρωτη t, bootstrap.
Εξοδος: nba_tests/t90_weights_edges_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import nba_full_clean_test as F
import t89_sos_kappa as T9
CFG_H, CFG_T = T9.CFG_H, T9.CFG_T
def rep(c, j, v): c = list(c); c[j] = v; return tuple(c)
VH = {'LIVE': (CFG_H, None)}
for v in (4, 6): VH[f'K {v}'] = (rep(CFG_H, 1, v), None)
for v in (30, 45): VH[f'HL {v}'] = (rep(CFG_H, 2, v), None)
for v in (1.0, 1.25): VH[f'ειδικοι {v}'] = (rep(CFG_H, 6, v), None)
VH['φιλικα 0.4'] = (rep(CFG_H, 7, 0.4), None)
for v in (0.5, 0.75): VH[f'SoS νωρις, μετα κ {v}'] = (CFG_H, v)
VT = {'LIVE': (CFG_T, None)}
for v in (4, 6): VT[f'K {v}'] = (rep(CFG_T, 1, v), None)
for v in (30, 45): VT[f'HL {v}'] = (rep(CFG_T, 2, v), None)
for v in (0.5, 0.75): VT[f'SoS νωρις, μετα κ {v}'] = (CFG_T, v)
GP_SWITCH = 20

def run_v(args):
    cfg, klate = args
    if 'C' not in F._W: F._init()
    if klate is None:
        _, mg, tt, _ = F.run_all(cfg); return args, mg, tt
    C = F._W['C']; Z = F._W['Z']; G = C.G
    carry, lam, HL, lw, muw, beta, kx, kp = cfg; h = 2.0
    if lw not in C.EHA: C.EHA[lw] = C.luck_eff(lw)
    EH, EA = C.EHA[lw]; R2 = C._radj2()['V0|W1']
    mg = np.full(len(G), np.nan); tt = np.full(len(G), np.nan); prior = {}
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
                gp = 2.0 * past.sum() / n                                   # μεσος αριθμος αγωνων ανα ομαδα ως τοτε
                if gp > GP_SWITCH: O, Dd = T9.refit(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, O, Dd, mu, o0, d0, lam, klate)
                pm, Pc = C.fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100; tt[sidx[cur]] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = F.fit_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, muw)
        O, Dd = T9.refit(hi, ai, eh, ea, hb, w, n, O, Dd, mu, o0, d0, lam, klate)
        pm, Pc = C.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return args, mg, tt

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    JOBS = sorted(set(list(VH.values()) + list(VT.values())), key=str)
    with Pool(8, initializer=F._init) as pool: R = pool.map(run_v, JOBS)
    RES = {a: (mg, tt) for a, mg, tt in R}
    F._init(); C = F._W['C']; G = C.G
    ND = NormalDist(); rng = np.random.default_rng(9)
    def checks(lab, Y, MU, U, CL, ys, day, wk):
        SE = sorted(set(ys)); rm = lambda k, m: float(np.sqrt(np.nanmean((Y[m] - MU[k][m]) ** 2)))
        P(f'\n################ {lab} ################')
        for k in MU:
            line = f"  {k:24s} σφαλμα {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(k, ys == s):.3f}' for s in SE) + f") · μοναδες {U[k].sum():+6.1f} · picks {int((U[k] != 0).sum())} · CLV {np.nanmean(CL[k]):+.2f}"
            if k != 'LIVE':
                bet = sum(rm(k, ys == s) < rm('LIVE', ys == s) for s in SE)
                d = (Y - MU['LIVE']) ** 2 - (Y - MU[k]) ** 2; dd = pd.Series(d).groupby(day).sum().dropna().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
                dw = pd.Series(U[k] - U['LIVE']).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(2000)])
                ok = bet >= 4 and U[k].sum() >= U['LIVE'].sum() and np.nanmean(CL[k]) >= np.nanmean(CL['LIVE'])
                line += f' │ καλυτερο {bet}/5 · t {t:+.2f} · Δμοναδες {dw.sum():+.1f} (P {100 * (bs > 0).mean():.0f}%) → {"ΠΕΡΝΑΕΙ" if ok else "✗"}'
            P(line)
        # walk-forward μεσα σε καθε οικογενεια μηχανισμου
        fams = {}
        for k in MU:
            if k != 'LIVE': fams.setdefault(k.split(' ')[0], []).append(k)
        for f_, ks in fams.items():
            ks = ['LIVE'] + ks; tot = [0.0, 0.0]; ch = []
            for s in SE[2:]:
                prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = min(ks, key=lambda k: rm(k, prev))
                tot[0] += U[b][cur].sum(); tot[1] += U['LIVE'][cur].sum(); ch.append(f'{s % 100}:{b}')
            P(f'  walk-forward [{f_}] επιλογες {" · ".join(ch)} → μοναδες {tot[0]:+.1f} vs live {tot[1]:+.1f}')
    # ---- ΣΥΝΟΛΑ ----
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O.date, O.home, O.away)]; O = O[O.g.notna()].copy(); O['g'] = O.g.astype(int)
    O = O[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.g, O.tot)]].reset_index(drop=True)
    O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
    gi = O.g.values; ys = O.sea.values; TOT, TL, OO, OU, FA, CF = (O[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    base = RES[VT['LIVE']][1][gi]; MU = {k: O.mu.values + (RES[a][1][gi] - base) for k, a in VT.items()}
    U, CL = {}, {}
    for k in MU:
        po = np.array([1 - ND.cdf((t - m) / 18) for t, m in zip(TL, MU[k])]); eo = po * OO - 1; eu = (1 - po) * OU - 1
        sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd > 0, OO, OU); x = (TOT - TL) * sd
        U[k] = np.where(e >= .08, np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0)), 0.0); CL[k] = np.where(e >= .08, sd * (CF - FA), np.nan)
    checks('ΣΥΝΟΛΑ (CFG_T, ανοιγμα Crown, edge ≥8%)', TOT, MU, U, CL, ys, day, wk)
    # ---- ΧΑΝΤΙΚΑΠ ----
    class _B(io.StringIO):
        def reconfigure(self, **k): pass
    _src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(_src, g)
    sys.stdout.reconfigure(encoding='utf-8')
    G2, VNO, SER, SHIFT, line_at, cover_, SIG_, abs_cost, W_B, EV, ACT2, SEAS2, dD2, REPS = (g[x] for x in (
        'G', 'VNO', 'SER', 'SHIFT', 'line_at', 'cover_', 'SIG_', 'abs_cost', 'W_B', 'EV', 'ACT', 'SEAS_G', 'dD', 'REP_SEASONS'))
    HR = []
    for i, (sw, tip, r21, _) in SER.items():
        s = int(SEAS2[i])
        if s not in EV or s not in REPS or not np.isfinite(VNO[i]): continue
        k0 = GI.get((str(dD2[i])[:10], G2.home.values[i], G2.away.values[i]))
        if k0 is None: continue
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
        if not rows: continue
        ln = line_at(rows, rows[0][0], sw); cl = line_at(rows, tip, sw)
        if not ln or not cl: continue
        h, a, d = G2.home.values[i], G2.away.values[i], dD2[i]
        m0 = VNO[i] - abs_cost(h, d, s, rows[0][0], W_B)[0] + abs_cost(a, d, s, rows[0][0], W_B)[0]
        HR.append((k0, s, str(d)[:10], m0, ln[0], ln[1], ln[2], ln[3], cl[3], float(ACT2[i])))
    H = pd.DataFrame(HR, columns=['k', 'sea', 'date', 'm0', 'L', 'oh', 'oa', 'fair', 'cfair', 'act'])
    kk = H.k.values; hb_ = RES[VH['LIVE']][0][kk]
    MUH = {k: H.m0.values + (RES[a][0][kk] - hb_) for k, a in VH.items()}
    UH, CH = {}, {}
    for k in MUH:
        u_, c_ = np.zeros(len(H)), np.full(len(H), np.nan)
        for j, r in enumerate(H.itertuples(index=False)):
            pw, pp, pl = cover_(MUH[k][j], r.L, SIG_); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
            sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
            if e < .08: continue
            x = (r.act + r.L) * sd; u_[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c_[j] = sd * (r.cfair - r.fair)
        UH[k], CH[k] = u_, c_
    dayh = pd.to_datetime(H.date).values.astype('datetime64[D]'); wkh = (dayh - dayh.min()).astype(int) // 7
    checks('ΧΑΝΤΙΚΑΠ (αντιγραφο live + Δ μηχανης, ανοιγμα Crown, edge ≥8%)', H.act.values, MUH, UH, CH, H.sea.values, dayh, wkh)
    # ---- μεροληψια προγραμματος ανα φαση σεζον (απο το cache του t89) ----
    z = np.load(os.path.join(SC, '_t89_cache.npz'), allow_pickle=True); JB = [(c, k) for c in (CFG_H, CFG_T) for k in T9.KAP]
    R9 = {JB[i]: tuple(z[f'a{i}_{j}'] for j in range(4)) for i in range(len(JB))}
    onh, ona = R9[(CFG_H, 1.0)][2], R9[(CFG_H, 1.0)][3]
    hist = {}; SOS = np.full((len(G), 2), np.nan); NG = np.zeros((len(G), 2))
    for k in np.argsort(G.date.values, kind='stable'):
        for j, t, o in ((0, G.home.values[k], onh[k]), (1, G.away.values[k], ona[k])):
            L = hist.setdefault((G.season.values[k], t), [])
            if len(L) >= 5: SOS[k, j] = np.mean(L); NG[k, j] = len(L)
            if np.isfinite(o): L.append(float(o))
    P('\n################ ΜΕΡΟΛΗΨΙΑ ΠΡΟΓΡΑΜΜΑΤΟΣ ΑΝΑ ΦΑΣΗ (χαντικαπ, κλιση υπολοιπου ανα 1 π./100 δυσκολιας· 0 = σωστο) ################')
    mk = {kap: H.m0.values + (R9[(CFG_H, kap)][0][kk] - R9[(CFG_H, 1.0)][0][kk]) for kap in (1.0, 0.5)}
    for lo, hi in ((5, 20), (21, 40), (41, 99)):
        line = f'  αγωνες {lo:2d}-{hi if hi < 99 else "τελος"}: '
        for kap in (1.0, 0.5):
            rr = [(SOS[r.k, sd_], sg * (r.act - mk[kap][j])) for j, r in enumerate(H.itertuples(index=False))
                  for sd_, sg in ((0, 1), (1, -1)) if np.isfinite(SOS[r.k, sd_]) and lo <= NG[r.k, sd_] <= hi]
            A = np.array(rr); b = np.polyfit(A[:, 0], A[:, 1], 1)[0]; se = np.std(A[:, 1]) / np.sqrt(len(A)) / A[:, 0].std()
            line += f'κ {kap}: {b:+.3f} (t {b / se:+.1f}, n {len(A)})   '
        P(line)
    open(os.path.join(SC, 't90_weights_edges_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
