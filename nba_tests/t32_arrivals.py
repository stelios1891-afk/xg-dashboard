# -*- coding: utf-8 -*-
"""t32_arrivals.py — ΠΙΣΤΩΣΗ ΤΩΝ ΠΑΙΚΤΩΝ ΠΟΥ ΕΡΧΟΝΤΑΙ ΜΕ ΜΕΤΑΓΡΑΦΗ (21/10/2026, Στελιος «τρεξε τα τεστ»).
Αφορμη (t31): ομαδες που «πηραν» στην προθεσμια παιζουν −1.74 π. κατω απο το μοντελο τις 20 επομενες μερες· οι αφιξεις παιζουν λιγοτερα λεπτα
(24.1 → 22.1, βασικοι 30.8 → 27.6) απ οσα πιστωνονται (λεπτα παλιας ομαδας).
ΒΑΣΗ = live (t15: αντιγραφο live ΜΕ μεταγραφες α 1.0, αντικ. −2· πιστωση αφιξης μονο στα ματς που επαιξε).
ΠΑΡΑΛΛΑΓΕΣ (μονο ο παικτης που ΕΡΧΕΤΑΙ· ο παικτης που φευγει μενει ιδιος):
  (α) λεπτα × f, f ∈ {1.0, 0.9, 0.8}
  (β) σταδιακη πιστωση: βαρος min(1, j/R) στο j-οστο ματς του με τη νεα ομαδα, R ∈ {0 (ολη απο την αρχη), 3, 5, 10}
  (γ) ολοι οι συνδυασμοι f × R (12)
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ιδιο με t15/t11): LOSO με RMSE στις αλλες 4· ΠΕΡΝΑ αν RMSE καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% ολης
  οχι χειροτερο (> −1.5pp) ΚΑΙ Φεβ-Απρ οχι χειροτερο (> −1.5pp). Περιγραφικα: λαθος μοντελου για ομαδες που ενισχυθηκαν, ματς 1-5 / 6-15 / 16-30.
Εξοδος: t32_arrivals_out.txt"""
import os, sys, io, contextlib, collections, itertools
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE0 = ns['BASE']
EVTS, TG, PLAYED, value, rm, roi_od, ALL, FA, MKH = ns['EVTS'], ns['TG'], ns['PLAYED'], ns['value'], ns['rm'], ns['roi_od'], ns['ALL'], ns['FA'], ns['MKH']
# GIDX με τον αυξοντα αριθμο ματς του παικτη στη νεα ομαδα (j)
GI = collections.defaultdict(list)
for s, t, tau, p, sgn, mm in EVTS:
    n = 0; j = 0
    for i in TG.get((s, t), []):
        if dD[i] < tau: continue
        n += 1
        if sgn > 0:
            if (p, t, dD[i]) not in PLAYED: continue
            j += 1
        side = 1 if G.home.values[i] == t else -1
        GI[i].append((side, sgn, value(p, s - 1), mm, n, j))
def adjv(f, R):
    X = np.zeros(len(G))
    for i, lst in GI.items():
        for side, sgn, v, mm, n, j in lst:
            w = 1.0
            if sgn > 0:
                mm = mm * f
                if R: w = min(1.0, j / R)
            X[i] += side * sgn * 0.75 * (v + 2.0) * mm / 48 * w
    return X
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
BASE = BASE0 + adjv(1.0, 0)
assert np.allclose(adjv(1.0, 0), ns['adj'](1.0, -2.0, None)), 'η βαση δεν ταιριαζει με το live του t15'
base_s = {Y: rm(BASE, [Y]) for Y in EV}
_, rb_all, _, _, _ = roi_od(BASE, msk=ALL); _, rb_fa, _, _, _ = roi_od(BASE, msk=FA)
AFF = np.zeros(len(G), bool); AFF[list(GI)] = True
P('NBA · ΠΙΣΤΩΣΗ ΑΦΙΞΕΩΝ (μεταγραφες μεσα στη σεζον) · βαση = live · 5 σεζον')
P(f'{"εκδοχη":22s} | RMSE ολα | καλ. | RMSE επηρ. | ROI ολη ≥8%          | ROI Φεβ-Απρ ≥8%')
VV = {}
def line(lab, v):
    n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); n3, r3, u3, ps3, _ = roi_od(v, msk=FA)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    P(f'{lab:22s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, AFF):9.4f} | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5 | {r3:+6.1f}% ({n3:4d}) {sum(ps3[Y] > 0 for Y in EV)}/5')
    return r2, r3
line('ΒΑΣΗ (live)', BASE)
GRID = list(itertools.product((1.0, 0.9, 0.8), (0, 3, 5, 10)))
for f, R in GRID:
    VV[(f, R)] = BASE0 + adjv(f, R)
    if (f, R) != (1.0, 0): line(f'λεπτα ×{f:<4g} σταδ. R={R}', VV[(f, R)])
VV[(1.0, 0)] = BASE
for nm, sub in (('(α) μονο λεπτα', [g for g in GRID if g[1] == 0]), ('(β) μονο σταδιακη', [g for g in GRID if g[0] == 1.0]), ('(γ) συνδυασμοι', GRID)):
    pk = {Y: min(sub, key=lambda g: rm(VV[g], [x for x in EV if x != Y])) for Y in EV}
    vL = BASE.copy()
    for Y in EV: m = SEAS_G == Y; vL[m] = VV[pk[Y]][m]
    P(''); P(f'{nm} · LOSO επιλογες {pk}')
    r2, r3 = line(f'LOSO {nm[:3]}', vL)
    c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = r2 - rb_all > -1.5; c3 = r3 - rb_fa > -1.5
    P(f'  ΚΡΙΤΗΡΙΑ: RMSE ≥4/5 {"✓" if c1 else "✗"} · ολη {r2 - rb_all:+.1f}pp {"✓" if c2 else "✗"} · Φεβ-Απρ {r3 - rb_fa:+.1f}pp {"✓" if c3 else "✗"} → {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
    P('  ανα σεζον RMSE ΒΑΣΗ/LOSO: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(vL, [Y]):.4f}' for Y in EV))
# περιγραφικο: ομαδες που ενισχυθηκαν καθαρα
P(''); P('=== ΠΕΡΙΓΡΑΦΙΚΟ: ομαδα που ενισχυθηκε καθαρα (≥0.5 π.) — λαθος (πραγματικο − προβλεψη), βαση vs (0.9, R5) vs (0.8, R10) ===')
X0 = adjv(1.0, 0)
for lab, lo, hi in (('1-5', 1, 5), ('6-15', 6, 15), ('16-30', 16, 30)):
    e = {k: [] for k in ('b', 'a', 'c')}
    for i, lst in GI.items():
        if not np.isfinite(BASE[i]) or SEAS_G[i] not in EV: continue
        n = min(x[4] for x in lst); x = X0[i]
        if abs(x) < 0.5 or not (lo <= n <= hi): continue
        sg = np.sign(x)
        e['b'].append(sg * (ACT[i] - BASE[i])); e['a'].append(sg * (ACT[i] - VV[(0.9, 5)][i])); e['c'].append(sg * (ACT[i] - VV[(0.8, 10)][i]))
    P(f'  ματς {lab:6s} n {len(e["b"]):4d} · βαση {np.mean(e["b"]):+5.2f} · (0.9, R5) {np.mean(e["a"]):+5.2f} · (0.8, R10) {np.mean(e["c"]):+5.2f}')
open(os.path.join(SC, 't32_arrivals_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
