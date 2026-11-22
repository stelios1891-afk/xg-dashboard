"""
sos_test.py — ΑΠΟΜΟΝΩΜΕΝΟ test: βοηθαει το SoS (Caley one-pass) το window 7-14;

ΔΕΝ αγγιζει το picks.py. Εισαγει τη κλειδωμενη μηχανη (load_matches, odds matching,
bet_signals, settlement) και αντικαθιστα ΜΟΝΟ το rating-step του predict():
  - baseline: raw team ratings (ιδιο math με picks.predict)
  - +SoS:     καθε rating διορθωνεται για τη δυσκολια των αντιπαλων που ΕΧΕΙ ηδη παιξει
              (Caley: "τι θα εβγαζε μια μεση ομαδα σε αυτο το προγραμμα"), ΜΟΝΟ στο xG part.

SoS = multiplicative αναλογο του Caley additive-xGD, στο native rating space του μοντελου:
  attack_adj = Ax × (lg_xgps / mean_opp_Dx)   # επαιξες αδυναμες αμυνες (υψηλο Dx) → deflate
  defense_adj= Dx × (lg_xgps / mean_opp_Ax)
  shotsF_adj = SF × (lg_shots / mean_opp_SA)
  shotsA_adj = SA × (lg_shots / mean_opp_SF)
Ολα walk-forward: opponent ratings = μονο απο ματς ΠΡΙΝ το τρεχον fixture.

Χρηση:
  python sos_test.py            # baseline vs +SoS στο 7-14, ανα λιγκα + συνολο (CORE 7)
  python sos_test.py sanity     # sanity: αναπαραγει picks backtest @15+ (baseline, no window)
"""
import sys, numpy as np, pandas as pd
import picks
from picks import wmean, BLEND, DECAY, HFA_FIX, load_matches, load_odds, make_resolver, bet_signals, TOP5, ALL_SEASONS
from league_config import ALIAS_FD, ALIAS_FD_OLD, ALIAS_TOA

# ═══════ 5-SEASON layer: season-aware odds (old=football-data short names, new=slim TOA full) ═══════
CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
FIVE_SEASONS = ['2122', '2223', '2324', '2425', '2526']
OLD_SEASONS = {'2122', '2223', '2324'}
def reg_of(sea):
    return 'old' if str(sea) in OLD_SEASONS else 'new'

def load_matches_5s(leagues, seasons, csv=None):
    # 2026-09-18: προεπιλογη το walk-forward αρχειο (rescale factor οπως το live, Kf=4)· το παλιο
    # teamgame_inputs_5s.csv εβλεπε μπροστα στον sf (full-season). Βλ. build_inputs_5s_wf.py, builder_wf_impact_out.txt.
    if csv is None:
        import os as _os
        csv = 'teamgame_inputs_5s_wf.csv' if _os.path.exists('teamgame_inputs_5s_wf.csv') else 'teamgame_inputs_5s.csv'
    """Ιδιο με picks.load_matches αλλα διαβαζει το 5-season csv (ΔΕΝ πειραζει production)."""
    import json
    TG = pd.read_csv(csv); TG['season'] = TG['season'].astype(str)
    id2name = {}
    for lg in leagues:
        for sea in seasons:
            try:
                d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
            except FileNotFoundError:
                continue
            for m in d.values():
                id2name[int(m['home']['id'])] = m['home']['name']
                id2name[int(m['away']['id'])] = m['away']['name']
    TG = TG[(TG.league.isin(leagues)) & (TG.season.isin(seasons))]
    TG = TG.sort_values(['league', 'season', 'date', 'mid', 'is_home'])
    MM = []
    for (lg, sea, mid), g in TG.groupby(['league', 'season', 'mid'], sort=False):
        if len(g) != 2:
            continue
        h = g[g.is_home == 1].iloc[0]; a = g[g.is_home == 0].iloc[0]
        MM.append(dict(league=lg, season=str(sea), mid=mid, date=h['date'],
                       home=int(h['team']), away=int(a['team']), hg=int(h['gf']), ag=int(a['gf']),
                       h_xg=h['xg_model'], a_xg=a['xg_model'], h_ns=h['ns_eff'], a_ns=a['ns_eff']))
    return pd.DataFrame(MM).sort_values(['league', 'season', 'date', 'mid']).reset_index(drop=True), id2name

def make_resolver_alias(fdn, alias):
    """picks.make_resolver αλλα με ΔΙΚΟ του alias dict (αντι για το global picks.ALIAS)."""
    cache = {}
    def resolve(n):
        if n in cache:
            return cache[n]
        tn = picks.norm(alias.get(n, n)); best = None; bs = 0; bj = 0
        for raw, tg in sorted(fdn.items()):   # ντετερμινιστικη σειρα (2026-08-28: το set-order εκανε την επιλυση τυχαια σε ισοβαθμιες)
            ov = len(tn & tg)
            if ov > bs or (ov == bs and ov / max(len(tn | tg), 1) > bj):
                bs = ov; bj = ov / max(len(tn | tg), 1); best = raw
        cache[n] = best if bs > 0 else None
        return cache[n]
    return resolve

def build_odds_layer(leagues, seasons):
    """Per-regime Om + resolver. old→ALIAS_FD(+OLD), new→ALIAS_TOA."""
    reg = {'old': dict(Om={}, fdn={}), 'new': dict(Om={}, fdn={})}
    for lg in leagues:
        for sea in seasons:
            try:
                o = pd.read_csv(f'odds/{lg}_{sea}.csv', encoding='latin-1')
            except FileNotFoundError:
                continue
            R = reg[reg_of(sea)]
            for _, r in o.iterrows():
                if pd.isna(r.get('HomeTeam')):
                    continue
                R['fdn'][r['HomeTeam']] = picks.norm(r['HomeTeam'])
                R['fdn'][r['AwayTeam']] = picks.norm(r['AwayTeam'])
                R['Om'].setdefault((str(sea), r['HomeTeam'], r['AwayTeam']), []).append(r)
    resolvers = {
        'old': make_resolver_alias(reg['old']['fdn'], {**ALIAS_FD, **ALIAS_FD_OLD}),
        'new': make_resolver_alias(reg['new']['fdn'], ALIAS_TOA),
    }
    return reg, resolvers

def bet_signals_5s(P, reg, resolvers):
    """picks.bet_signals αλλα season-aware (διαλεγει regime odds+resolver ανα season). Κραταει md."""
    rows = []
    for _, r in P.iterrows():
        g = reg_of(r['season']); Om = reg[g]['Om']; resolve = resolvers[g]
        o = picks.match_odds(Om, r['season'], resolve(r['home_name']), resolve(r['away_name']), r['date'])
        if o is None:
            continue
        line = o.get('AHCh'); oh, oa, book = picks.ah_odds(o)
        if pd.isna(line) or oh is None:
            continue
        xh = min(max(r['xg_h'], 0.05), 6.0); xa = min(max(r['xg_a'], 0.05), 6.0)  # ceiling: πρωιμα ratings εκτοξευονται
        for b in picks.evaluate_bet(xh, xa, float(line), oh, oa):
            rows.append(dict(league=r['league'], season=r['season'], date=r['date'],
                             home=r['home_name'], away=r['away_name'], book=book, gd=r.get('gd'),
                             pnl=picks.settle(r['gd'], b['side'], b['hcap'], b['odds']) if pd.notna(r.get('gd')) else float('nan'),
                             **b))
    return pd.DataFrame(rows)

# ---------- team ratings απο rolling hist (ιδιο ν/math με picks.predict) ----------
def ratings(t):
    """(Ax attack xg/shot, Dx defense xg/shot conceded, SF shots-for, SA shots-against)."""
    sf = wmean(t['sf']); sa = wmean(t['sa'])
    Ax = (BLEND * wmean(t['xf']) + (1 - BLEND) * wmean(t['gf'])) / max(sf, 1e-9)
    Dx = (BLEND * wmean(t['xa']) + (1 - BLEND) * wmean(t['ga'])) / max(sa, 1e-9)
    return Ax, Dx, sf, sa

def predict_from_ratings(rh, ra, lg_shots, lg_xgps, hf):
    """Ιδιο math με picks.predict, αλλα δεχεται ΕΤΟΙΜΑ (πιθ. SoS-adjusted) ratings."""
    Ax_h, Dx_h, SF_h, SA_h = rh
    Ax_a, Dx_a, SF_a, SA_a = ra
    af = 1 / hf
    esh_h = SF_h * SA_a / lg_shots
    esh_a = SF_a * SA_h / lg_shots
    xg_h = esh_h * (Ax_h * (Dx_a / lg_xgps)) * hf
    xg_a = esh_a * (Ax_a * (Dx_h / lg_xgps)) * af
    return xg_h, xg_a

def massey_adjust_all(hist, lg_shots, lg_xgps):
    """Massey least-squares exact solve (= σημειο συγκλισης SRS iterative). Λυνει την
    ΠΛΗΡΗ κυκλικοτητα: attack_true de-inflated απο ΤΗΝ ALHΘΙΝΗ αμυνα των αντιπαλων (οχι raw).
    Log-space (multiplicative→additive): [[I,W],[W,I]]·[a;d]=[A;D], W=decay-weighted opp adjacency."""
    teams = [t for t in hist if len(hist[t]['sf']) > 0]
    if len(teams) < 2:
        return {t: ratings(hist[t]) for t in teams}
    idx = {t: k for k, t in enumerate(teams)}; T = len(teams)
    A = np.zeros(T); D = np.zeros(T); SFl = np.zeros(T); SAl = np.zeros(T); W = np.zeros((T, T))
    for t in teams:
        Ax, Dx, SF, SA = ratings(hist[t]); i = idx[t]
        A[i] = np.log(max(Ax, 1e-9) / lg_xgps); D[i] = np.log(max(Dx, 1e-9) / lg_xgps)
        SFl[i] = np.log(max(SF, 1e-9) / lg_shots); SAl[i] = np.log(max(SA, 1e-9) / lg_shots)
        opps = hist[t]['opp']; n = len(opps)
        wts = np.array([DECAY ** (n - 1 - k) for k in range(n)]); wts /= wts.sum()
        for k, o in enumerate(opps):
            if o in idx:
                W[i, idx[o]] += wts[k]
    I = np.eye(T); M = np.block([[I, W], [W, I]])
    ad = np.linalg.lstsq(M, np.concatenate([A, D]), rcond=None)[0]
    sfa = np.linalg.lstsq(M, np.concatenate([SFl, SAl]), rcond=None)[0]
    a, d = ad[:T], ad[T:]; sfl, sal = sfa[:T], sfa[T:]
    return {t: (lg_xgps * np.exp(a[idx[t]]), lg_xgps * np.exp(d[idx[t]]),
               lg_shots * np.exp(sfl[idx[t]]), lg_shots * np.exp(sal[idx[t]])) for t in teams}

def sos_adjust(r, t, hist, lg_shots, lg_xgps, strength=1.0):
    """Caley one-pass: διορθωσε τα ratings για τη δυσκολια των αντιπαλων που εχει παιξει.
    opponent ratings = current best estimate (μονο ματς πριν το τρεχον fixture — walk-forward)."""
    Ax, Dx, SF, SA = r
    opps = t['opp']
    if not opps:
        return r
    oAx, oDx, oSF, oSA = [], [], [], []
    for o in opps:
        ho = hist.get(o)
        if ho and len(ho['sf']) > 0:
            aAx, aDx, aSF, aSA = ratings(ho)
        else:
            aAx, aDx, aSF, aSA = lg_xgps, lg_xgps, lg_shots, lg_shots
        oAx.append(aAx); oDx.append(aDx); oSF.append(aSF); oSA.append(aSA)
    mAx, mDx = wmean(oAx), wmean(oDx)
    mSF, mSA = wmean(oSF), wmean(oSA)
    # multiplicative factors, με strength dampening (1.0 = πληρες Caley)
    fAtt = (lg_xgps / max(mDx, 1e-9)) ** strength
    fDef = (lg_xgps / max(mAx, 1e-9)) ** strength
    fSF  = (lg_shots / max(mSA, 1e-9)) ** strength
    fSA  = (lg_shots / max(mSF, 1e-9)) ** strength
    return Ax * fAtt, Dx * fDef, SF * fSF, SA * fSA

def shrink_adjust(r, n, K, lg_shots, lg_xgps):
    """LEVER B: shrinkage προς μεσο λιγκας που ΛΙΩΝΕΙ με τα ματς. w=n/(n+K):
    λιγα ματς→βαρυ shrink προς μεσο· πολλα→κοντα στο raw. Log-space (multiplicative)."""
    Ax, Dx, SF, SA = r
    w = n / (n + K)
    return (lg_xgps * (max(Ax, 1e-9) / lg_xgps) ** w, lg_xgps * (max(Dx, 1e-9) / lg_xgps) ** w,
            lg_shots * (max(SF, 1e-9) / lg_shots) ** w, lg_shots * (max(SA, 1e-9) / lg_shots) ** w)

def sos_adjust_prioropp(r, t, hist, prevs, mean_tuple, lg_shots, lg_xgps, strength=1.0, K=10.0):
    """ΙΔΙΟ Caley SoS, αλλα η ποιοτητα ΑΝΤΙΠΑΛΩΝ = shrink-to-prior (σταθερη νωρις) αντι raw φετινο.
    Αντιπαλος με φετινα ματς → shrink(φετινο→περσινο)· χωρις φετινα → περσινο κατευθειαν (μεσος αν νεοφωτιστη)."""
    Ax, Dx, SF, SA = r
    opps = t['opp']
    if not opps:
        return r
    oAx, oDx, oSF, oSA = [], [], [], []
    for o in opps:
        ho = hist.get(o)
        if ho and len(ho['sf']) > 0:
            a = shrink_prior(ratings(ho), prevs.get(o, mean_tuple), len(ho['sf']), K)
        else:
            a = prevs.get(o, mean_tuple)      # 0 φετινα ματς → περσινο κατευθειαν
        oAx.append(a[0]); oDx.append(a[1]); oSF.append(a[2]); oSA.append(a[3])
    mAx, mDx = wmean(oAx), wmean(oDx); mSF, mSA = wmean(oSF), wmean(oSA)
    fAtt = (lg_xgps / max(mDx, 1e-9)) ** strength
    fDef = (lg_xgps / max(mAx, 1e-9)) ** strength
    fSF = (lg_shots / max(mSA, 1e-9)) ** strength
    fSA = (lg_shots / max(mSF, 1e-9)) ** strength
    return Ax * fAtt, Dx * fDef, SF * fSF, SA * fSA

def shrink_prior(r, prior, n, K):
    """LEVER B': shrinkage προς την ΠΕΡΣΙΝΗ ποιοτητα (οχι μεσο). στοχος=prior rating της ιδιας ομαδας.
    w=n/(n+K): λιγα ματς→κοντα στο περσινο· πολλα→κοντα στο φετινο (in-season). Καλες ομαδες μενουν καλες."""
    w = n / (n + K)
    out = []
    for ri, pi in zip(r, prior):
        ri = max(ri, 1e-9); pi = max(pi, 1e-9)
        out.append(pi * (ri / pi) ** w)
    return tuple(out)

def full_season_ratings(M):
    """{(league,season): {team_id: (Ax,Dx,SF,SA)}} — rating καθε ομαδας απο ΟΛΗ τη σεζον (για prior)."""
    res = {}
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        G = G.sort_values(['date', 'mid'])
        hist = {}
        for _, r in G.iterrows():
            for tid, sf, xf, sa, xa, gf, ga in [
                    (r['home'], r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (r['away'], r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga)]:
                    hist[tid][k].append(v)
        res[(lg, str(sea))] = {t: ratings(h) for t, h in hist.items() if len(h['sf']) > 0}
    return res

_SEAS_ORDER = ['2122', '2223', '2324', '2425', '2526']
def prev_season(sea):
    i = _SEAS_ORDER.index(str(sea)) if str(sea) in _SEAS_ORDER else -1
    return _SEAS_ORDER[i - 1] if i > 0 else None

# ---------- walk-forward predictions με window + SoS method ----------
def build_preds(M, id2name, method='none', lo=6, hi=13, strength=1.0, strength_fn=None, shrink_k=10.0):
    """method: 'none' | 'caley' | 'massey' | 'shrink' (K=strength) | 'combo' (shrink K=shrink_k ΜΕΤΑ SoS strength).
    strength_fn(md)→strength: αν δοθει, το caley strength εξαρταται απο την αγωνιστικη."""
    out = []
    prior_all = full_season_ratings(M) if method in ('shrinkprior', 'comboprior', 'comboprior_promo', 'caley_prioropp', 'comboprior_prioropp') else None
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        G = G.sort_values(['date', 'mid']).reset_index(drop=True)
        hist = {}
        lg_shots = pd.concat([G.h_ns, G.a_ns]).mean()
        lg_xgps = pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum()
        hf = HFA_FIX[lg]
        prevs = prior_all.get((lg, prev_season(sea)), {}) if prior_all is not None else {}
        mean_tuple = (lg_xgps, lg_xgps, lg_shots, lg_shots)
        # νεοφωτιστη weak prior: μεσος × μεταφραση (xGF×0.65/SF×0.73 → Ax×0.89· xGA×1.5/SA×1.34 → Dx×1.119)
        promo_tuple = (lg_xgps * 0.890, lg_xgps * 1.119, lg_shots * 0.73, lg_shots * 1.34)
        for _, r in G.iterrows():
            H, A = r['home'], r['away']
            hh = hist.get(H); ha = hist.get(A)
            if hh and ha and lo <= len(hh['sf']) <= hi and lo <= len(ha['sf']) <= hi:
                md = min(len(hh['sf']), len(ha['sf']))
                if method == 'caley':
                    st = strength_fn(md) if strength_fn is not None else strength
                    if st <= 0:
                        rh = ratings(hh); ra = ratings(ha)
                    else:
                        rh = sos_adjust(ratings(hh), hh, hist, lg_shots, lg_xgps, st)
                        ra = sos_adjust(ratings(ha), ha, hist, lg_shots, lg_xgps, st)
                elif method == 'massey':
                    adj = massey_adjust_all(hist, lg_shots, lg_xgps)
                    rh = adj.get(H, ratings(hh)); ra = adj.get(A, ratings(ha))
                elif method == 'comboprior_prioropp':   # ΠΛΗΡΩΣ ΣΥΝΕΠΕΣ: team shrink-to-prior + prior-opp SoS
                    st = strength_fn(md) if strength_fn is not None else strength
                    rh0 = shrink_prior(ratings(hh), prevs.get(H, mean_tuple), len(hh['sf']), shrink_k)
                    ra0 = shrink_prior(ratings(ha), prevs.get(A, mean_tuple), len(ha['sf']), shrink_k)
                    if st <= 0:
                        rh, ra = rh0, ra0
                    else:
                        rh = sos_adjust_prioropp(rh0, hh, hist, prevs, mean_tuple, lg_shots, lg_xgps, st, shrink_k)
                        ra = sos_adjust_prioropp(ra0, ha, hist, prevs, mean_tuple, lg_shots, lg_xgps, st, shrink_k)
                elif method == 'caley_prioropp':   # SoS-only αλλα αντιπαλοι prior-anchored
                    st = strength_fn(md) if strength_fn is not None else strength
                    if st <= 0:
                        rh = ratings(hh); ra = ratings(ha)
                    else:
                        rh = sos_adjust_prioropp(ratings(hh), hh, hist, prevs, mean_tuple, lg_shots, lg_xgps, st, shrink_k)
                        ra = sos_adjust_prioropp(ratings(ha), ha, hist, prevs, mean_tuple, lg_shots, lg_xgps, st, shrink_k)
                elif method == 'shrink':   # LEVER B: strength = K (shrink prior strength)
                    rh = shrink_adjust(ratings(hh), len(hh['sf']), strength, lg_shots, lg_xgps)
                    ra = shrink_adjust(ratings(ha), len(ha['sf']), strength, lg_shots, lg_xgps)
                elif method == 'combo':    # shrink (K=shrink_k) ΜΕΤΑ SoS (strength)
                    rh = sos_adjust(shrink_adjust(ratings(hh), len(hh['sf']), shrink_k, lg_shots, lg_xgps),
                                    hh, hist, lg_shots, lg_xgps, strength)
                    ra = sos_adjust(shrink_adjust(ratings(ha), len(ha['sf']), shrink_k, lg_shots, lg_xgps),
                                    ha, hist, lg_shots, lg_xgps, strength)
                elif method == 'shrinkprior':   # shrink προς ΠΕΡΣΙΝΟ rating (strength = K)
                    rh = shrink_prior(ratings(hh), prevs.get(H, mean_tuple), len(hh['sf']), strength)
                    ra = shrink_prior(ratings(ha), prevs.get(A, mean_tuple), len(ha['sf']), strength)
                elif method == 'comboprior':    # shrink-προς-περσινο (K=shrink_k) ΜΕΤΑ SoS (strength)
                    rh = sos_adjust(shrink_prior(ratings(hh), prevs.get(H, mean_tuple), len(hh['sf']), shrink_k),
                                    hh, hist, lg_shots, lg_xgps, strength)
                    ra = sos_adjust(shrink_prior(ratings(ha), prevs.get(A, mean_tuple), len(ha['sf']), shrink_k),
                                    ha, hist, lg_shots, lg_xgps, strength)
                elif method == 'comboprior_promo':   # ΙΔΙΟ αλλα νεοφωτιστες → promo_tuple (αδυναμο) αντι μεσου
                    rh = sos_adjust(shrink_prior(ratings(hh), prevs.get(H, promo_tuple), len(hh['sf']), shrink_k),
                                    hh, hist, lg_shots, lg_xgps, strength)
                    ra = sos_adjust(shrink_prior(ratings(ha), prevs.get(A, promo_tuple), len(ha['sf']), shrink_k),
                                    ha, hist, lg_shots, lg_xgps, strength)
                else:
                    rh = ratings(hh); ra = ratings(ha)
                xg_h, xg_a = predict_from_ratings(rh, ra, lg_shots, lg_xgps, hf)
                out.append(dict(league=lg, season=sea, mid=r['mid'], date=r['date'],
                                home_name=id2name.get(H), away_name=id2name.get(A),
                                gd=r['hg'] - r['ag'], hg=r['hg'], ag=r['ag'],
                                md=min(len(hh['sf']), len(ha['sf'])),   # min prior games (noisier team)
                                real_hxg=r['h_xg'], real_axg=r['a_xg'],  # ΠΡΑΓΜΑΤΙΚΟ xG του αγωνα (για luck check)
                                xg_h=xg_h, xg_a=xg_a, model_sup=xg_h - xg_a))
            for tid, opp, sf, xf, sa, xa, gf, ga in [
                    (H, A, r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (A, H, r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', opp)]:
                    hist[tid][k].append(v)
    return pd.DataFrame(out)

def roi(B):
    r = B.pnl.values
    if len(r) == 0:
        return 0.0, 0.0, 0
    return r.mean(), r.std() / np.sqrt(len(r)), len(r)

def run_arm(M, id2name, BET, method, lo, hi, strength=1.0):
    P = build_preds(M, id2name, method=method, lo=lo, hi=hi, strength=strength)
    if len(P) == 0:
        return pd.DataFrame(), {}
    B = BET(P)
    return B, dict(preds=len(P), bets=len(B))

def main():
    # '5s' στα args → 5 σεζον (CORE7, season-aware odds)· αλλιως 2 σεζον production
    use5s = '5s' in sys.argv
    if use5s:
        leagues = CORE7; seasons = FIVE_SEASONS
        M, id2name = load_matches_5s(leagues, seasons)
        _reg, _resolvers = build_odds_layer(leagues, seasons)
        BET = lambda P: bet_signals_5s(P, _reg, _resolvers)
        print(f"[5-SEASON MODE: CORE7, {seasons}]\n")
    else:
        leagues = TOP5; seasons = ALL_SEASONS
        M, id2name = load_matches(leagues, seasons)
        _, fdn, Om = load_odds(leagues, seasons)
        resolve = make_resolver(fdn)
        BET = lambda P: bet_signals(P, Om, resolve)

    if len(sys.argv) > 1 and sys.argv[1] == 'integ5':
        # INTEGRITY GATE για 5 σεζον: coverage, unresolved, collision, games-without-odds ανα λιγκα-σεζον
        M5, id2 = load_matches_5s(CORE7, FIVE_SEASONS)
        P = build_preds(M5, id2, method='none', lo=0, hi=9999)   # ολες οι προβλεψεις (καθε ματς με ιστορικο)
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        print("INTEGRITY 5-SEASON (CORE 7) — coverage/unresolved/collision ανα λιγκα-σεζον\n")
        allbad = 0
        for lg in CORE7:
            Pl = P[P.league == lg]
            for sea in FIVE_SEASONS:
                Ps = Pl[Pl.season == sea]
                if len(Ps) == 0:
                    continue
                g = reg_of(sea); resolve = resolvers[g]; Om = reg[g]['Om']
                teams = set(Ps.home_name) | set(Ps.away_name)
                rev = {}
                for t in teams:
                    rev.setdefault(resolve(t), []).append(t)
                unresolved = sorted(rev.get(None, []))
                coll = {k: v for k, v in rev.items() if k is not None and len(v) > 1}
                matched = 0; gaps = []
                for _, r in Ps.iterrows():
                    rh = resolve(r['home_name']); ra = resolve(r['away_name'])
                    if picks.match_odds(Om, sea, rh, ra, r['date']) is not None:
                        matched += 1
                    else:
                        key_exists = (str(sea), rh, ra) in Om
                        gaps.append((r['home_name'], r['away_name'], r['date'], rh, ra, key_exists))
                cov = 100 * matched / len(Ps)
                flag = '' if (cov >= 99.9 and not unresolved and not coll) else '  ← ΠΡΟΒΛΗΜΑ'
                if flag:
                    allbad += 1
                print(f"  {lg:>12s} {sea}: cov {cov:5.1f}% ({matched}/{len(Ps)})"
                      + (f"  UNRESOLVED={unresolved}" if unresolved else "")
                      + (f"  COLLISION={coll}" if coll else "") + flag)
                for hn, an, dt, rh, ra, ke in gaps:
                    print(f"       gap: {hn} v {an} ({dt}) → fd[{rh} v {ra}] key_in_odds={ke}")
        print(f"\n{'='*60}\n{'ΟΛΑ ΚΑΘΑΡΑ ✓' if allbad == 0 else f'*** {allbad} λιγκα-σεζον με προβλημα ***'}")
        return

    def withmd(method, st):
        P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
        B = BET(P)
        if len(B) == 0:
            return B
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')

    if len(sys.argv) > 1 and sys.argv[1] == 'deep':
        BUCK = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        Bb = withmd('none', 0); Bs = withmd('caley', 1.5)
        print("═══ (A) per-λιγκα × σεζον  (Caley 1.5, window 7-14)  ROI(n) ═══")
        print(f"{'λιγκα':>13s} | " + " | ".join(f"{s:>9s}" for s in seasons) + " |     ΟΛΕΣ")
        for lg in leagues:
            cs = []
            for s in seasons:
                m, se, n = roi(Bs[(Bs.league == lg) & (Bs.season == s)])
                cs.append(f"{m:>+4.0%}·{n:>2d}")
            m, se, n = roi(Bs[Bs.league == lg])
            print(f"{lg:>13s} | " + " | ".join(f"{c:>9s}" for c in cs) + f" | {m:>+6.1%}·{n:>3d}")
        print("\n═══ (A) leave-one-league-out  (Caley 1.5, ολο 7-14) ═══")
        m, se, n = roi(Bs); print(f"  {'ΟΛΕΣ 7':>16s}: {m:>+6.1%}  (n={n})")
        for lg in leagues:
            m, se, n = roi(Bs[Bs.league != lg]); print(f"  {'χωρις ' + lg:>16s}: {m:>+6.1%}  (n={n})")
        print("\n═══ (C) md 7-8 ΜΟΝΟ — robustness (baseline → Caley1.5) ═══")
        print("  -- ανα λιγκα --")
        for lg in leagues:
            mb, _, nb = roi(Bb[(Bb.md <= 7) & (Bb.league == lg)])
            ms, _, ns = roi(Bs[(Bs.md <= 7) & (Bs.league == lg)])
            print(f"     {lg:>13s}: base {mb:>+6.1%}(n{nb:>2d}) → SoS {ms:>+6.1%}(n{ns:>2d})")
        print("  -- ανα σεζον --")
        for s in seasons:
            mb, _, nb = roi(Bb[(Bb.md <= 7) & (Bb.season == s)])
            ms, _, ns = roi(Bs[(Bs.md <= 7) & (Bs.season == s)])
            print(f"     {s:>13s}: base {mb:>+6.1%}(n{nb:>2d}) → SoS {ms:>+6.1%}(n{ns:>2d})")
        mb, _, nb = roi(Bb[Bb.md <= 7]); ms, _, ns = roi(Bs[Bs.md <= 7])
        print(f"     {'ΣΥΝΟΛΟ':>13s}: base {mb:>+6.1%}(n{nb}) → SoS {ms:>+6.1%}(n{ns})")
        print("\n═══ (A) SerieA ανα md-bucket (Caley 1.5) ═══")
        for lo_b, hi_b, lab in BUCK:
            m, _, n = roi(Bs[(Bs.league == 'SerieA') & (Bs.md >= lo_b) & (Bs.md <= hi_b)])
            print(f"     {lab:>9s}: {m:>+6.1%} (n={n})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'levers':
        BUCK = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        print("═══ (B1) SHRINKAGE-to-mean standalone (ΧΩΡΙΣ SoS), K sweep — μικρο K=βαρυ shrink ═══")
        print(f"{'K':>5s} | {'ΟΛΟ 7-14':>13s} | " + " | ".join(f"{lab:>12s}" for _, _, lab in BUCK))
        for K in [0, 3, 6, 10, 20]:
            B = withmd('none', 0) if K == 0 else withmd('shrink', K)
            m, _, n = roi(B); row = [f"{m:>+6.1%} n{n:>3d}"]
            for lo_b, hi_b, lab in BUCK:
                mm, _, nn = roi(B[(B.md >= lo_b) & (B.md <= hi_b)]); row.append(f"{mm:>+6.1%} n{nn:>2d}")
            tag = 'baseline' if K == 0 else f'K={K}'
            print(f"{tag:>5s} | {row[0]:>13s} | " + " | ".join(f"{c:>12s}" for c in row[1:]))
        print("\n═══ (B2) EDGE threshold sweep (baseline & Caley1.5, ολο 7-14) ═══")
        orig = picks.EDGE
        for E in [0.10, 0.12, 0.15]:
            picks.EDGE = E
            mb, _, nb = roi(withmd('none', 0)); ms, _, ns = roi(withmd('caley', 1.5))
            print(f"  edge≥{E:.0%}: baseline {mb:>+6.1%} (n={nb:>3d})   |   Caley1.5 {ms:>+6.1%} (n={ns:>3d})")
        picks.EDGE = orig
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'lososhow':
        METHODS = [('comboprior (raw-opp)', 'comboprior'), ('full (prior-opp)', 'comboprior_prioropp'),
                   ('SoS-only (prior-opp)', 'caley_prioropp')]
        STR = [1.5, 2.0, 2.25]
        data = {}
        for mname, method in METHODS:
            for st in STR:
                P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
                data[(mname, st)] = BET(P)
        Bb = BET(build_preds(M, id2name, method='none', lo=6, hi=13))
        mb, sb, nb = roi(Bb[Bb.season != '2122'])
        print(f"LOSO SHOWDOWN — 7-14, 4 σεζον OOS (τυνε strength σε 4, τεστ στην κρυμμενη)\n")
        print(f"  baseline (no tuning): {mb:>+6.1%} ±{sb:.1%} (n={nb})\n")
        print(f"{'εκδοχη':>22s} | {'POOLED OOS':>14s} | περ-σεζον (best-str)")
        for mname, _ in METHODS:
            pool = []; detail = []
            for S in seasons:
                if S == '2122':
                    continue
                best = max(STR, key=lambda st: roi(data[(mname, st)][data[(mname, st)].season != S])[0])
                held = data[(mname, best)][data[(mname, best)].season == S]
                pool.append(held); detail.append(f"{S}:{roi(held)[0]:+.0%}({best})")
            allp = pd.concat(pool); m, se, n = roi(allp)
            print(f"{mname:>22s} | {m:>+7.1%} ±{se:.1%} | " + "  ".join(detail))
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'trace':
        prior_all = full_season_ratings(M)
        lg, sea = 'EPL', '2526'; K = 10.0; STR = 1.5
        G = M[(M.league == lg) & (M.season == sea)].sort_values(['date', 'mid']).reset_index(drop=True)
        lg_shots = pd.concat([G.h_ns, G.a_ns]).mean()
        lg_xgps = pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum()
        hf = HFA_FIX[lg]; prevs = prior_all.get((lg, prev_season(sea)), {})
        mean_tuple = (lg_xgps, lg_xgps, lg_shots, lg_shots)
        hist = {}; target = None
        for _, r in G.iterrows():
            H, A = r['home'], r['away']; hh = hist.get(H); ha = hist.get(A)
            if (hh and ha and 8 <= len(hh['sf']) <= 10 and 8 <= len(ha['sf']) <= 10
                    and H in prevs and A in prevs):   # ΚΑΜΙΑ νεοφωτιστη
                target = (r, hh, ha); break
            for tid, opp, sf, xf, sa, xa, gf, ga in [
                    (H, A, r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (A, H, r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', opp)]:
                    hist[tid][k].append(v)
        r, hh, ha = target
        H, A = r['home'], r['away']
        f = lambda t: f"Ax={t[0]:.3f} Dx={t[1]:.3f} SF={t[2]:.2f} SA={t[3]:.2f}"
        print(f"ΜΑΤΣ: {id2name.get(H)} vs {id2name.get(A)}  ({r['date']}, {lg} {sea})")
        print(f"league: lg_xgps={lg_xgps:.3f}  lg_shots={lg_shots:.2f}  HFA={hf}\n")
        for who, hx in [('ΓΗΠΕΔΟΥΧΟΣ ' + str(id2name.get(H)), hh)]:
            n = len(hx['sf']); w = n / (n + K)
            raw = ratings(hx); prior = prevs.get(list(hist.keys())[0], mean_tuple) if False else prevs.get(H, mean_tuple)
            shrunk = shrink_prior(raw, prior, n, K)
            print(f"=== {who}  (n={n} ματς) ===")
            print(f"  raw φετινο:  {f(raw)}")
            print(f"  περσινο:     {f(prior)}    (w_φετινο={w:.2f})")
            print(f"  shrunk→prior:{f(shrunk)}")
            print(f"  αντιπαλοι (Dx=αμυνα τους, οδηγει το attack-SoS):")
            oraw, opri = [], []
            for o in hx['opp']:
                ho = hist.get(o); rr = ratings(ho); pp = prevs.get(o, mean_tuple)
                ss = shrink_prior(rr, pp, len(ho['sf']), K)
                oraw.append(rr[1]); opri.append(ss[1])
                print(f"     {id2name.get(o):<22s} raw_Dx={rr[1]:.3f}  prior-anchored_Dx={ss[1]:.3f}")
            mraw, mpri = wmean(oraw), wmean(opri)
            print(f"  μεσος αντιπαλος Dx:  raw={mraw:.3f}   prior-anchored={mpri:.3f}   (lg={lg_xgps:.3f})")
            fr = (lg_xgps / mraw) ** STR; fp = (lg_xgps / mpri) ** STR
            print(f"  attack-SoS factor (str {STR}):  raw-opp=(lg/{mraw:.3f})^{STR}={fr:.3f}   prior-opp={fp:.3f}\n")
            print(f"  → ΕΚΔΟΧΗ 1 comboprior (shrunk team × raw-opp SoS):   Ax {shrunk[0]:.3f}→{shrunk[0]*fr:.3f}")
            print(f"  → ΕΚΔΟΧΗ 2 full     (shrunk team × prior-opp SoS):   Ax {shrunk[0]:.3f}→{shrunk[0]*fp:.3f}")
            print(f"  → ΕΚΔΟΧΗ 3 SoS-only (RAW team × prior-opp SoS):      Ax {raw[0]:.3f}→{raw[0]*fp:.3f}")
        # τελικες προβλεψεις xG και για τις 3
        def full_rating(hx, method):
            raw = ratings(hx); n = len(hx['sf']); pr = prevs.get(hx is hh and H or A, mean_tuple)
            sh = shrink_prior(raw, pr, n, K)
            if method == 1:
                return sos_adjust(sh, hx, hist, lg_shots, lg_xgps, STR)
            if method == 2:
                return sos_adjust_prioropp(sh, hx, hist, prevs, mean_tuple, lg_shots, lg_xgps, STR, K)
            return sos_adjust_prioropp(raw, hx, hist, prevs, mean_tuple, lg_shots, lg_xgps, STR, K)
        print("\n=== ΤΕΛΙΚΗ ΠΡΟΒΛΕΨΗ xG (home vs away) ===")
        for m, nm in [(1, 'comboprior'), (2, 'full prior-opp'), (3, 'SoS-only prior-opp')]:
            xh, xa = predict_from_ratings(full_rating(hh, m), full_rating(ha, m), lg_shots, lg_xgps, hf)
            print(f"  {nm:>20s}: xG {xh:.2f} - {xa:.2f}   (sup {xh-xa:+.2f})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'fullconsist':
        def build_md(method, st):
            P = build_preds(M, id2name, method=method, lo=1, hi=13, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        def w(B, lo_b, hi_b):
            return roi(B[(B.md >= lo_b) & (B.md <= hi_b)])
        print("ΠΛΗΡΩΣ ΣΥΝΕΠΕΣ (team shrink-to-prior + prior-opp SoS) — md2-6 & md7-14 (5σ)\n")
        print(f"{'arm':>28s} | {'md 2-6':>14s} | {'md 7-14':>14s}")
        Bb = build_md('none', 0); b26 = w(Bb, 1, 5); b714 = w(Bb, 6, 13)
        print(f"{'baseline':>28s} | {b26[0]:>+7.1%} (n{b26[2]:>3d}) | {b714[0]:>+7.1%} (n{b714[2]:>3d})")
        Bc = build_md('comboprior', 1.5); c26 = w(Bc, 1, 5); c714 = w(Bc, 6, 13)
        print(f"{'comboprior 1.5 (raw-opp ref)':>28s} | {c26[0]:>+7.1%} (n{c26[2]:>3d}) | {c714[0]:>+7.1%} (n{c714[2]:>3d})")
        print("  ── comboprior_prioropp (πληρως συνεπες) ──")
        for st in [1.5, 2.0, 2.25, 2.5, 3.0]:
            B = build_md('comboprior_prioropp', st)
            a26 = w(B, 1, 5); a714 = w(B, 6, 13)
            print(f"{('full ' + str(st)):>28s} | {a26[0]:>+7.1%} (n{a26[2]:>3d}) | {a714[0]:>+7.1%} (n{a714[2]:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sosopp2':
        def build_md(method, st):
            P = build_preds(M, id2name, method=method, lo=1, hi=13, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        def w(B, lo_b, hi_b):
            return roi(B[(B.md >= lo_b) & (B.md <= hi_b)])
        Bb = build_md('none', 0); Braw = build_md('caley', 1.5)
        print("SoS prior-opp — EXTENDED strength, ΚΑΙ md2-6 ΚΑΙ md7-14 (5σ)\n")
        print(f"{'arm':>22s} | {'md 2-6':>14s} | {'md 7-14':>14s}")
        b26 = w(Bb, 1, 5); b714 = w(Bb, 6, 13)
        print(f"{'baseline':>22s} | {b26[0]:>+7.1%} (n{b26[2]:>3d}) | {b714[0]:>+7.1%} (n{b714[2]:>3d})")
        r26 = w(Braw, 1, 5); r714 = w(Braw, 6, 13)
        print(f"{'raw-opp 1.5 (ref)':>22s} | {r26[0]:>+7.1%} (n{r26[2]:>3d}) | {r714[0]:>+7.1%} (n{r714[2]:>3d})")
        print("  ── prior-opp ──")
        for st in [1.5, 2.0, 2.25, 2.5, 2.75, 3.0]:
            B = build_md('caley_prioropp', st)
            a26 = w(B, 1, 5); a714 = w(B, 6, 13)
            print(f"{('prior-opp ' + str(st)):>22s} | {a26[0]:>+7.1%} (n{a26[2]:>3d}) | {a714[0]:>+7.1%} (n{a714[2]:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sosopp':
        def armroi(method, st):
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
            return roi(BET(P))
        mb, seb, nb = armroi('none', 0)
        print("SoS STRENGTH SWEEP — αντιπαλοι RAW-φετινο vs PRIOR-αγκυρωμενοι (7-14, 5σ)\n")
        print(f"  baseline (χωρις SoS): {mb:>+6.1%} ±{seb:.1%} (n={nb})\n")
        print(f"{'strength':>9s} | {'SoS raw-opp (τωρα)':>20s} | {'SoS prior-opp (νεο)':>22s}")
        for st in [1.0, 1.25, 1.5, 1.75, 2.0]:
            r0, s0, n0 = armroi('caley', st)
            r1, s1, n1 = armroi('caley_prioropp', st)
            print(f"{st:>9.2f} | {r0:>+11.1%} (n{n0:>3d}) | {r1:>+13.1%} (n{n1:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'valuelayer':
        # 1) BASE: comboprior predictions → base_margin, residual
        Pb = build_preds(M, id2name, method='comboprior', lo=6, hi=40, strength=1.5)
        Pb['mid'] = Pb['mid'].astype(str)
        Pb['base_margin'] = Pb['xg_h'] - Pb['xg_a']; Pb['residual'] = Pb['gd'] - Pb['base_margin']
        base = Pb.set_index(['league', 'season', 'mid'])[['base_margin', 'residual', 'gd', 'md', 'home_name', 'away_name', 'date']].to_dict('index')
        # 2) STYLE walk-forward → directional phase-matchup features ανα (lg,sea,mid)
        S = pd.read_csv('teamgame_style_5s.csv'); S['season'] = S['season'].astype(str); S['mid'] = S['mid'].astype(str)
        feats = {}
        for (lg, sea), G in S.groupby(['league', 'season'], sort=False):
            G = G.sort_values(['date', 'mid']); acc = {}
            for mid, g in G.groupby('mid', sort=False):
                if len(g) != 2:
                    continue
                h = g[g.is_home == 1].iloc[0]; a = g[g.is_home == 0].iloc[0]; H, A = int(h['team']), int(a['team'])
                def sh(tid):
                    d = acc[tid]; ff, fr, fd = sum(d['xf_fb']), sum(d['xf_reg']), sum(d['xf_db']); ft = ff + fr + fd + 1e-9
                    af, ar, ad = sum(d['xa_fb']), sum(d['xa_reg']), sum(d['xa_db']); at = af + ar + ad + 1e-9
                    return (ff / ft, fr / ft, fd / ft, af / at, ar / at, ad / at)  # a_fb,a_reg,a_db,d_fb,d_reg,d_db
                if H in acc and A in acc and len(acc[H]['xf_fb']) >= 6 and len(acc[A]['xf_fb']) >= 6:
                    hs = sh(H); as_ = sh(A)
                    net_fb = hs[0] * as_[3] - as_[0] * hs[3]     # home-perspective net matchup ανα phase
                    net_reg = hs[1] * as_[4] - as_[1] * hs[4]
                    net_db = hs[2] * as_[5] - as_[2] * hs[5]
                    feats[(lg, str(sea), str(mid))] = (net_fb, net_reg, net_db)
                for _, r in g.iterrows():
                    tid = int(r['team']); acc.setdefault(tid, dict(xf_fb=[], xf_reg=[], xf_db=[], xa_fb=[], xa_reg=[], xa_db=[]))
                    for k in ['xf_fb', 'xf_reg', 'xf_db', 'xa_fb', 'xa_reg', 'xa_db']:
                        acc[tid][k].append(r[k])
        # 3) merge → dataset
        rows = []
        for key, (nfb, nreg, ndb) in feats.items():
            b = base.get(key)
            if b is None:
                continue
            rows.append(dict(league=key[0], season=key[1], mid=key[2], residual=b['residual'],
                             base_margin=b['base_margin'], gd=b['gd'], md=b['md'], nfb=nfb, nreg=nreg, ndb=ndb,
                             home_name=b['home_name'], away_name=b['away_name'], date=b['date']))
        D = pd.DataFrame(rows)
        print(f"VALUE-LAYER: residual ~ phase-matchups, LOSO. n={len(D)} ματς (>=6 prior, 5σ)\n")
        # 4) LOSO linear fit residual ~ nfb+nreg+ndb
        FE = ['nfb', 'nreg', 'ndb']
        D['pred'] = np.nan
        for s in FIVE_SEASONS:
            tr = D[D.season != s]; te = D[D.season == s]
            if len(te) == 0:
                continue
            X = np.column_stack([np.ones(len(tr))] + [tr[f].values for f in FE]); y = tr['residual'].values
            coef = np.linalg.lstsq(X, y, rcond=None)[0]
            Xte = np.column_stack([np.ones(len(te))] + [te[f].values for f in FE])
            D.loc[te.index, 'pred'] = Xte @ coef
        # coefficients (full-sample, για ερμηνεια)
        Xf = np.column_stack([np.ones(len(D))] + [D[f].values for f in FE])
        cf = np.linalg.lstsq(Xf, D['residual'].values, rcond=None)[0]
        print("συντελεστες (full-sample):  intercept=%.3f  nfb=%.3f  nreg=%.3f  ndb=%.3f" % tuple(cf))
        corr = np.corrcoef(D['pred'], D['residual'])[0, 1]
        print(f"OOS correlation(predicted residual, actual residual): {corr:+.4f}")
        print(f"  (residual std={D['residual'].std():.2f}, predicted std={D['pred'].std():.3f})\n")
        # 5) FAVORITE GATE: βοηθαει το style-predicted residual το favorite cover;
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        favrows = []
        for _, r in D.iterrows():
            g = reg_of(r['season']); res = resolvers[g]
            o = picks.match_odds(reg[g]['Om'], r['season'], res(r['home_name']), res(r['away_name']), r['date'])
            if o is None:
                continue
            line = o.get('AHCh'); oh, oa, _ = picks.ah_odds(o)
            if pd.isna(line) or oh is None:
                continue
            line = float(line)
            if line < 0:
                fud, fodds, fside, fsig = line, oh, 1, r['pred']        # home fav: θετικο pred βοηθαει
            elif line > 0:
                fud, fodds, fside, fsig = -line, oa, -1, -r['pred']     # away fav: αρνητικο pred βοηθαει
            else:
                continue
            if abs(fud) >= 0.5 and picks.OMIN <= fodds <= picks.OMAX:
                favrows.append(dict(pnl=picks.settle(r['gd'], fside, fud, fodds), fav_signal=fsig, md=r['md']))
        F = pd.DataFrame(favrows)
        def rr(x):
            return f"{x.pnl.mean():>+7.1%} (n{len(x):>4d})" if len(x) else "—"
        print(f"── FAVORITE GATE: split κατα style-signal (predicted residual προς φαβορι) ──")
        print(f"  ΟΛΑ τα φαβορι: {rr(F)}")
        med = F.fav_signal.median(); q70 = F.fav_signal.quantile(0.70); q85 = F.fav_signal.quantile(0.85)
        print(f"  signal ΥΨΗΛΟ(>μεσο): {rr(F[F.fav_signal > med])}   ΧΑΜΗΛΟ: {rr(F[F.fav_signal <= med])}")
        print(f"  signal top-30%: {rr(F[F.fav_signal >= q70])}   top-15%: {rr(F[F.fav_signal >= q85])}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'stylefav':
        S = pd.read_csv('teamgame_style_5s.csv'); S['season'] = S['season'].astype(str)
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        _, id2name = load_matches_5s(CORE7, FIVE_SEASONS)
        rows = []
        for (lg, sea), G in S.groupby(['league', 'season'], sort=False):
            G = G.sort_values(['date', 'mid']); acc = {}
            for mid, g in G.groupby('mid', sort=False):
                if len(g) != 2:
                    continue
                h = g[g.is_home == 1].iloc[0]; a = g[g.is_home == 0].iloc[0]
                H, A, date = int(h['team']), int(a['team']), h['date']
                def prof(tid):
                    d = acc[tid]
                    ff, fr, fd = sum(d['xf_fb']), sum(d['xf_reg']), sum(d['xf_db']); ft = ff + fr + fd + 1e-9
                    af, ar, ad = sum(d['xa_fb']), sum(d['xa_reg']), sum(d['xa_db']); at = af + ar + ad + 1e-9
                    return dict(fb_for=ff / ft, reg_for=fr / ft, db_for=fd / ft, fb_ag=af / at, reg_ag=ar / at, db_ag=ad / at)
                if H in acc and A in acc and len(acc[H]['xf_fb']) >= 6 and len(acc[A]['xf_fb']) >= 6:
                    gg = reg_of(sea)
                    o = picks.match_odds(reg[gg]['Om'], sea, resolvers[gg](id2name.get(H)), resolvers[gg](id2name.get(A)), date)
                    if o is not None:
                        line = o.get('AHCh'); oh, oa, _ = picks.ah_odds(o)
                        if pd.notna(line) and oh is not None:
                            line = float(line)
                            fav = opp = fodds = fud = fside = None
                            if line < 0:
                                fav, opp, fodds, fud, fside = prof(H), prof(A), oh, line, 1
                            elif line > 0:
                                fav, opp, fodds, fud, fside = prof(A), prof(H), oa, -line, -1
                            if fav is not None and abs(fud) >= 0.5 and picks.OMIN <= fodds <= picks.OMAX:
                                rows.append(dict(league=lg, season=sea, md=min(len(acc[H]['xf_fb']), len(acc[A]['xf_fb'])),
                                                 pnl=picks.settle(h['gf'] - a['gf'], fside, fud, fodds),
                                                 mu_fb=fav['fb_for'] * opp['fb_ag'], mu_reg=fav['reg_for'] * opp['reg_ag'],
                                                 mu_db=fav['db_for'] * opp['db_ag']))
                for _, r in g.iterrows():
                    tid = int(r['team']); acc.setdefault(tid, dict(xf_fb=[], xf_reg=[], xf_db=[], xa_fb=[], xa_reg=[], xa_db=[]))
                    for k in ['xf_fb', 'xf_reg', 'xf_db', 'xa_fb', 'xa_reg', 'xa_db']:
                        acc[tid][k].append(r[k])
        B = pd.DataFrame(rows)
        def rr(sub):
            return f"{sub.pnl.mean():>+7.1%} (n{len(sub):>4d})" if len(sub) else "  —"
        print(f"STYLE-FAV MATCHUP: ΟΛΑ τα φαβορι (|line|>=0.5, odds 1.70-2.10, >=6 prior), 5σ")
        print("matchup = (επιθεση φαβορι στην κατηγορια) × (αδυναμια αντιπαλου στην ιδια)\n")
        print(f"  ΣΥΝΟΛΟ φαβορι: {rr(B)}\n")
        for feat, lab in [('mu_db', 'ΣΤΗΜΕΝΕΣ matchup (φαβορι σκοραρει στημενες × αντιπαλος δεχεται στημενες)'),
                          ('mu_fb', 'ΚΟΝΤΡΑ matchup (φαβορι στην κοντρα × αντιπαλος δεχεται στην κοντρα)'),
                          ('mu_reg', 'OPEN-PLAY matchup (φαβορι buildup × αντιπαλος δεχεται open-play)')]:
            med = B[feat].median(); q75 = B[feat].quantile(0.75); q90 = B[feat].quantile(0.90)
            print(f"── {lab} ──")
            print(f"     ΥΨΗΛΟ(>μεσο): {rr(B[B[feat] > med])}   ΧΑΜΗΛΟ: {rr(B[B[feat] <= med])}")
            print(f"     top-25%: {rr(B[B[feat] >= q75])}   top-10%: {rr(B[B[feat] >= q90])}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'mechtest':
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        orig_db = picks.DRAW_BOOST
        def eval_bets(P, kind):
            out = []
            for _, r in P.iterrows():
                g = reg_of(r['season']); res = resolvers[g]
                o = picks.match_odds(reg[g]['Om'], r['season'], res(r['home_name']), res(r['away_name']), r['date'])
                if o is None:
                    continue
                line = o.get('AHCh'); oh, oa, _ = picks.ah_odds(o)
                if pd.isna(line) or oh is None:
                    continue
                dist = picks.gd_dist(min(max(r['xg_h'], 0.05), 6.0), min(max(r['xg_a'], 0.05), 6.0))
                for side, ud, odds in [(1, float(line), oh), (-1, -float(line), oa)]:
                    keep = (ud >= picks.MIN_LINE) if kind == 'under' else (ud <= -picks.MIN_LINE)
                    if not keep or not (picks.OMIN <= odds <= picks.OMAX):
                        continue
                    pw, pp = picks.p_cover(dist, side, ud)
                    if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= picks.EDGE:
                        if pd.notna(r.get('gd')):
                            out.append(picks.settle(r['gd'], side, ud, odds))
            a = np.array(out)
            return (a.mean() if len(a) else 0.0, len(a))
        print("MECH TEST (comboprior 1.5, 5 σεζον). ΜΟΝΟ test-mode — δεν αγγιζει το live")
        Ps = {}
        for clab, csv in [('compressed', 'teamgame_inputs_5s.csv'), ('NO-comp', 'teamgame_inputs_5s_nocomp.csv')]:
            M2, id2 = load_matches_5s(CORE7, FIVE_SEASONS, csv=csv)
            Ps[clab] = build_preds(M2, id2, method='comboprior', lo=1, hi=40, strength=1.5)
        for wlab, lo_b, hi_b in [('ΟΛΗ ΣΕΖΟΝ', 1, 40), ('7-14', 6, 13), ('15+', 14, 40)]:
            print(f"\n═══ {wlab} ═══")
            print(f"{'inputs':>12s} {'score-model':>12s} | {'AΟΥΤΣΑΙΝΤΕΡ':>18s} | {'ΦΑΒΟΡΙ':>18s}")
            for clab in ['compressed', 'NO-comp']:
                Pw = Ps[clab][(Ps[clab].md >= lo_b) & (Ps[clab].md <= hi_b)]
                for dlab, db in [('draw-boost', orig_db), ('NO-boost', 1.0)]:
                    picks.DRAW_BOOST = db
                    um, un = eval_bets(Pw, 'under'); fm, fn = eval_bets(Pw, 'fav')
                    print(f"{clab:>12s} {dlab:>12s} | {um:>+7.1%} (n{un:>4d}) | {fm:>+7.1%} (n{fn:>4d})")
        picks.DRAW_BOOST = orig_db
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'favdiag':
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        P = build_preds(M, id2name, method='comboprior', lo=6, hi=13, strength=1.5)
        def clamp(x):
            return min(max(x, 0.05), 6.0)
        c = dict(matches=0, u_odds=0, u_edge=0, f_odds=0, f_edge=0, f_oddsany=0, f_shortcut=0)
        for _, r in P.iterrows():
            g = reg_of(r['season']); res = resolvers[g]
            o = picks.match_odds(reg[g]['Om'], r['season'], res(r['home_name']), res(r['away_name']), r['date'])
            if o is None:
                continue
            line = o.get('AHCh'); oh, oa, _ = picks.ah_odds(o)
            if pd.isna(line) or oh is None:
                continue
            c['matches'] += 1
            dist = picks.gd_dist(clamp(r['xg_h']), clamp(r['xg_a']))
            for side, ud, odds in [(1, float(line), oh), (-1, -float(line), oa)]:
                if ud >= picks.MIN_LINE:                          # underdog side
                    if picks.OMIN <= odds <= picks.OMAX:
                        c['u_odds'] += 1
                        pw, pp = picks.p_cover(dist, side, ud)
                        if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= picks.EDGE:
                            c['u_edge'] += 1
                elif ud <= -picks.MIN_LINE:                       # favorite side
                    if odds < picks.OMIN:
                        c['f_shortcut'] += 1                      # πολυ κοντες αποδοσεις (κοβονται)
                    if picks.OMIN <= odds <= picks.OMAX:
                        c['f_odds'] += 1
                        pw, pp = picks.p_cover(dist, side, ud)
                        if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= picks.EDGE:
                            c['f_edge'] += 1
        print("ΔΙΑΓΝΩΣΤΙΚΟ ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΙΝΤΕΡ (7-14)\n")
        print(f"  ματς με odds: {c['matches']}")
        print(f"  ΑΟΥΤΣΑΙΝΤΕΡ: πλευρες σε odds-range 1.70-2.10 = {c['u_odds']}  →  περνανε edge≥10% = {c['u_edge']}")
        print(f"  ΦΑΒΟΡΙ:      πλευρες σε odds-range 1.70-2.10 = {c['f_odds']}  →  περνανε edge≥10% = {c['f_edge']}")
        print(f"  ΦΑΒΟΡΙ με odds <1.70 (κοβονται απο φιλτρο): {c['f_shortcut']}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'markets':
        reg, resolvers = build_odds_layer(CORE7, FIVE_SEASONS)
        P = build_preds(M, id2name, method='comboprior', lo=1, hi=40, strength=1.5)
        def clamp(x):
            return min(max(x, 0.05), 6.0)
        def p_over25(lh, la):
            ar = np.arange(13); ph = np.exp(-lh) * lh ** ar / np.array(picks.F, float)
            pa = np.exp(-la) * la ** ar / np.array(picks.F, float)
            Pm = np.outer(ph, pa)
            for i in range(13):
                Pm[i, i] *= picks.DRAW_BOOST
            Pm /= Pm.sum()
            return float(sum(Pm[i, j] for i in range(13) for j in range(13) if i + j >= 3))
        def bet_fav(P):
            rows = []
            for _, r in P.iterrows():
                g = reg_of(r['season']); Om = reg[g]['Om']; res = resolvers[g]
                o = picks.match_odds(Om, r['season'], res(r['home_name']), res(r['away_name']), r['date'])
                if o is None:
                    continue
                line = o.get('AHCh'); oh, oa, _ = picks.ah_odds(o)
                if pd.isna(line) or oh is None:
                    continue
                dist = picks.gd_dist(clamp(r['xg_h']), clamp(r['xg_a']))
                for side, ud, odds in [(1, float(line), oh), (-1, -float(line), oa)]:
                    if ud > 0 or not (picks.OMIN <= odds <= picks.OMAX):
                        continue                                 # ΦΑΒΟΡΙ: ud <= 0 (μαζι pick'em & -0.25)
                    pw, pp = picks.p_cover(dist, side, ud)
                    if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= picks.EDGE:
                        rows.append(dict(season=r['season'], md=r['md'], hcap=round(ud, 2),
                                         pnl=picks.settle(r['gd'], side, ud, odds) if pd.notna(r.get('gd')) else np.nan))
            return pd.DataFrame(rows)
        def bet_goals(P):
            rows = []
            for _, r in P.iterrows():
                if r['season'] not in OLD_SEASONS:
                    continue
                Om = reg['old']['Om']; res = resolvers['old']
                o = picks.match_odds(Om, r['season'], res(r['home_name']), res(r['away_name']), r['date'])
                if o is None:
                    continue
                oo, uo = o.get('PC>2.5'), o.get('PC<2.5')
                if pd.isna(oo) or pd.isna(uo):
                    continue
                po = p_over25(clamp(r['xg_h']), clamp(r['xg_a'])); tot = r['hg'] + r['ag']
                for is_over, p, odds in [(True, po, float(oo)), (False, 1 - po, float(uo))]:
                    if not (picks.OMIN <= odds <= picks.OMAX):
                        continue
                    if p * (odds - 1) * (1 - picks.MARGIN) - (1 - p) >= picks.EDGE:
                        win = (tot >= 3) if is_over else (tot < 3)
                        rows.append(dict(season=r['season'], md=r['md'], over=is_over, pnl=(odds - 1) if win else -1.0))
            return pd.DataFrame(rows)
        Bu = BET(P)
        ku = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(columns={'home_name': 'home', 'away_name': 'away'})
        Bu = Bu.merge(ku, on=['league', 'season', 'date', 'home', 'away'], how='left')
        Bf, Bg = bet_fav(P), bet_goals(P)
        print("ΑΠΟΚΛΕΙΣΜΕΝΑ MARKETS στο 7-14 & 15+ (comboprior 1.5). γκολς=μονο 2122-2324\n")
        print(f"{'market':>26s} | {'7-14':>16s} | {'15+':>16s}")
        goals_over = Bg[Bg.over == True] if len(Bg) else Bg
        goals_under = Bg[Bg.over == False] if len(Bg) else Bg
        for nm, B in [('underdog +hcap (δικο μας)', Bu), ('ΦΑΒΟΡΙ -hcap', Bf),
                      ('OVER 2.5 γκολς', goals_over), ('UNDER 2.5 γκολς', goals_under)]:
            w1 = B[(B.md >= 6) & (B.md <= 13)]; w2 = B[B.md >= 14]
            m1, s1, n1 = roi(w1); m2, s2, n2 = roi(w2)
            print(f"{nm:>26s} | {m1:>+7.1%} (n{n1:>4d}) | {m2:>+7.1%} (n{n2:>4d})")
        print("\n── ΦΑΒΟΡΙ ανα γραμμη (7-14 | 15+) ──")
        for hc in sorted(Bf.hcap.unique()):
            sub = Bf[Bf.hcap == hc]; w1 = sub[(sub.md >= 6) & (sub.md <= 13)]; w2 = sub[sub.md >= 14]
            m1, s1, n1 = roi(w1); m2, s2, n2 = roi(w2)
            print(f"  γραμμη {hc:>+5.2f}: {m1:>+7.1%} (n{n1:>3d}) | {m2:>+7.1%} (n{n2:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'check2324b':
        P = build_preds(M, id2name, method='comboprior', lo=6, hi=13, strength=1.5)
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md', 'real_hxg', 'real_axg']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        xp = []
        for _, r in B.iterrows():
            dist = picks.gd_dist(max(r['real_hxg'], 0.05), max(r['real_axg'], 0.05))
            pw, pp = picks.p_cover(dist, int(r['side']), r['hcap']); xp.append(pw * (r['odds'] - 1) - (1 - pw - pp))
        B['exp_pnl'] = xp
        B24 = B[B.season == '2324']
        print("2324 — comboprior bets: actual vs xG-exp + odds sanity ανα λιγκα\n")
        print(f"{'λιγκα':>13s} | {'actual':>8s} {'xG-exp':>8s} | {'n':>3s} | {'odds min/mean/max':>18s} | {'|line| mean':>10s}")
        for lg in ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie', 'ΟΛΕΣ']:
            sub = B24 if lg == 'ΟΛΕΣ' else B24[B24.league == lg]
            if len(sub) == 0:
                print(f"{lg:>13s} | —"); continue
            a = sub.pnl.mean(); x = sub.exp_pnl.mean()
            om, oa, ox = sub.odds.min(), sub.odds.mean(), sub.odds.max()
            lm = sub.hcap.abs().mean()
            print(f"{lg:>13s} | {a:>+7.1%} {x:>+7.1%} | {len(sub):>3d} | {om:.2f}/{oa:.2f}/{ox:.2f}      | {lm:>10.2f}")
        # συγκριση: μεση αποδοση 2324 vs αλλες σεζον (μηπως corrupt)
        print(f"\n  odds mean ανα σεζον (ολες οι bets): " + "  ".join(f"{s}:{B[B.season==s].odds.mean():.2f}" for s in FIVE_SEASONS))
        print(f"  cover-rate (actual) 2324: {(B24.pnl>0).mean():.1%}   xG cover: {(1-0):.0%}  (n={len(B24)})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'table714':
        ARMS = [
            ('baseline',                    'none', 0),
            ('Caley 1.5 (χωρις shrink, raw-opp)',   'caley', 1.5),
            ('prior-opp 2.25 (χωρις shrink)',       'caley_prioropp', 2.25),
            ('comboprior 1.5 (ΜΕ shrink, raw-opp)', 'comboprior', 1.5),
            ('full 2.25 (ΜΕ shrink, prior-opp)',    'comboprior_prioropp', 2.25),
        ]
        print("ΟΛΟ ΤΟ 7-14 (5σ) — actual ROI\n")
        print(f"{'εκδοχη':>36s} | {'ΟΛΕΣ':>13s} | " + " ".join(f"{s:>7s}" for s in FIVE_SEASONS))
        for label, method, st in ARMS:
            B = BET(build_preds(M, id2name, method=method, lo=6, hi=13, strength=st))
            m, se, n = roi(B)
            cells = []
            for s in FIVE_SEASONS:
                ms = roi(B[B.season == s])[0]; cells.append(f"{ms:>+6.1%}")
            print(f"{label:>36s} | {m:>+6.1%}±{se:.1%} | " + " ".join(f"{c:>7s}" for c in cells))
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'md78split':
        prior_all = full_season_ratings(M); name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            return None if (prev is None or tid is None) else (tid not in prev)
        for cfg, method, st in [('baseline', 'none', 0), ('comboprior', 'comboprior', 1.5)]:
            P = build_preds(M, id2name, method=method, lo=6, hi=7, strength=st)   # md 7-8
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md', 'real_hxg', 'real_axg']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
            B = B[B.season != '2122'].copy()
            betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in B.iterrows()]
            B['bet_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, betname)]
            xp = []
            for _, r in B.iterrows():
                dist = picks.gd_dist(max(r['real_hxg'], 0.05), max(r['real_axg'], 0.05))
                pw, pp = picks.p_cover(dist, int(r['side']), r['hcap']); xp.append(pw * (r['odds'] - 1) - (1 - pw - pp))
            B['exp_pnl'] = xp
            print(f"\n═══ {cfg} — md7-8 (χωρις 2122) ═══")
            a, se, n = roi(B); print(f"  ΟΛΑ:          actual {a:>+7.1%}  xG-exp {B.exp_pnl.mean():>+7.1%}  (n={n})")
            N = B[B.bet_new == True]; a, se, n = roi(N); print(f"  νεοφωτιστες:  actual {a:>+7.1%}  xG-exp {N.exp_pnl.mean() if len(N) else 0:>+7.1%}  (n={n})")
            E = B[B.bet_new == False]; a, se, n = roi(E); print(f"  καθιερωμενες: actual {a:>+7.1%}  xG-exp {E.exp_pnl.mean() if len(E) else 0:>+7.1%}  (n={n})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'newseason':
        prior_all = full_season_ratings(M); name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            return None if (prev is None or tid is None) else (tid not in prev)
        P = build_preds(M, id2name, method='comboprior', lo=1, hi=40, strength=1.5)   # ΟΛΗ η σεζον
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md', 'real_hxg', 'real_axg']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        B = B[B.season != '2122'].copy()
        betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in B.iterrows()]
        B['bet_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, betname)]
        expp = []
        for _, r in B.iterrows():
            dist = picks.gd_dist(max(r['real_hxg'], 0.05), max(r['real_axg'], 0.05))
            pw, pp = picks.p_cover(dist, int(r['side']), r['hcap'])
            expp.append(pw * (r['odds'] - 1) - (1 - pw - pp))
        B['exp_pnl'] = expp
        BUCK = [(1, 5, 'md 2-6'), (6, 13, 'md 7-14'), (14, 20, 'md 15-21'), (21, 29, 'md 22-30'), (30, 40, 'md 31+')]
        print("NEWCOMER-BETS ανα παραθυρο σεζον (SoS+περσινο, 4 σεζον). actual | xG-exp | n\n")
        print(f"{'window':>10s} | {'ΝΕΟΦΩΤΙΣΤΕΣ actual':>18s} | {'xG-exp':>8s} | {'n':>4s} || {'καθιερ. actual':>14s} | {'n':>4s}")
        for lo_b, hi_b, lab in BUCK:
            N = B[(B.bet_new == True) & (B.md >= lo_b) & (B.md <= hi_b)]
            E = B[(B.bet_new == False) & (B.md >= lo_b) & (B.md <= hi_b)]
            na, _, nn = roi(N); ea, _, ne = roi(E)
            nx = N.exp_pnl.mean() if len(N) else 0
            print(f"{lab:>10s} | {na:>+16.1%} | {nx:>+7.1%} | {nn:>4d} || {ea:>+12.1%} | {ne:>4d}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'luck':
        prior_all = full_season_ratings(M); name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            return None if (prev is None or tid is None) else (tid not in prev)
        P = build_preds(M, id2name, method='comboprior', lo=6, hi=13, strength=1.5)
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md', 'real_hxg', 'real_axg']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        B = B[B.season != '2122'].copy()
        betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in B.iterrows()]
        B['bet_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, betname)]
        expp = []
        for _, r in B.iterrows():
            dist = picks.gd_dist(max(r['real_hxg'], 0.05), max(r['real_axg'], 0.05))
            pw, pp = picks.p_cover(dist, int(r['side']), r['hcap'])
            expp.append(pw * (r['odds'] - 1) - (1 - pw - pp))
        B['exp_pnl'] = expp
        def show(label, sub):
            if len(sub) == 0:
                print(f"  {label:>26s}: —"); return
            a, x = sub.pnl.mean(), sub.exp_pnl.mean()
            print(f"  {label:>26s}: actual {a:>+7.1%}  |  xG-exp {x:>+7.1%}  |  luck {a-x:>+6.1%}  (n={len(sub)})")
        print("═══ LUCK vs xG — ολο 7-14 (SoS+περσινο, χωρις 2122). luck>0 = τυχεροι ═══\n")
        show('ΟΛΑ 7-14', B)
        show('νεοφωτιστες', B[B.bet_new == True])
        show('καθιερωμενες', B[B.bet_new == False])
        E = B[B.bet_new == False]
        show('  καθιερ. ΓΗΠΕΔΟΥΧΟΣ', E[E.side == 1])
        show('  καθιερ. ΦΙΛΟΞΕΝ.', E[E.side == -1])
        print()
        show('ΟΛΟΙ γηπεδουχοι', B[B.side == 1])
        show('ΟΛΟΙ φιλοξενουμενοι', B[B.side == -1])
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'newluck':
        prior_all = full_season_ratings(M); name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            return None if (prev is None or tid is None) else (tid not in prev)
        P = build_preds(M, id2name, method='comboprior', lo=6, hi=13, strength=1.5)
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md', 'real_hxg', 'real_axg']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        B = B[B.season != '2122'].copy()
        betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in B.iterrows()]
        B['bet_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, betname)]
        N = B[B.bet_new == True].copy()
        # xG-based P(cover) απο το ΠΡΑΓΜΑΤΙΚΟ xG του αγωνα
        expp, xcov = [], []
        for _, r in N.iterrows():
            dist = picks.gd_dist(max(r['real_hxg'], 0.05), max(r['real_axg'], 0.05))
            pw, pp = picks.p_cover(dist, int(r['side']), r['hcap'])
            expp.append(pw * (r['odds'] - 1) - (1 - pw - pp)); xcov.append(pw + 0.5 * pp)
        N['exp_pnl'] = expp; N['xg_cover'] = xcov
        N['won'] = (N.pnl > 0).astype(float)
        print("═══ NEWCOMER-BETS: τυχη vs xG (SoS+περσινο, 7-14, χωρις 2122) ═══\n")
        print(f"  n = {len(N)} bets")
        print(f"  ACTUAL ROI:        {N.pnl.mean():>+7.1%}")
        print(f"  xG-EXPECTED ROI:   {N.exp_pnl.mean():>+7.1%}   (βασει realized xG + ιδιες αποδοσεις)")
        print(f"  → luck gap:        {N.pnl.mean() - N.exp_pnl.mean():>+7.1%}  (θετικο=τυχεροι)")
        print(f"  ACTUAL cover rate: {N.won.mean():>7.1%}")
        print(f"  xG cover prob:     {N.xg_cover.mean():>7.1%}")
        print("\n── ανα σεζον (actual ROI newcomer-bets) ──")
        for s in seasons:
            if s == '2122':
                continue
            Ns = N[N.season == s]; m, se, n = roi(Ns)
            xe = Ns.exp_pnl.mean() if len(Ns) else 0
            print(f"  {s}: actual {m:>+7.1%} (n{n:>2d})   xG-exp {xe:>+7.1%}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'promotest':
        prior_all = full_season_ratings(M)
        name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            if prev is None or tid is None:
                return None
            return tid not in prev
        for cfg, method in [('SoS+περσινο (μεσος)', 'comboprior'), ('SoS+περσινο (ΑΔΥΝΑΜΟ promo)', 'comboprior_promo')]:
            B = withmd(method, 1.5)
            m_all, se_all, n_all = roi(B)
            Bx = B[B.season != '2122'].copy()
            betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in Bx.iterrows()]
            Bx['bet_new'] = [is_new(l, s, n) for l, s, n in zip(Bx.league, Bx.season, betname)]
            print(f"\n═══ {cfg} ═══")
            print(f"  ΟΛΟ 7-14 (ολες σεζον):  {m_all:>+7.1%} ±{se_all:.1%} (n={n_all})")
            mn, _, nn = roi(Bx[Bx.bet_new == True]); print(f"  bets ΣΕ νεοφωτιστη:      {mn:>+7.1%} (n={nn})")
            mo, _, no = roi(Bx[Bx.bet_new == False]); print(f"  bets ΟΧΙ σε νεοφωτιστη:  {mo:>+7.1%} (n={no})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'newcomer':
        prior_all = full_season_ratings(M)
        name2id = {v: k for k, v in id2name.items()}
        def is_new(lg, sea, name):
            tid = name2id.get(name); prev = prior_all.get((lg, prev_season(sea)))
            if prev is None or tid is None:
                return None                       # 2122 ή αγνωστο
            return tid not in prev                # νεοφωτιστη = δεν ηταν περσι στην κατηγορια
        for cfg, method, st in [('baseline', 'none', 0), ('SoS+περσινο', 'comboprior', 1.5)]:
            B = withmd(method, st)
            B = B[B.season != '2122'].copy()      # 2122 δεν εχει prior
            betname = [(r['home'] if r['side'] == 1 else r['away']) for _, r in B.iterrows()]
            oppname = [(r['away'] if r['side'] == 1 else r['home']) for _, r in B.iterrows()]
            B['bet_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, betname)]
            B['opp_new'] = [is_new(l, s, n) for l, s, n in zip(B.league, B.season, oppname)]
            print(f"\n═══ {cfg} — 7-14 (χωρις 2122) ═══")
            m, se, n = roi(B); print(f"  ΟΛΑ 7-14:            {m:>+7.1%} ±{se:.1%} (n={n})")
            m, se, n = roi(B[B.bet_new == True]); print(f"  ΠΟΝΤΑΡΟΥΜΕ νεοφωτιστη: {m:>+7.1%} (n={n})")
            m, se, n = roi(B[B.opp_new == True]); print(f"  αντιπαλος νεοφωτιστη:  {m:>+7.1%} (n={n})")
            m, se, n = roi(B[(B.bet_new == False) & (B.opp_new == False)]); print(f"  ΚΑΜΙΑ νεοφωτιστη:      {m:>+7.1%} (n={n})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'hfacurve':
        M5, _ = load_matches_5s(CORE7, FIVE_SEASONS)
        MAXMD = 40; W = 2   # rolling ±2 αγωνιστικες
        for lg in CORE7:
            L = M5[M5.league == lg]
            hx = [0.0] * MAXMD; ax = [0.0] * MAXMD; cnt = [0] * MAXMD
            for sea, G in L.groupby('season'):
                G = G.sort_values(['date', 'mid']); prior = {}
                for _, r in G.iterrows():
                    H, A = r['home'], r['away']; md = min(prior.get(H, 0), prior.get(A, 0))
                    if md < MAXMD:
                        hx[md] += r['h_xg']; ax[md] += r['a_xg']; cnt[md] += 1
                    prior[H] = prior.get(H, 0) + 1; prior[A] = prior.get(A, 0) + 1
            out = []
            for md in range(MAXMD):
                lo, hi = max(0, md - W), min(MAXMD, md + W + 1)
                sh, sa = sum(hx[lo:hi]), sum(ax[lo:hi]); nn = sum(cnt[lo:hi])
                out.append(round((sh / sa) ** 0.5, 4) if sa > 0 and nn >= 20 else None)
            print(f"{lg}|{HFA_FIX[lg]}|{out}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'hfa':
        M5, _ = load_matches_5s(CORE7, FIVE_SEASONS)
        print("WALK-FORWARD HFA (μονο απο ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον) vs FIXED (look-ahead)")
        print("HFA = sqrt(Σhome / Σaway).  wf = cumulative prior seasons.  own = ιδια σεζον (in-sample ref)\n")
        for lg in CORE7:
            L = M5[M5.league == lg]
            print(f"── {lg}  (fixed={HFA_FIX[lg]:.3f}) ──")
            phx = pax = phg = pag = 0.0
            for sea in FIVE_SEASONS:
                S = L[L.season == sea]
                hx, ax = S.h_xg.sum(), S.a_xg.sum(); hg, ag = S.hg.sum(), S.ag.sum()
                own_x = (hx / ax) ** 0.5; own_g = (hg / ag) ** 0.5
                wf_x = (phx / pax) ** 0.5 if pax > 0 else float('nan')
                wf_g = (phg / pag) ** 0.5 if pag > 0 else float('nan')
                dx = wf_x - HFA_FIX[lg] if pax > 0 else float('nan')
                print(f"   {sea}: wf(xG)={wf_x:.3f}  wf(goals)={wf_g:.3f}   (own xG={own_x:.3f}, own goals={own_g:.3f})   Δ vs fixed={dx:+.3f}" if pax > 0
                      else f"   {sea}: wf=N/A (καμια προηγουμενη σεζον)   (own xG={own_x:.3f}, own goals={own_g:.3f})")
                phx += hx; pax += ax; phg += hg; pag += ag
            print()
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sidedetail':
        Bb = withmd('none', 0); Bs = withmd('caley', 1.5); Bp = withmd('comboprior', 1.5)
        def seg(df, lo_b, hi_b, sd):
            return roi(df[(df.md >= lo_b) & (df.md <= hi_b) & (df.side == sd)])
        print("── PART 1: baseline, home/away ανα σεζον — md9-12, md13-14, ΚΑΙ md9-14 μαζι ──")
        print(f"{'σεζον':>6s} | {'9-12 ΓΗΠ':>10s} {'9-12 ΦΙΛ':>10s} | {'13-14 ΓΗΠ':>10s} {'13-14 ΦΙΛ':>10s} | {'9-14 ΓΗΠ-only':>13s}")
        for s in list(seasons) + ['ΟΛΕΣ']:
            d = Bb if s == 'ΟΛΕΣ' else Bb[Bb.season == s]
            h912 = seg(d, 8, 11, 1); a912 = seg(d, 8, 11, -1)
            h1314 = seg(d, 12, 13, 1); a1314 = seg(d, 12, 13, -1)
            h914 = seg(d, 8, 13, 1)
            print(f"{s:>6s} | {h912[0]:>+7.1%}·{h912[2]:>2d} {a912[0]:>+7.1%}·{a912[2]:>2d} | "
                  f"{h1314[0]:>+7.1%}·{h1314[2]:>2d} {a1314[0]:>+7.1%}·{a1314[2]:>2d} | {h914[0]:>+8.1%}·{h914[2]:>2d}")
        print("\n── PART 2: md9-12 home vs away — βοηθανε οι τεχνικες τη ΓΗΠΕΔΟΥΧΟ πλευρα; ──")
        print(f"{'μεθοδος':>16s} | {'ΓΗΠΕΔΟΥΧΟΣ +hcap':>18s} | {'ΦΙΛΟΞΕΝ. +hcap':>18s}")
        for name, df in [('baseline', Bb), ('SoS 1.5', Bs), ('SoS 1.5 + περσινο', Bp)]:
            h = seg(df, 8, 11, 1); a = seg(df, 8, 11, -1)
            print(f"{name:>16s} | {h[0]:>+10.1%} (n{h[2]:>2d}) | {a[0]:>+10.1%} (n{a[2]:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sideseason':
        # md9-12: home vs away underdog ΑΝΑ ΣΕΖΟΝ (σταθερη η ασυμμετρια;)
        P = build_preds(M, id2name, method='none', lo=6, hi=13)
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        W = B[(B.md >= 8) & (B.md <= 11)]   # md 9-12 = prior games 8-11
        print("md 9-12: HOME vs AWAY underdog ΑΝΑ ΣΕΖΟΝ (baseline)\n")
        print(f"{'σεζον':>7s} | {'ΓΗΠΕΔΟΥΧΟΣ':>16s} | {'ΦΙΛΟΞΕΝ.':>16s} | {'home-only ολο':>14s}")
        for s in seasons:
            Ws = W[W.season == s]
            mh, _, nh = roi(Ws[Ws.side == 1]); ma, _, na = roi(Ws[Ws.side == -1])
            print(f"{s:>7s} | {mh:>+8.1%}(n{nh:>2d}) | {ma:>+8.1%}(n{na:>3d}) | {mh:>+8.1%}(n{nh:>2d})")
        mh, _, nh = roi(W[W.side == 1]); ma, _, na = roi(W[W.side == -1])
        print(f"{'ΟΛΕΣ':>7s} | {mh:>+8.1%}(n{nh:>2d}) | {ma:>+8.1%}(n{na:>3d}) | {mh:>+8.1%}(n{nh:>2d})")
        print("\n(home-only = τι θα κερδιζαμε αν στο md9-12 παιζαμε ΜΟΝΟ γηπεδουχους αουτσαιντερ)")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sidesplit':
        # home-underdog vs away-underdog ROI σε ΟΛΑ τα buckets (baseline) — early vs late
        P = build_preds(M, id2name, method='none', lo=6, hi=40)
        B = BET(P)
        key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
            columns={'home_name': 'home', 'away_name': 'away'})
        B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        BUCK = [(6, 7, 'md 7-8'), (8, 9, 'md 9-10'), (10, 11, 'md 11-12'), (12, 13, 'md 13-14'),
                (14, 20, 'md 15-21'), (21, 40, 'md 22+')]
        print("HOME vs AWAY underdog ανα bucket (baseline, CORE7, 5σ)\n")
        print(f"{'bucket':>10s} | {'ΓΗΠΕΔΟΥΧΟΣ +hcap':>20s} | {'ΦΙΛΟΞΕΝ. +hcap':>20s}")
        for lo_b, hi_b, lab in BUCK:
            sub = B[(B.md >= lo_b) & (B.md <= hi_b)]
            mh, _, nh = roi(sub[sub.side == 1]); ma, _, na = roi(sub[sub.side == -1])
            print(f"{lab:>10s} | {mh:>+9.1%} (n={nh:>3d}) | {ma:>+9.1%} (n={na:>3d})")
        allh = roi(B[B.side == 1]); alla = roi(B[B.side == -1])
        print(f"\n  ΟΛΑ: γηπεδουχος {allh[0]:+.1%}(n{allh[2]})  |  φιλοξεν. {alla[0]:+.1%}(n{alla[2]})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'md1112':
        Bb = withmd('none', 0); Bp = withmd('comboprior', 1.5)
        def m(df):
            return df[(df.md >= 10) & (df.md <= 11)]   # md 11-12 = prior games 10-11
        Mb, Mp = m(Bb), m(Bp)
        print("ΔΙΑΓΝΩΣΤΙΚΟ md 11-12 (CORE7, ΜΕ SerieA, 5σ)\n")
        print("── ανα λιγκα (baseline → SoS+περσινο) ──")
        for lg in leagues:
            mb, _, nb = roi(Mb[Mb.league == lg]); mp, _, np_ = roi(Mp[Mp.league == lg])
            print(f"  {lg:>13s}: base {mb:>+7.1%}(n{nb:>2d}) → {mp:>+7.1%}(n{np_:>2d})")
        print("\n── ανα σεζον ──")
        for s in seasons:
            mb, _, nb = roi(Mb[Mb.season == s]); mp, _, np_ = roi(Mp[Mp.season == s])
            print(f"  {s}: base {mb:>+7.1%}(n{nb:>2d}) → {mp:>+7.1%}(n{np_:>2d})")
        print("\n── πλευρα στοιχηματος (side=1 γηπεδουχος underdog, -1 φιλοξ. underdog) ──")
        for sd, nm in [(1, 'ΓΗΠΕΔΟΥΧΟΣ +hcap'), (-1, 'ΦΙΛΟΞΕΝ. +hcap')]:
            mb, _, nb = roi(Mb[Mb.side == sd]); mp, _, np_ = roi(Mp[Mp.side == sd])
            print(f"  {nm:>18s}: base {mb:>+7.1%}(n{nb:>3d}) → {mp:>+7.1%}(n{np_:>3d})")
        print("\n── odds bucket (baseline) ──")
        for lo_o, hi_o in [(1.70, 1.85), (1.85, 2.00), (2.00, 2.10)]:
            sub = Mb[(Mb.odds >= lo_o) & (Mb.odds < hi_o)]; mm, _, nn = roi(sub)
            print(f"  odds {lo_o}-{hi_o}: {mm:>+7.1%} (n={nn})")
        print(f"\n  ΣΥΝΟΛΟ md11-12: baseline {roi(Mb)[0]:+.1%} (n{roi(Mb)[2]}) → SoS+περσινο {roi(Mp)[0]:+.1%} (n{roi(Mp)[2]})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'losoprior':
        STR = [0.0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0]   # comboprior με K=10 (default shrink_k)
        B = {s: withmd('comboprior', s) for s in STR}
        Bb = withmd('none', 0)
        def sl(df, S, inS, lo_b, hi_b):
            sub = df[df.season == S] if inS else df[df.season != S]
            return sub[(sub.md >= lo_b) & (sub.md <= hi_b)]
        for lo_b, hi_b, wname in [(6, 13, 'ΟΛΟ 7-14'), (6, 7, 'md 7-8')]:
            print(f"\n═══ LOSO — SoS+περσινο shrinkage — {wname} (CORE7, ΜΕ SerieA) ═══")
            print(f"{'κρυμμενη':>9s} | {'best str':>8s} | {'OOS @best':>13s} | {'OOS @σταθ1.5':>13s} | {'baseline':>12s}")
            pb = []; pf = []; pbase = []
            for S in seasons:
                best = max(STR, key=lambda s: roi(sl(B[s], S, False, lo_b, hi_b))[0])
                hb = sl(B[best], S, True, lo_b, hi_b); hf = sl(B[1.5], S, True, lo_b, hi_b); ba = sl(Bb, S, True, lo_b, hi_b)
                pb.append(hb); pf.append(hf); pbase.append(ba)
                mb, _, nb = roi(hb); mf, _, nf = roi(hf); ma, _, na = roi(ba)
                print(f"{S:>9s} | {best:>8.2f} | {mb:>+8.1%}(n{nb:>3d}) | {mf:>+8.1%}(n{nf:>3d}) | {ma:>+7.1%}(n{na:>3d})")
            ab = pd.concat(pb); af = pd.concat(pf); aa = pd.concat(pbase)
            mab, sab, nab = roi(ab); maf, saf, naf = roi(af); maa, saa, naa = roi(aa)
            print(f"  {'POOLED':>9s} | {'':>8s} | {mab:>+8.1%}±{sab:.1%} | {maf:>+8.1%}±{saf:.1%} | {maa:>+7.1%}±{saa:.1%}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'loso':
        STR = [0.0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0]
        B = {s: (withmd('none', 0) if s == 0 else withmd('caley', s)) for s in STR}
        def slice_md(df, S, incl_S, lo_b, hi_b):
            sub = df[df.season == S] if incl_S else df[df.season != S]
            return sub[(sub.md >= lo_b) & (sub.md <= hi_b)]
        for lo_b, hi_b, wname in [(6, 7, 'md 7-8'), (6, 13, 'ολο 7-14')]:
            print(f"\n═══ LEAVE-ONE-SEASON-OUT — {wname}  (CORE7, με SerieA) ═══")
            print(f"{'κρυμμενη':>9s} | {'best str':>8s} | {'held-out @best':>16s} | {'held-out @σταθ.1.5':>18s}")
            pool_best = []; pool_fix = []
            for S in seasons:
                best = max(STR, key=lambda s: roi(slice_md(B[s], S, False, lo_b, hi_b))[0])
                hb = slice_md(B[best], S, True, lo_b, hi_b)
                hf = slice_md(B[1.5], S, True, lo_b, hi_b)
                pool_best.append(hb); pool_fix.append(hf)
                mb, _, nb = roi(hb); mf, _, nf = roi(hf)
                print(f"{S:>9s} | {best:>8.2f} | {mb:>+10.1%}(n{nb:>3d}) | {mf:>+11.1%}(n{nf:>3d})")
            ab = pd.concat(pool_best); af = pd.concat(pool_fix)
            mab, sab, nab = roi(ab); maf, saf, naf = roi(af)
            print(f"  {'POOLED':>9s} | {'':>8s} | {mab:>+10.1%}±{sab:.1%}(n{nab}) | {maf:>+11.1%}±{saf:.1%}(n{naf})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'prior':
        BUCK = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        def build(method, st, K=10.0):
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st, shrink_k=K)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        ARMS = [('baseline', 'none', 0, 0), ('shrink→mean K10', 'shrink', 10, 0),
                ('shrink→prior K10', 'shrinkprior', 10, 0), ('SoS 1.5', 'caley', 1.5, 0),
                ('SoS+shrink→prior', 'comboprior', 1.5, 10)]
        data = {}
        print("SHRINK-TO-PRIOR (5σ, window 7-14, ΜΕ SerieA). σημ: 2122 δεν εχει prior→mean fallback\n")
        print(f"{'arm':>17s} | {'ΟΛΟ 7-14':>13s} | " + " | ".join(f"{lab:>9s}" for _, _, lab in BUCK))
        for name, method, st, K in ARMS:
            B = build(method, st, K); data[name] = B
            m, se, n = roi(B); row = [f"{m:>+6.1%}±{se:.1%}"]
            for lo_b, hi_b, lab in BUCK:
                mm, _, nn = roi(B[(B.md >= lo_b) & (B.md <= hi_b)]); row.append(f"{mm:>+5.1%}·{nn:>2d}")
            print(f"{name:>17s} | {row[0]:>13s} | " + " | ".join(f"{c:>9s}" for c in row[1:]))
        print("\n── ανα λιγκα (baseline → shrink→prior → SoS+shrink→prior) ──")
        for lg in leagues:
            mb, _, nb = roi(data['baseline'][data['baseline'].league == lg])
            mp, _, np_ = roi(data['shrink→prior K10'][data['shrink→prior K10'].league == lg])
            mc, _, nc = roi(data['SoS+shrink→prior'][data['SoS+shrink→prior'].league == lg])
            print(f"  {lg:>13s}: base {mb:>+6.1%}  → shrink→prior {mp:>+6.1%}  → +SoS {mc:>+6.1%}")
        print("\n── SoS+shrink→prior ανα σεζον ──")
        B = data['SoS+shrink→prior']
        for s in seasons:
            m, se, n = roi(B[B.season == s]); print(f"  {s}: {m:>+6.1%} (n={n})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'attrib':
        # ΚΑΘΑΡΟ attribution: καθε μοχλος ΜΕ SerieA (CORE7) + διπλα CORE6, + buckets CORE7
        BUCK = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        def build(method, st, K=10.0):
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st, shrink_k=K)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        ARMS = [('baseline', 'none', 0, 0), ('shrink K10', 'shrink', 10, 0),
                ('SoS 1.5', 'caley', 1.5, 0), ('combo 1.5/K10', 'combo', 1.5, 10)]
        print("ΚΑΘΑΡΟ ATTRIBUTION (5σ, window 7-14).  CORE7 = ΜΕ SerieA· CORE6 = χωρις\n")
        print(f"{'arm':>14s} | {'CORE7':>13s} | {'CORE6':>13s} || CORE7 ανα bucket: " +
              " | ".join(f"{lab:>9s}" for _, _, lab in BUCK))
        for name, method, st, K in ARMS:
            B = build(method, st, K)
            m7, s7, n7 = roi(B); m6, s6, n6 = roi(B[B.league != 'SerieA'])
            buck = []
            for lo_b, hi_b, lab in BUCK:
                mm, _, nn = roi(B[(B.md >= lo_b) & (B.md <= hi_b)]); buck.append(f"{mm:>+5.1%}·{nn:>2d}")
            print(f"{name:>14s} | {m7:>+6.1%}±{s7:.1%}·{n7:>3d} | {m6:>+6.1%}±{s6:.1%}·{n6:>3d} || " +
                  " | ".join(f"{c:>9s}" for c in buck))
        # SerieA μονη της ανα μοχλο (ποσο χανει)
        print("\nSerieA ΜΟΝΗ ανα μοχλο (7-14):")
        for name, method, st, K in ARMS:
            B = build(method, st, K); m, se, n = roi(B[B.league == 'SerieA'])
            print(f"  {name:>14s}: {m:>+6.1%} (n={n})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'combo':
        BUCK = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        def build(method, st, K=10.0):
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st, shrink_k=K)
            B = BET(P)
            if len(B) == 0:
                return B
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            return B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        ARMS = [('baseline', 'none', 0, 0), ('SoS 1.5', 'caley', 1.5, 0),
                ('shrink K10', 'shrink', 10, 0), ('combo 1.5/K10', 'combo', 1.5, 10),
                ('combo 1.5/K6', 'combo', 1.5, 6), ('combo 2.0/K10', 'combo', 2.0, 10)]
        data = {}
        print("═══ COMBINE levers — ROI ολο 7-14 + ανα bucket (CORE 7, 5σ) ═══")
        print(f"{'arm':>14s} | {'ΟΛΟ 7-14':>13s} | " + " | ".join(f"{lab:>11s}" for _, _, lab in BUCK))
        for name, method, st, K in ARMS:
            B = build(method, st, K); data[name] = B
            m, se, n = roi(B); row = [f"{m:>+6.1%}±{se:.1%}"]
            for lo_b, hi_b, lab in BUCK:
                mm, _, nn = roi(B[(B.md >= lo_b) & (B.md <= hi_b)]); row.append(f"{mm:>+6.1%}·{nn:>2d}")
            print(f"{name:>14s} | {row[0]:>13s} | " + " | ".join(f"{c:>11s}" for c in row[1:]))
        print("\n═══ εξαιρεση SerieA (CORE 6) — ολο 7-14 ═══")
        for name in ['baseline', 'SoS 1.5', 'combo 1.5/K10']:
            B = data[name]; m, se, n = roi(B[B.league != 'SerieA'])
            print(f"  {name:>14s} χωρις SerieA: {m:>+6.1%} ±{se:.1%} (n={n})")
        print("\n═══ combo 1.5/K10 ανα σεζον (CORE7 & CORE6) ═══")
        B = data['combo 1.5/K10']
        for s in seasons:
            m7, _, n7 = roi(B[B.season == s]); m6, _, n6 = roi(B[(B.season == s) & (B.league != 'SerieA')])
            print(f"  {s}:  CORE7 {m7:>+6.1%}(n{n7:>3d})   CORE6 {m6:>+6.1%}(n{n6:>3d})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'profile':
        # για καθε bucket, σαρωση ΟΛΟΥ του strength → βρες το βελτιστο ανα αγωνιστικη
        STRENGTHS = [0.0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0]
        BUCKETS = [(6, 7, 'md7-8'), (8, 9, 'md9-10'), (10, 11, 'md11-12'), (12, 13, 'md13-14')]
        data = {}
        for st in STRENGTHS:
            method = 'none' if st == 0 else 'caley'
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            data[st] = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        print("ROI ανα bucket × strength (σαρωση) — CORE 7, 2 σεζον. ★=βελτιστο του bucket\n")
        print(f"{'strength':>9s} | " + " | ".join(f"{lab:>13s}" for _, _, lab in BUCKETS))
        # βρες best strength ανα bucket
        best = {}
        for lo_b, hi_b, lab in BUCKETS:
            vals = [(st, roi(data[st][(data[st].md >= lo_b) & (data[st].md <= hi_b)])[0]) for st in STRENGTHS]
            best[lab] = max(vals, key=lambda x: x[1])[0]
        for st in STRENGTHS:
            cells = []
            for lo_b, hi_b, lab in BUCKETS:
                m, se, n = roi(data[st][(data[st].md >= lo_b) & (data[st].md <= hi_b)])
                star = '★' if best[lab] == st else ' '
                cells.append(f"{star}{m:>+6.1%} n{n:>2d}")
            print(f"{st:>9.2f} | " + " | ".join(f"{c:>13s}" for c in cells))
        print("\nβελτιστο strength ανα bucket:  " + "  ".join(f"{lab}={best[lab]}" for _, _, lab in BUCKETS))
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'decay':
        # φθινον strength(md): ψηλα στη 7η, σβηνει στο 0 γυρω στη T. md15+ = strength 0 (baseline).
        def lin(S0, T):
            return lambda md: max(0.0, S0 * (T - md) / (T - 6)) if md <= T else 0.0
        SCHEDULES = [
            ("baseline",          lambda md: 0.0),
            ("const1.75(7-14)",   lambda md: 1.75 if md <= 13 else 0.0),
            ("step1.75 <=md11",   lambda md: 1.75 if md <= 11 else 0.0),
            ("step1.75 <=md12",   lambda md: 1.75 if md <= 12 else 0.0),
            ("step2.0 <=md11",    lambda md: 2.0 if md <= 11 else 0.0),
            ("lin 1.75→0 @T14",   lin(1.75, 14)),
        ]
        BUCKETS = [(6, 7, 'md 7-8'), (8, 9, 'md 9-10'), (10, 11, 'md 11-12'), (12, 13, 'md 13-14')]
        data = {}
        for tag, fn in SCHEDULES:
            P = build_preds(M, id2name, method='caley', lo=6, hi=40, strength_fn=fn)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            data[tag] = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        # δειγμα προφιλ strength
        print("strength profile (md → strength):")
        for tag, fn in SCHEDULES:
            print(f"  {tag:>18s}: " + " ".join(f"md{md}:{fn(md):.2f}" for md in [6, 8, 10, 12, 13, 14]))
        print()
        print(f"{'schedule':>18s} | " + " | ".join(f"{lab:>13s}" for _, _, lab in BUCKETS) + f" | {'ΟΛΟ 7-14':>13s} | {'2425':>7s} | {'2526':>7s}")
        for tag, _ in SCHEDULES:
            B = data[tag]; w = B[(B.md >= 6) & (B.md <= 13)]
            cells = []
            for lo_b, hi_b, lab in BUCKETS:
                m, se, n = roi(B[(B.md >= lo_b) & (B.md <= hi_b)])
                cells.append(f"{m:>+6.1%} n{n:>2d}")
            mw, _, nw = roi(w)
            m24, _, n24 = roi(w[w.season == '2425']); m25, _, n25 = roi(w[w.season == '2526'])
            print(f"{tag:>18s} | " + " | ".join(f"{c:>13s}" for c in cells) +
                  f" | {mw:>+6.1%} n{nw:>3d} | {m24:>+6.1%} | {m25:>+6.1%}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'leaguegrad':
        # ROI ανα ΛΙΓΚΑ × bucket × strength — για να φανει αν ενα bucket το «γραφει» μια λιγκα
        BUCKETS = [(6, 7, 'md 7-8'), (8, 9, 'md 9-10'), (10, 11, 'md 11-12'), (12, 13, 'md 13-14')]
        METHODS = [("base", 'none', 1.0), ("C1.0", 'caley', 1.0),
                   ("C1.5", 'caley', 1.5), ("C1.75", 'caley', 1.75)]
        data = {}
        for tag, method, st in METHODS:
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            data[tag] = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        for lo_b, hi_b, lab in BUCKETS:
            print(f"\n═══ {lab} ═══")
            print(f"{'λιγκα':>13s} | " + " | ".join(f"{t:>11s}" for t, _, _ in METHODS))
            for lg in leagues + ['ΣΥΝΟΛΟ']:
                cells = []
                for tag, _, _ in METHODS:
                    B = data[tag]; sub = B[(B.md >= lo_b) & (B.md <= hi_b)]
                    if lg != 'ΣΥΝΟΛΟ':
                        sub = sub[sub.league == lg]
                    m, se, n = roi(sub)
                    cells.append(f"{m:>+6.1%} n{n:>2d}" if n else f"{'—':>9s}")
                print(f"{lg:>13s} | " + " | ".join(f"{c:>11s}" for c in cells))
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'fullgrad':
        # ΟΛΗ η καμπυλη σεζον: ROI ανα matchday-bucket, baseline vs Caley1.5, μεχρι md30+
        BUCKETS = [(6, 7, 'md 7-8'), (8, 9, 'md 9-10'), (10, 11, 'md 11-12'),
                   (12, 13, 'md 13-14'), (14, 16, 'md 15-17'), (17, 20, 'md 18-21'),
                   (21, 25, 'md 22-26'), (26, 40, 'md 27+')]
        METHODS = [("baseline", 'none', 1.0), ("Caley1.5", 'caley', 1.5)]
        data = {}
        for tag, method, st in METHODS:
            P = build_preds(M, id2name, method=method, lo=6, hi=40, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            data[tag] = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
        print("ΟΛΗ Η ΚΑΜΠΥΛΗ ΣΕΖΟΝ: ROI ανα matchday-bucket  CORE 7  2 σεζον\n")
        print(f"{'bucket':>10s} | {'baseline':>16s} | {'Caley1.5':>16s}")
        for lo_b, hi_b, lab in BUCKETS:
            cells = []
            for tag, _, _ in METHODS:
                sub = data[tag][(data[tag].md >= lo_b) & (data[tag].md <= hi_b)]
                m, se, n = roi(sub)
                cells.append(f"{m:>+6.1%} (n={n:>3d})")
            print(f"{lab:>10s} | {cells[0]:>16s} | {cells[1]:>16s}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'gradient':
        # ROI ανα matchday-bucket (min prior games), baseline vs SoS strengths
        BUCKETS = [(6, 7, 'md 7-8'), (8, 9, 'md 9-10'), (10, 11, 'md 11-12'), (12, 13, 'md 13-14')]
        METHODS = [("baseline", 'none', 1.0), ("Caley1.0", 'caley', 1.0),
                   ("Caley1.5", 'caley', 1.5), ("Caley1.75", 'caley', 1.75)]
        # build P (με md) + B, merge md πισω στα bets
        data = {}
        for tag, method, st in METHODS:
            P = build_preds(M, id2name, method=method, lo=6, hi=13, strength=st)
            B = BET(P)
            key = P[['league', 'season', 'date', 'home_name', 'away_name', 'md']].rename(
                columns={'home_name': 'home', 'away_name': 'away'})
            B = B.merge(key, on=['league', 'season', 'date', 'home', 'away'], how='left')
            data[tag] = B
        print("ROI ανα matchday-bucket (min prior games)  window 7-14  CORE 7  2 σεζον\n")
        print(f"{'bucket':>10s} | " + " | ".join(f"{t:>14s}" for t, _, _ in METHODS))
        for lo_b, hi_b, lab in BUCKETS:
            cells = []
            for tag, _, _ in METHODS:
                B = data[tag]; sub = B[(B.md >= lo_b) & (B.md <= hi_b)]
                m, se, n = roi(sub)
                cells.append(f"{m:>+6.1%} (n={n:>3d})")
            print(f"{lab:>10s} | " + " | ".join(f"{c:>14s}" for c in cells))
        # συνολα ελεγχου
        print(f"{'ΟΛΟ 7-14':>10s} | " + " | ".join(
            f"{roi(data[t])[0]:>+6.1%} (n={roi(data[t])[2]:>3d})" for t, _, _ in METHODS))
        return

    if len(sys.argv) > 1 and sys.argv[1] == 'sanity':
        print("SANITY: baseline, no window (lo=14,hi=9999) — πρεπει να μοιαζει με picks backtest @15+\n")
        B, meta = run_arm(M, id2name, BET, method='none', lo=14, hi=9999)
        m, se, n = roi(B)
        print(f"  preds={meta['preds']}  bets={meta['bets']}  ROI={m:+.1%} ±{se:.1%} (n={n})")
        for sea in seasons:
            ms, ss, ns = roi(B[B.season == sea])
            print(f"    {sea}: {ms:+.1%} ±{ss:.1%} (n={ns})")
        return

    LO, HI = 6, 13   # window 7η-14η (7ο..14ο ματς καθε ομαδας = len prior 6..13)
    print(f"WINDOW 7-14  (lo={LO}, hi={HI})   λιγκες: CORE 7   σεζον: {seasons}\n")

    # ολες οι μεθοδοι SoS head-to-head
    ARMS = [
        ("baseline",        'none',   1.0),
        ("Caley 1.0",       'caley',  1.0),
        ("Caley 1.25",      'caley',  1.25),
        ("Caley 1.5",       'caley',  1.5),
        ("Caley 1.75",      'caley',  1.75),
        ("Caley 2.0",       'caley',  2.0),
        ("Massey (exact)",  'massey', 1.0),
    ]
    results = {}
    for tag, method, st in ARMS:
        B, meta = run_arm(M, id2name, BET, method=method, lo=LO, hi=HI, strength=st)
        results[tag] = B
        m, se, n = roi(B)
        print(f"{tag:>16s} | {m:>+7.1%} ±{se:>5.1%} | n={n:>4d}  (preds={meta['preds']})")

    print("\n── ανα λιγκα (baseline → best-per-method) ──")
    print(f"{'λιγκα':>13s} | " + " | ".join(f"{t:>10s}" for t, _, _ in ARMS))
    for lg in leagues:
        cells = []
        for tag, _, _ in ARMS:
            m, se, n = roi(results[tag][results[tag].league == lg])
            cells.append(f"{m:>+6.1%}(n{n:>2d})".replace('n ', 'n'))
        print(f"{lg:>13s} | " + " | ".join(f"{c:>10s}" for c in cells))

    print("\n── ανα σεζον ──")
    for sea in seasons:
        cells = []
        for tag, _, _ in ARMS:
            m, se, n = roi(results[tag][results[tag].season == sea])
            cells.append(f"{tag}:{m:+.1%}")
        print(f"  {sea} | " + "  ".join(cells))

if __name__ == '__main__':
    main()
