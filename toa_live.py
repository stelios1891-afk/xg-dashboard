"""
toa_live.py — LIVE value picks μεσω The Odds API (TOA· πληρωμενη συνδρομη ~100k/μηνα).

Τραβαει τρεχοντα Asian Handicap (spreads) Pinnacle+Matchbook ανα λιγκα (~1 credit/λιγκα),
ταιριαζει ονοματα με το μοντελο (FotMob), και βγαζει value +handicap picks (ιδια μηχανη
& staking με live_odds.compute_picks). Το μοντελο ΒΑΘΜΟΝΟΜΗΘΗΚΕ σε TOA odds → σωστη πηγη.

TOA_KEY: inline env var (NEVER σε αρχειο). Κοστος: markets=spreads × region=eu = 1 credit/λιγκα.
"""
import os, sys, time
from collections import defaultdict
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picks as engine
import live_odds   # reuse assign() / team_match()

BASE = 'https://api.the-odds-api.com/v4'
SPORT = {'EPL': 'soccer_epl', 'LaLiga': 'soccer_spain_la_liga', 'SerieA': 'soccer_italy_serie_a',
         'Bundesliga': 'soccer_germany_bundesliga', 'Ligue1': 'soccer_france_ligue_one',
         'PrimeiraLiga': 'soccer_portugal_primeira_liga', 'Belgium': 'soccer_belgium_first_div',
         'Eredivisie': 'soccer_netherlands_eredivisie', 'ScottishPrem': 'soccer_spl'}
# TOA ονομα -> FotMob/μοντελο ονομα (προσθηκες οποτε φανει block)
TOA_ALIAS = {}

def _key():
    k = os.environ.get('TOA_KEY')
    if not k:
        raise RuntimeError("TOA_KEY δεν βρεθηκε στο environment (inline).")
    return k

def _pb(g, bk):
    """AH (spreads) γραμμη ενος bookmaker -> (line_home_persp, home_odds, away_odds)."""
    ht, at = g.get('home_team'), g.get('away_team')
    for b in g.get('bookmakers', []):
        if b.get('key') != bk:
            continue
        for m in b.get('markets', []):
            if m.get('key') == 'spreads':
                hp = ha = aa = None
                for o in m.get('outcomes', []):
                    if o.get('name') == ht:
                        hp = o.get('point'); ha = o.get('price')
                    elif o.get('name') == at:
                        aa = o.get('price')
                if hp is not None and ha and aa:
                    return (float(hp), float(ha), float(aa))
    return None

def fetch_all(leagues):
    """{league: [fixtures]} + credits_remaining, credits_cost. 1 request/λιγκα."""
    out = {}; rem = None; cost = 0
    for lg in leagues:
        sport = SPORT.get(lg)
        if not sport:
            out[lg] = []; continue
        r = requests.get(f'{BASE}/sports/{sport}/odds',
                         params=dict(apiKey=_key(), regions='eu', markets='spreads',
                                     bookmakers='pinnacle,matchbook', oddsFormat='decimal'), timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        try:
            cost += int(r.headers.get('x-requests-last') or 0)
        except ValueError:
            pass
        if r.status_code != 200:
            out[lg] = []; continue
        fx = []
        for g in r.json():
            pin = _pb(g, 'pinnacle'); mb = _pb(g, 'matchbook')
            if pin and mb and abs(pin[0] - mb[0]) < 0.01:
                c = (pin[0], max(pin[1], mb[1]), max(pin[2], mb[2]))   # best price και των δυο
            else:
                c = pin or mb
            if not c:
                continue
            fx.append(dict(home_toa=g.get('home_team'), away_toa=g.get('away_team'),
                           line=c[0], home_odds=c[1], away_odds=c[2],
                           startTime=(g.get('commence_time') or '')[:16]))
        out[lg] = fx
        time.sleep(0.3)
    return out, rem, cost

def _al(n):
    return TOA_ALIAS.get(n, n)

def compute_picks_toa(leagues, ratings_season):
    """Structured value picks απο TOA — ιδια εξοδος με live_odds.compute_picks (+credits)."""
    M, id2name = engine.load_matches(list(SPORT), [ratings_season])
    name2id = {v: k for k, v in id2name.items()}
    lg_names = defaultdict(set)
    for _, r in M.iterrows():
        lg_names[r['league']].add(id2name.get(r['home']))
        lg_names[r['league']].add(id2name.get(r['away']))
    allfix, rem, cost = fetch_all(leagues)
    all_picks, all_blocked, all_norating = [], [], []
    for lg in leagues:
        state = engine.league_state(M, lg, ratings_season)
        fixtures = allfix.get(lg, [])
        toa_names = sorted({_al(n) for f in fixtures for n in (f['home_toa'], f['away_toa']) if n})
        res = live_odds.assign(toa_names, sorted(x for x in lg_names.get(lg, set()) if x))
        for f in fixtures:
            hfot, hok, hnote = live_odds.team_match(_al(f['home_toa']), res)
            afot, aok, anote = live_odds.team_match(_al(f['away_toa']), res)
            if not (hok and aok):
                bad = f['home_toa'] if not hok else f['away_toa']
                all_blocked.append((lg, f, bad, hnote if not hok else anote)); continue
            H = name2id.get(hfot); A = name2id.get(afot)
            if H is None or A is None:
                all_norating.append((lg, f, hfot if H is None else afot, 'δεν υπαρχει στα ratings')); continue
            pred = engine.predict_ids(state, H, A)
            if pred is None:
                all_norating.append((lg, f, f"{hfot}/{afot}", f'<{engine.MIN_PRIOR} ματς ιστορικο')); continue
            xg_h, xg_a = pred
            for b in engine.evaluate_bet(xg_h, xg_a, f['line'], f['home_odds'], f['away_odds']):
                all_picks.append(dict(lg=lg, home=hfot, away=afot, home_id=H, away_id=A,
                                      when=f['startTime'], **b, hnote=hnote, anote=anote))
    KELLY_FRAC = 0.125; CAP = 0.20
    for p in all_picks:
        p['stake'] = KELLY_FRAC * p['edge'] / (p['odds'] - 1)
    gross = sum(p['stake'] for p in all_picks)
    scale = CAP / gross if gross > CAP else 1.0
    for p in all_picks:
        p['stake_final'] = p['stake'] * scale
    return dict(picks=all_picks, blocked=all_blocked, norating=all_norating,
                gross=gross, scale=scale, cap=CAP, credits_remaining=rem, credits_cost=cost)

if __name__ == '__main__':
    res = compute_picks_toa(list(SPORT), sys.argv[1] if len(sys.argv) > 1 else '2526')
    print(f"credits remaining {res['credits_remaining']} · κοστος αυτου του scan {res['credits_cost']}")
    print(f"picks {len(res['picks'])} · blocked {len(res['blocked'])} · norating {len(res['norating'])}\n")
    for p in sorted(res['picks'], key=lambda x: -x['edge'])[:20]:
        team = p['home'] if p['side'] == 1 else p['away']
        print(f"  [{p['lg']}] {p['home']}–{p['away']}: {team} {'+' if p['hcap']>=0 else ''}{p['hcap']:g} "
              f"· Betfair {p['odds']:.2f} · proj {p['proj_odds']:.2f} · edge {p['edge']*100:.0f}% · "
              f"ποντ {p['stake_final']*100:.1f}%")
    if res['blocked']:
        print(f"\nblocked ονοματα (χρειαζονται alias):")
        for lg, f, bad, reason in res['blocked'][:15]:
            print(f"  [{lg}] {f['home_toa']} v {f['away_toa']} -> «{bad}» {reason}")
