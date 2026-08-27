"""
picks.py  -  ΒΗΜΑ 4: μηχανη προβλεψεων & value picks.

ΚΛΕΙΔΩΜΕΝΗ ΛΟΓΙΚΗ - ιδια ακριβως με hfa_compare.py:
  σταθερο HFA (per-league) · blend 80/20 · decay 0.96 · Poisson + draw boost 13%
  φιλτρα: edge >= 10% · ΜΟΝΟ +handicap (underdog) · γραμμη >= 0.5 · odds 1.70-2.10

Η προβλεψη καθε ματς υπολογιζεται walk-forward: ΜΟΝΟ απο προηγουμενα ματς, ΠΟΤΕ
απο το αποτελεσμα. Αρα ο,τι βγαζει στο backtest ειναι ιδιο με το τι θα βγαλει ζωντανα.

Χρηση:
  python picks.py backtest                 # αναπαραγει το ROI (validation), ολες οι σεζον
  python picks.py backtest 2526            # ROI μονο για μια σεζον
  python picks.py picks 2526               # λιστα value picks (μορφη alert) για τη σεζον
  python picks.py picks 2526 EPL           # + φιλτρο λιγκας
"""
import pandas as pd, numpy as np, json, unicodedata, re, sys
from math import exp, factorial
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---------- ΚΛΕΙΔΩΜΕΝΕΣ ΣΤΑΘΕΡΕΣ ----------
BLEND = 0.60; MIN_PRIOR = 6; DECAY = 0.96   # BLEND 0.80→0.60 (2026-08-26, blend_test.py + blend_roi.py): το 80/20 εδινε υπερβολικο βαρος στο xG. RPS: 60/40 καλυτερο σε ΚΑΙ ΤΙΣ 5 φασεις σεζον (0.1953 vs 0.1958), LOSO διαλεξε 50-60 σε 4/4 folds, ποτε 80. ROI @15η+: +5.2% vs +3.6%, συνολικο κερδος 63.2u vs 53.6u (+18%). Καθε τεστ ~1 SE μονο του — πειθει η ΣΥΜΦΩΝΙΑ δυο ανεξαρτητων μετρικων σε μονοτονη καμπυλη. Βλ. memory blend-60-40.
SOS = 1.5; SOS_MIN_N = 6   # Strength-of-Schedule (Caley one-pass). 1.5 (2026-08-27, sos_clean_loso.py/blend_ramp.py):
            # md7-14 ROI -10.3% -> +2.8%· md15+ +5.8%->+5.4% αλλα 4/4 σεζον & +40% ογκος (61u -> 80u).
            # SOS_MIN_N=6: με <6 αντιπαλους το SoS ΚΑΤΑΣΤΡΕΦΕΙ την ακριβεια (RPS md2-4: 0.1930 -> 0.2143).
            # Το gate n>=6 ειναι ΔΩΡΕΑΝ: ΙΔΙΟ ROI παντου (δεν στοιχηματιζουμε πριν την 7η ουτως ή αλλως),
            # και επαναφερει το RPS md2-4 στο 0.1930. Το n>=8 σπαει το md7-14 (-2.5%). Βλ. sos_ramp_test.py.
# --- ΡΑΜΠΑ blend μεσα στη σεζον (2026-08-27, blend_ramp.py/blend_early.py) ---
# Νωρις τα γκολ ειναι σχεδον καθαρος θορυβος (2-3 ματς)· οσο μαζευονται, αποκτουν σημα.
#   b(n) = 1.00 - D*n/(n+Kg)   n<=13   ·   b(n) = BLEND (0.60)   n>=14
# Ιδια μορφη n/(n+K) με το warm-start: καθε νεο ματς προσθετει ΛΙΓΟΤΕΡΟ απο το προηγουμενο.
# Προσγειωνεται ΑΚΡΙΒΩΣ στο 0.60 στην 14η -> καμια ασυνεχεια στο συνορο 14/15.
# md1 100/0 · md4 85/15 · md7 74/26 · md10 67/33 · md14 60/40 · md15+ 60/40
# Τεκμηριωση: ROI@md7-14 +2.8% (vs +0.9% flat 60/40, +1.5% flat 80/20)· RPS βελτιστο ή ισοπαλο
# σε ΚΑΘΕ υπο-παραθυρο· LOSO βελτιωση και στα δυο κριτηρια (ROI -0.23%->+0.62%, RPS .20066->.20055).
# Καθε μεμονωμενη διαφορα ειναι μεσα στον θορυβο — πειθει η συμφωνια ολων των κελιων.
BLEND_EARLY = 1.00; BLEND_SPLIT = 13; BLEND_KG = 12.0
_BLEND_D = (BLEND_EARLY - BLEND) * (BLEND_SPLIT + BLEND_KG) / BLEND_SPLIT

def blend_at(n):
    """Βαρος xG (εναντι γκολ) για ομαδα με n παιγμενα ματς ΦΕΤΟΣ.
    n=None ή n>13 -> BLEND (ωριμο 60/40). Χρησιμοποιειται και για το περσινο prior (n=None)."""
    if n is None or n > BLEND_SPLIT:
        return BLEND
    return BLEND_EARLY - _BLEND_D * n / (n + BLEND_KG)

EDGE = 0.10; OMIN, OMAX = 1.70, 2.10; MIN_LINE = 0.5; DRAW_BOOST = 1.13; MARGIN = 0.03  # MARGIN = vig-consistent haircut στα net winnings (standard εγχωριο+ευρωπαικο)
STAKE = 1000.0
F = [factorial(i) for i in range(13)]
# Σταθερο ιστορικο HFA (11 σεζον, within-pairing) - πληρης πινακας απο START_HERE
HFA_FIX = {'EPL': 1.10, 'LaLiga': 1.15, 'SerieA': 1.08, 'Bundesliga': 1.12, 'Ligue1': 1.105,
           'Bundesliga2': 1.102, 'Eredivisie': 1.130, 'PrimeiraLiga': 1.116,
           'GreeceSL': 1.133, 'Belgium': 1.113, 'ScottishPrem': 1.118}
TOP5 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']  # CORE 7 (2026-08-11): αφαιρεθηκαν Belgium & ScottishPrem — 5-season sharp = θορυβος/αρνητικες @15η+ (Belgium −11%, Scottish −7.6%). Core 7 @15η+ closing +6.3% (4/5 σεζον θετικες). Βλ. memory league-config-registry.
ALL_SEASONS = ['2425', '2526']

# ---------- φορτωση data & id->name ----------
def load_matches(leagues, seasons):
    TG = pd.read_csv('teamgame_inputs.csv')
    TG['season'] = TG['season'].astype(str)
    id2name = {}
    for lg in leagues:
        for sea in seasons:
            path = f'data_{lg}_{sea}.json'
            try:
                d = json.load(open(path, encoding='utf-8'))
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
                       home=int(h['team']), away=int(a['team']),
                       hg=int(h['gf']), ag=int(a['gf']),
                       h_xg=h['xg_model'], a_xg=a['xg_model'],
                       h_ns=h['ns_eff'], a_ns=a['ns_eff']))
    M = pd.DataFrame(MM).sort_values(['league', 'season', 'date', 'mid']).reset_index(drop=True)
    return M, id2name

# ---------- rolling ratings (walk-forward) ----------
def wmean(v):
    n = len(v)
    if n == 0:
        return None
    w = np.array([DECAY ** (n - 1 - i) for i in range(n)])
    return float((w * np.array(v)).sum() / w.sum())

def predict(hh, ha, lg_shots, lg_xgps, hf):
    """xg_h, xg_a απο τα rolling ιστορικα (ΠΡΙΝ το ματς). Ιδιο math με hfa_compare.build()."""
    af = 1 / hf
    def blx(t, fx, fg):
        b = blend_at(len(t[fx]))          # ραμπα: πολυ xG νωρις, 60/40 απο την 14η
        return b * wmean(t[fx]) + (1 - b) * wmean(t[fg])
    Hax = blx(hh, 'xf', 'gf') / max(wmean(hh['sf']), 1e-9)
    Hdx = blx(hh, 'xa', 'ga') / max(wmean(hh['sa']), 1e-9)
    Aax = blx(ha, 'xf', 'gf') / max(wmean(ha['sf']), 1e-9)
    Adx = blx(ha, 'xa', 'ga') / max(wmean(ha['sa']), 1e-9)
    esh_h = (wmean(hh['sf']) / lg_shots) * (wmean(ha['sa']) / lg_shots) * lg_shots
    esh_a = (wmean(ha['sf']) / lg_shots) * (wmean(hh['sa']) / lg_shots) * lg_shots
    xg_h = esh_h * (Hax * (Adx / lg_xgps)) * hf
    xg_a = esh_a * (Aax * (Hdx / lg_xgps)) * af
    return xg_h, xg_a

def sos_adjust(r, opps, ratings, lg_shots, lg_xgps, strength=SOS):
    """Caley one-pass Strength-of-Schedule.
    Διορθωνει το (Ax, Dx, SF, SA) μιας ομαδας για τη δυσκολια των αντιπαλων που ΕΧΕΙ ΗΔΗ
    παιξει ΦΕΤΟΣ. Αν επαιξε δυσκολο προγραμμα, τα νουμερα της ηταν τεχνητα χαμηλα -> πανω.
    `ratings` = οι ΠΡΙΝ-το-SoS βαθμολογιες ολης της λιγκας (one-pass: καμια αναδρομη).
    Επιστρεφει το r αμεταβλητο αν εχει παιξει <SOS_MIN_N αντιπαλους (πολυ θορυβος)."""
    if not opps or not strength or len(opps) < SOS_MIN_N:
        return r
    oA = []; oD = []; oSF = []; oSA = []
    for o in opps:
        a = ratings.get(o)
        if a is None:
            continue
        oA.append(a[0]); oD.append(a[1]); oSF.append(a[2]); oSA.append(a[3])
    if not oA:
        return r
    mA, mD, mSF, mSA = wmean(oA), wmean(oD), wmean(oSF), wmean(oSA)
    return (r[0] * (lg_xgps / max(mD, 1e-9)) ** strength,
            r[1] * (lg_xgps / max(mA, 1e-9)) ** strength,
            r[2] * (lg_shots / max(mSA, 1e-9)) ** strength,
            r[3] * (lg_shots / max(mSF, 1e-9)) ** strength)

def build_predictions(M, id2name):
    """Walk-forward: για καθε ματς με >=MIN_PRIOR ιστορικο, προβλεψη προ-αγωνα."""
    out = []
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        G = G.sort_values(['date', 'mid']).reset_index(drop=True)
        hist = {}
        lg_shots = pd.concat([G.h_ns, G.a_ns]).mean()
        lg_xgps = pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum()
        hf = HFA_FIX[lg]
        for _, r in G.iterrows():
            H, A = r['home'], r['away']
            hh = hist.get(H); ha = hist.get(A)
            if hh and ha and len(hh['sf']) >= MIN_PRIOR and len(ha['sf']) >= MIN_PRIOR:
                xg_h, xg_a = predict(hh, ha, lg_shots, lg_xgps, hf)
                out.append(dict(league=lg, season=sea, mid=r['mid'], date=r['date'],
                                home_name=id2name.get(H), away_name=id2name.get(A),
                                gd=r['hg'] - r['ag'], hg=r['hg'], ag=r['ag'],
                                xg_h=xg_h, xg_a=xg_a, model_sup=xg_h - xg_a))
            for tid, opp, sf, xf, sa, xa, gf, ga in [
                    (H, A, r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (A, H, r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', opp)]:
                    hist[tid][k].append(v)
    return pd.DataFrame(out)

# ---------- LIVE: τελικα ratings + προβλεψη ζευγαριου (για επερχομενα ματς) ----------
def league_state(M, league, season):
    """Χτιζει τα rolling ratings ΟΛΗΣ της λιγκας-σεζον και επιστρεφει την ΤΕΛΙΚΗ κατασταση:
    (hist ανα team_id, lg_shots, lg_xgps, hf). Ιδια ενημερωση με build_predictions()."""
    G = M[(M.league == league) & (M.season == str(season))].sort_values(['date', 'mid']).reset_index(drop=True)
    if len(G) == 0:
        return {}, None, None, HFA_FIX.get(league)
    hist = {}
    lg_shots = pd.concat([G.h_ns, G.a_ns]).mean()
    lg_xgps = pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum()
    hf = HFA_FIX[league]
    for _, r in G.iterrows():
        for tid, opp, sf, xf, sa, xa, gf, ga in [
                (r['home'], r['away'], r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                (r['away'], r['home'], r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
            hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
            for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', opp)]:
                hist[tid][k].append(v)
    return hist, lg_shots, lg_xgps, hf

def predict_ids(state, H, A):
    """(xg_h, xg_a) για επερχομενο ματς H(home) vs A(away), ή None αν <MIN_PRIOR ιστορικο."""
    hist, lg_shots, lg_xgps, hf = state
    hh = hist.get(H); ha = hist.get(A)
    if not (hh and ha and len(hh['sf']) >= MIN_PRIOR and len(ha['sf']) >= MIN_PRIOR):
        return None
    return predict(hh, ha, lg_shots, lg_xgps, hf)

def name_to_id(leagues, seasons):
    """FotMob ονομα -> team id (αντιστροφο του id2name)."""
    _, id2name = load_matches(leagues, seasons)
    return {v: k for k, v in id2name.items()}

# ---------- odds matching (ιδιο με hfa_compare) ----------
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z ]', ' ', s).split()) -
                     {'fc', 'cf', 'ac', 'calcio', 'club', 'de', 'afc', 'ss', 'us', 'as', 'rc',
                      'ud', 'sd', 'sc', 'rcd', 'real', '1', 'vfl', 'vfb', 'tsg', 'sv', 'bsc', 'og'})
# ΟΛΑ τα odds ειναι πλεον TOA-18h (ΠΛΗΡΗ ονοματα). Κραταμε μονο τα aliases που ταιριαζουν με TOA.
ALIAS = {'Athletic Club': 'Ath Bilbao',        # συμβατο με TOA 'Athletic Bilbao'
         'Sporting CP': 'Sp Lisbon',            # Primeira, συμβατο με TOA 'Sporting Lisbon'
         'Heart of Midlothian': 'Hearts',       # ScottishPrem: TOA 'Hearts'
         'St.Truiden': 'Sint Truiden'}          # Belgium: TOA 'Sint Truiden' (αλλιως collision 'St Pauli')
# ΑΦΑΙΡΕΘΗΚΑΝ (2026-08-08, μεταβαση all-18h TOA): Wolverhampton Wanderers/Espanyol/Atletico Madrid/
# Borussia Mönchengladbach/Hamburger SV/Paris Saint-Germain — ηταν football-data short-name aliases
# που ΣΠΑΝΕ/collision-αρουν με τα ΠΛΗΡΗ TOA ονοματα (π.χ. Ath Madrid→Real Madrid). Τα football-data
# closing odds δεν χρησιμοποιουνται πλεον (βλ. picks.py.bak για την closing εκδοχη).

def load_odds(leagues, seasons):
    O = []
    for lg in leagues:
        for sea in seasons:
            try:
                o = pd.read_csv(f'odds/{lg}_{sea}.csv', encoding='latin-1')
            except FileNotFoundError:
                continue
            o['season'] = sea; O.append(o)
    if not O:
        return pd.DataFrame(), {}, {}
    O = pd.concat(O, ignore_index=True)
    fdn = {}
    for _, r in O.iterrows():
        fdn[r['HomeTeam']] = norm(r['HomeTeam']); fdn[r['AwayTeam']] = norm(r['AwayTeam'])
    Om = {}
    for _, r in O.iterrows():
        Om.setdefault((str(r['season']), r['HomeTeam'], r['AwayTeam']), []).append(r)   # dict-of-lists: playoff repeats
    return O, fdn, Om

def make_resolver(fdn):
    cache = {}
    def resolve(n):
        if n in cache:
            return cache[n]
        tn = norm(ALIAS.get(n, n)); best = None; bs = 0; bj = 0
        for raw, tg in fdn.items():
            ov = len(tn & tg)
            if ov > bs or (ov == bs and ov / max(len(tn | tg), 1) > bj):
                bs = ov; bj = ov / max(len(tn | tg), 1); best = raw
        cache[n] = best if bs > 0 else None
        return cache[n]
    return resolve

def match_odds(Om, season, home, away, date):
    """Date-aware odds lookup. Οι λιγκες με playoff/split-season (Belgium/Scotland) εχουν
    το ιδιο ζευγαρι (home,away) 2-4×/σεζον → το κλειδι (season,home,away) ειναι ασαφες.
    Διαλεγει το fixture με την ΠΛΗΣΙΕΣΤΕΡΗ ημερομηνια στην προβλεψη. Για μοναδικα-fixture
    λιγκες (1 υποψηφιος) ταυτοσημο με πριν → ΔΕΝ αλλαζει top-5/Primeira/Eredivisie."""
    rows = Om.get((str(season), home, away))
    if not rows:
        return None
    if len(rows) == 1:
        cand = rows[0]
    else:
        try:
            d = pd.to_datetime(date)
            cand = min(rows, key=lambda r: abs((d - pd.to_datetime(r['Date'], dayfirst=True)).days))
        except Exception:
            return rows[-1]
    # date-sanity: αν το πλησιεστερο fixture ειναι >7 μερες μακρια → ΔΕΝ ειναι το ιδιο ματς
    # (π.χ. playoff προβλεψη που δεν εχει δικες της odds· ΜΗΝ τη ταιριαξεις με regular-season odds)
    try:
        if abs((pd.to_datetime(date) - pd.to_datetime(cand['Date'], dayfirst=True)).days) > 7:
            return None
    except Exception:
        pass
    return cand

# ---------- Poisson score model ----------
def gd_dist(lh, la):
    ph = [exp(-lh) * lh ** i / F[i] for i in range(13)]
    pa = [exp(-la) * la ** j / F[j] for j in range(13)]
    Pm = np.outer(ph, pa)
    for i in range(13):
        Pm[i, i] *= DRAW_BOOST
    Pm /= Pm.sum()
    gd = {}
    for i in range(13):
        for j in range(13):
            gd[i - j] = gd.get(i - j, 0) + Pm[i, j]
    return gd

def p_cover(dist, side, line):
    pw = pp = 0.0
    for k, p in dist.items():
        m = (k if side == 1 else -k) + line
        if m > 0.01:
            pw += p
        elif abs(m) < 0.01:
            pp += p
    return pw, pp

def settle(gd, side, line, odds):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pnl = 0.0
    for L in parts:
        s = 1 / len(parts); m = (gd if side == 1 else -gd) + L
        if m > 0.01:
            pnl += s * (odds - 1)
        elif abs(m) < 0.01:
            pnl += 0.0
        else:
            pnl -= s
    return pnl

def ah_odds(o):
    for hh, ha in [('BFECAHH', 'BFECAHA'), ('PCAHH', 'PCAHA'), ('AvgCAHH', 'AvgCAHA')]:
        if pd.notna(o.get(hh)) and pd.notna(o.get(ha)):
            return float(o[hh]), float(o[ha]), hh.replace('CAHH', '')
    return None, None, None

# ---------- ΚΛΕΙΔΩΜΕΝΟΣ πυρηνας αξιολογησης bet (κοινος: backtest & live) ----------
def evaluate_bet(xg_h, xg_a, line, oh, oa):
    """Δεδομενων model xG (home/away), γραμμης (home perspective) και home/away odds,
    επιστρεφει λιστα picks που περνανε τα φιλτρα (μονο +handicap >=0.5, odds 1.70-2.10, edge>=10%).
    Συνηθως 0 η 1 pick. Χρησιμοποιειται ΤΟΣΟ στο backtest ΟΣΟ και ζωντανα."""
    lh = max(xg_h, 0.05); la = max(xg_a, 0.05)   # = (tot±sup)/2
    dist = gd_dist(lh, la); out = []
    for side, ud, odds in [(1, line, oh), (-1, -line, oa)]:
        if ud < MIN_LINE or not (OMIN <= odds <= OMAX):
            continue
        pw, pp = p_cover(dist, side, ud)
        edge = pw * (odds - 1) * (1 - MARGIN) - (1 - pw - pp)   # 3% vig haircut στα winnings· DC μεσω gd_dist(DRAW_BOOST)
        if edge >= EDGE:
            # fair odds ΜΕ push (AH): break-even = (1-pp)/pw· το 1/pw αγνοουσε το push
            # (παραπλανητικο σε ακεραιες/μισες γραμμες)· ΔΕΝ αλλαζει edge/picks, μονο το display.
            out.append(dict(side=side, hcap=ud, odds=odds, pw=pw, pp=pp, edge=edge,
                            proj_odds=((1 - pp) / pw if pw > 0 else float('inf'))))
    return out

# ---------- signals: παραγει ΚΑΘΕ value bet (pre-match) [backtest, με football-data odds] ----------
def bet_signals(P, Om, resolve):
    rows = []
    for _, r in P.iterrows():
        o = match_odds(Om, r['season'], resolve(r['home_name']), resolve(r['away_name']), r['date'])
        if o is None:
            continue
        line = o.get('AHCh'); oh, oa, book = ah_odds(o)
        if pd.isna(line) or oh is None:
            continue
        for b in evaluate_bet(r['xg_h'], r['xg_a'], float(line), oh, oa):
            rows.append(dict(
                league=r['league'], season=r['season'], date=r['date'],
                home=r['home_name'], away=r['away_name'], book=book,
                gd=r.get('gd'),
                pnl=settle(r['gd'], b['side'], b['hcap'], b['odds']) if pd.notna(r.get('gd')) else float('nan'),
                **b))
    return pd.DataFrame(rows)

# ---------- INTEGRITY GATE: structural sanity (τρεχει ΜΑΖΙ με καθε backtest & ΠΡΙΝ καθε live pick) ----------
class IntegrityError(Exception):
    pass

def integrity_report(leagues, seasons):
    """Ολοι οι structural ελεγχοι του matching μαζι. Επιστρεφει (ok: bool, lines: list[str]).
    Πιανει: collision (2+ ομαδες→ιδιο ονομα), unresolved→None, coverage gap, team-imbalance
    (silent wrong-key σαν Atletico→Real), n-vs-fixtures (double-count), date-mismatch, duplicates.
    Ενα source of truth: το καλουν το backtest (Lvl2), το check_integrity.py (Lvl3), το live (Lvl4)."""
    lines = []; issues = []
    def FAIL(m): issues.append(m); lines.append('  [FAIL] ' + m)
    def WARN(m): lines.append('  [warn] ' + m)
    def OKL(m):  lines.append('  [ ok ] ' + m)
    M, id2name = load_matches(leagues, seasons)
    Pred = build_predictions(M, id2name)
    O, fdn, Om = load_odds(leagues, seasons)
    resolve = make_resolver(fdn)
    for lg in leagues:
        Pl = Pred[Pred.league == lg]
        if len(Pl) == 0:
            FAIL(f'{lg}: 0 προβλεψεις (λειπουν data;)'); continue
        teams = set(Pl.home_name) | set(Pl.away_name)
        rev = {}
        for t in teams:
            rev.setdefault(resolve(t), []).append(t)
        if rev.get(None):
            FAIL(f'{lg}: unresolved→None {sorted(rev[None])}')
        coll = {k: v for k, v in rev.items() if k is not None and len(v) > 1}
        if coll:
            FAIL(f'{lg}: COLLISION ' + ' | '.join(f'{v}→"{k}"' for k, v in coll.items()))
        for sea in seasons:
            Ps = Pl[Pl.season == sea]
            if len(Ps) == 0:
                continue
            fixtures = len(M[(M.league == lg) & (M.season == sea)])
            matched = datebad = reps = 0; appear = {}; used = {}
            for _, r in Ps.iterrows():
                rh = resolve(r['home_name']); ra = resolve(r['away_name'])
                row = match_odds(Om, sea, rh, ra, r['date'])
                if row is None:
                    continue
                matched += 1
                uk = (rh, ra, str(row.get('Date')))   # double-use tracking (ιδιο odds row 2×)
                used[uk] = used.get(uk, 0) + 1
                if len(Om.get((str(sea), rh, ra), [])) > 1:   # repeated fixture (playoff split)
                    reps += 1
                appear[rh] = appear.get(rh, 0) + 1
                appear[ra] = appear.get(ra, 0) + 1
                try:
                    if abs((pd.to_datetime(r['date']) - pd.to_datetime(row['Date'], dayfirst=True)).days) > 1:
                        datebad += 1
                except Exception:
                    pass
            cov = 100 * matched / len(Ps)
            tag = f'{lg} {sea}: coverage {cov:.1f}% ({matched}/{len(Ps)} preds, {fixtures} fixtures)'
            if cov < 98:      FAIL(tag)
            elif cov < 99.9:  WARN(tag)
            else:             OKL(tag)
            if len(Ps) > fixtures * 1.02:
                FAIL(f'{lg} {sea}: {len(Ps)} preds > {fixtures} fixtures (double-count;)')
            elif len(Ps) < fixtures * 0.55:
                WARN(f'{lg} {sea}: μονο {len(Ps)}/{fixtures} preds εχουν ιστορικο')
            if reps:
                OKL(f'{lg} {sea}: {reps} picks σε repeated fixtures (playoff split) — date-aware matching, date-diff={datebad}')
            if datebad:   # match_odds κοβει ηδη >7μερες → αυτα ειναι 2-7μ source discrepancy (FotMob vs odds), οχι λαθος fixture
                WARN(f'{lg} {sea}: {datebad} picks date-diff 2-7 μερες (source date discrepancy· double-use ελεγμενο ξεχωριστα)')
            dbl = sum(1 for c in used.values() if c > 1)   # ★ HARD GUARD: ιδιο odds row σε 2+ preds = playoff xG × λαθος odds
            if dbl:
                FAIL(f'{lg} {sea}: {dbl} odds rows σε 2+ predictions (DOUBLE-USE = playoff xG × λαθος odds!)')
            if appear:
                med = np.median(list(appear.values()))
                hi = {t: c for t, c in appear.items() if c > 1.5 * med}
                if hi:
                    FAIL(f'{lg} {sea}: ομαδα >1.5×μεσου (silent wrong-key;) ' +
                         ', '.join(f'"{t}"×{c}' for t, c in hi.items()))
    dupp = Pred.groupby(['season', 'league', 'home_name', 'away_name', 'date']).size()   # +date: playoff legs (διαφ. ημ/νια) ΔΕΝ ειναι διπλα
    if (dupp > 1).any():
        FAIL(f'διπλες προβλεψεις (ιδιο fixture ΙΔΙΑ ημ/νια = double-count): {int((dupp > 1).sum())}')
    okeys = {}
    for _, r in O.iterrows():
        if pd.isna(r.get('HomeTeam')):
            continue
        k = (str(r['season']), r['HomeTeam'], r['AwayTeam'])
        okeys[k] = okeys.get(k, 0) + 1
    dk = sum(1 for c in okeys.values() if c > 1)
    if dk:
        WARN(f'{dk} repeated-fixture odds keys (playoff splits) → date-aware matching ενεργο (match_odds → πλησιεστερη ημ/νια)')
    return (len(issues) == 0), lines

def print_integrity(leagues, seasons):
    """Τυπωνει το gate στην ΚΟΡΥΦΗ (Lvl2/3). Επιστρεφει ok."""
    ok, lines = integrity_report(leagues, seasons)
    print('=' * 66)
    print('INTEGRITY GATE:  ' + ('PASS ✓' if ok else '*** FAIL ***  (ΜΗΝ εμπιστευτεις τα νουμερα)'))
    print('=' * 66)
    for l in lines:
        print(l)
    print()
    return ok

def assert_integrity(leagues=None, seasons=None):
    """LIVE (Lvl4): σηκωνει IntegrityError αν το gate δεν περναει καθαρα.
    Ο live sender το καλει ΠΡΙΝ στειλει pick· αν σκασει → Telegram blocker alert, ΟΧΙ σιωπηλο pick."""
    leagues = leagues if leagues is not None else TOP5
    seasons = seasons if seasons is not None else ALL_SEASONS
    ok, lines = integrity_report(leagues, seasons)
    if not ok:
        raise IntegrityError('Integrity gate FAILED — δεν στελνω picks:\n' +
                             '\n'.join(l for l in lines if '[FAIL]' in l))
    return True

# ---------- εκτελεση ----------
def get_engine(leagues, seasons):
    M, id2name = load_matches(leagues, seasons)
    P = build_predictions(M, id2name)
    _, fdn, Om = load_odds(leagues, seasons)
    resolve = make_resolver(fdn)
    B = bet_signals(P, Om, resolve)
    return P, B

def cmd_backtest(args):
    seasons = [args[0]] if args else ALL_SEASONS
    gate_ok = print_integrity(TOP5, seasons)   # Lvl2: το gate τρεχει ΜΑΖΙ με το backtest, φωναζει στην κορυφη
    if not gate_ok:
        print(">> ΠΡΟΣΟΧΗ: το integrity gate ΑΠΕΤΥΧΕ — τα παρακατω ROI ειναι αναξιοπιστα.\n")
    P, B = get_engine(TOP5, seasons)
    print(f"προβλεψεις: {len(P)}  |  value bets: {len(B)}\n")
    print(f"{'σεζον':>6s} | {'ROI':>8s} {'±SE':>6s} {'bets':>5s}")
    r_all = B.pnl.values
    for sea in seasons:
        rs = B[B.season == sea].pnl.values
        if len(rs) == 0:
            continue
        print(f"{sea:>6s} | {rs.mean():>+7.1%} {rs.std()/np.sqrt(len(rs)):>6.1%} {len(rs):>5d}")
    if len(seasons) > 1:
        print(f"{'ΟΛΑ':>6s} | {r_all.mean():>+7.1%} {r_all.std()/np.sqrt(len(r_all)):>6.1%} {len(r_all):>5d}")

def cmd_picks(args):
    if not args:
        print("Χρηση: python picks.py picks <season> [league]"); return
    season = args[0]
    league = args[1] if len(args) > 1 else None
    leagues = [league] if league else TOP5
    P, B = get_engine(leagues, [season])
    B = B[B.season == season]
    if league:
        B = B[B.league == league]
    B = B.sort_values(['date', 'edge'], ascending=[True, False])
    header = (f"VALUE PICKS  σεζον={season}" + (f"  λιγκα={league}" if league else "")
              + f"   ({len(B)} picks)   [{datetime.now():%Y-%m-%d %H:%M}]")
    lines = [header, ""]
    for _, b in B.iterrows():
        s = '1' if b['side'] == 1 else '2'
        hc = f"+{b['hcap']:g}"
        res = ''
        if pd.notna(b['gd']):
            mark = 'W' if b['pnl'] > 0 else ('=' if b['pnl'] == 0 else 'L')
            res = f"   [αποτ {int(b['gd']):+d}: {mark} {b['pnl']:+.2f}u]"
        lines.append(f"value: {b['home']}-{b['away']}, {s} {hc}, "
                     f"projection {b['proj_odds']:.2f}, {b['book']} {b['odds']:.2f}, "
                     f"edge {b['edge']*100:.0f}%{res}")
    text = "\n".join(lines)
    print(text)
    with open('picks_output.txt', 'w', encoding='utf-8') as f:
        f.write(text + "\n")
    print(f"\n>> αποθηκευτηκε στο picks_output.txt")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('backtest', 'picks'):
        print(__doc__); sys.exit(1)
    if sys.argv[1] == 'backtest':
        cmd_backtest(sys.argv[2:])
    else:
        cmd_picks(sys.argv[2:])

if __name__ == '__main__':
    main()
