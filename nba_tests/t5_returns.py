# -*- coding: utf-8 -*-
"""t5_returns.py — TODO 1 (20/10): «ΜΠΟΝΟΥΣ ΕΠΙΣΤΡΟΦΗΣ» σημαντικων παικτων που ελειψαν.
ΕΠΙΣΤΡΟΦΗ (box score, ιδια A/αξια με absence_test):
  mid   = παικτης με μεσο ≥20′ (10 τελευταια φετινα ΜΕ την ομαδα) που ελειψε ≥5 συνεχομενα ματς της ομαδας και ξαναπαιζει (οχι ανταλλαγη).
  start = παικτης που ΔΕΝ επαιξε στα ≥5 πρωτα ματς της ομαδας, πρωτη εμφανιση γι αυτη, περσινος μεσος (10 τελευταια) ≥20′,
          χωρις φετινη εμφανιση σε αλλη ομαδα πριν (οχι ανταλλαγη μεσα στη σεζον).
ΜΠΟΝΟΥΣ: ξεκινα απο το 2ο ματς ΜΕΤΑ την επιστροφη (το ματς επιστροφης ειναι γνωστο μονο εκ των υστερων → οχι look-ahead),
  για Ν ματς της ομαδας: α·(αξια − (−1))·λεπτα/48·w_k στο περιθωριο της ομαδας του. λεπτα = μεσος πριν την απουσια (start: περσινος).
  w_k: σταθερη = 1 · γραμμικη = 1 − k/Ν (k = 0..Ν−1). Δεν δινεται αν ο παικτης ξαναλειπει ≥2 ματς (γνωστο, οπως LOSS[2]) ή αλλαξε ομαδα.
Πλεγμα α {0.25,0.5,0.75} × Ν {5,10,20} × φθορα {σταθερη, γραμμικη}, χωριστα: ολες / μονο start / μονο mid.
ΒΑΣΗ = production CFG_H + 0.75·LOSS[2] + 3.0·(B2A − B2H).
ΠΕΡΙΓΡΑΦΙΚΟ: για τα ματς k = −5..20 γυρω απο την επιστροφη (k=1 = ματς επιστροφης): μεσο υπολοιπο απο την πλευρα της ομαδας που
  παιρνει πισω τον παικτη, μοντελου (ACT − ΒΑΣΗ), αγορας ανοιγματος (ACT − αγορα), και μοντελο − αγορα (± SE).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): LOSO επιλογη (α,Ν,φθορα) με RMSE ολων στις αλλες 4 → περναει αν RMSE καλυτερο
  απο ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% Οκτ-Δεκ οχι χειροτερο (> −1.5pp). (RMSE ολων αλλαζει ΜΟΝΟ στα ματς με μπονους,
  αρα η φορα ειναι ιδια με το RMSE της ομαδας.)"""
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
BASE = MG + 0.75 * L2 + 3.0 * (B2A - B2H)
MKO = np.full(len(G), np.nan)
for i, dct in MKH.items(): MKO[i] = dct['o'][1]
GI = {}
for i in range(len(G)): GI[(G.home.values[i], dD[i])] = (i, 1); GI[(G.away.values[i], dD[i])] = (i, -1)
# ---------- περσινος μεσος (10 τελευταια, οποιαδηποτε ομαδα) ----------
LAST10 = {}
for (p, s), g in A.sort_values('date').groupby(['pid', 's']): LAST10[(p, int(s))] = float(g.MIN.values[-10:].mean())
seas_start = {int(s): g.d.min() for s, g in A.groupby('s')}
# ---------- γεγονοτα επιστροφης ----------
EVT = []                                            # (type, team, s, p, avg, unit, [days after return...], days_before)
for (t, s), g in A.groupby(['team', 's']):
    s = int(s); days = sorted(g.d.unique()); played = {d: dict(zip(x.pid, x.MIN)) for d, x in g.groupby('d')}
    hist = collections.defaultdict(list); pos = {d: j for j, d in enumerate(days)}
    for j, d in enumerate(days):
        for p, m in played[d].items():
            if m <= 0: continue
            H = hist.get(p); typ = None
            if H:
                nmiss = j - pos[H[-1][0]] - 1; avg = float(np.mean([x for _, x in H[-10:]]))
                if nmiss >= 5 and avg >= 20 and not traded(p, t, H[-1][0], d): typ = 'mid'
            elif j >= 5:
                avg = LAST10.get((p, s - 1), 0.0)
                other = any(seas_start[s] <= dd < d and tt != t for dd, tt in appear[p])
                if avg >= 20 and not other: typ = 'start'
            if typ:
                unit = (value(p, s - 1) - REP) * avg / 48
                EVT.append((typ, t, s, p, avg, unit, days[j:j + 21], days[max(0, j - 5):j]))
        for p, m in played[d].items():
            if m > 0: hist[p].append((d, m))
EVT = [e for e in EVT if e[2] in EV]
print(f'\nΓΕΓΟΝΟΤΑ ΕΠΙΣΤΡΟΦΗΣ (σεζον EVAL): {len(EVT)} · μεσο μεγεθος (αξια+1)·λεπτα/48 = {np.mean([e[5] for e in EVT]):.2f} π.')
for Y in EV:
    print(f'   {Y}: start {sum(e[0] == "start" and e[2] == Y for e in EVT):3d} · mid {sum(e[0] == "mid" and e[2] == Y for e in EVT):3d}')
OUTD = {}
for (t, d), lst in OUTS.items():
    for p, avg, v, nm, lastp in lst:
        if nm >= 2: OUTD[(t, d, p)] = 1
def bonus(typ, N, dec):
    B = np.zeros(len(G))
    for e in EVT:
        if typ != 'all' and e[0] != typ: continue
        _, t, s, p, avg, unit, aft, _b = e; d_ret = aft[0]
        for k, d in enumerate(aft[1:N + 1]):
            if (t, d, p) in OUTD or traded(p, t, d_ret, d): continue
            w = 1.0 if dec == 'flat' else 1 - k / N
            i, sg = GI.get((t, d), (None, 0))
            if i is not None: B[i] += sg * unit * w
    return B
ev_m = np.isin(SEAS_G, EV)
base_s = {Y: rm(BASE, [Y]) for Y in EV}
_, rb, _, psb, _ = roi_od(BASE); _, rfb, _, _, _ = roi_od(BASE, msk=ALL)
HDR = f'{"εκδοχη":30s} | RMSE ολα | καλ. | RMSE ομαδας (n)    | ROI Οκτ-Δεκ ≥8%       θετ | ROI ολη ≥8%     θετ'
def line(lab, v, aff):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    print(f'{lab:30s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, aff):6.3f}/{rm(BASE, EV, aff):6.3f} ({int((aff & ev_m).sum()):4d}) | {r1:+6.1f}% ({n1:4d}) {u1:+6.1f}u {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5', flush=True)
    return ps1
print(f'\nΒΑΣΗ: RMSE {rm(BASE, EV):.4f} · ROI Οκτ-Δεκ {rb:+.1f}% · ολη {rfb:+.1f}%')
GRID = [(a, N, dec) for a in (.25, .5, .75) for N in (5, 10, 20) for dec in ('flat', 'lin')]
for typ in ('all', 'start', 'mid'):
    BB = {(N, dec): bonus(typ, N, dec) for N in (5, 10, 20) for dec in ('flat', 'lin')}
    print(f'\n=== ΤΥΠΟΣ: {typ} ===\n{HDR}')
    for a, N, dec in GRID:
        B = BB[(N, dec)]; line(f'α={a:<4g} Ν={N:<2d} {dec}', BASE + a * B, B != 0)
    pk = {Y: min(GRID, key=lambda g: rm(BASE + g[0] * BB[(g[1], g[2])], [x for x in EV if x != Y])) for Y in EV}
    vL = BASE.copy(); aff = np.zeros(len(G), bool)
    for Y in EV:
        mm = SEAS_G == Y; B = BB[(pk[Y][1], pk[Y][2])]; vL[mm] = (BASE + pk[Y][0] * B)[mm]; aff |= mm & (B != 0)
    print(f'LOSO ανα σεζον {[pk[Y] for Y in EV]}'); ps = line(f'LOSO {typ}', vL, aff)
    print('   ανα σεζον RMSE ΒΑΣΗ/LOSO · units Οκτ-Δεκ ΒΑΣΗ/LOSO: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(vL, [Y]):.4f} {psb[Y]:+.1f}/{ps[Y]:+.1f}' for Y in EV))

print('\n=== ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο απο την πλευρα της ομαδας που παιρνει πισω τον παικτη (π., + = η ομαδα ηταν καλυτερη απ οτι προβλεφθηκε) ===')
print('    k<0 = ματς πριν την επιστροφη (μοντελο ΜΕ διορθωση απουσιας) · k=1 = ματς επιστροφης · μοντελο = ΒΑΣΗ χωρις μπονους')
for typ in ('start', 'mid'):
    rows = collections.defaultdict(list)
    for e in EVT:
        if e[0] != typ: continue
        _, t, s, p, avg, unit, aft, bef = e
        seq = [(k - len(bef), d) for k, d in enumerate(bef)] + [(k + 1, d) for k, d in enumerate(aft)]
        for k, d in seq:
            i, sg = GI.get((t, d), (None, 0))
            if i is None or not np.isfinite(BASE[i]): continue
            bk = 'πριν −5..−1' if k < 0 else (str(k) if k <= 5 else ('6-10' if k <= 10 else '11-20'))
            rows[bk].append((sg * (ACT[i] - BASE[i]), sg * (ACT[i] - MKO[i]), sg * (BASE[i] - MKO[i]), unit))
    print(f'  {typ}: {"k":12s} {"n":>5s} | {"μοντελο":>13s} | {"αγορα ανοιγ.":>13s} | {"μοντελο−αγορα":>13s} | μεγεθος')
    for bk in ('πριν −5..−1', '1', '2', '3', '4', '5', '6-10', '11-20'):
        R = np.array(rows[bk]);
        if not len(R): continue
        out = []
        for c in range(3):
            x = R[:, c]; x = x[np.isfinite(x)]; out.append(f'{x.mean():+5.2f}±{x.std() / np.sqrt(len(x)):.2f}' if len(x) else '   —   ')
        print(f'         {bk:12s} {len(R):5d} | {out[0]:>13s} | {out[1]:>13s} | {out[2]:>13s} | {R[:, 3].mean():.2f}')
