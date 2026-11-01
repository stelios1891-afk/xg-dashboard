# -*- coding: utf-8 -*-
"""el_prior_grid_test.py — ΑΦΕΤΗΡΙΑ ΣΕΖΟΝ: μειγμα περσι/ειδικοι × K (warm start) × εξοδος ειδικων (25/9/2026, αιτημα Στελιου).
Μοντελο = το live χαντικαπ (v1 walk-forward: HL 120, εδρα 6/100, τυχη 50%, ρυθμος), ΜΟΝΟ η αφετηρια της σεζον αλλαζει:
  αρχικο (επιθεση, αμυνα) = w_team·(περσινο τελος) + w_exp·E(θεση BasketNews)/2 (±)· ρυθμος = 0.7·περσι (αμεταβλητο)
  K = ποσα «ματς» αξιζει η αφετηρια απεναντι στα φετινα (ridge λ)
  εξοδος: ποτε / μετα την 10η αγωνιστικη (τοτε η αφετηρια γινεται μονο w_team·περσι — χωρις ειδικους)
  E(θεση): ποσοστημοριο ratings ομαδων των ΑΛΛΩΝ σεζον (ridge λ2, οπως live).
ΠΛΕΓΜΑ: w_team {0.2, 0.32, 0.5, 0.7} × w_exp {0, 0.2, 0.42, 0.6} × K {4, 8, 12, 20} × εξοδος {ποτε, 10} = 128
  (live = 0.32/0.42/8/ποτε · v1 = 0.7/0/8)
LOSO (2021-2025): επιλογη = ελαχιστο RMSE διαφορας σε ΟΛΑ τα ματς κανονικης περιοδου των αλλων 4 σεζον.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ΜΙΑ εκτελεση) — η LOSO επιλογη αντικαθιστα το live αν στα held-out:
  (α) RMSE μικροτερο συνολικα ΚΑΙ σε ≥3/5 σεζον · (β) ROI χαντικαπ edge ≥8% οχι χειροτερο απο live, κερδοφορες σεζον οχι λιγοτερες.
Εξοδος: el_prior_grid_test_out.txt"""
import sys, math, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o5 = []
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
exec(ex.split('base, ENDS = run_x(0.0)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''))
out = _o5
def P(s=''):
    print(s, flush=True); out.append(str(s))
gv = {}
exec(open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), gv)
TE = {s: gv['team_end'](s) for s in gv['SEAS']}
def q2r(q, excl):
    ends = [np.sort(np.array(list(TE[s].values())))[::-1] for s in gv['SEAS'] if s >= 'E2018' and s != excl]
    return float(np.mean([np.interp(q, (np.arange(len(e)) + .5) / len(e), e) for e in ends]))
SE5 = list(RANK)

# ---- v1 βαση: τελος καθε σεζον (O, D, P, mu, pm) με τις live ρυθμισεις ----
if 'L' not in _PTS:
    ph, pa = points(D, 'L'); _PTS['L'] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
EH, EA = _PTS['L']
dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
HL, H = 120, 6.0
END = {}; prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
for s in SEAS:
    sidx = np.where(D.season.values == s)[0]
    teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    START = dict(prior=dict(prior), mu0=mu0, pm0=pm0)
    o0 = np.array([0.7 * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([0.7 * prior.get(t, (0, 0, 0))[1] for t in teams]); p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
    hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
    hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, H / 2); dn = dnum[sidx]
    w = 0.5 ** ((dn.max() - dn) / HL)
    mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, 8, mu0)
    pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, 8, pm0)
    END[s] = START
    prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
# αριθμος αγωνα
rs_all = D[D.phase == 'RS'].sort_values('date'); cnt = {}; GN = np.full(len(D), 99)
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    GN[D.index.get_loc(i)] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])

def run_season(s, wt, we, Emap, lam, exit_r):
    st = END[s]; prior = st['prior']
    sidx = np.where(D.season.values == s)[0]
    teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    oT = np.array([wt * prior.get(t, (0, 0, 0))[0] for t in teams]); dT = np.array([wt * prior.get(t, (0, 0, 0))[1] for t in teams])
    p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
    e = np.array([Emap.get(t, 0.0) for t in teams]) * we
    oE, dE = oT + e / 2, dT - e / 2
    hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
    hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, H / 2); dn = dnum[sidx]; gn = GN[sidx]
    pred = np.full(len(sidx), np.nan)
    for d in np.unique(dn):
        past = dn < d; cur = np.where(dn == d)[0]
        use_exp = exit_r is None or gn[cur].min() <= exit_r
        o0, d0 = (oE, dE) if use_exp else (oT, dT)
        if past.any():
            w = 0.5 ** ((d - dn[past]) / HL)
            mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, lam, st['mu0'])
            pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, lam, st['pm0'])
        else:
            mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
        hh, aa, hbb = hi[cur], ai[cur], hb[cur]
        pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
    return sidx, pred

GRID = list(itertools.product([0.2, 0.32, 0.5, 0.7], [0.0, 0.2, 0.42, 0.6], [4, 8, 12, 20], [None, 10]))
EM = {Y: {t: q2r((r - .5) / len(RANK[Y]), Y) for t, r in RANK[Y].items()} for Y in SE5}
PRED = {}
ACTD = (D.hs - D.as_).values.astype(float)
for gi, c in enumerate(GRID):
    v = np.full(len(D), np.nan)
    for Y in SE5:
        sidx, pr = run_season(Y, c[0], c[1], EM[Y], c[2], c[3]); v[sidx] = pr
    PRED[c] = v
    if (gi + 1) % 16 == 0: print(f'  {gi + 1}/{len(GRID)}', flush=True)
LIVE, V1 = (0.32, 0.42, 8, None), (0.7, 0.0, 8, None)
# ελεγχος: V1 εδω = το v1 του backtest
assert np.allclose(PRED[V1][IDX][np.isin(SE, SE5)], M_V1[np.isin(SE, SE5)], atol=1e-6), 'V1 πρεπει να ταυτιζεται'
RSM = (D.phase.values == 'RS')
def rmse(v, s): m = RSM & (D.season.values == s); return np.sqrt(np.mean((ACTD - v)[m] ** 2))
def rmse_set(v, ss): m = RSM & np.isin(D.season.values, ss); return np.sqrt(np.mean((ACTD - v)[m] ** 2))
lab = lambda c: f'περσι {c[0]} · ειδικοι {c[1]} · K {c[2]} · εξοδος {"ποτε" if c[3] is None else f"μετα {c[3]}η"}'

P('=== LOSO επιλογη (ελαχιστο RMSE στις αλλες 4 σεζον) ===')
held = np.full(len(D), np.nan); picks = []
for Y in SE5:
    tr = [s for s in SE5 if s != Y]; best = min(GRID, key=lambda c: rmse_set(PRED[c], tr)); picks.append(best)
    m = D.season.values == Y; held[m] = PRED[best][m]
    P(f'  {Y[-4:]} εξω: [{lab(best)}] → RMSE {rmse(PRED[best], Y):.3f} · live {rmse(PRED[LIVE], Y):.3f} · v1 {rmse(PRED[V1], Y):.3f}')
from collections import Counter
for j, nm in enumerate(('περσι', 'ειδικοι', 'K', 'εξοδος')):
    P(f'  σταθεροτητα — {nm}: ' + ', '.join(f'{k}×{v}' for k, v in Counter(str(p[j]) for p in picks).most_common()))
P('')
P('=== ΑΚΡΙΒΕΙΑ (κανονικη περιοδος 2021-2025, ολα τα ματς) ===')
wins = sum(rmse(held, Y) < rmse(PRED[LIVE], Y) for Y in SE5)
for nm, v in (('LOSO επιλογη', held), ('live', PRED[LIVE]), ('v1 χωρις ειδικους', PRED[V1])):
    e10 = RSM & np.isin(D.season.values, SE5) & (GN <= 10)
    P(f'  {nm:18s} RMSE ολη {rmse_set(v, SE5):.3f} · αγων 1-10 {np.sqrt(np.mean((ACTD - v)[e10] ** 2)):.3f} · αγων 11+ {np.sqrt(np.mean((ACTD - v)[RSM & np.isin(D.season.values, SE5) & (GN > 10)] ** 2)):.3f}')
P(f'  LOSO καλυτερο απο live σε {wins}/5 σεζον')
P('')
P('=== ΠΩΣ ΑΛΛΑΖΕΙ ΤΟ RMSE (ολες οι 5 σεζον· καλυτερη τιμη των υπολοιπων ρυθμισεων για καθε τιμη) ===')
for j, nm, vals in ((0, 'βαρος περσι', [0.2, 0.32, 0.5, 0.7]), (1, 'βαρος ειδικων', [0.0, 0.2, 0.42, 0.6]), (2, 'K', [4, 8, 12, 20]), (3, 'εξοδος ειδικων', [None, 10])):
    P(f'  {nm:15s}: ' + ' · '.join(f'{"ποτε" if v is None and j == 3 else v}: {min(rmse_set(PRED[c], SE5) for c in GRID if c[j] == v):.3f}' for v in vals))
bestall = min(GRID, key=lambda c: rmse_set(PRED[c], SE5))
P(f'  καλυτερο σε ολες μαζι: [{lab(bestall)}] RMSE {rmse_set(PRED[bestall], SE5):.3f}')
P('  K με τα live βαρη (0.32/0.42, εξοδος ποτε): ' + ' · '.join(f'K {k}: {rmse_set(PRED[(0.32, 0.42, k, None)], SE5):.3f}' for k in (4, 8, 12, 20)))
P('  K με v1 (0.7/0): ' + ' · '.join(f'K {k}: {rmse_set(PRED[(0.7, 0.0, k, None)], SE5):.3f}' for k in (4, 8, 12, 20)))
P('')
P('=== ROI ΧΑΝΤΙΚΑΠ (Pinnacle closing, κανονικη περιοδος 2021-2025) ===')
def spb(v):
    b = bets(v[IDX], T_LO); return b[(b.mkt == 'sp') & b.season.isin(SE5)]
cell = lambda x: f'{x.p.mean()*100:+5.1f}% ({len(x)}, {x.p.sum():+.1f}u)'
R = {}
for nm, v in (('LOSO επιλογη', held), ('live', PRED[LIVE]), ('v1 χωρις ειδικους', PRED[V1])):
    b = spb(v); cells = []
    for thr in (0.05, 0.08, 0.10):
        x = b[b.edge >= thr]; pos = sum(1 for s in SE5 if len(x[x.season == s]) and x[x.season == s].p.mean() > 0)
        R[(nm, thr)] = (x.p.mean(), pos); cells.append(f'≥{thr*100:.0f}%: {cell(x)} {pos}/5')
    P(f'  {nm:18s} ' + ' | '.join(cells))
P('')
a_ = rmse_set(held, SE5) < rmse_set(PRED[LIVE], SE5) and wins >= 3
b_ = R[('LOSO επιλογη', 0.08)][0] >= R[('live', 0.08)][0] and R[('LOSO επιλογη', 0.08)][1] >= R[('live', 0.08)][1]
P(f'ΚΡΙΤΗΡΙΑ: (α) {"✓" if a_ else "✗"} ({wins}/5)  (β) {"✓" if b_ else "✗"} → {"Η LOSO ΕΠΙΛΟΓΗ ΑΝΤΙΚΑΘΙΣΤΑ ΤΟ LIVE" if a_ and b_ else "ΜΕΝΕΙ ΤΟ LIVE"}')
open('el_prior_grid_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
