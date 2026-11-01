# -*- coding: utf-8 -*-
"""t4_carry_roster.py — TODO 4 (20/10): η περσινη εικονα να σβηνει αναλογα με την ΑΛΛΑΓΗ ΡΟΣΤΕΡ.
μεριδιο (share) = Σ περσινα λεπτα (ΣΤΗΝ ΙΔΙΑ ομαδα) των παικτων που επαιξαν στο 1ο ματς της σεζον / συνολο περσινων λεπτων ομαδας.
carry_ομαδας = c0 · share^δ  (εφαρμογη στο o0/d0/p0 της αφετηριας· τα υπολοιπα του production ιδια: ροστερ Δ, ειδικοι, φιλικα).
Πλεγμα c0 ∈ {0.8,0.9,1.0} × δ ∈ {0,0.5,1,1.5}  (c0=.8, δ=0 = σημερα).
ΒΑΣΗ συγκρισης = production (c0 .8, δ 0) + 0.75·LOSS[2] + 3.0·(B2A − B2H)· καθε εκδοχη παιρνει τα ιδια LOSS/B2B.
Σημ.: το ρόστερ 1ου ματς ειναι ο ιδιος ορισμος (W1) που χρησιμοποιει ηδη το production roster prior.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): RMSE αγων 1-15 καλυτερο απο ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% Οκτ-Δεκ
οχι χειροτερο (> −1.5pp). Επισης LOSO επιλογη (c0, δ) με RMSE αγων 1-15 στις αλλες 4."""
import os, sys, collections
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0]
exec(src)
sys.stdout.reconfigure(encoding='utf-8')
L2 = LOSS[2][0]
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
EXTRA = 0.75 * L2 + 3.0 * (B2A - B2H)
EARLY = GN <= 15
# ---------- μεριδιο επιστρεφοντων λεπτων ----------
SHARE = {}
for s in sorted(A.s.unique()):
    if s - 1 not in set(A.s): continue
    cur = A[A.s == s]; prev = A[A.s == s - 1]
    for t in sorted(cur.team.unique()):
        tg = cur[cur.team == t].sort_values(['date', 'GAME_ID']); g1 = tg.GAME_ID.iloc[0]
        ros = set(tg[tg.GAME_ID == g1].pid); pt = prev[prev.team == t].groupby('pid').MIN.sum()
        SHARE[(int(s), t)] = float(pt[pt.index.isin(ros)].sum() / pt.sum()) if pt.sum() > 0 else 1.0
print('\nΜΕΡΙΔΙΟ ΕΠΙΣΤΡΕΦΟΝΤΩΝ ΛΕΠΤΩΝ ανα σεζον: μεσος / ελαχ. / ομαδες <0.5 / <0.6')
for Y in EV:
    v = {t: x for (s, t), x in SHARE.items() if s == Y}; lo = sorted(v.items(), key=lambda z: z[1])[:3]
    print(f'   {Y}: μ {np.mean(list(v.values())):.2f} · min {min(v.values()):.2f} · <0.5: {sum(x < .5 for x in v.values()):2d} · <0.6: {sum(x < .6 for x in v.values()):2d} · χαμηλοτερες {", ".join(f"{t} {x:.2f}" for t, x in lo)}')

fit_mu = F.fit_mu
def run_carry(c0, dl, cfg=(0.8, 8, 60, .75, 5.0, 1.0, .75, .25)):
    C_ = F._W['C']; Z = F._W['Z']; G_ = C_.G
    _c, lam, HL, lw, muw, beta, kx, kp = cfg; h = 2.0
    EH, EA = C_.EHA[lw]; R2 = C_._radj2()['V0|W1']
    mg = np.full(len(G_), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(G_.pace.mean())
    for s in C_.SEAS:
        sidx = np.where(G_.season.values == s)[0]
        teams = sorted(set(G_.home.values[sidx]) | set(G_.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        adj = np.array([beta * R2.get(f'{s}|{t}', 0.0) + kx * Z['C'].get(f'{s}|{t}', 0.0) + kp * Z['P'].get(f'{s}|{t}', 0.0) for t in teams])
        car = np.array([c0 * (SHARE.get((int(s), t), 1.0) ** dl if dl > 0 else 1.0) for t in teams])
        o0 = car * np.array([prior.get(t, (0, 0, 0))[0] for t in teams]) + adj / 2
        d0 = car * np.array([prior.get(t, (0, 0, 0))[1] for t in teams]) - adj / 2
        p0 = car * np.array([prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in G_.home.values[sidx]]); ai = np.array([ix[t] for t in G_.away.values[sidx]])
        nt = (~G_.neutral.values[sidx]).astype(float); hb = nt * h / 2; dn = C_.dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = G_.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_mu(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0, muw)
                pm, Pc = C_.fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        if F.END_APR != 1.0 and (F.END_APR_BEFORE is None or s < F.END_APR_BEFORE):
            w = w * np.where(G_.date.dt.month.values[sidx] == 4, F.END_APR, 1.0)
        mu, O, Dd = fit_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, muw)
        pm, Pc = C_.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return mg

BASE = MG + EXTRA
chk = run_carry(0.8, 0) + EXTRA
print(f'\n(ελεγχος αναπαραγωγης production: max |Δ| {np.nanmax(np.abs(chk - BASE)):.5f})')
base_s = {Y: rm(BASE, [Y], EARLY) for Y in EV}
LOWS = np.array([SHARE.get((int(SEAS_G[i]), G.home.values[i]), 1) < .6 or SHARE.get((int(SEAS_G[i]), G.away.values[i]), 1) < .6 for i in range(len(G))]) & EARLY
_, rb, _, psb, _ = roi_od(BASE)
print(f'\n{"εκδοχη":22s} | RMSE 1-15 (καλ.) | RMSE ολα | RMSE 1-15 share<.6 | ROI Οκτ-Δεκ ≥8%        θετ | ROI ολη ≥8%        θετ')
V = {}
for c0 in (0.8, 0.9, 1.0):
    for dl in (0, 0.5, 1, 1.5):
        v = BASE if (c0 == .8 and dl == 0) else run_carry(c0, dl) + EXTRA; V[(c0, dl)] = v
        n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); bet = sum(rm(v, [Y], EARLY) < base_s[Y] - 1e-5 for Y in EV)
        print(f'c0={c0:.1f} δ={dl:<3g}{"(ΒΑΣΗ)" if c0 == .8 and dl == 0 else "      "} | {rm(v, EV, EARLY):8.4f} ({bet}/5) | {rm(v, EV):8.4f} | {rm(v, EV, LOWS):10.3f}         | '
              f'{r1:+6.1f}% ({n1:4d}) {u1:+6.1f}u {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5', flush=True)
pk = {Y: min(V, key=lambda k: rm(V[k], [x for x in EV if x != Y], EARLY)) for Y in EV}
vL = BASE.copy()
for Y in EV: mm = SEAS_G == Y; vL[mm] = V[pk[Y]][mm]
n1, r1, u1, ps1, _ = roi_od(vL)
print(f'\nLOSO (c0,δ) ανα σεζον {[pk[Y] for Y in EV]} → RMSE 1-15 {rm(vL, EV, EARLY):.4f} (ΒΑΣΗ {rm(BASE, EV, EARLY):.4f}) · καλυτερο {sum(rm(vL, [Y], EARLY) < base_s[Y] - 1e-5 for Y in EV)}/5 · ROI Οκτ-Δεκ {r1:+.1f}% ({n1}) vs ΒΑΣΗ {rb:+.1f}%')
print('ανα σεζον RMSE 1-15 ΒΑΣΗ / LOSO · units Οκτ-Δεκ ΒΑΣΗ / LOSO:')
for Y in EV: print(f'   {Y}: {base_s[Y]:.4f} / {rm(vL, [Y], EARLY):.4f} · {psb[Y]:+.1f} / {ps1[Y]:+.1f}')
