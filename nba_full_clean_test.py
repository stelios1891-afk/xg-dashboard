# -*- coding: utf-8 -*-
"""nba_full_clean_test.py — NBA: ΚΑΘΕ ΒΑΡΟΣ, ΚΑΘΕ ΜΗΧΑΝΙΣΜΟΣ σε «καθαρο» τεστ (6/10/2026, Στελιος «θελω καθε βαρος, καθε μηχανισμος να τεσταριστει»).
Σεζον-τεστ 2021-22…2025-26 (κανονικη περιοδος)· αγορα Crown (Nowgoal) ανοιγμα/κλεισιμο, χαντικαπ & συνολο. «ΚΑΘΑΡΟ» = καθε επιλογη μονο απο τις αλλες 4 σεζον.
Α. ΠΛΕΓΜΑ ΜΗΧΑΝΗΣ (1.152 εκδοχες, καθε μια δινει ΚΑΙ διαφορα ΚΑΙ συνολο): περσι {.7,.8,.9,1} × βαρος αφετηριας K {8,12} × μνημη HL {60,∞} ×
   τυχη {.5,.75} × επιπεδο λιγκας μ_w {5,50} × ροστερ beta {0,1} × ειδικοι/αποδοσεις (συναινεση z) κx {0,.5,.75} × φιλικα κp {0,.1,.25}· εδρα 2.
   Χαντικαπ: επιλογη με RMSE διαφορας · Συνολα: επιλογη με RMSE συνολου (ξεχωριστα, οπως Ευρωλιγκα).
Β. ΣΥΝΟΛΑ — επιπλεον μηχανισμοι πανω στην καθαρη μηχανη (LOSO): (Β1) καμπυλη σεζον a + b·αγωνας · (Β2) φιλικα στα συνολα κT {0,.25,.5} (αγων ≤20)
   · (Β3) back-to-back κb {0,−1,−2,−3} ανα ομαδα που επαιξε χθες.  ΠΡΟ-ΔΗΛΩΜΕΝΟ: καθε ενα ΜΠΑΙΝΕΙ αν RMSE καλυτερο σε ≥4/5 σεζον.
Γ. ΧΑΝΤΙΚΑΠ — back-to-back κ {0,1,2,3} (διαφορα B2B γηπ − φιλ) — ιδιο κριτηριο.
Δ. ΠΛΕΙ-ΟΦ: προβλεψη με την κατασταση τελους κανονικης· υπολοιπο (πραγματικο − μοντελο) διαφορας & συνολου — «το μοντελο το χανει» αν |t| ≥ 2 & ιδιο προσημο ≥4/5 & ≥1 π.
   (χωρις αποδοσεις πλει-οφ → μονο ακριβεια).
Ε. ΚΑΝΟΝΑΣ PICKS (χαντικαπ & συνολα): σημερινος (μοντελο ≥8%) vs μιξη 50/50 ≥6% — (α) «περισσοτερα χρηματα»: Α ≥4/5 & συνολο, Γ bootstrap ≥.90, Δ CLV ≥ ·
   (β) «λιγοτερο ρισκο»: Τ1 P(ROI) ≥ .90, Τ2 χειροτερη σεζον & βυθιση, Τ4 κλεισιμο P ≥ .80, Τ5 CLV P ≥ .90 → ΟΛΑ (δεν υπαρχει 2ο βιβλιο στο NBA).
ΣΤ. ΦΙΛΤΡΟ TANKING (ομαδα με ποσοστο ≤ .35 μετα απο ≥50 ματς): τα picks ΥΠΕΡ της → ΑΦΑΙΡΟΥΝΤΑΙ αν χειροτερα σε ≥4/5 σεζον & το ROI που μενει ανεβαινει.
Ζ. ΤΕΛΙΚΟ ΚΑΘΑΡΟ BACKTEST ΟΛΩΝ ΜΑΖΙ: μηχανη + ο,τι περασε + κανονας (επιλογη {≥5%, ≥8%, μιξη ≥6%} με μοναδες απο τις αλλες σεζον) — Οκτ-Δεκ & ολη.
Εξοδος: nba_full_clean_out.txt · cache nba_full_grid.npz"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'   # 6/10: πολλες διεργασιες × νηματα BLAS = πολυ αργο
import sys, json, math, itertools, collections
import numpy as np
from multiprocessing import Pool
GRID = list(itertools.product((.7, .8, .9, 1.0), (8, 12), (60, 9999), (.5, .75), (5.0, 50.0), (0.0, 1.0), (0.0, .5, .75), (0.0, .1, .25)))
CACHE = 'nba_full_grid.npz'
_W = {}
def _init():
    import nba_base_core as C
    _W['C'] = C; _W['Z'] = json.load(open('nba_full_z.json', encoding='utf-8'))
def fit_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, muw):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(muw); y[-1] = math.sqrt(muw) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]
def run_all(cfg):
    C = _W['C']; Z = _W['Z']; G = C.G
    carry, lam, HL, lw, muw, beta, kx, kp = cfg; h = 2.0
    if lw not in C.EHA: C.EHA[lw] = C.luck_eff(lw)
    EH, EA = C.EHA[lw]; R2 = C._radj2()['V0|W1']
    mg = np.full(len(G), np.nan); tt = np.full(len(G), np.nan); prior = {}; fin = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(G.pace.mean())
    for s in C.SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        adj = np.array([beta * R2.get(f'{s}|{t}', 0.0) + kx * Z['C'].get(f'{s}|{t}', 0.0) + kp * Z['P'].get(f'{s}|{t}', 0.0) for t in teams])
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]) + adj / 2
        d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams]) - adj / 2
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        nt = (~G.neutral.values[sidx]).astype(float); hb = nt * h / 2; dn = C.dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = G.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_mu(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0, muw)
                pm, Pc = C.fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100; tt[sidx[cur]] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, muw)
        pm, Pc = C.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        fin[int(s)] = dict(mu=float(mu), pm=float(pm), O={t: float(O[i]) for t, i in ix.items()}, D={t: float(Dd[i]) for t, i in ix.items()}, P={t: float(Pc[i]) for t, i in ix.items()})
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return cfg, mg.astype(np.float32), tt.astype(np.float32), fin
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    import nba_base_core as C
    nd = NormalDist(); Phi = nd.cdf
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    G = C.G; EV = [int(s) for s in C.EVAL]; SEAS_G = G.season.values.astype(int)
    lab = lambda y: f'{y - 1}-{str(y)[2:]}'
    # ---------- z συναινεσης & φιλικα (ιδια με nba_preseason_info_test) ----------
    O = json.load(open('nba_preseason_odds.json', encoding='utf-8'))['seasons']
    RK = json.load(open('nba_power_rankings.json', encoding='utf-8'))['sources']
    PG = json.load(open('nba_preseason_games.json', encoding='utf-8'))['seasons']
    def zs(d):
        v = np.array(list(d.values()), float); m, s = v.mean(), v.std(); return {t: (x - m) / s for t, x in d.items()} if s > 0 else {}
    ZC, ZP, RT = {}, {}, {}
    for y in EV:
        L = lab(y); teams = O.get(L, {}).get('teams', {})
        zw = zs({t: v['win_total'] for t, v in teams.items() if v.get('win_total') is not None})
        zt = zs({t: -math.log(v['title_odds_decimal']) for t, v in teams.items() if v.get('title_odds_decimal')})
        acc = collections.defaultdict(list)
        for src, ss in RK.items():
            r = ss.get(L)
            if not r or r.get('kind', '') != 'preseason_final' or len(r.get('ranking', [])) < 30: continue
            for i, t in enumerate(r['ranking'], 1): acc[t].append(nd.inv_cdf(1 - (i - .5) / 30))
        zr = {t: float(np.mean(v)) for t, v in acc.items()}
        for t in set(zw) | set(zt) | set(zr):
            zz = [d[t] for d in (zw, zt, zr) if t in d]; ZC[f'{y}|{t}'] = float(np.mean(zz))
        prev = G[G.season == y - 1]; pdf = collections.defaultdict(list); ptot = collections.defaultdict(list)
        for r in prev.itertuples():
            pdf[r.home].append(r.hs - r.as_); pdf[r.away].append(r.as_ - r.hs); ptot[r.home].append(r.hs + r.as_); ptot[r.away].append(r.hs + r.as_)
        Rp = {t: float(np.mean(v)) for t, v in pdf.items()}; lgm = float(np.mean(prev.hs + prev.as_)); Tp = {t: float(np.mean(v)) - lgm for t, v in ptot.items()}
        res, rest = collections.defaultdict(list), collections.defaultdict(list)
        rows = [r for r in PG.get(L, {}).get('rows', []) if r.get('team_is_nba') and r.get('opp_is_nba')]
        tots = {}
        for r in rows: tots.setdefault(r['game_id'], []).append(r['pts'])
        pre_mu = np.mean([sum(v) for v in tots.values() if len(v) == 2]) if tots else lgm
        for r in rows:
            me, op = r['team'], r.get('opp')
            if me in Rp and op in Rp: res[me].append(float(np.clip(r['plus_minus'], -30, 30)) - (Rp[me] - Rp[op]))
            g2 = tots.get(r['game_id'], [])
            if len(g2) == 2 and me in Tp and op in Tp: rest[me].append(sum(g2) - pre_mu - Tp[me] - Tp[op])
        for t, v in res.items(): ZP[f'{y}|{t}'] = sum(v) / (len(v) + 4)
        for t, v in rest.items(): RT[(y, t)] = sum(v) / (len(v) + 4)
    json.dump(dict(C=ZC, P=ZP), open('nba_full_z.json', 'w', encoding='utf-8'))
    # ---------- Α. πλεγμα ----------
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); MG = dict(zip(map(tuple, z['keys'].tolist()), z['mg'])); TT = dict(zip(map(tuple, z['keys'].tolist()), z['tt'])); FIN = z['fin'].item()
    else:
        MG, TT, FIN = {}, {}, {}
        with Pool(20, initializer=_init) as pool:
            for j, (cfg, mg, tt, fin) in enumerate(pool.imap_unordered(run_all, GRID, chunksize=4)):
                MG[cfg], TT[cfg], FIN[cfg] = mg, tt, fin
                if (j + 1) % 96 == 0: print(f'  {j + 1}/{len(GRID)}', flush=True)
        ks = list(MG); np.savez(CACHE, keys=np.array(ks, dtype=object), mg=np.array([MG[k] for k in ks]), tt=np.array([TT[k] for k in ks]), fin=np.array(FIN, dtype=object))
    P(f'πλεγμα: {len(MG)} εκδοχες · σεζον-τεστ {EV}')
    # ---------- αγορα ----------
    ODD = collections.defaultdict(dict)
    for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln); ODD[r['ngid']][r['t']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    keyd = {}
    for i, r in G.iterrows(): keyd.setdefault((int(r.season), int(r.hs), int(r.as_)), []).append(i)
    SIG = C.SIG; MKH, MKT = {}, {}
    NGS = {'21-22': 2022, '22-23': 2023, '23-24': 2024, '24-25': 2025, '25-26': 2026}
    for sea, se in NGS.items():
        try: S = json.load(open(f'nowgoal_nba/sched_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for g in S:
            if g['hs'] is None or g['ngid'] not in ODD: continue
            us = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize()
            cand = [i for i in keyd.get((se, g['hs'], g['as_']), []) if abs((G.date[i] - us).days) <= 1]; swap = False
            if not cand: cand = [i for i in keyd.get((se, g['as_'], g['hs']), []) if abs((G.date[i] - us).days) <= 1]; swap = True
            if len(cand) != 1: continue
            i = cand[0]; od = ODD[g['ngid']]
            if od.get(21):
                def ch(x):
                    L = -x[1] * (-1 if swap else 1); oh, oa = (1 + x[2], 1 + x[3]) if not swap else (1 + x[3], 1 + x[2])
                    ph = (1 / oh) / (1 / oh + 1 / oa); return (L, -L + SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)), oh, oa)
                MKH[i] = dict(o=ch(od[21][0]), c=ch(od[21][-1]))
            if od.get(23):
                MKT[i] = dict(o=(float(od[23][0][1]), 1 + od[23][0][2], 1 + od[23][0][3]), c=(float(od[23][-1][1]), 1 + od[23][-1][2], 1 + od[23][-1][3]))
    ACT = (G.hs - G.as_).values.astype(float); TOT = (G.hs + G.as_).values.astype(float)
    it_ = [i for i in MKT if SEAS_G[i] in EV]
    SIGT = float(np.std([TOT[i] - MKT[i]['c'][0] for i in it_]))
    for i, d in MKT.items():
        for k in ('o', 'c'):
            T, oo, ou = d[k]; po = (1 / oo) / (1 / oo + 1 / ou); d[k] = (T, T + SIGT * nd.inv_cdf(min(max(po, 1e-4), 1 - 1e-4)), oo, ou)
    P(f'αγορα: χαντικαπ {len(MKH)} · συνολα {len(MKT)} · σ διαφορα {SIG:.1f} · σ συνολο {SIGT:.1f}')
    INM = np.zeros(len(G), bool); INM[list(MKH)] = True
    MON = G.date.dt.month.values; OD = np.isin(MON, [10, 11, 12]); ALL = np.ones(len(G), bool)
    def rm(v, tgt, ys, msk=ALL):
        m = np.isin(SEAS_G, ys) & msk & np.isfinite(v); return float(np.sqrt(np.mean((tgt - v)[m] ** 2)))
    # αριθμος αγωνα, B2B
    GN = np.zeros(len(G)); cnt = {}; last = {}; B2H = np.zeros(len(G)); B2A = np.zeros(len(G))
    for i in np.argsort(G.date.values, kind='stable'):
        s = SEAS_G[i]; h, a = G.home.values[i], G.away.values[i]; dd = G.date.values[i]
        GN[i] = max(cnt.get((s, h), 0), cnt.get((s, a), 0)) + 1
        for t, arr in ((h, B2H), (a, B2A)):
            if (s, t) in last and (dd - last[(s, t)]) / np.timedelta64(1, 'D') <= 1.01: arr[i] = 1
        for t in (h, a): cnt[(s, t)] = cnt.get((s, t), 0) + 1; last[(s, t)] = dd
    # ---------- καθαρη επιλογη μηχανης ----------
    def nested(D_, tgt, msk=ALL):
        held = np.full(len(G), np.nan); ch = {}
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(D_, key=lambda k: rm(D_[k], tgt, tr, msk)); ch[Y] = k
            m = SEAS_G == Y; held[m] = D_[k][m]
        return held, ch
    LIVE_LIKE = (.8, 12, 60, .75, 5.0, 1.0, 0.0, 0.0)
    HH, chH = nested(MG, ACT); HT0, chT = nested(TT, TOT)
    P(''); P('################ Α. ΚΑΘΑΡΗ ΜΗΧΑΝΗ ################')
    nm = ('περσι', 'K', 'HL', 'τυχη', 'μ_w', 'ροστερ', 'ειδικοι', 'φιλικα')
    for Y in EV: P(f'  {lab(Y)}: χαντικαπ {chH[Y]} · συνολο {chT[Y]}')
    for j, n_ in enumerate(nm):
        vals = sorted({k[j] for k in MG})
        P(f'  προφιλ {n_:8s} (καλυτερο των υπολοιπων) χαντικαπ: ' + ' · '.join(f'{v}: {min(rm(MG[k], ACT, EV) for k in MG if k[j] == v):.3f}' for v in vals)
          + ' | συνολο: ' + ' · '.join(f'{v}: {min(rm(TT[k], TOT, EV) for k in TT if k[j] == v):.3f}' for v in vals))
    P(f'  RMSE χαντικαπ: καθαρο {rm(HH, ACT, EV):.3f} (Οκτ-Δεκ {rm(HH, ACT, EV, OD):.3f}) · «σημερινη» {rm(MG[LIVE_LIKE], ACT, EV):.3f} · αγορα κλεισιμο {np.sqrt(np.mean([(ACT[i] - MKH[i]["c"][1]) ** 2 for i in MKH if SEAS_G[i] in EV])):.3f}')
    P(f'  RMSE συνολο: καθαρο {rm(HT0, TOT, EV):.3f} · αγορα κλεισιμο {np.sqrt(np.mean([(TOT[i] - MKT[i]["c"][1]) ** 2 for i in MKT if SEAS_G[i] in EV])):.3f}')
    def loso_add(base, feat, ks, tgt, lab_, msk=ALL):
        PR = {k: base + k * feat for k in ks}; held = np.full(len(G), np.nan); ch = []
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(PR, key=lambda k: rm(PR[k], tgt, tr, msk)); ch.append(k); held[SEAS_G == Y] = PR[k][SEAS_G == Y]
        d = [rm(held, tgt, [Y], msk) - rm(base, tgt, [Y], msk) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
        P(f'  {lab_:38s} {rm(base, tgt, EV, msk):.3f} → {rm(held, tgt, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · επιλογες {ch}' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
        return (held if ok else base), ok
    # ---------- Β. συνολα ----------
    P(''); P('################ Β. ΣΥΝΟΛΑ — επιπλεον μηχανισμοι ################')
    HT = HT0.copy()
    cur = np.full(len(G), np.nan)
    for Y in EV:
        tr = np.isin(SEAS_G, [x for x in EV if x != Y]) & np.isfinite(HT)
        b, a = np.polyfit(GN[tr], (TOT - HT)[tr], 1); m = SEAS_G == Y; cur[m] = HT[m] + a + b * GN[m]
    d = [rm(cur, TOT, [Y]) - rm(HT, TOT, [Y]) for Y in EV]; okc = sum(x < 0 for x in d) >= 4
    P(f'  {"Β1 καμπυλη σεζον":38s} {rm(HT, TOT, EV):.3f} → {rm(cur, TOT, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΜΠΑΙΝΕΙ' if okc else '  <- ✗'))
    if okc: HT = cur
    FRT = np.array([(RT.get((SEAS_G[i], G.home.values[i]), 0) + RT.get((SEAS_G[i], G.away.values[i]), 0)) if GN[i] <= 20 else 0.0 for i in range(len(G))])
    HT, _ = loso_add(HT, FRT, (0, .25, .5), TOT, 'Β2 φιλικα στα συνολα (αγων ≤20)')
    HT, _ = loso_add(HT, B2H + B2A, (0, -1, -2, -3), TOT, 'Β3 back-to-back στα συνολα')
    # ---------- Γ. χαντικαπ B2B ----------
    P(''); P('################ Γ. ΧΑΝΤΙΚΑΠ — back-to-back ################')
    HHb, okb = loso_add(HH, B2A - B2H, (0, 1, 2, 3), ACT, 'Γ back-to-back (φιλ − γηπ)')
    import pickle   # 6/10: δεδομενα για τη διαγνωση (nba_diag.py)
    pickle.dump(dict(G=G[['season', 'date', 'home', 'away', 'hs', 'as_', 'neutral', 'pace']].copy(), HH=HHb, HT=HT, MKH=MKH, MKT=MKT, GN=GN, B2H=B2H, B2A=B2A, EV=EV, SIG=SIG, SIGT=SIGT),
                open('nba_diag_data.pkl', 'wb'))
    # ---------- Δ. πλει-οφ ----------
    P(''); P('################ Δ. ΠΛΕΙ-ΟΦ (κατασταση τελους κανονικης) ################')
    Lg = pd.read_csv('nba_gamelogs.csv', low_memory=False); Lp = Lg[(Lg.table == 'team_game_log_post') & (Lg.game_location.fillna('') != '@')]
    for nmk, Dsel, ch_, tgt_fn in (('διαφορα', MG, chH, lambda r: r.team_game_score - r.opp_team_game_score), ('συνολο', TT, chT, lambda r: r.team_game_score + r.opp_team_game_score)):
        res = collections.defaultdict(list)
        for r in Lp.itertuples():
            y = int(r.season_end)
            if y not in EV: continue
            f = FIN[ch_[y]].get(y)
            if not f or r.team not in f['O'] or r.opp_name_abbr not in f['O']: continue
            h_, a_ = r.team, r.opp_name_abbr
            e_h = f['mu'] + f['O'][h_] + f['D'][a_] + 1.0; e_a = f['mu'] + f['O'][a_] + f['D'][h_] - 1.0; poss = f['pm'] + f['P'][h_] + f['P'][a_]
            pred = poss * (e_h - e_a) / 100 if nmk == 'διαφορα' else poss * (e_h + e_a) / 100
            try: res[y].append(float(tgt_fn(r)) - pred)
            except Exception: pass
        allr = np.concatenate([np.array(v) for v in res.values()]); m = allr.mean(); se = allr.std() / math.sqrt(len(allr)); per = [np.mean(v) for v in res.values()]
        same = sum(np.sign(p) == np.sign(m) for p in per); fl = abs(m / se) >= 2 and same >= 4 and abs(m) >= 1
        P(f'  {nmk}: n {len(allr)} · μεσο υπολοιπο {m:+.2f} (t {m/se:+.1f}) · ανα σεζον ' + ' '.join(f'{p:+.1f}' for p in per) + ('  ← ΤΟ ΜΟΝΤΕΛΟ ΤΟ ΧΑΝΕΙ' if fl else ''))
    # ---------- picks ----------
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def bets(kind, v, w, thr, wh='o', msk=ALL):
        R = []
        MKX = MKH if kind == 'h' else MKT
        for i, d in MKX.items():
            if SEAS_G[i] not in EV or not np.isfinite(v[i]) or not msk[i]: continue
            L, mk, o1, o2 = d[wh]; mu = mk + w * (v[i] - mk)
            if kind == 'h': pw, pp, pl = cover(mu, L, SIG)
            else: pw, pp, pl = cover(mu, -L, SIGT)
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < thr: continue
            x = ((ACT[i] + L) if kind == 'h' else (TOT[i] - L)) * s_
            R.append((i, (od - 1) if x > 0 else (0 if x == 0 else -1), (d['c'][1] - d['o'][1]) * s_, s_))
        return R
    rng = np.random.default_rng(5)
    def summ(R, lab_):
        u = np.array([r[1] for r in R]) if R else np.zeros(1); ps = {Y: sum(r[1] for r in R if SEAS_G[r[0]] == Y) for Y in EV}
        order = sorted(R, key=lambda r: G.date.values[r[0]]); cum = np.cumsum([r[1] for r in order]) if R else np.zeros(1); dd = float(np.max(np.maximum.accumulate(cum) - cum))
        P(f'    {lab_:30s} {len(R):5d} picks · ROI {u.mean()*100:+.1f}% · {u.sum():+.1f}u · θετ. {sum(v > 0 for v in ps.values())}/5 · χειροτ. {min(ps.values()):+.1f} · βυθιση {dd:.1f}')
        return ps, dd
    def boot_mean(Ra, Rb, key=1):
        games = sorted({r[0] for r in Ra} | {r[0] for r in Rb}); gi = {g: k for k, g in enumerate(games)}
        va = np.full(len(games), np.nan); vb = np.full(len(games), np.nan)
        for r in Ra: va[gi[r[0]]] = r[key]
        for r in Rb: vb[gi[r[0]]] = r[key]
        w = 0
        for _ in range(3000):
            s = rng.integers(0, len(games), len(games))
            if np.nanmean(va[s]) > np.nanmean(vb[s]): w += 1
        return w / 3000
    def boot_units(Ra, Rb):
        games = sorted({r[0] for r in Ra} | {r[0] for r in Rb}); gi = {g: k for k, g in enumerate(games)}; d = np.zeros(len(games))
        for r in Ra: d[gi[r[0]]] += r[1]
        for r in Rb: d[gi[r[0]]] -= r[1]
        return float(np.mean([d[rng.integers(0, len(d), len(d))].sum() > 0 for _ in range(3000)]))
    VH = HHb; VT = HT
    P(''); P('################ Ε. ΚΑΝΟΝΑΣ PICKS: σημερινος vs μιξη ################')
    for kind, v, labk in (('h', VH, 'ΧΑΝΤΙΚΑΠ'), ('t', VT, 'ΣΥΝΟΛΑ')):
        for per_lab, msk in (('Οκτ-Δεκ', OD), ('ολη η σεζον', ALL)):
            P(f'  [{labk} · {per_lab}]')
            Rc, Rm = bets(kind, v, 1.0, .08, 'o', msk), bets(kind, v, .5, .06, 'o', msk)
            psC, ddC = summ(Rc, 'σημερινος (μοντελο ≥8%)'); psM, ddM = summ(Rm, 'μιξη 50/50 ≥6%')
            Kc, Km = bets(kind, v, 1.0, .08, 'c', msk), bets(kind, v, .5, .06, 'c', msk)
            summ(Kc, 'σημερινος — κλεισιμο'); summ(Km, 'μιξη — κλεισιμο')
            A_ = sum(psM[Y] > psC[Y] for Y in EV) >= 4 and sum(psM.values()) > sum(psC.values())
            pG = boot_units(Rm, Rc); clvC = np.mean([r[2] for r in Rc]) if Rc else 0; clvM = np.mean([r[2] for r in Rm]) if Rm else 0
            p1 = boot_mean(Rm, Rc); T2 = min(psM.values()) > min(psC.values()) and ddM < ddC; p4 = boot_mean(Km, Kc); p5 = boot_mean(Rm, Rc, 2)
            P(f'    (α) περισσοτερα χρηματα: Α {"✓" if A_ else "✗"} · Γ P {pG:.2f} {"✓" if pG >= .9 else "✗"} · Δ CLV {clvM:+.2f} vs {clvC:+.2f} {"✓" if clvM >= clvC else "✗"} → {"ΠΕΡΝΑ" if A_ and pG >= .9 and clvM >= clvC else "✗"}')
            P(f'    (β) λιγοτερο ρισκο: Τ1 P {p1:.2f} {"✓" if p1 >= .9 else "✗"} · Τ2 {"✓" if T2 else "✗"} · Τ4 P {p4:.2f} {"✓" if p4 >= .8 else "✗"} · Τ5 P {p5:.2f} {"✓" if p5 >= .9 else "✗"} → {"ΠΕΡΝΑ" if p1 >= .9 and T2 and p4 >= .8 and p5 >= .9 else "✗"}')
    # ---------- ΣΤ. tanking ----------
    P(''); P('################ ΣΤ. ΦΙΛΤΡΟ TANKING ################')
    rec = {}; TANK = {}
    for i in np.argsort(G.date.values, kind='stable'):
        s = SEAS_G[i]
        for t in (G.home.values[i], G.away.values[i]):
            w_, n_ = rec.get((s, t), (0, 0)); TANK[(i, t)] = n_ >= 50 and w_ / n_ <= .35
        hw = ACT[i] > 0
        rec[(s, G.home.values[i])] = (rec.get((s, G.home.values[i]), (0, 0))[0] + hw, rec.get((s, G.home.values[i]), (0, 0))[1] + 1)
        rec[(s, G.away.values[i])] = (rec.get((s, G.away.values[i]), (0, 0))[0] + (not hw), rec.get((s, G.away.values[i]), (0, 0))[1] + 1)
    Rh = bets('h', VH, 1.0, .08)
    pro = [r for r in Rh if TANK.get((r[0], G.home.values[r[0]] if r[3] == 1 else G.away.values[r[0]]), False)]
    rest_ = [r for r in Rh if r not in pro]
    psP = {Y: np.mean([r[1] for r in pro if SEAS_G[r[0]] == Y]) if any(SEAS_G[r[0]] == Y for r in pro) else 0 for Y in EV}
    psR = {Y: np.mean([r[1] for r in rest_ if SEAS_G[r[0]] == Y]) for Y in EV}
    worse = sum(psP[Y] < psR[Y] for Y in EV)
    P(f'  picks ΥΠΕΡ tanking ομαδας: {len(pro)} · ROI {np.mean([r[1] for r in pro])*100 if pro else 0:+.1f}% · υπολοιπα {len(rest_)} · ROI {np.mean([r[1] for r in rest_])*100:+.1f}% (ολα {np.mean([r[1] for r in Rh])*100:+.1f}%) · '
      f'χειροτερα σε {worse}/5 → ' + ('ΦΙΛΤΡΟ ΠΕΡΝΑ' if worse >= 4 and np.mean([r[1] for r in rest_]) > np.mean([r[1] for r in Rh]) else 'ΦΙΛΤΡΟ ✗'))
    # ---------- Ζ. τελικο καθαρο ----------
    P(''); P('################ Ζ. ΤΕΛΙΚΟ ΚΑΘΑΡΟ BACKTEST ΟΛΩΝ ΜΑΖΙ ################')
    RULES = {'μοντελο ≥5%': (1.0, .05), 'μοντελο ≥8%': (1.0, .08), 'μιξη ≥6%': (.5, .06)}
    for kind, v, labk in (('h', VH, 'ΧΑΝΤΙΚΑΠ'), ('t', VT, 'ΣΥΝΟΛΑ')):
        for per_lab, msk in (('Οκτ-Δεκ', OD), ('ολη η σεζον', ALL)):
            tot = []; chs = []
            for Y in EV:
                tr = [x for x in EV if x != Y]
                rn = max(RULES, key=lambda r: sum(x[1] for x in bets(kind, v, *RULES[r], 'o', msk) if SEAS_G[x[0]] in tr)); chs.append(rn)
                tot += [x for x in bets(kind, v, *RULES[rn], 'o', msk) if SEAS_G[x[0]] == Y]
            u = np.array([x[1] for x in tot]); ps = {Y: sum(x[1] for x in tot if SEAS_G[x[0]] == Y) for Y in EV}
            P(f'  {labk} {per_lab:12s} κανονες {chs} → {len(u)} picks · ROI {u.mean()*100 if len(u) else 0:+.1f}% · {u.sum():+.1f}u · θετ. {sum(x > 0 for x in ps.values())}/5 · '
              + ' '.join(f'{lab(Y)[-5:]}:{x:+.1f}' for Y, x in ps.items()))
            ii = [i for i in (MKH if kind == 'h' else MKT) if SEAS_G[i] in EV and msk[i] and np.isfinite(v[i])]
            mc = np.array([(MKH if kind == 'h' else MKT)[i]['c'][1] for i in ii]); a = (ACT if kind == 'h' else TOT)[ii]; m = v[ii]; ss = SEAS_G[ii]
            x, z = m - mc, a - mc; b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x)
            se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); per_ = [np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EV]
            P(f'      λαθος μοντελο {np.sqrt(np.mean((a - m) ** 2)):.2f} vs κλεισιμο {np.sqrt(np.mean((a - mc) ** 2)):.2f} · Κ2 b {b:+.2f} (t {b/se:+.1f}, θετ. {sum(q > 0 for q in per_)}/5)')
    open('nba_full_clean_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
if __name__ == '__main__':
    main()
