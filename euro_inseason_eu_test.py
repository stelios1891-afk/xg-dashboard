"""
euro_inseason_eu_test.py — ΦΕΤΙΝΑ ΕΥΡΩΠΑΪΚΑ ΜΑΤΣ ΣΤΟ ΦΕΤΙΝΟ RATING (walk-forward, με διορθωση αντιπαλου).

ΚΑΛΟΥΠΙ: euro_prior_eu_test.py (V6 harness, LOSO FIT2/CAL/HFA, ιδιο δειγμα κλειδωμενο στο
euro_v6_preds.pkl) — ο κορμος (γρ. 29-625) αντιγραφεται ΑΥΤΟΥΣΙΟΣ.

BASELINE = LIVE ευρωπαικο stack (euro_live_projections.py), σε LOSO μορφη:
  V4 engine (GEngine+Griffis, K=8, ρ=1.0, s_v4 ιεραρχια POFF→bridge→ClubElo→FIT2, CAL goals→Elo,
  HFA Ευρωπης LOSO) + prior-EU w=2 (t−1 ευρωπαικα στο prior)
  + ξεφουσκωμα λιγκας c = −0.470·D (D = s_v4(γηπ) − s_v4(φιλοξ)): λh−c/2, λa+c/2, clip 0.05
  + UCL_FAV_SCALE 1.16 στη πλευρα του φαβορι (μεγαλυτερο λ μετα το ξεφουσκωμα), ΜΟΝΟ UCL
    νεου format (2425, 2526 — το 2627 live ειναι νεο format· το κ βγηκε/επικυρωθηκε μονο εκει)
  + EU_DRAW_SCALE 0.85 στο P(X) (αναλογικη ανακατανομη στο 1/2) για RPS και pricing.
  (Το OU ζευγος πεναλτι-0.76 ΔΕΝ υπαρχει στο harness → ROI μονο AH, χωρις overs.)

ΜΟΝΗ ΑΛΛΑΓΗ (νεος μηχανισμος): για ευρωπαικο ματς της ομαδας T την στιγμη d (ευρωπαικη σεζον S):
  E_T(d) = τα ευρωπαικα ματς της T στη σεζον S (ομιλος/LP + KO, ολες οι 3 διοργανωσεις — τα
  προκριματικα ΔΕΝ υπαρχουν στο data_Europe, αρα ΔΕΝ μπαινουν) με ημερομηνια ΑΥΣΤΗΡΑ < d.
  Καθε ματς → «εγχωρια-ισοδυναμη» παρατηρηση με ΑΚΡΙΒΩΣ τη διορθωση του prior-EU:
    xGF_eq = (b·xG + (1−b)·γκολ) · exp( ½lnXm_T − q_def(O) − ρ·s_T ∓ ln hf )
    xGA_eq = (b·xGA + (1−b)·γκολ κατα) · exp( ½lnXm_T − q_att(O) + ρ·s_T ± ln hf )
  q_def/q_att = ½lnXm_O + leak/att του αντιπαλου (ΙΔΙΟ opp_q με το prior-EU: rating K=8 του
  engine την ημερα του ματς, goals→Elo οπου ισχυει, s_v4 του fold)· αντιπαλος χωρις rating →
  μεσος q διοργανωσης-σεζον S απο ματς με ημερομηνια < του ματς (walk-forward)· αν κανενα,
  ο t−1 μεσος (οπως prior-EU). b = picks.blend_at(None). hf = LOSO HFA του fold.
  Xm_T, s_T = χαρακας (στη στιγμη του ευρωπαικου ματς) και offset της ΤΡΕΧΟΥΣΑΣ εγχωριας
  λιγκας-σεζον της T (αυτης στην οποια συγχωνευεται η παρατηρηση).
  ΣΥΓΧΩΝΕΥΣΗ στο φετινο σκελος (αναλογα με το prior-EU, σε μοναδες xG/ματς):
    cur = (Ax, Dx, sf, sa) φετινο εγχωριο (wmean DECAY, blend_at(n)), n = φετινα εγχωρια
    xGF_cur' = (n·Ax·sf + w_in·Σ xGF_eq) / (n + w_in·n_eu)      Ax' = xGF_cur'/sf
    xGA_cur' = (n·Dx·sa + w_in·Σ xGA_eq) / (n + w_in·n_eu)      Dx' = xGA_cur'/sa
    n' = n + w_in·n_eu  →  rating = _shrink(cur', prior_EU(w=2), n', K=8)  [w = n'/(n'+8)]
    (αν n=0: sf/sa απο το prior, cur' = μεσος των eq, n' = w_in·n_eu· αν δεν υπαρχει prior:
     rating = cur'). Goals-πλευρες με Elo-αντικατασταση μενουν Elo (οπως live) → ανεπηρεαστες.
  t−1 prior-EU w=2 μενει οπως live. Opp_q ΔΕΝ μολυνεται απο κανενα εμπλουτισμο (οπως live).

ΠΡΟ-ΔΗΛΩΜΕΝΟ grid w_in ∈ {0.5, 1, 2}· επιλογη LOSO (train = οι αλλες σεζον) στο RPS 1Χ2 των
ΕΠΗΡΕΑΖΟΜΕΝΩΝ ματς (>=1 πλευρα με >=1 φετινο ευρωπαικο obs πριν το ματς). w_in=0 = sanity.
ΚΡΙΤΗΡΙΑ (α)/(β)/(γ) τυπωνονται ΠΡΙΝ τα αποτελεσματα. ΜΙΑ εκτελεση, κανενα tuning.
Output: euro_inseason_eu_out.txt (redirect) + euro_inseason_eu_preds.pkl. ΔΕΝ αγγιζει υπαρχοντα.
"""
import json, glob, sys, pickle, math, time
from datetime import datetime
import numpy as np, pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import picks
import euro_engine as EE
import red_modes
from euro_engine import (Engine, team_xg_raw, kodt, EU_SEASONS, EU_EVAL,
                         GAMMA_PLAYER, NS_CONST, EPS, w, _shrink)

T0 = time.time()
K = 8
RHO = 1.0
RIDGE = 3.0
MIN_FIT_N = 15
PEN_XG = 0.79
W_GRID = [0.5, 1.0, 2.0]          # προδηλωμενο — αναφερονται ολα
PRVSEA = {'2223': '2122', '2324': '2223', '2425': '2324', '2526': '2425'}

GRIFFIS_LGS = ['CzechFirstLeague', 'CroatiaHNL', 'SerbiaSuperLiga', 'RomaniaLigaI',
               'HungaryNBI', 'SlovakiaNikeLiga', 'IsraelLigatHaAl',
               'FinlandVeikkausliiga', 'LatviaVirsliga']
GRIFFIS_SKIP_SEA = {'2627', '2026'}

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
}

# ================================================================ V0/V4/V5 αναφορες
D0 = pickle.load(open('euro_preds.pkl', 'rb'))
E0 = D0['preds'][D0['preds'].sea.isin(EU_EVAL)].reset_index(drop=True)
POFF = D0['player_off']
MIDS_O = list(E0.mid)
V6 = pickle.load(open('euro_v6_preds.pkl', 'rb'))

def s_player(lg):
    return -GAMMA_PLAYER * POFF[lg] if lg in POFF else None

# ---------------- HFA LOSO (ιδιο με euro_expand_test) ----------------
xg_by_sea = {}
for sea in EU_SEASONS:
    de = json.load(open(f'data_Europe_{sea}.json', encoding='utf-8'))
    sh = sa = 0.0
    for m in de.values():
        if m['hs'] is None or m['as'] is None or not m['shots']:
            continue
        xh, xa = team_xg_raw(m)
        sh += xh; sa += xa
    xg_by_sea[sea] = (sh, sa)
HF = {}
for sea in EU_EVAL:
    sh = sum(v[0] for k, v in xg_by_sea.items() if k != sea)
    sa = sum(v[1] for k, v in xg_by_sea.items() if k != sea)
    HF[sea] = math.sqrt(sh / sa)

# ---------------- fitted LOSO fallback (ιδιος κωδικας) ----------------
def fit_fold(E, test_sea):
    T = E[E.sea != test_sea]
    hfv = T.sea.map(HF).values
    xgb_h = T['bxh8'].values * hfv
    xgb_a = T['bxa8'].values / hfv
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

def fitted_s(FIT, lg, fold):
    f = FIT[fold]
    s_ii = f['s'].get(lg if lg in f['lgs'] or lg == 'EPL' else 'OTH')
    return s_ii if s_ii is not None else f['s'].get('OTH', 0.0)

# ---------------- Griffis (ιδιος κωδικας) ----------------
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

# ---------------- GEngine (πιστη αντιγραφη euro_expand_test) ----------------
class GEngine(Engine):
    def __init__(self, griffis=None, verbose=False):
        self.griffis = griffis or {}
        super().__init__(verbose=verbose)

    def _build_domestic(self):
        import os
        files = {}
        for p in sorted(glob.glob('data_*.json')):
            base = os.path.basename(p)[:-5]
            parts = base.split('_')
            lg = '_'.join(parts[1:-1]); sea = parts[-1]
            if lg in EE.SKIP_LG or sea in EE.SKIP_SEA or not sea.isdigit():
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
                        _RA = red_modes.live_adj(m)     # 5/11/2026: η φορμουλα κοκκινων του live (5/10) — ως τοτε εδω ειχε μεινει η παλια +0.0083/λεπτο (uel_homefav_reds)
                        for is_home, tid, gf, dis_self, dis_opp in [
                                (1, hid, m['hs'], dis_home, dis_away),
                                (0, aid, m['as'], dis_away, dis_home)]:
                            a = agg[tid]
                            a = dict(a); a['np_raw'] *= _RA[tid]['fr']; a['np_comp'] *= _RA[tid]['fc']; a['ns'] *= _RA[tid]['fn']
                            red_xg = _RA[tid]['term']
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
                        g['ns_eff'] = np.maximum(g['ns'] + g['pen'] + g['red_xg'] / 0.10, 0.5 * (g['ns'] + g['pen']))
                if len(g) == 0:
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

def build_rows(eng, EU, griffis_keys):
    """Ιδιο με euro_expand_test.build_rows + hid/aid (χρειαζονται για το prior variant)."""
    recs = []
    for r in EU.itertuples():
        sth = eng.side_state(r.hid, r.date); sta = eng.side_state(r.aid, r.date)
        if sth is None or sta is None:
            continue
        rh = eng.rating_of(sth, K); ra = eng.rating_of(sta, K)
        SLh, XLh = eng.ruler(sth['lg'], sth['sea'], r.date)
        SLa, XLa = eng.ruler(sta['lg'], sta['sea'], r.date)
        Ss = (SLh * SLa) ** 0.5; Xs = (XLh * XLa) ** 0.5
        Axh, Dxh, SFh, SAh = rh; Axa, Dxa, SFa, SAa = ra
        att_h = math.log(max((SFh / SLh) * (Axh / XLh), EPS))
        leak_h = math.log(max((SAh / SLh) * (Dxh / XLh), EPS))
        att_a = math.log(max((SFa / SLa) * (Axa / XLa), EPS))
        leak_a = math.log(max((SAa / SLa) * (Dxa / XLa), EPS))
        lXs = math.log(Ss * Xs)
        def src(st):
            if (st['lg'], st['sea']) in griffis_keys: return 'griffis'
            return 'goals' if st['goal_only'] else 'shots'
        recs.append(dict(mid=r.mid, sea=r.sea, gh=r.gh, ga=r.ga, hid=r.hid, aid=r.aid,
                         lg_h=sth['lg'], lg_a=sta['lg'],
                         src_h=src(sth), src_a=src(sta),
                         att_h=att_h, leak_h=leak_h, att_a=att_a, leak_a=leak_a, lXs=lXs,
                         bxh8=math.exp(lXs + att_h + leak_a),
                         bxa8=math.exp(lXs + att_a + leak_h),
                         comp=r.comp, phase=r.phase, date=r.date,
                         hname=r.hname, aname=r.aname,
                         xgh_act=r.xgh_act, xga_act=r.xga_act))
    return pd.DataFrame(recs)

# ================================================================ MAIN

# ================================================================ MAIN
print('=' * 100)
print('ΦΕΤΙΝΑ ΕΥΡΩΠΑΪΚΑ ΣΤΟ ΦΕΤΙΝΟ RATING — baseline = live stack (V4 + prior-EU w=2 + γ−0.470 + κ1.16 UCL + X×0.85), LOSO')
print('=' * 100)
print('''
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραμμενα ΠΡΙΝ την εκτελεση — μια εκτελεση, κανενα tuning):
 (α) ΠΡΟΒΛΕΨΗ: RPS 1Χ2 των ΕΠΗΡΕΑΖΟΜΕΝΩΝ ματς καλυτερο (Δ<0) με το LOSO-επιλεγμενο w_in
     σε >=3 απο 4 σεζον ΚΑΙ pooled Δ<0.
 (β) BIAS: |μεσο bias επιθεσης| ΚΑΙ |μεσο bias αμυνας| των διορθωμενων φετινων ευρωπαικων obs
     (xGF_eq − xGF rating, xGA_eq − xGA rating, rating = baseline εγχωριο rating της ομαδας τη
     στιγμη του ευρωπαικου ματς) < 0.05 γκολ/ματς· ΚΑΙ pooled |μεσο(pred − actual margin)| στα
     επηρεαζομενα ματς (νεο) οχι χειροτερο απο του base κατα περισσοτερο απο 1 SE (SE του base).
 (γ) ROI ΦΡΟΥΡΟΣ: ROI των UCL picks (live κανονες) νεο >= base − 1 SE(base), ΚΑΙ στο Crown
     ΚΑΙ στο Pinnacle closing.
 PASS = α & β & γ. Αν το (β) αποτυχει, τα α/γ αναφερονται κανονικα.
''')

G = load_griffis()
GKEYS = set(G.keys())
print('[build] engine (+Griffis)...', flush=True)
eng2 = GEngine(griffis=G, verbose=False)
EU_ALL = eng2.load_europe()
EUe = EU_ALL[EU_ALL.sea.isin(EU_EVAL)].reset_index(drop=True)
B_ALL = build_rows(eng2, EUe, GKEYS)

# ---------------- αποδοσεις (ιδιος parser) ----------------
def parse_line(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None

BOOKS = {3: 'Crown', 31: 'SBOBET'}
SNAP = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r['cid'] not in BOOKS:
            continue
        rows = []
        for mt, u, g, dn in r.get('ah') or []:
            gl = parse_line(g)
            try:
                oh = float(u) + 1; oa = float(dn) + 1
            except (TypeError, ValueError):
                continue
            if gl is None or mt is None:
                continue
            rows.append((int(mt), -gl, oh, oa))
        if not rows:
            continue
        rows.sort()
        close = rows[-1]
        SNAP[(str(r['mid']), r['cid'])] = dict(close=close)

def has_odds(mid):
    return (mid, 3) in SNAP or (mid, 31) in SNAP

S_now = B_ALL[B_ALL.mid.map(has_odds)].sort_values(['date', 'mid']).reset_index(drop=True)
mids_now = set(S_now.mid); mids_v6 = set(V6['mids'])
extra = sorted(mids_now - mids_v6); gone = sorted(mids_v6 - mids_now)
if extra or gone:
    print(f'[ΠΡΟΣΟΧΗ] τωρινη καλυψη != euro_v6_preds: +{len(extra)} νεα, -{len(gone)} χαμενα mids '
          f'(τα δεδομενα ανανεωθηκαν μετα το v6 run). ΚΛΕΙΔΩΝΩ στο δειγμα του V6.')
    if gone:
        print(f'  ΧΑΜΕΝΑ (δεν καλυπτονται πια — ΣΤΑΜΑΤΩ αν >0): {gone[:10]}')
        sys.exit(1)
S = S_now[S_now.mid.isin(mids_v6)].reset_index(drop=True)
MIDS = list(S.mid); N = len(S)
assert list(V6['mids']) == MIDS, 'σειρα/συνολο mids != euro_v6_preds.pkl — ΣΤΑΜΑΤΩ'
print(f'Δειγμα: n={N} (κλειδωμενο στο euro_v6_preds.pkl)')

# ---------------- ΠΑΓΩΜΕΝΑ FITS στο παλιο 1158 (ιδιος κωδικας) ----------------
GH_O = E0.gh.values; GA_O = E0.ga.values
SEA_O = E0.sea.values
B2o = B_ALL.set_index('mid').reindex(MIDS_O)
for c, v0 in [('bxh8', E0.bxh8.values), ('bxa8', E0.bxa8.values)]:
    B2o[c] = B2o[c].fillna(pd.Series(v0, index=MIDS_O))
B2o['lg_h'] = B2o['lg_h'].fillna(pd.Series(E0.lg_h.values, index=MIDS_O))
B2o['lg_a'] = B2o['lg_a'].fillna(pd.Series(E0.lg_a.values, index=MIDS_O))
B2o['sea'] = pd.Series(SEA_O, index=MIDS_O)
B2o['gh'] = GH_O; B2o['ga'] = GA_O
FIT2 = {sea: fit_fold(B2o.reset_index(), sea) for sea in EU_EVAL}

ce = pd.read_csv('clubelo_europe.csv')
ce['mid'] = ce['mid'].astype(str)
ELO = {r.mid: (r.home_elo, r.away_elo) for r in ce.itertuples()}
ath_o = B2o.att_h.values; lkh_o = B2o.leak_h.values
ata_o = B2o.att_a.values; lka_o = B2o.leak_a.values
srh_o = B2o.src_h.values; sra_o = B2o.src_a.values
LGH_O = B2o.lg_h.values; LGA_O = B2o.lg_a.values
eh_o = np.array([ELO.get(m, (np.nan, np.nan))[0] for m in MIDS_O], float)
ea_o = np.array([ELO.get(m, (np.nan, np.nan))[1] for m in MIDS_O], float)
has_comp_o = ~np.isnan(B2o.lXs.values)

CAL = {}
for fold in EU_EVAL:
    xs = []; ys = []
    tr = (SEA_O != fold) & has_comp_o
    for i in np.where(tr)[0]:
        for (srcv, lg, at, lk, el) in [(srh_o[i], LGH_O[i], ath_o[i], lkh_o[i], eh_o[i]),
                                       (sra_o[i], LGA_O[i], ata_o[i], lka_o[i], ea_o[i])]:
            if srcv == 'goals' or (isinstance(el, float) and np.isnan(el)) or lg not in POFF:
                continue
            ys.append(RHO * s_player(lg) + 0.5 * (at - lk))
            xs.append(el / 100.0)
    xs = np.array(xs); ys = np.array(ys)
    b = np.cov(xs, ys)[0, 1] / np.var(xs)
    a = ys.mean() - b * xs.mean()
    CAL[fold] = (a, b)

# ---------------- offset ιεραρχια (ιδια) ----------------
lo = json.load(open('league_offsets.json', encoding='utf-8'))
id2off = {}
for k_, v in lo.items():
    if '#' in k_:
        try:
            id2off[int(k_.rsplit('#', 1)[1])] = (k_, float(v))
        except ValueError:
            pass
samp_lgs = sorted(set(S.lg_h) | set(S.lg_a))
bridge2 = {}
for lg in samp_lgs:
    if lg in POFF:
        continue
    lid = LID.get(lg)
    if lid is not None and lid in id2off:
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

def s_v4(lg, fold):
    sp = s_player(lg)
    if sp is not None:
        return sp
    if lg in bridge2:
        return -GAMMA_PLAYER * bridge2[lg][1]
    if lg in off_elo:
        return -GAMMA_PLAYER * off_elo[lg]
    return fitted_s(FIT2, lg, fold)

# ================================================================ arrays δειγματος
SEA = S.sea.values
GH = S.gh.values; GA = S.ga.values; GD = GH - GA
HID = S.hid.values; AID = S.aid.values
DATES = list(S.date)
COMP = S.comp.values
HFV = pd.Series(SEA).map(HF).values
src_h = S.src_h.values; src_a = S.src_a.values
LGH = S.lg_h.values; LGA = S.lg_a.values
eh = np.array([ELO.get(m, (np.nan, np.nan))[0] for m in MIDS], float)
ea = np.array([ELO.get(m, (np.nan, np.nan))[1] for m in MIDS], float)

# ---------------- side_state cache ----------------
_SS = {}
def SS(tid, d):
    key = (tid, d)
    if key not in _SS:
        _SS[key] = eng2.side_state(tid, d)
    return _SS[key]

# ================================================================ ΕΥΡΩΠΑΪΚΕΣ ΠΑΡΑΤΗΡΗΣΕΙΣ -> PRIOR
b_blend = picks.blend_at(None)

EU_BY_TEAM = {}
for r in EU_ALL.itertuples():
    if isinstance(r.xgh_act, float) and math.isnan(r.xgh_act):
        continue
    EU_BY_TEAM.setdefault((r.sea, r.hid), []).append((r.mid, r.date, 1, r.xgh_act, r.xga_act, r.gh, r.ga, r.aid, r.comp))
    EU_BY_TEAM.setdefault((r.sea, r.aid), []).append((r.mid, r.date, 0, r.xga_act, r.xgh_act, r.ga, r.gh, r.hid, r.comp))

def opp_q(oid, mid, is_opp_home, d, fold):
    """(q_def, q_att, used_elo) του αντιπαλου στη στιγμη d, στον χωρο του V4· None αν χωρις rating."""
    st = SS(oid, d)
    if st is None:
        return None
    Ax, Dx, SF, SA = eng2.rating_of(st, K)
    SL, XL = eng2.ruler(st['lg'], st['sea'], d)
    att = math.log(max((SF / SL) * (Ax / XL), EPS))
    leak = math.log(max((SA / SL) * (Dx / XL), EPS))
    src = 'griffis' if (st['lg'], st['sea']) in GKEYS else ('goals' if st['goal_only'] else 'shots')
    s_o = s_v4(st['lg'], fold)
    used_elo = False
    if src == 'goals':
        el = ELO.get(mid, (np.nan, np.nan))[0 if is_opp_home else 1]
        try:
            el = float(el)
        except (TypeError, ValueError):
            el = float('nan')
        if not math.isnan(el):
            a_f, b_f = CAL[fold]
            u = a_f + b_f * el / 100.0 - RHO * s_o
            att, leak = u, -u
            used_elo = True
    lnXmO = math.log(max(SL * XL, EPS))
    return (0.5 * lnXmO + leak - RHO * s_o, 0.5 * lnXmO + att + RHO * s_o, used_elo)

# προ-περασμα: κλειδια (fold, tid, lg, sea_dom) των πλευρων του δειγματος με prior
TEAMKEYS = {fold: set() for fold in EU_EVAL}
for i in range(N):
    for tid in (HID[i], AID[i]):
        st = SS(tid, DATES[i])
        if st is not None and st['prior'] is not None:
            TEAMKEYS[SEA[i]].add((tid, st['lg'], st['sea']))

# comp-season μεσος (fallback για αντιπαλο χωρις rating)
CMEAN = {}
for fold in EU_EVAL:
    p_eu = PRVSEA[fold]
    acc = {}
    for r in EU_ALL[EU_ALL.sea == p_eu].itertuples():
        for oid, ish in [(r.hid, True), (r.aid, False)]:
            q = opp_q(oid, r.mid, ish, r.date, fold)
            if q is not None:
                acc.setdefault(r.comp, []).append((q[0], q[1]))
    CMEAN[fold] = {c: (float(np.mean([v[0] for v in vv])), float(np.mean([v[1] for v in vv])))
                   for c, vv in acc.items()}

# κατασκευη εμπλουτισμενων priors
ENR = {wg: {} for wg in W_GRID}
NEU = {}
n_fb = n_elo = n_obs_tot = 0
EX_ROWS = []
for fold in EU_EVAL:
    p_eu = PRVSEA[fold]
    lhf = math.log(HF[fold])
    for (tid, lg, sea_dom) in TEAMKEYS[fold]:
        p_dom = eng2.PRV.get((lg, sea_dom))
        if p_dom is None:
            continue
        prior = eng2.PRIOR[(lg, p_dom)].get(tid)
        if prior is None:
            continue
        n_dom = len(eng2.H[(lg, p_dom)][tid]['dates'])
        sT = s_v4(lg, fold)
        obs = []
        for (mid, d, ish, xgf, xga, gf, ga, oid, comp) in EU_BY_TEAM.get((p_eu, tid), ()):
            q = opp_q(oid, mid, ish == 0, d, fold)
            if q is None:
                cm = CMEAN[fold].get(comp)
                if cm is None:
                    continue
                qd, qa = cm
                n_fb += 1
            else:
                qd, qa, uel = q
                n_elo += int(uel)
            SLt, XLt = eng2.ruler(lg, p_dom, d)
            lnXmT = math.log(max(SLt * XLt, EPS))
            hterm = lhf if ish else -lhf
            raw_att = b_blend * xgf + (1 - b_blend) * gf
            raw_def = b_blend * xga + (1 - b_blend) * ga
            adjF = math.exp(0.5 * lnXmT - qd - RHO * sT - hterm)
            adjA = math.exp(0.5 * lnXmT - qa + RHO * sT + hterm)
            obs.append((raw_att * adjF, raw_def * adjA))
        NEU[(fold, tid, lg, sea_dom)] = len(obs)
        n_obs_tot += len(obs)
        if not obs:
            continue
        Patt = prior[0] * prior[2]; Pdef = prior[1] * prior[3]
        s_att = sum(o[0] for o in obs); s_def = sum(o[1] for o in obs)
        for wg in W_GRID:
            na = (n_dom * Patt + wg * s_att) / (n_dom + wg * len(obs))
            nd = (n_dom * Pdef + wg * s_def) / (n_dom + wg * len(obs))
            ENR[wg][(fold, tid, lg, sea_dom)] = (na / max(prior[2], EPS), nd / max(prior[3], EPS),
                                                 prior[2], prior[3])
        na1 = ENR[1.0][(fold, tid, lg, sea_dom)]
        EX_ROWS.append(dict(fold=fold, tid=tid, lg=lg, name=eng2.id2name.get(tid, str(tid)),
                            n_dom=n_dom, n_eu=len(obs),
                            att0=Patt, att1=na1[0] * na1[2], def0=Pdef, def1=na1[1] * na1[3],
                            eu_att=s_att / len(obs), eu_def=s_def / len(obs)))

nk = sum(len(v) for v in TEAMKEYS.values())
enr_k = len(EX_ROWS)
neu_vals = [NEU[k] for k in NEU]
print(f'\nΟμαδα-fold πλευρες με prior: {nk}  με >=1 περσινο ευρωπαικο obs: {enr_k}  '
      f'obs συνολο: {n_obs_tot}  (fallback comp-mean: {n_fb}, goals→Elo αντιπαλοι: {n_elo})')
hist = {b: sum(1 for v in neu_vals if lo_ <= v <= hi_)
        for b, lo_, hi_ in [('0', 0, 0), ('1-3', 1, 3), ('4-7', 4, 7), ('8+', 8, 999)]}
print(f'Κατανομη n_eu ανα ομαδα-fold: ' + '  '.join(f'{k}: {v}' for k, v in hist.items()))


# ####################################################################################
# ======================= ΝΕΟ ΤΜΗΜΑ: ΦΕΤΙΝΑ ΕΥΡΩΠΑΪΚΑ ΣΤΟ ΦΕΤΙΝΟ RATING ==================
# ####################################################################################
from collections import Counter

W_PRIOR = 2.0                    # live prior-EU
W_IN_GRID = [0.5, 1.0, 2.0]      # προδηλωμενο
GAMMA_LG_DEFLATE = -0.470        # live
EU_DRAW_SCALE = 0.85             # live
UCL_FAV_SCALE = 1.16             # live (UCL, φαβορι, νεο format)
NEW_FMT = {'2425', '2526'}
CLOSE_TOL = 900

# ---------------- γυρος/φαση ----------------
_ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
ROUND = {str(m['mid']): str(m['round']) for v in _ef.values() for m in v}
RND = np.array([ROUND.get(m, '?') for m in MIDS])
def phase_of(r):
    if r.isdigit():
        return 'LP md1-2' if int(r) <= 2 else 'LP md3-8'
    return 'KO'
PH = np.array([phase_of(r) for r in RND])
PHASES = ['LP md1-2', 'LP md3-8', 'KO']
FMm = (src_h == 'shots') & (src_a == 'shots')

# ---------------- walk-forward comp-season μεσος q (fallback αντιπαλου χωρις rating) ----------------
QSEA = {}
for fold in EU_EVAL:
    for r in EU_ALL[EU_ALL.sea == fold].itertuples():
        for oid, ish in [(r.hid, True), (r.aid, False)]:
            q = opp_q(oid, r.mid, ish, r.date, fold)
            if q is not None:
                QSEA.setdefault((fold, r.comp), []).append((r.date, q[0], q[1]))
_CMW = {}
def cmean_wf(fold, comp, d):
    key = (fold, comp, d)
    if key not in _CMW:
        vals = [x for x in QSEA.get((fold, comp), []) if x[0] < d]
        if vals:
            _CMW[key] = ((float(np.mean([v[1] for v in vals])), float(np.mean([v[2] for v in vals]))), 'wf')
        else:
            _CMW[key] = (CMEAN[fold].get(comp), 'prev')
    return _CMW[key]

# ---------------- φετινες ευρωπαικες παρατηρησεις ----------------
_OBS = {}
OBS_SRC = Counter()
def eq_obs(tid, rec, fold, lg, sea):
    mid, d_eu, ish, xgf, xga, gf, ga, oid, comp = rec
    key = (tid, mid, fold, lg, sea)
    if key in _OBS:
        return _OBS[key]
    q = opp_q(oid, mid, ish == 0, d_eu, fold)
    if q is None:
        cm, how = cmean_wf(fold, comp, d_eu)
        if cm is None:
            _OBS[key] = None
            OBS_SRC['drop'] += 1
            return None
        qd, qa = cm
        src = 'fallback_' + how
    else:
        qd, qa, uel = q
        src = 'elo' if uel else 'rated'
    OBS_SRC[src] += 1
    SLt, XLt = eng2.ruler(lg, sea, d_eu)
    lnXmT = math.log(max(SLt * XLt, EPS))
    sT = s_v4(lg, fold)
    lhf = math.log(HF[fold])
    hterm = lhf if ish else -lhf
    raw_att = b_blend * xgf + (1 - b_blend) * gf
    raw_def = b_blend * xga + (1 - b_blend) * ga
    o = (raw_att * math.exp(0.5 * lnXmT - qd - RHO * sT - hterm),
         raw_def * math.exp(0.5 * lnXmT - qa + RHO * sT + hterm), d_eu, comp)
    _OBS[key] = o
    return o

def inseason(tid, d, fold, st):
    out = []
    for rec in EU_BY_TEAM.get((fold, tid), ()):
        if rec[1] < d:
            o = eq_obs(tid, rec, fold, st['lg'], st['sea'])
            if o is not None:
                out.append((rec[0], o))
    return out

# ---------------- ratings ----------------
def prior_enr(st, tid, fold):
    pr = st['prior']
    if pr is not None:
        pr = ENR[W_PRIOR].get((fold, tid, st['lg'], st['sea']), pr)
    return pr

def rate_base(st, tid, fold, d):
    """ΙΔΙΟ με το rate() του prior-EU predict με wg=2 (live)."""
    pr = prior_enr(st, tid, fold)
    if st['cur'] is None:
        return pr
    if pr is None:
        return st['cur']
    return _shrink(st['cur'], pr, st['n'], K)

USED = set()
def make_rate_new(w_in, track=False):
    def rate_new(st, tid, fold, d):
        pr = prior_enr(st, tid, fold)
        cur, n = st['cur'], st['n']
        obs = inseason(tid, d, fold, st)
        if obs:
            ne = len(obs)
            den = n + w_in * ne
            if den > 0:
                sA = sum(o[1][0] for o in obs); sD = sum(o[1][1] for o in obs)
                if cur is not None:
                    sf, sa = cur[2], cur[3]
                    ca, cd = cur[0] * sf, cur[1] * sa
                else:
                    sf, sa = pr[2], pr[3]
                    ca = cd = 0.0
                na_ = (n * ca + w_in * sA) / den
                nd_ = (n * cd + w_in * sD) / den
                cur = (na_ / max(sf, EPS), nd_ / max(sa, EPS), sf, sa)
                n = den
            if track:
                for mid_, _o in obs:
                    USED.add((tid, mid_, fold, st['lg'], st['sea']))
        if cur is None:
            return pr
        if pr is None:
            return cur
        return _shrink(cur, pr, n, K)
    return rate_new

def predict_arm(ratefn):
    """Σωμα = predict() του euro_prior_eu_test, με εξωτερικη συναρτηση rating."""
    LHv = np.empty(N); LAv = np.empty(N)
    for i in range(N):
        fold = SEA[i]; d = DATES[i]
        sth = SS(HID[i], d); sta = SS(AID[i], d)
        SLh, XLh = eng2.ruler(sth['lg'], sth['sea'], d)
        SLa, XLa = eng2.ruler(sta['lg'], sta['sea'], d)
        Ss = (SLh * SLa) ** 0.5; Xs = (XLh * XLa) ** 0.5
        lXs = math.log(Ss * Xs)
        Axh, Dxh, SFh, SAh = ratefn(sth, HID[i], fold, d)
        Axa, Dxa, SFa, SAa = ratefn(sta, AID[i], fold, d)
        att_h = math.log(max((SFh / SLh) * (Axh / XLh), EPS))
        leak_h = math.log(max((SAh / SLh) * (Dxh / XLh), EPS))
        att_a = math.log(max((SFa / SLa) * (Axa / XLa), EPS))
        leak_a = math.log(max((SAa / SLa) * (Dxa / XLa), EPS))
        D_ = s_v4(LGH[i], fold) - s_v4(LGA[i], fold)
        ah, lh_ = att_h, leak_h
        aa, la_ = att_a, leak_a
        a_f, b_f = CAL[fold]
        if src_h[i] == 'goals' and not np.isnan(eh[i]):
            sig = a_f + b_f * eh[i] / 100.0
            u = sig - RHO * s_v4(LGH[i], fold)
            ah, lh_ = u, -u
        if src_a[i] == 'goals' and not np.isnan(ea[i]):
            sig = a_f + b_f * ea[i] / 100.0
            u = sig - RHO * s_v4(LGA[i], fold)
            aa, la_ = u, -u
        bxh = math.exp(lXs + ah + la_)
        bxa = math.exp(lXs + aa + lh_)
        LHv[i] = bxh * HFV[i] * math.exp(RHO * D_)
        LAv[i] = bxa / HFV[i] * math.exp(-RHO * D_)
    return LHv, LAv

# ---------------- live stack (deflate + κ) ----------------
D_ARR = np.array([s_v4(LGH[i], SEA[i]) - s_v4(LGA[i], SEA[i]) for i in range(N)])
C_ARR = GAMMA_LG_DEFLATE * D_ARR
KSCOPE = (COMP == 'ChampionsLeague') & np.isin(SEA, list(NEW_FMT))
def live_stack(LH, LA):
    lh = np.maximum(LH - C_ARR / 2.0, 0.05); la = np.maximum(LA + C_ARR / 2.0, 0.05)
    fav_h = lh >= la
    lh2 = np.where(KSCOPE & fav_h, lh * UCL_FAV_SCALE, lh)
    la2 = np.where(KSCOPE & ~fav_h, la * UCL_FAV_SCALE, la)
    return lh2, la2

# ================================================================ ΠΡΟΒΛΕΨΕΙΣ
t1 = time.time()
RAW = {}
RAW['base'] = predict_arm(rate_base)
RAW[0.0] = predict_arm(make_rate_new(0.0))
for wi in W_IN_GRID:
    RAW[wi] = predict_arm(make_rate_new(wi, track=(wi == 1.0)))
print(f'[predict] {len(RAW)} αρμοι [{time.time()-t1:.0f}s]')

# ---------------- SANITY ----------------
print('\n' + '=' * 100)
print('SANITY')
print('=' * 100)
d0 = max(np.abs(RAW[0.0][0] - RAW['base'][0]).max(), np.abs(RAW[0.0][1] - RAW['base'][1]).max())
print(f'[SANITY 1] w_in=0 (γενικη διαδρομη συγχωνευσης, χωρις βραχυκυκλωμα) vs baseline: max|Δλ| = {d0:.2e}')
if d0 > 1e-12:
    print('ΣΤΑΜΑΤΩ: το w_in=0 ΔΕΝ αναπαραγει το baseline.')
    sys.exit(1)
W2P = pickle.load(open('euro_v6w2_preds.pkl', 'rb'))
assert list(W2P['mids']) == MIDS
dw2 = max(np.abs(RAW['base'][0] - np.asarray(W2P['lh'])).max(), np.abs(RAW['base'][1] - np.asarray(W2P['la'])).max())
dw2m = (np.abs(RAW['base'][0] - np.asarray(W2P['lh'])).mean() + np.abs(RAW['base'][1] - np.asarray(W2P['la'])).mean()) / 2
LHw0, LAw0 = predict_arm(lambda st, tid, fold, d: (st['prior'] if st['cur'] is None else
                         (st['cur'] if st['prior'] is None else _shrink(st['cur'], st['prior'], st['n'], K))))
dv6 = max(np.abs(LHw0 - np.asarray(V6['lh'])).max(), np.abs(LAw0 - np.asarray(V6['la'])).max())
print(f'[SANITY 2] baseline (w=2, pre-γ/κ) vs euro_v6w2_preds.pkl (8/9): max|Δλ| = {dw2:.2e}, mean {dw2m:.2e}')
print(f'[SANITY 3] prior-EU w=0 vs euro_v6_preds.pkl: max|Δλ| = {dv6:.2e} (18/9 γνωστο data drift 3.23e-02 στο αθικτο πρωτοτυπο)')
print('  → Τα 2/3 ειναι πληροφοριακα (data refresh μετα τα pickles)· η συγκριση base/νεο ειναι paired στα ΙΔΙΑ τρεχοντα δεδομενα.')

# ================================================================ n_in / επηρεαζομενα
def n_in(i, tid):
    st = SS(tid, DATES[i])
    return len(inseason(tid, DATES[i], SEA[i], st))
NIH = np.array([n_in(i, HID[i]) for i in range(N)])
NIA = np.array([n_in(i, AID[i]) for i in range(N)])
AFF = (NIH >= 1) | (NIA >= 1)
print(f'\nΦετινες ευρωπαικες obs (μοναδικες ομαδα×ματς×κατασταση): {len(_OBS)}  πηγες q αντιπαλου: ' +
      ', '.join(f'{k}: {v}' for k, v in OBS_SRC.most_common()))
print(f'Επηρεαζομενα ματς (>=1 πλευρα με >=1 φετινο obs): {int(AFF.sum())}/{N}')
for s_ in EU_EVAL:
    ms = SEA == s_
    print(f'  {s_}: ' + '  '.join(f'{p}: {int((AFF & ms & (PH == p)).sum())}/{int((ms & (PH == p)).sum())}'
                                   for p in PHASES))
print(f'  κατανομη max(n_in) στα επηρεαζομενα: ' +
      ', '.join(f'{lo_}-{hi_}: {int((AFF & (np.maximum(NIH, NIA) >= lo_) & (np.maximum(NIH, NIA) <= hi_)).sum())}'
                for lo_, hi_ in [(1, 2), (3, 5), (6, 8), (9, 20)]))

# ================================================================ ΜΕΤΡΙΚΕΣ
GDf = GD.astype(float)
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))

def eu_dist(lh, la, scale):
    dist = picks.gd_dist(max(lh, 0.05), max(la, 0.05))
    px = dist.get(0, 0.0)
    if px <= 0 or px >= 1 or scale == 1.0:
        return dist
    k = (1.0 - scale * px) / (1.0 - px)
    return {g: (p * scale if g == 0 else p * k) for g, p in dist.items()}

def rps_arr(LH, LA):
    R = np.zeros(N)
    for i in range(N):
        dist = eu_dist(LH[i], LA[i], EU_DRAW_SCALE)
        ph = sum(p for k_, p in dist.items() if k_ > 0)
        pdw = dist.get(0, 0.0)
        o = OUT3[i]
        R[i] = 0.5 * ((ph - (o == 0)) ** 2 + (ph + pdw - (o <= 1)) ** 2)
    return R

LIVE = {k: live_stack(*v) for k, v in RAW.items()}
RPS = {k: rps_arr(*v) for k, v in LIVE.items()}
MARG = {k: v[0] - v[1] for k, v in LIVE.items()}
MAE = {k: np.abs(MARG[k] - GDf) for k in LIVE}
chg = (np.abs(LIVE[1.0][0] - LIVE['base'][0]) + np.abs(LIVE[1.0][1] - LIVE['base'][1])) > 1e-12
print(f'  ματς με πραγματικη αλλαγη λ (w_in=1): {int(chg.sum())} (επηρεαζομενα χωρις αλλαγη = goals+Elo πλευρες)')

# ---------------- LOSO επιλογη w_in ----------------
CHOSEN = {}
print('\n' + '=' * 100)
print('LOSO ΕΠΙΛΟΓΗ w_in (train = αλλες 3 σεζον, RPS επηρεαζομενων)')
print('=' * 100)
for fold in EU_EVAL:
    tr = AFF & (SEA != fold)
    sc = {wi: RPS[wi][tr].mean() for wi in W_IN_GRID}
    CHOSEN[fold] = min(sc, key=sc.get)
    print(f'  fold {fold}: ' + '  '.join(f'w={wi}: {sc[wi]:.5f}' for wi in W_IN_GRID) + f'  → w_in={CHOSEN[fold]}')
LH_L = np.empty(N); LA_L = np.empty(N)
for fold in EU_EVAL:
    m = SEA == fold
    LH_L[m] = LIVE[CHOSEN[fold]][0][m]; LA_L[m] = LIVE[CHOSEN[fold]][1][m]
LIVE['loso'] = (LH_L, LA_L)
RPS['loso'] = np.array([RPS[CHOSEN[SEA[i]]][i] for i in range(N)])
MARG['loso'] = LH_L - LA_L
MAE['loso'] = np.abs(MARG['loso'] - GDf)

def dse(d):
    n = len(d)
    if n < 2:
        return float('nan'), float('nan')
    return float(d.mean()), float(d.std(ddof=1) / math.sqrt(n))

# ---------------- ΠΙΝΑΚΑΣ 1: RPS επηρεαζομενων ανα σεζον ----------------
print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 1: RPS 1Χ2 (live stack) — ΕΠΗΡΕΑΖΟΜΕΝΑ ματς, ανα σεζον· Δ = νεο − base (paired ±SE)')
print('=' * 100)
ARMS = ['loso'] + W_IN_GRID
print(f'  {"σεζον":>7s} {"n":>5s} {"RPS base":>9s} | ' + ' | '.join(f'{("LOSO" if a == "loso" else "w="+str(a)):>22s}' for a in ARMS))
per_sea_delta = {}
for s_ in EU_EVAL + ['POOLED']:
    mk = AFF & ((SEA == s_) if s_ != 'POOLED' else np.ones(N, bool))
    cells = []
    for a in ARMS:
        m_, se_ = dse(RPS[a][mk] - RPS['base'][mk])
        cells.append(f'{RPS[a][mk].mean():.4f} Δ{m_*1000:+6.2f}±{se_*1000:4.2f}')
        if a == 'loso':
            per_sea_delta[s_] = (m_, se_, int(mk.sum()))
    lab = s_ + (f' w={CHOSEN[s_]}' if s_ in CHOSEN else '')
    print(f'  {lab:>7s} {int(mk.sum()):5d} {RPS["base"][mk].mean():9.4f} | ' + ' | '.join(f'{c:>22s}' for c in cells))
print('  (Δ σε ×10⁻³· LOSO: καθε σεζον με το w_in που διαλεξαν οι αλλες 3)')

print('\n--- ΟΛΑ τα ματς (επηρεαζομενα + μη) ---')
for s_ in EU_EVAL + ['POOLED']:
    mk = (SEA == s_) if s_ != 'POOLED' else np.ones(N, bool)
    m_, se_ = dse(RPS['loso'][mk] - RPS['base'][mk])
    mm, sm = dse(MAE['loso'][mk] - MAE['base'][mk])
    print(f'  {s_:>7s} n={int(mk.sum()):5d}  RPS {RPS["base"][mk].mean():.4f}→{RPS["loso"][mk].mean():.4f} '
          f'Δ{m_*1000:+6.2f}±{se_*1000:4.2f}  |  MAE {MAE["base"][mk].mean():.3f}→{MAE["loso"][mk].mean():.3f} '
          f'Δ{mm:+.4f}±{sm:.4f}')

# ---------------- ΠΙΝΑΚΑΣ 2: ανα φαση ----------------
print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 2: ανα φαση (LOSO w_in) — RPS & MAE margin, ΟΛΑ / ΕΠΗΡΕΑΖΟΜΕΝΑ')
print('  (LP md3-8 = ομιλος md3-6 στο παλιο format· KO = playoff/1/16 κ.ε.)')
print('=' * 100)
for p in PHASES:
    for lab, extra in [('ολα', np.ones(N, bool)), ('επηρ.', AFF)]:
        mk = (PH == p) & extra
        if mk.sum() < 2:
            print(f'  {p:>9s} {lab:>6s} n={int(mk.sum())}')
            continue
        m_, se_ = dse(RPS['loso'][mk] - RPS['base'][mk])
        mm, sm = dse(MAE['loso'][mk] - MAE['base'][mk])
        print(f'  {p:>9s} {lab:>6s} n={int(mk.sum()):5d}  RPS {RPS["base"][mk].mean():.4f}→{RPS["loso"][mk].mean():.4f} '
              f'Δ{m_*1000:+6.2f}±{se_*1000:4.2f}  |  MAE {MAE["base"][mk].mean():.3f}→{MAE["loso"][mk].mean():.3f} '
              f'Δ{mm:+.4f}±{sm:.4f}')
print('\n--- επηρεαζομενα ανα φαση × σεζον (ΔRPS ×10⁻³ LOSO, n) ---')
for p in PHASES[1:]:
    cells = []
    for s_ in EU_EVAL:
        mk = (PH == p) & AFF & (SEA == s_)
        m_, se_ = dse(RPS['loso'][mk] - RPS['base'][mk])
        cells.append(f'{s_}: {m_*1000:+6.2f}±{se_*1000:4.2f} (n={int(mk.sum())})')
    print(f'  {p:>9s}: ' + '  '.join(cells))

# ================================================================ BIAS
print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 3: BIAS — διορθωμενες φετινες ευρωπαικες obs vs baseline εγχωριο rating τη στιγμη του ματς')
print('  bias_att = xGF_eq − xGF_rating (Ax·SF), bias_def = xGA_eq − xGA_rating (Dx·SA), γκολ/ματς')
print('  (μοναδικες obs που χρησιμοποιηθηκαν σε προβλεψεις του δειγματος· rating = rate_base στη στιγμη d_eu)')
print('=' * 100)
BROWS = []
n_skip = 0
for (tid, mid_, fold, lg, sea) in USED:
    o = _OBS[(tid, mid_, fold, lg, sea)]
    d_eu, comp = o[2], o[3]
    st = SS(tid, d_eu)
    if st is None or st['lg'] != lg or st['sea'] != sea:
        n_skip += 1
        continue
    r = rate_base(st, tid, fold, d_eu)
    BROWS.append(dict(fold=fold, comp=comp, lg=lg, att=o[0] - r[0] * r[2], dfn=o[1] - r[1] * r[3],
                      eq_att=o[0], eq_def=o[1], r_att=r[0] * r[2], r_def=r[1] * r[3]))
BR = pd.DataFrame(BROWS)
print(f'  obs: {len(BR)} (παραλειφθηκαν {n_skip}: αλλη εγχωρια σεζον στη στιγμη του ευρωπαικου ματς — ημερολογιακες λιγκες)')
def brow(lab, df):
    if len(df) < 2:
        print(f'  {lab:>18s} n={len(df)}'); return
    a, sa_ = dse(df.att.values); d_, sd_ = dse(df.dfn.values)
    print(f'  {lab:>18s} n={len(df):5d} | att: eq {df.eq_att.mean():.3f} vs rating {df.r_att.mean():.3f} → bias {a:+.3f}±{sa_:.3f}'
          f' | def: eq {df.eq_def.mean():.3f} vs rating {df.r_def.mean():.3f} → bias {d_:+.3f}±{sd_:.3f}')
brow('POOLED', BR)
for s_ in EU_EVAL:
    brow(s_, BR[BR.fold == s_])
for c_ in ['ChampionsLeague', 'EuropaLeague', 'ConferenceLeague']:
    brow(c_, BR[BR.comp == c_])
TOP7 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie'}
brow('ομαδα top7', BR[BR.lg.isin(TOP7)])
brow('ομαδα αλλη λιγκα', BR[~BR.lg.isin(TOP7)])
BIAS_ATT = float(BR.att.mean()); BIAS_DEF = float(BR.dfn.mean())

print('\n--- margin: μεσο προβλεπομενο vs πραγματικο (επηρεαζομενα, γηπεδουχος-οπτικη) ---')
MB = {}
for a in ['base', 'loso'] + W_IN_GRID:
    e = MARG[a][AFF] - GDf[AFF]
    m_, se_ = dse(e)
    MB[a] = (m_, se_)
    print(f'  {("w="+str(a)) if a not in ("base","loso") else a:>6s}: pred {MARG[a][AFF].mean():+.3f} vs act {GDf[AFF].mean():+.3f} → '
          f'pred−act {m_:+.4f}±{se_:.4f}')
# πληροφοριακο: κατευθυνση της μετατοπισης (η «οπτικη πλευρας» αλληλοαναιρειται οταν εχουν obs
# και οι δυο πλευρες → αντικατασταθηκε με αυτο, καθαρα πληροφοριακο, εκτος κριτηριων)
dm_ = MARG['loso'] - MARG['base']
res_ = GDf - MARG['base']
mk_ = AFF & (np.abs(dm_) > 1e-9)
sg_ = np.sign(dm_[mk_]) * res_[mk_]
m_, se_ = dse(sg_)
slope = float((dm_[mk_] * res_[mk_]).sum() / (dm_[mk_] ** 2).sum())
sres = res_[mk_] - slope * dm_[mk_]
sslope = float(math.sqrt((sres ** 2).sum() / (mk_.sum() - 1) / (dm_[mk_] ** 2).sum()))
print(f'  (πληροφοριακο) κατευθυνση μετατοπισης LOSO: n={int(mk_.sum())}, μεσο |Δmargin| {np.abs(dm_[mk_]).mean():.3f}· '
      f'E[sign(Δ)·(act−pred_base)] = {m_:+.4f}±{se_:.4f}· κλιση (act−pred_base) ~ Δmargin = {slope:+.2f}±{sslope:.2f} '
      f'(1 = σωστο μεγεθος, 0 = θορυβος)')

# ================================================================ ROI (live κανονες, AH)
print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 4: ROI flat 1u — LIVE κανονες euro_shadow_scan (AH μονο· overs ΔΕΝ υποστηριζονται απο το harness)')
print('  FotMob+FotMob · ζωνη 1.70-2.10 · fav γραμμη<=−0.5 / dog >=+0.5 · UCL fav@10 dog@4 · UEL/UECL dog@10 fav@4')
print('  pricing: λ live stack + P(X)×0.85 + picks.p_cover/settle (MARGIN 0.03)· closing Crown (<=KO+15′) & Pinnacle (toa_pin_hist)')
print('=' * 100)
KO = {}
for m, d in zip(MIDS, DATES):
    try:
        KO[m] = int(pd.Timestamp(d).tz_localize('UTC').timestamp())
    except Exception:
        pass
CROWN = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r['cid'] != 3:
            continue
        mid = str(r['mid']); ko = KO.get(mid)
        if ko is None:
            continue
        rows = []
        for mt, u, g, dn in r.get('ah') or []:
            gl = parse_line(g)
            try:
                oh = float(u) + 1; oa = float(dn) + 1
            except (TypeError, ValueError):
                continue
            if gl is None or mt is None:
                continue
            rows.append((int(mt), -gl, oh, oa))
        rows = sorted(x for x in rows if x[0] <= ko + CLOSE_TOL)
        if rows:
            CROWN[mid] = rows[-1][1:]
PIN = {}
for line in open('toa_pin_hist.jsonl', encoding='utf-8'):
    r = json.loads(line)
    if r.get('line') is None or r.get('oh') is None or r.get('oa') is None:
        continue
    PIN[str(r['mid'])] = (float(r['line']), float(r['oh']), float(r['oa']))
BOOKS_ROI = {'Crown': CROWN, 'Pinnacle': PIN}
print(f'  closing διαθεσιμο στο δειγμα: Crown {sum(1 for m in MIDS if m in CROWN)}, Pinnacle {sum(1 for m in MIDS if m in PIN)} / {N}')

def gen_picks(LH, LA, book):
    OD = BOOKS_ROI[book]
    rows = {}
    for i, mid in enumerate(MIDS):
        if not FMm[i] or mid not in OD:
            continue
        lf, oh, oa = OD[mid]
        dist = eu_dist(LH[i], LA[i], EU_DRAW_SCALE)
        ucl = COMP[i] == 'ChampionsLeague'
        for side, ln, o in ((1, lf, oh), (-1, -lf, oa)):
            if not (1.70 <= o <= 2.10):
                continue
            role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
            if role is None:
                continue
            pw, pp = picks.p_cover(dist, side, ln)
            edge = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            thr = (0.10 if role == 'fav' else 0.04) if ucl else (0.04 if role == 'fav' else 0.10)
            if edge >= thr:
                rows[(mid, side)] = dict(i=i, comp=COMP[i], role=role, edge=edge, sea=SEA[i],
                                         aff=bool(AFF[i]), pnl=picks.settle(GD[i], side, ln, o))
    return rows

def roi(rows):
    p = np.array([r['pnl'] for r in rows])
    if len(p) == 0:
        return 0, float('nan'), float('nan')
    if len(p) == 1:
        return 1, float(p.mean()), float('nan')
    return len(p), float(p.mean()), float(p.std(ddof=1) / math.sqrt(len(p)))

def fmt(n, m_, se_):
    if n == 0:
        return f'{0:4d} {"-":>14s}'
    return f'{n:4d} {m_*100:+7.2f}±{(se_*100 if not math.isnan(se_) else 0):5.2f}'

GAMMA_RES = {}
PK = {}
for book in ['Crown', 'Pinnacle']:
    PB = gen_picks(*LIVE['base'], book); PN = gen_picks(*LIVE['loso'], book)
    PK[book] = (PB, PN)
    print(f'\n  === {book} closing ===')
    print(f'  {"διοργανωση":>16s} | {"BASE n ROI±SE":>20s} | {"ΝΕΟ n ROI±SE":>20s} | {"κοινα":>20s} | {"μονο base (πεσαν)":>20s} | {"μονο νεο (νεα)":>20s}')
    for lab, flt in [('UCL', lambda r: r['comp'] == 'ChampionsLeague'),
                     ('  UCL fav@10', lambda r: r['comp'] == 'ChampionsLeague' and r['role'] == 'fav'),
                     ('  UCL dog@4', lambda r: r['comp'] == 'ChampionsLeague' and r['role'] == 'dog'),
                     ('UEL', lambda r: r['comp'] == 'EuropaLeague'),
                     ('UECL', lambda r: r['comp'] == 'ConferenceLeague'),
                     ('ΟΛΑ', lambda r: True)]:
        kb = {k for k, r in PB.items() if flt(r)}; kn = {k for k, r in PN.items() if flt(r)}
        rb = [PB[k] for k in kb]; rn = [PN[k] for k in kn]
        com = [PN[k] for k in kb & kn]; drop = [PB[k] for k in kb - kn]; new = [PN[k] for k in kn - kb]
        nb, mb, sb = roi(rb); nn, mn, sn = roi(rn)
        print(f'  {lab:>16s} | {fmt(nb, mb, sb):>20s} | {fmt(nn, mn, sn):>20s} | {fmt(*roi(com)):>20s} | '
              f'{fmt(*roi(drop)):>20s} | {fmt(*roi(new)):>20s}')
        if lab == 'UCL':
            GAMMA_RES[book] = (nb, mb, sb, nn, mn, sn)
    # UCL μονο επηρεαζομενα ματς
    rb = [r for r in PB.values() if r['comp'] == 'ChampionsLeague' and r['aff']]
    rn = [r for r in PN.values() if r['comp'] == 'ChampionsLeague' and r['aff']]
    print(f'  {"UCL επηρεαζ.":>16s} | {fmt(*roi(rb)):>20s} | {fmt(*roi(rn)):>20s}')
    # UCL ανα σεζον
    print('  UCL ανα σεζον (base → νεο): ' + '  '.join(
        f'{s_}: {fmt(*roi([r for r in PB.values() if r["comp"] == "ChampionsLeague" and r["sea"] == s_])).strip()} → '
        f'{fmt(*roi([r for r in PN.values() if r["comp"] == "ChampionsLeague" and r["sea"] == s_])).strip()}'
        for s_ in EU_EVAL))

print('\n  --- ΜΕΣΟΣ ΟΡΟΣ Crown/Pinnacle (UCL) ---')
mb_ = np.mean([GAMMA_RES[b][1] for b in GAMMA_RES]); mn_ = np.mean([GAMMA_RES[b][4] for b in GAMMA_RES])
print(f'  UCL base {mb_*100:+.2f}%  →  νεο {mn_*100:+.2f}%  (n Crown {GAMMA_RES["Crown"][0]}→{GAMMA_RES["Crown"][3]}, '
      f'Pinnacle {GAMMA_RES["Pinnacle"][0]}→{GAMMA_RES["Pinnacle"][3]})')

# ================================================================ PICKLE
out = dict(mids=MIDS, sea=list(SEA), comp=list(COMP), round=list(RND), phase=list(PH), gd=list(GD),
           src_h=list(src_h), src_a=list(src_a), n_in_h=list(NIH), n_in_a=list(NIA), affected=list(AFF),
           chosen_w=CHOSEN,
           raw={str(k): (list(v[0]), list(v[1])) for k, v in RAW.items()},
           live={str(k): (list(v[0]), list(v[1])) for k, v in LIVE.items()},
           rps={str(k): list(v) for k, v in RPS.items()},
           note='raw = V4 λ (pre-γ/κ)· live = +γ−0.470 +κ1.16 (UCL νεο format)· base = prior-EU w=2 live· '
                'loso = νεος μηχανισμος με LOSO w_in')
pickle.dump(out, open('euro_inseason_eu_preds.pkl', 'wb'))
print('\n[pickle] euro_inseason_eu_preds.pkl')

# ================================================================ ΚΡΙΣΗ
print('\n' + '=' * 100)
print('ΚΡΙΣΗ (προ-δηλωμενα κριτηρια)')
print('=' * 100)
nneg = sum(1 for s_ in EU_EVAL if per_sea_delta[s_][0] < 0)
a_ok = nneg >= 3 and per_sea_delta['POOLED'][0] < 0
print(f'  (α) ΔRPS επηρεαζομενων <0 σε >=3/4 σεζον ΚΑΙ pooled<0: {"ΠΕΡΝΑ" if a_ok else "ΔΕΝ ΠΕΡΝΑ"} '
      f'({nneg}/4· pooled {per_sea_delta["POOLED"][0]*1000:+.2f}±{per_sea_delta["POOLED"][1]*1000:.2f} ×10⁻³, '
      f'n={per_sea_delta["POOLED"][2]})')
b1 = abs(BIAS_ATT) < 0.05 and abs(BIAS_DEF) < 0.05
b2 = abs(MB['loso'][0]) <= abs(MB['base'][0]) + MB['base'][1]
b_ok = b1 and b2
print(f'  (β) |bias att| & |bias def| < 0.05: {"ΝΑΙ" if b1 else "ΟΧΙ"} (att {BIAS_ATT:+.3f}, def {BIAS_DEF:+.3f})· '
      f'|pred−act margin| νεο <= base+1SE: {"ΝΑΙ" if b2 else "ΟΧΙ"} '
      f'(νεο {abs(MB["loso"][0]):.4f} vs base {abs(MB["base"][0]):.4f}+{MB["base"][1]:.4f}) → {"ΠΕΡΝΑ" if b_ok else "ΔΕΝ ΠΕΡΝΑ"}')
g_parts = []
g_ok = True
for b in ['Crown', 'Pinnacle']:
    nb, mb, sb, nn, mn, sn = GAMMA_RES[b]
    okb = (not math.isnan(mn)) and (not math.isnan(sb)) and mn >= mb - sb
    g_ok = g_ok and okb
    g_parts.append(f'{b}: base {mb*100:+.2f}±{sb*100:.2f} (n={nb}) → νεο {mn*100:+.2f} (n={nn}) {"ΟΚ" if okb else "ΧΕΙΡΟΤΕΡΟ >1SE"}')
print(f'  (γ) UCL ROI νεο >= base − 1SE (Crown ΚΑΙ Pinnacle): {"ΠΕΡΝΑ" if g_ok else "ΔΕΝ ΠΕΡΝΑ"} — ' + ' · '.join(g_parts))
print(f'\n  ΣΥΝΟΛΟ: α={"✓" if a_ok else "✗"} β={"✓" if b_ok else "✗"} γ={"✓" if g_ok else "✗"} → '
      + ('PASS' if (a_ok and b_ok and g_ok) else 'FAIL'))
print(f'\nΤΕΛΟΣ [{time.time()-T0:.0f}s]')
