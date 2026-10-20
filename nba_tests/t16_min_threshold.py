# -*- coding: utf-8 -*-
"""t16_min_threshold.py — ΚΑΤΩΦΛΙ ΛΕΠΤΩΝ ΣΤΗ ΦΟΡΜΟΥΛΑ ΑΠΟΥΣΙΩΝ (20/10/2026, Στελιος: «γιατι κατω απο 20′ δεν μετραει καθολου; το τεσταραμε;
υπαρχουν σημαντικοι ρολιστες κοντα στα 20′»). Το 20′ ειχε δοκιμαστει ΜΟΝΟ για το παλιο φιλτρο (nba_absence_cutoffs), οχι για το κοστος.
ΒΑΣΗ = live: production + B2B 3 + γνωστες απουσιες (K=2) 0.75·(αξια+2)·λεπτα/48 για παικτες με μ.ο. ≥C′ (10 τελευταια φετινα).
Εκδοχες C ∈ {5, 10, 15, 20 (live), 25}. Ιδια αξιολογηση με t11: RMSE ανα σεζον, ROI ανοιγματος ≥8% Οκτ-Δεκ & ολη, LOSO επιλογη C.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο): η LOSO εκδοχη περνα αν RMSE καλυτερο απο τη ΒΑΣΗ (C=20) σε ≥4/5 σεζον ΚΑΙ ROI Οκτ-Δεκ
  οχι χειροτερο (> −1.5pp) ΚΑΙ ROI ολης οχι χειροτερο (> −1.5pp). Εξοδος: t16_min_threshold_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'absence_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; MG = ns['MG']; A = ns['A']
rm, roi_od, ALL, value, traded = ns['rm'], ns['roi_od'], ns['ALL'], ns['value'], ns['traded']
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
# ιδια λογικη με absence_test (γνωστο εκτος = εχασε τους τελευταιους K αγωνες, B2B: αγνοησε τον χθεσινο), με ΜΕΤΑΒΛΗΤΟ κατωφλι
OUTS = {}
for (t, s), g in A.groupby(['team', 's']):
    days = sorted(g.d.unique()); played = {d: dict(zip(x.pid, x.MIN)) for d, x in g.groupby('d')}
    hist = collections.defaultdict(list)
    for j, d in enumerate(days):
        prev = days[:j]
        if prev:
            usable = prev if (np.datetime64(d) - np.datetime64(prev[-1])).astype(int) > 1 else prev[:-1]
            for p, H in hist.items():
                avg = float(np.mean([m for _, m in H[-10:]]))
                if avg < 5 or not usable: continue
                lastp = H[-1][0]; nmiss = sum(1 for x in usable if x > lastp)
                if nmiss < 2: continue
                OUTS.setdefault((t, np.datetime64(d)), []).append((p, avg, value(p, s - 1), lastp))
        for p, m in played[d].items():
            if m > 0: hist[p].append((d, m))
def loss(C):
    L = np.zeros(len(G))
    for i in range(len(G)):
        for sg, t in ((1, G.home.values[i]), (-1, G.away.values[i])):
            tot = 0.0
            for p, avg, v, lastp in OUTS.get((t, dD[i]), []):
                if avg < C or traded(p, t, lastp, dD[i]): continue
                tot += (v + 2.0) * avg / 48
            L[i] += -sg * tot
    return L
CS = (5, 10, 15, 20, 25)
V = {C: MG + 3.0 * (B2A - B2H) + 0.75 * loss(C) for C in CS}
BASE = V[20]; base_s = {Y: rm(BASE, [Y]) for Y in EV}
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P('NBA · ΚΑΤΩΦΛΙ ΛΕΠΤΩΝ ΣΤΙΣ ΑΠΟΥΣΙΕΣ (αντικαταστατης −2, γνωστες K=2) · 5 σεζον · picks = edge ≥8% στο ανοιγμα')
P(f'{"εκδοχη":22s} | RMSE ολα | καλ. | ROI Οκτ-Δεκ ≥8% (picks, μον., θετ.) | ROI ολη ≥8% (picks, μον., θετ.)')
R = {}
def line(lab, v):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    P(f'{lab:22s} | {rm(v, EV):8.4f} | {bet}/5  | {r1:+6.1f}% ({n1:4d}, {u1:+6.1f}u, {sum(ps1[Y] > 0 for Y in EV)}/5) | {r2:+6.1f}% ({n2:4d}, {u2:+6.1f}u, {sum(ps2[Y] > 0 for Y in EV)}/5)')
    return r1, r2
for C in CS: R[C] = line(f'≥{C}′' + (' (LIVE)' if C == 20 else ''), V[C])
pk = {Y: min(CS, key=lambda C: rm(V[C], [x for x in EV if x != Y])) for Y in EV}
vL = BASE.copy()
for Y in EV: m = SEAS_G == Y; vL[m] = V[pk[Y]][m]
P(f'LOSO επιλογες: {pk}')
rl1, rl2 = line('LOSO', vL)
c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = rl1 - R[20][0] > -1.5; c3 = rl2 - R[20][1] > -1.5
P(f'ΚΡΙΤΗΡΙΑ: (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) Οκτ-Δεκ {rl1 - R[20][0]:+.1f}pp {"✓" if c2 else "✗"} · (3) ολη {rl2 - R[20][1]:+.1f}pp {"✓" if c3 else "✗"} '
  f'→ {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('ανα σεζον RMSE: ' + ' · '.join(f'{Y}: ' + '/'.join(f'{rm(V[C], [Y]):.3f}' for C in CS) for Y in EV) + f'  (σειρα C = {CS})')
open(os.path.join(SC, 't16_min_threshold_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
