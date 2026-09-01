"""
build_data.py — παραγει LIVE τα δεδομενα προβλεψεων για το dashboard.

Πηγες:
  - Fixtures (επερχομενα ματς 26/27): FotMob (δωρεαν, χωρις quota).
  - Ratings: το locked μοντελο (picks.py) πανω στην τελευταια ΠΛΗΡΗ σεζον (2526) ως
    warm-start, μεχρι να μαζευτουν φετινα ματς (τοτε αλλαζει σε '2627').
  Επειδη fixtures ΚΑΙ ratings ειναι FotMob, τα ονοματα/ids ταιριαζουν αμεσα.

Επιστρεφει λιστα match dicts με schema συμβατο με το dashboard:
  home, away, gw, utc, league,
  home_exp_shots, home_xg_shot, home_xg (neutral), home_adj_xg (HFA),
  away_exp_shots, away_xg_shot, away_xg, away_adj_xg,
  + hw/d/aw (%) & hw_odds/d_odds/aw_odds (fair, απο το μοντελο).
"""
import os, sys, json, gzip, urllib.request
from math import exp, factorial

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import picks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATINGS_SEASON_DEFAULT = '2526'   # περσινη πληρης σεζον (prior για warm-start)
CURRENT_SEASON = '2627'           # φετινη in-season (blend-άρεται πανω στο prior)
CURRENT_FOTMOB_SEASON = '2026%2F2027'
K_WARM = 8.0                      # warm-start blend: βαρος_φετινου = n/(n+K). K=8 (2026-08-26, k_final.py): με ΔΙΟΡΘΩΜΕΝΕΣ νεοφωτιστες το βελτιστο μετακινηθηκε 6→8 (RPS ολικο ελαχιστο· LOSO διαλεξε >=8 σε 4/4 folds). Πλατο K=4-12 — η διαφορα 6 vs 8 ειναι 1/15 του τυπικου σφαλματος, δηλ. αδιαφορη.
KN_NORM = 20.0                     # "χαρακας" λιγκας (lg_shots/lg_xgps): ραμπα περσινος->φετινος, βαρος_φετινου = nc/(nc+20)
                                  # (2026-09-01, norm_switch_test): πριν ητανε ΠΑΝΤΑ περσινος -> σφαλμα 5.4% ΟΛΗ τη σεζον.
                                  # Με τα φετινα ματς: 1.6% απο την 7η αγων. (3.4x ακριβεστερος). Πλατο Kn=10-40 αδιαφορο.
                                  # Ραμπα, οχι σκαλι: στις 1-3 αγων. τα φετινα ειναι πολυ λιγα (σκετος φετινος = 7.9% σφαλμα).
MARKET_1X2_F = os.path.join(ROOT, 'market_1x2_latest.json')   # market 1X2 απο τον scanner (scan_value.py)

def _market_1x2():
    """Market 1X2 odds -> {"{home_id}_{away_id}": {h,d,a,when}}. {} αν λειπει (graceful)."""
    try:
        with open(MARKET_1X2_F, encoding='utf-8') as fh:
            return json.load(fh).get('odds', {})
    except Exception:
        return {}
LEAGUE_FOTMOB = {'EPL': 47, 'LaLiga': 87, 'SerieA': 55, 'Bundesliga': 54, 'Ligue1': 53,
                 'Eredivisie': 57, 'PrimeiraLiga': 61}   # CORE 7 (Belgium & ScottishPrem αφαιρεθηκαν 2026-08, εκτος portfolio)

# --- Νεοφωτιστες (αναθεωρηθηκε 2026-08-26, βλ. memory early-window-mechanics) ---
# ΕΠΙΠΕΔΟ: μεσος λιγκας × per-league συντελεστη. Μετρημενο σε 78 νεοφωτιστες / 4 μεταβασεις
#          (top-flight δεδομενα μονο), shrunk 0.7 προς το pooled (split-half reliability 0.76).
# ΞΕΧΩΡΙΣΜΑ: × (θεση της στη 2η κατηγορια / μεσος των νεοφωτιστων)^λ  με λ=0.5.
#          λ βρεθηκε με LOSO MAE (0.237@λ=0 → 0.223@λ=0.5)· λ=1 (η παλια συμπεριφορα) ειναι
#          ΧΕΙΡΟΤΕΡΟ κι απο λ=0 (0.245) — υπερ-διαφοροποιει, corr(Champ,EPL xGD)=0.44 μονο.
SECOND_DIV = {'EPL': 'Championship', 'LaLiga': 'LaLiga2', 'SerieA': 'SerieB',
              'Bundesliga': 'Bundesliga2', 'Ligue1': 'Ligue2'}
PROMO_SEASON = '2526'
PROMO_LAMBDA = 0.5
PROMO_COEF = {   # σχετικα με τον μεσο ορο της λιγκας (xGF, xGA, σουτ-υπερ, σουτ-κατα)
    'EPL':          dict(xf=0.772, xa=1.239, sf=0.812, sa=1.192),
    'Eredivisie':   dict(xf=0.800, xa=1.192, sf=0.829, sa=1.147),
    'Ligue1':       dict(xf=0.817, xa=1.152, sf=0.859, sa=1.098),
    'Bundesliga':   dict(xf=0.835, xa=1.176, sf=0.885, sa=1.110),
    'LaLiga':       dict(xf=0.839, xa=1.185, sf=0.873, sa=1.143),
    'SerieA':       dict(xf=0.852, xa=1.160, sf=0.880, sa=1.108),
    'PrimeiraLiga': dict(xf=0.853, xa=1.129, sf=0.902, sa=1.128),
}
PROMO_POOLED = dict(xf=0.828, xa=1.159, sf=0.861, sa=1.134)   # fallback (78 ομαδες)

# ΑΠΟΦΑΣΗ (Stelios): FLAT για ΟΛΕΣ, με τα playoffs ΜΕΣΑ. Το Belgium regular-only εβγαζε −11% αλλα
# n=68 (μια σεζον) → δεν ρισκαρουμε overfit· το flat-all ειναι ηδη −4.9% vs decay, ασφαλες κερδος.
# (REGULAR_CUTOFF παραμενει σαν μηχανισμος αν θελησουμε να το ξαναδουμε με περισσοτερα δεδομενα.)
REGULAR_CUTOFF = {}

def flatten_warmstart(hist, league):
    """Cross-season prior: FLAT (χωρις decay) aggregation του περσινου — καλυτερο για ΠΡΩΤΕΣ 6
    (test 2026-08-09: flat < decay 0.96 MAE, μονοτονο· σε ολες τις λιγκες, playoffs μεσα).
    Αντικαθιστα καθε team-history με constant lists (μεσος) ωστε wmean=flat για οποιοδηποτε decay."""
    cut = REGULAR_CUTOFF.get(league)   # None → ολη η σεζον (h[k][:None] = full)
    K = 8
    out = {}
    for tid, h in hist.items():
        if not h.get('sf'):
            out[tid] = h; continue
        out[tid] = {k: [sum(h[k][:cut]) / len(h[k][:cut])] * K for k in ('sf', 'xf', 'sa', 'xa', 'gf', 'ga')}
    return out

def _second_div_stats(second_div):
    """({tid: {name,xf,xa,sf,sa} ανα ματς}, {μεσοι της κατηγοριας}) — raw, ΧΩΡΙΣ μεταφραση."""
    path = os.path.join(ROOT, f'data_{second_div}_{PROMO_SEASON}.json')
    if not os.path.exists(path):
        return {}, None
    with open(path, encoding='utf-8') as fh:
        d = json.load(fh)
    from collections import defaultdict
    ag = defaultdict(lambda: dict(name='', sf=0, xf=0.0, sa=0, xa=0.0, n=0))
    for m in d.values():
        h, a = m['home'], m['away']; xf = {h['id']: 0.0, a['id']: 0.0}; sh = {h['id']: 0, a['id']: 0}
        for s in m.get('shots', []):
            if s.get('sit') != 'Penalty' and s.get('xg') is not None and s.get('tid') in xf:
                xf[s['tid']] += s['xg']; sh[s['tid']] += 1
        for t, o in [(h['id'], a['id']), (a['id'], h['id'])]:
            ag[t]['name'] = h['name'] if t == h['id'] else a['name']
            ag[t]['sf'] += sh[t]; ag[t]['xf'] += xf[t]; ag[t]['sa'] += sh[o]; ag[t]['xa'] += xf[o]; ag[t]['n'] += 1
    out = {}
    for tid, v in ag.items():
        if v['n'] < 10:
            continue
        n = v['n']
        out[int(tid)] = dict(name=v['name'], xf=v['xf']/n, xa=v['xa']/n, sf=v['sf']/n, sa=v['sa']/n)
    if not out:
        return {}, None
    mean = {k: sum(v[k] for v in out.values()) / len(out) for k in ('xf', 'xa', 'sf', 'sa')}
    return out, mean

def promoted_priors(league, newcomer_ids, lg_shots, lg_xgps, id2name=None):
    """{tid: (name, synthetic_hist)} για τις ΝΕΟΦΩΤΙΣΤΕΣ που παιζουν φετος.

    επιπεδο   = μεσος λιγκας × per-league συντελεστη
    ξεχωρισμα = × (θεση της στη 2η κατηγορια / μεσος ΤΩΝ ΝΕΟΦΩΤΙΣΤΩΝ)^λ   (οπου εχουμε δεδομενα)
    Οσες δεν εχουν δεδομενα 2ης κατηγοριας -> σκετο το επιπεδο (λ ανενεργο).
    """
    if not newcomer_ids:
        return {}
    coef = PROMO_COEF.get(league, PROMO_POOLED)
    lgX = lg_shots * lg_xgps
    base = dict(xf=lgX * coef['xf'], xa=lgX * coef['xa'],
                sf=lg_shots * coef['sf'], sa=lg_shots * coef['sa'])
    stats, dmean = _second_div_stats(SECOND_DIV[league]) if league in SECOND_DIV else ({}, None)
    have = {t: stats[t] for t in newcomer_ids if t in stats}
    pm = None
    if have and dmean:                      # μεσος ΤΩΝ ΝΕΟΦΩΤΙΣΤΩΝ (αυτο-κανονικοποιηση)
        pm = {k: sum(v[k] / dmean[k] for v in have.values()) / len(have) for k in ('xf', 'xa', 'sf', 'sa')}
    out = {}
    for t in newcomer_ids:
        v = have.get(t)
        if v and pm:
            f = {k: max((v[k] / dmean[k]) / pm[k], 1e-6) ** PROMO_LAMBDA for k in ('xf', 'xa', 'sf', 'sa')}
        else:
            f = dict(xf=1.0, xa=1.0, sf=1.0, sa=1.0)
        xf = base['xf'] * f['xf']; xa = base['xa'] * f['xa']
        sf = max(base['sf'] * f['sf'], 1.0); sa = max(base['sa'] * f['sa'], 1.0)
        nm = (v or {}).get('name') or (id2name or {}).get(t) or str(t)
        K = 8
        out[t] = (nm, dict(sf=[sf]*K, xf=[xf]*K, sa=[sa]*K, xa=[xa]*K, gf=[xf]*K, ga=[xa]*K))
    return out

_FOT_HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
def _fotmob(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=_FOT_HDR), timeout=30).read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

def fetch_upcoming(league):
    """Επερχομενα (not-started) fixtures της λιγκας 26/27 απο FotMob."""
    lid = LEAGUE_FOTMOB[league]
    d = _fotmob(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={CURRENT_FOTMOB_SEASON}')
    out = []
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {})
        if st.get('started') or st.get('cancelled') or st.get('finished'):
            continue
        h, a = m.get('home', {}), m.get('away', {})
        out.append(dict(gw=int(m.get('round') or 0), utc=st.get('utcTime', ''),
                        fid=m.get('id'),
                        home_name=h.get('name'), home_id=h.get('id'),
                        away_name=a.get('name'), away_id=a.get('id')))
    return out

def predict_full(hh, ha, lg_shots, lg_xgps, hf):
    """Ιδιο math με picks.predict() αλλα εκθετει ΟΛΑ τα ενδιαμεσα (exp_shots, xg/shot, neutral, adj)."""
    af = 1.0 / hf
    def blx(t, fx, fg):
        return picks.BLEND * picks.wmean(t[fx]) + (1 - picks.BLEND) * picks.wmean(t[fg])
    Hax = blx(hh, 'xf', 'gf') / max(picks.wmean(hh['sf']), 1e-9)
    Hdx = blx(hh, 'xa', 'ga') / max(picks.wmean(hh['sa']), 1e-9)
    Aax = blx(ha, 'xf', 'gf') / max(picks.wmean(ha['sf']), 1e-9)
    Adx = blx(ha, 'xa', 'ga') / max(picks.wmean(ha['sa']), 1e-9)
    esh_h = (picks.wmean(hh['sf']) / lg_shots) * (picks.wmean(ha['sa']) / lg_shots) * lg_shots
    esh_a = (picks.wmean(ha['sf']) / lg_shots) * (picks.wmean(hh['sa']) / lg_shots) * lg_shots
    xgps_h = Hax * (Adx / lg_xgps)   # effective npxG/shot για το matchup
    xgps_a = Aax * (Hdx / lg_xgps)
    neu_h = esh_h * xgps_h; neu_a = esh_a * xgps_a
    return dict(home_exp_shots=round(esh_h, 3), home_xg_shot=round(xgps_h, 5),
                home_xg=round(neu_h, 3), home_adj_xg=round(neu_h * hf, 3),
                away_exp_shots=round(esh_a, 3), away_xg_shot=round(xgps_a, 5),
                away_xg=round(neu_a, 3), away_adj_xg=round(neu_a * af, 3))

_F = [factorial(i) for i in range(13)]
def one_x_two(lh, la):
    """1X2 πιθανοτητες (%) + fair odds απο Poisson + draw-boost (ιδιο με picks.gd_dist)."""
    lh = max(lh, 0.05); la = max(la, 0.05)
    ph = [exp(-lh) * lh ** i / _F[i] for i in range(13)]
    pa = [exp(-la) * la ** j / _F[j] for j in range(13)]
    hw = dw = aw = 0.0
    for i in range(13):
        for j in range(13):
            p = ph[i] * pa[j] * (picks.DRAW_BOOST if i == j else 1.0)
            if i > j: hw += p
            elif i == j: dw += p
            else: aw += p
    t = hw + dw + aw
    hw, dw, aw = hw / t, dw / t, aw / t
    return dict(hw=round(hw * 100, 1), d=round(dw * 100, 1), aw=round(aw * 100, 1),
                hw_odds=round(1 / hw, 2) if hw else None,
                d_odds=round(1 / dw, 2) if dw else None,
                aw_odds=round(1 / aw, 2) if aw else None)

# ---------- warm-start blend: prior (flat περσινο) + in-season (φετινο), w=n/(n+K_WARM) ----------
def _rating(h, n=None):
    """(Ax,Dx,SF,SA) απο rolling history.
    n = παιγμενα ματς ΦΕΤΟΣ -> ραμπα blend (picks.blend_at). n=None -> ωριμο 60/40,
    που ειναι το σωστο για το ΠΕΡΣΙΝΟ prior (πληρης σεζον)."""
    b = picks.blend_at(n)
    sf = picks.wmean(h['sf']); sa = picks.wmean(h['sa'])
    Ax = (b * picks.wmean(h['xf']) + (1 - b) * picks.wmean(h['gf'])) / max(sf, 1e-9)
    Dx = (b * picks.wmean(h['xa']) + (1 - b) * picks.wmean(h['ga'])) / max(sa, 1e-9)
    return (Ax, Dx, sf, sa)

def _shrink(r, prior, n, K=K_WARM):
    """Geometric shrink προς prior· w=n/(n+K) (ιδιο με sos_test.shrink_prior)."""
    w = n / (n + K)
    return tuple(max(pi, 1e-9) * (max(ri, 1e-9) / max(pi, 1e-9)) ** w for ri, pi in zip(r, prior))

def _predict_ratings(rh, ra, lg_shots, lg_xgps, hf):
    """Ιδιο math με predict_full αλλα δεχεται ΕΤΟΙΜΑ (blended) rating tuples."""
    Ax_h, Dx_h, SF_h, SA_h = rh; Ax_a, Dx_a, SF_a, SA_a = ra
    af = 1.0 / hf
    esh_h = (SF_h / lg_shots) * (SA_a / lg_shots) * lg_shots
    esh_a = (SF_a / lg_shots) * (SA_h / lg_shots) * lg_shots
    xgps_h = Ax_h * (Dx_a / lg_xgps); xgps_a = Ax_a * (Dx_h / lg_xgps)
    neu_h = esh_h * xgps_h; neu_a = esh_a * xgps_a
    return dict(home_exp_shots=round(esh_h, 3), home_xg_shot=round(xgps_h, 5),
                home_xg=round(neu_h, 3), home_adj_xg=round(neu_h * hf, 3),
                away_exp_shots=round(esh_a, 3), away_xg_shot=round(xgps_a, 5),
                away_xg=round(neu_a, 3), away_adj_xg=round(neu_a * af, 3))

def blend_league(prior_r, histc, K=K_WARM):
    """prior_r: {tid:(Ax,Dx,SF,SA)} flat περσινο. histc: {tid: φετινο in-season hist}.
    -> ({tid: blended rating}, {tid: n φετινα ματς}). n=0 → καθαρα prior· χωρις prior → θελει n>=MIN_PRIOR."""
    out = {}; ns = {}
    for tid in set(prior_r) | set(histc):
        hc = histc.get(tid); n = len(hc['sf']) if hc else 0; ns[tid] = n
        pr = prior_r.get(tid)
        if n == 0:
            if pr is not None:
                out[tid] = pr
        else:
            ri = _rating(hc, n)      # ραμπα blend αναλογα με τα φετινα ματς
            if pr is not None:
                out[tid] = _shrink(ri, pr, n, K)
            elif n >= picks.MIN_PRIOR:      # νεα ομαδα χωρις prior → μονο με αρκετα φετινα ματς
                out[tid] = ri
    return out, ns

def league_ratings(lg, Mp, Mc, ratings_season=RATINGS_SEASON_DEFAULT,
                   current_season=CURRENT_SEASON, id2name=None, name2id=None):
    """ΚΟΙΝΗ λογικη ratings μιας λιγκας — χρησιμοποιειται ΚΑΙ απο το dashboard ΚΑΙ απο τον scanner.
    ΜΗΝ την διπλασιασεις αλλου: καθε αλλαγη (νεοφωτιστες/K/prior) πρεπει να ισχυει και στα δυο.

    -> dict(blended, ns, lg_shots, lg_xgps, hf, fixtures, promoted)
    """
    id2name = id2name if id2name is not None else {}
    name2id = name2id if name2id is not None else {}
    histp, lg_shots, lg_xgps, hf = picks.league_state(Mp, lg, ratings_season)
    fixtures = fetch_upcoming(lg)          # χρειαζεται για να ξερουμε ΠΟΙΕΣ ειναι οι νεοφωτιστες
    fx_ids = set(); fx_names = {}
    for f in fixtures:
        for ik, nk in (('home_id', 'home_name'), ('away_id', 'away_name')):
            if f.get(ik):
                fx_ids.add(int(f[ik])); fx_names.setdefault(int(f[ik]), f.get(nk))
    for t, nm in fx_names.items():
        if nm:
            id2name.setdefault(t, nm); name2id.setdefault(nm, t)
    newcomers = sorted(t for t in fx_ids if t not in histp)
    promoted = set()
    for tid, (nm, synth) in promoted_priors(lg, newcomers, lg_shots, lg_xgps, id2name).items():
        histp[tid] = synth; id2name.setdefault(tid, nm)
        name2id.setdefault(nm, tid); promoted.add(tid)
    histp = flatten_warmstart(histp, lg)                         # flat περσινο prior
    prior_r = {tid: _rating(h) for tid, h in histp.items() if h.get('sf')}
    histc, cur_shots, cur_xgps, _ = picks.league_state(Mc, lg, current_season)  # φετινο rolling (in-season)
    # ---------- χαρακας λιγκας: ραμπα περσινος -> φετινος (KN_NORM) ----------
    # Ολη η προβλεψη ειναι "ποσες φορες τον μεσο ορο" (= $B$22/$Q$22 του αρχικου Google Sheet),
    # οποτε ο μεσος ορος πρεπει να ειναι της ΙΔΙΑΣ εποχης με τα ratings — αλλιως ολα βγαινουν
    # κλιμακωμενα λαθος. Τα SF/SA του blended ειναι ηδη κυριως φετινα· ο χαρακας ακολουθει.
    nc = sum(len(h['sf']) for h in histc.values())
    if nc and cur_shots and cur_xgps:
        w = nc / (nc + KN_NORM)
        lg_shots = lg_shots * (cur_shots / lg_shots) ** w
        lg_xgps = lg_xgps * (cur_xgps / lg_xgps) ** w
    blended, ns = blend_league(prior_r, histc)                    # warm-start blend K=K_WARM
    if picks.SOS:                        # SoS: διορθωση για τη δυσκολια του ΦΕΤΙΝΟΥ προγραμματος
        blended = {tid: picks.sos_adjust(r, histc.get(tid, {}).get('opp', []),
                                         blended, lg_shots, lg_xgps)
                   for tid, r in blended.items()}
    return dict(blended=blended, ns=ns, lg_shots=lg_shots, lg_xgps=lg_xgps, hf=hf,
                fixtures=fixtures, promoted=promoted)

def build_matches(ratings_season=RATINGS_SEASON_DEFAULT, current_season=CURRENT_SEASON, leagues=None):
    leagues = leagues or list(LEAGUE_FOTMOB)
    Mp, id2name = picks.load_matches(list(LEAGUE_FOTMOB), [ratings_season])   # περσινο (prior)
    Mc, id2c = picks.load_matches(list(LEAGUE_FOTMOB), [current_season])      # φετινο (in-season)
    id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    market = _market_1x2()
    out = []; stats = {}
    for lg in leagues:
        try:
            LR = league_ratings(lg, Mp, Mc, ratings_season, current_season, id2name, name2id)
        except Exception as e:
            stats[lg] = dict(fixtures=0, projected=0, error=str(e)[:120]); continue
        blended, ns = LR['blended'], LR['ns']
        lg_shots, lg_xgps, hf = LR['lg_shots'], LR['lg_xgps'], LR['hf']
        fixtures, promoted = LR['fixtures'], LR['promoted']
        proj = 0
        for f in fixtures:
            H = name2id.get(f['home_name']); A = name2id.get(f['away_name'])
            if H is None and f['home_id'] and int(f['home_id']) in blended: H = int(f['home_id'])
            if A is None and f['away_id'] and int(f['away_id']) in blended: A = int(f['away_id'])
            rec = dict(league=lg, gw=f['gw'], utc=f['utc'], fid=f.get('fid'),
                       home=f['home_name'], away=f['away_name'],
                       home_id=f['home_id'], away_id=f['away_id'], projectable=False,
                       promoted=(H in promoted or A in promoted))
            rh = blended.get(H); ra = blended.get(A)
            if rh and ra:
                pf = _predict_ratings(rh, ra, lg_shots, lg_xgps, hf)
                pf.update(one_x_two(pf['home_adj_xg'], pf['away_adj_xg']))
                nh = ns.get(H, 0); na = ns.get(A, 0)
                pf['warm_cur'] = round((nh / (nh + K_WARM) + na / (na + K_WARM)) / 2, 3)  # μεσο βαρος φετινου
                rec.update(pf); rec['projectable'] = True; proj += 1
                mo = market.get(f"{H}_{A}")
                if mo:
                    rec['mkt_hw_odds'], rec['mkt_d_odds'], rec['mkt_aw_odds'] = mo.get('h'), mo.get('d'), mo.get('a')
            out.append(rec)
        stats[lg] = dict(fixtures=len(fixtures), projected=proj)
    return out, stats

if __name__ == '__main__':
    lgs = sys.argv[1:] or ['EPL']
    matches, stats = build_matches(leagues=lgs)
    print('STATS:', json.dumps(stats, ensure_ascii=False))
    proj = [m for m in matches if m['projectable']]
    print(f'\n{len(proj)} projectable / {len(matches)} total. Πρωτα 6:')
    for m in proj[:6]:
        print(f"  GW{m['gw']} {m['home']} vs {m['away']}: "
              f"xG {m['home_adj_xg']}-{m['away_adj_xg']}  |  {m['hw']}%/{m['d']}%/{m['aw']}%  "
              f"(fair {m['hw_odds']}/{m['d_odds']}/{m['aw_odds']})")
