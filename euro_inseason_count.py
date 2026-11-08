"""euro_inseason_count.py — 9/10/2026 (Στελιος: «απο ποσα ευρωπαικα και μετα υπαρχει αξια; μηπως τα πρωτα ειναι θορυβος;»).
(Α) Οφελος (ΔRPS vs ΧΩΡΙΣ φετινα, ×10⁻³) ανα ΑΡΙΘΜΟ φετινων ευρωπαικων που εχει ηδη η ομαδα (μεγιστο των 2 ομαδων), B1 & V0, w 0.5/1.
(Β) Κανονας «μετρανε ΜΟΝΟ αφου η ομαδα εχει ≥k ευρωπαικα» (k=1 = σημερα, 3, 5, 7) — RPS ανα σεζον + ROI σημερινη τιμολογηση.
Περιγραφικο· τα φετινα ευρωπαικα περιλαμβανουν και τα προκριματικα (γι' αυτο υπαρχουν ομαδες με 2-6 πριν την 1η αγωνιστικη)."""
import sys, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'cnt'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
(rps_arr, dse, AFF, SEA, PH, SEAS, R_BASE, gen, roi, FLT, CROWN, PIN, BASE, NIH, NIA, N, HID, AID, DATES, SS, live_stack,
 predict_arm) = (g[k] for k in ('rps_arr', 'dse', 'AFF', 'SEA', 'PH', 'SEAS', 'R_BASE', 'gen', 'roi', 'FLT', 'CROWN', 'PIN', 'BASE',
                               'NIH', 'NIA', 'N', 'HID', 'AID', 'DATES', 'SS', 'live_stack', 'predict_arm'))
G = g['g']; _shrink, K, EPS = G['_shrink'], G['K'], G['EPS']
def make_rate(w_in, kmin):
    def rate(st, tid, fold, d):
        pr = G['prior_enr'](st, tid, fold)
        cur, n = st['cur'], st['n']
        obs = G['inseason'](tid, d, fold, st)
        if len(obs) >= kmin:
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
def arm(eq, w, kmin):
    G['eq_obs'] = eq; G['_OBS'] = {}; g['DONE2'].clear()
    L = live_stack(*predict_arm(make_rate(w, kmin))); return L, rps_arr(*L)
def roi_line(L):
    GG = [gen(L, OD) for OD in (CROWN, PIN)]; out = []
    for lab, flt in FLT:
        v = [roi([r for r in x.values() if flt(r)]) for x in GG]
        out.append(f'{lab} {(v[0][0] + v[1][0]) / 2:.0f} {100 * np.nanmean([v[0][1], v[1][1]]):+.1f}%')
    return ' · '.join(out)
NMAX = np.maximum(NIH, NIA)
BK = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 99))
print('(Α) ΟΦΕΛΟΣ ανα αριθμο φετινων ευρωπαικων (μεγιστο των 2 ομαδων) — ΔRPS ×10⁻³ (αρνητικο = καλυτερο) · [σεζον καλυτερες/4]')
print('    n ματς ανα καδο: ' + ' · '.join(f'{a}-{b}: {int(((NMAX >= a) & (NMAX <= b)).sum())}' for a, b in BK))
ARMS = {}
for lab, eq in (('B1', g['eq_B1']), ('V0', g['EQ0'])):
    for w in (0.5, 1.0):
        L, R = arm(eq, w, 1); ARMS[(lab, w)] = (L, R)
        cells = []
        for a, b in BK:
            m = (NMAX >= a) & (NMAX <= b)
            d, s = dse(R[m] - R_BASE[m])
            ns = sum(dse(R[m & (SEA == z)] - R_BASE[m & (SEA == z)])[0] < 0 for z in SEAS if (m & (SEA == z)).sum() > 5)
            cells.append(f'{a}-{b}: {1000 * d:+.2f}±{1000 * s:.2f} [{ns}/4]')
        print(f'   {lab} w={w}: ' + ' · '.join(cells))
print('\n(Β) ΚΑΝΟΝΑΣ «μετρανε μονο απο το k-οστο ευρωπαικο» — ΔRPS ×10⁻³ ολων των επηρεαζομενων (σεζον) · ROI')
print('   ΧΩΡΙΣ φετινα: ROI ' + roi_line(BASE))
for lab, eq in (('B1', g['eq_B1']), ('V0', g['EQ0'])):
    for w in (0.5, 1.0):
        for kmin in (1, 3, 5, 7):
            L, R = ARMS[(lab, w)] if kmin == 1 else arm(eq, w, kmin)
            cs = [dse(R[AFF & (SEA == z)] - R_BASE[AFF & (SEA == z)])[0] for z in SEAS]; d, s = dse(R[AFF] - R_BASE[AFF])
            print(f'   {lab} w={w} k≥{kmin}: {1000 * d:+.2f}±{1000 * s:.2f} (' + ' '.join(f'{1000 * c:+.2f}' for c in cs)
                  + f') {sum(c < 0 for c in cs)}/4 · ROI {roi_line(L)}')
