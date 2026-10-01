# -*- coding: utf-8 -*-
"""ec_totals_test.py — EuroCup ΣΥΝΟΛΑ ΠΟΝΤΩΝ (1/10/2026, Στελιος «παμε στο τεστ των συνολων»).
Αφετηρια: ec_model_test (μηχανη χαντικαπ, τυχη 50%, μ_w 5, carry .7) στα συνολα: Κ2 b +0.191 (t 1.5) ✗ · ROI ανοιγμα over −10% / under −5%.
Ιδεες απο την Ευρωλιγκα (εκει περασαν): μηχανη συνολων v2 (τυχη 25%, επιπεδο λιγκας σχεδον σταθερο μ_w 50) + καμπυλη σεζον (σκορ ανεβαινουν με τον αριθμο αγωνα).
ΠΛΕΓΜΑ μηχανης: τυχη w {.25, .5, 1 (ωμο)} × περσι {.2, .5, .7} × μ_w {5, 50} × HL {60, 9999} × λ {4, 8}  (εδρα 5).
  Καμπυλη: συνολο += a + b·GN (GN = αριθμος αγωνα σεζον, max των 2 ομαδων) — a, b απο τις ΑΛΛΕΣ σεζον (υπολοιπο πραγματικο − μοντελο).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO επιλογη με RMSE συνολου στις U2018-U2025 (8 σεζον, χωρις αποδοσεις) →
  Κ2 vs Crown κλεισιμο (U2020-U2025): b ≥ 0.15 ΚΑΙ t ≥ 2 ΚΑΙ b > 0 σε ≥4/6 σεζον = ΠΕΡΝΑ. ROI over/under edge ≥8% (σ 16.7) ανοιγμα/κλεισιμο = αναφορα.
  Καμπυλη: μπαινει αν RMSE καλυτερο σε ≥6/8 σεζον.
Εξοδος: ec_totals_test_out.txt"""
import sys, json, math, itertools, io, contextlib, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
src = src.replace("B = json.load(open('el_box.json', encoding='utf-8'))", "B = {k: v for k, v in json.load(open('ec_box.json', encoding='utf-8')).items() if v.get('season') != 'U2026'}")
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("open('el_model_test_out.txt', 'w'", "open('_unused_ect.txt', 'w'")
NS = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(src, NS)
D, fit_pace, lg_prev = NS['D'], NS['fit_pace'], NS['lg_prev']
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
SEAS = sorted(D.season.unique()); H = 5.0
P(f'EuroCup ματς {len(D)} · σεζον {SEAS[0]}–{SEAS[-1]}')
def luck_eff(w):
    res = []
    for side in ('h', 'a'):
        p3l = np.array([lg_prev(s)['p3'] for s in D.season]); ftl = np.array([lg_prev(s)['ft'] for s in D.season])
        m3, a3, mf, af = (D[f'{side}_{c}'].values.astype(float) for c in ('fgm3', 'fga3', 'ftm', 'fta'))
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        res.append(100 * (D[f'{side}_pts'].values - 3 * m3 + 3 * a3 * (w * p3g + (1 - w) * p3l) - mf + af * (w * ftg + (1 - w) * ftl)) / D.poss.values)
    return res[0], res[1]
def fit_eff_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, mu_w):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(mu_w); y[-1] = math.sqrt(mu_w) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]
dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
GN = np.zeros(len(D), int)
for Y in SEAS:
    cnt = {}
    for i in np.where(D.season.values == Y)[0]:
        h_, a_ = D.home.values[i], D.away.values[i]
        cnt[h_] = cnt.get(h_, 0) + 1; cnt[a_] = cnt.get(a_, 0) + 1; GN[i] = max(cnt[h_], cnt[a_])
EFF = {w: luck_eff(w) for w in (.25, .5, 1.0)}
def run(w, carry, mu_w, HL, lam):
    EH, EA = EFF[w]; preds = np.full((len(D), 2), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff_mu(hi[past], ai[past], eh[past], ea[past], hb[past], ww, n, o0, d0, lam, mu0, mu_w)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], ww, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            for j in cur:
                e_h = mu + O[hi[j]] + Dd[ai[j]] + hb[j]; e_a = mu + O[ai[j]] + Dd[hi[j]] - hb[j]; poss = pm + Pc[hi[j]] + Pc[ai[j]]
                preds[sidx[j]] = (poss * (e_h - e_a) / 100, poss * (e_h + e_a) / 100)
        ww = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff_mu(hi, ai, eh, ea, hb, ww, n, o0, d0, lam, mu0, mu_w)
        pm, Pc = fit_pace(hi, ai, pc, ww, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds
tot = (D.hs + D.as_).values.astype(float)
EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']; EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
seasn = D.season.values
def rm(v, ss, msk=None):
    m = np.isin(seasn, ss) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((tot - v)[m] ** 2)))
GRID = list(itertools.product((.25, .5, 1.0), (.2, .5, .7), (5, 50), (60, 9999), (4, 8)))
PRED = {}
for i, g in enumerate(GRID):
    PRED[g] = run(*g)[:, 1]
    if i % 12 == 0: print(f'  {i + 1}/{len(GRID)} …', flush=True)
REF = (.5, .7, 5, 9999, 4)          # = ec_model_test (σημερινη μηχανη)
P(''); P('=== IN-SAMPLE RMSE συνολου U2018-U2025 (καλυτερα 8) ===')
for g in sorted(PRED, key=lambda g: rm(PRED[g], EV8))[:8]: P(f'  τυχη {g[0]} · περσι {g[1]} · μ_w {g[2]} · HL {g[3]} · λ {g[4]}: {rm(PRED[g], EV8):.3f}')
P(f'  σημερα {REF}: {rm(PRED[REF], EV8):.3f}')
# ---- LOSO μηχανη ----
held = np.full(len(D), np.nan); ch = []
for Y in EV8:
    tr = [x for x in EV8 if x != Y]; g = min(PRED, key=lambda g: rm(PRED[g], tr)); ch.append(g); held[seasn == Y] = PRED[g][seasn == Y]
P(''); P(f'=== LOSO μηχανη · επιλογες {ch} ===')
d = [rm(held, [Y]) - rm(PRED[REF], [Y]) for Y in EV8]
P(f'  RMSE {rm(PRED[REF], EV8):.3f} → {rm(held, EV8):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV8, d)) + f' → καλυτερο {sum(x < 0 for x in d)}/8')
# ---- καμπυλη σεζον (LOSO a, b) ----
def curve(base):
    v = base.copy(); ab = []
    for Y in EV8 + ['U2017']:
        tr = [x for x in EV8 if x != Y]; m = np.isin(seasn, tr) & np.isfinite(base)
        b, a = np.polyfit(GN[m], (tot - base)[m], 1); ab.append((round(a, 2), round(b, 3)))
        v[seasn == Y] = base[seasn == Y] + a + b * GN[seasn == Y]
    return v, ab
HC, ab = curve(held)
d2 = [rm(HC, [Y]) - rm(held, [Y]) for Y in EV8]
P(f'  + καμπυλη (a, b ανα σεζον {ab[:8]}): RMSE {rm(held, EV8):.3f} → {rm(HC, EV8):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV8, d2))
  + f' → καλυτερο {sum(x < 0 for x in d2)}/8' + ('  ΜΠΑΙΝΕΙ' if sum(x < 0 for x in d2) >= 6 else '  ✗'))
REFC, _ = curve(PRED[REF])
# ---- μεροληψια ανα φαση ----
P(''); P('=== ΜΕΡΟΛΗΨΙΑ (πραγματικο − προβλεψη, ποντοι) ανα φαση σεζον · U2018-25 ===')
for lab, m in (('αγων 1-3', GN <= 3), ('4-6', (GN >= 4) & (GN <= 6)), ('7-10', (GN >= 7) & (GN <= 10)), ('11-18', (GN >= 11) & (GN <= 18)), ('19+', GN >= 19)):
    mm = np.isin(seasn, EV8) & m
    P(f'  {lab:8s} n {mm.sum():4d} · σημερα {np.mean((tot - PRED[REF])[mm]):+.2f} · LOSO {np.mean((tot - held)[mm]):+.2f} · LOSO+καμπυλη {np.mean((tot - HC)[mm]):+.2f}')
# ---- αγορα: Crown συνολα ----
N = NormalDist(); Phi = N.cdf
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] == 23: ROWS[r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
MK = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
    for key_ in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
        for i in ix2.get(key_, []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit = i; break
        if hit is not None: break
    if hit is None: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        oo, ou = 1 + x[2], 1 + x[3]; ph = (1 / oo) / (1 / oo + 1 / ou)
        return (float(x[1]), oo, ou, float(x[1]) + 16.7 * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)))
    MK[hit] = dict(o=conv(rows[0]), c=conv(rows[-1]))
MC = np.full(len(D), np.nan); MO = np.full(len(D), np.nan)
for i in MK: MC[i] = MK[i]['c'][3]; MO[i] = MK[i]['o'][3]
P(''); P(f'=== ΑΓΟΡΑ (Crown, U2020-25): {sum(1 for i in MK if seasn[i] in EVM)} ματς ===')
def cov(mu, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((mu + L - 0.5) / s); pl = Phi((-mu - L - 0.5) / s); return pw, 1 - pw - pl
    return Phi((mu + L) / s), 0.0
def evaluate(v, lab, msk=None):
    ii = [i for i in MK if seasn[i] in EVM and np.isfinite(v[i]) and (msk is None or msk[i])]
    x = np.array([v[i] - MC[i] for i in ii]); z = np.array([tot[i] - MC[i] for i in ii]); ss = np.array([seasn[i] for i in ii])
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = {Y: np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EVM if (ss == Y).sum() > 20}
    pos = sum(p > 0 for p in per.values()); ok = b >= .15 and b / se >= 2 and pos >= 4
    rmse_m = math.sqrt(np.mean((tot[ii] - v[ii]) ** 2)); rmse_k = math.sqrt(np.mean((tot[ii] - MC[ii]) ** 2))
    P(f'  {lab:34s} n {len(ii)} · RMSE μοντ. {rmse_m:.2f} / αγορα {rmse_k:.2f} · Κ2 b {b:+.3f} (t {b/se:+.1f}) θετικη {pos}/{len(per)} ['
      + ' '.join(f'{k[-2:]}:{p:+.2f}' for k, p in per.items()) + ']' + ('  ΠΕΡΝΑ' if ok else '  ✗'))
    for when in ('o', 'c'):
        R = {'over': [], 'under': []}
        for i in ii:
            T, oo, ou, _ = MK[i][when]; po, pq = cov(v[i], -T, 16.7); pu = 1 - po - pq
            eo, eu = po * oo + pq - 1, pu * ou + pq - 1
            if max(eo, eu) >= .08:
                ov = eo >= eu; vv = (tot[i] - T) * (1 if ov else -1); od = oo if ov else ou
                R['over' if ov else 'under'].append(((od - 1) if vv > 0 else (0 if vv == 0 else -1), seasn[i]))
        cells = []
        for k, L in R.items():
            a = np.array([q[0] for q in L]); ys = sorted(set(q[1] for q in L))
            pos_ = sum(1 for Y in ys if np.mean([q[0] for q in L if q[1] == Y]) > 0)
            cells.append(f'{k} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos_}/{len(ys)})')
        P(f'      ROI {"ανοιγμα " if when == "o" else "κλεισιμο"}: ' + ' · '.join(cells))
    return ok
evaluate(PRED[REF], 'ΣΗΜΕΡΙΝΗ μηχανη (ec_model_test)')
evaluate(REFC, 'σημερινη + καμπυλη')
evaluate(held, 'LOSO μηχανη')
evaluate(HC, 'LOSO μηχανη + καμπυλη')
P(''); P('=== ανα φαση (LOSO μηχανη + καμπυλη) ===')
for lab, m in (('αγων 1-6', GN <= 6), ('7-10', (GN >= 7) & (GN <= 10)), ('11+', GN >= 11)):
    evaluate(HC, lab, m)
P(''); P('=== μεροληψια αγορας (πραγματικο − αγορα κλεισιμο) ανα φαση · U2020-25 ===')
for lab, m in (('αγων 1-6', GN <= 6), ('7-10', (GN >= 7) & (GN <= 10)), ('11+', GN >= 11)):
    mm = np.isin(seasn, EVM) & m & np.isfinite(MC)
    P(f'  {lab:8s} n {mm.sum():4d} · αγορα {np.mean((tot - MC)[mm]):+.2f} · μοντελο (LOSO+καμπυλη) {np.mean((tot - HC)[mm]):+.2f}')
open('ec_totals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
