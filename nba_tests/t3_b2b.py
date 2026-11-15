# -*- coding: utf-8 -*-
"""t3_b2b.py — TODO 5 (20/10): ΕΠΑΝΕΛΕΓΧΟΣ BACK-TO-BACK ΜΕ ΤΙΣ ΑΠΟΥΣΙΕΣ ΜΕΣΑ.
ΒΑΣΗ = production CFG_H (MG) + 0.75·LOSS[2] (γνωστες απουσιες) + 3.0·(B2A − B2H).
ΕΚΔΟΧΕΣ:
 (α) κοινος συντελεστης b ∈ {0,1,1.5,2,2.5,3,3.5}:  MG + .75·L + b·(B2A − B2H)
 (β) ξεχωριστα: bH (μονο γηπ σε B2B) · bA (μονο φιλ σε B2B) ∈ {0,1,…,3.5} · bB (ΚΑΙ οι δυο σε B2B, επι του γηπ) ∈ {−2,−1,0,1,2}
 (γ) ΑΝΑΤΟΛΙΚΟ ΤΑΞΙΔΙ γηπεδουχου: προηγουμενο ματς του ΕΚΤΟΣ (οχι ουδετερο), σε ζωνη ωρας δυτικοτερη, πριν ≤2 μερες
     (≤1 μερα ξεκουρασης). Τιμες βιβλιογραφιας (μελετη 2022): 1 ωρα −1.29, ≥2 ωρες −4.53 · κλιμακα k ∈ {0,.25,.5,.75,1}
     πανω στη ΒΑΣΗ. Ζωνες: ET/CT/MT/PT, PHO = MT χωρις θερινη ωρα (Μαρ-Νοε ιδια με PT).
 (δ) περιγραφικο: OLS του υπολοιπου (ACT − MG − .75·L) στις κατηγοριες (μονο-γηπ, μονο-φιλ, και-οι-δυο, ανατ. 1ω, ανατ. ≥2ω) ± SE.
ΑΞΙΟΛΟΓΗΣΗ: 5 σεζον 2021-22…2025-26, LOSO (επιλογη με RMSE ολων στις αλλες 4).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ «ΠΕΡΝΑΕΙ» (γραφτηκε ΠΡΙΝ το τρεξιμο): η LOSO εκδοχη εχει RMSE (ολα) καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον
ΚΑΙ ROI ανοιγματος edge ≥8% Οκτ-Δεκ οχι χειροτερο (διαφορα > −1.5pp = θορυβος/οχι χειροτερο)."""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0]
exec(src)
sys.stdout.reconfigure(encoding='utf-8')
L2 = LOSS[2][0]
# ---------- B2B ----------
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}; lastloc = {}
TZ = {**{t: -5 for t in 'ATL BOS BRK CHO CLE DET IND MIA NYK ORL PHI TOR WAS'.split()},
      **{t: -6 for t in 'CHI DAL HOU MEM MIL MIN NOP OKC SAS'.split()},
      **{t: -7 for t in 'DEN UTA PHO'.split()}, **{t: -8 for t in 'GSW LAC LAL POR SAC'.split()}}
def tz(t, d):
    ts = pd.Timestamp(d); y = ts.year
    dst0 = pd.Timestamp(y, 3, 8) + pd.Timedelta(days=(6 - pd.Timestamp(y, 3, 8).weekday()) % 7)
    dst1 = pd.Timestamp(y, 11, 1) + pd.Timedelta(days=(6 - pd.Timestamp(y, 11, 1).weekday()) % 7)
    dst = dst0 <= ts < dst1
    return TZ[t] + (1 if dst and t != 'PHO' else 0)
EAST = np.zeros(len(G))                                  # ωρες προς ανατολη (γηπεδουχος), μονο με ≤1 μερα ξεκουρασης
NEU = G.neutral.values
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    if not NEU[i] and (s, h_) in last:
        gap = int((d - last[(s, h_)]).astype(int)); loc = lastloc[(s, h_)]
        if gap <= 2 and loc is not None and loc != h_:
            EAST[i] = max(0, tz(h_, d) - tz(loc, last[(s, h_)]))
    loc_i = None if NEU[i] else h_
    last[(s, h_)] = d; last[(s, a_)] = d; lastloc[(s, h_)] = loc_i; lastloc[(s, a_)] = loc_i
HO = B2H * (1 - B2A); AO = B2A * (1 - B2H); BO = B2H * B2A
E1 = (EAST == 1).astype(float); E2 = (EAST >= 2).astype(float)
CORE = MG + 0.75 * L2
BASE = CORE + 3.0 * (B2A - B2H)
ev_m = np.isin(SEAS_G, EV)
print(f'\nΑγωνες EVAL {ev_m.sum()} · μονο γηπ B2B {int((HO * ev_m).sum())} · μονο φιλ B2B {int((AO * ev_m).sum())} · και οι δυο {int((BO * ev_m).sum())} · '
      f'ανατολ. ταξιδι γηπ (≤1 μερα ξεκ.) 1ω {int((E1 * ev_m).sum())} · ≥2ω {int((E2 * ev_m).sum())}')
AFF = (B2H + B2A) > 0
base_s = {Y: rm(BASE, [Y]) for Y in EV}
nb, rb, ub, psb, _ = roi_od(BASE); nfb, rfb, ufb, psfb, _ = roi_od(BASE, msk=ALL)
def line(lab, v, aff=AFF):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-5 for Y in EV)
    print(f'{lab:34s} | {rm(v, EV):7.4f} | {bet}/5 | {rm(v, EV, aff):7.3f} | {r1:+6.1f}% ({n1:4d}) {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5', flush=True)
HDR = f'{"εκδοχη":34s} | RMSE ολα| καλ.| RMSE ομ.| ROI Οκτ-Δεκ ≥8% θετ.   | ROI ολη ≥8% θετ.'
print('\n=== (δ) ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο (ACT − MG − .75·L) ~ κατηγοριες (π., θετικο = υπερ γηπεδουχου) ===')
X = [HO, AO, BO, E1, E2]; m = ev_m & np.isfinite(CORE)
y = (ACT - CORE)[m]; Xm = np.c_[np.ones(m.sum()), *[x[m] for x in X]]; c, *_ = np.linalg.lstsq(Xm, y, rcond=None)
r = y - Xm @ c; s2 = r.var() * len(y) / (len(y) - Xm.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(Xm.T @ Xm)))
for nm, cc, ss in zip(['σταθερα', 'μονο γηπ B2B', 'μονο φιλ B2B', 'και οι δυο B2B', 'ανατ. ταξιδι 1ω', 'ανατ. ταξιδι ≥2ω'], c, se):
    print(f'   {nm:20s} {cc:+6.2f} ± {ss:.2f}')
print('   ανα σεζον (μονο γηπ / μονο φιλ):')
for Y in EV:
    mY = m & (SEAS_G == Y); yy = (ACT - CORE)[mY]; XX = np.c_[np.ones(mY.sum()), *[x[mY] for x in X]]; cY, *_ = np.linalg.lstsq(XX, yy, rcond=None)
    print(f'     {Y}: γηπ {cY[1]:+5.2f} · φιλ {cY[2]:+5.2f} · δυο {cY[3]:+5.2f} · ανατ1 {cY[4]:+5.2f} · ανατ2 {cY[5]:+5.2f}')

print(f'\n=== (α) ΚΟΙΝΟΣ ΣΥΝΤΕΛΕΣΤΗΣ (ομαδα = αγωνες με B2B: {int((AFF & ev_m).sum())}) ===\n{HDR}')
line('χωρις B2B (b=0)', CORE)
GR = (1, 1.5, 2, 2.5, 3, 3.5)
for b in GR: line(f'b={b:g}' + ('  (ΒΑΣΗ)' if b == 3 else ''), CORE + b * (B2A - B2H))
pick = {Y: min((0,) + GR, key=lambda b: rm(CORE + b * (B2A - B2H), [x for x in EV if x != Y])) for Y in EV}
vL = BASE.copy()
for Y in EV: mm = SEAS_G == Y; vL[mm] = CORE[mm] + pick[Y] * (B2A - B2H)[mm]
print(f'LOSO επιλογη b ανα σεζον {[pick[Y] for Y in EV]}'); line('LOSO κοινο b', vL)

print('\n=== (β) ΞΕΧΩΡΙΣΤΑ γηπ / φιλ / και οι δυο ===')
G0 = (0,) + GR; GB = (-2, -1, 0, 1, 2)
def vsep(bh, ba, bb): return CORE - bh * HO + ba * AO + bb * BO
combos = [(bh, ba, bb) for bh in G0 for ba in G0 for bb in GB]
SE_ = {Y: {cb: None for cb in []} for Y in EV}
sq = {}
for cb in combos:
    v = vsep(*cb); sq[cb] = {Y: rm(v, [Y]) for Y in EV}
def rm_oth(cb, Y):
    oth = [x for x in EV if x != Y]; return np.sqrt(np.mean([sq[cb][x] ** 2 for x in oth]))   # ~ισοβαρη σεζον
best_all = min(combos, key=lambda cb: rm(vsep(*cb), EV))
print(f'{HDR}')
line(f'βελτιστο in-sample bH/bA/bB={best_all}', vsep(*best_all))
for cb in ((3, 3, 0), (1.5, 3, 0), (3, 1.5, 0), (2, 2, 0), (1, 1, 0)):
    line(f'bH/bA/bB={cb}', vsep(*cb))
pk = {}
for Y in EV:
    oth = [x for x in EV if x != Y]; pk[Y] = min(combos, key=lambda cb: rm(vsep(*cb), oth))
vL2 = BASE.copy()
for Y in EV: mm = SEAS_G == Y; vL2[mm] = vsep(*pk[Y])[mm]
print(f'LOSO (bH,bA,bB) ανα σεζον {[pk[Y] for Y in EV]}'); line('LOSO ξεχωριστα', vL2)

print(f'\n=== (γ) ΑΝΑΤΟΛΙΚΟ ΤΑΞΙΔΙ γηπεδουχου (πανω στη ΒΑΣΗ· ομαδα = αγωνες με ταξιδι: {int(((E1 + E2) > 0)[ev_m].sum())}) ===\n{HDR}')
EAFF = (E1 + E2) > 0; ELIT = -1.29 * E1 - 4.53 * E2
for k in (0, .25, .5, .75, 1.0): line(f'k={k:g} × (−1.29 / −4.53)' + ('  (ΒΑΣΗ)' if k == 0 else ''), BASE + k * ELIT, EAFF)
pkE = {Y: min((0, .25, .5, .75, 1.0), key=lambda k: rm(BASE + k * ELIT, [x for x in EV if x != Y])) for Y in EV}
vE = BASE.copy()
for Y in EV: mm = SEAS_G == Y; vE[mm] = (BASE + pkE[Y] * ELIT)[mm]
print(f'LOSO k ανα σεζον {[pkE[Y] for Y in EV]}'); line('LOSO ανατολικο', vE, EAFF)
print('\nΑΝΑ ΣΕΖΟΝ RMSE (ΒΑΣΗ / LOSO κοινο / LOSO ξεχωρ. / LOSO ανατ.) και ROI Οκτ-Δεκ units:')
for Y in EV:
    print(f'   {Y}: {base_s[Y]:.4f} / {rm(vL, [Y]):.4f} / {rm(vL2, [Y]):.4f} / {rm(vE, [Y]):.4f} · units ΒΑΣΗ {psb[Y]:+.1f} κοινο {roi_od(vL)[3][Y]:+.1f} ξεχ {roi_od(vL2)[3][Y]:+.1f} ανατ {roi_od(vE)[3][Y]:+.1f}')
