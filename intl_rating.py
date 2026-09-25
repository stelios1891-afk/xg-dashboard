"""
intl_rating.py — Elo / xElo ΕΘΝΙΚΩΝ (19/9/2026, βημα 1-2 του πλανου· ιδεες PADDLIN' του Caley ως ΠΑΡΑΛΛΑΓΕΣ που κρινονται
walk-forward στα δικα μας δεδομενα, οχι ως αντιγραφη).

Βαση: intl_matches.csv (5.276 ματς 2018-2026, 1.511 με xG). Ολα τα ratings ενημερωνονται ΣΕΙΡΙΑΚΑ (walk-forward) =>
καθε προβλεψη ειναι out-of-sample ως προς το ματς. Αφετηρια: eloratings.net τελος 2019 (code -> ονομα -> FotMob id).

ΠΑΡΑΛΛΑΓΕΣ (προ-δηλωμενες, ΧΩΡΙΣ tuning σε ROI):
  E0  Elo αποτελεσματων: K ανα τυπο (φιλικο 20 / NL 35 / προκριματικα 40 / τουρνουα 50), πολλαπλασιαστης διαφορας
      (1, 1.5, 1.75, +0.125/γκολ — eloratings), εδρα H=80 (0 σε ουδετερο).
  X1  xElo raw: οπου υπαρχει xG, «αποτελεσμα» = αναμενομενο σκορ απο Poisson(np-xG)· αλλιως το πραγματικο.
  X2  xElo με συμπιεση ευκαιριων (cap 0.40, +25% πανω απο cap, rescale στο μεσο raw).
  X3  xElo με συμπιεση + game state (φαβορι>=100 Elo που χανει: xG x0.55· καθε προπορευομενος x1.30·
      αουτσαιντερ που προηγειται x1.45· αουτσαιντερ που χανει x0.90· ισοπαλια x1)· rescale.
  B   blend 50/50 E0+X3 (ratings).
  ΕΞΩΤΕΡΙΚΟ benchmark: eloratings.net τελος προηγουμενου ετους (στατικο).
Μετρο: RPS (και log-loss) 1Χ2 σε ΑΓΩΝΙΣΤΙΚΑ ματς (nl/qual/tourn), ανα σεζον 2021..2526· η αντιστοιχιση
diff -> 1Χ2 ειναι ordered logit που fit-αρεται ΜΟΝΟ σε αλλες σεζον (LOSO στη χαρτογραφηση).
ΚΡΙΤΗΡΙΟ «στρωμα μενει»: βελτιωνει τον RPS του E0 σε >= 4/6 σεζον και συνολικα.
Εξοδος: intl_rating_out.txt, intl_ratings_latest.csv (τρεχοντα ratings ολων των παραλλαγων).
"""
import json, math, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import picks

M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
import intl_dedupe
M = intl_dedupe.dedupe(M, where='intl_rating').sort_values('date').reset_index(drop=True)   # 25/9: κλειδι ασφαλειας — διπλα ματς δεν μετρανε
# 25/9/2026 (Στελιος): ο δικος μας υπολογισμος ξεκινα ΑΚΡΙΒΩΣ μετα την αφετηρια eloratings (τελος SEED_YEAR) — χωρις επικαλυψη
SEED_YEAR = '2019'; WALK_START = f'{int(SEED_YEAR) + 1}-01-01'     # ηταν '2019-07-01' → Ιουλ-Δεκ 2019 μετρουσαν διπλα
M = M[M['date'] >= WALK_START].reset_index(drop=True)
K_TYPE = {'friendly': 20, 'nl': 35, 'qual': 40, 'tourn': 50}
HFA = 80
FAV_D = 100
GS = dict(fav_trail=0.55, lead=1.30, dog_lead=1.45, dog_trail=0.90)
CAP = 0.40

# ---------- αφετηρια απο eloratings 2019 ----------
NAMES = json.load(open('intl_team_ids.json', encoding='utf-8'))
code2name = {}
for line in open('elo_intl/en.teams.tsv', encoding='utf-8'):
    p = line.rstrip('\n').split('\t')
    if len(p) >= 2:
        code2name[p[0]] = p[1]
ELO_ALIAS = {'Turkey': 'Türkiye', 'Czech Republic': 'Czechia', 'Bosnia and Herzegovina': 'Bosnia and Herzegovina', 'Ireland': 'Ireland',
             'United States': 'USA', 'South Korea': 'South Korea', 'Ivory Coast': 'Ivory Coast', 'Cape Verde': 'Cape Verde',
             'DR Congo': 'DR Congo', 'Macedonia': 'North Macedonia', 'Republic of Ireland': 'Ireland',
             # 25/9 (Στελιος «διορθωσε και αυτο»): 6 ομαδες ξεκινουσαν απο 1500 λογω ονοματος
             'Taiwan': 'Chinese Taipei', 'East Timor': 'Timor-Leste', 'United Arab Emirates': 'UAE',
             'US Virgin Islands': 'U.S. Virgin Islands', 'Saint Kitts and Nevis': 'St. Kitts and Nevis'}
# εφεδρεια: ονοματα FotMob απο τον ιδιο τον πινακα ματς (π.χ. Ερυθραια δεν ειναι στο intl_team_ids.json)
_MN = pd.read_csv('intl_matches.csv', usecols=['hid', 'aid', 'hn', 'an'])
NAMES_FB = {**dict(zip(_MN.hn, _MN.hid)), **dict(zip(_MN.an, _MN.aid))}


def seed_year(y):
    out = {}
    for line in open(f'elo_intl/{y}.tsv', encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) < 4:
            continue
        code, rating = p[2], p[3]
        nm = code2name.get(code)
        if not nm:
            continue
        nm2 = ELO_ALIAS.get(nm, nm)
        tid = NAMES.get(nm2) or NAMES.get(nm) or NAMES_FB.get(nm2) or NAMES_FB.get(nm)
        if tid is None:
            tn = picks.norm(nm2)
            for k, v in NAMES.items():
                if picks.norm(k) == tn:
                    tid = v; break
        if tid is not None:
            try:
                out[int(tid)] = float(rating)
            except ValueError:
                pass
    return out


SEED = seed_year(SEED_YEAR)
_ids = set(M[M.ctype != 'friendly'].hid) | set(M[M.ctype != 'friendly'].aid)
_noseed = sorted({n for i, n in list(zip(M.hid, M.hn)) + list(zip(M.aid, M.an)) if i in _ids and int(i) not in SEED})
if _noseed:
    print(f'⚠ ομαδες σε επισημα ματς ΧΩΡΙΣ αφετηρια eloratings {SEED_YEAR} (ξεκινουν 1500): {_noseed}', flush=True)
assert M['date'].min() >= pd.Timestamp(WALK_START), 'ο υπολογισμος ξεκινα πριν το τελος της αφετηριας eloratings'
EXT = {y: seed_year(str(y)) for y in range(2019, 2026)}      # στατικο benchmark: τελος ετους y
print(f'αφετηρια eloratings 2019: {len(SEED)} ομαδες αντιστοιχισμενες (απο {sum(1 for _ in open("elo_intl/2019.tsv"))})')

# ---------- Poisson «αναμενομενο σκορ» απο xG ----------
def exp_score(lh, la, max_g=10):
    lh = max(lh, 0.05); la = max(la, 0.05)
    ph = [math.exp(-lh) * lh ** i / math.factorial(i) for i in range(max_g + 1)]
    pa = [math.exp(-la) * la ** j / math.factorial(j) for j in range(max_g + 1)]
    w = d = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            if i > j:
                w += ph[i] * pa[j]
            elif i == j:
                d += ph[i] * pa[j]
    return w + 0.5 * d


def margin_mult(gd):
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return 1.75 + 0.125 * (gd - 3)


def adj_xg(shots_json, fav, mode):
    """(xg_h, xg_a) διορθωμενα. fav: +1 γηπεδουχος φαβορι, -1 φιλοξ. φαβορι, 0 κανενας. mode: 'raw'|'comp'|'gs'."""
    sh = json.loads(shots_json)
    sh.sort(key=lambda s: (s[1] if s[1] is not None else 0))
    hs = as_ = 0; xh = xa = 0.0
    for is_h, mn, xg, goal, pen in sh:
        if pen:
            if goal:
                hs += is_h; as_ += (1 - is_h)
            continue
        v = xg
        if mode in ('comp', 'gs'):
            v = min(v, CAP) + max(v - CAP, 0) * 0.25
        if mode == 'gs':
            d = (hs - as_) if is_h else (as_ - hs)                # κατασταση της ομαδας που σουταρει
            is_fav = (fav == 1 and is_h) or (fav == -1 and not is_h)
            is_dog = (fav == -1 and is_h) or (fav == 1 and not is_h)
            if d < 0:
                v *= GS['fav_trail'] if is_fav else (GS['dog_trail'] if is_dog else 1.0)
            elif d > 0:
                v *= GS['dog_lead'] if is_dog else GS['lead']
        if is_h:
            xh += v
        else:
            xa += v
        if goal:
            hs += is_h; as_ += (1 - is_h)
    return xh, xa


# «as» ειναι δεσμευμενη λεξη στα itertuples -> προσβαση μεσω θεσης
M = M.rename(columns={'as': 'ag'})
def run2(mode):
    R = dict(SEED); rows = []
    scale = 1.0
    if mode in ('X2', 'X3'):
        raw = adj = 0.0
        for r in M[M.has_xg].itertuples():
            a, b = adj_xg(r.shots, 0, 'comp' if mode == 'X2' else 'gs')
            raw += r.xg_h + r.xg_a; adj += a + b
        scale = raw / adj
    for r in M.itertuples():
        rh = R.get(r.hid, 1500.0); ra = R.get(r.aid, 1500.0)
        d = rh + (0 if r.neutral else HFA) - ra
        E = 1 / (1 + 10 ** (-d / 400))
        gd = int(r.hs) - int(r.ag)
        rows.append(dict(mid=r.mid, date=r.date, season=r.season, ctype=r.ctype, comp=r.comp, hid=r.hid, aid=r.aid, hn=r.hn, an=r.an,
                         diff=d, gd=gd, has_xg=bool(r.has_xg)))
        S_res = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        if mode != 'E0' and r.has_xg:
            fav = 1 if d >= FAV_D else (-1 if d <= -FAV_D else 0)
            if mode == 'X1':
                xh, xa = float(r.xg_h), float(r.xg_a)
            else:
                xh, xa = adj_xg(r.shots, fav, 'comp' if mode == 'X2' else 'gs'); xh *= scale; xa *= scale
            S = exp_score(xh, xa); mm = margin_mult(round(xh - xa))
        else:
            S = S_res; mm = margin_mult(gd)
        K = K_TYPE.get(r.ctype, 30) * mm
        R[r.hid] = rh + K * (S - E); R[r.aid] = ra - K * (S - E)
    return pd.DataFrame(rows), R


# ---------- ordered logit diff -> 1X2, LOSO ανα σεζον ----------
def sig(x):
    return 1 / (1 + np.exp(-x))


def nelder_mead(f, x0, steps, iters=3000, tol=1e-7):
    """Μικρος Nelder-Mead (numpy μονο, χωρις scipy)."""
    n = len(x0); simplex = [x0.copy()]
    for i in range(n):
        x = x0.copy(); x[i] += steps[i]; simplex.append(x)
    vals = [f(x) for x in simplex]
    for _ in range(iters):
        order = np.argsort(vals); simplex = [simplex[i] for i in order]; vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = np.mean(simplex[:-1], axis=0)
        xr = c + (c - simplex[-1]); fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - simplex[-1]); fe = f(xe)
            simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (simplex[-1] - c); fc = f(xc)
            if fc < vals[-1]:
                simplex[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    simplex[i] = simplex[0] + 0.5 * (simplex[i] - simplex[0]); vals[i] = f(simplex[i])
    return simplex[int(np.argmin(vals))]


def fit_ol(d, y):
    """y: 0=away,1=draw,2=home. params: beta, c1, c2 (c2>c1)."""
    def nll(p):
        b, c1, dc = p; c2 = c1 + abs(dc) + 1e-6
        pa = sig(c1 - b * d); pd_ = sig(c2 - b * d) - pa; ph = 1 - sig(c2 - b * d)
        P = np.where(y == 0, pa, np.where(y == 1, pd_, ph))
        return -np.sum(np.log(np.clip(P, 1e-9, 1)))
    b, c1, dc = nelder_mead(nll, np.array([0.006, -0.6, 1.2]), steps=np.array([0.002, 0.2, 0.2]))
    return b, c1, c1 + abs(dc) + 1e-6


def probs(d, p):
    b, c1, c2 = p
    pa = sig(c1 - b * d); ph = 1 - sig(c2 - b * d); pd_ = 1 - pa - ph
    return np.vstack([ph, pd_, pa]).T          # [home, draw, away]


def rps(P, y):   # y: 2=home,1=draw,0=away -> outcome vector σε σειρα [home,draw,away]
    O = np.zeros_like(P); O[np.arange(len(y)), 2 - y] = 1
    return np.mean(np.sum((np.cumsum(P, 1) - np.cumsum(O, 1)) ** 2, 1) / 2)


def logloss(P, y):
    return -np.mean(np.log(np.clip(P[np.arange(len(y)), 2 - y], 1e-9, 1)))


EVAL_SEASONS = ['2021', '2122', '2223', '2324', '2425', '2526']
results = {}; latest = {}
preds = {}
for mode in ['E0', 'X1', 'X2', 'X3']:
    D, R = run2(mode); D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
    preds[mode] = D; latest[mode] = R
# blend B: μεσος των diff E0 και X3 (ιδια κλιμακα Elo)
DB = preds['E0'].copy(); DB['diff'] = 0.5 * preds['E0']['diff'].values + 0.5 * preds['X3']['diff'].values
preds['B'] = DB
# εξωτερικο benchmark: eloratings τελος προηγουμενου ημερολογιακου ετους
DE = preds['E0'].copy()
def ext_diff(r):
    y = r.date.year - 1 if r.date.month >= 1 else r.date.year - 1
    tab = EXT.get(y, {})
    if r.hid in tab and r.aid in tab:
        return tab[r.hid] + (0 if r.ctype == 'tourn' else HFA) - tab[r.aid]      # προσεγγιση ουδετερου
    return np.nan
DE['diff'] = DE.apply(ext_diff, axis=1)
preds['EXT'] = DE
for _m, _D in preds.items():
    _D.to_csv(f'intl_preds_{_m}.csv', index=False)

out_lines = []
def P(s=''):
    print(s); out_lines.append(s)

P('=' * 110)
P('RPS ανα σεζον (ΑΓΩΝΙΣΤΙΚΑ ματς: nl/qual/tourn) — ordered logit fit-αρισμενο LOSO στις αλλες σεζον')
P('=' * 110)
table = []
for mode, D in preds.items():
    C = D[D.ctype.isin(['nl', 'qual', 'tourn']) & D['diff'].notna()].copy()
    row = dict(variant=mode)
    allP = []; ally = []
    for s in EVAL_SEASONS:
        tr = C[(C.season != s) & (C.season.isin(EVAL_SEASONS + ['1920', '2021']))]; te = C[C.season == s]
        if len(te) < 20 or len(tr) < 100:
            row[s] = np.nan; continue
        p = fit_ol(tr['diff'].values, tr['y'].values)
        Pm = probs(te['diff'].values, p)
        row[s] = round(rps(Pm, te['y'].values), 4); allP.append(Pm); ally.append(te['y'].values)
    if allP:
        Pm = np.vstack(allP); yy = np.concatenate(ally)
        row['ALL'] = round(rps(Pm, yy), 4); row['logloss'] = round(logloss(Pm, yy), 4); row['n'] = len(yy)
    table.append(row)
T = pd.DataFrame(table).set_index('variant')
P(T.to_string())
base = T.loc['E0']
P('\n-- σε σχεση με E0 (αρνητικο = καλυτερο), και σε ποσες σεζον καλυτερο:')
for v in T.index:
    if v == 'E0':
        continue
    better = sum(1 for s in EVAL_SEASONS if pd.notna(T.loc[v, s]) and pd.notna(base[s]) and T.loc[v, s] < base[s])
    P(f'  {v:4s}: ΔRPS {T.loc[v, "ALL"] - base["ALL"]:+.4f}  καλυτερο σε {better}/{sum(pd.notna(base[s]) for s in EVAL_SEASONS)} σεζον')
P('\n-- ανα τυπο αγωνα (ALL σεζον, ιδια LOSO χαρτογραφηση):')
rows = []
for mode, D in preds.items():
    C = D[D['diff'].notna()].copy()
    r = dict(variant=mode)
    for ct in ['friendly', 'nl', 'qual', 'tourn']:
        allP = []; ally = []
        for s in EVAL_SEASONS:
            trn = C[(C.season != s) & C.ctype.isin(['nl', 'qual', 'tourn'])]; te = C[(C.season == s) & (C.ctype == ct)]
            if len(te) < 15 or len(trn) < 100:
                continue
            p = fit_ol(trn['diff'].values, trn['y'].values); allP.append(probs(te['diff'].values, p)); ally.append(te['y'].values)
        r[ct] = round(rps(np.vstack(allP), np.concatenate(ally)), 4) if allP else np.nan
    rows.append(r)
P(pd.DataFrame(rows).set_index('variant').to_string())

# ---------- τρεχοντα ratings ----------
names = {}
for r in M.itertuples():
    names[r.hid] = r.hn; names[r.aid] = r.an
L = pd.DataFrame({m: pd.Series(R) for m, R in latest.items()})
L['name'] = L.index.map(names); L['B'] = 0.5 * L['E0'] + 0.5 * L['X3']
last = M.groupby('hid')['date'].max().combine(M.groupby('aid')['date'].max(), max)
L['last_match'] = L.index.map(last)
L = L[L['last_match'] >= '2025-01-01'].sort_values('B', ascending=False)
L.to_csv('intl_ratings_latest.csv')
P('\n-- ΤΟΠ 25 τρεχοντα ratings (B = blend E0/X3):')
P(L[['name', 'E0', 'X1', 'X2', 'X3', 'B']].head(25).round(0).to_string())
open('intl_rating_out.txt', 'w', encoding='utf-8').write('\n'.join(out_lines))
