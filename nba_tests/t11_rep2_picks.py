# -*- coding: utf-8 -*-
"""t11_rep2_picks.py — ΑΝΤΙΚΑΤΑΣΤΑΤΗΣ −2 ΑΝΤΙ −1 ΣΤΙΣ ΑΠΟΥΣΙΕΣ: ΚΕΡΔΟΣ ΣΤΑ PICKS; (20/10/2026, Στελιος «τρεξτο ναι» μετα το t10).
Κοστος απωντα = 0.75 × (αξια − ΑΝΤΙΚΑΤΑΣΤΑΤΗΣ) × λεπτα/48. Live: αντικαταστατης −1. Τεστ: −1.5 / −2 / −2.5.
ΒΑΣΗ = production (ιδια με t3/t_common): MG + 3.0·(B2A − B2H) + 0.75·LOSS[2] (γνωστες απουσιες, χωρις ματια στο μελλον).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο, ιδιο με τα t3/t4): η LOSO εκδοχη (επιλογη με RMSE στις αλλες 4 σεζον)
  (1) RMSE καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ (2) ROI ανοιγματος edge ≥8% Οκτ-Δεκ οχι χειροτερο (διαφορα > −1.5pp)
  ΚΑΙ (3) ROI ολης της σεζον ≥8% οχι χειροτερο (> −1.5pp). Εξοδος: t11_rep2_picks_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'absence_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; MG = ns['MG']; ACT = ns['ACT']
rm, roi_od, ALL, team_loss = ns['rm'], ns['roi_od'], ns['ALL'], ns['team_loss']
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def loss(rep, K=2):
    ns['REP'] = rep
    LH = np.zeros(len(G)); LA = np.zeros(len(G))
    for i in range(len(G)):
        h, a, d = G.home.values[i], G.away.values[i], dD[i]
        LH[i], _ = team_loss(h, d, K); LA[i], _ = team_loss(a, d, K)
    return LH - LA
REPS = (-1.0, -1.5, -2.0, -2.5)
V = {}
for K in (2, 1):
    for r in REPS:
        V[(K, r)] = MG + 3.0 * (B2A - B2H) + 0.75 * loss(r, K)
BASE = V[(2, -1.0)]
base_s = {Y: rm(BASE, [Y]) for Y in EV}
P('NBA · ΑΝΤΙΚΑΤΑΣΤΑΤΗΣ ΣΤΙΣ ΑΠΟΥΣΙΕΣ: −1 (live) vs −1.5 / −2 / −2.5 · 5 σεζον · picks = edge ≥8% στο ΑΝΟΙΓΜΑ')
P(f'{"εκδοχη":30s} | RMSE ολα | καλ.σεζ | ROI Οκτ-Δεκ ≥8%  (picks, μον., θετ.σεζ) | ROI ολη ≥8%  (picks, μον., θετ.σεζ)')
def line(lab, v):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-5 for Y in EV)
    P(f'{lab:30s} | {rm(v, EV):8.4f} | {bet}/5     | {r1:+6.1f}% ({n1:4d}, {u1:+6.1f}u, {sum(ps1[Y] > 0 for Y in EV)}/5)       '
      f'| {r2:+6.1f}% ({n2:4d}, {u2:+6.1f}u, {sum(ps2[Y] > 0 for Y in EV)}/5)')
    return r1, r2
for K in (2, 1):
    P(f'-- γνωστες απουσιες K={K} ({"ιδιο με τα προηγουμενα τεστ" if K == 2 else "και οσοι εχασαν μονο το προηγουμενο ματς"}) --')
    for r in REPS:
        line(f'αντικαταστατης {r:+g}' + (' (LIVE)' if r == -1.0 else ''), V[(K, r)])
P('')
P('-- LOSO (K=2): διαλεγω αντικαταστατη με RMSE στις 4 σεζον, εφαρμοζω στην 5η --')
vL = BASE.copy(); pick = {}
for Y in EV:
    oth = [x for x in EV if x != Y]; pick[Y] = min(REPS, key=lambda r: rm(V[(2, r)], oth)); m = SEAS_G == Y; vL[m] = V[(2, pick[Y])][m]
P(f'  επιλογες ανα σεζον: {pick}')
rb1, rb2 = line('ΒΑΣΗ (live, −1)', BASE)
rl1, rl2 = line('LOSO', vL)
c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-5 for Y in EV) >= 4; c2 = rl1 - rb1 > -1.5; c3 = rl2 - rb2 > -1.5
P(f'  ΚΡΙΤΗΡΙΑ: (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) Οκτ-Δεκ {rl1 - rb1:+.1f}pp {"✓" if c2 else "✗"} · (3) ολη {rl2 - rb2:+.1f}pp {"✓" if c3 else "✗"} '
  f'→ {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('')
P('-- ανα σεζον (ROI Οκτ-Δεκ / ολη, μοναδες) --')
for lab, v in (('ΒΑΣΗ −1', BASE), ('−2', V[(2, -2.0)])):
    _, _, _, ps1, n1 = roi_od(v); _, _, _, ps2, n2 = roi_od(v, msk=ALL)
    P(f'  {lab:8s} ' + ' · '.join(f'{Y}: {ps1[Y]:+5.1f}u/{n1[Y]} | {ps2[Y]:+5.1f}u/{n2[Y]}' for Y in EV))
open(os.path.join(SC, 't11_rep2_picks_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
