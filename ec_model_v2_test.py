# -*- coding: utf-8 -*-
"""ec_model_v2_test.py — EUROCUP v2 = βασικο μοντελο + ΠΡΟΕΤΟΙΜΑΣΙΑ + ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ (1/10/2026, Στελιος: «προσθεσε αυτα που εχουμε σιγουρα,
δηλαδη φιλικα και εγχωρια — το θεμα ειναι τα εγχωρια απο ποιο σημειο και μετα»).
Βαση: ec_model_test.py παγωμενο (HL 9999, λ 4, carry .7, h 5, «τυχη» L).
ΠΡΟΕΤΟΙΜΑΣΙΑ (οπως el_preseason_prior): r = Σ[διαφορα (±20) − (R_ομαδας − R_αντιπαλου)]/(n+4) σε φιλικα & Super Cups (1 Αυγ … πρεμιερα EuroCup),
  R = κοινη κλιμακα περσινης σεζον (fs_bk_games). Αφετηρια += κ_pre·r·100/72 (μισο επιθεση/μισο αμυνα).
ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ (οπως el_domestic_rating_test, ταβανι 20): Δ = εγχωριο rating (ματς ΠΡΙΝ τη μερα) − 0.7×περσινο τελος.
  Αφετηρια += κ_dom·Δ·100/72 ΜΟΝΟ για ματς οπου η ομαδα εχει ηδη παιξει ≥ F−1 ματς EuroCup, F ∈ {1, 4, 7, 11}.
ΠΛΕΓΜΑ: κ_pre {0, .25, .5, 1} × κ_dom {0, .25, .5, .75, 1} × F {1, 4, 7, 11}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO στις U2021-U2025 (προετοιμασια υπαρχει απο 2021· επιλογη με RMSE διαφορας στις ΑΛΛΕΣ 4) →
  (1) RMSE εκτος δειγματος καλυτερο απο τη βαση σε ≥4/5 σεζον · (2) Κ2 vs Crown κλεισιμο: b ≥ 0.15, t ≥ 2, θετικη ≥4/5 · (3) ROI αναφορα.
Εξοδος: ec_model_v2_test_out.txt"""
import sys, json, math, re, unicodedata, datetime as dt, itertools
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
# ---- βαση EuroCup (D, μηχανη) ----
src = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
src = src.replace("B = json.load(open('el_box.json', encoding='utf-8'))",
                  "B = {k: v for k, v in json.load(open('el_players.json', encoding='utf-8')).items() if v.get('comp') == 'U'}")
NS = {}; exec(src, NS)
D, fit_eff, fit_pace, points, P, out = NS['D'], NS['fit_eff'], NS['fit_pace'], NS['points'], NS['P'], NS['out']
out.clear()
HL, LAM, CARRY, H, VAR = 9999, 4, 0.7, 5, 'L'
SEAS = sorted(D.season.unique())
ph_, pa_ = points(D, VAR); EH, EA = 100 * ph_ / D.poss.values, 100 * pa_ / D.poss.values
# ---- εγχωρια Δ (απο el_domestic_rating_test) ----
DOMNS = {}
exec(open('el_domestic_rating_test.py', encoding='utf-8').read().split('# ---- 2. αντιστοιχιση')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
     .replace("open('el_domestic_rating_test_out.txt', 'w'", "open('_unused_ec2.txt', 'w'"), DOMNS)
S20 = DOMNS['dom_series'](20)[0]; NAMES = DOMNS['NAMES']; tok = DOMNS['tok']; D0 = DOMNS['D0']
S0keys = list(S20.keys())
MAPD = {}
for Y in SEAS:
    es = 'E' + Y[1:]
    sub = D[D.season == Y]; tn = {}
    for r in sub.itertuples(): tn.setdefault(r.home, r.hname); tn.setdefault(r.away, r.aname)
    cands = [k for k in S0keys if k[0] == es]
    for code, nm in tn.items():
        te = tok(nm)
        sc = sorted([(len(te & tok(NAMES.get((L, t), ''))) / max(1, len(tok(NAMES.get((L, t), '')))), (es_, t, L)) for (es_, t, L) in cands], reverse=True)
        if sc and sc[0][0] >= 0.5: MAPD[(Y, code)] = sc[0][1]
def dshift(Y, code, dday):
    k = MAPD.get((Y, code))
    if not k or k not in S20: return 0.0
    v = 0.0
    for dd, x in S20[k]:
        if dd <= dday - 1: v = x
        else: break
    return v
P(f'EuroCup ματς {len(D)} · αντιστοιχιση με εγχωριο: ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in MAPD if k[0] == Y)}/{len(set(D[D.season == Y].home))}' for Y in SEAS))
# ---- προετοιμασια ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8')); PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
def common(y):
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    if not rows: return {}
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}
PRE = {}
for Y in SEAS:
    y = int(Y[1:])
    if f'EC_{y}' not in FG: continue
    C = common(y - 1); sub = D[D.season == Y]
    start = min(pd.Timestamp(t).date() for t in sub.t)
    FS2 = {}
    idx = {}
    for r in sub.itertuples(): idx.setdefault((int(r.hs), int(r.as_)), []).append(r)
    for e in FG.get(f'EC_{y}', []):
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        for r in idx.get((hs, as_), []):
            if abs((pd.Timestamp(r.t).date() - d).days) <= 1: FS2[e['hid']] = r.home; FS2[e['aid']] = r.away; break
    acc = {}
    for key, L in PS.items():
        for e in L:
            if not e.get('ts'): continue
            d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
            if not (dt.date(y, 8, 1) <= d < start): continue
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            for me, op, sg in ((e.get('hid'), e.get('aid'), 1), (e.get('aid'), e.get('hid'), -1)):
                code = FS2.get(me)
                if code and me in C and op in C: acc.setdefault(code, []).append(sg * m - (C[me] - C[op]))
    for code, L in acc.items(): PRE[(Y, code)] = sum(L) / (len(L) + 4.0)
P('προετοιμασια (ομαδες με r): ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in PRE if k[0] == Y)}' for Y in SEAS))
# ---- μηχανη με μετατοπισεις ----
dnum = np.array([(pd.Timestamp(t).tz_localize(None) - pd.Timestamp(D0)).days if pd.Timestamp(t).tzinfo else (pd.Timestamp(t) - pd.Timestamp(D0)).days for t in D.t])
GN = np.zeros(len(D), int)
for Y in SEAS:
    cnt = {}
    for i in np.where(D.season.values == Y)[0]:
        h_, a_ = D.home.values[i], D.away.values[i]
        GN[i] = max(cnt.get(h_, 0), cnt.get(a_, 0)); cnt[h_] = cnt.get(h_, 0) + 1; cnt[a_] = cnt.get(a_, 0) + 1
def run(kp, kd, F):
    preds = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
        pre = np.array([kp * PRE.get((s, t), 0.0) * 100 / 72 for t in teams])
        o0b = np.array([CARRY * prior.get(t, (0, 0, 0))[0] for t in teams]) + pre / 2
        d0b = np.array([CARRY * prior.get(t, (0, 0, 0))[1] for t in teams]) - pre / 2
        p0 = np.array([CARRY * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]; gn = GN[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            use_dom = kd > 0 and (gn[cur] >= F - 1).any()
            if use_dom:
                sh = np.array([kd * dshift(s, t, d) * 100 / 72 for t in teams]); o0 = o0b + sh / 2; d0 = d0b - sh / 2
            else:
                o0, d0 = o0b, d0b
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, LAM, mu0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, LAM, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            if use_dom and not (gn[cur] >= F - 1).all():          # μικτη μερα: ματς κατω απο F → χωρις εγχωρια
                if past.any():
                    mu_b, O_b, D_b = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0b, d0b, LAM, mu0)
                else:
                    mu_b, O_b, D_b = mu0, o0b, d0b
            for j in cur:
                if use_dom and gn[j] < F - 1:
                    m_, O_, D_ = mu_b, O_b, D_b
                else:
                    m_, O_, D_ = mu, O, Dd
                e_h = m_ + O_[hi[j]] + D_[ai[j]] + hb[j]; e_a = m_ + O_[ai[j]] + D_[hi[j]] - hb[j]
                preds[sidx[j]] = (pm + Pc[hi[j]] + Pc[ai[j]]) * (e_h - e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, eh, ea, hb, w, n, o0b, d0b, LAM, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, LAM, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds
act = (D.hs - D.as_).values.astype(float)
EVS = ['U2021', 'U2022', 'U2023', 'U2024', 'U2025']
def rm(v, ss): m = np.isin(D.season.values, ss) & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
GRID = [(kp, kd, F) for kp in (0, .25, .5, 1) for kd in (0, .25, .5, .75, 1) for F in (1, 4, 7, 11) if not (kd == 0 and F != 1)]
PRED = {}
for i, g in enumerate(GRID):
    PRED[g] = run(*g)
    if i % 10 == 0: print(f'  {i + 1}/{len(GRID)} …', flush=True)
base = PRED[(0, 0, 1)]
P(''); P('=== IN-SAMPLE RMSE διαφορας U2021-U2025 (καλυτερα 8) ===')
for g in sorted(PRED, key=lambda g: rm(PRED[g], EVS))[:8]: P(f'  κ_pre {g[0]} · κ_dom {g[1]} · απο αγων {g[2]}: {rm(PRED[g], EVS):.3f}')
P(f'  βαση: {rm(base, EVS):.3f}')
held = base.copy(); ch = []
for Y in EVS:
    tr = [s for s in EVS if s != Y]; g = min(PRED, key=lambda g: rm(PRED[g], tr)); ch.append(g); held[D.season.values == Y] = PRED[g][D.season.values == Y]
diffs = [rm(held, [Y]) - rm(base, [Y]) for Y in EVS]; w_ = sum(d < 0 for d in diffs)
P(''); P(f'=== LOSO: επιλογες {ch} ===')
P(f'  RMSE {rm(base, EVS):.3f} → {rm(held, EVS):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs) + f' → καλυτερο {w_}/5 {"ΠΕΡΝΑ (1)" if w_ >= 4 else "✗"}')
# ---- Κ2 & ROI vs Crown ----
EC = {}
exec(open('ec_model_test.py', encoding='utf-8').read().split("E = D.loc[sorted(MKT)].copy()")[0].split("# ---- αγορα: Crown απο Nowgoal ----")[1]
     .replace("D.t.values[i]", "D.t.values[i]"), dict(globals(), **{'MKT': None}), EC) if False else None
N = NormalDist(); Phi = N.cdf
SCH = {}
for sea in ('21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] == 21: ROWS[r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
MK = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
    for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
        for i in ix2.get((a_, b_), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
        if hit is not None: break
    if hit is None: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 11.5 * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        return (-L, -mu, o2, o1) if sw else (L, mu, o1, o2)
    MK[hit] = dict(o=conv(rows[0]), c=conv(rows[-1]))
def evaluate(v, lab):
    ii = [i for i in MK if D.season.values[i] in EVS and np.isfinite(v[i])]
    x = np.array([v[i] - MK[i]['c'][1] for i in ii]); z = np.array([act[i] - MK[i]['c'][1] for i in ii]); ss = np.array([D.season.values[i] for i in ii])
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = {Y: np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EVS}
    pos = sum(p > 0 for p in per.values())
    rr = {}
    for when in ('o', 'c'):
        R = []
        for i in ii:
            L, _, o1, o2 = MK[i][when]; m = v[i]
            if abs(L - round(L)) < 1e-9:
                pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
            else:
                pw = Phi((m + L) / 11.5); pl = 1 - pw
            pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e >= .08:
                vv = (act[i] + L) * side; R.append(((od - 1) if vv > 0 else (0 if vv == 0 else -1), D.season.values[i]))
        a = np.array([q[0] for q in R]); rr[when] = (len(a), a.mean() * 100 if len(a) else 0, a.sum(), sum(1 for Y in EVS if any(q[1] == Y for q in R) and np.mean([q[0] for q in R if q[1] == Y]) > 0))
    P(f'  {lab:22s} n {len(ii)} · Κ2 b {b:+.3f} (t {b/se:+.1f}) · θετικη {pos}/5 [' + ' '.join(f'{k[-2:]}:{p:+.2f}' for k, p in per.items()) + ']'
      + ('  ΠΕΡΝΑ (2)' if b >= .15 and b / se >= 2 and pos >= 4 else '  ✗')
      + f' · ROI ανοιγμα {rr["o"][1]:+.1f}% ({rr["o"][0]}, {rr["o"][2]:+.1f} μον., {rr["o"][3]}/5) · κλεισιμο {rr["c"][1]:+.1f}% ({rr["c"][0]}, {rr["c"][2]:+.1f} μον., {rr["c"][3]}/5)')
P(''); P('=== Κ2 & ROI χαντικαπ vs Crown (U2021-U2025) ===')
evaluate(base, 'ΒΑΣΗ')
evaluate(held, 'v2 (LOSO)')
open('ec_model_v2_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
