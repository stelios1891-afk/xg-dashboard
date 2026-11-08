# -*- coding: utf-8 -*-
"""
btts_test.py — BTTS (Both Teams To Score) ως πιθανη νεα αγορα (26/9/2026, ερωτημα Στελιου).

ΔΕΝ υπαρχουν ιστορικες αποδοσεις BTTS. Το τεστ: εχει το P_mod(BTTS) του μοντελου πληροφορια
ΠΕΡΑ απο την αγορα; Το P_mkt(BTTS) βγαινει απο την closing AH + closing O/U του ιδιου ματς.

ΜΕΘΟΔΟΣ (ιδια για μοντελο και αγορα, απλη):
  - Ανεξαρτητο Poisson, ΧΩΡΙΣ draw-boost / Dixon-Coles (ιδια μεταχειριση και στα δυο).
  - Αγορα: λ_h, λ_a λυνονται ωστε P(home καλυπτει closing AH) και P(over closing O/U) χωρις
    γκανιοτα (αναλογικη κανονικοποιηση two-way) να ταιριαζουν. Τεταρτα = μισο/μισο, push εξαιρειται:
    fair q = W/(W+L), W/L = αθροισμα πιθανοτητων νικης/ηττας στα δυο μισα.
  - P(BTTS) = 1 − P(h=0) − P(a=0) + P(0,0) = (1−e^−λh)(1−e^−λa).
  - y = 1 αν σκοραραν και οι δυο (τελικο σκορ).

ΣΥΜΠΑΝΤΑ:
  A) Εγχωρια CORE7 2223-2526 (4 σεζον· το 2122 ειναι μονο prior — δεν υπαρχει περσινη σεζον).
     Μηχανη: αντιγραφο του ou_blend.run (warm-start K=8, SoS 1.5 n=6..13, νεοφωτιστες CC).
     ΚΥΡΙΟ λ = blend γκολ 0.85 σταθερο (το λ των O/U τεστ: ou_blend/ou_xgbuild)·
     ΔΕΥΤΕΡΕΥΟΝ = ραμπα live (100→60/40), μονο για πληροφορια.
     Closing AH: canonical layer (odds/, AHCh + BFEC/PC/AvgC AH — ιδιο με gd_calib/sos_test).
     Closing O/U 2.5: football-data PC>2.5/PC<2.5 (Pinnacle closing), fallback AvgC (2223-2324 odds/,
     2425-2526 odds_full/*_fd.csv) — ιδιο με totals_market_test.
  B) Εθνικες 2122-2526: intl_model_choice_v3 (ιδια LOSO/τιμολογηση με intl_window_test, T_MODE=live,
     GD_FIX=none): λ = (T ± A_GOAL·diff)/2, clamp 0.15, Μ1/Μ2/Μ3. Νεκρα ματς εξαιρουνται (οπως το harness).
     Closing = τελευταια pre-KO κινηση Nowgoal, Crown (cid 3) και SBOBET (cid 31) ξεχωριστα·
     ενας αριθμος = μεσος Crown/SBOBET (* = διαφωνια προσημου).

ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ: τυπωνονται πριν τα αποτελεσματα. ΜΙΑ εκτελεση, κανενα tuning.
Εξοδος: btts_test_out.txt. ΔΕΝ αγγιζει picks.py / live αρχεια.
"""
import sys, os, json, glob, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

EDGES = (0.05, 0.08, 0.10)
MARGIN_BTTS = 0.05
KG = 15
GRID = np.arange(KG)
FACTK = np.array([math.factorial(int(k)) for k in GRID], float)
ND = 2 * KG - 1                      # gd -14..14 / total 0..28
# one-hot πινακες (K*K, ND)
_I, _J = np.meshgrid(GRID, GRID, indexing='ij')
OH_GD = np.zeros((KG * KG, ND)); OH_GD[np.arange(KG * KG), (_I - _J).ravel() + KG - 1] = 1
OH_TOT = np.zeros((KG * KG, ND)); OH_TOT[np.arange(KG * KG), (_I + _J).ravel()] = 1
DVALS = np.arange(ND) - (KG - 1)     # gd τιμες
TVALS = np.arange(ND)                # total τιμες


def parts_of(L):
    q = round(L * 4) / 4
    return [q] if abs(q * 2 - round(q * 2)) < 1e-9 else [q - 0.25, q + 0.25]


def ah_weights(lines):
    """home καλυπτει αν gd + L > 0. Επιστρεφει (wW, wL) (N, ND)."""
    N = len(lines); wW = np.zeros((N, ND)); wL = np.zeros((N, ND))
    for i, L in enumerate(lines):
        for p in parts_of(L):
            wW[i] += (DVALS + p > 1e-9); wL[i] += (DVALS + p < -1e-9)
    return wW, wL


def ou_weights(lines):
    N = len(lines); wW = np.zeros((N, ND)); wL = np.zeros((N, ND))
    for i, L in enumerate(lines):
        for p in parts_of(L):
            wW[i] += (TVALS - p > 1e-9); wL[i] += (TVALS - p < -1e-9)
    return wW, wL


def joint(lh, la):
    ph = np.exp(-lh)[:, None] * lh[:, None] ** GRID[None, :] / FACTK[None, :]
    pa = np.exp(-la)[:, None] * la[:, None] ** GRID[None, :] / FACTK[None, :]
    return (ph[:, :, None] * pa[:, None, :]).reshape(len(lh), -1)


def fair_q(W, L):
    return W / np.maximum(W + L, 1e-12)


def solve_market(ah_line, oh, oa, ou_line, oo, ou_):
    """Διανυσματικη εμφωλευμενη διχοτομηση: εξω T (O/U), μεσα s (AH). Επιστρεφει λh, λa, resid."""
    ah_line = np.asarray(ah_line, float); ou_line = np.asarray(ou_line, float)
    qh = (1 / oh) / (1 / oh + 1 / oa); qo = (1 / oo) / (1 / oo + 1 / ou_)
    aW, aL = ah_weights(ah_line); oW, oL = ou_weights(ou_line)
    N = len(qh)

    def inner(T):
        lo = -T + 0.04; hi = T - 0.04
        for _ in range(32):
            s = 0.5 * (lo + hi)
            J = joint((T + s) / 2, (T - s) / 2); pg = J @ OH_GD
            f = fair_q((pg * aW).sum(1), (pg * aL).sum(1))
            up = f < qh
            lo = np.where(up, s, lo); hi = np.where(up, hi, s)
        return 0.5 * (lo + hi)

    Tlo = np.full(N, 0.4); Thi = np.full(N, 8.0)
    for _ in range(30):
        T = 0.5 * (Tlo + Thi); s = inner(T)
        J = joint((T + s) / 2, (T - s) / 2); pt = J @ OH_TOT
        f = fair_q((pt * oW).sum(1), (pt * oL).sum(1))
        up = f < qo
        Tlo = np.where(up, T, Tlo); Thi = np.where(up, Thi, T)
    T = 0.5 * (Tlo + Thi); s = inner(T)
    lh, la = (T + s) / 2, (T - s) / 2
    J = joint(lh, la); pg = J @ OH_GD; pt = J @ OH_TOT
    r1 = fair_q((pg * aW).sum(1), (pg * aL).sum(1)) - qh
    r2 = fair_q((pt * oW).sum(1), (pt * oL).sum(1)) - qo
    return lh, la, np.maximum(np.abs(r1), np.abs(r2))


def p_btts(lh, la):
    return (1 - np.exp(-np.asarray(lh))) * (1 - np.exp(-np.asarray(la)))


# ---------------- μετρικες ----------------
EPS = 1e-4
def clipp(p): return np.clip(p, EPS, 1 - EPS)
def logit(p): p = clipp(p); return np.log(p / (1 - p))


def logreg(X, y, offset=None):
    """IRLS. X χωρις σταθερα (προστιθεται). Επιστρεφει beta, se."""
    X = np.column_stack([np.ones(len(y)), X]); b = np.zeros(X.shape[1])
    off = np.zeros(len(y)) if offset is None else offset
    for _ in range(50):
        eta = X @ b + off; p = 1 / (1 + np.exp(-eta)); w = p * (1 - p)
        H = X.T @ (X * w[:, None]); g = X.T @ (y - p)
        step = np.linalg.solve(H, g); b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    eta = X @ b + off; p = 1 / (1 + np.exp(-eta)); w = p * (1 - p)
    cov = np.linalg.inv(X.T @ (X * w[:, None]))
    return b, np.sqrt(np.diag(cov))


def metrics(pm, pk, y):
    """Brier/logloss μοντελο vs αγορα + paired διαφορα ±SE· regression coef μοντελου."""
    pm = clipp(pm); pk = clipp(pk); y = np.asarray(y, float); n = len(y)
    bm = (pm - y) ** 2; bk = (pk - y) ** 2
    lm = -(y * np.log(pm) + (1 - y) * np.log(1 - pm)); lk = -(y * np.log(pk) + (1 - y) * np.log(1 - pk))
    db = bm - bk; dl = lm - lk
    out = dict(n=n, base=y.mean(), pm=pm.mean(), pk=pk.mean(),
               brier_m=bm.mean(), brier_k=bk.mean(), dbrier=db.mean(), dbrier_se=db.std(ddof=1) / np.sqrt(n),
               ll_m=lm.mean(), ll_k=lk.mean(), dll=dl.mean(), dll_se=dl.std(ddof=1) / np.sqrt(n))
    if n >= 30:
        b, se = logreg(np.column_stack([logit(pk), logit(pm)]), y)
        out.update(b_mkt=b[1], b_mod=b[2], t_mod=b[2] / se[2])
        d = logit(pm) - logit(pk)
        b2, se2 = logreg(d[:, None], y, offset=logit(pk))          # αγορα ως offset (συντ. 1)
        out.update(b_delta=b2[1], t_delta=b2[1] / se2[1])
    return out


def roi_table(pm, pk, y):
    """ΥΠΟΘΕΤΙΚΟ: τιμες BTTS Yes/No = P_mkt με 5% margin αναλογικα. Flat 1u."""
    pm = np.asarray(pm); pk = np.asarray(pk); y = np.asarray(y)
    oy = 1 / (pk * (1 + MARGIN_BTTS)); on = 1 / ((1 - pk) * (1 + MARGIN_BTTS))
    ey = pm * oy - 1; en = (1 - pm) * on - 1
    res = {}
    for thr in EDGES:
        by = (ey >= thr) & (ey >= en); bn = (en >= thr) & (en > ey)
        pnl = np.concatenate([np.where(y[by] == 1, oy[by] - 1, -1.0), np.where(y[bn] == 0, on[bn] - 1, -1.0)])
        res[thr] = (len(pnl), pnl.mean() if len(pnl) else np.nan,
                    pnl.std(ddof=1) / np.sqrt(len(pnl)) if len(pnl) > 1 else np.nan, int(by.sum()), int(bn.sum()))
    py = np.where(y == 1, oy - 1, -1.0); pn = np.where(y == 0, on - 1, -1.0)
    res['allY'] = (len(py), py.mean(), py.std(ddof=1) / np.sqrt(len(py)), len(py), 0)
    res['allN'] = (len(pn), pn.mean(), pn.std(ddof=1) / np.sqrt(len(pn)), 0, len(pn))
    return res


def calib_delta(pm, pk, y, nb=5):
    pm = np.asarray(pm); pk = np.asarray(pk); y = np.asarray(y, float)
    d = pm - pk; qs = np.quantile(d, np.linspace(0, 1, nb + 1)); rows = []
    for i in range(nb):
        m = (d >= qs[i]) & (d <= qs[i + 1]) if i == nb - 1 else (d >= qs[i]) & (d < qs[i + 1])
        rows.append((int(m.sum()), d[m].mean(), pm[m].mean(), pk[m].mean(), y[m].mean(), (y[m] - pk[m]).mean()))
    return rows


def calib_dec(p, y, nb=10):
    p = np.asarray(p); y = np.asarray(y, float); qs = np.quantile(p, np.linspace(0, 1, nb + 1)); rows = []
    for i in range(nb):
        m = (p >= qs[i]) & (p <= qs[i + 1]) if i == nb - 1 else (p >= qs[i]) & (p < qs[i + 1])
        rows.append((int(m.sum()), p[m].mean(), y[m].mean()))
    return rows


def phase(md):
    return 'md1-6' if md <= 5 else ('md7-14' if md <= 13 else 'md15+')


# =====================================================================================
print('BTTS TEST — πληροφορια μοντελου περα απο την αγορα (P_mkt απο closing AH + closing O/U)')
print('=' * 100)
print("""ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ τα αποτελεσματα, ΜΙΑ εκτελεση):
  Κ1 «πληροφορια»: συντελεστης logit(P_mod) στο y ~ logit(P_mkt) + logit(P_mod) > 0 με t ≥ 2 pooled
      ΚΑΙ θετικος σε ≥3/4 σεζον (εγχωρια, 4 διαθεσιμες) / ≥3/5 (εθνικες).
  Κ2 «Brier»: Brier μοντελου οχι χειροτερο της αγορας κατα > 1 SE (paired ΔBrier/SE ≤ 1). Αναφερονται και τα δυο.
  Κ3 «ΥΠΟΘΕΤΙΚΟ ROI» στο edge ≥8%: θετικο σε ≥4/5 σεζον → με 4 διαθεσιμες εγχωριες σεζον: ≥3/4 ΚΑΙ pooled > 0
      (εθνικες: ≥3/5 ΚΑΙ pooled > 0 — ιδια αναλογια με Κ1).
  ΚΡΙΤΗΡΙΑ ΚΑΛΥΠΤΟΝΤΑΙ = Κ1 ΚΑΙ Κ2 ΚΑΙ Κ3. Εγχωρια: κρινεται το ΚΥΡΙΟ λ (blend γκολ 0.85)· η ραμπα live = πληροφορια.
  Εθνικες: κρινεται καθε μοντελο (Μ1/Μ2/Μ3) στον μεσο Crown/SBOBET.
""")

# =====================================================================================
# A) ΕΓΧΩΡΙΑ
# =====================================================================================
import picks
from picks import HFA_FIX, wmean
from sos_test import prev_season, reg_of, make_resolver_alias
from league_config import ALIAS_FD
import corrected_config as CC

SEAS = ['2223', '2324', '2425', '2526']
K = 8.0; SOS = 1.5; SOS_LO, SOS_HI = 6, 13
RAMP_BL, RAMP_SPLIT, RAMP_KG = 0.60, 13, 12.0
RAMP_D = (1.0 - RAMP_BL) * (RAMP_SPLIT + RAMP_KG) / RAMP_SPLIT
M, id2 = CC.M, CC.id2name


def bfun(cfg, n):
    if cfg == 'ramp':
        return 1.0 - RAMP_D * n / (n + RAMP_KG) if n <= RAMP_SPLIT else RAMP_BL
    return cfg


def flat_prior(b):
    out = {}
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        agg = {}
        for _, r in G.iterrows():
            for tid, sf, xf, sa, xa, gf, ga in [
                    (r['home'], r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (r['away'], r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                d = agg.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga)]:
                    d[k].append(v)
        pr = {}
        for tid, d in agg.items():
            sf = np.mean(d['sf']); sa = np.mean(d['sa'])
            pr[tid] = ((b * np.mean(d['xf']) + (1 - b) * np.mean(d['gf'])) / max(sf, 1e-9),
                       (b * np.mean(d['xa']) + (1 - b) * np.mean(d['ga'])) / max(sa, 1e-9), sf, sa)
        out[(lg, str(sea))] = pr
    return out


def rat(t, b):
    sf = wmean(t['sf']); sa = wmean(t['sa'])
    return ((b * wmean(t['xf']) + (1 - b) * wmean(t['gf'])) / max(sf, 1e-9),
            (b * wmean(t['xa']) + (1 - b) * wmean(t['ga'])) / max(sa, 1e-9), sf, sa)


def shrink(r, p, n):
    w = n / (n + K)
    return tuple(max(pi, 1e-9) * (max(ri, 1e-9) / max(pi, 1e-9)) ** w for ri, pi in zip(r, p))


def run(cfg):
    FL = flat_prior(RAMP_BL if cfg == 'ramp' else cfg)
    rows = []
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        sea = str(sea)
        if sea not in SEAS:
            continue
        ls, lx = CC.NORM[(lg, prev_season(sea))]
        hf = HFA_FIX[lg]
        prev = FL.get((lg, prev_season(sea)), {})
        G = G.sort_values(['date', 'mid']).reset_index(drop=True)
        hist = {}; cache = {}

        def warm(tid):
            h = hist.get(tid); n = len(h['sf']) if h else 0
            key = (tid, n)
            if key in cache:
                return cache[key]
            p = prev.get(tid)
            if p is None:
                p = CC.promo_prior(lg, sea, tid)
            v = p if n == 0 else shrink(rat(h, bfun(cfg, n)), p, n)
            cache[key] = v
            return v

        def sosadj(r, t):
            if not t or not (SOS_LO <= len(t['opp']) <= SOS_HI):
                return r
            oA = []; oD = []; oSF = []; oSA = []
            for o in t['opp']:
                a = warm(o)
                oA.append(a[0]); oD.append(a[1]); oSF.append(a[2]); oSA.append(a[3])
            mA, mD, mSF, mSA = wmean(oA), wmean(oD), wmean(oSF), wmean(oSA)
            return (r[0] * (lx / max(mD, 1e-9)) ** SOS, r[1] * (lx / max(mA, 1e-9)) ** SOS,
                    r[2] * (ls / max(mSA, 1e-9)) ** SOS, r[3] * (ls / max(mSF, 1e-9)) ** SOS)

        for _, r in G.iterrows():
            H, A = r['home'], r['away']
            hh = hist.get(H); ha = hist.get(A)
            nh = len(hh['sf']) if hh else 0
            na = len(ha['sf']) if ha else 0
            mn = min(nh, na)
            rh = sosadj(warm(H), hh); ra = sosadj(warm(A), ha)
            xh = min(max((rh[2] * ra[3] / ls) * (rh[0] * (ra[1] / lx)) * hf, .05), 6.)
            xa = min(max((ra[2] * rh[3] / ls) * (ra[0] * (rh[1] / lx)) / hf, .05), 6.)
            rows.append(dict(league=lg, season=sea, mid=r['mid'], date=r['date'], home=H, away=A,
                             home_name=id2.get(H), away_name=id2.get(A), md=mn, xh=xh, xa=xa,
                             hg=int(r['hg']), ag=int(r['ag'])))
            for tid, opp, sf, xf, sa2, xa2, gf, ga in [
                    (H, A, r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (A, H, r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                dd = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                for k_, v in [('sf', sf), ('xf', xf), ('sa', sa2), ('xa', xa2),
                              ('gf', gf), ('ga', ga), ('opp', opp)]:
                    dd[k_].append(v)
    return pd.DataFrame(rows)


print('[A] χτισιμο προβλεψεων εγχωριων (0.85 + ραμπα) ...', flush=True)
P85 = run(0.85)
PRA = run('ramp')
P = P85.rename(columns={'xh': 'xh85', 'xa': 'xa85'})
P['xhR'] = PRA['xh'].values; P['xaR'] = PRA['xa'].values
assert (PRA['mid'].values == P85['mid'].values).all()

# sanity: ραμπα vs gd_calib_preds (live build_preds_live)
try:
    GC = pd.read_pickle('gd_calib_preds.pkl')
    mg = P.merge(GC[['league', 'season', 'date', 'home_name', 'away_name', 'xg_h', 'xg_a']],
                 on=['league', 'season', 'date', 'home_name', 'away_name'], how='inner')
    dd_ = np.abs(mg.xhR - mg.xg_h.clip(.05, 6)).mean()
    print(f'  sanity ραμπα vs gd_calib_preds: κοινα {len(mg)} · μεση |Δxg_h| = {dd_:.4f} · corr {np.corrcoef(mg.xhR, mg.xg_h)[0,1]:.4f}')
except Exception as e:
    print('  sanity παραλειφθηκε:', e)

# ---- odds: AH canonical + O/U 2.5 FD ----
OmF, fdnF = {}, {}
for lg in CC.CORE7 if hasattr(CC, 'CORE7') else ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']:
    for sea in ['2425', '2526']:
        try:
            o = pd.read_csv(f'odds_full/{lg}_{sea}_fd.csv', encoding='latin-1')
        except FileNotFoundError:
            print(f'  ΛΕΙΠΕΙ odds_full/{lg}_{sea}_fd.csv'); continue
        for _, r in o.iterrows():
            if pd.isna(r.get('HomeTeam')):
                continue
            fdnF[r['HomeTeam']] = picks.norm(r['HomeTeam']); fdnF[r['AwayTeam']] = picks.norm(r['AwayTeam'])
            OmF.setdefault((str(sea), r['HomeTeam'], r['AwayTeam']), []).append(r)
resolveF = make_resolver_alias(fdnF, ALIAS_FD)

rec = []
for r in P.itertuples():
    g = reg_of(r.season); Om = CC.reg[g]['Om']; res = CC.resolvers[g]
    o = picks.match_odds(Om, r.season, res(r.home_name), res(r.away_name), r.date)
    line = oh = oa = bk = None
    if o is not None:
        line = o.get('AHCh'); oh, oa, bk = picks.ah_odds(o)
        if pd.isna(line) or oh is None:
            line = oh = oa = bk = None
    if g == 'old':
        o2 = o
    else:
        o2 = picks.match_odds(OmF, r.season, resolveF(r.home_name), resolveF(r.away_name), r.date)
    ov = un = None; tag = None
    if o2 is not None:
        ov, un, tag = o2.get('PC>2.5'), o2.get('PC<2.5'), 'PC'
        if pd.isna(ov) or pd.isna(un):
            ov, un, tag = o2.get('AvgC>2.5'), o2.get('AvgC<2.5'), 'AvgC'
        if pd.isna(ov) or pd.isna(un):
            ov = un = tag = None
    rec.append((np.nan if line is None else float(line), oh, oa, bk, ov, un, tag))
P['ah'], P['oh'], P['oa'], P['ahbook'], P['oo'], P['ou'], P['ousrc'] = zip(*rec)
n_all = len(P)
Pd = P[P.ah.notna() & P.oo.notna()].copy().reset_index(drop=True)
for c in ['oh', 'oa', 'oo', 'ou']:
    Pd[c] = Pd[c].astype(float)
Pd = Pd[(Pd.oh > 1) & (Pd.oa > 1) & (Pd.oo > 1) & (Pd.ou > 1)].reset_index(drop=True)
print(f'  ματς: {n_all} · με closing AH + O/U2.5: {len(Pd)} · AH book: {Pd.ahbook.value_counts().to_dict()} · '
      f'O/U πηγη: {Pd.ousrc.value_counts().to_dict()}', flush=True)
print('  O/U fallback AvgC ανα σεζον: ' + ' '.join(f"{s}:{(Pd[Pd.season == s].ousrc == 'AvgC').mean():.0%}" for s in SEAS))

lh, la, resid = solve_market(Pd.ah.values, Pd.oh.values, Pd.oa.values, np.full(len(Pd), 2.5), Pd.oo.values, Pd.ou.values)
Pd['lh_m'] = lh; Pd['la_m'] = la; Pd['resid'] = resid
bad = resid > 0.005
print(f'  αντιστροφη αγορας: max resid {resid.max():.2e} · >0.005: {int(bad.sum())} (εξαιρουνται)')
Pd = Pd[~bad].reset_index(drop=True)
Pd['pk'] = p_btts(Pd.lh_m, Pd.la_m)
Pd['pm85'] = p_btts(Pd.xh85, Pd.xa85)
Pd['pmR'] = p_btts(Pd.xhR, Pd.xaR)
Pd['y'] = ((Pd.hg > 0) & (Pd.ag > 0)).astype(int)
Pd['phase'] = Pd.md.map(phase)
print(f'  τελικο δειγμα: {len(Pd)} · sanity μεσο λ_m (h+a) {(Pd.lh_m + Pd.la_m).mean():.3f} vs actual {(Pd.hg + Pd.ag).mean():.3f} · '
      f'μεσο λ_mod0.85 {(Pd.xh85 + Pd.xa85).mean():.3f} · ραμπα {(Pd.xhR + Pd.xaR).mean():.3f}')


def fmt_se(v, se, d=4):
    return f'{v:+.{d}f}±{se:.{d}f}'


def report_dom(col, label):
    print('\n' + '-' * 100)
    print(f'ΕΓΧΩΡΙΑ — {label}')
    print('-' * 100)
    print(f"{'σεζον':>7s} {'n':>5s} {'BTTS%':>6s} {'P_mod':>6s} {'P_mkt':>6s} | {'Brier mod':>9s} {'Brier mkt':>9s} {'ΔBrier±SE':>17s} | "
          f"{'LL mod':>7s} {'LL mkt':>7s} {'ΔLL±SE':>17s} | {'b_mod(t)':>13s} {'b_mkt':>6s} | {'b_Δ offset(t)':>14s}")
    R = {}
    for s in SEAS + ['POOLED']:
        d = Pd if s == 'POOLED' else Pd[Pd.season == s]
        m = metrics(d[col].values, d.pk.values, d.y.values); R[s] = m
        print(f"{s:>7s} {m['n']:5d} {m['base']*100:5.1f}% {m['pm']:.3f} {m['pk']:.3f} | {m['brier_m']:.5f} {m['brier_k']:.5f} "
              f"{fmt_se(m['dbrier'], m['dbrier_se'], 5):>17s} | {m['ll_m']:.4f} {m['ll_k']:.4f} {fmt_se(m['dll'], m['dll_se'], 4):>17s} | "
              f"{m['b_mod']:+.3f}({m['t_mod']:+.2f}) {m['b_mkt']:+.3f} | {m['b_delta']:+.3f}({m['t_delta']:+.2f})")
    print('  ανα φαση (pooled):')
    for ph in ['md1-6', 'md7-14', 'md15+']:
        d = Pd[Pd.phase == ph]; m = metrics(d[col].values, d.pk.values, d.y.values)
        print(f"   {ph:>7s} n={m['n']:5d} BTTS {m['base']*100:4.1f}% · ΔBrier {fmt_se(m['dbrier'], m['dbrier_se'], 5)} · "
              f"b_mod {m['b_mod']:+.3f} (t {m['t_mod']:+.2f})")
    print('  βαθμονομηση ανα πεμπτημοριο Δ = P_mod − P_mkt (pooled):')
    print(f"   {'n':>5s} {'μεσο Δ':>7s} {'P_mod':>6s} {'P_mkt':>6s} {'actual':>6s} {'act−mkt':>8s}")
    for row in calib_delta(Pd[col].values, Pd.pk.values, Pd.y.values):
        print(f'   {row[0]:5d} {row[1]:+.3f} {row[2]:.3f} {row[3]:.3f} {row[4]:.3f} {row[5]:+.3f}')
    print('  βαθμονομηση δεκατημορια (pooled): P_mod→actual | P_mkt→actual')
    cm = calib_dec(Pd[col].values, Pd.y.values); ck = calib_dec(Pd.pk.values, Pd.y.values)
    for a, b in zip(cm, ck):
        print(f'   mod {a[1]:.3f}→{a[2]:.3f} (n {a[0]:4d})   |   mkt {b[1]:.3f}→{b[2]:.3f} (n {b[0]:4d})')
    print('  ΥΠΟΘΕΤΙΚΟ ROI (τιμες = P_mkt με 5% margin αναλογικα· flat 1u · ΟΧΙ πραγματικες αποδοσεις):')
    print(f"   {'κανονας':>10s} | " + ' | '.join(f'{s:>20s}' for s in SEAS + ['POOLED']) + ' | Y/N pooled')
    RO = {s: roi_table((Pd if s == 'POOLED' else Pd[Pd.season == s])[col].values,
                       (Pd if s == 'POOLED' else Pd[Pd.season == s]).pk.values,
                       (Pd if s == 'POOLED' else Pd[Pd.season == s]).y.values) for s in SEAS + ['POOLED']}
    for key in list(EDGES) + ['allY', 'allN']:
        lab = f'edge≥{int(key*100)}%' if not isinstance(key, str) else ('τυφλο Yes' if key == 'allY' else 'τυφλο No')
        cells = []
        for s in SEAS + ['POOLED']:
            n, roi, se, ny, nn = RO[s][key]
            cells.append(f'{n:5d} {roi*100:+6.1f}±{se*100:4.1f}%' if n > 1 else f'{n:5d}      —      ')
        print(f'   {lab:>10s} | ' + ' | '.join(f'{c:>20s}' for c in cells) + f' | {RO["POOLED"][key][3]}/{RO["POOLED"][key][4]}')
    print('  ΥΠΟΘΕΤΙΚΟ ROI edge≥8% ανα φαση (pooled):')
    for ph in ['md1-6', 'md7-14', 'md15+']:
        d = Pd[Pd.phase == ph]; n, roi, se, ny, nn = roi_table(d[col].values, d.pk.values, d.y.values)[0.08]
        print(f'   {ph:>7s} n={n:5d} ROI {roi*100:+.1f}±{se*100:.1f}% (Yes {ny} / No {nn})')
    # κριτηρια
    k1 = R['POOLED']['b_mod'] > 0 and R['POOLED']['t_mod'] >= 2 and sum(R[s]['b_mod'] > 0 for s in SEAS) >= 3
    k2 = R['POOLED']['dbrier'] <= R['POOLED']['dbrier_se']
    k3n = sum(RO[s][0.08][1] > 0 for s in SEAS if RO[s][0.08][0] > 0)
    k3 = k3n >= 3 and RO['POOLED'][0.08][1] > 0
    print(f"  ΚΡΙΤΗΡΙΑ: Κ1 b_mod {R['POOLED']['b_mod']:+.3f} t {R['POOLED']['t_mod']:+.2f}, θετικο {sum(R[s]['b_mod'] > 0 for s in SEAS)}/4 → {'✓' if k1 else '✗'} · "
          f"Κ2 ΔBrier/SE {R['POOLED']['dbrier']/R['POOLED']['dbrier_se']:+.2f} → {'✓' if k2 else '✗'} · "
          f"Κ3 ROI@8% θετικο {k3n}/4, pooled {RO['POOLED'][0.08][1]*100:+.1f}% → {'✓' if k3 else '✗'}  ⇒  "
          f"{'ΚΑΛΥΠΤΟΝΤΑΙ (PASS)' if (k1 and k2 and k3) else 'ΔΕΝ ΚΑΛΥΠΤΟΝΤΑΙ (FAIL)'}")


report_dom('pm85', 'ΚΥΡΙΟ: λ blend γκολ 0.85 (O/U-τεστ κατασκευη)')
report_dom('pmR', 'ΔΕΥΤΕΡΕΥΟΝ (πληροφορια): λ ραμπα live 100→60/40')

# =====================================================================================
# B) ΕΘΝΙΚΕΣ
# =====================================================================================
print('\n' + '=' * 100)
print('[B] ΕΘΝΙΚΕΣ — χτισιμο (intl_model_choice_v3, ιδιο με intl_window_test) ...', flush=True)
src = open('intl_model_choice_v3.py', encoding='utf-8').read()
G = {'__name__': 'btts'}
import io, contextlib
class _Buf(io.StringIO):
    def reconfigure(self, *a, **k): pass
_buf = _Buf()
with contextlib.redirect_stdout(_buf):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, MODELS, T_of, A_GOAL = (G[k] for k in ('D', 'MODELS', 'T_of', 'A_GOAL'))
MI = pd.read_csv('intl_matches.csv', dtype={'mid': str})
KO = {m: pd.Timestamp(d).tz_localize('UTC').timestamp() for m, d in zip(MI.mid, MI.date)}


def hk(v):
    v = float(v); return v + 1 if v < 1.5 else v


def line_of(s):
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)


def ok_row(x):
    return x[1] in ('', None) and not x[7] and x[4] not in (None, '') and x[5] not in (None, '', '0') and x[6] not in (None, '', '0')


ROWS = {}
for f in glob.glob('nowgoal_intl_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') not in (3, 31):
            continue
        mid = str(r['mid']); k = KO.get(mid)
        if k is None:
            continue
        rc = {'ah': [], 'ou': []}
        for x in (r.get('ah') or []):
            if ok_row(x) and x[0] < k:
                try: rc['ah'].append(((k - x[0]) / 3600, -line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        for x in (r.get('ou') or []):
            if ok_row(x) and x[0] < k:
                try: rc['ou'].append(((k - x[0]) / 3600, line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        rc['ah'].sort(key=lambda z: -z[0]); rc['ou'].sort(key=lambda z: -z[0])
        ROWS[(mid, r['cid'])] = rc

NSEAS = sorted(D.season.unique())
Dn = D[~D.dead].copy()
Dn['hg'] = ((Dn.tot + Dn.gd) / 2).round().astype(int); Dn['ag'] = ((Dn.tot - Dn.gd) / 2).round().astype(int)
Dn['y'] = ((Dn.hg > 0) & (Dn.ag > 0)).astype(int)
for m in MODELS:
    T = np.array([T_of(getattr(r, f'd_{m}'), r) for r in Dn.itertuples()])
    s_ = A_GOAL * Dn[f'd_{m}'].values
    Dn[f'pm_{m}'] = p_btts(np.maximum((T + s_) / 2, .15), np.maximum((T - s_) / 2, .15))
print(f'  αγωνιστικα (μη νεκρα) με diff: {len(Dn)} · σεζον {NSEAS}')

BOOKS = ((3, 'Crown'), (31, 'SBOBET'))
BK = {}
for cid, bname in BOOKS:
    rows = []
    for r in Dn.itertuples():
        rc = ROWS.get((str(r.mid), cid))
        if not rc or not rc['ah'] or not rc['ou']:
            continue
        a = rc['ah'][-1]; u = rc['ou'][-1]
        rows.append((r.Index, a[1], a[2], a[3], u[1], u[2], u[3]))
    X = pd.DataFrame(rows, columns=['ix', 'ah', 'oh', 'oa', 'oul', 'oo', 'ou']).set_index('ix')
    X = X[(X.oh > 1) & (X.oa > 1) & (X.oo > 1) & (X.ou > 1)]
    lh, la, resid = solve_market(X.ah.values, X.oh.values, X.oa.values, X.oul.values, X.oo.values, X.ou.values)
    X['pk'] = p_btts(lh, la); X['resid'] = resid; X['lsum'] = lh + la
    nb = int((resid > 0.005).sum()); X = X[X.resid <= 0.005]
    B = Dn.loc[X.index].join(X[['pk', 'lsum']])
    BK[bname] = B
    print(f'  {bname}: ματς με closing AH+O/U {len(X) + nb} · αντιστροφη ✗ {nb} · τελικο {len(B)} · '
          f'μεσο λ_m {B.lsum.mean():.3f} vs actual {B.tot.mean():.3f}')

both = set(BK['Crown'].index) & set(BK['SBOBET'].index)
print(f'  κοινα Crown∩SBOBET: {len(both)}')


def avg2(a, b):
    return (a + b) / 2


def flag(a, b):
    return '*' if (np.sign(a) != np.sign(b) and a != 0 and b != 0) else ' '


for m in MODELS:
    col = f'pm_{m}'
    print('\n' + '-' * 100)
    print(f'ΕΘΝΙΚΕΣ — {m} ({G["LAB"].get(m, m)}) · ενας αριθμος = μεσος Crown/SBOBET (* = διαφωνια προσημου)')
    print('-' * 100)
    print(f"{'σεζον':>7s} {'n C/S':>9s} {'BTTS%':>6s} | {'Brier mod':>9s} {'Brier mkt':>9s} {'ΔBrier±SE':>17s} | {'ΔLL±SE':>17s} | "
          f"{'b_mod(t)':>14s} | {'b_Δ offset(t)':>15s}")
    R = {}
    for s in NSEAS + ['POOLED']:
        mm = {}
        for bname in ('Crown', 'SBOBET'):
            d = BK[bname] if s == 'POOLED' else BK[bname][BK[bname].season == s]
            mm[bname] = metrics(d[col].values, d.pk.values, d.y.values)
        c, sb = mm['Crown'], mm['SBOBET']
        a = {k: avg2(c[k], sb[k]) for k in c if k != 'n'}; a['n'] = (c['n'], sb['n'])
        a['fl_b'] = flag(c['b_mod'], sb['b_mod']); a['fl_db'] = flag(c['dbrier'], sb['dbrier'])
        a['pos_c'] = c['b_mod'] > 0; a['pos_s'] = sb['b_mod'] > 0
        R[s] = a
        print(f"{s:>7s} {c['n']:4d}/{sb['n']:<4d} {a['base']*100:5.1f}% | {a['brier_m']:.5f} {a['brier_k']:.5f} "
              f"{fmt_se(a['dbrier'], a['dbrier_se'], 5):>16s}{a['fl_db']} | {fmt_se(a['dll'], a['dll_se'], 4):>17s} | "
              f"{a['b_mod']:+.3f}({a['t_mod']:+.2f}){a['fl_b']} | {a['b_delta']:+.3f}({a['t_delta']:+.2f})")
    print('  βαθμονομηση ανα πεμπτημοριο Δ = P_mod − P_mkt (pooled, μεσος 2 βιβλιων):')
    cc = calib_delta(BK['Crown'][col].values, BK['Crown'].pk.values, BK['Crown'].y.values)
    cs = calib_delta(BK['SBOBET'][col].values, BK['SBOBET'].pk.values, BK['SBOBET'].y.values)
    print(f"   {'μεσο Δ':>7s} {'P_mod':>6s} {'P_mkt':>6s} {'actual':>6s} {'act−mkt':>8s}")
    for x1, x2 in zip(cc, cs):
        print(f'   {avg2(x1[1], x2[1]):+.3f} {avg2(x1[2], x2[2]):.3f} {avg2(x1[3], x2[3]):.3f} {avg2(x1[4], x2[4]):.3f} '
              f'{avg2(x1[5], x2[5]):+.3f}{flag(x1[5], x2[5])}  (n ~{(x1[0] + x2[0]) // 2})')
    print('  ΥΠΟΘΕΤΙΚΟ ROI (τιμες = P_mkt του καθε βιβλιου με 5% margin· flat 1u · ΟΧΙ πραγματικες αποδοσεις):')
    print(f"   {'κανονας':>10s} | " + ' | '.join(f'{s:>19s}' for s in NSEAS + ['POOLED']))
    RO = {}
    for s in NSEAS + ['POOLED']:
        rr = {}
        for bname in ('Crown', 'SBOBET'):
            d = BK[bname] if s == 'POOLED' else BK[bname][BK[bname].season == s]
            rr[bname] = roi_table(d[col].values, d.pk.values, d.y.values)
        RO[s] = rr
    for key in list(EDGES) + ['allY', 'allN']:
        lab = f'edge≥{int(key*100)}%' if not isinstance(key, str) else ('τυφλο Yes' if key == 'allY' else 'τυφλο No')
        cells = []
        for s in NSEAS + ['POOLED']:
            c = RO[s]['Crown'][key]; sb = RO[s]['SBOBET'][key]
            n = (c[0] + sb[0]) / 2
            if c[0] > 1 and sb[0] > 1:
                cells.append(f'{n:4.0f} {avg2(c[1], sb[1])*100:+6.1f}±{avg2(c[2], sb[2])*100:4.1f}{flag(c[1], sb[1])}')
            else:
                cells.append(f'{n:4.0f}      —      ')
        print(f'   {lab:>10s} | ' + ' | '.join(f'{c_:>19s}' for c_ in cells))
    roi8 = {s: avg2(RO[s]['Crown'][0.08][1], RO[s]['SBOBET'][0.08][1]) for s in NSEAS + ['POOLED']}
    k1 = R['POOLED']['b_mod'] > 0 and R['POOLED']['t_mod'] >= 2 and sum(R[s]['b_mod'] > 0 for s in NSEAS) >= 3
    k2 = R['POOLED']['dbrier'] <= R['POOLED']['dbrier_se']
    k3n = sum(roi8[s] > 0 for s in NSEAS if np.isfinite(roi8[s]))
    k3 = k3n >= 3 and roi8['POOLED'] > 0
    print(f"  ΚΡΙΤΗΡΙΑ: Κ1 b_mod {R['POOLED']['b_mod']:+.3f} t {R['POOLED']['t_mod']:+.2f}, θετικο {sum(R[s]['b_mod'] > 0 for s in NSEAS)}/5 → {'✓' if k1 else '✗'} · "
          f"Κ2 ΔBrier/SE {R['POOLED']['dbrier']/R['POOLED']['dbrier_se']:+.2f} → {'✓' if k2 else '✗'} · "
          f"Κ3 ROI@8% θετικο {k3n}/5, pooled {roi8['POOLED']*100:+.1f}% → {'✓' if k3 else '✗'}  ⇒  "
          f"{'ΚΑΛΥΠΤΟΝΤΑΙ (PASS)' if (k1 and k2 and k3) else 'ΔΕΝ ΚΑΛΥΠΤΟΝΤΑΙ (FAIL)'}")

print("""
ΣΗΜΕΙΩΣΕΙΣ:
 - P_mkt απο closing AH + closing O/U με ανεξαρτητο Poisson (χωρις draw-boost) — το ιδιο και για το μοντελο.
   Το P_mkt ΔΕΝ ειναι πραγματικη τιμη BTTS· ειναι αυτο που «λενε» οι δυο αγορες μαζι.
 - ΥΠΟΘΕΤΙΚΟ ROI: ισοδυναμει με «το μοντελο κερδιζει την αγορα-proxy + 5% margin». Πραγματικες τιμες BTTS
   μπορει να περιεχουν πληροφορια (ή μεροληψια) που το proxy δεν εχει.
 - Εγχωρια: 4 σεζον (2223-2526)· 2122 = μονο prior.
""")
