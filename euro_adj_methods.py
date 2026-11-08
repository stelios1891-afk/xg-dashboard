"""
euro_adj_methods.py — 9/10/2026 (Στελιος: «να αναλυσουμε τη διορθωση αντιπαλου με ολους τους πιθανους τροπους»).
Φετινα ευρωπαικα ματς στο ευρωπαικο rating — ΣΥΓΚΡΙΣΗ 9 ΤΡΟΠΩΝ ADJUST του xG για τη δυναμη του αντιπαλου.
  M1 26/9 (V0): rating αντιπαλου + χασμα λιγκας V4 (= λογικη Στελιου περσι, με δικο μας rating αντι Elo)
  M2 B1: obs = rating × πραγματικο / λ πληρους προβλεψης (V4 + γ + κ)
  M3 B1 χωρις κ (V4 + γ)
  M4 B1 χωρις γ,κ (καθαρο V4 — ελεγχος: ≈ M1)
  M5 M1 με χασμα λιγκας ×1.25        M6 M1 με χασμα ×1.5
  M7 M1 με χασμα ×f, f απο LOSO ωστε να μηδενιζει τη μεροληψια λιγκας στα xG των αλλων σεζον
  M8 «τι xG να περιμενω»: Poisson LOSO στα πραγματικα ευρωπαικα xG των αλλων σεζον,
     log E[xG] = a + b1·log λ_ομαδας(V4) + b2·log λ_αντιπαλου(V4) + b3·χασμα λιγκας + b4·εδρα → obs = rating × πραγματικο / E
  M9 ELO (τροπος Στελιου): log E[xG] = a + bT·Elo_ομαδας − bO·Elo_αντιπαλου + h·εδρα (LOSO)·
     obs = πραγματικο × e^{bO(Elo_αντ − μεσο Elo λιγκας ομαδας)/100 ∓ h} × κλιμακα (ενας συντελεστης LOSO)
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραμμενα πριν την εκτελεση):
  Κ1 ΔΙΚΑΙΟΣΥΝΗ: μεροληψια (διορθωμενο − rating) σε 5 καδους ανισοτητας ματς + CORE7/αλλες λιγκες, επιθεση & αμυνα (14 κελια):
     ολα |·| < 0.10 γκολ/ματς → «δικαιη»· αναφερεται μεγιστο και μεσο |·|.
  Κ2 ΠΡΟΒΛΕΨΗ (βαρος 0.5): RPS επηρεαζομενων vs ΧΩΡΙΣ φετινα <0 pooled ΚΑΙ σε ≥3/4 σεζον· και vs M2 (B1, σημερινο καλυτερο).
  Κ3 ΦΡΟΥΡΟΣ ROI (βαρος 0.5, σημερινη τιμολογηση, μεσος Crown/Pinnacle): ΟΛΑ & UCL ≥ χωρις − 1SE.
  «Καλυτερος τροπος» = περνα Κ1 & Κ3 με το καλυτερο pooled RPS (Κ2). Αν κανενας δεν περνα Κ1: ο μικροτερος μεγιστος |·| + RPS του.
  Δευτερευον: RPS με βαρος 1 και με LOSO βαρους {0.25, 0.5, 1}.
Σημ.: μεσο Elo λιγκας = clubelo_current (σημερινο, προσεγγιση).
"""
import sys, io, math, contextlib, time
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
T0 = time.time()
g = {'__name__': 'am'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']
SS, rate_base, s_v4, eng2, HF, RHO, EPS, CAL, ELO, GKEYS = (g[k] for k in ('SS', 'rate_base', 's_v4', 'eng2', 'HF', 'RHO', 'EPS', 'CAL', 'ELO', 'GKEYS'))
GAM, KAPPA, NEWF = g['GAM'], g['KAPPA'], g['NEWF']
rps_arr, dse, AFF, SEA, SEAS, R_BASE, gen, roi, FLT, CROWN, PIN, BASE = (g[k] for k in (
    'rps_arr', 'dse', 'AFF', 'SEA', 'SEAS', 'R_BASE', 'gen', 'roi', 'FLT', 'CROWN', 'PIN', 'BASE'))
live_stack, predict_arm = g['live_stack'], g['predict_arm']
EQ0 = g['EQ0']; TOP7 = g['TOP7']; b_bl = G['b_blend']
_shrink, K = G['_shrink'], G['K']
ELO_C, LG_COUNTRY = G['ELO_C'], G['LG_COUNTRY']
print(f'[setup {time.time() - T0:.0f}s]')


def side_terms(st, tid, fold, d, mid, is_home):
    SL, XL = eng2.ruler(st['lg'], st['sea'], d)
    Ax, Dx, SF, SA = rate_base(st, tid, fold, d)
    att = math.log(max((SF / SL) * (Ax / XL), EPS)); leak = math.log(max((SA / SL) * (Dx / XL), EPS))
    if (st['lg'], st['sea']) not in GKEYS and st['goal_only']:
        el = ELO.get(mid, (np.nan, np.nan))[0 if is_home else 1]
        try:
            el = float(el)
        except (TypeError, ValueError):
            el = float('nan')
        if not math.isnan(el):
            a_f, b_f = CAL[fold]; u = a_f + b_f * el / 100.0 - RHO * s_v4(st['lg'], fold); att, leak = u, -u
    return SL, XL, att, leak


def pred3(hid, aid, d, fold, comp, mid):
    """(λ καθαρο V4, λ +γ, λ +γ+κ) για γηπ/φιλ — None αν λειπει rating."""
    sh, sa = SS(hid, d), SS(aid, d)
    if sh is None or sa is None or (sh['prior'] is None and sh['cur'] is None) or (sa['prior'] is None and sa['cur'] is None):
        return None
    SLh, XLh, ah, lh_ = side_terms(sh, hid, fold, d, mid, True)
    SLa, XLa, aa, la_ = side_terms(sa, aid, fold, d, mid, False)
    lXs = math.log(((SLh * SLa) ** 0.5) * ((XLh * XLa) ** 0.5))
    D_ = s_v4(sh['lg'], fold) - s_v4(sa['lg'], fold); hf = HF[fold]
    LH = math.exp(lXs + ah + la_) * hf * math.exp(RHO * D_); LA = math.exp(lXs + aa + lh_) / hf * math.exp(-RHO * D_)
    C = GAM * D_; LHg = max(LH - C / 2, .05); LAg = max(LA + C / 2, .05)
    LHk, LAk = LHg, LAg
    if comp == 'ChampionsLeague' and fold in NEWF:
        if LHg >= LAg: LHk = LHg * KAPPA
        else: LAk = LAg * KAPPA
    return (LH, LA), (LHg, LAg), (LHk, LAk), D_


def elo_ref(lg):
    cc = LG_COUNTRY.get(lg)
    return float(ELO_C.loc[cc, 'mean']) if cc in ELO_C.index else None


# ---------------- πινακας χαρακτηριστικων για ΚΑΘΕ φετινη ευρωπαικη παρατηρηση ----------------
FEAT = {}
for (fold, tid), lst in G['EU_BY_TEAM'].items():
    if fold not in SEAS:
        continue
    for rec in lst:
        mid, d, ish, xgf, xga, gf, ga, oid, comp = rec
        st = SS(tid, d)
        if st is None or (st['prior'] is None and st['cur'] is None):
            continue
        p = pred3(tid, oid, d, fold, comp, mid) if ish else pred3(oid, tid, d, fold, comp, mid)
        if p is None:
            continue
        sw = (lambda t: (t[0], t[1])) if ish else (lambda t: (t[1], t[0]))
        l0, lg_, lk = sw(p[0]), sw(p[1]), sw(p[2]); Dt = p[3] if ish else -p[3]
        r = rate_base(st, tid, fold, d)
        so = SS(oid, d)
        el = ELO.get(mid, (np.nan, np.nan))
        try:
            eT, eO = (float(el[0]), float(el[1])) if ish else (float(el[1]), float(el[0]))
        except (TypeError, ValueError):
            eT = eO = float('nan')
        SLt, XLt = eng2.ruler(st['lg'], st['sea'], d)
        FEAT[(tid, mid, fold)] = dict(fold=fold, lg=st['lg'], sea_dom=st['sea'], top7=st['lg'] in TOP7, comp=comp, home=1 if ish else -1,
                                      ya=b_bl * xgf + (1 - b_bl) * gf, yd=b_bl * xga + (1 - b_bl) * ga,
                                      l0F=l0[0], l0A=l0[1], lgF=lg_[0], lgA=lg_[1], lkF=lk[0], lkA=lk[1], Dt=Dt,
                                      ra=r[0] * r[2], rd=r[1] * r[3], eT=eT, eO=eO, eref=elo_ref(st['lg']),
                                      sc=math.sqrt(SLt * XLt), supk=lk[0] - lk[1])
F = pd.DataFrame.from_dict(FEAT, orient='index')
print(f'παρατηρησεις με χαρακτηριστικα: {len(F)} [{time.time() - T0:.0f}s]')


def pois(X, y, ridge=1e-6):
    b = np.zeros(X.shape[1]); b[0] = math.log(max(y.mean(), 1e-3))
    for _ in range(60):
        mu = np.exp(X @ b); z = X @ b + (y - mu) / mu
        A = X.T @ (mu[:, None] * X) + ridge * np.eye(X.shape[1]); bn = np.linalg.solve(A, X.T @ (mu * z))
        if np.max(np.abs(bn - b)) < 1e-9: b = bn; break
        b = bn
    return b


# ---------------- LOSO συντελεστες ----------------
COEF8, COEF9, F7 = {}, {}, {}
for fold in SEAS:
    tr = F[F.fold != fold]
    # M8: στοιβαζουμε επιθεση (ομαδα) και αμυνα (= επιθεση αντιπαλου)
    Xa = np.c_[np.ones(len(tr)), np.log(tr.l0F), np.log(tr.l0A), tr.Dt, tr.home]
    Xd = np.c_[np.ones(len(tr)), np.log(tr.l0A), np.log(tr.l0F), -tr.Dt, -tr.home]
    COEF8[fold] = pois(np.r_[Xa, Xd], np.r_[tr.ya.values, tr.yd.values])
    # M9: Elo
    te = tr[np.isfinite(tr.eT) & np.isfinite(tr.eO)]
    Xa = np.c_[np.ones(len(te)), te.eT / 100, te.eO / 100, te.home]
    Xd = np.c_[np.ones(len(te)), te.eO / 100, te.eT / 100, -te.home]
    b9 = pois(np.r_[Xa, Xd], np.r_[te.ya.values, te.yd.values])
    bO, h = -b9[2], b9[3]
    ok = te[te.eref.notna()]
    fa = ok.ya * np.exp(bO * (ok.eO - ok.eref) / 100 - h * ok.home) * ok.sc
    fd = ok.yd * np.exp(-bO * (ok.eO - ok.eref) / 100 + h * ok.home) * ok.sc
    ca = float((ok.ra).sum() / fa.sum()); cd = float((ok.rd).sum() / fd.sum())
    COEF9[fold] = (bO, h, ca, cd, b9)
print('M8 συντελεστες (a, log λ ομαδας, log λ αντιπαλου, χασμα, εδρα): ' + ' | '.join(f'{f}: ' + ' '.join(f'{x:+.2f}' for x in c) for f, c in COEF8.items()))
print('M9 Elo: ' + ' | '.join(f'{f}: bO {c[0]:.2f}/100 Elo, εδρα {c[1]:+.2f}' for f, c in COEF9.items()))


def obs_m8(f):
    c = COEF8[f.fold]
    ea = math.exp(c[0] + c[1] * math.log(f.l0F) + c[2] * math.log(f.l0A) + c[3] * f.Dt + c[4] * f.home)
    ed = math.exp(c[0] + c[1] * math.log(f.l0A) + c[2] * math.log(f.l0F) - c[3] * f.Dt - c[4] * f.home)
    return f.ra * f.ya / ea, f.rd * f.yd / ed


def obs_m9(f):
    if not (np.isfinite(f.eT) and np.isfinite(f.eO)) or f.eref is None or (isinstance(f.eref, float) and math.isnan(f.eref)):
        return None
    bO, h, ca, cd, _ = COEF9[f.fold]
    return (f.ya * math.exp(bO * (f.eO - f.eref) / 100 - h * f.home) * f.sc * ca,
            f.yd * math.exp(-bO * (f.eO - f.eref) / 100 + h * f.home) * f.sc * cd)


def make_eq(kind, f_gap=1.0):
    def eq(tid, rec, fold, lg, sea):
        key = (tid, rec[0], fold, lg, sea)
        if key in CACHE:
            return CACHE[key]
        G['_OBS'] = {}
        o = EQ0(tid, rec, fold, lg, sea)
        if o is None:
            CACHE[key] = None; return None
        f = FEAT.get((tid, rec[0], fold))
        usable = f is not None and f['lg'] == lg and f['sea_dom'] == sea
        out = o
        if kind in ('M5', 'M6', 'M7'):
            fg = F7[fold] if kind == 'M7' else f_gap
            so = SS(rec[7], rec[1])
            if so is not None:
                dl = RHO * (s_v4(lg, fold) - s_v4(so['lg'], fold))
                out = (o[0] * math.exp(-(fg - 1) * dl), o[1] * math.exp((fg - 1) * dl), o[2], o[3])
        elif usable and kind in ('M2', 'M3', 'M4'):
            lF, lA = {'M2': (f['lkF'], f['lkA']), 'M3': (f['lgF'], f['lgA']), 'M4': (f['l0F'], f['l0A'])}[kind]
            out = (f['ra'] * f['ya'] / lF, f['rd'] * f['yd'] / lA, o[2], o[3])
        elif usable and kind == 'M8':
            a, d_ = obs_m8(pd.Series(f)); out = (a, d_, o[2], o[3])
        elif usable and kind == 'M9':
            r9 = obs_m9(pd.Series(f))
            if r9 is not None:
                out = (r9[0], r9[1], o[2], o[3])
        CACHE[key] = out
        return out
    return eq


CACHE = {}


def make_rate(w_in):
    def rate(st, tid, fold, d):
        pr = G['prior_enr'](st, tid, fold)
        cur, n = st['cur'], st['n']
        obs = G['inseason'](tid, d, fold, st)
        if obs:
            ne = len(obs); den = n + w_in * ne
            sA = sum(o[1][0] for o in obs); sD = sum(o[1][1] for o in obs)
            if cur is not None:
                sf, sa = cur[2], cur[3]; ca, cd = cur[0] * sf, cur[1] * sa
            else:
                sf, sa = pr[2], pr[3]; ca = cd = 0.0
            cur = ((n * ca + w_in * sA) / den / max(sf, EPS), (n * cd + w_in * sD) / den / max(sa, EPS), sf, sa); n = den
        if cur is None: return pr
        if pr is None: return cur
        return _shrink(cur, pr, n, K)
    return rate


def bias_table(kind, f_gap=1.0):
    eq = make_eq(kind, f_gap); CACHE.clear(); rows = []
    for (tid, mid, fold), f in FEAT.items():
        rec = next((r for r in G['EU_BY_TEAM'][(fold, tid)] if r[0] == mid), None)
        o = eq(tid, rec, fold, f['lg'], f['sea_dom'])
        if o is None: continue
        rows.append(dict(ba=o[0] - f['ra'], bd=o[1] - f['rd'], sup=f['supk'], top7=f['top7']))
    B = pd.DataFrame(rows); cells = {}
    for lo, hi, lab in ((-9, -1, 'μεγ.αουτ'), (-1, -.3, 'αουτ'), (-.3, .3, 'ισορ'), (.3, 1, 'φαβ'), (1, 9, 'μεγ.φαβ')):
        x = B[(B.sup > lo) & (B.sup <= hi)]; cells[lab] = (x.ba.mean(), x.bd.mean())
    for t7, lab in ((True, 'CORE7'), (False, 'αλλες')):
        x = B[B.top7 == t7]; cells[lab] = (x.ba.mean(), x.bd.mean())
    vals = np.abs(np.array(list(cells.values()))).ravel()
    return cells, vals.max(), vals.mean(), (B.ba.mean(), B.bd.mean())


# M7: f απο LOSO — ελαχιστοποιει τη μεροληψια λιγκας (CORE7/αλλες, επιθ+αμυνα) στις αλλες σεζον
for fold in SEAS:
    best, bv = 1.0, 9e9
    for fg in np.round(np.arange(1.0, 2.01, 0.05), 2):
        eq = make_eq('M5', fg); CACHE.clear(); acc = {True: [], False: []}
        for (tid, mid, fo), f in FEAT.items():
            if fo == fold: continue
            rec = next((r for r in G['EU_BY_TEAM'][(fo, tid)] if r[0] == mid), None)
            o = eq(tid, rec, fo, f['lg'], f['sea_dom'])
            if o is not None: acc[f['top7']].append((o[0] - f['ra'], o[1] - f['rd']))
        v = sum(np.mean([a[i] for a in acc[t]]) ** 2 for t in (True, False) for i in (0, 1))
        if v < bv: best, bv = fg, v
    F7[fold] = best
print('M7 χασμα f (LOSO): ' + ' '.join(f'{k}:{v}' for k, v in F7.items()) + f' [{time.time() - T0:.0f}s]')

METHODS = [('M1', '26/9 (λογικη Στελιου)', 1.0), ('M2', 'B1 (+γ+κ)', 1.0), ('M3', 'B1 χωρις κ', 1.0), ('M4', 'B1 χωρις γ,κ', 1.0),
           ('M5', 'χασμα ×1.25', 1.25), ('M6', 'χασμα ×1.5', 1.5), ('M7', 'χασμα LOSO', 1.0), ('M8', '«τι xG να περιμενω»', 1.0),
           ('M9', 'Elo', 1.0)]
print('\n1. ΔΙΚΑΙΟΣΥΝΗ — μεροληψια επιθ/αμυνα (γκολ/ματς) ανα τυπο ματς και λιγκα')
print(f'   {"τροπος":24s} | ' + ' | '.join(f'{c:>13s}' for c in ('μεγ.αουτ', 'αουτ', 'ισορ', 'φαβ', 'μεγ.φαβ', 'CORE7', 'αλλες')) + ' | max · μεσο')
BT = {}
for code, lab, fg in METHODS:
    cells, mx, mn, tot = bias_table('M5' if code in ('M5', 'M6') else code, fg)
    BT[code] = (mx, mn)
    print(f'   {code} {lab:21s} | ' + ' | '.join(f'{v[0]:+.2f}/{v[1]:+.2f}'.rjust(13) for v in cells.values()) + f' | {mx:.2f} · {mn:.3f}')

print(f'\n2. ΠΡΟΒΛΕΨΗ — ΔRPS επηρεαζομενων vs ΧΩΡΙΣ φετινα (×10⁻³, αρνητικο = καλυτερο) [{time.time() - T0:.0f}s]')
RES = {}
for code, lab, fg in METHODS:
    eqf = make_eq('M5' if code in ('M5', 'M6') else code, fg)
    RR = {}
    for w in (0.25, 0.5, 1.0):
        G['eq_obs'] = eqf; CACHE.clear(); G['_OBS'] = {}
        L = live_stack(*predict_arm(make_rate(w))); RR[w] = (L, rps_arr(*L))
    ch = {}; Rl = np.empty(len(SEA))
    for s in SEAS:
        tr = AFF & (SEA != s); ch[s] = min(RR, key=lambda w: RR[w][1][tr].mean()); Rl[SEA == s] = RR[ch[s]][1][SEA == s]
    RES[code] = (RR, Rl, ch)
R2 = RES['M2'][0][0.5][1]
for code, lab, fg in METHODS:
    RR, Rl, ch = RES[code]; out = []
    for tag, R in (('w.5', RR[0.5][1]), ('w1', RR[1.0][1]), ('LOSO', Rl)):
        cs = [dse(R[AFF & (SEA == s)] - R_BASE[AFF & (SEA == s)])[0] for s in SEAS]; d, se = dse(R[AFF] - R_BASE[AFF])
        out.append(f'{tag} {1000 * d:+.2f}±{1000 * se:.2f} {sum(c < 0 for c in cs)}/4')
    d2, s2 = dse(RR[0.5][1][AFF] - R2[AFF])
    print(f'   {code} {lab:21s} | ' + ' · '.join(out) + f' · (w.5 vs B1 {1000 * d2:+.2f}±{1000 * s2:.2f}) · LOSO βαρη ' + ' '.join(f'{v}' for v in ch.values()))


def roi_tab(L):
    GG = [gen(L, OD) for OD in (CROWN, PIN)]; out = {}
    for lab, flt in FLT:
        v = [roi([r for r in x.values() if flt(r)]) for x in GG]
        out[lab] = ((v[0][0] + v[1][0]) / 2, np.nanmean([v[0][1], v[1][1]]), np.nanmean([v[0][2], v[1][2]]))
    return out


print('\n3. ROI (βαρος 0.5, σημερινη τιμολογηση, κλεισιμο, μεσος Crown/Pinnacle)')
RB = roi_tab(BASE)
print('   ΧΩΡΙΣ φετινα          | ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in RB.items()))
ROI = {}
for code, lab, fg in METHODS:
    ROI[code] = roi_tab(RES[code][0][0.5][0])
    print(f'   {code} {lab:19s} | ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in ROI[code].items()))

print('\nΚΡΙΣΗ (προ-δηλωμενα)')
passing = []
for code, lab, fg in METHODS:
    R = RES[code][0][0.5][1]
    cs = [dse(R[AFF & (SEA == s)] - R_BASE[AFF & (SEA == s)])[0] for s in SEAS]; d, _ = dse(R[AFF] - R_BASE[AFF])
    k1 = BT[code][0] < 0.10; k2 = d < 0 and sum(c < 0 for c in cs) >= 3
    k3 = all(ROI[code][l][1] >= RB[l][1] - RB[l][2] for l in ('ΟΛΑ', 'UCL'))
    if k1 and k3: passing.append((d, code))
    print(f'   {code} {lab:21s}: Κ1 δικαιη {"✓" if k1 else "✗"} (max {BT[code][0]:.2f}) · Κ2 προβλεψη {"✓" if k2 else "✗"} ({1000 * d:+.2f}, {sum(c < 0 for c in cs)}/4) · Κ3 ROI {"✓" if k3 else "✗"}')
if passing:
    d, code = min(passing); print(f'\n   ΚΑΛΥΤΕΡΟΣ (Κ1+Κ3, μετα RPS): {code} ({1000 * d:+.2f})')
else:
    code = min(BT, key=lambda c: BT[c][0]); print(f'\n   κανενας δικαιος σε ολα τα κελια· μικροτερο μεγιστο: {code} (max {BT[code][0]:.2f})')
print(f'\nΤΕΛΟΣ [{time.time() - T0:.0f}s]')
