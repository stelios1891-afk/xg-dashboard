# -*- coding: utf-8 -*-
"""el_hcap_big_test.py — ΜΕΓΑΛΟ ΤΕΣΤ ΧΑΝΤΙΚΑΠ: ολες οι ρυθμισεις μαζι (25/9/2026, αιτημα Στελιου «ξεκινα το 3»).
Μοντελο = live χαντικαπ (walk-forward μεσα στη σεζον). Προηγουμενες σεζον χτιζονται με τις ιδιες HL/τυχη/εδρα/K και περσι 0.7 (οπως live).
ΠΛΕΓΜΑ: περσι {0.32, 0.5, 0.7} × ειδικοι {0, 0.42} × K {8, 12} × HL {60, 120, ποτε} × εδρα {4, 5, 6} × τυχη {0.25, 0.5, 0.75}
        × ανοιγμα απο 7η αγωνιστικη {1.0, 1.1, 1.2} = 972. Live = 0.32/0.42/8/120/6/0.5/1.0.
ΣΕΖΟΝ-ΤΕΣΤ 2021-2025 (ειδικοι BasketNews)· E(θεση) LOSO· Pinnacle closing· κανονικη περιοδος.
ΔΥΟ LOSO ΕΠΙΛΟΓΕΣ: (i) ελαχιστο RMSE διαφορας (ολα τα ματς RS) στις αλλες 4 · (ii) μεγιστο ROI χαντικαπ edge ≥8% στις αλλες 4.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΜΙΑ εκτελεση): μια επιλογη αντικαθιστα το live αν στα held-out: RMSE μικροτερο συνολικα ΚΑΙ σε ≥3/5 σεζον
  ΚΑΙ ROI ≥8% μεγαλυτερο με πιθανοτητα ≥80% (bootstrap ματς, 2000 δειγματα).
Εξοδος: el_hcap_big_test_out.txt"""
import sys, math, itertools
import numpy as np, pandas as pd
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
_o6 = []
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
exec(ex.split('base, ENDS = run_x(0.0)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''))
out = _o6
def P(s=''):
    print(s, flush=True); out.append(str(s))
gv = {}
exec(open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), gv)
TE = {s: gv['team_end'](s) for s in gv['SEAS']}
def q2r(q, excl):
    ends = [np.sort(np.array(list(TE[s].values())))[::-1] for s in gv['SEAS'] if s >= 'E2018' and s != excl]
    return float(np.mean([np.interp(q, (np.arange(len(e)) + .5) / len(e), e) for e in ends]))
SE5 = list(RANK)
EM = {Y: {t: q2r((r - .5) / len(RANK[Y]), Y) for t, r in RANK[Y].items()} for Y in SE5}
dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
rs_all = D[D.phase == 'RS'].sort_values('date'); cnt = {}; GN = np.full(len(D), 99)
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    GN[D.index.get_loc(i)] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
LUCK = {}
for lw in (0.25, 0.5, 0.75):
    a, b = luck_pts(lw); LUCK[lw] = (np.asarray(a, float), np.asarray(b, float))

def ends_for(HL, h, lw, lam):
    """κατασταση στην αρχη καθε σεζον (περσινο τελος) με αυτες τις ρυθμισεις, περσι 0.7, χωρις ειδικους (οπως live)."""
    EH, EA = LUCK[lw]; START = {}; prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        START[s] = dict(prior=dict(prior), mu0=mu0, pm0=pm0)
        o0 = np.array([0.7 * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([0.7 * prior.get(t, (0, 0, 0))[1] for t in teams]); p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, h / 2); dn = dnum[sidx]
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return START

def run_season(s, st, wt, we, Emap, lam, HL, h, lw):
    EH, EA = LUCK[lw]; prior = st['prior']
    sidx = np.where(D.season.values == s)[0]
    teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    e = np.array([Emap.get(t, 0.0) for t in teams]) * we
    o0 = np.array([wt * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2; d0 = np.array([wt * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2
    p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
    hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
    hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, h / 2); dn = dnum[sidx]
    pred = np.full(len(sidx), np.nan)
    for d in np.unique(dn):
        past = dn < d; cur = np.where(dn == d)[0]
        if past.any():
            w = 0.5 ** ((d - dn[past]) / HL)
            mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, lam, st['mu0'])
            pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, lam, st['pm0'])
        else:
            mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
        hh, aa, hbb = hi[cur], ai[cur], hb[cur]
        pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
    return sidx, pred

ENG = list(itertools.product([0.32, 0.5, 0.7], [0.0, 0.42], [8, 12], [60, 120, 9999], [4.0, 5.0, 6.0], [0.25, 0.5, 0.75]))
STRETCH = [1.0, 1.1, 1.2]
BASEP = {}
cache_end = {}
for gi, (wt, we, lam, HL, h, lw) in enumerate(ENG):
    k = (HL, h, lw, lam)
    if k not in cache_end: cache_end[k] = ends_for(HL, h, lw, lam)
    v = np.full(len(D), np.nan)
    for Y in SE5:
        sidx, pr = run_season(Y, cache_end[k][Y], wt, we, EM[Y], lam, HL, h, lw); v[sidx] = pr
    BASEP[(wt, we, lam, HL, h, lw)] = v
    if (gi + 1) % 27 == 0: print(f'  {gi + 1}/{len(ENG)}', flush=True)
PRED = {}
for c, v in BASEP.items():
    for sf in STRETCH:
        PRED[c + (sf,)] = np.where(GN >= 7, v * sf, v)
GRID = list(PRED)
LIVE = (0.32, 0.42, 8, 120, 6.0, 0.5, 1.0); V1 = (0.7, 0.0, 8, 120, 6.0, 0.5, 1.0)
assert np.allclose(PRED[V1][IDX][np.isin(SE, SE5)], M_V1[np.isin(SE, SE5)], atol=1e-6), 'V1 πρεπει να ταυτιζεται με το v1'
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
SQ = {c: (ACTD - v) ** 2 for c, v in PRED.items()}
def rmse(c, ss): m = RSM & np.isin(SEASD, ss); return np.sqrt(np.mean(SQ[c][m]))
# ---- ROI: στοιχηματα χαντικαπ ανα ματς (για γρηγορη αθροιση) ----
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
v_home = AC + L_
def bets_for(c, thr=0.08):
    m = PRED[c][IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    v = v_home * side; p = np.where(v > 0, od - 1, np.where(v == 0, 0.0, -1.0))
    sel = e >= thr
    return p, sel
def roi(c, ss, thr=0.08):
    p, sel = bets_for(c, thr); m = sel & np.isin(SJ, ss); return p[m].mean() if m.any() else -9, p, sel

P(f'πλεγμα {len(GRID)} συνδυασμοι · ελεγχος: v1 ταυτιζεται ✓')
P('')
res = {}
for track, key in (('(i) ακριβεια', 'rmse'), ('(ii) ROI ≥8%', 'roi')):
    held_sq = np.full(len(D), np.nan); held_p = np.zeros(len(jj)); held_sel = np.zeros(len(jj), bool); picks = []
    for Y in SE5:
        tr = [s for s in SE5 if s != Y]
        best = min(GRID, key=lambda c: rmse(c, tr)) if key == 'rmse' else max(GRID, key=lambda c: roi(c, tr)[0])
        picks.append(best)
        m = SEASD == Y; held_sq[m] = SQ[best][m]
        _, p, sel = roi(best, [Y]); mj = SJ == Y; held_p[mj] = p[mj]; held_sel[mj] = sel[mj]
    res[track] = dict(sq=held_sq, p=held_p, sel=held_sel, picks=picks)
    P(f'=== LOSO {track}: επιλογες ανα σεζον (περσι · ειδικοι · K · HL · εδρα · τυχη · ανοιγμα) ===')
    for Y, c in zip(SE5, picks): P(f'  {Y[-4:]} εξω: {c}')
    for j, nm in enumerate(('περσι', 'ειδικοι', 'K', 'HL', 'εδρα', 'τυχη', 'ανοιγμα')):
        P(f'    σταθεροτητα {nm}: ' + ', '.join(f'{k}×{v}' for k, v in Counter(str(p[j]) for p in picks).most_common()))
    P('')
_, pL, sL = roi(LIVE, SE5); _, pV, sV = roi(V1, SE5)
def summary(nm, sq, p, sel):
    m5 = RSM & np.isin(SEASD, SE5)
    per = {Y: np.sqrt(np.mean(sq[RSM & (SEASD == Y)])) for Y in SE5}
    x = p[sel]; pos = sum(1 for Y in SE5 if p[sel & (SJ == Y)].mean() > 0)
    e10 = m5 & (GN <= 10)
    P(f'  {nm:20s} RMSE {np.sqrt(np.mean(sq[m5])):.3f} (1-10 {np.sqrt(np.mean(sq[e10])):.3f}) · ROI ≥8% {x.mean()*100:+.1f}% ({sel.sum()}, {x.sum():+.1f}u) {pos}/5 | ανα σεζον RMSE ' + ' '.join(f'{Y[-2:]}:{per[Y]:.2f}' for Y in SE5))
    return per
P('=== ΑΠΟΤΕΛΕΣΜΑΤΑ (held-out 2021-2025) ===')
perL = summary('live', SQ[LIVE], pL, sL); summary('v1 χωρις ειδικους', SQ[V1], pV, sV)
rng = np.random.default_rng(7); G_ = len(jj); BOOT = rng.integers(0, G_, size=(2000, G_))
decisions = {}
for track in res:
    r = res[track]; per = summary(f'LOSO {track}', r['sq'], r['p'], r['sel'])
    wins = sum(per[Y] < perL[Y] for Y in SE5); m5 = RSM & np.isin(SEASD, SE5)
    better_rmse = np.sqrt(np.mean(r['sq'][m5])) < np.sqrt(np.mean(SQ[LIVE][m5])) and wins >= 3
    # bootstrap ROI διαφορα (ιδια ματς)
    diffs = []
    for idx in BOOT:
        a_p, a_s, b_p, b_s = r['p'][idx], r['sel'][idx], pL[idx], sL[idx]
        diffs.append((a_p[a_s].mean() if a_s.any() else 0) - (b_p[b_s].mean() if b_s.any() else 0))
    prob = float(np.mean(np.array(diffs) > 0))
    decisions[track] = better_rmse and prob >= 0.8
    P(f'      vs live: RMSE καλυτερο σε {wins}/5 · πιθανοτητα ROI ≥8% μεγαλυτερο απο live: {prob*100:.0f}% → {"ΑΝΤΙΚΑΘΙΣΤΑ" if decisions[track] else "οχι"}')
diffs = []
for idx in BOOT:
    diffs.append(pV[idx][sV[idx]].mean() - pL[idx][sL[idx]].mean())
P(f'  (αναφορα) πιθανοτητα ROI ≥8% v1 > live: {np.mean(np.array(diffs) > 0)*100:.0f}% · RMSE διαφορα ζευγαρωτα live − v1: {np.mean(SQ[LIVE][RSM & np.isin(SEASD, SE5)] - SQ[V1][RSM & np.isin(SEASD, SE5)]):+.2f} (τετρ.)')
P('')
P('=== ΕΠΙΔΡΑΣΗ ΚΑΘΕ ΡΥΘΜΙΣΗΣ (ολες οι 5 σεζον): μεση τιμη πανω σε ολους τους υπολοιπους συνδυασμους ===')
names = ('περσι', 'ειδικοι', 'K', 'HL', 'εδρα', 'τυχη', 'ανοιγμα')
allr = {c: rmse(c, SE5) for c in GRID}; allroi = {c: roi(c, SE5)[0] for c in GRID}
for j, nm in enumerate(names):
    vals = sorted({c[j] for c in GRID})
    P(f'  {nm:8s}: ' + ' · '.join(f'{v}: RMSE {np.mean([allr[c] for c in GRID if c[j] == v]):.3f} / ROI {np.mean([allroi[c] for c in GRID if c[j] == v])*100:+.1f}%' for v in vals))
top = sorted(GRID, key=lambda c: allr[c])[:5]
P('  καλυτεροι 5 σε ακριβεια (ολες μαζι): ' + ' | '.join(f'{c} {allr[c]:.3f} / {allroi[c]*100:+.1f}%' for c in top))
top = sorted(GRID, key=lambda c: -allroi[c])[:5]
P('  καλυτεροι 5 σε ROI ≥8% (ολες μαζι — υπερ-προσαρμογη!): ' + ' | '.join(f'{c} {allr[c]:.3f} / {allroi[c]*100:+.1f}%' for c in top))
P('')
P('ΑΠΟΦΑΣΗ: ' + ('; '.join(f'{t} → {"ΑΝΤΙΚΑΘΙΣΤΑ το live" if d else "δεν περνα"}' for t, d in decisions.items())))
open('el_hcap_big_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
