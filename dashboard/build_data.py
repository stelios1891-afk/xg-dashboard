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

RATINGS_SEASON_DEFAULT = '2526'   # τελευταια πληρης σεζον (warm-start για 26/27)
CURRENT_FOTMOB_SEASON = '2026%2F2027'
LEAGUE_FOTMOB = {'EPL': 47, 'LaLiga': 87, 'SerieA': 55, 'Bundesliga': 54, 'Ligue1': 53,
                 'Belgium': 40, 'ScottishPrem': 64, 'Eredivisie': 57, 'PrimeiraLiga': 61}

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

def build_matches(ratings_season=RATINGS_SEASON_DEFAULT, leagues=None):
    leagues = leagues or list(LEAGUE_FOTMOB)
    M, id2name = picks.load_matches(list(LEAGUE_FOTMOB), [ratings_season])
    name2id = {v: k for k, v in id2name.items()}
    out = []; stats = {}
    for lg in leagues:
        hist, lg_shots, lg_xgps, hf = picks.league_state(M, lg, ratings_season)
        try:
            fixtures = fetch_upcoming(lg)
        except Exception as e:
            stats[lg] = dict(fixtures=0, projected=0, error=str(e)[:120]); continue
        proj = 0
        for f in fixtures:
            H = name2id.get(f['home_name']); A = name2id.get(f['away_name'])
            if H is None and f['home_id'] and int(f['home_id']) in hist: H = int(f['home_id'])
            if A is None and f['away_id'] and int(f['away_id']) in hist: A = int(f['away_id'])
            rec = dict(league=lg, gw=f['gw'], utc=f['utc'],
                       home=f['home_name'], away=f['away_name'],
                       home_id=f['home_id'], away_id=f['away_id'], projectable=False)
            hh = hist.get(H); ha = hist.get(A)
            if hh and ha and len(hh['sf']) >= picks.MIN_PRIOR and len(ha['sf']) >= picks.MIN_PRIOR:
                pf = predict_full(hh, ha, lg_shots, lg_xgps, hf)
                pf.update(one_x_two(pf['home_adj_xg'], pf['away_adj_xg']))
                rec.update(pf); rec['projectable'] = True; proj += 1
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
