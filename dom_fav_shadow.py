# -*- coding: utf-8 -*-
"""
dom_fav_shadow.py — LIVE ΣΚΙΑ «FAV S2» για τον scanner (εγκριση Στελιου 10/9).

Ρευμα ΜΟΝΟ φαβορι (γραμμη πλευρας <= -0.5), pricing S2 (συμβασεις fav_combo_test.py):
  (α) λ_fav απο engine με game-state διορθωση shot-xG: input = Σ(xg_shot/mult[state])
      + 0.25·pen + red_xg — POOLED v2 ελεγχομενοι mults ως ΣΤΑΘΕΡΕΣ (gamestate_v2 out):
      +2+:1.001, +1:0.988, 0:1.000, -1:1.144, -2-:1.171
  (β) ΧΩΡΙΣ συμπιεση Caley (np_raw αντι np_comp, χωρις w(), χωρις sf-rescale)
  (γ) λ_dog απο την ΚΑΝΟΝΙΚΗ συνθεση (build_inputs_5s: comp·sf + 0.25·pen + red_xg)
  (δ) tilt φαβορι: λ_fav +0.045, λ_dog −0.045 (TILT=0.09, συμβαση dom/euro_favtilt)
  (ε) quarter-aware p_cover: μεσος των p_cover σε line∓0.25 για γραμμες x.25/x.75
Κανονες pick: edge >= 0.10, αποδοση 1.70-2.10, γραμμη φαβορι <= -0.5.
Στο |line| = 0.5 ακριβως: λ baseline και στις δυο πλευρες (S2≡S1, συμβαση fav_combo).

Ratings «ως σημερα»: warm-start μηχανικη gamestate_v2/fav_combo (flat περσινο prior
2526, K=8, ραμπα blend_at, DECAY 0.96 wmean, SoS 1.5 gate n=6..13, HFA_FIX, norms
περσινης σεζον) πανω στα committed data_{lg}_{sea}.json (2526 prior + 2627 φετινη).
ΑΠΟΚΛΙΣΗ (τεκμηριωμενη): prior νεοφερτων = μεσος ορος prior λιγκας (οχι promo-coef
LOSO του corrected_config — δεν ειναι διαθεσιμο/αναγκαιο live· η σκια ειναι συνεπης
με τον εαυτο της).

Αποδοσεις: dom_odds_latest.json (κλειδια "{hid}_{aid}", πεδια line/oh/oa/ko/lg),
ΜΟΝΟ pre-KO. Αποτυπωση: append-on-change στο dom_fav_shadow.jsonl με state στο
dom_fav_shadow_state.json (sig: line|odds|edge_s2|edge_base).
edge_base = ιδιο ματς με ΚΑΝΟΝΙΚΗ συνθεση + picks.p_cover, ΧΩΡΙΣ tilt/quarter/GS/uncomp
(= S0 του fav_combo) — μονο για συγκριση.

Τρεχει στον GitHub Actions scanner ΜΕΤΑ το dom_odds_scan· δεν χρειαζεται TOA_KEY
(μονο committed αρχεια). Αν λειπουν αρχεια → graceful μηνυμα, exit 0.
ΔΕΝ αγγιζει picks.py / scan_value / shadow_scan / live αρχεια.
"""
import sys, os, json, math, datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import picks
from picks import BLEND, HFA_FIX, MARGIN, OMIN, OMAX, wmean, blend_at

CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
PRIOR_SEA, CUR_SEA = '2526', '2627'    # yearly update μαζι με το data-refresh
K = 8.0                                # warm-start shrink n/(n+K)
ST = 1.5                               # SoS strength
SOS_MIN_N, SOS_MAX_N = 6, 13
FT = 95
TILT = 0.09                            # ±TILT/2 στο pricing του ρευματος φαβορι
EDGE_MIN = 0.10
MULTS = {'+2+': 1.001, '+1': 0.988, '0': 1.000, '-1': 1.144, '-2-': 1.171}  # POOLED v2 ΣΤΑΘΕΡΕΣ
OUT = 'dom_fav_shadow.jsonl'
STATE_F = 'dom_fav_shadow_state.json'
ODDS_F = 'dom_odds_latest.json'


# ---------- helpers δεδομενων (ιδια logic με build_inputs_5s / gamestate_v2.load_raw) ----------
def isodate(s):
    try:
        return datetime.datetime.strptime(
            s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return str(s)[:10]


def state_of(diff):
    if diff >= 2: return '+2+'
    if diff == 1: return '+1'
    if diff == 0: return '0'
    if diff == -1: return '-1'
    return '-2-'


def w_comp(xg):     # ΙΔΙΟ με build_inputs_5s.w()
    if xg <= 0.2: return 1.00
    if xg <= 0.4: return 0.45
    if xg <= 0.5: return 0.25
    if xg <= 0.7: return 0.15
    return 0.05


def load_league_season(lg, sea, id2name):
    """data_{lg}_{sea}.json → λιστα παιγμενων ματς (κατα date,mid) με per-team:
       np_raw, np_comp, s2 (=Σ xg/mult[state]), pen, ns, red, gf. None αν λειπει το αρχειο."""
    path = f'data_{lg}_{sea}.json'
    if not os.path.exists(path):
        return None
    d = json.load(open(path, encoding='utf-8'))
    out = []
    for mid, m in d.items():
        hid = int(m['home']['id']); aid = int(m['away']['id'])
        id2name[hid] = m['home']['name']; id2name[aid] = m['away']['name']
        if m['hs'] is None or m['as'] is None:
            continue
        # reds → red_xg (ΙΔΙΟ με build_inputs_5s)
        dis_h = dis_a = 0.0
        for r in m['reds']:
            mn = r.get('min') or 0
            dur = max(0, FT - mn)
            if r['home']: dis_h += dur
            else: dis_a += dur
        red = {hid: 0.0083 * dis_a - 0.5 * 0.0083 * dis_h,
               aid: 0.0083 * dis_h - 0.5 * 0.0083 * dis_a}
        # ανακατασκευη σκορ για game-state: goal=true σουτ κατα (min, σειρα αρχειου)
        shots = sorted(enumerate(m['shots']), key=lambda t: ((t[1].get('min') or 0), t[0]))
        sh = sa = 0
        agg = {hid: dict(raw=0.0, comp=0.0, s2=0.0, pen=0, ns=0),
               aid: dict(raw=0.0, comp=0.0, s2=0.0, pen=0, ns=0)}
        for _, s in shots:
            tid = s.get('tid'); xg = s.get('xg')
            if tid not in agg:
                continue
            diff = (sh - sa) if tid == hid else (sa - sh)
            if xg is not None:
                if s.get('sit') == 'Penalty':
                    agg[tid]['pen'] += 1
                else:
                    agg[tid]['raw'] += xg
                    agg[tid]['comp'] += xg * w_comp(xg)
                    agg[tid]['s2'] += xg / MULTS[state_of(diff)]
                    agg[tid]['ns'] += 1
            if s.get('goal'):
                if tid == hid: sh += 1
                else: sa += 1
        out.append(dict(mid=str(mid), date=isodate(m['date']), hid=hid, aid=aid,
                        hg=int(m['hs']), ag=int(m['as']), agg=agg, red=red))
    out.sort(key=lambda r: (r['date'], r['mid']))
    return out


def teamgames(matches, variant):
    """→ λιστα (date, mid, tid, opp, sf(ns_eff), xf, sa, xa, gf, ga) κατα σειρα ημερομηνιας.
       variant 'base': comp·sf_λιγκας + 0.25·pen + red · 'gs': Σ(xg/mult) + 0.25·pen + red."""
    if variant == 'base':
        sraw = sum(m['agg'][t]['raw'] for m in matches for t in m['agg'])
        scomp = sum(m['agg'][t]['comp'] for m in matches for t in m['agg'])
        sf_l = sraw / max(scomp, 1e-9)
    rows = []
    for m in matches:
        xg = {}; ns = {}
        for t, a in m['agg'].items():
            npx = a['comp'] * sf_l if variant == 'base' else a['s2']
            xg[t] = npx + 0.25 * a['pen'] + m['red'][t]
            ns[t] = a['ns'] + a['pen'] + abs(m['red'][t]) / 0.10   # ns_eff (build_inputs_5s)
        h, a_ = m['hid'], m['aid']
        rows.append((m['date'], m['mid'], h, a_, ns[h], xg[h], ns[a_], xg[a_],
                     m['hg'], m['ag']))
        rows.append((m['date'], m['mid'], a_, h, ns[a_], xg[a_], ns[h], xg[h],
                     m['ag'], m['hg']))
    return rows


# ---------- warm-start engine (μηχανικη gamestate_v2.run, κατασταση «ως σημερα») ----------
class LeagueEngine:
    def __init__(self, lg, prior_rows, cur_rows):
        self.lg = lg
        self.hf = HFA_FIX[lg]
        # flat περσινο prior + norms (gamestate_v2.build_flat_norm)
        agg = {}
        for _, _, tid, _, sf, xf, sa, xa, gf, ga in prior_rows:
            d = agg.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[]))
            for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa),
                         ('gf', gf), ('ga', ga)]:
                d[k].append(v)
        self.prior = {}
        for tid, d in agg.items():
            sf = sum(d['sf']) / len(d['sf']); sa = sum(d['sa']) / len(d['sa'])
            Ax = (BLEND * sum(d['xf']) / len(d['xf']) +
                  (1 - BLEND) * sum(d['gf']) / len(d['gf'])) / max(sf, 1e-9)
            Dx = (BLEND * sum(d['xa']) / len(d['xa']) +
                  (1 - BLEND) * sum(d['ga']) / len(d['ga'])) / max(sa, 1e-9)
            self.prior[tid] = (Ax, Dx, sf, sa)
        asf = [v for d in agg.values() for v in d['sf']]
        axf = [v for d in agg.values() for v in d['xf']]
        self.ls = sum(asf) / max(len(asf), 1)
        self.lx = sum(axf) / max(sum(asf), 1e-9)
        # ΑΠΟΚΛΙΣΗ: prior νεοφερτων = μεσος prior λιγκας (αντι promo-coef LOSO)
        P = list(self.prior.values())
        self.mean_prior = tuple(sum(p[i] for p in P) / len(P) for i in range(4))
        # φετινο ιστορικο (με σειρα ημερομηνιας — το wmean/DECAY εξαρταται απο τη σειρα)
        self.hist = {}
        for _, _, tid, opp, sf, xf, sa, xa, gf, ga in sorted(cur_rows):
            d = self.hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
            for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa),
                         ('gf', gf), ('ga', ga), ('opp', opp)]:
                d[k].append(v)
        self._cache = {}

    def n_of(self, tid):
        h = self.hist.get(tid)
        return len(h['sf']) if h else 0

    def warm(self, tid):
        if tid in self._cache:
            return self._cache[tid]
        p = self.prior.get(tid, self.mean_prior)
        h = self.hist.get(tid)
        n = len(h['sf']) if h else 0
        if n == 0:
            v = p
        else:
            b = blend_at(n)
            sf = wmean(h['sf']); sa = wmean(h['sa'])
            Ax = (b * wmean(h['xf']) + (1 - b) * wmean(h['gf'])) / max(sf, 1e-9)
            Dx = (b * wmean(h['xa']) + (1 - b) * wmean(h['ga'])) / max(sa, 1e-9)
            w = n / (n + K)
            v = tuple(max(pi, 1e-9) * (max(ri, 1e-9) / max(pi, 1e-9)) ** w
                      for ri, pi in zip((Ax, Dx, sf, sa), p))
        self._cache[tid] = v
        return v

    def sosadj(self, r, tid):
        t = self.hist.get(tid)
        if not t or not (SOS_MIN_N <= len(t['opp']) <= SOS_MAX_N):
            return r
        oA = []; oD = []; oSF = []; oSA = []
        for o in t['opp']:
            a = self.warm(o)
            oA.append(a[0]); oD.append(a[1]); oSF.append(a[2]); oSA.append(a[3])
        mA, mD, mSF, mSA = wmean(oA), wmean(oD), wmean(oSF), wmean(oSA)
        return (r[0] * (self.lx / max(mD, 1e-9)) ** ST,
                r[1] * (self.lx / max(mA, 1e-9)) ** ST,
                r[2] * (self.ls / max(mSA, 1e-9)) ** ST,
                r[3] * (self.ls / max(mSF, 1e-9)) ** ST)

    def predict(self, H, A):
        """(xg_h, xg_a) για επερχομενο ματς — ιδιο math με gamestate_v2.run."""
        sh = self.sosadj(self.warm(H), H)
        sa_ = self.sosadj(self.warm(A), A)
        xg_h = (sh[2] * sa_[3] / self.ls) * (sh[0] * (sa_[1] / self.lx)) * self.hf
        xg_a = (sa_[2] * sh[3] / self.ls) * (sa_[0] * (sh[1] / self.lx)) / self.hf
        return xg_h, xg_a


# ---------- pricing (συμβασεις fav_combo_test) ----------
def p_cover_quarter(dist, side, line):
    """= clv_ledger.pq: μεσος των p_cover στα line−0.25/line+0.25 για x.25/x.75."""
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L in parts:
        w, p = picks.p_cover(dist, side, L)
        pw += w / len(parts); pp += p / len(parts)
    return pw, pp


def price_s2(lh, la, side, ln, o):
    """S2 pricing pick φαβορι στην πλευρα side (1=εντος) με γραμμη ln (<=-0.5), αποδοση o.
    Clip λ στο [0.05,6.0] ΠΡΙΝ το tilt, μετα max(.,0.05) — οπως fav_combo.price_pair."""
    lh = min(max(lh, 0.05), 6.0)
    la = min(max(la, 0.05), 6.0)
    lh2 = lh + (TILT / 2 if side == 1 else -TILT / 2)
    la2 = la - (TILT / 2 if side == 1 else -TILT / 2)
    dist = picks.gd_dist(max(lh2, 0.05), max(la2, 0.05))
    pw, pp = p_cover_quarter(dist, side, ln)
    edge = pw * (o - 1) * (1 - MARGIN) - (1 - pw - pp)
    return edge, pw, pp, lh2, la2


def price_base(lh, la, side, ln, o):
    """S0 reference: κανονικη συνθεση, picks.p_cover ως εχει, χωρις tilt/quarter."""
    lh = min(max(lh, 0.05), 6.0)
    la = min(max(la, 0.05), 6.0)
    dist = picks.gd_dist(lh, la)
    pw, pp = picks.p_cover(dist, side, ln)
    return pw * (o - 1) * (1 - MARGIN) - (1 - pw - pp), pw, pp


def show_example(c):
    """Παραδειγμα υπολογισμου βημα-βημα (sanity στο out)."""
    side = 1 if c['fav_side'] == 'H' else -1
    print('\nΠΑΡΑΔΕΙΓΜΑ ΥΠΟΛΟΓΙΣΜΟΥ ΒΗΜΑ-ΒΗΜΑ:')
    print(f"  {c['lg']}: {c['home']} - {c['away']} (γραμμη {c['line']:+.2f}, "
          f"φαβορι {'ΕΝΤΟΣ' if side == 1 else 'ΕΚΤΟΣ'}, ud={c['ud']:+.2f}, "
          f"αποδοση {c['odds']:.2f}, n φετινων: {c['n_h']}/{c['n_a']})")
    xh_b, xa_b = c['_lam']['xh_b'], c['_lam']['xa_b']
    xh_s2, xa_s2 = c['_lam']['xh_s2'], c['_lam']['xa_s2']
    print(f'  λ base   (κανονικη συνθεση): λh={xh_b:.4f}  λa={xa_b:.4f}')
    print(f'  λ S2-eng (GS mults+uncomp) : λh={xh_s2:.4f}  λa={xa_s2:.4f}')
    swap = abs(c['line']) > 0.5
    lam_h = xh_s2 if (swap and side == 1) else xh_b
    lam_a = xa_s2 if (swap and side == -1) else xa_b
    print(f"  υβριδικο ζευγος pricing: λ_fav←{'S2' if swap else 'base (|line|=0.5 → S2≡S1)'}, "
          f"λ_dog←base → λh={lam_h:.3f} λa={lam_a:.3f}")
    e, pw, pp, lh2, la2 = price_s2(lam_h, lam_a, side, c['ud'], c['odds'])
    print(f"  tilt ±{TILT / 2}: λ_fav +0.045, λ_dog −0.045 → λh'={lh2:.4f} λa'={la2:.4f}")
    parts = [c['ud']] if (c['ud'] * 4) % 2 == 0 else [c['ud'] - 0.25, c['ud'] + 0.25]
    dist = picks.gd_dist(max(lh2, 0.05), max(la2, 0.05))
    for L in parts:
        w, p = picks.p_cover(dist, side, L)
        print(f"    p_cover @ γραμμη {L:+.2f}: pw={w:.4f} pp={p:.4f}")
    print(f"  quarter μεσος: pw={pw:.4f} pp={pp:.4f}")
    print(f"  edge_s2 = pw·(o−1)·(1−{MARGIN}) − (1−pw−pp) = {pw:.4f}·{c['odds'] - 1:.2f}·0.97 − "
          f"{1 - pw - pp:.4f} = {e:+.4f}")
    eb, pwb, ppb = price_base(xh_b, xa_b, side, c['ud'], c['odds'])
    print(f"  edge_base (S0: base λ, p_cover ως εχει, χωρις tilt): pw={pwb:.4f} pp={ppb:.4f} "
          f"→ {eb:+.4f}")


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.isoformat(timespec='minutes')
    print(f'FAV S2 shadow — {ts}')

    # ---------- odds ----------
    if not os.path.exists(ODDS_F):
        print(f'{ODDS_F} δεν βρεθηκε — τιποτα να κανω (exit 0).')
        return
    try:
        odds = json.load(open(ODDS_F, encoding='utf-8')).get('odds', {})
    except Exception as e:
        print(f'{ODDS_F}: σφαλμα αναγνωσης ({type(e).__name__}) — exit 0.')
        return
    if not odds:
        print('κανενα ματς στο dom_odds_latest — τιποτα να κανω.')
        return

    # ---------- engines μονο για λιγκες που εχουν ματς στο odds file ----------
    need = sorted({v.get('lg') for v in odds.values() if v.get('lg') in CORE7})
    id2name = {}
    ENG = {}
    for lg in need:
        prior_m = load_league_season(lg, PRIOR_SEA, id2name)
        cur_m = load_league_season(lg, CUR_SEA, id2name)
        if prior_m is None or cur_m is None:
            print(f'{lg}: λειπει data_{lg}_{PRIOR_SEA if prior_m is None else CUR_SEA}.json — '
                  f'παραλειπεται.')
            continue
        ENG[lg] = dict(
            base=LeagueEngine(lg, teamgames(prior_m, 'base'), teamgames(cur_m, 'base')),
            gs=LeagueEngine(lg, teamgames(prior_m, 'gs'), teamgames(cur_m, 'gs')))
    if not ENG:
        print('καμια λιγκα με πληρη data JSONs — exit 0.')
        return
    print(f'engines: {", ".join(ENG)} (prior {PRIOR_SEA}, φετος {CUR_SEA})')

    # ---------- state ----------
    try:
        state = json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        state = {}

    n_seen = n_preko = n_fav = n_cand = n_new = 0
    cands = []
    with open(OUT, 'a', encoding='utf-8') as fh:
        for key, v in odds.items():
            n_seen += 1
            lg = v.get('lg')
            if lg not in ENG:
                continue
            try:
                ko = datetime.datetime.fromisoformat(str(v.get('ko')))
                line = float(v['line']); oh = float(v['oh']); oa = float(v['oa'])
            except (TypeError, ValueError, KeyError):
                continue
            if not (math.isfinite(line) and math.isfinite(oh) and math.isfinite(oa)):
                continue
            if ko <= now:
                continue                      # ΜΟΝΟ pre-KO
            n_preko += 1
            # πλευρα φαβορι: side=1 (εντος) αν line<=-0.5, side=-1 (εκτος) αν -line<=-0.5
            if line <= -0.5:
                side, ud, o = 1, line, oh
            elif line >= 0.5:
                side, ud, o = -1, -line, oa
            else:
                continue                      # χωρις σαφες φαβορι
            n_fav += 1
            try:
                hid, aid = (int(x) for x in key.split('_'))
            except ValueError:
                continue
            eb_pair = ENG[lg]['base'].predict(hid, aid)
            gs_pair = ENG[lg]['gs'].predict(hid, aid)
            xh_b, xa_b = eb_pair; xh_s2, xa_s2 = gs_pair
            if not all(math.isfinite(x) for x in (xh_b, xa_b, xh_s2, xa_s2)):
                continue
            # υβριδικο ζευγος: λ_fav απο S2 engine ΜΟΝΟ αν |line|>0.5 (στο 0.5: S2≡S1, base λ)
            swap = abs(line) > 0.5
            lam_h = xh_s2 if (swap and side == 1) else xh_b
            lam_a = xa_s2 if (swap and side == -1) else xa_b
            e_s2, pw, pp, _, _ = price_s2(lam_h, lam_a, side, ud, o)
            e_b, _, _ = price_base(xh_b, xa_b, side, ud, o)
            c = dict(t=ts, key=key, lg=lg, ko=str(v.get('ko')),
                     home=id2name.get(hid, str(hid)), away=id2name.get(aid, str(aid)),
                     fav_side='H' if side == 1 else 'A', line=round(line, 2),
                     ud=round(ud, 2), odds=round(o, 2),
                     edge_s2=round(e_s2, 4), edge_base=round(e_b, 4),
                     pw_s2=round(pw, 4), pp_s2=round(pp, 4),
                     xh_b=round(xh_b, 3), xa_b=round(xa_b, 3),
                     xh_s2=round(xh_s2, 3), xa_s2=round(xa_s2, 3),
                     n_h=ENG[lg]['base'].n_of(hid), n_a=ENG[lg]['base'].n_of(aid))
            # πληρης ακριβεια για το παραδειγμα (ΔΕΝ γραφεται στο jsonl)
            c['_lam'] = dict(xh_b=xh_b, xa_b=xa_b, xh_s2=xh_s2, xa_s2=xa_s2)
            cands.append(c)
            if not (e_s2 >= EDGE_MIN and OMIN <= o <= OMAX):
                continue
            n_cand += 1
            sig = f"{line:.2f}|{o:.2f}|{e_s2:.4f}|{e_b:.4f}"
            if state.get(key) == sig:
                continue                      # append-on-change: τιποτα δεν αλλαξε
            state[key] = sig
            fh.write(json.dumps({k: v2 for k, v2 in c.items() if not k.startswith('_')},
                                ensure_ascii=False) + '\n')
            n_new += 1

    with open(STATE_F, 'w', encoding='utf-8') as fh:
        json.dump(state, fh)

    print(f'ματς στο αρχειο odds: {n_seen} · pre-KO με γραμμη: {n_preko} · '
          f'με σαφες φαβορι (|line|>=0.5): {n_fav} · S2 candidates '
          f'(edge>={EDGE_MIN}, {OMIN}-{OMAX}): {n_cand} · νεες εγγραφες: {n_new}')
    if cands:
        print('\nΟΛΑ τα ρευματα φαβορι του παραθυρου (ενημερωτικα):')
        for c in sorted(cands, key=lambda x: -x['edge_s2']):
            mark = ' *S2 PICK*' if (c['edge_s2'] >= EDGE_MIN and
                                    OMIN <= c['odds'] <= OMAX) else ''
            print(f"  {c['lg']:>13s} {c['home']} - {c['away']} | φαβ {c['fav_side']} "
                  f"{c['ud']:+.2f} @ {c['odds']:.2f} | edge_s2 {c['edge_s2']:+.4f} "
                  f"(base {c['edge_base']:+.4f}) | λ_b {c['xh_b']:.2f}/{c['xa_b']:.2f} "
                  f"λ_s2 {c['xh_s2']:.2f}/{c['xa_s2']:.2f} | n {c['n_h']}/{c['n_a']}{mark}")
        show_example(sorted(cands, key=lambda x: -x['edge_s2'])[0])


if __name__ == '__main__':
    main()
