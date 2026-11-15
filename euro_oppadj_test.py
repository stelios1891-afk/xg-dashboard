"""
euro_oppadj_test.py — 9/10/2026 (Στελιος: «η διορθωση αντιπαλου ειναι το αδυναμο σημειο — μηπως το κανουμε καλυτερο;»).
Φετινα ευρωπαικα ματς στο ευρωπαικο rating (euro_inseason_eu_test, 26/9) — ΒΕΛΤΙΩΣΗ ΤΗΣ ΔΙΟΡΘΩΣΗΣ ΑΝΤΙΠΑΛΟΥ.
Ευρημα κωδικα: η ΠΡΟΒΛΕΨΗ εχει χασμα λιγκας V4 + γ (−0.47, live_stack) — η ΔΙΟΡΘΩΣΗ των obs μονο V4 → ασυνεπεια,
συμβατη με τη μεροληψια 26/9 (top7 επιθ +0.082 / αμυνα −0.062, αλλες λιγκες επιθ −0.054).
ΕΚΔΟΧΕΣ (ολες με LOSO w_in ∈ {0.5,1,2}):
  V0 = 26/9 (αναφορα)
  B1 = «αναλογια προς την προβλεψη του μοντελου»: obs = rating_τωρα × (πραγματικο / λ πληρους live αλυσιδας για εκεινο το ματς)
       (ιδιος αντιπαλος, ιδια λιγκα, ιδιο γ/κ/εδρα με την προβλεψη· fallback V0 αν δεν βγαινει λ)
  B2 = V0 με χασμα λιγκας ×f στη διορθωση, f ∈ {1.0,1.25,1.5,1.75} (LOSO μαζι με w_in)
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραμμενα πριν την εκτελεση):
  (1) vs V0: RPS επηρεαζομενων pooled καλυτερο ΚΑΙ καλυτερο σε ≥3/4 σεζον.
  (2) ΜΕΡΟΛΗΨΙΑ ομαδων: |επιθ| & |αμυνα| < 0.05 ΚΑΙ στις ομαδες top7 ΚΑΙ στις αλλες λιγκες.
  (3) vs ΧΩΡΙΣ φετινα (base): RPS επηρεαζομενων <0 σε ≥3/4 σεζον ΚΑΙ pooled <0.
  (4) ΦΡΟΥΡΟΣ ROI (σημερινη τιμολογηση: φαβ σωστα τεταρτα / dogs p_cover, UCL fav@10 dog@4, αλλα fav@4 dog@10, FotMob+FotMob,
      μεσος Crown/Pinnacle κλεισιμο): ΟΛΑ και UCL νεο ≥ base − 1SE.
  «Καλυτερη διορθωση» = (1)&(2). «Υποψηφιο live» = (1)&(2)&(3)&(4).
"""
import sys, io, math, contextlib, time
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
T0 = time.time()
src = open('euro_inseason_eu_test.py', encoding='utf-8').read()
A = src[:src.index('# ================================================================ ΠΡΟΒΛΕΨΕΙΣ')]
Bk = src[src.index('KO = {}\nfor m, d in zip(MIDS, DATES):'):src.index("BOOKS_ROI = {'Crown': CROWN, 'Pinnacle': PIN}")]
A = A.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'oa'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(A, g)
    exec(Bk, g)
print(f'[setup {time.time() - T0:.0f}s]')
N, SEA, COMP, MIDS, GD, HID, AID, DATES, FMm, PH, EU_EVAL = (g[k] for k in (
    'N', 'SEA', 'COMP', 'MIDS', 'GD', 'HID', 'AID', 'DATES', 'FMm', 'PH', 'EU_EVAL'))
SS, s_v4, rate_base, predict_arm, make_rate_new, live_stack = (g[k] for k in (
    'SS', 's_v4', 'rate_base', 'predict_arm', 'make_rate_new', 'live_stack'))
eng2, HF, RHO, EPS, CAL, ELO, GKEYS, picks, CROWN, PIN = (g[k] for k in (
    'eng2', 'HF', 'RHO', 'EPS', 'CAL', 'ELO', 'GKEYS', 'picks', 'CROWN', 'PIN'))
GAM, KAPPA, NEWF, DRAW = g['GAMMA_LG_DEFLATE'], g['UCL_FAV_SCALE'], g['NEW_FMT'], g['EU_DRAW_SCALE']
TOP7 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie'}
EQ0 = g['eq_obs']
SEAS = list(EU_EVAL)


# ---------------- προβλεψη ΕΝΟΣ ευρωπαικου ματς (ιδια με predict_arm + live_stack, base ratings) ----------------
def side_terms(st, tid, fold, d, mid, is_home):
    SL, XL = eng2.ruler(st['lg'], st['sea'], d)
    Ax, Dx, SF, SA = rate_base(st, tid, fold, d)
    att = math.log(max((SF / SL) * (Ax / XL), EPS))
    leak = math.log(max((SA / SL) * (Dx / XL), EPS))
    if (st['lg'], st['sea']) not in GKEYS and st['goal_only']:
        el = ELO.get(mid, (np.nan, np.nan))[0 if is_home else 1]
        try:
            el = float(el)
        except (TypeError, ValueError):
            el = float('nan')
        if not math.isnan(el):
            a_f, b_f = CAL[fold]
            u = a_f + b_f * el / 100.0 - RHO * s_v4(st['lg'], fold)
            att, leak = u, -u
    return SL, XL, att, leak


def pred_one(hid, aid, d, fold, comp, mid):
    sh, sa = SS(hid, d), SS(aid, d)
    if sh is None or sa is None:
        return None
    if (sh['prior'] is None and sh['cur'] is None) or (sa['prior'] is None and sa['cur'] is None):
        return None
    SLh, XLh, ah, lh_ = side_terms(sh, hid, fold, d, mid, True)
    SLa, XLa, aa, la_ = side_terms(sa, aid, fold, d, mid, False)
    lXs = math.log(((SLh * SLa) ** 0.5) * ((XLh * XLa) ** 0.5))
    D_ = s_v4(sh['lg'], fold) - s_v4(sa['lg'], fold)
    hf = HF[fold]
    LH = math.exp(lXs + ah + la_) * hf * math.exp(RHO * D_)
    LA = math.exp(lXs + aa + lh_) / hf * math.exp(-RHO * D_)
    C = GAM * D_
    LH = max(LH - C / 2, .05); LA = max(LA + C / 2, .05)
    if comp == 'ChampionsLeague' and fold in NEWF:
        if LH >= LA:
            LH *= KAPPA
        else:
            LA *= KAPPA
    return LH, LA


N_FB = {'B1': 0}


def eq_B1(tid, rec, fold, lg, sea):
    mid, d_eu, ish, xgf, xga, gf, ga, oid, comp = rec
    key = (tid, mid, fold, lg, sea)
    if key in g['_OBS']:
        return g['_OBS'][key]
    st = SS(tid, d_eu)
    p = pred_one(tid, oid, d_eu, fold, comp, mid) if ish else pred_one(oid, tid, d_eu, fold, comp, mid)
    if p is None or st is None or st['lg'] != lg or st['sea'] != sea:
        N_FB['B1'] += 1
        return EQ0(tid, rec, fold, lg, sea)
    lf, la = (p[0], p[1]) if ish else (p[1], p[0])
    r = rate_base(st, tid, fold, d_eu)
    b = g['b_blend']
    raw_att = b * xgf + (1 - b) * gf
    raw_def = b * xga + (1 - b) * ga
    o = (r[0] * r[2] * raw_att / lf, r[1] * r[3] * raw_def / la, d_eu, comp)
    g['_OBS'][key] = o
    return o


def make_B2(f):
    def eq(tid, rec, fold, lg, sea):
        key = (tid, rec[0], fold, lg, sea)
        if key in g['_OBS'] and key in DONE2:
            return g['_OBS'][key]
        o = EQ0(tid, rec, fold, lg, sea)
        if o is None:
            return None
        so = SS(rec[7], rec[1])
        if so is not None:
            dl = RHO * (s_v4(lg, fold) - s_v4(so['lg'], fold))
            o = (o[0] * math.exp(-(f - 1) * dl), o[1] * math.exp((f - 1) * dl), o[2], o[3])
        g['_OBS'][key] = o
        DONE2.add(key)
        return o
    return eq


DONE2 = set()

# ---------------- μετρικες ----------------
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))


def eu_dist(lh, la):
    dist = picks.gd_dist(max(lh, .05), max(la, .05))
    px = dist.get(0, 0.0)
    k = (1 - DRAW * px) / (1 - px)
    return {gg: (p * DRAW if gg == 0 else p * k) for gg, p in dist.items()}


def rps_arr(LH, LA):
    R = np.zeros(N)
    for i in range(N):
        dist = eu_dist(LH[i], LA[i])
        ph = sum(p for k_, p in dist.items() if k_ > 0)
        pdw = dist.get(0, 0.0)
        o = OUT3[i]
        R[i] = 0.5 * ((ph - (o == 0)) ** 2 + (ph + pdw - (o <= 1)) ** 2)
    return R


def bias_rows():
    rows = []
    for (tid, mid_, fold, lg, sea) in g['USED']:
        o = g['_OBS'].get((tid, mid_, fold, lg, sea))
        if o is None:
            continue
        st = SS(tid, o[2])
        if st is None or st['lg'] != lg or st['sea'] != sea:
            continue
        r = rate_base(st, tid, fold, o[2])
        rows.append(dict(fold=fold, comp=o[3], top7=lg in TOP7, att=o[0] - r[0] * r[2], dfn=o[1] - r[1] * r[3]))
    return pd.DataFrame(rows)


def run(eqfn, w):
    g['eq_obs'] = eqfn
    g['_OBS'] = {}
    g['USED'] = set()
    DONE2.clear()
    LH, LA = predict_arm(make_rate_new(w, track=True))
    return live_stack(LH, LA), bias_rows()


BASE = live_stack(*predict_arm(rate_base))
R_BASE = rps_arr(*BASE)
g['eq_obs'] = EQ0
g['_OBS'] = {}
NIH = np.array([len(g['inseason'](HID[i], DATES[i], SEA[i], SS(HID[i], DATES[i]))) for i in range(N)])
NIA = np.array([len(g['inseason'](AID[i], DATES[i], SEA[i], SS(AID[i], DATES[i]))) for i in range(N)])
AFF = (NIH >= 1) | (NIA >= 1)
print(f'επηρεαζομενα: {int(AFF.sum())}/{N}')
ARMS = {}
for w in (0.5, 1.0, 2.0):
    ARMS[('V0', 1.0, w)] = run(EQ0, w)
    ARMS[('B1', 1.0, w)] = run(eq_B1, w)
    ARMS[('B2', 1.0, w)] = ARMS[('V0', 1.0, w)]
    for f in (1.25, 1.5, 1.75):
        ARMS[('B2', f, w)] = run(make_B2(f), w)
    print(f'[w={w} {time.time() - T0:.0f}s]')
RPS = {k: rps_arr(*v[0]) for k, v in ARMS.items()}


def loso(fam):
    keys = [k for k in RPS if k[0] == fam]
    ch = {}
    LH = np.empty(N); LA = np.empty(N); R = np.empty(N)
    for s in SEAS:
        tr = AFF & (SEA != s)
        best = min(keys, key=lambda k: RPS[k][tr].mean())
        ch[s] = best
        m = SEA == s
        LH[m] = ARMS[best][0][0][m]; LA[m] = ARMS[best][0][1][m]; R[m] = RPS[best][m]
    return ch, (LH, LA), R


def dse(x):
    return float(x.mean()), float(x.std(ddof=1) / math.sqrt(len(x)))


RES = {fam: loso(fam) for fam in ('V0', 'B1', 'B2')}
print('\n1. RPS ΕΠΗΡΕΑΖΟΜΕΝΩΝ (×10⁻³, LOSO) — Δ vs ΧΩΡΙΣ φετινα (και vs V0)')
for fam in ('V0', 'B1', 'B2'):
    ch, L, R = RES[fam]
    R0 = RES['V0'][2]
    cells = []
    for s in SEAS + ['ΟΛΑ']:
        m = AFF & ((SEA == s) if s != 'ΟΛΑ' else np.ones(N, bool))
        a, sa = dse(R[m] - R_BASE[m])
        txt = f'{s}: {1000 * a:+.2f}±{1000 * sa:.2f}'
        if fam != 'V0':
            b, sb = dse(R[m] - R0[m])
            txt += f' (vs V0 {1000 * b:+.2f}±{1000 * sb:.2f})'
        cells.append(txt)
    print(f'   {fam}  επιλογες ' + ' '.join(f'{s}:w{k[2]}' + (f'/f{k[1]}' if fam == 'B2' else '') for s, k in ch.items()))
    print('       ' + ' · '.join(cells))
print('\n   ανα φαση (vs χωρις φετινα, ×10⁻³):')
for fam in ('V0', 'B1', 'B2'):
    R = RES[fam][2]
    cells = []
    for p in ('LP md1-2', 'LP md3-8', 'KO'):
        m = AFF & (PH == p)
        a, sa = dse(R[m] - R_BASE[m])
        cells.append(f'{p}: {1000 * a:+.2f}±{1000 * sa:.2f}')
    print(f'   {fam}: ' + ' · '.join(cells))

print('\n2. ΜΕΡΟΛΗΨΙΑ ευρωπαικων obs μετα τη διορθωση (γκολ/ματς, w=1): επιθ / αμυνα')
BIAS = {}
f2 = RES['B2'][0][SEAS[-1]][1]
for fam, k in (('V0', ('V0', 1.0, 1.0)), ('B1', ('B1', 1.0, 1.0)), ('B2', ('B2', f2, 1.0)), ('B2 f1.25', ('B2', 1.25, 1.0)), ('B2 f1.5', ('B2', 1.5, 1.0)), ('B2 f1.75', ('B2', 1.75, 1.0))):
    B = ARMS[k][1]
    out = {}
    for lab, m in (('ΟΛΑ', np.ones(len(B), bool)), ('top7', B.top7.values), ('αλλες', ~B.top7.values),
                   ('UCL', (B.comp == 'ChampionsLeague').values), ('UEL', (B.comp == 'EuropaLeague').values),
                   ('UECL', (B.comp == 'ConferenceLeague').values)):
        out[lab] = (B.att[m].mean(), B.att[m].std() / math.sqrt(m.sum()), B.dfn[m].mean(), B.dfn[m].std() / math.sqrt(m.sum()))
    BIAS[fam] = out
    print(f'   {fam}{"" if fam != "B2" else f" (f={f2}, LOSO 2526)"} n{len(B)}: '
          + ' · '.join(f'{l} {v[0]:+.3f}±{v[1]:.3f} / {v[2]:+.3f}±{v[3]:.3f}' for l, v in out.items()))
print(f'   (B1 fallback σε V0: {N_FB["B1"]} obs, σε ολα τα τρεξιματα)')

print('\n3. ΜΕΓΕΘΟΣ ΜΕΤΑΤΟΠΙΣΗΣ: κλιση (πραγματικο − base) ~ Δπεριθωριο (1 = σωστο μεγεθος, 0 = θορυβος)')
GDf = GD.astype(float)
MB = BASE[0] - BASE[1]
for fam in ('V0', 'B1', 'B2'):
    L = RES[fam][1]
    dm = (L[0] - L[1]) - MB
    res = GDf - MB
    mk = AFF & (np.abs(dm) > 1e-9)
    sl = float((dm[mk] * res[mk]).sum() / (dm[mk] ** 2).sum())
    sres = res[mk] - sl * dm[mk]
    ss = math.sqrt((sres ** 2).sum() / (mk.sum() - 1) / (dm[mk] ** 2).sum())
    print(f'   {fam}: κλιση {sl:+.2f}±{ss:.2f} · μεσο |Δπεριθ| {np.abs(dm[mk]).mean():.3f}')


def cover_q(dist, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L_ in parts:
        for k_, p in dist.items():
            m_ = (k_ if side == 1 else -k_) + L_
            if m_ > 0.01:
                pw += p / len(parts)
            elif abs(m_) <= 0.01:
                pp += p / len(parts)
    return pw, pp


def gen(L, OD):
    rows = {}
    for i, mid in enumerate(MIDS):
        if not FMm[i] or mid not in OD:
            continue
        lf, oh, oa = OD[mid]
        dist = eu_dist(L[0][i], L[1][i])
        ucl = COMP[i] == 'ChampionsLeague'
        for side, ln, o in ((1, lf, oh), (-1, -lf, oa)):
            if not (1.70 <= o <= 2.10):
                continue
            role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
            if role is None:
                continue
            pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
            e = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            thr = (0.10 if role == 'fav' else 0.04) if ucl else (0.04 if role == 'fav' else 0.10)
            if e >= thr:
                rows[(mid, side)] = dict(comp=COMP[i], role=role, sea=SEA[i], pnl=picks.settle(GD[i], side, ln, o))
    return rows


def roi(rows):
    p = np.array([r['pnl'] for r in rows])
    return (len(p), p.mean() if len(p) else np.nan, p.std(ddof=1) / math.sqrt(len(p)) if len(p) > 1 else np.nan)


print('\n4. ROI (σημερινη τιμολογηση, κλεισιμο, μεσος Crown/Pinnacle) — n / ROI ±SE')
FLT = (('ΟΛΑ', lambda r: True), ('UCL', lambda r: r['comp'] == 'ChampionsLeague'),
       ('UCL φαβ', lambda r: r['comp'] == 'ChampionsLeague' and r['role'] == 'fav'),
       ('UCL dog', lambda r: r['comp'] == 'ChampionsLeague' and r['role'] == 'dog'),
       ('UEL', lambda r: r['comp'] == 'EuropaLeague'), ('UECL', lambda r: r['comp'] == 'ConferenceLeague'))
ROI = {}
for fam, L in (('base', BASE), ('V0', RES['V0'][1]), ('B1', RES['B1'][1]), ('B2', RES['B2'][1])):
    G = [gen(L, OD) for OD in (CROWN, PIN)]
    out = {}
    for lab, flt in FLT:
        vals = [roi([r for r in GG.values() if flt(r)]) for GG in G]
        out[lab] = ((vals[0][0] + vals[1][0]) / 2, np.nanmean([vals[0][1], vals[1][1]]), np.nanmean([vals[0][2], vals[1][2]]))
    ROI[fam] = out
    print(f'   {fam:5s} ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%±{100 * v[2]:.1f}' for l, v in out.items()))

print('\nΚΡΙΣΗ (προ-δηλωμενα)')
for fam in ('B1', 'B2'):
    R, R0 = RES[fam][2], RES['V0'][2]
    d0 = [dse(R[AFF & (SEA == s)] - R0[AFF & (SEA == s)])[0] for s in SEAS]
    dp0 = dse(R[AFF] - R0[AFF])[0]
    c1 = dp0 < 0 and sum(x < 0 for x in d0) >= 3
    bb = BIAS[fam]
    # B2: η μεροληψια πρεπει να περνα σε ΚΑΘΕ f που διαλεξε το LOSO (f=1.0 = V0)
    fsel = sorted({RES['B2'][0][s][1] for s in SEAS}) if fam == 'B2' else [None]
    bl = [BIAS['B1']] if fam == 'B1' else [BIAS['V0'] if f_ == 1.0 else BIAS[f'B2 f{f_}'] for f_ in fsel]
    c2 = all(abs(b_[l][0]) < .05 and abs(b_[l][2]) < .05 for b_ in bl for l in ('top7', 'αλλες'))
    db = [dse(R[AFF & (SEA == s)] - R_BASE[AFF & (SEA == s)])[0] for s in SEAS]
    dpb = dse(R[AFF] - R_BASE[AFF])[0]
    c3 = dpb < 0 and sum(x < 0 for x in db) >= 3
    c4 = all(ROI[fam][l][1] >= ROI['base'][l][1] - ROI['base'][l][2] for l in ('ΟΛΑ', 'UCL'))
    verdict = 'ΥΠΟΨΗΦΙΟ LIVE' if (c1 and c2 and c3 and c4) else ('ΚΑΛΥΤΕΡΗ ΔΙΟΡΘΩΣΗ' if (c1 and c2) else 'ΔΕΝ ΠΕΡΝΑ')
    print(f'   {fam}: (1) vs V0 {"✓" if c1 else "✗"} ({sum(x < 0 for x in d0)}/4, pooled {1000 * dp0:+.2f}) · '
          f'(2) μεροληψια {"✓" if c2 else "✗"} · (3) vs χωρις {"✓" if c3 else "✗"} ({sum(x < 0 for x in db)}/4, pooled {1000 * dpb:+.2f}) · '
          f'(4) ROI {"✓" if c4 else "✗"} → {verdict}')
print(f'\nΤΕΛΟΣ [{time.time() - T0:.0f}s]')
