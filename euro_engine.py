"""
euro_engine.py — ΕΥΡΩΠΑΪΚΟ ΜΟΝΤΕΛΟ v2: builder (module, θα ξαναχρησιμοποιηθει απο τη σουιτα).

ΠΛΗΡΕΣ εγχωριο engine (ορισμοι live, αντιγραφη ΟΧΙ επανεφευρεση):
  1. Teamgame inputs ανα λιγκα απο data_{Lg}_{sea}.json με τον ορισμο του expansion_test.py:
     compression w(xg), pen 0.25, red_xg adj, per-league-season rescale, ns_eff.
     ΓΚΟΛ-ΜΟΝΟ λιγκες (shots κενα): xg_model = γκολ (blend 0% xG αυτοματα αφου xf==gf),
     σουτ = σταθερα NS_CONST (ουδετερο, απαλειφεται)· σημαδεμενες goal_only=True.
  2. Ratings ομαδας: warm-start οπως live (dashboard/build_data.py):
     περσινο FLAT prior (flatten_warmstart) + φετινο rolling (picks.wmean DECAY 0.96),
     ραμπα picks.blend_at(n), γεωμετρικο _shrink w=n/(n+K) (K παραμετρικο για το τεστ Α1).
     Χωρις prior (πρωτη σεζον δεδομενων/νεοφωτιστη): current-only ΜΟΝΟ αν n>=6, αλλιως
     η πλευρα ειναι ΑΚΥΡΗ (ΟΧΙ "αγνωστοι ως μεσοι" — αυτο ηταν το bug του παλιου).
     Ημερολογιακες λιγκες: το "season" καθοριζεται απο την ημερομηνια του ματς
     (τελευταια σεζον με εναρξη <= d), prior = η αμεσως προηγουμενη χρονολογικα.
  3. ΧΑΡΑΚΑΣ διαλιγκικου ματς: γεωμετρικος μεσος των (lg_shots, lg_xgps) των δυο λιγκων.
     Ανα λιγκα ο χαρακας ειναι περσινος -> φετινος με ραμπα w=nc/(nc+KN_NORM) (οπως live).
  4. ΚΑΝΕΝΑ inter-league offset / HFA εδω: ο builder δινει ΟΥΔΕΤΕΡΑ base xg (xgh0, xga0).
     Offsets (πηγες i/ii/iii, ρ) και HFA Ευρωπης (LOSO) εφαρμοζονται στο test script
     πολλαπλασιαστικα: xg_h = xgh0 * hf * exp(+D), xg_a = xga0 / hf * exp(-D).
Read-only στα production αρχεια. Γραφει euro_preds.pkl + euro_ratings.pkl (μονο αν κληθει ως main
ή μεσω build_and_save()).
"""
import json, glob, os, sys, pickle, bisect
import numpy as np, pandas as pd
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import picks

SKIP_LG = {'Europe', 'Brazil', 'MLS', 'Championship', 'Bundesliga2', 'LaLiga2', 'SerieB', 'Ligue2'}
SKIP_SEA = {'2627', '2026'}          # φετινες (live) σεζον — δεν χρειαζονται για Ευρωπη <=2526
EU_SEASONS = ['2122', '2223', '2324', '2425', '2526']
EU_EVAL = ['2223', '2324', '2425', '2526']   # 2122 μονο prior (καμια αξιολογηση)
NS_CONST = 12.0                       # ουδετερα "σουτ" για γκολ-μονο λιγκες (απαλειφεται στο math)
KN_NORM = 20.0                        # ραμπα χαρακα λιγκας (ιδιο με live build_data.py)
K_GRID = [0, 4, 8, 16]
MIN_NOPRIOR_N = 6                     # χωρις prior: δεκτη πλευρα μονο με >=6 φετινα ματς
GAMMA_PLAYER = 1.09                   # κλιμακα player-offsets -> log-goal (multileague_test: γ=1.09 SE 0.05)

# player-bridge offsets (league_offsets.json)· ΜΟΝΟ σιγουρα mappings. Θετικο = πιο αδυναμη λιγκα.
PLAYER_OFF_KEY = {
    'EPL': 'EPL', 'LaLiga': 'LaLiga', 'SerieA': 'SerieA', 'Bundesliga': 'Bundesliga',
    'Ligue1': 'Ligue1', 'PrimeiraLiga': 'PrimeiraLiga', 'Eredivisie': 'Eredivisie',
    'Belgium': 'First Division A#40', 'GreeceSL': 'Super League 1#135',
    'ScottishPrem': 'Premiership#64', 'DanishSuperLiga': 'Superligaen#46',
    'AustrianBundesliga': 'Bundesliga#38', 'SwissSuperleague': 'Super League#69',
    'TurkishSuperLig': 'Super Lig#71', 'Allsvenskan': 'Allsvenskan#67',
    'Eliteserien': 'Eliteserien#59', 'Ekstraklasa': 'Ekstraklasa#196',
    'CroatiaHNL': 'HNL#252', 'CzechFirstLeague': '1. Liga#122',
    'RomaniaLigaI': 'Liga I#189', 'SerbiaSuperLiga': 'Super Liga#182',
    'IsraelLigatHaAl': "Ligat ha'Al#127", 'FinlandVeikkausliiga': 'Veikkausliiga#51',
}

EPS = 1e-9


# ---------- ορισμοι inputs (αντιγραφη expansion_test.py / build_inputs_5s.py) ----------
def w(xg):
    if xg <= 0.2: return 1.00
    if xg <= 0.4: return 0.45
    if xg <= 0.5: return 0.25
    if xg <= 0.7: return 0.15
    return 0.05


def kodt(s):
    try:
        return datetime.strptime(s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
    except Exception:
        return None


def team_xg_raw(m):
    """Ευρωπαικο πραγματικο xG ανα πλευρα (οπως multileague_roi.team_xg: raw, pen=0.25)."""
    hid = int(m['home']['id']); aid = int(m['away']['id'])
    agg = {hid: 0.0, aid: 0.0}
    for s in m['shots']:
        xg = s.get('xg'); tid = s.get('tid')
        if xg is None or tid not in agg: continue
        agg[tid] += 0.25 if s.get('sit') == 'Penalty' else xg
    return agg[hid], agg[aid]


def player_offsets():
    lo = json.load(open('league_offsets.json', encoding='utf-8'))
    return {lg: float(lo[k]) for lg, k in PLAYER_OFF_KEY.items() if k in lo}


def _wmean_slice(arr, n):
    """picks.wmean (DECAY 0.96) πανω στα πρωτα n στοιχεια numpy array."""
    if n == 0:
        return None
    wts = picks.DECAY ** np.arange(n - 1, -1, -1)
    return float((wts * arr[:n]).sum() / wts.sum())


def _shrink(r, prior, n, K):
    """Γεωμετρικο shrink προς prior, w=n/(n+K) (ιδιο με dashboard/build_data._shrink)."""
    if n <= 0:
        return prior
    wgt = 1.0 if K == 0 else n / (n + K)
    return tuple(max(pi, EPS) * (max(ri, EPS) / max(pi, EPS)) ** wgt for ri, pi in zip(r, prior))


class Engine:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.notes = []
        self._build_domestic()

    def log(self, *a):
        if self.verbose:
            print(*a)

    # ================= 1. εγχωρια teamgame inputs =================
    def _build_domestic(self):
        files = {}
        for p in sorted(glob.glob('data_*.json')):
            base = os.path.basename(p)[:-5]
            parts = base.split('_')
            lg = '_'.join(parts[1:-1]); sea = parts[-1]
            if lg in SKIP_LG or sea in SKIP_SEA or not sea.isdigit():
                continue
            files.setdefault(lg, []).append((sea, p))

        self.H = {}          # (lg, sea) -> {tid: dict(dates list[dt], sf/xf/sa/xa/gf/ga np arrays)}
        self.PRIOR = {}      # (lg, sea) -> {tid: flat rating tuple (Ax,Dx,SF,SA)}
        self.RULER_FULL = {} # (lg, sea) -> (lg_shots, lg_xgps) full season
        self.RUN = {}        # (lg, sea) -> (dates_sorted, cum_ns, cum_xg) teamgame-level για running χαρακα
        self.SPAN = {}       # (lg, sea) -> (start_dt, end_dt)
        self.GOAL_ONLY = set()
        self.SEASONS = {}    # lg -> [sea με χρονολογικη σειρα]
        self.PRV = {}        # (lg, sea) -> prev sea ή None
        self.TEAM_LGS = {}   # tid -> set(lg)
        self.id2name = {}

        for lg, sps in files.items():
            med = {}
            for sea, path in sps:
                d = json.load(open(path, encoding='utf-8'))
                rows = []          # ανα team-match
                any_shots = any(m['shots'] for m in d.values())
                goal_only = not any_shots
                if goal_only:
                    self.GOAL_ONLY.add((lg, sea))
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
                        continue    # λιγκα με σουτ αλλα ματς χωρις -> εξω (οπως build_inputs)
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
                    sf = g.np_raw.sum() / max(g.np_comp.sum(), EPS)   # per-league-season rescale
                    g['xg_model'] = g['np_comp'] * sf + 0.25 * g['pen'] + g['red_xg']
                    g['ns_eff'] = g['ns'] + g['pen'] + g['red_xg'].abs() / 0.10
                # στοιχεια ανα ομαδα (υπερ + κατα) απο τα ΖΕΥΓΗ rows (home,away του ιδιου ματς)
                per_team = {}
                for i in range(0, len(g) - 1, 2):
                    a_, b_ = g.iloc[i], g.iloc[i + 1]
                    per_team.setdefault(int(a_.team), []).append(
                        (a_.date, a_.ns_eff, a_.xg_model, a_.gf, b_.ns_eff, b_.xg_model, b_.gf))
                    per_team.setdefault(int(b_.team), []).append(
                        (b_.date, b_.ns_eff, b_.xg_model, b_.gf, a_.ns_eff, a_.xg_model, a_.gf))
                g = g.sort_values('date').reset_index(drop=True)
                key = (lg, sea)
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
            # flat περσινα priors
            for sea in order:
                pri = {}
                for tid, h in self.H[(lg, sea)].items():
                    pri[tid] = self._flat_rating(h)
                self.PRIOR[(lg, sea)] = pri
        n_ls = len(self.H)
        self.log(f'[engine] εγχωριες λιγκες: {len(self.SEASONS)}, λιγκα-σεζον: {n_ls}, '
                 f'γκολ-μονο: {len(self.GOAL_ONLY)}')

    @staticmethod
    def _flat_rating(h):
        """FLAT full-season rating (Ax,Dx,SF,SA) — οπως flatten_warmstart + _rating(n=None) (b=BLEND)."""
        b = picks.blend_at(None)
        sf = float(np.mean(h['sf'])); sa = float(np.mean(h['sa']))
        Ax = (b * np.mean(h['xf']) + (1 - b) * np.mean(h['gf'])) / max(sf, EPS)
        Dx = (b * np.mean(h['xa']) + (1 - b) * np.mean(h['ga'])) / max(sa, EPS)
        return (float(Ax), float(Dx), sf, sa)

    # ================= 2. warm-start rating στη στιγμη d =================
    def season_at(self, lg, d):
        best = None
        for sea in self.SEASONS.get(lg, []):
            st, en = self.SPAN[(lg, sea)]
            if st - timedelta(days=7) <= d:
                best = sea
        if best is None:
            return None
        st, en = self.SPAN[(lg, best)]
        if d > en + timedelta(days=400):
            return None      # μπαγιατικη καλυψη (η λιγκα δεν εχει πια δεδομενα)
        return best

    def _cur_tuple(self, h, d):
        """(tuple, n) απο φετινο rolling ΠΡΙΝ το d· ραμπα blend_at(n), wmean DECAY 0.96."""
        n = bisect.bisect_left(h['dates'], d)
        if n == 0:
            return None, 0
        b = picks.blend_at(n)
        sf = _wmean_slice(h['sf'], n); sa = _wmean_slice(h['sa'], n)
        Ax = (b * _wmean_slice(h['xf'], n) + (1 - b) * _wmean_slice(h['gf'], n)) / max(sf, EPS)
        Dx = (b * _wmean_slice(h['xa'], n) + (1 - b) * _wmean_slice(h['ga'], n)) / max(sa, EPS)
        return (Ax, Dx, sf, sa), n

    def side_state(self, tid, d):
        """Επιλυση (λιγκα, σεζον) της ομαδας στη στιγμη d. -> dict ή None."""
        cands = []
        for lg in self.TEAM_LGS.get(tid, ()):  # στην πραξη 1 λιγκα
            sea = self.season_at(lg, d)
            if sea is None:
                continue
            in_cur = tid in self.H[(lg, sea)]
            prv = self.PRV[(lg, sea)]
            in_prv = prv is not None and tid in self.H[(lg, prv)]
            if not in_cur and not in_prv:
                continue
            cands.append((in_cur, self.SPAN[(lg, sea)][0], lg, sea, prv, in_prv))
        if not cands:
            return None
        cands.sort(reverse=True)
        in_cur, _, lg, sea, prv, in_prv = cands[0]
        h = self.H[(lg, sea)].get(tid)
        cur, n = self._cur_tuple(h, d) if h else (None, 0)
        prior = self.PRIOR[(lg, prv)].get(tid) if in_prv else None
        if prior is None and n < MIN_NOPRIOR_N:
            return None            # ΟΧΙ "αγνωστος ως μεσος"
        return dict(lg=lg, sea=sea, cur=cur, n=n, prior=prior,
                    goal_only=(lg, sea) in self.GOAL_ONLY)

    def rating_of(self, st, K):
        if st['cur'] is None:
            return st['prior']
        if st['prior'] is None:
            return st['cur']
        return _shrink(st['cur'], st['prior'], st['n'], K)

    # ================= 3. χαρακας λιγκας στη στιγμη d =================
    def ruler(self, lg, sea, d):
        dts, cns, cxg = self.RUN[(lg, sea)]
        nc = bisect.bisect_left(dts, d)
        prv = self.PRV[(lg, sea)]
        if prv is not None:
            s0, x0 = self.RULER_FULL[(lg, prv)]
            if nc > 0:
                wr = nc / (nc + KN_NORM)
                sc = cns[nc] / nc; xc = cxg[nc] / max(cns[nc], EPS)
                return s0 * (sc / s0) ** wr, x0 * (xc / x0) ** wr
            return s0, x0
        if nc >= 40:
            return cns[nc] / nc, cxg[nc] / max(cns[nc], EPS)
        return self.RULER_FULL[(lg, sea)]     # fallback: full-season (ελαχιστο in-sample, σπανιο)

    # ================= 4. ουδετερη προβλεψη διαλιγκικου ζευγαριου =================
    def predict_neutral(self, sth, sta, d, K):
        """Base xg (xgh0, xga0) ΧΩΡΙΣ HFA και ΧΩΡΙΣ offsets. Χαρακας = γεωμ. μεσος λιγκων."""
        rh = self.rating_of(sth, K); ra = self.rating_of(sta, K)
        SLh, XLh = self.ruler(sth['lg'], sth['sea'], d)
        SLa, XLa = self.ruler(sta['lg'], sta['sea'], d)
        Ss = (SLh * SLa) ** 0.5; Xs = (XLh * XLa) ** 0.5
        Axh, Dxh, SFh, SAh = rh; Axa, Dxa, SFa, SAa = ra
        # σχετικα με τη δικη τους λιγκα
        axh, dxh, sfh, sah = Axh / XLh, Dxh / XLh, SFh / SLh, SAh / SLh
        axa, dxa, sfa, saa = Axa / XLa, Dxa / XLa, SFa / SLa, SAa / SLa
        xgh0 = (sfh * saa * Ss) * (axh * dxa * Xs)
        xga0 = (sfa * sah * Ss) * (axa * dxh * Xs)
        return xgh0, xga0

    # ================= 5. Ευρωπη: φορτωση & preds =================
    def load_europe(self):
        ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
        ROUND = {}
        for k, v in ef.items():
            for m in v:
                ROUND[str(m['mid'])] = m['round']
        rows = []
        for sea in EU_SEASONS:
            de = json.load(open(f'data_Europe_{sea}.json', encoding='utf-8'))
            for mid, m in de.items():
                if m['hs'] is None or m['as'] is None:
                    continue
                d = kodt(m['date'])
                if d is None:
                    continue
                if m['shots']:
                    xh, xa = team_xg_raw(m)
                else:
                    xh = xa = np.nan
                rd = ROUND.get(str(mid), '?')
                rows.append(dict(mid=str(mid), sea=sea, comp=m['comp'],
                                 phase='league' if rd.isdigit() else 'KO', date=d,
                                 hid=int(m['home']['id']), aid=int(m['away']['id']),
                                 hname=m['home']['name'], aname=m['away']['name'],
                                 gh=int(m['hs']), ga=int(m['as']),
                                 xgh_act=xh, xga_act=xa))
        return pd.DataFrame(rows).sort_values(['date', 'mid']).reset_index(drop=True)

    def load_crown(self):
        """Crown (cid=3) closing ανα mid: (g_home_gives, oh, oa). Συμβασεις multileague_roi."""
        def parse_line(g):
            try:
                p = [float(x) for x in str(g).split('/')]
                if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
                return sum(p) / len(p)
            except Exception:
                return None
        out = {}
        for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
            for line in open(f, encoding='utf-8'):
                r = json.loads(line)
                if r['cid'] != 3:
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
                    rows.append((int(mt), gl, oh, oa))
                if not rows:
                    continue
                rows.sort()
                _, gl, oh, oa = rows[-1]     # closing = τελευταιο ts
                out[str(r['mid'])] = (gl, oh, oa)
        return out

    def build_preds(self, k_grid=K_GRID):
        EU = self.load_europe()
        crown = self.load_crown()
        recs = []; drop = {}
        for _, r in EU.iterrows():
            sth = self.side_state(r.hid, r.date); sta = self.side_state(r.aid, r.date)
            if sth is None or sta is None:
                key = (r.sea, 'no_home' if sth is None else 'no_away')
                drop[key] = drop.get(key, 0) + 1
                continue
            rec = dict(mid=r.mid, sea=r.sea, comp=r.comp, phase=r.phase, date=r.date,
                       hname=r.hname, aname=r.aname, gh=r.gh, ga=r.ga, gd=r.gh - r.ga,
                       xgh_act=r.xgh_act, xga_act=r.xga_act,
                       lg_h=sth['lg'], lg_a=sta['lg'], n_h=sth['n'], n_a=sta['n'],
                       prior_h=sth['prior'] is not None, prior_a=sta['prior'] is not None,
                       go_h=sth['goal_only'], go_a=sta['goal_only'])
            mo = crown.get(r.mid)
            rec['mkt_g'] = mo[0] if mo else np.nan
            rec['mkt_oh'] = mo[1] if mo else np.nan
            rec['mkt_oa'] = mo[2] if mo else np.nan
            for K in k_grid:
                xh0, xa0 = self.predict_neutral(sth, sta, r.date, K)
                rec[f'bxh{K}'] = xh0; rec[f'bxa{K}'] = xa0
            recs.append(rec)
        P = pd.DataFrame(recs)
        self.drop_stats = drop
        return P


def build_and_save(k_grid=K_GRID):
    eng = Engine()
    P = eng.build_preds(k_grid)
    with open('euro_preds.pkl', 'wb') as f:
        pickle.dump(dict(preds=P, k_grid=k_grid, drop=eng.drop_stats,
                         goal_only=sorted(eng.GOAL_ONLY), player_off=player_offsets(),
                         gamma_player=GAMMA_PLAYER), f)
    # τελικα (τελος σεζον) ratings ανα λιγκα-σεζον — για τα επομενα τεστ της σουιτας
    RAT = {}
    for (lg, sea), hh in eng.H.items():
        end = eng.SPAN[(lg, sea)][1] + timedelta(days=1)
        RAT[(lg, sea)] = dict(ruler=eng.RULER_FULL[(lg, sea)],
                              goal_only=(lg, sea) in eng.GOAL_ONLY,
                              teams={tid: eng._flat_rating(h) for tid, h in hh.items()})
    with open('euro_ratings.pkl', 'wb') as f:
        pickle.dump(RAT, f)
    return eng, P


if __name__ == '__main__':
    eng, P = build_and_save()
    print(f'preds: {len(P)} ματς με εγκυρες 2 πλευρες (απο {sum(1 for _ in P.index)}...)')
    print('drops ανα σεζον:', eng.drop_stats)
    print(P.groupby('sea').size())
