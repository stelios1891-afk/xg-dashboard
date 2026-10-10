# ΠΑΡΑΛΛΑΓΗ (10/10/2026): πεναλτι 0.76 στα ratings = μηχανη γκολ (W2) των overs — για το τεστ χρονισμου UCL (ucl_timing_full).
"""
euro_v6w2_test.py — αντιγραφο του euro_prior_eu_test.py, ΜΟΝΟ το σκελος w=2:
παραγει και ΣΩΖΕΙ τα λ του w=2 ως euro_v6w2_preds.pkl (mids/sea/lh/la/src_h/src_a/gd,
ιδια σειρα mids με euro_v6_preds.pkl). Sanity w=0 vs V6 διατηρειται. Τα υπολοιπα
tables του πρωτοτυπου κοβονται (δεν χρειαζονται εδω).

--- πρωτοτυπο docstring ---
euro_prior_eu_test.py — ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ ΜΑΤΣ ΜΕΣΑ ΣΤΟ PRIOR (warm-start) του V4.

Βαση: euro_rebase_test.py (V6 baseline, δειγμα μετα το data refresh 8-9/9, LOSO FIT2/CAL
στο παλιο 1158) — ΙΔΙΟΙ μηχανισμοι. Sanity: w=0 πρεπει να αναπαραγει bit-for-bit το
euro_v6_preds.pkl (το v4/v5 ειναι ξεπερασμενο baseline μετα το refresh). ΜΟΝΗ αλλαγη: το flat περσινο εγχωριο prior καθε ομαδας εμπλουτιζεται με τα
ευρωπαικα της ματς της ΠΡΟΗΓΟΥΜΕΝΗΣ ευρωπαικης σεζον (t−1), μετατραπενα σε «εγχωρια-
ισοδυναμες» παρατηρησεις:

  xGF_eq = (b·xG + (1−b)·γκολ) · exp( ½lnXm_T − q_def(αντιπαλος) − ρ·s_T ∓ ln hf )
  xGA_eq = (b·xGA + (1−b)·γκολ κατα) · exp( ½lnXm_T − q_att(αντιπαλος) + ρ·s_T ± ln hf )

οπου q_def/q_att = ½lnXm_O + leak/att του αντιπαλου (rating του ΙΔΙΟΥ engine τη στιγμη του
ματς, K=8, με το goals→Elo replacement του V4 οπου ισχυει) ∓ ρ·s_O (offset λιγκας απο την
ιδια ιεραρχια s_v4 του fold). Αντιπαλος χωρις rating → μεσος ορος διοργανωσης-σεζον.
b = picks.blend_at(None) (ιδιο blend με το flat prior). hf = LOSO HFA Ευρωπης του fold.
Xm_T = χαρακας της λιγκας της ομαδας (running, στιγμη του ματς, περσινη σεζον).

Παραλλαγη prior (αριθμητικος μεσος οπως το flat prior):
  xGF' = (n_dom·xGF_prior + w·Σ xGF_eq) / (n_dom + w·n_eu)   — ομοια για αμυνα.
ΠΡΟΔΗΛΩΜΕΝΟ grid: w ∈ {0.5, 1, 2}, αναφερονται ΚΑΙ τα τρια. w=0 = sanity (bit-for-bit V4).

Αξιολογηση στο ΙΔΙΟ δειγμα με το v6, LOSO οπως V4: RPS 1Χ2, MAE margin — συνολο ΚΑΙ στο
υποδειγμα «≥4 περσινα ευρωπαικα σε τουλαχιστον μια πλευρα»· βαθμονομηση (pred−act cover,
universe dogs Crown closing) στο υποδειγμα· ROI picks αναφορικα. + παραδειγματα prior.

Output: euro_prior_eu_out.txt (redirect). ΔΕΝ αγγιζει κανενα υπαρχον αρχειο.
"""
import json, glob, sys, pickle, math, time
from datetime import datetime
import numpy as np, pandas as pd
import os, red_modes
RED_MODE = os.environ.get('RED_MODE') or None      # 5/10/2026: τεστ φορμουλας κοκκινων (κενο = παλια)
W2_OUT = os.environ.get('W2_OUT', 'euro_v6w2_preds.pkl')

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import picks
import euro_engine as EE
from euro_engine import (Engine, team_xg_raw, kodt, EU_SEASONS, EU_EVAL,
                         GAMMA_PLAYER, NS_CONST, EPS, w, _shrink)

T0 = time.time()
K = 8
RHO = 1.0
RIDGE = 3.0
MIN_FIT_N = 15
PEN_XG = 0.79
W_GRID = [2.0]                    # ΜΟΝΟ το w=2 (live setting)
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
                             xg_model=float(npxg + 0.76 * n_pen),
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
                        _RA = red_modes.team_adj(m, RED_MODE) if RED_MODE else None
                        for is_home, tid, gf, dis_self, dis_opp in [
                                (1, hid, m['hs'], dis_home, dis_away),
                                (0, aid, m['as'], dis_away, dis_home)]:
                            a = agg[tid]
                            red_xg = 0.0083 * dis_opp - 0.5 * 0.0083 * dis_self
                            if _RA is not None:     # 5/10/2026 τεστ κοκκινων (RED_MODE): νεα φορμουλα αντι της παλιας
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
                        g['xg_model'] = g['np_comp'] * sf + 0.76 * g['pen'] + g['red_xg']
                        g['ns_eff'] = g['ns'] + g['pen'] + g['red_xg'].abs() / 0.10
                        if RED_MODE:
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
print('=' * 100)
print('ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ ΣΤΟ PRIOR — baseline V6 (euro_v6_preds), LOSO· grid w ∈ {0.5, 1, 2} προδηλωμενο, w=0 sanity')
print('=' * 100)

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
        na1 = ENR[W_GRID[-1]][(fold, tid, lg, sea_dom)]
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

# ================================================================ ΠΡΟΒΛΕΨΕΙΣ ανα w
def predict(wg):
    LHv = np.empty(N); LAv = np.empty(N)
    for i in range(N):
        fold = SEA[i]; d = DATES[i]
        sth = SS(HID[i], d); sta = SS(AID[i], d)
        SLh, XLh = eng2.ruler(sth['lg'], sth['sea'], d)
        SLa, XLa = eng2.ruler(sta['lg'], sta['sea'], d)
        Ss = (SLh * SLa) ** 0.5; Xs = (XLh * XLa) ** 0.5
        lXs = math.log(Ss * Xs)
        def rate(st, tid):
            pr = st['prior']
            if wg > 0 and pr is not None:
                pr = ENR[wg].get((fold, tid, st['lg'], st['sea']), pr)
            if st['cur'] is None:
                return pr
            if pr is None:
                return st['cur']
            return _shrink(st['cur'], pr, st['n'], K)
        Axh, Dxh, SFh, SAh = rate(sth, HID[i])
        Axa, Dxa, SFa, SAa = rate(sta, AID[i])
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

PRED = {0.0: predict(0.0)}
for wg in W_GRID:
    PRED[wg] = predict(wg)

# ================================================================ SANITY w=0 vs V6
LH0, LA0 = PRED[0.0]
d6 = max(np.abs(LH0 - np.asarray(V6['lh'])).max(), np.abs(LA0 - np.asarray(V6['la'])).max())
print(f'\n[SANITY] w=0: max|Δλ| vs euro_v6_preds (n={N}) = {d6:.2e}')
print('  (guard προς v4/v5 δεν εφαρμοζεται: data store refresh 8-9/9 — v6 ειναι το baseline)')
if d6 > 1e-9 and not RED_MODE and not os.environ.get('NO_SANITY'):
    print('ΣΤΑΜΑΤΩ: το w=0 ΔΕΝ αναπαραγει το V6 baseline bit-for-bit (οδηγια).')
    sys.exit(1)
print('[SANITY] ΟΚ.')

# ================================================================ ΑΠΟΘΗΚΕΥΣΗ w=2 λ
LH2, LA2 = PRED[2.0]
out = dict(mids=MIDS, sea=list(SEA), lh=list(LH2), la=list(LA2),
           src_h=list(src_h), src_a=list(src_a), gd=list(GD))
pickle.dump(out, open(W2_OUT, 'wb'))
print(f'\n[SAVE] euro_v6w2_preds.pkl: n={N} (mids ιδια σειρα με euro_v6_preds.pkl)')
print(f'  mean λh: v6 {np.asarray(V6["lh"]).mean():.4f} -> w2 {LH2.mean():.4f}  |  '
      f'mean λa: v6 {np.asarray(V6["la"]).mean():.4f} -> w2 {LA2.mean():.4f}')
print(f'  max|Δλ| w2 vs v6: {max(np.abs(LH2-np.asarray(V6["lh"])).max(), np.abs(LA2-np.asarray(V6["la"])).max()):.4f}')
print(f'\nΤΕΛΟΣ [{time.time()-T0:.0f}s]')
sys.exit(0)

# ================================================================ n_eu ανα ματς & υποδειγμα
def neu_side(i, tid):
    st = SS(tid, DATES[i])
    if st is None or st['prior'] is None:
        return 0
    return NEU.get((SEA[i], tid, st['lg'], st['sea']), 0)

NEU_H = np.array([neu_side(i, HID[i]) for i in range(N)])
NEU_A = np.array([neu_side(i, AID[i]) for i in range(N)])
SUB = (NEU_H >= 4) | (NEU_A >= 4)
ANY = (NEU_H >= 1) | (NEU_A >= 1)
print(f'\nΥποδειγμα «>=4 περσινα ευρωπαικα (τουλαχιστον μια πλευρα)»: n={int(SUB.sum())}/{N}'
      f'  |  >=1 obs: {int(ANY.sum())}')
per = '  '.join(f'{s}: {int((SUB & (SEA == s)).sum())}/{int((SEA == s).sum())}' for s in EU_EVAL)
print(f'  ανα σεζον (sub/ολα): {per}')

# ================================================================ MAE / RPS
MKT = np.array([-SNAP[(m, 3)]['close'][1] if (m, 3) in SNAP else np.nan for m in MIDS])
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))

def probs_1x2(lh, la):
    dist = picks.gd_dist(max(lh, 0.05), max(la, 0.05))
    ph = sum(p for k_, p in dist.items() if k_ > 0)
    pd_ = dist.get(0, 0.0)
    return ph, pd_, 1 - ph - pd_

def metrics(LHv, LAv):
    RPSv = np.zeros(N)
    for i in range(N):
        ph, pdw, pa = probs_1x2(LHv[i], LAv[i])
        o = OUT3[i]
        RPSv[i] = 0.5 * ((ph - (o == 0)) ** 2 + (ph + pdw - (o <= 1)) ** 2)
    MAEv = np.abs((LHv - LAv) - GD)
    return RPSv, MAEv

MET = {wg: metrics(*PRED[wg]) for wg in [0.0] + W_GRID}
MAE_MKT = np.abs(MKT - GD)

def pse(d):
    return f'{d.mean():+8.5f}±{d.std(ddof=1)/math.sqrt(len(d)):.5f}' if len(d) > 1 else '-'

print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 1: RPS 1Χ2 / MAE margin ανα w — παγιδευμενα Δ vs w=0 (paired, ±SE)')
print('=' * 100)
for lab, mk in [(f'ΟΛΑ ({N})', np.ones(N, bool)), ('SUB >=4 eu', SUB),
                ('εκτος SUB', ~SUB), ('>=1 obs', ANY)]:
    print(f'\n--- {lab}: n={int(mk.sum())}  (MAE αγορας: {np.nanmean(MAE_MKT[mk]):.3f})')
    print(f'  {"w":>4s} {"RPS":>8s} {"ΔRPS vs w0":>17s} {"MAE":>8s} {"ΔMAE vs w0":>17s}')
    for wg in [0.0] + W_GRID:
        R_, M_ = MET[wg]
        R0, M0 = MET[0.0]
        dr = pse(R_[mk] - R0[mk]) if wg > 0 else '-'
        dm = pse(M_[mk] - M0[mk]) if wg > 0 else '-'
        print(f'  {wg:4.1f} {R_[mk].mean():8.4f} {dr:>17s} {M_[mk].mean():8.3f} {dm:>17s}')

print('\n--- RPS ανα σεζον (LOSO) — ΟΛΑ / SUB')
hdr = '  '.join(f'{s:>16s}' for s in EU_EVAL)
print(f'  {"w":>4s} {hdr}')
for wg in [0.0] + W_GRID:
    R_, _ = MET[wg]
    cells = []
    for s in EU_EVAL:
        mk = SEA == s; ms = mk & SUB
        cells.append(f'{R_[mk].mean():.4f}/{R_[ms].mean() if ms.sum() else float("nan"):.4f}')
    print(f'  {wg:4.1f} ' + '  '.join(f'{c:>16s}' for c in cells))
print('  (μορφη: ΟΛΑ/SUB· n SUB ανα σεζον: ' +
      ', '.join(f'{s}:{int((SUB & (SEA == s)).sum())}' for s in EU_EVAL) + ')')

# ================================================================ ΒΑΘΜΟΝΟΜΗΣΗ + ROI
def cover_act(gd, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    c = 0.0
    for L in parts:
        m = (gd if side == 1 else -gd) + L
        c += (1.0 if m > 0.01 else (0.5 if abs(m) < 0.01 else 0.0)) / len(parts)
    return c

def gen_universe(cid, LHv, LAv):
    rows = []
    for i, mid in enumerate(MIDS):
        s = SNAP.get((mid, cid))
        if not s:
            continue
        ts_, lf, oh, oa = s['close']
        dist = picks.gd_dist(max(LHv[i], 0.05), max(LAv[i], 0.05))
        for side, ud, odds in [(1, lf, oh), (-1, -lf, oa)]:
            if ud <= 0.01:
                continue
            pw, pp = picks.p_cover(dist, side, ud)
            rows.append(dict(i=i, sea=SEA[i], sub=bool(SUB[i]),
                             pred=pw + 0.5 * pp, act=cover_act(GD[i], side, ud),
                             pnl=picks.settle(GD[i], side, ud, odds)))
    return pd.DataFrame(rows)

def gen_bets(cid, LHv, LAv, edge_thr):
    old = picks.EDGE; picks.EDGE = edge_thr
    rows = []
    for i, mid in enumerate(MIDS):
        s = SNAP.get((mid, cid))
        if not s:
            continue
        ts_, lf, oh, oa = s['close']
        for b in picks.evaluate_bet(LHv[i], LAv[i], lf, oh, oa):
            rows.append(dict(i=i, sea=SEA[i], sub=bool(SUB[i]), edge=b['edge'],
                             pnl=picks.settle(GD[i], b['side'], b['hcap'], b['odds'])))
    picks.EDGE = old
    return pd.DataFrame(rows)

def rline(b):
    n = len(b)
    if n == 0:
        return f'{0:5d} {"-":>13s}'
    roi = b.pnl.mean() * 100
    se = b.pnl.std(ddof=1) / math.sqrt(n) * 100 if n > 1 else 0.0
    return f'{n:5d} {roi:+7.2f}±{se:5.2f}'

print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 2: ΒΑΘΜΟΝΟΜΗΣΗ universe dogs (Crown closing, χωρις φιλτρα): pred−act cover ανα w')
print('=' * 100)
print(f'  {"w":>4s} | {"SUB: n":>7s} {"pred":>6s} {"act":>6s} {"pred−act±SE":>15s} | '
      f'{"ΟΛΑ: n":>7s} {"pred":>6s} {"act":>6s} {"pred−act±SE":>15s}')
for wg in [0.0] + W_GRID:
    u = gen_universe(3, *PRED[wg])
    us = u[u['sub']]
    def cstr(df):
        d = df.pred - df.act
        return (f'{len(df):7d} {df.pred.mean():6.3f} {df.act.mean():6.3f} '
                f'{d.mean():+8.3f}±{d.std(ddof=1)/math.sqrt(len(df)):.3f}')
    print(f'  {wg:4.1f} | {cstr(us)} | {cstr(u)}')

print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 3: ROI picks (picks.evaluate_bet ως εχει, Crown closing) ανα w — αναφορα, ΟΧΙ επιλογη')
print('=' * 100)
print(f'  {"w":>4s} | {"@10% ΟΛΑ":^15s} | {"@10% SUB":^15s} | {"@6% ΟΛΑ":^15s} | {"@6% SUB":^15s}')
for wg in [0.0] + W_GRID:
    bb = gen_bets(3, *PRED[wg], 0.06)
    b10 = bb[bb.edge >= 0.10]; b6 = bb[bb.edge >= 0.06]
    print(f'  {wg:4.1f} | {rline(b10):>15s} | {rline(b10[b10["sub"]]):>15s} | '
          f'{rline(b6):>15s} | {rline(b6[b6["sub"]]):>15s}')

# ================================================================ ΠΑΡΑΔΕΙΓΜΑΤΑ PRIOR
print('\n' + '=' * 100)
print('ΠΙΝΑΚΑΣ 4: ΜΕΓΑΛΥΤΕΡΕΣ ΑΛΛΑΓΕΣ PRIOR (w=1) — περσινο ανα-ματς xGF/xGA prior πριν→μετα')
print('  eu_att/eu_def = μεσος «εγχωρια-ισοδυναμων» ευρωπαικων obs (πριν μπει στον μεσο)')
print('=' * 100)
EX = pd.DataFrame(EX_ROWS)
EX['chg'] = (np.abs(np.log(EX.att1 / EX.att0)) + np.abs(np.log(EX.def1 / EX.def0)))
print(f'  {"ομαδα":24s} {"λιγκα":16s} {"fold":>5s} {"n_dom":>5s} {"n_eu":>4s} '
      f'{"xGF: πριν→μετα":>16s} {"xGA: πριν→μετα":>16s} {"eu_att":>7s} {"eu_def":>7s}')
for r in EX.sort_values('chg', ascending=False).head(6).itertuples():
    print(f'  {r.name:24s} {r.lg:16s} {r.fold:>5s} {r.n_dom:5d} {r.n_eu:4d} '
          f'{r.att0:7.3f}→{r.att1:.3f} {r.def0:7.3f}→{r.def1:.3f} {r.eu_att:7.3f} {r.eu_def:7.3f}')
vil = EX[EX.name.str.contains('Villarreal', case=False, na=False)]
if len(vil):
    print('  --- Villarreal (ολα τα folds):')
    for r in vil.itertuples():
        print(f'  {r.name:24s} {r.lg:16s} {r.fold:>5s} {r.n_dom:5d} {r.n_eu:4d} '
              f'{r.att0:7.3f}→{r.att1:.3f} {r.def0:7.3f}→{r.def1:.3f} {r.eu_att:7.3f} {r.eu_def:7.3f}')
print(f'\n  μεση |Δlog prior| (w=1, μονο εμπλουτισμενες): att {np.abs(np.log(EX.att1/EX.att0)).mean():.4f}  '
      f'def {np.abs(np.log(EX.def1/EX.def0)).mean():.4f}')
print(f'  μεσο eu_att/prior_att: {(EX.eu_att/EX.att0).mean():.3f}  μεσο eu_def/prior_def: {(EX.eu_def/EX.def0).mean():.3f}')

print(f'\nΤΕΛΟΣ [{time.time()-T0:.0f}s]')
