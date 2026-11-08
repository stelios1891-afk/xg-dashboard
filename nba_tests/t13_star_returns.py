# -*- coding: utf-8 -*-
"""t13_star_returns.py — ΕΠΙΣΤΡΟΦΗ ΣΤΑΡ (20/10/2026, Στελιος: «το μοντελο μαθαινει απο τα ματς χωρις τον παικτη και μπορει να νομιζει
οτι η ομαδα ειναι χειροτερη + ισως δεν τιμολογει την επιδραση ενος σουπερσταρ οταν γυρναει» → «τρεξε την επιστροφη σταρ»).
Ιδια γεγονοτα με t5_returns (box score, χωρις ανταλλαγες): mid = λειπει ≥5 συνεχομενα ματς μεσα στη σεζον · start = λειπει απο τα ≥5 πρωτα.
ΒΑΣΗ = ΣΗΜΕΡΙΝΟ LIVE: production + B2B 3 + απουσιες 0.75·(αξια+2)·λεπτα/48 (γνωστες, K=2).
ΜΕΓΕΘΟΣ επιστροφης σε «δικους μας» ποντους = 0.75·(αξια+2)·λεπτα/48: ΣΤΑΡ ≥2 (π.χ. Maxey 2.9) · μεσαιοι 1-2 · μικροι <1.
(Α) ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο μοντελου / αγορας ανοιγματος απο την πλευρα της ομαδας, ματς −5..20 γυρω απο την επιστροφη, ανα μεγεθος
    + καλυψη/ROI αν παιζαμε την ομαδα που παιρνει πισω τον σταρ στο ανοιγμα (ματς 1, 2-5, 6-10).
(Β) ΜΠΟΝΟΥΣ ΜΟΝΟ ΓΙΑ ΣΤΑΡ (απο το 2ο ματς μετα την επιστροφη, οπως t5 — χωρις look-ahead): α·(αξια+2)·λεπτα/48 για Ν ματς, σταθερο/φθινον.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο, ιδιο με t5): LOSO επιλογη (α,Ν,φθορα) με RMSE ολων στις αλλες 4 → περναει αν RMSE καλυτερο
  απο ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% Οκτ-Δεκ οχι χειροτερο (> −1.5pp). Εξοδος: t13_star_returns_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't5_returns.py'), encoding='utf-8').read().split('OUTD = {}')[0]
with contextlib.redirect_stdout(_B()):
    exec(src)
sys.stdout.reconfigure(encoding='utf-8')
# ---------- ΣΗΜΕΡΙΝΟ LIVE: αντικαταστατης −2 ----------
REP = -2.0
LH = np.zeros(len(G)); LA = np.zeros(len(G))
for i in range(len(G)):
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    LH[i], _ = team_loss(h, d, 2); LA[i], _ = team_loss(a, d, 2)
BASE = MG + 0.75 * (LH - LA) + 3.0 * (B2A - B2H)
EVT = [(t_, tm, s, p, avg, (value(p, s - 1) + 2.0) * avg / 48, aft, bef) for (t_, tm, s, p, avg, _u, aft, bef) in EVT]
SZ = lambda e: 0.75 * e[5]
TIERS = (('ΣΤΑΡ ≥2 π.', lambda e: SZ(e) >= 2), ('μεσαιοι 1-2 π.', lambda e: 1 <= SZ(e) < 2), ('μικροι <1 π.', lambda e: SZ(e) < 1))
OUTD = {}
for (t, d), lst in OUTS.items():
    for p, avg, v, nm, lastp in lst:
        if nm >= 2: OUTD[(t, d, p)] = 1
MKL = {i: dct['o'] for i, dct in MKH.items()}                 # (L, mk, o1, o2) ανοιγμα
ev_m = np.isin(SEAS_G, EV)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P('NBA · ΕΠΙΣΤΡΟΦΗ ΣΤΑΡ · 5 σεζον · βαση = live (αντικαταστατης −2) · + = η ομαδα που παιρνει πισω τον παικτη ηταν ΚΑΛΥΤΕΡΗ απο την προβλεψη')
for lab, f in TIERS:
    E = [e for e in EVT if f(e)]
    P(f'  {lab:16s}: {len(E):4d} επιστροφες (start {sum(e[0] == "start" for e in E)}, mid {sum(e[0] == "mid" for e in E)}) · μεσο μεγεθος {np.mean([SZ(e) for e in E]):.2f} π.')
P('  παραδειγματα σταρ: ' + ', '.join(f'{PID2NAME.get(e[3], e[3]) if "PID2NAME" in globals() else e[3]}' for e in sorted([e for e in EVT if SZ(e) >= 2], key=lambda e: -SZ(e))[:0]))

P(''); P('=== (Α) ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο γυρω απο την επιστροφη (k=1 = ματς επιστροφης) ===')
for lab, f in TIERS:
    for typ in ('mid', 'start', 'ολα'):
        rows = collections.defaultdict(list); bets = collections.defaultdict(list)
        for e in EVT:
            if not f(e) or (typ != 'ολα' and e[0] != typ): continue
            _, t, s, p, avg, unit, aft, bef = e
            seq = [(k - len(bef), d) for k, d in enumerate(bef)] + [(k + 1, d) for k, d in enumerate(aft)]
            for k, d in seq:
                i, sg = GI.get((t, d), (None, 0))
                if i is None or not np.isfinite(BASE[i]): continue
                bk = 'πριν −5..−1' if k < 0 else ('1' if k == 1 else ('2-5' if k <= 5 else ('6-10' if k <= 10 else '11-20')))
                rows[bk].append((sg * (ACT[i] - BASE[i]), sg * (ACT[i] - MKO[i]), sg * (BASE[i] - MKO[i])))
                if k >= 1 and i in MKL:
                    L, mk, o1, o2 = MKL[i]; x = (ACT[i] + L) * sg; od_ = o1 if sg == 1 else o2
                    bets[bk].append(0.0 if x == 0 else ((od_ - 1) if x > 0 else -1.0))
        if not rows: continue
        P(f'  {lab} · {typ}: {"k":12s} {"n":>5s} | {"μοντελο":>12s} | {"αγορα ανοιγ.":>12s} | {"μοντ.−αγορα":>12s} | ομαδα στο ανοιγμα: καλυψη/ROI')
        for bk in ('πριν −5..−1', '1', '2-5', '6-10', '11-20'):
            R = np.array(rows[bk])
            if not len(R): continue
            cs = []
            for c in range(3):
                x = R[:, c]; x = x[np.isfinite(x)]; cs.append(f'{x.mean():+5.2f}±{x.std() / np.sqrt(len(x)):.2f}' if len(x) else '—')
            b = np.array(bets.get(bk, []))
            bb = f'{100 * (b > 0).sum() / max((b != 0).sum(), 1):4.1f}% / {100 * b.mean():+5.1f}% ({len(b)})' if len(b) else ''
            P(f'      {bk:14s} {len(R):5d} | {cs[0]:>12s} | {cs[1]:>12s} | {cs[2]:>12s} | {bb}')

P(''); P('=== (Β) ΜΠΟΝΟΥΣ ΕΠΙΣΤΡΟΦΗΣ ΜΟΝΟ ΓΙΑ ΣΤΑΡ (≥2 π.) — απο το 2ο ματς μετα την επιστροφη ===')
def bonus(N, dec, f):
    B = np.zeros(len(G))
    for e in EVT:
        if not f(e): continue
        _, t, s, p, avg, unit, aft, _b = e; d_ret = aft[0]
        for k, d in enumerate(aft[1:N + 1]):
            if (t, d, p) in OUTD or traded(p, t, d_ret, d): continue
            w = 1.0 if dec == 'flat' else 1 - k / N
            i, sg = GI.get((t, d), (None, 0))
            if i is not None: B[i] += sg * unit * w
    return B
base_s = {Y: rm(BASE, [Y]) for Y in EV}
n0, rb, u0, psb, _ = roi_od(BASE); _, rfb, _, _, _ = roi_od(BASE, msk=ALL)
P(f'ΒΑΣΗ (live): RMSE {rm(BASE, EV):.4f} · ROI Οκτ-Δεκ {rb:+.1f}% ({n0}, {u0:+.1f}u) · ολη {rfb:+.1f}%')
P(f'{"εκδοχη":24s} | RMSE ολα | καλ. | RMSE ματς με μπονους (n) | ROI Οκτ-Δεκ ≥8%            | ROI ολη ≥8%')
def line(lab, v, aff):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    P(f'{lab:24s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, aff):6.3f}/{rm(BASE, EV, aff):6.3f} ({int((aff & ev_m).sum()):4d})  | '
      f'{r1:+6.1f}% ({n1:4d}) {u1:+6.1f}u {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5')
    return r1, ps1
STAR = TIERS[0][1]
GRID = [(a, N, dec) for a in (.25, .5, .75, 1.0) for N in (5, 10, 20) for dec in ('flat', 'lin')]
BB = {(N, dec): bonus(N, dec, STAR) for N in (5, 10, 20) for dec in ('flat', 'lin')}
for a, N, dec in GRID:
    B = BB[(N, dec)]; line(f'α={a:<4g} Ν={N:<2d} {dec}', BASE + a * B, B != 0)
pk = {Y: min(GRID, key=lambda g: rm(BASE + g[0] * BB[(g[1], g[2])], [x for x in EV if x != Y])) for Y in EV}
vL = BASE.copy(); aff = np.zeros(len(G), bool)
for Y in EV:
    mm = SEAS_G == Y; B = BB[(pk[Y][1], pk[Y][2])]; vL[mm] = (BASE + pk[Y][0] * B)[mm]; aff |= mm & (B != 0)
P(f'LOSO επιλογες: {[pk[Y] for Y in EV]}')
rl, psl = line('LOSO', vL, aff)
c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = rl - rb > -1.5
P(f'ΚΡΙΤΗΡΙΑ: (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) Οκτ-Δεκ {rl - rb:+.1f}pp {"✓" if c2 else "✗"} → {"ΠΕΡΝΑΕΙ" if c1 and c2 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('  ανα σεζον RMSE ΒΑΣΗ/LOSO · μοναδες Οκτ-Δεκ: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(vL, [Y]):.4f} {psb[Y]:+.1f}/{psl[Y]:+.1f}' for Y in EV))
open(os.path.join(SC, 't13_star_returns_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
