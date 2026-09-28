# -*- coding: utf-8 -*-
"""nba_base_core.py — πυρηνας για το nba_base_grid: ιδιο walk-forward μοντελο ομαδων με nba_model_test + 2 επεκτασεις:
  (α) ΕΔΡΑ ΑΝΑ ΟΜΑΔΑ: u[ομαδα] γυρω απο την κοινη εδρα h, ridge βαρος lam_u «ματς» προς την περσινη u της ομαδας (1η σεζον 0).
  (β) ΑΦΕΤΗΡΙΑ ΑΠΟ ΡΟΣΤΕΡ: περσινο rating × carry + beta × Δ ρόστερ (nba_roster_adj.json, π./100 στη διαφορα, μισο σε επιθεση/μισο αμυνα).
run2(h, lam, HL, carry, lw, lam_u=None, beta=0) → προβλεψη διαφορας για καθε ματς (ΠΡΙΝ τη μερα του)."""
import sys, io, json, math, contextlib
import numpy as np
_src = open('nba_model_test.py', encoding='utf-8').read().split("P('')\nP('=== ΒΑΣΙΚΟ ΜΟΝΤΕΛΟ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
with contextlib.redirect_stdout(io.StringIO()):
    exec(_src)
RADJ = json.load(open('nba_roster_adj.json', encoding='utf-8'))['delta']

def fit_eff2(hi, ai, eh, ea, hb, nt, w, n, o0, d0, lam, mu0, lam_u, u0):
    nG = len(hi); sw = np.sqrt(w); nu = n if lam_u else 0
    A = np.zeros((2 * nG + 2 * n + nu + 1, 1 + 2 * n + nu)); y = np.zeros(A.shape[0])
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    if nu:
        A[r0, 1 + 2 * n + hi] = 0.5 * sw * nt; A[r1, 1 + 2 * n + hi] = -0.5 * sw * nt
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    if nu:
        su = math.sqrt(lam_u); A[2 * nG + 2 * n + k, 1 + 2 * n + k] = su; y[2 * nG + 2 * n + k] = su * u0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:1 + 2 * n], (x[1 + 2 * n:] if nu else np.zeros(n))

def run2(h=2.0, lam=8, HL=60, carry=0.7, lw=0.5, lam_u=None, beta=0.0):
    if lw not in EHA: EHA[lw] = luck_eff(lw)
    EH, EA = EHA[lw]
    pm_ = np.full(len(G), np.nan); prior = {}; uprior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(G.pace.mean())
    for s in SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        adj = np.array([beta * RADJ.get(f'{s}|{t}', 0.0) for t in teams])
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]) + adj / 2
        d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams]) - adj / 2
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        u0 = np.array([uprior.get(t, 0.0) for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        nt = (~G.neutral.values[sidx]).astype(float)
        hb = nt * h / 2; dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = G.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd, U = fit_eff2(hi[past], ai[past], eh[past], ea[past], hb[past], nt[past], w, n, o0, d0, lam, mu0, lam_u, u0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, U, pm, Pc = mu0, o0, d0, u0, pm0, p0
            hh, aa = hi[cur], ai[cur]; hbb = hb[cur] + nt[cur] * U[hh] / 2
            eh_ = mu + O[hh] + Dd[aa] + hbb; ea_ = mu + O[aa] + Dd[hh] - hbb; poss = pm + Pc[hh] + Pc[aa]
            pm_[sidx[cur]] = poss * (eh_ - ea_) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd, U = fit_eff2(hi, ai, eh, ea, hb, nt, w, n, o0, d0, lam, mu0, lam_u, u0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
        uprior = {t: U[i] for t, i in ix.items()}
    return pm_.astype(np.float32)

def job(cfg):
    return cfg, run2(**cfg)
