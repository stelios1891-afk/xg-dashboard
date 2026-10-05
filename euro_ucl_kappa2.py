# -*- coding: utf-8 -*-
"""euro_ucl_kappa2.py — ΒΗΜΑ 2β (εντολη 11/9): κ ΜΟΝΟ για το ΝΕΟ 36-ομαδων format.

Το euro_ucl_kappa (ενιαιο κ, 4 σεζον) περασε 4/5 κριτηρια αλλα εκοψε στο Brier totals:
το ενιαιο κ ΥΠΕΡ-διορθωνε το παλιο format (z=+1.6) και ΥΠΟ-διορθωνε το νεο (z=−2.3).
Εδω: λ_φαβορι x κ ΜΟΝΟ σε UCL ματς ΝΕΟΥ format (2425+2526) — γραμμη 3 του
προ-γραμμενου πινακα Fable 5.2 («κλιμακα απο το νεο format και μετα, 2 σεζον αποδειξη»).
Το παλιο format (2223+2324) μενει ΑΝΕΓΓΙΧΤΟ (control). Το live 2627 ΕΙΝΑΙ νεο format.

ΕΚΤΙΜΗΣΗ: LOSO 2-fold (2425<->2526), grid 1.00-1.30, Poisson LL γκολ στα UCL-νεο-format train.
ΚΡΙΤΗΡΙΑ (ιδια 5, αξιολογηση ΣΤΟ ΝΕΟ FORMAT): 1. γκολ |z|<=1 · 2. ισοπαλιες |z|<=1.5 ·
3. P(φ>=2) |z|<=1.5 · 4. Brier totals καλυτερο και στις 2 σεζον · 5. RPS οχι χειροτερο.
ΦΡΟΥΡΟΙ: UEL/UECL + παλιο format ανεγγιχτα · ογκος+ROI streams πριν/μετα.
ΚΑΘΑΡΑ ΠΕΡΙΓΡΑΦΙΚΟ — κανενα live αρχειο δεν αγγιζεται. Output: euro_ucl_kappa2_out.txt.
"""
import io, json, glob, pickle, math, sys, time, contextlib
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

T0 = time.time()
GAMMA_LIVE = -0.470
CLOSE_TOL = 900
EU_DRAW_SCALE = 0.85

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import fs_upgrade_full as F
import picks

EU_EVAL = list(F.EU_EVAL)


def run_arm_gaps(B_ALL):
    S = B_ALL[B_ALL.mid.map(F.has_odds)].sort_values(['date', 'mid']).reset_index(drop=True)
    MIDS = list(S.mid); N = len(S)

    B2o = B_ALL.set_index('mid').reindex(F.MIDS_O)
    for c, v0 in [('bxh8', F.E0.bxh8.values), ('bxa8', F.E0.bxa8.values)]:
        B2o[c] = B2o[c].fillna(pd.Series(v0, index=F.MIDS_O))
    B2o['lg_h'] = B2o['lg_h'].fillna(pd.Series(F.E0.lg_h.values, index=F.MIDS_O))
    B2o['lg_a'] = B2o['lg_a'].fillna(pd.Series(F.E0.lg_a.values, index=F.MIDS_O))
    SEA_O = F.E0.sea.values
    B2o['sea'] = pd.Series(SEA_O, index=F.MIDS_O)
    B2o['gh'] = F.E0.gh.values; B2o['ga'] = F.E0.ga.values
    FIT2 = {sea: F.fit_fold(B2o.reset_index(), sea) for sea in EU_EVAL}

    eh_o = np.array([F.ELO.get(m, (np.nan, np.nan))[0] for m in F.MIDS_O], float)
    ea_o = np.array([F.ELO.get(m, (np.nan, np.nan))[1] for m in F.MIDS_O], float)
    ath_o = B2o.att_h.values; lkh_o = B2o.leak_h.values
    ata_o = B2o.att_a.values; lka_o = B2o.leak_a.values
    srh_o = B2o.src_h.values; sra_o = B2o.src_a.values
    LGH_O = B2o.lg_h.values; LGA_O = B2o.lg_a.values
    has_comp_o = ~np.isnan(B2o.lXs.values)
    CAL = {}
    for fold in EU_EVAL:
        xs = []; ys = []
        tr = (SEA_O != fold) & has_comp_o
        for i in np.where(tr)[0]:
            for (srcv, lg, at, lk, el) in [(srh_o[i], LGH_O[i], ath_o[i], lkh_o[i], eh_o[i]),
                                           (sra_o[i], LGA_O[i], ata_o[i], lka_o[i], ea_o[i])]:
                if srcv == 'goals' or (isinstance(el, float) and np.isnan(el)) or lg not in F.POFF:
                    continue
                ys.append(F.RHO * F.s_player(lg) + 0.5 * (at - lk))
                xs.append(el / 100.0)
        xs = np.array(xs); ys = np.array(ys)
        b = np.cov(xs, ys)[0, 1] / np.var(xs)
        a = ys.mean() - b * xs.mean()
        CAL[fold] = (a, b)

    samp_lgs = sorted(set(S.lg_h) | set(S.lg_a))
    bridge2 = {}
    for lg in samp_lgs:
        if lg in F.POFF:
            continue
        lid = F.LID.get(lg)
        if lid is not None and lid in F.id2off:
            bridge2[lg] = F.id2off[lid]

    def s_v4(lg, fold):
        sp = F.s_player(lg)
        if sp is not None:
            return sp
        if lg in bridge2:
            return -F.GAMMA_PLAYER * bridge2[lg][1]
        if lg in F.off_elo:
            return -F.GAMMA_PLAYER * F.off_elo[lg]
        return F.fitted_s(FIT2, lg, fold)

    SEA = S.sea.values
    HFV = pd.Series(SEA).map(F.HF).values
    att_h = S.att_h.values; leak_h = S.leak_h.values
    att_a = S.att_a.values; leak_a = S.leak_a.values
    lXs = S.lXs.values
    src_h = S.src_h.values; src_a = S.src_a.values
    LGH = S.lg_h.values; LGA = S.lg_a.values
    eh = np.array([F.ELO.get(m, (np.nan, np.nan))[0] for m in MIDS], float)
    ea = np.array([F.ELO.get(m, (np.nan, np.nan))[1] for m in MIDS], float)

    D = np.array([s_v4(LGH[i], SEA[i]) - s_v4(LGA[i], SEA[i]) for i in range(N)])
    ah = att_h.copy(); lh_ = leak_h.copy(); aa = att_a.copy(); la_ = leak_a.copy()
    for i in range(N):
        a_f, b_f = CAL[SEA[i]]
        for (is_h, srcv, lg, el) in [(True, src_h[i], LGH[i], eh[i]), (False, src_a[i], LGA[i], ea[i])]:
            if srcv != 'goals' or np.isnan(el):
                continue
            sig = a_f + b_f * el / 100.0
            u = sig - F.RHO * s_v4(lg, SEA[i])
            if is_h:
                ah[i] = u; lh_[i] = -u
            else:
                aa[i] = u; la_[i] = -u
    LH = np.exp(lXs + ah + la_) * HFV * np.exp(F.RHO * D)
    LA = np.exp(lXs + aa + lh_) / HFV * np.exp(-F.RHO * D)
    return S, MIDS, LH, LA, D, s_v4


S_df, MIDS_G, LH_G, LA_G, D, _sv4 = run_arm_gaps(F.B_b)

V6 = pickle.load(open('euro_v6_preds.pkl', 'rb'))
W2 = pickle.load(open(__import__('os').environ.get('W2_IN', 'euro_v6w2_preds.pkl'), 'rb'))   # 5/10: W2_IN για τεστ κοκκινων
assert list(V6['mids']) == list(W2['mids']), 'mids mismatch — ΣΤΑΜΑΤΩ'
assert list(V6['mids']) == MIDS_G, 'mids mismatch pkl vs rebuild — ΣΤΑΜΑΤΩ'
MIDS = V6['mids']
LH2 = np.array(W2['lh']); LA2 = np.array(W2['la'])
GD = np.array(V6['gd']); SEA = np.array(V6['sea'])
COMP = np.array(V6['comp']); PHASE = np.array(V6['phase'])
DATES = V6['date']
FM = np.array([(h == 'shots' and a == 'shots') for h, a in zip(V6['src_h'], V6['src_a'])])
N = len(MIDS)

SEASONS = ('2223', '2324', '2425', '2526')
NEW_SEAS = ('2425', '2526')
UCL = COMP == 'ChampionsLeague'
NEW36 = np.isin(np.array(V6['sea']), NEW_SEAS)

C = GAMMA_LIVE * D
LH2c = np.maximum(LH2 - C / 2.0, 0.05); LA2c = np.maximum(LA2 + C / 2.0, 0.05)
FAVH = LH2c >= LA2c          # φαβορι ΜΟΝΤΕΛΟΥ (live-εφαρμοσιμο)
GH = S_df.gh.values.astype(float); GA = S_df.ga.values.astype(float)

# ---------------- Crown closing: AH + OU ----------------
KO = {}
for m, d in zip(MIDS, DATES):
    try:
        KO[m] = int(pd.Timestamp(d).tz_localize('UTC').timestamp())
    except Exception:
        pass


def parse_line(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None

SNAP = {}; SNAP_OU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r['cid'] != 3:
            continue
        mid = str(r['mid']); ko = KO.get(mid)
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
        if rows and ko:
            rows.sort()
            rows = [x for x in rows if x[0] <= ko + CLOSE_TOL]
            if rows:
                SNAP[mid] = rows[-1][1:]
        orows = []
        for mt, ov, g, un in r.get('ou') or []:
            gl = parse_line(g)
            try:
                oo = float(ov) + 1; ou_ = float(un) + 1
            except (TypeError, ValueError):
                continue
            if gl is None or mt is None:
                continue
            orows.append((int(mt), gl, oo, ou_))
        if orows and ko:
            orows.sort()
            orows = [x for x in orows if x[0] <= ko + CLOSE_TOL]
            if orows:
                SNAP_OU[mid] = orows[-1][1:]

MS = np.array([-SNAP[m][0] if m in SNAP else np.nan for m in MIDS])
HASM = ~np.isnan(MS)
agree = np.mean((MS[HASM & UCL] >= 0) == FAVH[HASM & UCL])
print(f'Δειγμα: {N} · UCL: {int(UCL.sum())} · με AH closing: {int(HASM.sum())} · με OU closing: '
      f'{sum(1 for m in MIDS if m in SNAP_OU)}')
print(f'[SANITY] φαβορι μοντελου == φαβορι αγορας (UCL): {agree*100:.1f}%')

# ---------------- κ: εφαρμογη + LOSO fit ----------------
SCOPE = UCL & NEW36     # το κ αγγιζει ΜΟΝΟ αυτα


def apply_kappa(kap):
    lh = LH2c.copy(); la = LA2c.copy()
    m = SCOPE & FAVH
    lh[m] = lh[m] * kap
    m2 = SCOPE & ~FAVH
    la[m2] = la[m2] * kap
    return lh, la


def pois_ll(lh, la, mask):
    ll = (GH[mask] * np.log(lh[mask]) - lh[mask]) + (GA[mask] * np.log(la[mask]) - la[mask])
    return ll.sum()

GRID = np.arange(1.000, 1.3001, 0.005)
CHOSEN = {}
for fold in NEW_SEAS:
    tr = SCOPE & (SEA != fold)     # train = η ΑΛΛΗ σεζον νεου format
    best = None
    for kap in GRID:
        lh, la = apply_kappa(kap)
        ll = pois_ll(lh, la, tr)
        if best is None or ll > best[0]:
            best = (ll, kap)
    CHOSEN[fold] = best[1]
print('\nLOSO κ (2-fold, νεο format): ' + ' · '.join(f'{s}: {CHOSEN[s]:.3f}' for s in NEW_SEAS))

LH_N = LH2c.copy(); LA_N = LA2c.copy()
for fold in NEW_SEAS:
    m = SEA == fold
    lh, la = apply_kappa(CHOSEN[fold])
    LH_N[m] = lh[m]; LA_N[m] = la[m]
d_old = max(np.abs(LH_N - LH2c)[UCL & ~NEW36].max(), np.abs(LA_N - LA2c)[UCL & ~NEW36].max())
print(f'[SANITY] παλιο format ανεγγιχτο: max|Δλ| = {d_old:.1e}')

# ---------------- dists ----------------
def scaled_dist(lh, la):
    dist = picks.gd_dist(max(lh, 0.05), max(la, 0.05))
    p0 = dist.get(0, 0.0)
    new0 = p0 * EU_DRAW_SCALE
    fac = (1.0 - new0) / (1.0 - p0)
    return {k: (new0 if k == 0 else p * fac) for k, p in dist.items()}

DIST_B = [scaled_dist(LH2c[i], LA2c[i]) for i in range(N)]
DIST_N = [scaled_dist(LH_N[i], LA_N[i]) for i in range(N)]

# ---------------- 1-3) γκολ / ισοπαλιες / διαλυσεις (UCL OOS) ----------------
print('\n' + '=' * 112)
print('=== ΚΡΙΤΗΡΙΑ 1-3 (UCL, OOS): γκολ / ισοπαλιες / διαλυσεις — ΠΡΙΝ -> ΜΕΤΑ ===')
TG = GH + GA


def zrow(label, mask):
    mk = mask & UCL
    n = int(mk.sum())
    if n < 20:
        print(f'{label:>22s} n={n}')
        return
    for tag, LHx, LAx, DV in (('ΠΡΙΝ', LH2c, LA2c, DIST_B), ('ΜΕΤΑ', LH_N, LA_N, DIST_N)):
        em = (LHx + LAx)[mk].mean(); ea_ = TG[mk].mean()
        se_g = TG[mk].std(ddof=1) / math.sqrt(n)
        idx = np.where(mk)[0]
        px = float(np.mean([DV[i].get(0, 0.0) for i in idx]))
        ax = float(np.mean(GD[mk] == 0))
        zx = (ax - px) / math.sqrt(max(px * (1 - px), 1e-9) / n)
        pf2 = float(np.mean([sum(p for k, p in DV[i].items() if (k >= 2 if FAVH[i] else k <= -2)) for i in idx]))
        af2 = float(np.mean([(GD[i] >= 2 if FAVH[i] else GD[i] <= -2) for i in idx]))
        zf = (af2 - pf2) / math.sqrt(max(pf2 * (1 - pf2), 1e-9) / n)
        print(f'{label:>22s} {tag} n={n:4d} | γκολ {em:.3f} vs {ea_:.3f} (z={(em-ea_)/se_g:+.1f}) | '
              f'Χ {px*100:4.1f}% vs {ax*100:4.1f}% (z={zx:+.1f}) | '
              f'P(φ>=2) {pf2*100:4.1f}% vs {af2*100:4.1f}% (z={zf:+.1f})')

zrow('ΝΕΟ FORMAT (κριτηρια)', NEW36)
for s in NEW_SEAS:
    zrow(s, SEA == s)
zrow('παλιο (control, ιδιο)', ~NEW36)
for lo, hi, zl in [(0.0, 0.5, 'νεο |sup|<0.5'), (0.5, 1.0, 'νεο 0.5-1'), (1.0, 99.0, 'νεο >=1')]:
    zrow(zl, NEW36 & HASM & (np.abs(MS) >= lo) & (np.abs(MS) < hi))

# ---------------- 4) Brier totals στη γραμμη Crown OU ----------------
def pois_cdf_probs(lam, half_line):
    """P(total > half_line), P(total < half_line) για γραμμη x.5 (οχι push)."""
    kmax = 15
    pmf = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(kmax + 1)]
    p_under = sum(pmf[k] for k in range(kmax + 1) if k < half_line)
    return 1.0 - p_under, p_under


def ou_probs(lam, line):
    """(p_over_win, p_push, p_under_win) για γραμμη (και quarter)."""
    q2 = round(line * 2)
    if q2 % 2 == 1:   # x.5
        po, pu = pois_cdf_probs(lam, line)
        return po, 0.0, pu
    if abs(line - round(line)) < 1e-9:   # ακεραια
        kmax = 15
        pmf = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(kmax + 1)]
        po = sum(pmf[k] for k in range(kmax + 1) if k > line)
        pu = sum(pmf[k] for k in range(kmax + 1) if k < line)
        return po, 1.0 - po - pu, pu
    lo, hi = line - 0.25, line + 0.25
    o1, p1, u1 = ou_probs(lam, lo)
    o2, p2, u2 = ou_probs(lam, hi)
    return (o1 + o2) / 2, (p1 + p2) / 2, (u1 + u2) / 2


print('\n=== ΚΡΙΤΗΡΙΟ 4: Brier του P(over) στη γραμμη Crown closing (UCL ΝΕΟ format, χωρις push) ===')
for s in ('ΟΛΕΣ',) + NEW_SEAS:
    bb = []; bn = []
    for i, m in enumerate(MIDS):
        if not SCOPE[i] or (s != 'ΟΛΕΣ' and SEA[i] != s) or m not in SNAP_OU:
            continue
        line = SNAP_OU[m][0]
        if abs(TG[i] - line) < 1e-9:
            continue   # push
        y = 1.0 if TG[i] > line else 0.0
        for tag, LHx, LAx, acc in (('b', LH2c, LA2c, bb), ('n', LH_N, LA_N, bn)):
            po, pp, pu = ou_probs(LHx[i] + LAx[i], line)
            p = po / max(po + pu, 1e-9)
            acc.append((p - y) ** 2)
    if len(bb) < 20:
        print(f'  {s}: n={len(bb)}')
        continue
    d_ = np.mean(bn) - np.mean(bb)
    se = (np.array(bn) - np.array(bb)).std(ddof=1) / math.sqrt(len(bb))
    print(f'  {s:>5s} n={len(bb):4d} | Brier {np.mean(bb):.4f} -> {np.mean(bn):.4f} '
          f'Δ={d_:+.4f}±{se:.4f} ({"καλυτερο" if d_ < 0 else "ΧΕΙΡΟΤΕΡΟ"})')

# ---------------- 5) RPS 1X2 paired ----------------
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))


def rps_i(dist, o):
    ph = sum(p for k, p in dist.items() if k > 0)
    pdw = dist.get(0, 0.0)
    return 0.5 * ((ph - (o == 0)) ** 2 + (ph + pdw - (o <= 1)) ** 2)

print('\n=== ΚΡΙΤΗΡΙΟ 5: RPS 1X2 (UCL ΝΕΟ format, paired) — οχι χειροτερο ===')
for s in ('ΟΛΕΣ',) + NEW_SEAS:
    idx = [i for i in range(N) if SCOPE[i] and (s == 'ΟΛΕΣ' or SEA[i] == s)]
    rb = np.array([rps_i(DIST_B[i], OUT3[i]) for i in idx])
    rn = np.array([rps_i(DIST_N[i], OUT3[i]) for i in idx])
    d_ = rn.mean() - rb.mean()
    se = (rn - rb).std(ddof=1) / math.sqrt(len(idx))
    print(f'  {s:>5s} n={len(idx):4d} | RPS {rb.mean():.4f} -> {rn.mean():.4f} Δ={d_:+.5f}±{se:.5f} '
          f'({"καλυτερο" if d_ < 0 else ("ισο" if abs(d_) < 1e-6 else "ΧΕΙΡΟΤΕΡΟ")})')

# ---------------- ΦΡΟΥΡΟΣ: streams UCL πριν/μετα ----------------
def collect(DV, LHx, LAx):
    dogs = []; favs = []; overs = []; unders = []
    for i, mid in enumerate(MIDS):
        if not UCL[i]:
            continue
        s = SNAP.get(mid)
        if s:
            lf, oh, oa = s
            dist = DV[i]
            for side, ud, odds in [(1, lf, oh), (-1, -lf, oa)]:
                if ud < picks.MIN_LINE or not (picks.OMIN <= odds <= picks.OMAX):
                    continue
                pw, pp = picks.p_cover(dist, side, ud)
                edge = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                dogs.append(dict(i=i, edge=edge, pnl=picks.settle(GD[i], side, ud, odds)))
            for side, ln, o in ((1, lf, oh), (-1, -lf, oa)):
                if ln > -picks.MIN_LINE + 1e-9 or not (picks.OMIN <= o <= picks.OMAX):
                    continue
                pw, pp = picks.p_cover(dist, side, ln)
                edge = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                favs.append(dict(i=i, edge=edge, pnl=picks.settle(GD[i], side, ln, o)))
        so = SNAP_OU.get(mid)
        if so:
            line, oo, ou_ = so
            lamT = LHx[i] + LAx[i]
            po, pp_, pu = ou_probs(lamT, line)
            for stream, pw, odds in ((overs, po, oo), (unders, pu, ou_)):
                if not (picks.OMIN <= odds <= picks.OMAX):
                    continue
                edge = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp_)
                won = (TG[i] > line) if stream is overs else (TG[i] < line)
                lost = (TG[i] < line) if stream is overs else (TG[i] > line)
                # quarter settle: μισο push
                gap = TG[i] - line if stream is overs else line - TG[i]
                if abs(gap) < 0.26 and abs(gap) > 1e-9:
                    pnl = (odds - 1) / 2 if gap > 0 else -0.5
                elif abs(gap) < 1e-9:
                    pnl = 0.0
                else:
                    pnl = (odds - 1) if gap > 0 else -1.0
                stream.append(dict(i=i, edge=edge, pnl=pnl))
    return dogs, favs, overs, unders

DG_B, FV_B, OV_B, UN_B = collect(DIST_B, LH2c, LA2c)
DG_N, FV_N, OV_N, UN_N = collect(DIST_N, LH_N, LA_N)


def roi_cell(B, thr, mask=None):
    b = [x['pnl'] for x in B if FM[x['i']] and x['edge'] >= thr and (mask is None or mask[x['i']])]
    if len(b) < 3:
        return f'n={len(b):4d} {"-":>13s}'
    m_ = np.mean(b); se = np.std(b, ddof=1) / math.sqrt(len(b))
    return f'n={len(b):4d} {m_*100:+6.2f}±{se*100:5.2f}'

print('\n' + '=' * 112)
print('=== ΦΡΟΥΡΟΣ: UCL streams ΠΡΙΝ -> ΜΕΤΑ — ΜΟΝΟ ΝΕΟ format (το παλιο αμεταβλητο) ===')
for tag, DG, FV, OV, UN in (('ΠΡΙΝ', DG_B, FV_B, OV_B, UN_B), ('ΜΕΤΑ', DG_N, FV_N, OV_N, UN_N)):
    print(f'  {tag} | dogs@4  {roi_cell(DG, .04, NEW36)} | dogs@10 {roi_cell(DG, .10, NEW36)} | '
          f'favs@4  {roi_cell(FV, .04, NEW36)} | favs@10 {roi_cell(FV, .10, NEW36)}')
    print(f'  {tag} | overs@4 {roi_cell(OV, .04, NEW36)} | overs@10 {roi_cell(OV, .10, NEW36)} | '
          f'unders@4 {roi_cell(UN, .04, NEW36)} | unders@10 {roi_cell(UN, .10, NEW36)}')
print('\n-- favs@4 ανα σεζον (νεο format) --')
for s in NEW_SEAS:
    for tag, FV in (('ΠΡΙΝ', FV_B), ('ΜΕΤΑ', FV_N)):
        b = [x['pnl'] for x in FV if FM[x['i']] and x['edge'] >= .04 and SEA[x['i']] == s]
        print(f'   {s} {tag}: n={len(b):3d} ' + (f'{np.mean(b)*100:+6.1f}' if len(b) >= 3 else '-'))

print('\n[ΣΗΜΕΙΩΣΗ] UEL/UECL: ΚΑΜΙΑ αλλαγη by construction (το κ εφαρμοζεται μονο σε COMP==UCL).')
print(f'\nΤΕΛΟΣ [{time.time()-T0:.0f}s]')
