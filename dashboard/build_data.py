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
K_WARM = 6.0                      # warm-start blend: βαρος_φετινου = n/(n+K)· βρεθηκε με backtest (warmstart_k_test.py, RPS, LOSO-σταθερο 5-7)
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

# --- Νεοφωτιστες: prior απο 2η κατηγορια × μεταφραση (βλ. memory promoted-team-translation) ---
SECOND_DIV = {'EPL': 'Championship', 'LaLiga': 'LaLiga2', 'SerieA': 'SerieB',
              'Bundesliga': 'Bundesliga2', 'Ligue1': 'Ligue2'}
PROMO_SEASON = '2526'
PROMO_ATT, PROMO_DEF = 0.65, 1.50   # xGF ×0.65 (−35%), xGA ×1.5 (+50%) — England-validated (approx αλλες χωρες)
PROMO_SF, PROMO_SA = 0.73, 1.34     # σουτ επιθεσης ×0.73, δεχομενα σουτ ×1.34 (για ρεαλιστικο shots display)

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

def _promoted_synth(second_div):
    """{tid: (name, synthetic_hist)} — ομαδες 2ης κατηγοριας με μεταφρασμενο (translated) rating.
    Το synthetic hist ειναι 8 σταθερα 'ματς' ωστε το predict_full να τις χειριζεται σαν κανονικες."""
    path = os.path.join(ROOT, f'data_{second_div}_{PROMO_SEASON}.json')
    if not os.path.exists(path):
        return {}
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
        sf = (v['sf'] / n) * PROMO_SF; xf = (v['xf'] / n) * PROMO_ATT        # attack (translated)
        sa = (v['sa'] / n) * PROMO_SA; xa = (v['xa'] / n) * PROMO_DEF        # defense (translated)
        K = 8
        out[tid] = (v['name'], dict(sf=[sf]*K, xf=[xf]*K, sa=[sa]*K, xa=[xa]*K, gf=[xf]*K, ga=[xa]*K))
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
def _rating(h):
    """(Ax,Dx,SF,SA) απο rolling history — ιδιο math με sos_test.ratings."""
    sf = picks.wmean(h['sf']); sa = picks.wmean(h['sa'])
    Ax = (picks.BLEND * picks.wmean(h['xf']) + (1 - picks.BLEND) * picks.wmean(h['gf'])) / max(sf, 1e-9)
    Dx = (picks.BLEND * picks.wmean(h['xa']) + (1 - picks.BLEND) * picks.wmean(h['ga'])) / max(sa, 1e-9)
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
            ri = _rating(hc)
            if pr is not None:
                out[tid] = _shrink(ri, pr, n, K)
            elif n >= picks.MIN_PRIOR:      # νεα ομαδα χωρις prior → μονο με αρκετα φετινα ματς
                out[tid] = ri
    return out, ns

def build_matches(ratings_season=RATINGS_SEASON_DEFAULT, current_season=CURRENT_SEASON, leagues=None):
    leagues = leagues or list(LEAGUE_FOTMOB)
    Mp, id2name = picks.load_matches(list(LEAGUE_FOTMOB), [ratings_season])   # περσινο (prior)
    Mc, id2c = picks.load_matches(list(LEAGUE_FOTMOB), [current_season])      # φετινο (in-season)
    id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    market = _market_1x2()
    out = []; stats = {}
    for lg in leagues:
        histp, lg_shots, lg_xgps, hf = picks.league_state(Mp, lg, ratings_season)
        # --- νεοφωτιστες (2η κατηγορια × μεταφραση) ως prior ---
        promoted = set()
        if lg in SECOND_DIV:
            for tid, (nm, synth) in _promoted_synth(SECOND_DIV[lg]).items():
                if tid not in histp:
                    histp[tid] = synth; id2name.setdefault(tid, nm)
                    name2id.setdefault(nm, tid); promoted.add(tid)
        histp = flatten_warmstart(histp, lg)                       # flat περσινο prior
        prior_r = {tid: _rating(h) for tid, h in histp.items() if h.get('sf')}
        histc, _, _, _ = picks.league_state(Mc, lg, current_season)  # φετινο rolling (in-season)
        blended, ns = blend_league(prior_r, histc)                  # blend K=6 ανα ομαδα
        try:
            fixtures = fetch_upcoming(lg)
        except Exception as e:
            stats[lg] = dict(fixtures=0, projected=0, error=str(e)[:120]); continue
        proj = 0
        for f in fixtures:
            H = name2id.get(f['home_name']); A = name2id.get(f['away_name'])
            if H is None and f['home_id'] and int(f['home_id']) in blended: H = int(f['home_id'])
            if A is None and f['away_id'] and int(f['away_id']) in blended: A = int(f['away_id'])
            rec = dict(league=lg, gw=f['gw'], utc=f['utc'],
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
