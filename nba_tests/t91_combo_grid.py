# -*- coding: utf-8 -*-
"""t91_combo_grid.py — NBA: ΚΑΛΥΤΕΡΟΣ ΣΥΝΔΥΑΣΜΟΣ ΒΑΡΩΝ (25/10/2026, Στελιος «το θεμα ειναι ποιος ειναι ο καλυτερος συνδυασμος, οχι ενα ενα»).
ΧΑΝΤΙΚΑΠ 40: ειδικοι {.75, 1, 1.25, 1.5, 2} × HL {45, 60} × K {6, 8} × φιλικα {.25, .4} (υπολοιπα = CFG_H live).
ΣΥΝΟΛΑ 8: τυχη αμυνας {.5, .25} (επιθεση .5) × HL {45, 60} × K {6, 8} (υπολοιπα = CFG_T live).
ΕΠΙΛΟΓΗ χωρις να βλεπει τη σεζον που κρινεται: LOSO (σφαλμα στις αλλες 4) · WALK-FORWARD (μονο προηγουμενες).
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): ο LOSO-συνδυασμος ΠΕΡΝΑ αν σφαλμα καλυτερο απο live ≥4/5 ΚΑΙ μοναδες & CLV οχι χειροτερα ΚΑΙ walk-forward
  μοναδες οχι χειροτερες ΚΑΙ placebo < 5%. (+ ζευγαρωτη t, bootstrap, top-5 συνδυασμοι για πληροφορια.)
Εξοδος: nba_tests/t91_combo_grid_out.txt"""
import os, sys, io, contextlib, itertools
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import nba_full_clean_test as F
import t85_luck_split as T5
CFG_H = (0.8, 8, 60, .75, 5.0, 1.0, .75, .25); CFG_T = (0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0)
GH = [(kx, hl, k, kp) for kx in (.75, 1.0, 1.25, 1.5, 2.0) for hl in (45, 60) for k in (6, 8) for kp in (.25, .4)]
GT = [(wd, hl, k) for wd in (.5, .25) for hl in (45, 60) for k in (6, 8)]
LIVE_H, LIVE_T = (.75, 60, 8, .25), (.5, 60, 8)
def cfgH(c): kx, hl, k, kp = c; return (CFG_H[0], k, hl, CFG_H[3], CFG_H[4], CFG_H[5], kx, kp)
def cfgT(c): wd, hl, k = c; return (CFG_T[0], k, hl, CFG_T[3], CFG_T[4], 0.0, 0.0, 0.0), wd

def job(a):
    kind, c = a
    if 'C' not in F._W: F._init()
    if kind == 'H':
        _, mg, tt, _ = F.run_all(cfgH(c)); return a, mg, tt
    cfg, wd = cfgT(c); T5.CFG = cfg
    _, mg, tt = T5.run_split((0.5, wd)); return a, mg, tt

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    JOBS = [('H', c) for c in GH] + [('T', c) for c in GT]
    with Pool(8, initializer=F._init) as pool: R = pool.map(job, JOBS, chunksize=1)
    RES = {a: (mg, tt) for a, mg, tt in R}
    F._init(); C = F._W['C']; G = C.G
    _, _, tlive, _ = F.run_all(CFG_T)
    P(f"ελεγχος: συνολα (.5/.5, 60, 8) εδω vs live run_all · μεγ. διαφορα {np.nanmax(np.abs(RES[('T', LIVE_T)][1] - tlive)):.3f} π.")
    ND = NormalDist(); rng = np.random.default_rng(21)
    def evaluate(lab, Y, MU, U, CL, ys, day, wk, live, pick_fn, base_mu):
        SE = sorted(set(ys)); rm = lambda k, m: float(np.sqrt(np.nanmean((Y[m] - MU[k][m]) ** 2)))
        P(f'\n################ {lab} · {len(MU)} συνδυασμοι ################')
        tot = {k: rm(k, ys == ys) for k in MU}
        P('  TOP-6 (ολες οι σεζον, μονο πληροφορια):')
        for k in sorted(MU, key=lambda k: tot[k])[:6] + ([live] if live not in sorted(MU, key=lambda k: tot[k])[:6] else []):
            bet = sum(rm(k, ys == s) < rm(live, ys == s) for s in SE)
            P(f"    {str(k):24s}{' (LIVE)' if k == live else '       '} σφαλμα {tot[k]:.3f} · καλυτερο απο live {bet}/5 · μοναδες {U[k].sum():+6.1f} · picks {int((U[k] != 0).sum())} · CLV {np.nanmean(CL[k]):+.2f}")
        sel = {s: min(MU, key=lambda k: rm(k, ys != s)) for s in SE}
        P('  LOSO επιλογες: ' + ' · '.join(f'{s % 100}:{sel[s]}' for s in SE))
        LM = np.zeros(len(Y)); LU = np.zeros(len(Y)); LC = np.full(len(Y), np.nan)
        for s in SE: m = ys == s; LM[m] = MU[sel[s]][m]; LU[m] = U[sel[s]][m]; LC[m] = CL[sel[s]][m]
        bet = sum(np.sqrt(np.nanmean((Y - LM)[ys == s] ** 2)) < rm(live, ys == s) for s in SE)
        d = (Y - MU[live]) ** 2 - (Y - LM) ** 2; dd = pd.Series(d).groupby(day).sum().dropna().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
        dw = pd.Series(LU - U[live]).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(3000)])
        P(f'  LOSO: σφαλμα {np.sqrt(np.nanmean((Y - LM) ** 2)):.3f} vs live {tot[live]:.3f} · καλυτερο {bet}/5 · ζευγαρωτη t {t:+.2f} · μοναδες {LU.sum():+.1f} vs {U[live].sum():+.1f} '
          f'(bootstrap P {100 * (bs > 0).mean():.0f}%) · CLV {np.nanmean(LC):+.2f} vs {np.nanmean(CL[live]):+.2f}')
        wf = [0.0, 0.0]; ch = []
        for s in SE[2:]:
            prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = min(MU, key=lambda k: rm(k, prev))
            wf[0] += U[b][cur].sum(); wf[1] += U[live][cur].sum(); ch.append(f'{s % 100}:{b}')
        P(f'  WALK-FORWARD: {" · ".join(ch)} → μοναδες {wf[0]:+.1f} vs live {wf[1]:+.1f}')
        dlt = LM - MU[live]; real = LU.sum() - U[live].sum(); res = []
        for _ in range(300):
            perm = dlt.copy()
            for s in SE:
                m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
            res.append(pick_fn(base_mu + perm)[0].sum() - U[live].sum())
        pl = 100 * (np.array(res) >= real).mean()
        P(f'  PLACEBO: πραγματικο {real:+.1f}μ · ανακατεμενη 95% ως {np.percentile(res, 95):+.1f} · ≥ πραγματικο {pl:.1f}%')
        ok = bet >= 4 and LU.sum() >= U[live].sum() and np.nanmean(LC) >= np.nanmean(CL[live]) and wf[0] >= wf[1] and pl < 5
        P(f'  ΚΡΙΤΗΡΙΑ → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
    # ---- ΣΥΝΟΛΑ ----
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O.date, O.home, O.away)]; O = O[O.g.notna()].copy(); O['g'] = O.g.astype(int)
    O = O[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.g, O.tot)]].reset_index(drop=True)
    O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
    gi = O.g.values; ys = O.sea.values; TOT, TL, OO, OU, FA, CF = (O[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    base = RES[('T', LIVE_T)][1][gi]; MU = {c: O.mu.values + (RES[('T', c)][1][gi] - base) for c in GT}
    def pickT(mu):
        po = np.array([1 - ND.cdf((t - m) / 18) for t, m in zip(TL, mu)]); eo = po * OO - 1; eu = (1 - po) * OU - 1
        sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd > 0, OO, OU); x = (TOT - TL) * sd
        return np.where(e >= .08, np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0)), 0.0), np.where(e >= .08, sd * (CF - FA), np.nan)
    U, CL = {}, {}
    for c in GT: U[c], CL[c] = pickT(MU[c])
    evaluate('ΣΥΝΟΛΑ (τυχη αμυνας, HL, K)', TOT, MU, U, CL, ys, day, wk, LIVE_T, pickT, MU[LIVE_T])
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
    kk = H.k.values; hb_ = RES[('H', LIVE_H)][0][kk]
    MUH = {c: H.m0.values + (RES[('H', c)][0][kk] - hb_) for c in GH}
    Lh, OH, OA, FH, CFH, AH = (H[c].values.astype(float) for c in ('L', 'oh', 'oa', 'fair', 'cfair', 'act'))
    def pickH(mu):
        u_, c_ = np.zeros(len(H)), np.full(len(H), np.nan)
        for j in range(len(H)):
            pw, pp, pl = cover_(mu[j], Lh[j], SIG_); e1, e2 = pw * OH[j] + pp - 1, pl * OA[j] + pp - 1
            sd, e, od = (1, e1, OH[j]) if e1 >= e2 else (-1, e2, OA[j])
            if e < .08: continue
            x = (AH[j] + Lh[j]) * sd; u_[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c_[j] = sd * (CFH[j] - FH[j])
        return u_, c_
    UH, CH = {}, {}
    for c in GH: UH[c], CH[c] = pickH(MUH[c])
    dayh = pd.to_datetime(H.date).values.astype('datetime64[D]'); wkh = (dayh - dayh.min()).astype(int) // 7
    evaluate('ΧΑΝΤΙΚΑΠ (ειδικοι, HL, K, φιλικα)', AH, MUH, UH, CH, H.sea.values, dayh, wkh, LIVE_H, pickH, MUH[LIVE_H])
    open(os.path.join(SC, 't91_combo_grid_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
