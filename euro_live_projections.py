# -*- coding: utf-8 -*-
"""
euro_live_projections.py — LIVE προβλεψεις του ευρωπαικου V4 engine για ΟΛΑ τα ματς
της League Phase 2627 (UCL/UEL/UECL) απο το europe_fixtures_2627.json.
Γραφει euro_projections.json (για το Streamlit dashboard). Ξανατρεχει end-to-end.

Πιστη αναπαραγωγη της μηχανης του euro_expand_test.py (GEngine+Griffis, build_rows,
s_v4/src_off ιεραρχια POFF→bridge-id→ClubElo→fitted, CAL Elo-αντικατασταση για
goals-πλευρες, HFA) με ΜΙΑ διαφορα: LIVE, οχι LOSO — ολα τα fits (FIT2 per-league s,
CAL a/b, HFA) γινονται σε ΟΛΟ το ιστορικο δειγμα (2223-2526 μαζι, HFA και με 2122).
Επιπλεον live αναγκη: ο εγχωριος builder ΔΕΝ σκιπαρει τις φετινες σεζον (2627/2026),
ωστε να υπαρχει side_state στις ημερομηνιες του 2627. Για goals-πλευρες του 2627 δεν
υπαρχει per-mid Elo (clubelo_europe.csv) — χρησιμοποιειται clubelo_current.csv με
αντιστοιχιση ονοματος στη χωρα της λιγκας· αν δεν ταιριαξει, μενει raw goals-rating
και σημειωνεται.

ΔΕΝ αγγιζει κανενα υπαρχον αρχειο.
"""
import json, glob, os, re, sys, math, time, bisect, unicodedata
from datetime import datetime, timezone
from collections import Counter
import numpy as np, pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import picks
import euro_engine as EE
from euro_engine import (Engine, team_xg_raw, kodt, EU_SEASONS, EU_EVAL,
                         GAMMA_PLAYER, NS_CONST, EPS, w, player_offsets)

T0 = time.time()
K = 8
RHO = 1.0
RIDGE = 3.0
MIN_FIT_N = 15
PEN_XG = 0.79
CUR_SEAS = {'2627', '2026'}     # "φετινες" σεζον — οτιδηποτε αλλο στο state = μπαγιατικο, σημειωνεται

GRIFFIS_LGS = ['CzechFirstLeague', 'CroatiaHNL', 'SerbiaSuperLiga', 'RomaniaLigaI',
               'HungaryNBI', 'SlovakiaNikeLiga', 'IsraelLigatHaAl',
               'FinlandVeikkausliiga', 'LatviaVirsliga']
GRIFFIS_SKIP_SEA = set()   # live: μπαινουν ΚΑΙ οι φετινες σεζον Griffis (2627/2026)

LID = {
    'CzechFirstLeague': 122, 'CroatiaHNL': 252, 'BulgariaFirstLeague': 270,
    'CyprusFirstDivision': 136, 'SerbiaSuperLiga': 182, 'UkrainePremierLeague': 441,
    'IsraelLigatHaAl': 127, 'HungaryNBI': 212, 'SlovakiaNikeLiga': 176,
    'RomaniaLigaI': 189, 'SloveniaPrvaLiga': 173, 'AzerbaijanPremierLeague': 262,
    'ArmeniaPremierLeague': 118, 'BosniaPremierLeague': 267, 'AlbaniaKategoriaSuperiore': 260,
    'LithuaniaALyga': 228, 'GeorgiaErovnuliLiga': 439, 'KazakhstanPremierLeague': 225,
    'FinlandVeikkausliiga': 51, 'LatviaVirsliga': 226,
}
LG_COUNTRY = {
    'EPL': 'ENG', 'LaLiga': 'ESP', 'SerieA': 'ITA', 'Bundesliga': 'GER', 'Ligue1': 'FRA',
    'PrimeiraLiga': 'POR', 'Eredivisie': 'NED', 'Belgium': 'BEL', 'GreeceSL': 'GRE',
    'ScottishPrem': 'SCO', 'DanishSuperLiga': 'DEN', 'AustrianBundesliga': 'AUT',
    'SwissSuperleague': 'SUI', 'TurkishSuperLig': 'TUR', 'Allsvenskan': 'SWE',
    'Eliteserien': 'NOR', 'Ekstraklasa': 'POL', 'CroatiaHNL': 'CRO',
    'CzechFirstLeague': 'CZE', 'RomaniaLigaI': 'ROU', 'SerbiaSuperLiga': 'SRB',
    'IsraelLigatHaAl': 'ISR', 'FinlandVeikkausliiga': 'FIN',
    'HungaryNBI': 'HUN', 'SlovakiaNikeLiga': 'SVK', 'LatviaVirsliga': 'LVA',
    'BulgariaFirstLeague': 'BUL', 'CyprusFirstDivision': 'CYP', 'UkrainePremierLeague': 'UKR',
    'SloveniaPrvaLiga': 'SVN', 'AzerbaijanPremierLeague': 'AZE', 'ArmeniaPremierLeague': 'ARM',
    'BosniaPremierLeague': 'BIH', 'AlbaniaKategoriaSuperiore': 'ALB',
    'LithuaniaALyga': 'LTU', 'GeorgiaErovnuliLiga': 'GEO', 'KazakhstanPremierLeague': 'KAZ',
    'PrimeiraLiga2': 'POR', 'NorwayOBOS': 'NOR',
}

POFF = player_offsets()

def s_player(lg):
    return -GAMMA_PLAYER * POFF[lg] if lg in POFF else None

# ---------------- Griffis — ιδιος κωδικας με euro_expand_test ----------------
def load_griffis():
    df = pd.read_csv('griffis_matches.csv')
    nmap = json.load(open('griffis_name_map.json', encoding='utf-8'))
    name2id = {}
    for lg in GRIFFIS_LGS:
        d_ = {}
        for p in sorted(glob.glob(f'data_{lg}_*.json')):
            dd = json.load(open(p, encoding='utf-8'))
            for m in dd.values():
                for side in ('home', 'away'):
                    d_[m[side]['name']] = int(m[side]['id'])
        name2id[lg] = d_
    out = {}
    for r in df.itertuples():
        sea = str(r.season)
        if sea in GRIFFIS_SKIP_SEA or r.league not in GRIFFIS_LGS:
            continue
        key = (r.league, sea)
        tids = []
        for nm in (r.home, r.away):
            e = nmap.get(f'{r.league}|{nm}')
            fm = e.get('fotmob') if e else None
            tids.append(name2id[r.league].get(fm) if fm else None)
        if tids[0] is None or tids[1] is None:
            continue
        dt = datetime.strptime(r.date, '%Y-%m-%d')
        rows = out.setdefault(key, [])
        for tid, gf, xg, npxg, shots in [(tids[0], r.hg, r.xg_h, r.npxg_h, r.shots_h),
                                         (tids[1], r.ag, r.xg_a, r.npxg_a, r.shots_a)]:
            n_pen = int(round(max(xg - npxg, 0.0) / PEN_XG))
            rows.append(dict(date=dt, team=tid, gf=float(gf),
                             xg_model=float(npxg + 0.25 * n_pen),
                             ns_eff=float(max(shots, 1.0))))
    return {k: pd.DataFrame(v) for k, v in out.items()}

# ---------------- GEngine (πιστη αντιγραφη euro_expand_test / euro_roi_test) ----------------
# Live διαφορες: (α) skip_sea=set() (μπαινουν και 2627/2026 εγχωρια δεδομενα),
# (β) guard διεφθαρμενων αρχειων: λιγκα-σεζον με median ημερομηνια ασυμβατη με το label
#     της σεζον πετιεται (πιανει τα data_AustrianBundesliga_2122/2223/2324.json που
#     περιεχουν ματς ανοιξης 2026 και χαλανε τη χρονολογηση/PRV της Αυστριας).
def _sea_label_ok(sea, med_dt):
    my = med_dt.year + med_dt.month / 12.0
    if sea.startswith('20') and len(sea) == 4 and int(sea[2]) < 3:   # ημερολογιακη π.χ. '2026'
        y0 = int(sea)
        return (y0 - 0.2) <= my <= (y0 + 1.2)
    y0 = 2000 + int(sea[:2])                                          # π.χ. '2627'
    return (y0 + 0.4) <= my <= (y0 + 1.6)

class GEngine(Engine):
    def __init__(self, griffis=None, skip_sea=frozenset(), verbose=False):
        self.griffis = griffis or {}
        self.skip_sea = set(skip_sea)
        self.BAD_SEASONS = []
        super().__init__(verbose=verbose)

    def _build_domestic(self):
        files = {}
        for p in sorted(glob.glob('data_*.json')):
            base = os.path.basename(p)[:-5]
            parts = base.split('_')
            lg = '_'.join(parts[1:-1]); sea = parts[-1]
            if lg in EE.SKIP_LG or sea in self.skip_sea or not sea.isdigit():
                continue
            files.setdefault(lg, []).append((sea, p))
        self.H = {}; self.PRIOR = {}; self.RULER_FULL = {}; self.RUN = {}
        self.SPAN = {}; self.GOAL_ONLY = set(); self.SEASONS = {}; self.PRV = {}
        self.TEAM_LGS = {}; self.id2name = {}
        for lg, sps in files.items():
            med = {}
            for sea, path in sps:
                key = (lg, sea)
                if key in self.griffis:
                    g = self.griffis[key].copy()
                    goal_only = False
                else:
                    d = json.load(open(path, encoding='utf-8'))
                    rows = []
                    any_shots = any(m['shots'] for m in d.values())
                    goal_only = not any_shots
                    if goal_only:
                        self.GOAL_ONLY.add(key)
                    for mid, m in d.items():
                        hid = int(m['home']['id']); aid = int(m['away']['id'])
                        self.id2name[hid] = m['home']['name']; self.id2name[aid] = m['away']['name']
                        if m['hs'] is None or m['as'] is None:
                            continue
                        dt = kodt(m['date'])
                        if dt is None:
                            continue
                        if goal_only:
                            for is_home, tid, gf in [(1, hid, m['hs']), (0, aid, m['as'])]:
                                rows.append(dict(date=dt, team=tid, is_home=is_home, gf=gf,
                                                 np_raw=np.nan, np_comp=np.nan, pen=0, ns=np.nan, red_xg=0.0))
                            continue
                        if not m['shots']:
                            continue
                        agg = {hid: dict(np_raw=0.0, np_comp=0.0, pen=0, ns=0),
                               aid: dict(np_raw=0.0, np_comp=0.0, pen=0, ns=0)}
                        for s in m['shots']:
                            xg = s.get('xg')
                            if xg is None: continue
                            tid = s.get('tid')
                            if tid not in agg: continue
                            if s.get('sit') == 'Penalty':
                                agg[tid]['pen'] += 1
                            else:
                                agg[tid]['np_raw'] += xg
                                agg[tid]['np_comp'] += xg * w(xg)
                                agg[tid]['ns'] += 1
                        ft = 95; dis_home = 0.0; dis_away = 0.0
                        for r in (m.get('reds') or []):
                            mn = r.get('min') or 0
                            dur = max(0, ft - mn)
                            if r['home']: dis_home += dur
                            else: dis_away += dur
                        for is_home, tid, gf, dis_self, dis_opp in [
                                (1, hid, m['hs'], dis_home, dis_away),
                                (0, aid, m['as'], dis_away, dis_home)]:
                            a = agg[tid]
                            red_xg = 0.0083 * dis_opp - 0.5 * 0.0083 * dis_self
                            rows.append(dict(date=dt, team=tid, is_home=is_home, gf=gf,
                                             np_raw=a['np_raw'], np_comp=a['np_comp'], pen=a['pen'],
                                             ns=a['ns'], red_xg=red_xg))
                    if not rows:
                        continue
                    g = pd.DataFrame(rows)
                    if goal_only:
                        g['xg_model'] = g['gf'].astype(float)
                        g['ns_eff'] = NS_CONST
                    else:
                        sf = g.np_raw.sum() / max(g.np_comp.sum(), EPS)
                        g['xg_model'] = g['np_comp'] * sf + 0.25 * g['pen'] + g['red_xg']
                        g['ns_eff'] = g['ns'] + g['pen'] + g['red_xg'].abs() / 0.10
                if len(g) == 0:
                    continue
                med_dt = sorted(g.date)[len(g) // 2]
                if not _sea_label_ok(sea, med_dt):
                    self.BAD_SEASONS.append((lg, sea, str(med_dt.date())))
                    continue
                per_team = {}
                for i in range(0, len(g) - 1, 2):
                    a_, b_ = g.iloc[i], g.iloc[i + 1]
                    per_team.setdefault(int(a_.team), []).append(
                        (a_.date, a_.ns_eff, a_.xg_model, a_.gf, b_.ns_eff, b_.xg_model, b_.gf))
                    per_team.setdefault(int(b_.team), []).append(
                        (b_.date, b_.ns_eff, b_.xg_model, b_.gf, a_.ns_eff, a_.xg_model, a_.gf))
                g = g.sort_values('date').reset_index(drop=True)
                hh = {}
                for tid, tm in per_team.items():
                    tm.sort(key=lambda x: x[0])
                    hh[tid] = dict(dates=[x[0] for x in tm],
                                   sf=np.array([x[1] for x in tm], float),
                                   xf=np.array([x[2] for x in tm], float),
                                   gf=np.array([x[3] for x in tm], float),
                                   sa=np.array([x[4] for x in tm], float),
                                   xa=np.array([x[5] for x in tm], float),
                                   ga=np.array([x[6] for x in tm], float))
                self.H[key] = hh
                self.RULER_FULL[key] = (float(g.ns_eff.mean()),
                                        float(g.xg_model.sum() / max(g.ns_eff.sum(), EPS)))
                dts = sorted(g.date)
                gs = g.sort_values('date')
                self.RUN[key] = (list(gs.date), np.concatenate([[0.0], np.cumsum(gs.ns_eff.values)]),
                                 np.concatenate([[0.0], np.cumsum(gs.xg_model.values)]))
                self.SPAN[key] = (dts[0], dts[-1])
                med[sea] = dts[len(dts) // 2]
                for tid in hh:
                    self.TEAM_LGS.setdefault(tid, set()).add(lg)
            order = sorted(med, key=lambda s: med[s])
            self.SEASONS[lg] = order
            for i, sea in enumerate(order):
                prv = order[i - 1] if i > 0 else None
                if prv is not None and (med[sea] - med[prv]).days > 550:
                    prv = None
                self.PRV[(lg, sea)] = prv
            for sea in order:
                pri = {}
                for tid, h in self.H[(lg, sea)].items():
                    pri[tid] = self._flat_rating(h)
                self.PRIOR[(lg, sea)] = pri

# ---------------- side terms (ιδια μαθηματικα με build_rows του expand test) ----------------
def side_terms(eng, st, d, griffis_keys):
    """(att, leak, SL, XL, src) για μια πλευρα στη στιγμη d."""
    rh = eng.rating_of(st, K)
    SL, XL = eng.ruler(st['lg'], st['sea'], d)
    Ax, Dx, SF, SA = rh
    att = math.log(max((SF / SL) * (Ax / XL), EPS))
    leak = math.log(max((SA / SL) * (Dx / XL), EPS))
    if (st['lg'], st['sea']) in griffis_keys:
        src = 'griffis'
    else:
        src = 'goals' if st['goal_only'] else 'shots'
    return att, leak, SL, XL, src

def build_rows(eng, EU, griffis_keys):
    """Ιδιοι υπολογισμοι με euro_expand_test.build_rows (ιστορικο δειγμα για τα fits)."""
    recs = []
    for r in EU.itertuples():
        sth = eng.side_state(r.hid, r.date); sta = eng.side_state(r.aid, r.date)
        if sth is None or sta is None:
            continue
        att_h, leak_h, SLh, XLh, sr_h = side_terms(eng, sth, r.date, griffis_keys)
        att_a, leak_a, SLa, XLa, sr_a = side_terms(eng, sta, r.date, griffis_keys)
        lXs = math.log(((SLh * SLa) ** 0.5) * ((XLh * XLa) ** 0.5))
        recs.append(dict(mid=r.mid, sea=r.sea, gh=r.gh, ga=r.ga,
                         lg_h=sth['lg'], lg_a=sta['lg'], src_h=sr_h, src_a=sr_a,
                         att_h=att_h, leak_h=leak_h, att_a=att_a, leak_a=leak_a, lXs=lXs,
                         bxh8=math.exp(lXs + att_h + leak_a),
                         bxa8=math.exp(lXs + att_a + leak_h)))
    return pd.DataFrame(recs)

# ================================================================ MAIN
print('=' * 100)
print('EURO V4 — LIVE PROJECTIONS League Phase 2627 (ολα τα fits σε ΟΛΟ το ιστορικο δειγμα, οχι LOSO)')
print('=' * 100)

G = load_griffis()
print('[build] GEngine LIVE (+Griffis, ΜΕ φετινες εγχωριες σεζον)...', flush=True)
eng = GEngine(griffis=G, skip_sea=set(), verbose=False)
GKEYS = set(G.keys())
if eng.BAD_SEASONS:
    print('ΠΕΤΑΧΤΗΚΑΝ διεφθαρμενες λιγκα-σεζον (label ασυμβατο με ημερομηνιες): ' +
          ', '.join(f'{lg}/{sea} (med {md})' for lg, sea, md in eng.BAD_SEASONS))

# ---------------- HFA LIVE: ολες οι σεζον data_Europe (2122-2526) ----------------
sh_tot = sa_tot = 0.0
for sea in EU_SEASONS:
    de = json.load(open(f'data_Europe_{sea}.json', encoding='utf-8'))
    for m in de.values():
        if m['hs'] is None or m['as'] is None or not m['shots']:
            continue
        xh, xa = team_xg_raw(m)
        sh_tot += xh; sa_tot += xa
HF_LIVE = math.sqrt(sh_tot / sa_tot)
print(f'HFA LIVE (ολες οι σεζον {EU_SEASONS[0]}-{EU_SEASONS[-1]}): hf = {HF_LIVE:.4f}')

# ---------------- ιστορικο δειγμα για τα fits: ΟΛΑ τα 2223-2526 με 2 πλευρες ----------------
EU_ALL = eng.load_europe()
EUe = EU_ALL[EU_ALL.sea.isin(EU_EVAL)].reset_index(drop=True)
B_ALL = build_rows(eng, EUe, GKEYS)
print(f'Ιστορικο δειγμα fits: {len(B_ALL)}/{len(EUe)} ματς 2223-2526 με rating 2 πλευρων')

# ---------------- FIT2 LIVE (fitted-offset fallback) — ιδιο ridge-Poisson, χωρις fold ----------------
def fit_all(T):
    xgb_h = T['bxh8'].values * HF_LIVE
    xgb_a = T['bxa8'].values / HF_LIVE
    cnt = pd.concat([T.lg_h, T.lg_a]).value_counts()
    lgs = sorted(cnt[cnt >= MIN_FIT_N].index)
    def grp(lg): return lg if lg in lgs else 'OTH'
    params = [L for L in lgs if L != 'EPL'] + (['OTH'] if (pd.concat([T.lg_h, T.lg_a]).map(grp) == 'OTH').any() else [])
    idx = {L: j + 1 for j, L in enumerate(params)}
    n = len(T); rows = 2 * n; ncol = 1 + len(params)
    X = np.zeros((rows, ncol)); X[:, 0] = 1.0
    y = np.r_[T.gh.values, T.ga.values].astype(float)
    off = np.log(np.maximum(np.r_[xgb_h, xgb_a], 1e-6))
    own = np.r_[T.lg_h.map(grp).values, T.lg_a.map(grp).values]
    opp = np.r_[T.lg_a.map(grp).values, T.lg_h.map(grp).values]
    for i in range(rows):
        if own[i] in idx: X[i, idx[own[i]]] += 1.0
        if opp[i] in idx: X[i, idx[opp[i]]] -= 1.0
    th = np.zeros(ncol)
    R = np.eye(ncol) * RIDGE; R[0, 0] = 0.0
    for _ in range(40):
        eta = X @ th
        lam = np.clip(np.exp(off + eta), 1e-6, 20.0)
        z = eta + (y - lam) / lam
        A = X.T @ (X * lam[:, None]) + R
        b = X.T @ (lam * z)
        new = np.linalg.solve(A, b)
        if np.max(np.abs(new - th)) < 1e-9:
            th = new; break
        th = new
    s = {L: float(th[idx[L]]) for L in params}
    s['EPL'] = 0.0
    return dict(s=s, lgs=set(lgs))

FIT_LIVE = fit_all(B_ALL)

def fitted_s(lg):
    s_ii = FIT_LIVE['s'].get(lg if lg in FIT_LIVE['lgs'] or lg == 'EPL' else 'OTH')
    return s_ii if s_ii is not None else FIT_LIVE['s'].get('OTH', 0.0)

# ---------------- CAL LIVE (Elo->signal για goals-αντικατασταση) — χωρις fold ----------------
ce = pd.read_csv('clubelo_europe.csv')
ce['mid'] = ce['mid'].astype(str)
ELO_MID = {r.mid: (r.home_elo, r.away_elo) for r in ce.itertuples()}
xs = []; ys = []
for r in B_ALL.itertuples():
    eh, ea = ELO_MID.get(r.mid, (np.nan, np.nan))
    for (srcv, lg, at, lk, el) in [(r.src_h, r.lg_h, r.att_h, r.leak_h, eh),
                                   (r.src_a, r.lg_a, r.att_a, r.leak_a, ea)]:
        if srcv == 'goals' or (isinstance(el, float) and np.isnan(el)) or lg not in POFF:
            continue
        ys.append(RHO * s_player(lg) + 0.5 * (at - lk))
        xs.append(el / 100.0)
xs = np.array(xs); ys = np.array(ys)
B_CAL = np.cov(xs, ys)[0, 1] / np.var(xs)
A_CAL = ys.mean() - B_CAL * xs.mean()
print(f'CAL LIVE (n={len(xs)} πλευρες): a={A_CAL:+.3f}  b={B_CAL:.4f}')

# ---------------- offset ιεραρχια POFF -> bridge-id -> ClubElo-χωρας -> fitted ----------------
lo = json.load(open('league_offsets.json', encoding='utf-8'))
id2off = {}
for k_, v in lo.items():
    if '#' in k_:
        try:
            id2off[int(k_.rsplit('#', 1)[1])] = (k_, float(v))
        except ValueError:
            pass
bridge2 = {}
for lg, lid in LID.items():
    if lg not in POFF and lid in id2off:
        bridge2[lg] = id2off[lid]

cel = pd.read_csv('clubelo_current.csv')
ELO_C = cel[cel.level == 1].groupby('country')['elo'].agg(['mean', 'size'])
anch = [(lg, POFF[lg], ELO_C.loc[LG_COUNTRY[lg], 'mean'])
        for lg in sorted(POFF) if lg in LG_COUNTRY and LG_COUNTRY[lg] in ELO_C.index]
ax = np.array([a[2] / 100.0 for a in anch]); ay = np.array([a[1] for a in anch])
c1 = np.cov(ax, ay)[0, 1] / np.var(ax)
c0 = ay.mean() - c1 * ax.mean()
off_elo = {}
for lg, cc in LG_COUNTRY.items():
    if cc in ELO_C.index:
        off_elo[lg] = float(c0 + c1 * ELO_C.loc[cc, 'mean'] / 100.0)
print(f'Offset αγκυρες: n={len(anch)}  OLS off = {c0:+.3f} {c1:+.4f}·(Elo/100)')

def s_v4(lg):
    sp = s_player(lg)
    if sp is not None:
        return sp
    if lg in bridge2:
        return -GAMMA_PLAYER * bridge2[lg][1]
    if lg in off_elo:
        return -GAMMA_PLAYER * off_elo[lg]
    return fitted_s(lg)

def src_off(lg):
    if lg in POFF: return 'POFF'
    if lg in bridge2: return 'bridge-id'
    if lg in off_elo: return 'ClubElo'
    return 'fitted'

# ---------------- Elo ομαδας (clubelo_current) για goals-πλευρες 2627 ----------------
_TR = str.maketrans({'ø': 'o', 'Ø': 'O', 'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D',
                     'ß': 'ss', 'æ': 'ae', 'Æ': 'Ae', 'ı': 'i', 'þ': 'th', 'ð': 'd'})
def norm_name(s):
    s = str(s).translate(_TR)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s.lower())

# alias: FotMob name -> ClubElo name (μονο οπου η αυτοματη αντιστοιχιση δεν πιανει)
ELO_ALIAS = {
    'FC Copenhagen': 'FC Kobenhavn', 'FC København': 'FC Kobenhavn',
    'Ludogorets Razgrad': 'Razgrad', 'Ludogorets': 'Razgrad',
    'Universitatea Craiova': 'Univ Craiova',
    'Maccabi Tel Aviv': 'Maccabi Tel-Aviv',
    'Beitar Jerusalem': 'Beitar Jerushalayim',
    'Hapoel Beer Sheva': 'Hapoel Beer-Sheva', "Hapoel Be'er Sheva": 'Hapoel Beer-Sheva',
    'Qarabag': 'Karabakh Agdam', 'Qarabağ': 'Karabakh Agdam', 'Qarabag FK': 'Karabakh Agdam',
    'Slavia Prague': 'Slavia Praha', 'Sparta Prague': 'Sparta Praha',
    'Pafos FC': 'Paphos', 'Pafos': 'Paphos',
    'Riga FC': 'FK Riga', 'KuPS': 'Kuopio',
    'Kairat Almaty': 'FK Kairat', 'Kairat': 'FK Kairat',
}
def _unesc(s):
    """Το clubelo_current.csv εχει καποια ονοματα με literal \\uXXXX escapes."""
    return s.encode('ascii', 'backslashreplace').decode('unicode_escape') if '\\u' in s else s

CEL_BY_C = {}
for r in cel.itertuples():
    nm = _unesc(str(r.name))
    CEL_BY_C.setdefault(r.country, []).append((norm_name(nm), nm, float(r.elo)))

def team_elo(name, lg):
    """Elo απο clubelo_current με αντιστοιχιση ονοματος στη χωρα της λιγκας. -> (elo, πηγη) ή (None, None)."""
    cc = LG_COUNTRY.get(lg)
    cands = CEL_BY_C.get(cc, [])
    if name in ELO_ALIAS:
        tgt = norm_name(ELO_ALIAS[name])
        for nn, orig, el in cands:
            if nn == tgt:
                return el, orig
    nn0 = norm_name(name)
    for nn, orig, el in cands:
        if nn == nn0:
            return el, orig
    # μοναδικο containment (>=5 χαρακτηρες για να μη πιανει τυχαια)
    hits = [(orig, el) for nn, orig, el in cands
            if len(nn) >= 5 and len(nn0) >= 5 and (nn in nn0 or nn0 in nn)]
    if len(hits) == 1:
        return hits[0][1], hits[0][0]
    return None, None

# ================================================================ ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ -> PRIOR (w=2)
# Επικυρωμενο 9/9/2026 (euro_prior_eu_test @ v6: ΔRPS −0.0011±0.0004, 4/4 σεζον, μονοτονο στο
# προδηλωμενο grid {0.5,1,2}). Καθε περσινο ευρωπαικο ματς μπαινει στο flat prior της ομαδας
# ως w=2 «εγχωρια» παρατηρηση, διορθωμενο για ποιοτητα αντιπαλου/offsets/εδρα (μηχανικη ιδια
# με το τεστ). Υπολογισμος ΟΛΩΝ πρωτα, εγγραφη στα eng.PRIOR μετα (οχι μολυνση των opp_q).
W_EU = 2.0
EU_DRAW_SCALE = 0.85
P_EU_SEA = '2526'
b_blend = picks.blend_at(None)
lhf_eu = math.log(HF_LIVE)

fx = json.load(open('europe_fixtures_2627.json', encoding='utf-8'))
_teams_2627 = {}
for key_ in sorted(fx):
    for m_ in fx[key_]:
        for tid_ in (int(m_['hid']), int(m_['aid'])):
            d_ = datetime.fromisoformat(str(m_['utc']).replace('Z', '+00:00')).replace(tzinfo=None)
            if tid_ not in _teams_2627 or d_ < _teams_2627[tid_]:
                _teams_2627[tid_] = d_

EU_BY_TEAM = {}
for r in EU_ALL[EU_ALL.sea == P_EU_SEA].itertuples():
    if isinstance(r.xgh_act, float) and math.isnan(r.xgh_act):
        continue
    EU_BY_TEAM.setdefault(r.hid, []).append((r.mid, r.date, 1, r.xgh_act, r.xga_act, r.gh, r.ga, r.aid, r.comp))
    EU_BY_TEAM.setdefault(r.aid, []).append((r.mid, r.date, 0, r.xga_act, r.xgh_act, r.ga, r.gh, r.hid, r.comp))

def _opp_q(oid, mid, is_opp_home, d):
    st_o = eng.side_state(oid, d)
    if st_o is None:
        return None
    att_o, leak_o, SL_o, XL_o, src_o = side_terms(eng, st_o, d, GKEYS)
    s_o = s_v4(st_o['lg'])
    if src_o == 'goals':
        el = ELO_MID.get(str(mid), (np.nan, np.nan))[0 if is_opp_home else 1]
        try:
            el = float(el)
        except (TypeError, ValueError):
            el = float('nan')
        if not math.isnan(el):
            u = A_CAL + B_CAL * el / 100.0 - RHO * s_o
            att_o, leak_o = u, -u
    lnXmO = math.log(max(SL_o * XL_o, 1e-9))
    return (0.5 * lnXmO + leak_o - RHO * s_o, 0.5 * lnXmO + att_o + RHO * s_o)

_cm_acc = {}
for r in EU_ALL[EU_ALL.sea == P_EU_SEA].itertuples():
    for oid_, ish_ in [(r.hid, True), (r.aid, False)]:
        q_ = _opp_q(oid_, r.mid, ish_, r.date)
        if q_ is not None:
            _cm_acc.setdefault(r.comp, []).append(q_)
CMEAN_EU = {c: (float(np.mean([v[0] for v in vv])), float(np.mean([v[1] for v in vv])))
            for c, vv in _cm_acc.items()}

_enr = {}
_ex = []
for tid_, d0 in _teams_2627.items():
    st_ = eng.side_state(tid_, d0)
    if st_ is None:
        continue
    lg_, sea_ = st_['lg'], st_['sea']
    p_dom = eng.PRV.get((lg_, sea_))
    if p_dom is None:
        continue
    prior = eng.PRIOR.get((lg_, p_dom), {}).get(tid_)
    if prior is None or tid_ not in EU_BY_TEAM:
        continue
    n_dom = len(eng.H[(lg_, p_dom)][tid_]['dates'])
    sT = s_v4(lg_)
    obs = []
    for (mid_, dm, ish, xgf, xga, gf, ga, oid_, comp_) in EU_BY_TEAM[tid_]:
        q_ = _opp_q(oid_, mid_, ish == 0, dm)
        if q_ is None:
            q_ = CMEAN_EU.get(comp_)
            if q_ is None:
                continue
        qd, qa = q_
        SLt, XLt = eng.ruler(lg_, p_dom, dm)
        lnXmT = math.log(max(SLt * XLt, 1e-9))
        hterm = lhf_eu if ish else -lhf_eu
        raw_att = b_blend * xgf + (1 - b_blend) * gf
        raw_def = b_blend * xga + (1 - b_blend) * ga
        obs.append((raw_att * math.exp(0.5 * lnXmT - qd - RHO * sT - hterm),
                    raw_def * math.exp(0.5 * lnXmT - qa + RHO * sT + hterm)))
    if not obs:
        continue
    Patt = prior[0] * prior[2]; Pdef = prior[1] * prior[3]
    s_att = sum(o[0] for o in obs); s_def = sum(o[1] for o in obs)
    na = (n_dom * Patt + W_EU * s_att) / (n_dom + W_EU * len(obs))
    nd = (n_dom * Pdef + W_EU * s_def) / (n_dom + W_EU * len(obs))
    _enr[(lg_, p_dom, tid_)] = (na / max(prior[2], 1e-9), nd / max(prior[3], 1e-9), prior[2], prior[3])
    _ex.append((abs(math.log(max(na, 1e-9) / max(Patt, 1e-9))) +
                abs(math.log(max(nd, 1e-9) / max(Pdef, 1e-9))),
                eng.id2name.get(tid_, str(tid_)), Patt, na, Pdef, nd, len(obs)))
for (lg_, p_dom, tid_), tup in _enr.items():
    eng.PRIOR[(lg_, p_dom)][tid_] = tup
_ex.sort(reverse=True)
print(f'ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ ΣΤΟ PRIOR (w={W_EU:.0f}): εμπλουτιστηκαν {len(_enr)} ομαδες '
      f'({sum(e[6] for e in _ex)} ματς 2526)· μεγαλυτερες αλλαγες:')
for _, nm_, a0, a1, d0_, d1, ne_ in _ex[:6]:
    print(f'  {nm_:22s} n_eu={ne_:2d}  xGF prior {a0:.2f}->{a1:.2f}  xGA {d0_:.2f}->{d1:.2f}')

# ================================================================ 2627 fixtures -> projections
SRC_LABEL = {'shots': 'FotMob', 'griffis': 'Ben'}
matches = []
miss_team = Counter()
elo_miss = set()
stale = Counter()
n_goals_sub = n_goals_raw = 0

for key in sorted(fx):
    comp = key.rsplit('_', 1)[0]
    for m in fx[key]:
        d = datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00')).replace(tzinfo=None)
        rec = dict(mid=str(m['mid']), comp=comp, round=m.get('round'), utc=m['utc'],
                   home=m['hname'], away=m['aname'], hid=int(m['hid']), aid=int(m['aid']),
                   finished=bool(m.get('finished')), score=m.get('score') or '')
        sth = eng.side_state(int(m['hid']), d)
        sta = eng.side_state(int(m['aid']), d)
        if sth is None or sta is None:
            miss = []
            if sth is None: miss.append(f'εδρα: {m["hname"]}'); miss_team[m['hname']] += 1
            if sta is None: miss.append(f'φιλοξ: {m["aname"]}'); miss_team[m['aname']] += 1
            rec.update(covered=False, note='χωρις rating — ' + ', '.join(miss))
            matches.append(rec)
            continue
        att_h, leak_h, SLh, XLh, sr_h = side_terms(eng, sth, d, GKEYS)
        att_a, leak_a, SLa, XLa, sr_a = side_terms(eng, sta, d, GKEYS)
        lXs = math.log(((SLh * SLa) ** 0.5) * ((XLh * XLa) ** 0.5))
        notes = []
        lab = {}
        for tag, st_, nm in [('h', sth, m['hname']), ('a', sta, m['aname'])]:
            sr = sr_h if tag == 'h' else sr_a
            if sr == 'goals':
                el, elo_nm = team_elo(nm, st_['lg'])
                if el is not None:
                    sig = A_CAL + B_CAL * el / 100.0
                    u = sig - RHO * s_v4(st_['lg'])
                    if tag == 'h':
                        att_h, leak_h = u, -u
                    else:
                        att_a, leak_a = u, -u
                    lab[tag] = 'γκολ+Elo'
                    n_goals_sub += 1
                else:
                    lab[tag] = 'γκολ'
                    n_goals_raw += 1
                    elo_miss.add(f'{nm} ({st_["lg"]})')
                    notes.append(f'χωρις Elo match: {nm} — raw goals-rating')
            else:
                lab[tag] = SRC_LABEL[sr]
            if st_['sea'] not in CUR_SEAS:
                stale[(st_['lg'], st_['sea'])] += 1
                notes.append(f'{"εδρα" if tag == "h" else "φιλοξ"} {nm}: δεδομενα σεζον {st_["sea"]} (μπαγιατικα)')
        D = s_v4(sth['lg']) - s_v4(sta['lg'])
        xgh0 = math.exp(lXs + att_h + leak_a + RHO * D)
        xga0 = math.exp(lXs + att_a + leak_h - RHO * D)
        xgh = xgh0 * HF_LIVE
        xga = xga0 / HF_LIVE
        dist = picks.gd_dist(max(xgh, 0.05), max(xga, 0.05))
        p1 = sum(p for k_, p in dist.items() if k_ > 0)
        px = dist.get(0, 0.0)
        p2 = 1.0 - p1 - px
        # ΔΙΟΡΘΩΣΗ ΙΣΟΠΑΛΙΩΝ ΕΥΡΩΠΗΣ (9/9/2026, euro_testB + dc_draw_test): η Ευρωπη βγαζει
        # λιγοτερα Χ απ' οσα το εγχωριο DC boost 1.13 προβλεπει (actual 18-20% vs pred 24.8%,
        # μονοτονη πτωση 5/5 σεζον)· LOSO ρ=0.78-0.86, βελτιωση RPS 4/4 → συντηρητικο 0.85.
        # Εφαρμοζεται ΜΟΝΟ εδω (ευρωπαικα)· το εγχωριο 1.13 μενει ως εχει.
        px_new = EU_DRAW_SCALE * px
        k_win = (1.0 - px_new) / max(1.0 - px, 1e-9)
        p1 *= k_win; p2 *= k_win; px = px_new
        rec.update(covered=True, note='· '.join(notes),
                   xgh=round(xgh, 3), xga=round(xga, 3),
                   xgh0=round(xgh0, 3), xga0=round(xga0, 3),
                   p1=round(p1, 4), px=round(px, 4), p2=round(p2, 4),
                   o1=round(1 / p1, 3), ox=round(1 / px, 3), o2=round(1 / p2, 3),
                   src_h=lab['h'], src_a=lab['a'],
                   lg_h=sth['lg'], lg_a=sta['lg'],
                   n_h=int(sth['n']), n_a=int(sta['n']))
        matches.append(rec)

out = dict(generated=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           engine='euro V4 — bridges ρ=1.0 + ClubElo offsets, warm-start K=8',
           hfa=round(HF_LIVE, 4),
           matches=matches)
with open('euro_projections.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ================================================================ ΑΝΑΦΟΡΑ / SANITY
cov = [m for m in matches if m['covered']]
print(f'\nΓραφτηκε euro_projections.json: {len(matches)} ματς ({len(cov)} covered, {len(matches)-len(cov)} οχι)')
per = '  '.join(f'{c}: {sum(1 for m in matches if m["comp"] == c)} '
                f'(cov {sum(1 for m in cov if m["comp"] == c)})'
                for c in ['ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'])
print('ανα comp: ' + per)

teams = {}
for m in matches:
    teams[m['hid']] = m['home']; teams[m['aid']] = m['away']
cov_teams = set()
for m in cov:
    cov_teams.add(m['hid']); cov_teams.add(m['aid'])
never = sorted(nm for tid, nm in teams.items() if tid not in cov_teams)
print(f'ομαδες συνολο: {len(teams)}  με >=1 covered ματς: {len(cov_teams)}  '
      f'ΠΟΤΕ καλυμμενες: {len(never)} -> {", ".join(never) if never else "-"}')
if miss_team:
    print('ακαλυπτες πλευρες ανα ομαδα: ' +
          ', '.join(f'{t} ({c} ματς)' for t, c in miss_team.most_common()))
print(f'goals-πλευρες: με Elo-αντικατασταση {n_goals_sub}, raw (χωρις Elo match) {n_goals_raw}')
if elo_miss:
    print('  χωρις Elo match: ' + ', '.join(sorted(elo_miss)))
if stale:
    print('μπαγιατικα states (λιγκα, σεζον -> πλευρες): ' +
          ', '.join(f'{k[0]}/{k[1]}:{v}' for k, v in sorted(stale.items())))

src_cnt = Counter()
for m in cov:
    src_cnt[m['src_h']] += 1; src_cnt[m['src_a']] += 1
print('πηγη ανα πλευρα: ' + ', '.join(f'{k}: {v}' for k, v in src_cnt.most_common()))

tot = np.array([m['xgh'] + m['xga'] for m in cov])
print(f'\nSANITY (α): μεσο συνολο xG = {tot.mean():.3f}  (min {tot.min():.2f}, max {tot.max():.2f}, '
      f'p5 {np.percentile(tot,5):.2f}, p95 {np.percentile(tot,95):.2f})')
mean_p1 = np.mean([m['p1'] for m in cov]); mean_px = np.mean([m['px'] for m in cov])
print(f'μεσα 1Χ2: p1 {mean_p1:.3f}  px {mean_px:.3f}  p2 {1-mean_p1-mean_px:.3f}')

print('\nSANITY (β) — δειγματα projections:')
def show(mm):
    if mm['covered']:
        print(f'  [{mm["comp"][:4]} R{mm["round"]}] {mm["home"]} - {mm["away"]}  '
              f'xG {mm["xgh"]:.2f}-{mm["xga"]:.2f} (ουδ. {mm["xgh0"]:.2f}-{mm["xga0"]:.2f})  '
              f'1Χ2 {mm["p1"]*100:.0f}/{mm["px"]*100:.0f}/{mm["p2"]*100:.0f}%  '
              f'fair {mm["o1"]:.2f}/{mm["ox"]:.2f}/{mm["o2"]:.2f}  '
              f'[{mm["src_h"]}/{mm["src_a"]}  n={mm["n_h"]}/{mm["n_a"]}]' +
              (f'  ! {mm["note"]}' if mm['note'] else ''))
    else:
        print(f'  [{mm["comp"][:4]} R{mm["round"]}] {mm["home"]} - {mm["away"]}  ΑΚΑΛΥΠΤΟ: {mm["note"]}')

want = [('AEK', 'LASK'), ('Man City', None), ('Real Madrid', None), ('Bayern', None),
        ('Olympiakos', None), ('PAOK', None), ('Fiorentina', None), ('Shakhtar', None)]
shown = set()
for a, b in want:
    for mm in matches:
        if a.lower() in (mm['home'] + '|' + mm['away']).lower() and \
           (b is None or b.lower() in (mm['home'] + '|' + mm['away']).lower()):
            if mm['mid'] not in shown:
                show(mm); shown.add(mm['mid'])
            break
print('\nτυχαια 4 ακομα:')
import random
random.seed(7)
for mm in random.sample(cov, 4):
    if mm['mid'] not in shown:
        show(mm)

print(f'\nΤΕΛΟΣ [{time.time()-T0:.0f}s]')
