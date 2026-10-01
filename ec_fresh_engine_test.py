# -*- coding: utf-8 -*-
"""ec_fresh_engine_test.py — EuroCup ΑΠΟ ΤΗΝ ΑΡΧΗ, βημα 1: ΞΑΝΑΡΥΘΜΙΣΗ ΜΗΧΑΝΗΣ στο ιδιο το EuroCup με ολα τα φετινα συστατικα μεσα
(1/10/2026, Στελιος: «να αναλυσεις το eurocup σαν καινουργιο, χωρις αποφασεις βαση της Ευρωλιγκας»).
Σημερινο live ec1: HL 9999 · λ 4 · εδρα 5 · τυχη .5 · μ_w 5 (ρυθμισμενα ΜΟΝΟ U2017-19, χωρις εγχωρια/ειδικους) · περσι .2 · ειδικοι 4 · φιλικα .5 · εγχωρια κ1.
ΣΤΑΔΙΟ Α: HL {30,60,120,9999} × λ {2,4,8,12} × εδρα {3..7} × τυχη {1,.5,.25} × μ_w {5,50} (περσι/ειδικοι/φιλικα σταθερα = live).
ΣΤΑΔΙΟ Β: περσι {0,.2,.35,.5} × ειδικοι {3,4,5} × φιλικα {0,.5,1} πανω στις 5 καλυτερες μηχανες του Α + τη live.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO σε ΟΛΟ το πλεγμα, U2018-U2025, επιλογη με RMSE διαφορας ΟΛΩΝ των ματς των αλλων 7 σεζον →
  ΑΛΛΑΓΗ αν καλυτερο απο το live σε ≥6/8 σεζον. Αναφορα: πρωτα 6 ματς · Κ2/ROI vs Crown (σ 11.5 προσωρινα — βημα 2 θα το κρινει).
Εξοδος: ec_fresh_engine_out.txt · ec_fresh_engine_preds.pkl"""
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
     .replace("open('el_domestic_rating_test_out.txt', 'w'", "open('_unused_ec4.txt', 'w'"), DOMNS)
tok = DOMNS['tok']; D0 = DOMNS['D0']
# ---- (α) επιπλεον πρωταθληματα απο Flashscore, σε μορφη bk_domestic ----
XT = json.load(open('fs_bk_extra.json', encoding='utf-8')); XID = {}
for key, L in XT.items():
    lg, y = key.split('_'); y = int(y); kk = f'{lg}_{y % 100:02d}-{(y + 1) % 100:02d}'
    teams, games = {}, []
    for e in L:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        if not e.get('hid') or not e.get('aid') or not e.get('ts'): continue
        ih = XID.setdefault((lg, e['hid']), 900000 + len(XID)); ia = XID.setdefault((lg, e['aid']), 900000 + len(XID))
        teams[str(ih)] = e['home']; teams[str(ia)] = e['away']
        games.append([e['id'], dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), ih, ia, str(hs), str(as_), 1])
    if games: DOMNS['DOM'][kk] = dict(teams=teams, games=games)
DOMNS['LEAGUES'][:] = sorted({k.split('_')[0] for k in DOMNS['DOM']})
S20, NAMES = DOMNS['dom_series'](20)
# ---- (β) σταθερη αντιστοιχιση (Nowgoal με παλια ονοματα χορηγων) ----
MANUAL = {'TOR': ('LBA', 4730), 'BRE': ('LBA', 3936), 'UNK': ('VTB', 942), 'DAR': ('TBL', 1098), 'GAL': ('TBL', 1010),
          'BES': ('TBL', 1127), 'PAI': ('LNB', 915), 'MAN': ('ACB', 1815), 'PAT': ('GBL', 5413)}
S0keys = list(S20.keys())
MAPD = {}
for Y in SEAS:
    es = 'E' + Y[1:]
    sub = D[D.season == Y]; tn = {}
    for r in sub.itertuples(): tn.setdefault(r.home, r.hname); tn.setdefault(r.away, r.aname)
    cands = [k for k in S0keys if k[0] == es]
    for code, nm in tn.items():
        if code in MANUAL and (es, MANUAL[code][1], MANUAL[code][0]) in S20:
            MAPD[(Y, code)] = (es, MANUAL[code][1], MANUAL[code][0]); continue
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
def run(kp, kd, F, kx=0.0, XS=None):
    preds = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
        pre = np.array([(kp * PRE.get((s, t), 0.0) + kx * (XS or {}).get((s, t), 0.0)) * 100 / 72 for t in teams])
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

import functools, itertools, sys as _sys
EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
seasn = D.season.values
LGP = NS['lg_prev']
# ---- ειδικοι (καταταξεις + αποδοσεις νικητη, οπως live) ----
EX = json.load(open('ec_expert.json', encoding='utf-8')); OR = json.load(open('ec_outrights.json', encoding='utf-8')); _nd = NormalDist()
ZC = {}
for S, tm in EX.items():
    od = {c: d['odds'] for c, d in tm.items() if 'odds' in d}
    use_o = S in OR and OR[S].get('after_round', 0) <= 1 and len(od) >= 0.8 * len(tm)
    if use_o:
        lv = {c: -math.log(o) for c, o in od.items()}; m_, s_ = np.mean(list(lv.values())), np.std(list(lv.values()))
    for c, d in tm.items():
        zz = [_nd.inv_cdf(1 - (d[k] - .5) / d[k + '_n']) for k in ('EH', 'TTC') if k in d] + ([(lv[c] - m_) / s_] if use_o and c in lv else [])
        if zz: ZC[(S, c)] = float(np.mean(zz))
# ---- τυχη με βαρος w (1 = ωμο, .5 = 'L', .25) ----
def luck_eff(w):
    res = []
    for side in ('h', 'a'):
        p3l = np.array([LGP(s)['p3'] for s in D.season]); ftl = np.array([LGP(s)['ft'] for s in D.season])
        m3, a3, mf, af = (D[f'{side}_{c}'].values.astype(float) for c in ('fgm3', 'fga3', 'ftm', 'fta'))
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        res.append(100 * (D[f'{side}_pts'].values - 3 * m3 + 3 * a3 * (w * p3g + (1 - w) * p3l) - mf + af * (w * ftg + (1 - w) * ftl)) / D.poss.values)
    return res[0], res[1]
EFF = {w: luck_eff(w) for w in (1.0, .5, .25)}
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
@functools.lru_cache(maxsize=None)
def dsh(s, t, d): return dshift(s, t, d)
def run2(HLv, lamv, hv, w, muw, carry, kx, kp):
    EH_, EA_ = EFF[w]; preds = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH_.mean() + EA_.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, hv / 2)
        ex = np.array([(kp * PRE.get((s, t), 0.0) + kx * ZC.get((s, t), 0.0)) * 100 / 72 for t in teams])
        o0b = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]) + ex / 2
        d0b = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams]) - ex / 2
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH_[sidx]; ea = EA_[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            sh = np.array([dsh(s, t, int(d)) * 100 / 72 for t in teams]); o0 = o0b + sh / 2; d0 = d0b - sh / 2
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HLv)
                mu, O, Dd = fit_eff_mu(hi[past], ai[past], eh[past], ea[past], hb[past], ww, n, o0, d0, lamv, mu0, muw)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], ww, n, p0, lamv, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            for j in cur:
                e_h = mu + O[hi[j]] + Dd[ai[j]] + hb[j]; e_a = mu + O[ai[j]] + Dd[hi[j]] - hb[j]
                preds[sidx[j]] = (pm + Pc[hi[j]] + Pc[ai[j]]) * (e_h - e_a) / 100
        ww = 0.5 ** ((dn.max() - dn) / HLv)
        mu, O, Dd = fit_eff_mu(hi, ai, eh, ea, hb, ww, n, o0b, d0b, lamv, mu0, muw)
        pm, Pc = fit_pace(hi, ai, pc, ww, n, p0, lamv, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds
def rmm(v, ss, msk=None):
    m = np.isin(seasn, ss) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)          # σημερινο live ec1
import time as _t
_t0 = _t.time()
base_live = run2(*LIVE)
P(''); P(f'live ec1 {LIVE}: RMSE ολα {rmm(base_live, EV8):.3f} · πρωτα 6 {rmm(base_live, EV8, GN <= 5):.3f} · (1 run {_t.time() - _t0:.1f}s)')
STAGE = _sys.argv[1] if len(_sys.argv) > 1 else 'A'
PRED = {LIVE: base_live}
if STAGE in ('A', 'AB'):
    GA = [(HLv, lamv, hv, w, muw, .2, 4.0, .5) for HLv, lamv, hv, w, muw in itertools.product((30, 60, 120, 9999), (2, 4, 8, 12), (3, 4, 5, 6, 7), (1.0, .5, .25), (5, 50))]
    for i, g in enumerate(GA):
        if g not in PRED: PRED[g] = run2(*g)
        if i % 40 == 0: print(f'  A {i + 1}/{len(GA)} … ({_t.time() - _t0:.0f}s)', flush=True)
    bestA = min(GA, key=lambda g: rmm(PRED[g], EV8))
    P(''); P('=== ΣΤΑΔΙΟ Α (μηχανη, περσι .2/ειδικοι 4/φιλικα .5 σταθερα) · IN-SAMPLE RMSE ολα U2018-25 (καλυτερα 10) ===')
    for g in sorted(GA, key=lambda g: rmm(PRED[g], EV8))[:10]:
        P(f'  HL {g[0]} · λ {g[1]} · εδρα {g[2]} · τυχη {g[3]} · μ_w {g[4]}: {rmm(PRED[g], EV8):.3f} (πρωτα 6 {rmm(PRED[g], EV8, GN <= 5):.3f})')
    for nm, ix_, vals in (('HL', 0, (30, 60, 120, 9999)), ('λ', 1, (2, 4, 8, 12)), ('εδρα', 2, (3, 4, 5, 6, 7)), ('τυχη', 3, (1.0, .5, .25)), ('μ_w', 4, (5, 50))):
        P(f'  προφιλ {nm} (καλυτερο των υπολοιπων): ' + ' · '.join(f'{v}: {min(rmm(PRED[g], EV8) for g in GA if g[ix_] == v):.3f}' for v in vals))
    # ---- ΣΤΑΔΙΟ Β: περσι/ειδικοι/φιλικα πανω στις 5 καλυτερες μηχανες ----
    top5 = sorted(GA, key=lambda g: rmm(PRED[g], EV8))[:5]
    GB = [eng[:5] + (c, k, p) for eng in top5 + [LIVE] for c, k, p in itertools.product((0, .2, .35, .5), (3.0, 4.0, 5.0), (0, .5, 1.0))]
    for i, g in enumerate(GB):
        if g not in PRED: PRED[g] = run2(*g)
        if i % 40 == 0: print(f'  B {i + 1}/{len(GB)} … ({_t.time() - _t0:.0f}s)', flush=True)
    P(''); P('=== ΣΤΑΔΙΟ Β (περσι × ειδικοι × φιλικα πανω στις 5 καλυτερες μηχανες) · καλυτερα 10 ===')
    for g in sorted(PRED, key=lambda g: rmm(PRED[g], EV8))[:10]:
        P(f'  {g}: {rmm(PRED[g], EV8):.3f} (πρωτα 6 {rmm(PRED[g], EV8, GN <= 5):.3f})')
import pickle
if STAGE != '0': pickle.dump({k: v for k, v in PRED.items()}, open('ec_fresh_engine_preds.pkl', 'wb'))
# ---- LOSO πανω σε ΟΛΟ το πλεγμα ----
held = np.full(len(D), np.nan); ch = []
for Y in EV8:
    tr = [x for x in EV8 if x != Y]; g = min(PRED, key=lambda g: rmm(PRED[g], tr)); ch.append(g); held[seasn == Y] = PRED[g][seasn == Y]
d = [rmm(held, [Y]) - rmm(base_live, [Y]) for Y in EV8]
d6 = [rmm(held, [Y], GN <= 5) - rmm(base_live, [Y], GN <= 5) for Y in EV8]
P(''); P('=== LOSO (επιλογη με RMSE ολων των ματς των ΑΛΛΩΝ 7 σεζον) ===')
for Y, g in zip(EV8, ch): P(f'  {Y}: {g}')
P(f'  ΟΛΑ: live {rmm(base_live, EV8):.3f} → {rmm(held, EV8):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV8, d)) + f' → {sum(x < 0 for x in d)}/8'
  + ('  <- ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 6 else '  <- ✗'))
P(f'  ΠΡΩΤΑ 6: live {rmm(base_live, EV8, GN <= 5):.3f} → {rmm(held, EV8, GN <= 5):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV8, d6)) + f' → {sum(x < 0 for x in d6)}/8')
N = NormalDist(); Phi = N.cdf
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
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
MC = np.full(len(D), np.nan); MO = np.full(len(D), np.nan)
for i in MK: MC[i] = MK[i]['c'][1]; MO[i] = MK[i]['o'][1]
def evaluate(v, lab, msk=None):
    ii = [i for i in MK if seasn[i] in EVM and np.isfinite(v[i]) and (msk is None or msk[i])]
    x = np.array([v[i] - MC[i] for i in ii]); z = np.array([act[i] - MC[i] for i in ii]); ss = np.array([seasn[i] for i in ii])
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = {Y: np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EVM}
    cells = []
    for when in ('o', 'c'):
        R = []
        for i in ii:
            L_, _, o1, o2 = MK[i][when]; m = v[i]
            if abs(L_ - round(L_)) < 1e-9: pw = Phi((m + L_ - .5) / 11.5); pl = Phi((-m - L_ - .5) / 11.5)
            else: pw = Phi((m + L_) / 11.5); pl = 1 - pw
            pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e >= .08:
                vv = (act[i] + L_) * side; R.append(((od_ - 1) if vv > 0 else (0 if vv == 0 else -1), seasn[i]))
        a = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R))
        pos = sum(1 for Y in ys if np.mean([q[0] for q in R if q[1] == Y]) > 0)
        cells.append(f'{"ανοιγμα" if when == "o" else "κλεισ."} {a.mean()*100:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/{len(ys)})')
    P(f'  {lab:30s} RMSE μοντ. {math.sqrt(np.mean((act[ii] - v[ii]) ** 2)):.2f} / αγορα κλεισ. {math.sqrt(np.mean((act[ii] - MC[ii]) ** 2)):.2f} · Κ2 b {b:+.3f} (t {b/se:+.1f}) θετ. {sum(p > 0 for p in per.values())}/6 · ' + ' · '.join(cells))
P(''); P('=== ΑΓΟΡΑ (Crown U2020-25, σ 11.5, edge ≥8%) ===')
for lab, msk in (('ΟΛΑ', None), ('ΠΡΩΤΑ 6', GN <= 5), ('7+', GN >= 6)):
    evaluate(base_live, f'live ec1 · {lab}', msk); evaluate(held, f'LOSO νεο · {lab}', msk)
pickle.dump(dict(MK=MK, act=act, GN=GN, seasn=seasn, live=base_live, held=held, home=D.home.values, away=D.away.values, t=D.t.astype(str).values),
            open('ec_fresh_market.pkl', 'wb'))
if STAGE != '0': open('ec_fresh_engine_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
