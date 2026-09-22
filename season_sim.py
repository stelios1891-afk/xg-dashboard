"""
season_sim.py — ΓΕΝΙΚΗ ΜΗΧΑΝΗ Monte Carlo τελους σεζον (εντολη Στελιου 22/9/2026).

Δεδομενων: (α) παιγμενα ματς ως ενα cutoff, (β) υπολοιπα fixtures, (γ) ratings της μηχανης ΣΤΟ cutoff
-> λ_home/λ_away ανα ματς (ιδιο math με dashboard/build_data._predict_ratings, HFA_FIX)
-> σκορ απο Poisson x DRAW_BOOST 1.13 (ιδια κατανομη με picks.gd_dist / build_data.one_x_two)
-> N runs vectorized numpy -> καταταξη με κριτηρια ισοβαθμιας ανα λιγκα -> πιθανοτητες.

ΔΕΙΓΜΑΤΟΛΗΨΙΑ ΣΚΟΡ (ακριβης, οχι προσεγγιση): rejection sampling. Η κατανομη με draw boost ειναι
p'(i,j) ∝ Poi(i;λh)·Poi(j;λa)·(1.13 αν i==j αλλιως 1). Τραβαμε (i,j) απο σκετο Poisson και
δεχομαστε τα ΜΗ-ισοπαλα με πιθανοτητα 1/1.13, τις ισοπαλιες παντα· ξανατραβαμε τα απορριφθεντα.
Αυτο δινει ΑΚΡΙΒΩΣ την p'. (Μονη διαφορα απο το 13x13 του gd_dist: δεν κοβει στα 12 γκολ —
μαζα >12 γκολ ~1e-9, αμελητεα.) Το one_x_two του dashboard επαληθευεται στο __main__ (MC vs αναλυτικο).

ΑΒΕΒΑΙΟΤΗΤΑ ratings (M1): ανα run, ανα ομαδα, πολλαπλασιαστικος lognormal θορυβος σε επιθεση και
αμυνα, ανεξαρτητα: f = exp(N(-sd²/2, sd²)) (E[f]=1), sd = s0/sqrt(1+n/8), n = φετινα ματς της ομαδας.
λh(run) = λh·att[home]·def[away], λa(run) = λa·att[away]·def[home].

REGRESSION προς μεσο (M2): πριν την προβλεψη, καθε rating (Ax,Dx,SF,SA) -> μεσος·(r/μεσος)^w
(γεωμετρικα, οπως το _shrink του live), w = 1 - ρ·(υπολοιπα ματς ΤΗΣ ΟΜΑΔΑΣ / ματς σεζον).

ΚΡΙΤΗΡΙΑ ΙΣΟΒΑΘΜΙΑΣ (προ-δηλωμενα):
  EPL, Bundesliga, Ligue1, Eredivisie: βαθμοι -> GD -> GF (EPL: h2h μετα το GF αγνοειται — πρακτικα ποτε)
  LaLiga, SerieA, PrimeiraLiga: βαθμοι -> h2h (βαθμοι μεταξυ τους, μετα GD μεταξυ τους) -> GD -> GF
  h2h ΜΟΝΟ για ισοβαθμιες 2 ομαδων (ακριβως 2 ομαδες με τους ιδιους βαθμους)· για >=3 ομαδες GD -> GF.
  Υπολοιπες ισοβαθμιες: τυχαια (ομοιομορφα) — δηλωμενο.
  Το h2h μετραει τα παιγμενα + τα προσομοιωμενα σκορ των δυο ματς του ζευγους.

ΘΕΣΕΙΣ ανα λιγκα (προ-δηλωμενες): βλ. LEAGUE_RULES.
DEDUCTIONS: χειροκινητο πεδιο {(league, season, team_name): points} — βλ. season_sim_validate.py.

Offline αναπαραγωγη ratings ΣΤΟ cutoff (ratings_at_cutoff): ΙΔΙΑ λογικη με build_data.league_ratings
(flat περσινο prior -> _rating(n=None), warm-start _shrink K=8 με ραμπα blend_at(n), χαρακας λιγκας
ραμπα KN_NORM=20 με τα φετινα ΜΕΧΡΙ το cutoff, SoS 1.5 για n=6..13, νεοφωτιστες = μεσος λιγκας x
PROMO_COEF χωρις ξεχωρισμα 2ης κατηγοριας [λ ανενεργο — δηλωμενο]). ΣΤΑΤΙΚΑ ratings: ολα τα
υπολοιπα fixtures προβλεπονται με τα ratings του cutoff, ΚΑΝΕΝΑ look-ahead.
"""
import os, sys, json
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
import picks
import build_data as BD

DRAW_BOOST = picks.DRAW_BOOST      # 1.13
HFA_FIX = picks.HFA_FIX
CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga']
SEASONS5 = ['2122', '2223', '2324', '2425', '2526']

# --------- κανονες λιγκας: (tiebreak, title, ucl, ucl5?, eur, rel_direct, rel_playoff?) ----------
# eur = UCL+UEL+UECL θεσεις συνολικα (δηλωμενο στην εντολη): EPL 7, LaLiga 7, SerieA 7, Bundesliga 6,
# Ligue1 5, Primeira 4, Eredivisie 4. Eredivisie: ΧΩΡΙΣ ευρωπαικα playoffs (2 απευθειας UCL) — δηλωμενο.
LEAGUE_RULES = {
    'EPL':          dict(tb='gd',  ucl=4, ucl5=True,  eur=7, rel=3, rel_po=False),
    'LaLiga':       dict(tb='h2h', ucl=4, ucl5=True,  eur=7, rel=3, rel_po=False),
    'SerieA':       dict(tb='h2h', ucl=4, ucl5=True,  eur=7, rel=3, rel_po=False),
    'Bundesliga':   dict(tb='gd',  ucl=4, ucl5=True,  eur=6, rel=2, rel_po=True),
    'Ligue1':       dict(tb='gd',  ucl=3, ucl5=False, eur=5, rel=2, rel_po=True),
    'PrimeiraLiga': dict(tb='h2h', ucl=2, ucl5=False, eur=4, rel=2, rel_po=True),
    'Eredivisie':   dict(tb='gd',  ucl=2, ucl5=False, eur=4, rel=2, rel_po=True),
}
# Ligue1 με 20 ομαδες (2122, 2223): 2122 = 3 απευθειας (+18η playoff), 2223 = 4 απευθειας (20->18).
REL_OVERRIDE = {('Ligue1', '2122'): 3, ('Ligue1', '2223'): 4}

# --------- διπλες εγγραφες (ιδιο ζευγος home-away 2 φορες στη σεζον) ----------
# Προεπιλογη: κραταμε την ΠΡΩΤΗ (η δευτερη = playoff: Eredivisie ευρωπαικα playoffs, SerieA 2223 Spezia-Verona).
# ΔΙΑΚΟΠΕΝΤΑ ματς (κραταμε τη ΔΕΥΤΕΡΗ = επαναληψη/τελικη εγγραφη): χειροκινητη λιστα.
ABANDONED_KEEP_LATER = {
    ('EPL', '2324', 'AFC Bournemouth', 'Luton Town'),
    ('Ligue1', '2122', 'Lyon', 'Marseille'),
    ('Ligue1', '2122', 'Nice', 'Marseille'),
    ('Ligue1', '2324', 'Montpellier', 'Clermont Foot'),
}


# ======================= δεδομενα =======================
def load_5s(leagues=CORE7, seasons=SEASONS5):
    """Ματς CORE7 5 σεζον απο teamgame_inputs_5s_wf.csv (μεσω sos_test.load_matches_5s) — ΚΑΘΑΡΙΣΜΕΝΑ
    απο playoffs/διακοπεντα. -> (M DataFrame, id2name)."""
    import sos_test
    M, id2name = sos_test.load_matches_5s(leagues, seasons)
    M = M.sort_values(['league', 'season', 'date', 'mid']).reset_index(drop=True)
    keep = np.ones(len(M), bool)
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        dup = G[G.duplicated(['home', 'away'], keep=False)]
        for (h, a), g in dup.groupby(['home', 'away']):
            g = g.sort_values(['date', 'mid'])
            key = (lg, sea, id2name.get(h), id2name.get(a))
            drop_idx = g.index[:-1] if key in ABANDONED_KEEP_LATER else g.index[1:]
            keep[drop_idx] = False
    M = M[keep].reset_index(drop=True)
    return M, id2name


def n_teams(G):
    return len(set(G.home) | set(G.away))


def cutoff_index(G, k):
    """Πληθος ματς που «εχουν παιχτει» μετα την αγωνιστικη k: τα πρωτα k*T/2 ματς κατα ημερομηνια."""
    T = n_teams(G)
    return min(int(round(k * T / 2)), len(G))


# ======================= ratings ΣΤΟ cutoff (offline αντιγραφο του live) =======================
def _hist_from(G):
    """rolling hist ανα ομαδα (ιδιο schema με picks.league_state) απο λιστα ματς."""
    hist = {}
    for r in G.itertuples(index=False):
        for tid, opp, sf, xf, sa, xa, gf, ga in [
                (r.home, r.away, r.h_ns, r.h_xg, r.a_ns, r.a_xg, r.hg, r.ag),
                (r.away, r.home, r.a_ns, r.a_xg, r.h_ns, r.h_xg, r.ag, r.hg)]:
            h = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
            h['sf'].append(sf); h['xf'].append(xf); h['sa'].append(sa); h['xa'].append(xa)
            h['gf'].append(gf); h['ga'].append(ga); h['opp'].append(opp)
    return hist


def league_means(G):
    lg_shots = float(pd.concat([G.h_ns, G.a_ns]).mean())
    lg_xgps = float(pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum())
    return lg_shots, lg_xgps


def ratings_at_cutoff(lg, Gprev, Gcur_played, cur_teams, prior_only=False, sos=True):
    """Ratings ολων των ομαδων της φετινης σεζον ΣΤΟ cutoff — ιδια λογικη με build_data.league_ratings.
    Gprev: ολα τα ματς της περσινης σεζον (prior)· Gcur_played: φετινα ματς ΜΕΧΡΙ το cutoff.
    prior_only=True (B3): αγνοει τα φετινα (n=0 για ολες, χαρακας περσινος).
    -> dict(blended={tid:(Ax,Dx,SF,SA)}, ns={tid:n}, lg_shots, lg_xgps, hf, promoted=set)"""
    hf = HFA_FIX[lg]
    histp = _hist_from(Gprev)
    lg_shots, lg_xgps = league_means(Gprev)
    newcomers = sorted(t for t in cur_teams if t not in histp)
    promoted = set()
    coef = BD.PROMO_COEF.get(lg, BD.PROMO_POOLED)
    lgX = lg_shots * lg_xgps
    for t in newcomers:   # μεσος λιγκας x per-league συντελεστη, ΧΩΡΙΣ ξεχωρισμα 2ης κατηγοριας (λ ανενεργο)
        K = 8
        xf = lgX * coef['xf']; xa = lgX * coef['xa']; sf = lg_shots * coef['sf']; sa = lg_shots * coef['sa']
        histp[t] = dict(sf=[sf]*K, xf=[xf]*K, sa=[sa]*K, xa=[xa]*K, gf=[xf]*K, ga=[xa]*K)
        promoted.add(t)
    histp = BD.flatten_warmstart(histp, lg)
    prior_r = {t: BD._rating(h) for t, h in histp.items() if h.get('sf')}
    if prior_only or len(Gcur_played) == 0:
        blended = {t: prior_r[t] for t in cur_teams if t in prior_r}
        return dict(blended=blended, ns={t: 0 for t in cur_teams}, lg_shots=lg_shots, lg_xgps=lg_xgps,
                    hf=hf, promoted=promoted)
    histc = _hist_from(Gcur_played)
    cur_shots, cur_xgps = league_means(Gcur_played)
    nc = sum(len(h['sf']) for h in histc.values())
    w = nc / (nc + BD.KN_NORM)
    lg_shots = lg_shots * (cur_shots / lg_shots) ** w
    lg_xgps = lg_xgps * (cur_xgps / lg_xgps) ** w
    blended, ns = BD.blend_league(prior_r, histc)
    if sos and picks.SOS:
        blended = {t: picks.sos_adjust(r, histc.get(t, {}).get('opp', []), blended, lg_shots, lg_xgps)
                   for t, r in blended.items()}
    blended = {t: blended[t] for t in cur_teams if t in blended}
    for t in cur_teams:
        ns.setdefault(t, 0)
    return dict(blended=blended, ns=ns, lg_shots=lg_shots, lg_xgps=lg_xgps, hf=hf, promoted=promoted)


def regress_ratings(blended, games_left, season_games, rho, lg_shots, lg_xgps):
    """M2: r -> μεσος·(r/μεσος)^w, w = 1 - ρ·(υπολοιπα της ομαδας / ματς σεζον)."""
    if not rho:
        return blended
    out = {}
    means = (lg_xgps, lg_xgps, lg_shots, lg_shots)
    for t, r in blended.items():
        w = 1.0 - rho * games_left.get(t, 0) / season_games
        out[t] = tuple(m * (max(ri, 1e-9) / m) ** w for ri, m in zip(r, means))
    return out


def fixture_lambdas(fixtures, blended, lg_shots, lg_xgps, hf):
    """fixtures: list of (home_id, away_id) -> (lam_h, lam_a) arrays (HFA-adjusted xG)."""
    lh = np.zeros(len(fixtures)); la = np.zeros(len(fixtures))
    for i, (h, a) in enumerate(fixtures):
        p = BD._predict_ratings(blended[h], blended[a], lg_shots, lg_xgps, hf)
        lh[i] = p['home_adj_xg']; la[i] = p['away_adj_xg']
    return np.clip(lh, 0.05, 6.0), np.clip(la, 0.05, 6.0)


# ======================= δειγματοληψια σκορ =======================
def sample_scores(lam_h, lam_a, rng, draw_boost=DRAW_BOOST):
    """lam_h, lam_a: arrays ιδιου σχηματος -> (gh, ga) ακεραιοι, κατανομη Poisson x draw_boost (rejection)."""
    gh = rng.poisson(lam_h); ga = rng.poisson(lam_a)
    if draw_boost and draw_boost != 1.0:
        p_acc = 1.0 / draw_boost
        redo = (gh != ga) & (rng.random(gh.shape) > p_acc)
        while redo.any():
            idx = np.nonzero(redo)
            nh = rng.poisson(lam_h[idx] if lam_h.ndim == redo.ndim else np.broadcast_to(lam_h, redo.shape)[idx])
            na = rng.poisson(lam_a[idx] if lam_a.ndim == redo.ndim else np.broadcast_to(lam_a, redo.shape)[idx])
            gh[idx] = nh; ga[idx] = na
            redo = np.zeros_like(redo)
            redo[idx] = (nh != na) & (rng.random(nh.shape) > p_acc)
    return gh, ga


def score_matrix(lh, la, draw_boost=DRAW_BOOST):
    """13x13 πινακας σκορ (ιδιος με picks.gd_dist) — για αναφορα/ελεγχο."""
    from math import exp, factorial
    F = [factorial(i) for i in range(13)]
    ph = np.array([exp(-lh) * lh ** i / F[i] for i in range(13)])
    pa = np.array([exp(-la) * la ** j / F[j] for j in range(13)])
    P = np.outer(ph, pa)
    P[np.arange(13), np.arange(13)] *= draw_boost
    return P / P.sum()


# ======================= καταταξη =======================
def rank_table(pts, gd, gf, h2h_pts, h2h_gd, tb, rng):
    """pts/gd/gf: (N,T)· h2h_pts/h2h_gd: (N,T,T) ή None· -> pos (N,T) 0-based (0 = πρωτος)."""
    N, T = pts.shape
    key = pts.astype(np.float64) * 1e7 + (gd + 500.0) * 1e3 + gf + rng.random((N, T)) * 0.5
    if tb == 'h2h' and h2h_pts is not None:
        ptsf = pts.astype(np.float64)
        for a in range(T):
            cnt_a = (pts == pts[:, a][:, None]).sum(1)
            for b in range(a + 1, T):
                m = (pts[:, a] == pts[:, b]) & (cnt_a == 2)
                if not m.any():
                    continue
                d = h2h_pts[m, a, b] - h2h_pts[m, b, a]
                dg = h2h_gd[m, a, b]
                s = np.sign(d); s = np.where(s == 0, np.sign(dg), s)
                idx = np.nonzero(m)[0]
                win_a = idx[s > 0]; win_b = idx[s < 0]
                key[win_a, a] = ptsf[win_a, a] * 1e7 + 9.99e6; key[win_a, b] = ptsf[win_a, b] * 1e7 + 1.0
                key[win_b, b] = ptsf[win_b, b] * 1e7 + 9.99e6; key[win_b, a] = ptsf[win_b, a] * 1e7 + 1.0
    order = np.argsort(-key, axis=1, kind='stable')
    pos = np.empty_like(order)
    rows = np.arange(N)[:, None]
    pos[rows, order] = np.arange(T)[None, :]
    return pos


# ======================= Η ΠΡΟΣΟΜΟΙΩΣΗ =======================
def simulate(teams, played, fixtures, lam_h, lam_a, tb, n_runs=10000, seed=0,
             draw_boost=DRAW_BOOST, noise_sd=None, deductions=None):
    """teams: list team_id (σειρα = δεικτης)· played: list (h,a,gh,ga) παιγμενα· fixtures: list (h,a)·
    lam_h/lam_a: arrays len(fixtures)· tb: 'gd'|'h2h'· noise_sd: {tid: sd} (M1) ή None·
    deductions: {tid: pts} (αφαιρουνται)·
    -> dict(pos (N,T), pts (N,T), gd, gf, W, D, L, pts_now, gd_now, ...)"""
    rng = np.random.default_rng(seed)
    T = len(teams); idx = {t: i for i, t in enumerate(teams)}
    N = n_runs; R = len(fixtures)
    # παιγμενα
    pts0 = np.zeros(T); gd0 = np.zeros(T); gf0 = np.zeros(T); w0 = np.zeros(T); d0 = np.zeros(T); l0 = np.zeros(T)
    H2P0 = np.zeros((T, T)); H2G0 = np.zeros((T, T))
    for h, a, gh, ga in played:
        i, j = idx[h], idx[a]
        gf0[i] += gh; gf0[j] += ga; gd0[i] += gh - ga; gd0[j] += ga - gh
        H2G0[i, j] += gh - ga; H2G0[j, i] += ga - gh
        if gh > ga: pts0[i] += 3; w0[i] += 1; l0[j] += 1; H2P0[i, j] += 3
        elif gh < ga: pts0[j] += 3; w0[j] += 1; l0[i] += 1; H2P0[j, i] += 3
        else: pts0[i] += 1; pts0[j] += 1; d0[i] += 1; d0[j] += 1; H2P0[i, j] += 1; H2P0[j, i] += 1
    if deductions:
        for t, p in deductions.items():
            if t in idx:
                pts0[idx[t]] -= p
    hi = np.array([idx[h] for h, a in fixtures], int); ai = np.array([idx[a] for h, a in fixtures], int)
    # λ ανα run
    LH = np.broadcast_to(lam_h, (N, R)).copy(); LA = np.broadcast_to(lam_a, (N, R)).copy()
    if noise_sd:
        sd = np.array([noise_sd.get(t, 0.0) for t in teams])
        att = np.exp(rng.normal(-sd ** 2 / 2, sd, (N, T))); dfc = np.exp(rng.normal(-sd ** 2 / 2, sd, (N, T)))
        if R:
            LH *= att[:, hi] * dfc[:, ai]; LA *= att[:, ai] * dfc[:, hi]
    if R:
        gh, ga = sample_scores(LH, LA, rng, draw_boost)
    else:
        gh = np.zeros((N, 0), int); ga = np.zeros((N, 0), int)
    wh = (gh > ga).astype(np.float64); dr = (gh == ga).astype(np.float64); wa = (gh < ga).astype(np.float64)
    Hm = np.zeros((R, T)); Am = np.zeros((R, T))
    if R:
        Hm[np.arange(R), hi] = 1; Am[np.arange(R), ai] = 1
    ghf = gh.astype(np.float64); gaf = ga.astype(np.float64)
    W = w0 + wh @ Hm + wa @ Am; D = d0 + dr @ (Hm + Am); L = l0 + wa @ Hm + wh @ Am
    pts = pts0 + 3 * (W - w0) + (D - d0)
    GF = gf0 + ghf @ Hm + gaf @ Am
    GA = (gf0 - gd0) + gaf @ Hm + ghf @ Am
    GD = GF - GA
    h2p = h2g = None
    if tb == 'h2h':
        h2p = np.broadcast_to(H2P0, (N, T, T)).copy(); h2g = np.broadcast_to(H2G0, (N, T, T)).copy()
        for r in range(R):
            i, j = hi[r], ai[r]
            h2p[:, i, j] += 3 * wh[:, r] + dr[:, r]; h2p[:, j, i] += 3 * wa[:, r] + dr[:, r]
            h2g[:, i, j] += ghf[:, r] - gaf[:, r]; h2g[:, j, i] += gaf[:, r] - ghf[:, r]
    pos = rank_table(pts.astype(np.int64), GD.astype(np.int64), GF.astype(np.int64), h2p, h2g, tb, rng)
    return dict(teams=teams, pos=pos, pts=pts, gd=GD, gf=GF, W=W, D=D, L=L,
                pts_now=pts0, gd_now=gd0, gf_now=gf0, w_now=w0, d_now=d0, l_now=l0,
                played_n=w0 + d0 + l0, n_runs=N)


def summarize(sim, lg, season=None):
    """Πιθανοτητες ανα ομαδα απο το αποτελεσμα της simulate."""
    rules = LEAGUE_RULES[lg]; T = len(sim['teams']); pos = sim['pos']; N = sim['n_runs']
    rel = REL_OVERRIDE.get((lg, season), rules['rel'])
    out = {}
    for i, t in enumerate(sim['teams']):
        p = pos[:, i]
        dist = np.bincount(p, minlength=T) / N
        pts = sim['pts'][:, i]
        out[t] = dict(
            p_title=float(dist[0]), p_ucl=float(dist[:rules['ucl']].sum()),
            p_ucl5=float(dist[rules['ucl']]) if rules['ucl5'] else None,
            p_eur=float(dist[:rules['eur']].sum()), p_top6=float(dist[:6].sum()),
            p_rel=float(dist[T - rel:].sum()),
            p_rel_po=float(dist[T - rel - 1]) if rules['rel_po'] else None,
            e_pts=float(pts.mean()), pts_p10=float(np.percentile(pts, 10)), pts_p50=float(np.percentile(pts, 50)),
            pts_p90=float(np.percentile(pts, 90)),
            e_w=float(sim['W'][:, i].mean()), e_d=float(sim['D'][:, i].mean()), e_l=float(sim['L'][:, i].mean()),
            e_gd=float(sim['gd'][:, i].mean()), pos_dist=dist.tolist(),
            pts_now=float(sim['pts_now'][i]), played=int(sim['played_n'][i]),
            w_now=int(sim['w_now'][i]), d_now=int(sim['d_now'][i]), l_now=int(sim['l_now'][i]),
            gd_now=int(sim['gd_now'][i]))
    return out


def final_table(teams, played, tb, deductions=None):
    """Πραγματικη τελικη καταταξη (ιδια κριτηρια) -> {tid: (pos0, pts)}."""
    s = simulate(teams, played, [], np.zeros(0), np.zeros(0), tb, n_runs=1, seed=1, deductions=deductions)
    return {t: (int(s['pos'][0, i]), float(s['pts'][0, i])) for i, t in enumerate(teams)}


if __name__ == '__main__':
    # sanity: MC 1X2 vs αναλυτικο one_x_two
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    rng = np.random.default_rng(0)
    for lh, la in [(1.6, 1.1), (2.4, 0.7), (1.2, 1.3)]:
        n = 400000
        gh, ga = sample_scores(np.full(n, lh), np.full(n, la), rng)
        mc = ((gh > ga).mean() * 100, (gh == ga).mean() * 100, (gh < ga).mean() * 100)
        an = BD.one_x_two(lh, la)
        print(f"λ {lh}-{la}: MC {mc[0]:.1f}/{mc[1]:.1f}/{mc[2]:.1f}  αναλυτικο {an['hw']}/{an['d']}/{an['aw']}")
    M, id2name = load_5s()
    print(M.groupby(['league', 'season']).size().to_string())
    for lg, sea in [('EPL', '2324'), ('SerieA', '2223'), ('Ligue1', '2324')]:
        G = M[(M.league == lg) & (M.season == sea)]
        teams = sorted(set(G.home) | set(G.away))
        ded = {}
        if (lg, sea) == ('EPL', '2324'):
            ded = {t: {'Everton': 8, 'Nottingham Forest': 4}[id2name[t]] for t in teams if id2name[t] in ('Everton', 'Nottingham Forest')}
        if (lg, sea) == ('SerieA', '2223'):
            ded = {t: 10 for t in teams if id2name[t] == 'Juventus'}
        ft = final_table(teams, list(zip(G.home, G.away, G.hg, G.ag)), LEAGUE_RULES[lg]['tb'], ded)
        print(f"\n{lg} {sea} τελικη:")
        for t, (p, pts) in sorted(ft.items(), key=lambda kv: kv[1][0]):
            print(f"  {p+1:2d}. {id2name[t]:28s} {pts:.0f}")
