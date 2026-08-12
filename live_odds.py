"""
live_odds.py  -  ΒΗΜΑ 5β (μεταφραστης OddsPapi -> μοντελο).

Παιρνει επερχομενα fixtures + Betfair Exchange Asian Handicap odds απο το OddsPapi
(το Pinnacle feed ειναι stale — βλ. fetch_fixtures), ταιριαζει τα ονοματα ομαδων με
τα ονοματα του μοντελου (FotMob), και τα δινει στη μηχανη picks.py για value +handicap picks.

Το API key διαβαζεται απο το environment variable ODDSPAPI_KEY (οχι απο αρχειο).

Χρηση:
    python live_odds.py check-names EPL      # πινακας αντιστοιχισης ονοματων (για ελεγχο)
    python live_odds.py check-names all       # ολες οι top-5 λιγκες
"""
import os, sys, json, re, time, unicodedata, urllib.request, gzip
from collections import defaultdict, Counter
import requests

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ονομα -> {FotMob league id, OddsPapi tournament id}
LEAGUES = {
    'EPL':          {'fotmob': 47, 'oddspapi': 17},
    'LaLiga':       {'fotmob': 87, 'oddspapi': 8},
    'SerieA':       {'fotmob': 55, 'oddspapi': 23},
    'Bundesliga':   {'fotmob': 54, 'oddspapi': 35},
    'Ligue1':       {'fotmob': 53, 'oddspapi': 34},
    # --- προσθηκες Phase-2 (backtest-validated, ανεξαρτητη βαθμονομηση) ---
    'Eredivisie':   {'fotmob': 57, 'oddspapi': 37},    # @15η+ closing +8.4%
    'PrimeiraLiga': {'fotmob': 61, 'oddspapi': 238},   # @15η+ closing +7.6%
    # ΑΦΑΙΡΕΘΗΚΑΝ (2026-08-11): Belgium (fotmob 40/oddspapi 38) & ScottishPrem (64/36) —
    # 5-season sharp = θορυβος/αρνητικες @15η+ (Belgium −11%, Scottish −7.6%, μικρο ασταθες δειγμα).
}
# Λιγκες σε "παρατηρηση": παραγουν picks/alerts αλλα σημαινονται ⚠ watch (αδυναμο σημα,
# μικρο/μηδεν stake μεχρι να επιβεβαιωθει σε 3η σεζον 26/27). Belgium & top-5 = σιγουρα.
WATCH = {'PrimeiraLiga'}   # Belgium/Eredivisie/ScottishPrem βγηκαν απο WATCH (TOA-gold @18h validated 2 σεζον)
CURRENT_FOTMOB_SEASON = '2026%2F2027'   # 26/27

BASE = 'https://api.oddspapi.io'
_KEY = None
def key():
    global _KEY
    if _KEY is None:
        _KEY = os.environ.get('ODDSPAPI_KEY')
        if not _KEY:
            print("ΣΦΑΛΜΑ: δεν βρεθηκε το ODDSPAPI_KEY στο environment.\n"
                  "  Βαλ' το με (PowerShell):  [Environment]::SetEnvironmentVariable('ODDSPAPI_KEY','<key>','User')")
            sys.exit(1)
    return _KEY

# ---------- HTTP (throttled για το free-tier rate limit) ----------
def opapi(path, pause=1.5):
    time.sleep(pause)
    sep = '&' if '?' in path else '?'
    u = f'{BASE}{path}{sep}apiKey={key()}'
    r = requests.get(u, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"OddsPapi HTTP {r.status_code}: {r.text[:150]}")
    return r.json()

_FOT_HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
def fotmob(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=_FOT_HDR), timeout=30).read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

# ---------- ονοματα ----------
_PART = None
def participants():
    """OddsPapi χαρτης participantId -> ονομα (cache στη μνημη)."""
    global _PART
    if _PART is None:
        d = opapi('/v4/participants?sportId=10')
        _PART = {str(k): v for k, v in d.items()} if isinstance(d, dict) else {}
    return _PART

def oddspapi_team_names(league):
    """Μοναδικα ονοματα ομαδων απο τα επερχομενα Pinnacle fixtures της λιγκας."""
    tid = LEAGUES[league]['oddspapi']
    fx = opapi(f'/v4/odds-by-tournaments?tournamentIds={tid}&bookmaker=pinnacle')
    pmap = participants()
    names = set()
    for f in (fx if isinstance(fx, list) else []):
        for pid in (f.get('participant1Id'), f.get('participant2Id')):
            nm = pmap.get(str(pid))
            if nm:
                names.add(nm)
    return sorted(names)

def fotmob_team_names(league):
    """Ονοματα ομαδων της τρεχουσας σεζον απο το FotMob leagues endpoint (και απαικτα ματς)."""
    lid = LEAGUES[league]['fotmob']
    d = fotmob(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={CURRENT_FOTMOB_SEASON}')
    names = set()
    for m in d.get('fixtures', {}).get('allMatches', []):
        for side in ('home', 'away'):
            nm = m.get(side, {}).get('name')
            if nm:
                names.add(nm)
    return sorted(names)

# ---------- normalizer & resolver ----------
STOP = {'fc', 'cf', 'ac', 'afc', 'ss', 'us', 'as', 'rc', 'ud', 'sd', 'sc', 'rcd',
        'calcio', 'club', 'de', 'real', 'vfl', 'vfb', 'tsg', 'sv', 'bsc', 'og', '1', 'the'}
# χειροκινητες αντιστοιχισεις: OddsPapi ονομα -> FotMob ονομα
# (επιβεβαιωμενες με το ματι μεσω `check-names`, για ονοματα που ο αλγοριθμος
#  δεν πιανει σωστα η τα μπερδευει με αλλη ομαδα)
ALIAS = {
    'Espanyol Barcelona': 'Espanyol',      # αλλιως συγκρουεται με 'Barcelona'
    '1. FC Cologne':      '1. FC Köln',     # Cologne = Köln (0 κοινα tokens)
}

def toks(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z0-9 ]', ' ', s).split()) - STOP)

def assign(opapi_names, fot_names):
    """1-προς-1 αντιστοιχιση OddsPapi -> FotMob.
    Πρωτα τα aliases (forced), μετα greedy με σειρα (overlap, jaccard) φθινουσα,
    ωστε καθε FotMob ομαδα να χρησιμοποιειται το πολυ μια φορα (αποφυγη συγκρουσεων).
    Επιστρεφει dict: opapi_name -> (fot_name|None, overlap, jaccard, method)."""
    ft = {n: toks(n) for n in fot_names}
    result = {}; used = set()
    # 1) forced aliases
    pending = []
    for nm in opapi_names:
        tgt = ALIAS.get(nm)
        if tgt and tgt in ft and tgt not in used:
            result[nm] = (tgt, 99, 1.0, 'alias'); used.add(tgt)
        else:
            pending.append(nm)
    # 2) greedy 1-προς-1 στα υπολοιπα
    cand = []
    for nm in pending:
        tn = toks(nm)
        for fn in fot_names:
            ov = len(tn & ft[fn])
            if ov:
                cand.append((ov, ov / max(len(tn | ft[fn]), 1), nm, fn))
    cand.sort(key=lambda x: (-x[0], -x[1]))
    done = set(result)
    for ov, j, nm, fn in cand:
        if nm in done or fn in used:
            continue
        result[nm] = (fn, ov, round(j, 2), 'auto'); done.add(nm); used.add(fn)
    for nm in opapi_names:
        result.setdefault(nm, (None, 0, 0.0, 'NONE'))
    return result

# ---------- εντολη: check-names ----------
def check_league(league):
    print(f"\n{'='*72}\n  {league}  -  αντιστοιχιση ονοματων  (OddsPapi  ->  FotMob/μοντελο)\n{'='*72}")
    try:
        opapi_names = oddspapi_team_names(league)
    except Exception as e:
        print(f"  OddsPapi σφαλμα: {e}"); return
    try:
        fot_names = fotmob_team_names(league)
    except Exception as e:
        print(f"  FotMob σφαλμα: {e}"); return

    res = assign(opapi_names, fot_names)
    print(f"  OddsPapi ομαδες: {len(opapi_names)}   |   FotMob ομαδες: {len(fot_names)}\n")
    print(f"  {'OddsPapi':30s} -> {'FotMob (μοντελο)':28s} {'ov':>3s} {'jac':>5s}  σημ.")
    print(f"  {'-'*30}    {'-'*28} {'-'*3} {'-'*5}  ----")
    matched_fot = set()
    weak = []
    for nm in opapi_names:
        best, ov, j, method = res[nm]
        matched_fot.add(best)
        if best is None:
            flag = 'ΚΑΜΙΑ!'
        elif method == 'alias':
            flag = 'alias'
        elif j >= 0.5 or ov >= 2:
            flag = 'OK'
        else:
            flag = 'WEAK'
        if flag in ('WEAK', 'ΚΑΜΙΑ!'):
            weak.append(nm)
        jshow = 1.00 if method == 'alias' else j
        print(f"  {nm:30s} -> {str(best):28s} {ov:>3d} {jshow:>5.2f}  {flag}")

    # FotMob ομαδες που δεν ταιριαχτηκαν με καμια OddsPapi
    unpaired = [n for n in fot_names if n not in matched_fot]
    if unpaired:
        print(f"\n  ⚠ FotMob ομαδες ΧΩΡΙΣ αντιστοιχο OddsPapi ({len(unpaired)}):")
        for n in unpaired:
            print(f"      {n}")
    if weak:
        print(f"\n  ⚠ ΠΡΟΣ ΕΛΕΓΧΟ (weak/καμια): {', '.join(weak)}")
    if not weak and not unpaired:
        print("\n  ✔ Ολες οι ομαδες ταιριαξαν καθαρα (1-προς-1).")


# ---------- Betfair Exchange: κυρια full-match Asian Handicap γραμμη ----------
# ΓΙΑΤΙ Betfair κι οχι Pinnacle: το Pinnacle feed μεσω OddsPapi ειναι STALE (τιμες
# παγωμενες 2-9 μερες), ενω το Betfair Exchange ανανεωνεται καθε ~20 λεπτα. Το
# validation μας ειναι κι αυτο Betfair-based. Βλ. memory oddspapi-integration.
#
# ΤΟ ΚΡΙΣΙΜΟ — home/away: το Betfair δινει selection IDs χωρις ονομα ομαδας
# (participantId/playerName = null). ΛΥΣΗ (ντετερμινιστικη, οχι εικασια): το OddsPapi
# χρησιμοποιει ΚΟΙΝΑ outcome-keys σε ολους τους bookmakers — το ιδιο key σημαινει το
# ιδιο (side, line) παντου. Η Pinnacle δινει ΡΗΤΗ ετικετα '{line}/home|away' ανα key
# (structural — δεν εξαρταται απο την [stale] τιμη της). Διαβαζουμε λοιπον το
# key->side απο Pinnacle, και την ΤΙΜΗ (best availableToBack) απο Betfair στο ιδιο key.
# Επαληθευμενο: parity 100% καθαρη (ζυγα keys=home, μονα=away), 80/80 keys συμφωνια.

# Το home/away βασιζεται στα Pinnacle labels. Δικλειδες αν η Pinnacle φυγει καποτε (οπως
# το Marathonbet): (α) cache του key->side στον δισκο (τα keys ειναι σταθερα — κραταμε το
# τελευταιο γνωστο), (β) parity fallback (ζυγα keys=home, μονα=away — επαληθευμενο 66/66).
KEYMAP_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oddspapi_keymap.json')

def _load_keymap_cache():
    try:
        with open(KEYMAP_CACHE, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}

def _save_keymap_cache(km):
    try:
        with open(KEYMAP_CACHE, 'w', encoding='utf-8') as fh:
            json.dump(km, fh)
    except Exception:
        pass

def side_for_key(k, keymap):
    """side ενος outcome-key: πρωτα keymap (Pinnacle/cache), αλλιως parity fallback."""
    s = keymap.get(str(k))
    if s:
        return s
    try:
        return 'home' if int(k) % 2 == 0 else 'away'
    except (TypeError, ValueError):
        return None

def build_keymap(pinn_fixtures):
    """GLOBAL outcome-key -> side ('home'/'away') απο τα ρητα Pinnacle labels.
    Τα keys ειναι σταθερα, οποτε ενας χαρτης απ' ολα τα fixtures καλυπτει καθε γραμμη.
    Ανανεωνει & αποθηκευει cache· αν η Pinnacle λειπει, γυρνα το τελευταιο γνωστο cache."""
    votes = defaultdict(Counter)
    for f in pinn_fixtures:
        for m in f.get('bookmakerOdds', {}).get('pinnacle', {}).get('markets', {}).values():
            if 'spreads' not in str(m.get('bookmakerMarketId', '')):
                continue
            for k, o in m.get('outcomes', {}).items():
                oc = o.get('players', {}).get('0', {}).get('bookmakerOutcomeId', '')
                if '/' in oc:
                    _, side = oc.rsplit('/', 1)
                    if side in ('home', 'away'):
                        votes[str(k)][side] += 1
    fresh = {k: c.most_common(1)[0][0] for k, c in votes.items()}
    cache = _load_keymap_cache()
    if fresh:
        cache.update(fresh)
        _save_keymap_cache(cache)
    return cache

def betfair_main_line(bf_fixture, keymap):
    """(line_home_persp, home_back, away_back) της κυριας (πιο ισορροπημενης) γραμμης.
    Χρησιμοποιει ΟΛΟ το Betfair ladder: για καθε runner, το side ερχεται απ' το keymap
    και η γραμμη (home-perspective) απ' το bookmakerHandicap του ιδιου του Betfair."""
    lines = defaultdict(dict)
    for m in bf_fixture.get('bookmakerOdds', {}).get('betfair-ex', {}).get('markets', {}).values():
        for k, o in m.get('outcomes', {}).items():
            side = side_for_key(k, keymap)
            if side is None:
                continue
            p = o.get('players', {}).get('0', {})
            em = p.get('exchangeMeta') or {}
            hc = em.get('bookmakerHandicap')
            ab = em.get('availableToBack')
            if hc is None or not ab or not ab[0].get('price'):
                continue
            home_line = round(hc if side == 'home' else -hc, 2)   # home-perspective
            lines[home_line][side] = ab[0]['price']
    cands = [(abs(v['home'] - v['away']), ln, v['home'], v['away'])
             for ln, v in lines.items() if 'home' in v and 'away' in v]
    if not cands:
        return None
    _, ln, hb, ab = min(cands)
    return ln, hb, ab

def fetch_all_fixtures(leagues):
    """Fixtures ΟΛΩΝ των λιγκων με ΜΙΑ κληση/bookmaker (batch tournamentIds) — κραταει το
    request quota χαμηλα (free plan = 250/μηνα). 2 billable κλησεις συνολικα: pinnacle
    (key->side) + betfair-ex (τιμες). Διατρεχει τα Betfair fixtures (εχουν participant
    ids + τιμες)· η Pinnacle δινει μονο το key->side (με cache/parity fallback αν λειπει).
    Επιστρεφει {league: [fixtures]}."""
    tid2lg = {LEAGUES[lg]['oddspapi']: lg for lg in leagues}
    tids = list(tid2lg)
    pinn_all, bf_all = [], []
    for i in range(0, len(tids), 3):     # betfair-ex: max 3 tournamentIds/κληση
        ids = ','.join(str(t) for t in tids[i:i + 3])
        p = opapi(f'/v4/odds-by-tournaments?tournamentIds={ids}&bookmaker=pinnacle')
        b = opapi(f'/v4/odds-by-tournaments?tournamentIds={ids}&bookmaker=betfair-ex')
        if isinstance(p, list):
            pinn_all += p
        if isinstance(b, list):
            bf_all += b
    keymap = build_keymap(pinn_all)
    pmap = participants()
    out = {lg: [] for lg in leagues}
    for f in bf_all:
        lg = tid2lg.get(f.get('tournamentId'))
        if lg is None:
            continue
        ml = betfair_main_line(f, keymap)
        if ml is None:
            continue
        line, ho, ao = ml
        out[lg].append(dict(fixtureId=f.get('fixtureId'), startTime=f.get('startTime', '')[:16],
                            home_opapi=pmap.get(str(f.get('participant1Id'))),
                            away_opapi=pmap.get(str(f.get('participant2Id'))),
                            line=line, home_odds=ho, away_odds=ao))
    return out

def fetch_fixtures(league):
    """Wrapper μιας λιγκας (συμβατοτητα)."""
    return fetch_all_fixtures([league]).get(league, [])

# ---------- LIVE picks (με αυστηρη δικλειδα ονοματων + ειδοποιησεις) ----------
def team_match(opapi_name, res):
    """(fot_name, ok, note) — ok=False σημαινει ΜΠΛΟΚ (δεν ταιριαξε με βεβαιοτητα)."""
    if opapi_name is None:
        return None, False, 'κενο ονομα OddsPapi'
    fot, ov, j, method = res.get(opapi_name, (None, 0, 0.0, 'NONE'))
    if fot is None or ov == 0:
        return None, False, f"δεν βρεθηκε αντιστοιχη ομαδα μοντελου ({method})"
    note = '' if (method == 'alias' or ov >= 2 or j >= 0.5) else 'low-confidence'
    return fot, True, note

def compute_picks(leagues, ratings_season):
    """Structured value picks (data, οχι print) — κοινο για CLI & dashboard.
    Επιστρεφει dict: picks[], blocked[], norating[], gross, scale, cap.
    Ιδια λογικη/staking με cmd_live (⅛ Kelly + cap 20%)."""
    import picks as engine
    M, id2name = engine.load_matches(list(LEAGUES), [ratings_season])
    name2id = {v: k for k, v in id2name.items()}
    all_picks, all_blocked, all_norating = [], [], []
    allfix = fetch_all_fixtures(leagues)
    for lg in leagues:
        state = engine.league_state(M, lg, ratings_season)
        fixtures = allfix.get(lg, [])
        opapi_names = sorted({n for f in fixtures for n in (f['home_opapi'], f['away_opapi']) if n})
        try:
            fot_names = fotmob_team_names(lg)
        except Exception:
            fot_names = []
        res = assign(opapi_names, fot_names)
        for f in fixtures:
            hfot, hok, hnote = team_match(f['home_opapi'], res)
            afot, aok, anote = team_match(f['away_opapi'], res)
            if not (hok and aok):
                bad = f['home_opapi'] if not hok else f['away_opapi']
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
    KELLY_FRAC = 0.125; CAP_EXPOSURE = 0.20
    for p in all_picks:
        p['stake'] = KELLY_FRAC * p['edge'] / (p['odds'] - 1)
    gross = sum(p['stake'] for p in all_picks)
    scale = CAP_EXPOSURE / gross if gross > CAP_EXPOSURE else 1.0
    for p in all_picks:
        p['stake_final'] = p['stake'] * scale
    return dict(picks=all_picks, blocked=all_blocked, norating=all_norating,
                gross=gross, scale=scale, cap=CAP_EXPOSURE)


def cmd_live(leagues, ratings_season, demo=False, notify_tg=False):
    import picks as engine
    M, id2name = engine.load_matches(list(LEAGUES), [ratings_season])
    name2id = {v: k for k, v in id2name.items()}

    print("=" * 78)
    print(f"  LIVE PICKS  (Betfair Exchange)   ratings απο σεζον {ratings_season}")
    if demo:
        print("  ⚠ ΕΠΙΔΕΙΞΗ: ratings περσινης σεζον ως προσωρινη προβολη — ΟΧΙ πραγματικα picks.")
        print("    Το κλειδωμενο μοντελο χρειαζεται >=6 ΦΕΤΙΝΑ ματς/ομαδα πριν βγαλει αληθινο pick.")
    print("=" * 78)

    all_picks, all_blocked, all_norating = [], [], []
    try:
        allfix = fetch_all_fixtures(leagues)   # 2 billable κλησεις για ΟΛΕΣ τις λιγκες (quota-friendly)
    except Exception as e:
        print(f"\nσφαλμα ανακτησης OddsPapi: {e}")
        return
    for lg in leagues:
        state = engine.league_state(M, lg, ratings_season)
        fixtures = allfix.get(lg, [])
        try:
            opapi_names = sorted({n for f in fixtures for n in (f['home_opapi'], f['away_opapi']) if n})
            fot_names = fotmob_team_names(lg)
        except Exception as e:
            print(f"\n[{lg}] σφαλμα ανακτησης ονοματων: {e}")
            continue
        res = assign(opapi_names, fot_names)
        print(f"\n[{lg}]  {len(fixtures)} επερχομενα ματς")
        for f in fixtures:
            hfot, hok, hnote = team_match(f['home_opapi'], res)
            afot, aok, anote = team_match(f['away_opapi'], res)
            # ΔΙΚΛΕΙΔΑ: αν ΚΑΠΟΙΑ ομαδα δεν ταιριαξε -> ΚΑΝΕΝΑ pick + ειδοποιηση
            if not (hok and aok):
                bad = f['home_opapi'] if not hok else f['away_opapi']
                reason = hnote if not hok else anote
                all_blocked.append((lg, f, bad, reason))
                continue
            H = name2id.get(hfot); A = name2id.get(afot)
            if H is None or A is None:
                all_norating.append((lg, f, hfot if H is None else afot, 'δεν υπαρχει στα ratings'))
                continue
            pred = engine.predict_ids(state, H, A)
            if pred is None:
                all_norating.append((lg, f, f"{hfot}/{afot}", f'<{engine.MIN_PRIOR} ματς ιστορικο'))
                continue
            xg_h, xg_a = pred
            for b in engine.evaluate_bet(xg_h, xg_a, f['line'], f['home_odds'], f['away_odds']):
                all_picks.append(dict(lg=lg, home=hfot, away=afot, when=f['startTime'],
                                      **b, hnote=hnote, anote=anote))

    # ---- staking: ⅛ Kelly + cap 20% ταυτοχρονης εκθεσης (τελικη πολιτικη, βλ memory) ----
    KELLY_FRAC = 0.125     # ⅛ Kelly: ιδιο ROI/μοναδα με ¼ αλλα μισο drawdown
    CAP_EXPOSURE = 0.20    # max 20% της καβας ανοιχτα ταυτοχρονα σε ενα αγωνιστικο παραθυρο
    for p in all_picks:
        p['stake'] = KELLY_FRAC * p['edge'] / (p['odds'] - 1)   # ποσοστο καβας
    gross = sum(p['stake'] for p in all_picks)
    scale = CAP_EXPOSURE / gross if gross > CAP_EXPOSURE else 1.0   # αναλογικη σμικρυνση αν >cap

    # ---- κειμενο picks (κοινο για οθονη & Telegram) ----
    pick_lines = []
    if all_picks:
        if scale < 1.0:
            pick_lines.append(f"⚙ staking ⅛Kelly — συνολικη εκθεση {gross*100:.0f}% > cap 20%, "
                              f"μειωση ολων ×{scale:.2f} (ανοιχτα ακριβως 20% καβας)")
        else:
            pick_lines.append(f"⚙ staking ⅛Kelly — συνολικη εκθεση {gross*100:.0f}% (κατω απο cap 20%, χωρις μειωση)")
    for p in all_picks:
        s = '1' if p['side'] == 1 else '2'
        lc = '  ⚠low-conf' if (p['hnote'] or p['anote']) else ''
        wt = '  ⚠ WATCH' if p['lg'] in WATCH else ''
        stake = p['stake'] * scale   # ⅛ Kelly μετα το cap
        pick_lines.append(f"[{p['lg']}] value: {p['home']}-{p['away']}, {s} +{p['hcap']:g}, "
                          f"projection {p['proj_odds']:.2f}, Betfair {p['odds']:.2f}, "
                          f"edge {p['edge']*100:.0f}%, ποντ. {stake*100:.1f}% καβας   [{p['when']}]{wt}{lc}")
    block_lines = []
    for lg, f, bad, reason in all_blocked:
        block_lines.append(f"[{lg}] {f['home_opapi']} vs {f['away_opapi']}  @ {f['startTime']}\n"
                           f"    -> ΜΠΛΟΚ: '{bad}' {reason}")

    # ---- OUTPUT οθονη ----
    print("\n" + "=" * 78 + "\n  VALUE PICKS\n" + "=" * 78)
    print("\n".join("  " + l for l in pick_lines) if pick_lines
          else "  (κανενα pick — αναμενομενο προεποχικα/χωρις αρκετο ιστορικο)")
    if block_lines:
        print("\n" + "=" * 78 + "\n  ⚠ ΜΠΛΟΚΑΡΙΣΜΕΝΑ (ασφαλεια ονοματος — ΔΕΝ βγηκε pick, ΔΙΟΡΘΩΣΕ ALIAS):\n" + "=" * 78)
        print("\n".join("  " + l for l in block_lines))
    if all_norating:
        print("\n  (χωρις προβλεψη ακομα — μη επαρκες ιστορικο ή νεοφωτιστη:)")
        for lg, f, who, reason in all_norating:
            print(f"    [{lg}] {f['home_opapi']} vs {f['away_opapi']}  ({who}: {reason})")

    # ---- Telegram ----
    if notify_tg:
        import notify
        tag = "🧪 ΕΠΙΔΕΙΞΗ (περσινα ratings)\n\n" if demo else ""
        if pick_lines:
            notify.send(f"🎯 VALUE PICKS ({len(pick_lines)})\n{tag}" + "\n".join(pick_lines))
        else:
            notify.send(f"ℹ️ Καμια value pick σημερα.{(' ' + tag) if demo else ''}", silent=True)
        if block_lines:
            notify.send("⚠️ ΜΠΛΟΚΑΡΙΣΜΕΝΑ ΟΝΟΜΑΤΑ (δεν βγηκε pick — χρειαζεται alias):\n\n"
                        + "\n".join(block_lines))


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'check-names':
        arg = sys.argv[2] if len(sys.argv) > 2 else 'EPL'
        leagues = list(LEAGUES) if arg == 'all' else [arg]
        for lg in leagues:
            check_league(lg)
    elif cmd == 'picks':
        # python live_odds.py picks <league|all> [ratings_season] [--telegram]
        pos = [a for a in sys.argv[2:] if not a.startswith('--')]
        flags = [a for a in sys.argv[2:] if a.startswith('--')]
        arg = pos[0] if pos else 'EPL'
        leagues = list(LEAGUES) if arg == 'all' else [arg]
        rs = pos[1] if len(pos) > 1 else '2627'
        cmd_live(leagues, rs, demo=(rs != '2627'), notify_tg=('--telegram' in flags))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
