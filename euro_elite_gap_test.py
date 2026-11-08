"""
euro_elite_gap_test.py — 10/10/2026 (Στελιος: «αλλο να παιξεις με τη Λανς και αλλο με την Παρι· η Παρι με τη Σιτι ή τη Μπαγερν δεν εχουν
μεγαλες διαφορες, παροτι οι λιγκες εχουν»). Η διαφορα λιγκας μικραινει για τις ΚΥΡΙΑΡΧΕΣ ομαδες;
Κυριαρχια z = μισο της (επιθεση − διαρροη) σε log ως προς τον μεσο ορο της ΔΙΚΗΣ ΤΗΣ λιγκας (0 = μεση ομαδα, PSG/Bayern ~0.5-0.8).
1. ΔΙΑΓΝΩΣΗ (σημερινη αλυσιδα, 2223-2526, ολα τα ευρωπαικα): πραγματικο − μοντελο (xG, γκολ, διαφορα) και − αγορα,
   ανα κυριαρχια ομαδας × αν η αντιπαλη λιγκα ειναι ισχυροτερη/ιδια/ασθενεστερη.
2. ΔΙΟΡΘΩΣΗ (LOSO β): Δ1 διαφορα λιγκας × (1 − β·μεση κυριαρχια των 2 ομαδων) · Δ2 × (1 − β·κυριαρχια της ομαδας της ΑΣΘΕΝΕΣΤΕΡΗΣ λιγκας).
   Το γ εφαρμοζεται στη νεα διαφορα, το κ μετα (οπως live).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ: (1) RPS καλυτερο σε ≥3/4 σεζον ΚΑΙ pooled · (2) η μεροληψια των κυριαρχων ομαδων ασθενεστερης λιγκας
(πραγματικη διαφορα − μοντελο, z ≥ 0.35 vs ισχυροτερη λιγκα) μικραινει · (3) ROI (σημερινη τιμολογηση, μεσος Crown/Pinnacle) ΟΛΑ & UCL ≥ σημερα − 1SE.
"""
import sys, io, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'eg'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']
MIDS, SEA, COMP, GD, GH, GA = G['MIDS'], g['SEA'], G['COMP'], G['GD'], G['GH'], G['GA']
HID, AID, DATES, N = G['HID'], G['AID'], G['DATES'], G['N']
SS, rate_base, s_v4, eng2, RHO, EPS, CAL = G['SS'], G['rate_base'], G['s_v4'], G['eng2'], G['RHO'], G['EPS'], G['CAL']
LGH, LGA, src_h, src_a, eh, ea = G['LGH'], G['LGA'], G['src_h'], G['src_a'], G['eh'], G['ea']
GAM, KAP, KS, HFV = G['GAMMA_LG_DEFLATE'], G['UCL_FAV_SCALE'], G['KSCOPE'], G['HFV']
rps_arr, dse, gen, roi, FLT, CROWN, PIN = g['rps_arr'], g['dse'], g['gen'], g['roi'], g['FLT'], g['CROWN'], g['PIN']
picks = g['picks']
RAWH, RAWA = G['predict_arm'](rate_base)
BASE = g['BASE']; R0 = rps_arr(*BASE)
D = np.array([s_v4(LGH[i], SEA[i]) - s_v4(LGA[i], SEA[i]) for i in range(N)])
# ---------------- κυριαρχια (ιδια att/leak με την προβλεψη) ----------------
def att_leak(st, tid, fold, d, srcv, elo, lg):
    SL, XL = eng2.ruler(st['lg'], st['sea'], d)
    Ax, Dx, SF, SA = rate_base(st, tid, fold, d)
    a = math.log(max((SF / SL) * (Ax / XL), EPS)); l = math.log(max((SA / SL) * (Dx / XL), EPS))
    if srcv == 'goals' and not np.isnan(elo):
        a_f, b_f = CAL[fold]; u = a_f + b_f * elo / 100.0 - RHO * s_v4(lg, fold); a, l = u, -u
    return a, l
ZH = np.zeros(N); ZA = np.zeros(N)
for i in range(N):
    d = DATES[i]; fold = SEA[i]
    ah, lh = att_leak(SS(HID[i], d), HID[i], fold, d, src_h[i], eh[i], LGH[i])
    aa, la = att_leak(SS(AID[i], d), AID[i], fold, d, src_a[i], ea[i], LGA[i])
    ZH[i] = 0.5 * (ah - lh); ZA[i] = 0.5 * (aa - la)
# λογαριθμος ως προς τον μεσο ορο ολων (κεντραρισμα: μεση ομαδα λιγκας ≈ 0)
print(f'κυριαρχια z: μεσος {np.r_[ZH, ZA].mean():+.2f} · 90ο εκατοστημοριο {np.percentile(np.r_[ZH, ZA], 90):+.2f} · π.χ. υψηλες τιμες: ' +
      ', '.join(sorted({G['S'].hname.values[i] if ZH[i] > ZA[i] else G['S'].aname.values[i] for i in np.argsort(-np.maximum(ZH, ZA))[:12]})))
# ---------------- αγορα ----------------
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(24):
        s = (lo + hi) / 2; dd = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(dd, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
MK = np.array([msup(*CROWN[m], BASE[0][i] + BASE[1][i]) if m in CROWN else np.nan for i, m in enumerate(MIDS)])
XG = {}
import json
for sea in ('2223', '2324', '2425', '2526'):
    for mid, mm in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not mm.get('shots'): continue
        h, a = int(mm['home']['id']), int(mm['away']['id']); agg = {h: 0.0, a: 0.0}
        for s_ in mm['shots']:
            if s_.get('xg') is not None and s_.get('tid') in agg: agg[s_['tid']] += 0.25 if s_.get('sit') == 'Penalty' else s_['xg']
        XG[str(mid)] = (agg[h], agg[a])
XH = np.array([XG.get(m, (np.nan, np.nan))[0] for m in MIDS]); XA = np.array([XG.get(m, (np.nan, np.nan))[1] for m in MIDS])
rows = []
for i in range(N):
    for side in (1, -1):
        z = ZH[i] if side == 1 else ZA[i]; dt = D[i] * side
        lf = BASE[0][i] if side == 1 else BASE[1][i]; la = BASE[1][i] if side == 1 else BASE[0][i]
        rows.append(dict(i=i, sea=SEA[i], comp=COMP[i], z=z, dt=dt, xf=(XH[i] if side == 1 else XA[i]), lf=lf, la=la,
                         gf=(GH[i] if side == 1 else GA[i]), ga=(GA[i] if side == 1 else GH[i]), mk=MK[i] * side, gd=GD[i] * side))
S = pd.DataFrame(rows)
S['zb'] = pd.cut(S.z, [-9, 0.0, 0.2, 0.35, 0.5, 9], labels=['κατω απο μεσο', 'μετρια 0-0.2', 'καλη 0.2-0.35', 'κυριαρχη 0.35-0.5', 'πολυ κυριαρχη 0.5+'])
S['lgv'] = np.where(S.dt <= -0.10, 'vs ΙΣΧΥΡΟΤΕΡΗ λιγκα', np.where(S.dt >= 0.10, 'vs ασθενεστερη λιγκα', 'vs παρομοια λιγκα'))
def se(x): x = x.dropna(); return x.std() / math.sqrt(len(x)) if len(x) > 1 else np.nan
print('\n1. ΔΙΑΓΝΩΣΗ — οπτικη ομαδας: xG−λ · (διαφορα γκολ − μοντελο) · (διαφορα γκολ − αγορα)')
for lv in ('vs ΙΣΧΥΡΟΤΕΡΗ λιγκα', 'vs παρομοια λιγκα', 'vs ασθενεστερη λιγκα'):
    print(f'   {lv}:')
    for zb in S.zb.cat.categories:
        x = S[(S.lgv == lv) & (S.zb == zb)]
        if len(x) < 15: continue
        dm = x.gd - (x.lf - x.la); dk = x.gd - x.mk
        print(f'      {zb:20s} n{len(x):4d} · xG−λ {(x.xf - x.lf).mean():+.2f}±{se(x.xf - x.lf):.2f} · διαφ−μοντ {dm.mean():+.2f}±{se(dm):.2f} · διαφ−αγορα {dk.mean():+.2f}±{se(dk):.2f}')
# ---------------- 2. διορθωση ----------------
def stack(beta, mode):
    if mode == 'Δ1':
        zz = np.clip((ZH + ZA) / 2, 0, None)
    else:   # ομαδα της ασθενεστερης λιγκας
        zz = np.clip(np.where(D >= 0, ZA, ZH), 0, None)
    Deff = D * np.clip(1 - beta * zz, 0, None)
    lh = RAWH * np.exp(RHO * (Deff - D)); la = RAWA * np.exp(-RHO * (Deff - D))
    C = GAM * Deff
    lh = np.maximum(lh - C / 2, .05); la = np.maximum(la + C / 2, .05)
    fh = lh >= la
    return np.where(KS & fh, lh * KAP, lh), np.where(KS & ~fh, la * KAP, la)
assert np.allclose(stack(0.0, 'Δ1')[0], BASE[0]) and np.allclose(stack(0.0, 'Δ1')[1], BASE[1]), 'ανακατασκευη ≠ σημερινη'
BETAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
SEAS = ['2223', '2324', '2425', '2526']
def bias_elite(L):
    m = (S.lgv == 'vs ΙΣΧΥΡΟΤΕΡΗ λιγκα') & (S.z >= 0.35)
    x = S[m]; lf = np.array([L[0][i] if 1 else 0 for i in x.i]);
    sup = np.array([(L[0][r.i] - L[1][r.i]) * (1 if r.dt == D[r.i] else -1) for r in x.itertuples()])
    return float((x.gd.values - sup).mean()), int(len(x))
print('\n2. ΔΙΟΡΘΩΣΗ (LOSO β)')
RES = {}
for mode in ('Δ1', 'Δ2'):
    RR = {b: rps_arr(*stack(b, mode)) for b in BETAS}
    ch = {}; Rl = np.empty(N); LHl = np.empty(N); LAl = np.empty(N)
    for s in SEAS:
        tr = SEA != s; b = min(BETAS, key=lambda b: RR[b][tr].mean()); ch[s] = b
        m = SEA == s; Rl[m] = RR[b][m]; L = stack(b, mode); LHl[m] = L[0][m]; LAl[m] = L[1][m]
    cs = [dse(Rl[SEA == s] - R0[SEA == s])[0] for s in SEAS]; d_, se_ = dse(Rl - R0)
    b0, n0 = bias_elite(BASE); b1, _ = bias_elite((LHl, LAl))
    RES[mode] = (ch, (LHl, LAl), cs, d_, se_, b0, b1, n0)
    print(f'   {mode}: β ανα σεζον ' + ' '.join(f'{s}:{b}' for s, b in ch.items()) + f' · ΔRPS ×10⁻³ ' + ' '.join(f'{1000 * c:+.2f}' for c in cs) +
          f' · pooled {1000 * d_:+.2f}±{1000 * se_:.2f} · μεροληψια κυριαρχων ασθενεστερης λιγκας (n{n0}) {b0:+.2f} → {b1:+.2f}')
    print('      ολο το δειγμα ανα β (ΔRPS ×10⁻³): ' + ' '.join(f'{b}:{1000 * (RR[b] - R0).mean():+.2f}' for b in BETAS))
def roi_tab(L):
    GG = [gen(L, OD) for OD in (CROWN, PIN)]; out = {}
    for lab, flt in FLT:
        v = [roi([r for r in x.values() if flt(r)]) for x in GG]
        out[lab] = ((v[0][0] + v[1][0]) / 2, np.nanmean([v[0][1], v[1][1]]), np.nanmean([v[0][2], v[1][2]]))
    return out
print('\n3. ROI (σημερινη τιμολογηση, κλεισιμο, μεσος Crown/Pinnacle)')
RB = roi_tab(BASE)
print('   σημερα  ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in RB.items()))
for mode in ('Δ1', 'Δ2'):
    RT = roi_tab(RES[mode][1])
    print(f'   {mode}      ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in RT.items()))
    ch, L, cs, d_, se_, b0, b1, n0 = RES[mode]
    k1 = d_ < 0 and sum(c < 0 for c in cs) >= 3; k2 = abs(b1) < abs(b0)
    k3 = all(RT[l][1] >= RB[l][1] - RB[l][2] for l in ('ΟΛΑ', 'UCL'))
    print(f'      ΚΡΙΣΗ: (1) RPS {"✓" if k1 else "✗"} ({sum(c < 0 for c in cs)}/4) · (2) μεροληψια {"✓" if k2 else "✗"} · (3) ROI {"✓" if k3 else "✗"} → {"ΠΕΡΝΑ" if k1 and k2 and k3 else "ΔΕΝ ΠΕΡΝΑ"}')
# ---------------- 4. picks μας εναντιον κυριαρχων ασθενεστερης λιγκας ----------------
print('\n4. ΤΑ PICKS ΜΑΣ (σημερα) ΣΕ/ΚΑΤΑ κυριαρχων ομαδων ασθενεστερης λιγκας (z ≥ 0.35, αντιπαλος απο ισχυροτερη)')
P = []
for bk, OD in (('Crown', CROWN), ('Pin', PIN)):
    for (mid, side), rr in gen(BASE, OD).items():
        i = MIDS.index(mid); zt = ZH[i] if side == 1 else ZA[i]; zo = ZA[i] if side == 1 else ZH[i]; dt = D[i] * side
        P.append(dict(bk=bk, role=rr['role'], pnl=rr['pnl'], comp=rr['comp'],
                      kind=('pick ΥΠΕΡ κυριαρχης ασθενεστερης λιγκας' if (zt >= .35 and dt <= -.10) else
                            ('pick ΚΑΤΑ κυριαρχης ασθενεστερης λιγκας' if (zo >= .35 and dt >= .10) else 'αλλα'))))
P = pd.DataFrame(P)
for k in ('pick ΚΑΤΑ κυριαρχης ασθενεστερης λιγκας', 'pick ΥΠΕΡ κυριαρχης ασθενεστερης λιγκας', 'αλλα'):
    x = P[P.kind == k]; m = x.groupby('bk').pnl.agg(['mean', 'size'])
    print(f'   {k:42s} {m["size"].mean() if len(m) else 0:4.0f} picks {100 * m["mean"].mean() if len(m) else float("nan"):+.1f}%')

# ---------------- 5. συγκεκριμενες κορυφαιες ομαδες «μικροτερων» λιγκων vs ισχυροτερη λιγκα ----------------
print('\n5. ΣΥΓΚΕΚΡΙΜΕΝΕΣ ΟΜΑΔΕΣ vs ομαδες ισχυροτερης λιγκας (οπτικη της ομαδας): μοντελο / αγορα / πραγματικο (διαφορα γκολ), xG−λ')
NM = np.array([G['S'].hname.values[r.i] if r.dt == D[r.i] * 1 and (r.dt == 0 or True) else '' for r in S.itertuples()])
S['team'] = [G['S'].hname.values[r.i] if k % 2 == 0 else G['S'].aname.values[r.i] for k, r in enumerate(S.itertuples())]
for t in ('Paris Saint-Germain', 'Bayern München', 'Borussia Dortmund', 'Bayer Leverkusen', 'Benfica', 'FC Porto', 'Sporting CP', 'PSV Eindhoven', 'Ajax', 'Feyenoord', 'Inter', 'Real Madrid', 'Barcelona', 'Manchester City', 'Liverpool', 'Arsenal'):
    x = S[(S.team == t) & (S.lgv == 'vs ΙΣΧΥΡΟΤΕΡΗ λιγκα')]
    y = S[(S.team == t)]
    if len(y) == 0: continue
    print(f'   {t:20s} z {y.z.mean():.2f} · vs ισχυροτερη: n{len(x):2d} μοντ {(x.lf - x.la).mean() if len(x) else float("nan"):+.2f} αγορα {x.mk.mean() if len(x) else float("nan"):+.2f} πραγμ {x.gd.mean() if len(x) else float("nan"):+.2f} xG−λ {(x.xf - x.lf).mean() if len(x) else float("nan"):+.2f}'
          f' · ΟΛΑ τα ευρωπαικα n{len(y):2d} πραγμ−μοντ {(y.gd - (y.lf - y.la)).mean():+.2f} πραγμ−αγορα {(y.gd - y.mk).mean():+.2f}')
