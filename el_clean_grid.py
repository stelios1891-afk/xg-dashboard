# -*- coding: utf-8 -*-
"""el_clean_grid.py — ΕΥΡΩΛΙΓΚΑ «ΚΑΘΑΡΟ» BACKTEST, σταδιο 1: ΠΛΕΓΜΑ ΠΡΟΒΛΕΨΕΩΝ (5/10/2026, Στελιος «τρεξε ολα τα τεστ»).
Ολες οι εκδοχες της μηχανης γυρω απο το live, ωστε στο σταδιο 2 (el_clean_tests.py) καθε σεζον-ελεγχου να επιλεγει μηχανη ΜΟΝΟ απο τις αλλες.
ΧΑΝΤΙΚΑΠ (ιδια δομικα κομματια με el_domestic_rating_test / el_preseason_test / live el_refresh ENG_SPREAD):
  περσι wt {.3,.5,.7} × ειδικοι we {0,.42,.7} × λ {8,12} × HL {60,120} × εδρα {5,6} × ανοιγμα απο 7ο sf {1,1.1}
  × φετινα εγχωρια απο 11ο κd {0,.5} × φιλικα κp {0,.5}  (τυχη .5) — live = (.5, .42, 12, 60, 5, 1.1, .5, .5)
ΣΥΝΟΛΟ (ιδια με live ENG_TOTAL, χωρις φθορα, εδρα 6): τυχη {.25,.5} × περσι {.5,.7,1} × λ {8,12} × μ_w {5,50} — καμπυλη/φιλικα στο σταδιο 2.
Εξοδος: el_clean_grid.pkl {'D_key': [κλειδια ματς], 'H': {cfg: array}, 'T': {cfg: array}, 'GN', 'season', 'act', 'tot', 'phase', 'PRE_T', 'home', 'away'}"""
import sys, time, pickle, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
A = {}
src = open('el_preseason_test.py', encoding='utf-8').read().split('# ---- 1. διαγνωση ----')[0]
src = src.replace("open('el_preseason_test_out.txt', 'w'", "open('_unused_ecg1.txt', 'w'")
exec(src, A)
def find(ns, name, depth=0):
    if name in ns: return ns[name]
    if depth > 4: return None
    for v in list(ns.values()):
        if isinstance(v, dict) and v is not ns and '__builtins__' in v:
            r = find(v, name, depth + 1)
            if r is not None: return r
    return None
D, SE5, EM, GN, dnum, LUCK, fit_eff, fit_pace, PRE = (A[k] for k in ('D', 'SE5', 'EM', 'GN', 'dnum', 'LUCK', 'fit_eff', 'fit_pace', 'PRE'))
S20, dom_shift = A['S20'], A['dom_shift']
ends_for = find(A, 'ends_for')
assert ends_for is not None, 'δεν βρεθηκε ends_for'
print(f'D {len(D)} ματς · σεζον-τεστ {SE5} · PRE {len(PRE)}', flush=True)
# ---------- χαντικαπ ----------
ENDC = {}
def ends(HL, h, lam):
    k = (HL, h, lam)
    if k not in ENDC: ENDC[k] = ends_for(HL, h, .5, lam)
    return ENDC[k]
DSH = {}
def dsh(Y, t, d):
    k = (Y, t, d)
    if k not in DSH: DSH[k] = dom_shift(S20, Y, t, d)
    return DSH[k]
def run_h(wt, we, lam, HL, h, sf, kd, kp):
    EH, EA = LUCK[.5]; ENDS = ends(HL, h, lam); v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; prior = st['prior']
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * we
        pr = np.array([kp * PRE.get((Y, t), 0.0) * 100 / 72 for t in teams])
        o0b = np.array([wt * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2 + pr / 2
        d0b = np.array([wt * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2 - pr / 2
        p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, h / 2); dn = dnum[sidx]; gn = GN[sidx]
        pred = np.full(len(sidx), np.nan)
        for d in np.unique(dn):
            cur = np.where(dn == d)[0]; past = dn < d
            def solve(o0, d0):
                if past.any():
                    w = 0.5 ** ((d - dn[past]) / HL)
                    mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, lam, st['mu0'])
                    pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, lam, st['pm0'])
                else:
                    mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
                return mu, O, Dd, pm, Pc
            late = gn[cur] >= 11
            groups = []
            if kd and late.any():
                sh = np.array([kd * dsh(Y, t, int(d)) * 100 / 72 for t in teams])
                groups.append((cur[late], solve(o0b + sh / 2, d0b - sh / 2)))
                if (~late).any(): groups.append((cur[~late], solve(o0b, d0b)))
            else:
                groups.append((cur, solve(o0b, d0b)))
            for cc, (mu, O, Dd, pm, Pc) in groups:
                hh, aa, hbb = hi[cc], ai[cc], hb[cc]
                pred[cc] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
        v[sidx] = pred
    return np.where(GN >= 7, v * sf, v)
# ---------- συνολο ----------
def fit_eff_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, mu_w):
    nG = len(hi); sw = np.sqrt(w)
    Am = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    Am[r0, 0] = sw; Am[r0, 1 + hi] = sw; Am[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    Am[r1, 0] = sw; Am[r1, 1 + ai] = sw; Am[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    Am[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; Am[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    Am[-1, 0] = math.sqrt(mu_w); y[-1] = math.sqrt(mu_w) * mu0
    x = np.linalg.lstsq(Am, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]
SEAS = sorted(set(D.season))
def run_t(lw, carry, lam, muw, h=6.0):
    EH, EA = LUCK[lw]; v = np.full(len(D), np.nan); prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, h / 2); dn = dnum[sidx]
        if s in SE5:
            for d in np.unique(dn):
                cur = np.where(dn == d)[0]; past = dn < d
                if past.any():
                    w = np.ones(past.sum())
                    mu, O, Dd = fit_eff_mu(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, lam, mu0, muw)
                    pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, lam, pm0)
                else:
                    mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
                hh, aa = hi[cur], ai[cur]
                v[sidx[cur]] = (pm + Pc[hh] + Pc[aa]) * (2 * mu + O[hh] + Dd[aa] + O[aa] + Dd[hh]) / 100
        w = np.ones(len(sidx))
        mu, O, Dd = fit_eff_mu(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, lam, mu0, muw)
        pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return v
if '--time' in sys.argv:
    t0 = time.time(); run_h(.5, .42, 12, 60, 5.0, 1.1, .5, .5); print(f'1 χαντικαπ {time.time() - t0:.1f}s')
    t0 = time.time(); run_t(.25, .7, 8, 50.0); print(f'1 συνολο {time.time() - t0:.1f}s'); sys.exit()
import itertools
H = {}; T = {}; t0 = time.time()
GH = list(itertools.product((.3, .5, .7), (0.0, .42, .7), (8, 12), (60, 120), (5.0, 6.0), (1.0, 1.1), (0.0, .5), (0.0, .5)))
for j, g in enumerate(GH):
    H[g] = run_h(*g)
    if j % 24 == 0: print(f'  χαντικαπ {j + 1}/{len(GH)} ({time.time() - t0:.0f}s)', flush=True)
for g in itertools.product((.25, .5), (.5, .7, 1.0), (8, 12), (5.0, 50.0)):
    T[g] = run_t(*g)
print(f'συνολα {len(T)} ετοιμα ({time.time() - t0:.0f}s)', flush=True)
# φιλικα στα συνολα (el_preseason_totals_test PRE_T)
B = {}
src = open('el_preseason_totals_test.py', encoding='utf-8').read().split('# ---- 1. διαγνωση ----')[0].replace("open('el_preseason_totals_test_out.txt', 'w'", "open('_unused_ecg2.txt', 'w'")
exec(src, B)
key = [(D.season.values[i], D.home.values[i], D.away.values[i], str(pd.Timestamp(D.t.values[i]))[:16]) for i in range(len(D))]
pickle.dump(dict(key=key, H=H, T=T, GN=np.asarray(GN), season=D.season.values, phase=D.phase.values, home=D.home.values, away=D.away.values,
                 act=(D.hs - D.as_).values.astype(float), tot=(D.hs + D.as_).values.astype(float), PRE_T=dict(B['PRE_T']), SE5=list(SE5),
                 ff=(D.ff.values | D.relocated.values), t=[str(x) for x in D.t.values]), open('el_clean_grid.pkl', 'wb'))
print(f'ΤΕΛΟΣ: el_clean_grid.pkl · χαντικαπ {len(H)} · συνολο {len(T)} · {time.time() - t0:.0f}s')
