# -*- coding: utf-8 -*-
"""el_pir_shrink_test.py — EUROLEAGUE ΧΑΝΤΙΚΑΠ: μαζεμα PIR/40 προς τον ΜΕΣΟ παικτη αντι για PIR 0 (23/10/2026, Στελιος «οκ τρεξε το τεστ»).
Το live (el_absence.pir40) = ΣPIR/(Σλεπτα + 200)·40 → με λιγα λεπτα (καινουργιοι) το PIR/40 πεφτει προς 0 και το κοστος βγαινει αρνητικο
(φετος 55/64 χωρις περσινα: π.χ. T. Martin 15.0 → 6.7 → −0.27 π.). ΔΙΟΡΘΩΣΗ: (ΣPIR + 200·12.1/40)/(Σλεπτα + 200)·40 (12.1 = PIR_MU του live).
Στησιμο: el_absence_v2_test V1 (= live R0: 1481 ματς E2021-25, αποντες απο box scores, ανοιγμα Crown, σ 11.5, picks ≥8%, LOSO β0/β1).
ΙΔΙΑ ΟΛΑ (τυπος, g(k), τακτικος ≥3/10, ≥10′)· αλλαζει ΜΟΝΟ η γραμμη του PIR.
ΠΡΟ-ΔΗΛΩΜΕΝΑ: ΠΕΡΝΑ αν RMSE διαφορας καλυτερο απο R0 σε ≥4/5 σεζον ΚΑΙ μοναδες ≥ R0 ΚΑΙ θετικες σεζον ≥4/5.
ΕΛΕΓΧΟΣ: R0 = 626 picks / +65.8μ, αλλιως STOP. Περιγραφικα: αγωνιστικες 1-10 vs 11+, χωρις περσινα vs με, παραδειγματα.
Εξοδος: el_pir_shrink_test_out.txt"""
import sys, io, contextlib, collections, math
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
PAV = open('el_player_absence_value.py', encoding='utf-8').read()
OLD = "    per40 = a[:, 1:].sum(0) / (mins + PRIOR_MIN) * 40"
assert PAV.count(OLD) == 1
FIX = OLD + "\n    per40[1] = (a[:, 2].sum() + PRIOR_MIN * 12.1 / 40) / (mins + PRIOR_MIN) * 40"
V2 = open('el_absence_v2_test.py', encoding='utf-8').read().split("P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ")[0]
SRC_OPEN = "open('el_player_absence_value.py', encoding='utf-8').read()"
assert V2.count(SRC_OPEN) == 1
def build(src):
    ns = {'PAV_SRC': src}
    with contextlib.redirect_stdout(_B()):
        exec(V2.replace(SRC_OPEN, 'PAV_SRC'), ns)
    return ns
A, Bn = build(PAV), build(PAV.replace(OLD, FIX))
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
SE = A['SE']; rows0, rows1 = A['rows'], Bn['rows']; keys = A['keys']
assert len(rows0) == len(rows1) and all(a['y'] == b['y'] and a['act'] == b['act'] for a, b in zip(rows0, rows1))
Y = A['Y']; ys = A['ys']; TG = A['TG']; NAME = A['NAME']
def held(ns):
    h = np.zeros(len(Y))
    for s in SE:
        b, pr = ns['fit']([0, 1], [x for x in SE if x != s]); h[ys == s] = pr[ys == s]
    return h, ns['fit']([0, 1], SE)[0]
H0, b0 = held(A); H1, b1 = held(Bn)
rmse = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2)))
# ---- αγωνιστικη ≈ φετινα ματς γηπεδουχου πριν + 1 ----
rnd = np.array([sum(1 for x in TG.get((sea, hc), []) if x[0] < ts - 3600) + 1 for sea, hc, ac, ts in keys])
def picks(rows, adj, mask):
    U = collections.defaultdict(list); Phi = A['Phi']
    for r, a, mk in zip(rows, adj, mask):
        if not mk: continue
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        U[r['y']].append(((od - 1) if (r['act'] + L) * sd > 0 else (0 if (r['act'] + L) * sd == 0 else -1)) if e >= .08 else None)
    return U
def summ(U):
    u = [x for v in U.values() for x in v if x is not None]; pos = sum(1 for s in SE if [x for x in U[s] if x is not None] and sum(x for x in U[s] if x is not None) > 0)
    return len(u), sum(u), (np.mean(u) * 100 if u else float('nan')), pos, {s: sum(x for x in U[s] if x is not None) for s in SE}
ALL = np.ones(len(Y), bool)
P(f'ματς {len(Y)} (E2021-25) · αποντες {sum(len(r["ah"]) + len(r["aa"]) for r in rows0)}')
P(f'κλιμακα z (μεσος/τυπ.απ. PIR/40 των αποντων): R0 {A["MU"]["pir"]:.1f}/{A["SD"]["pir"]:.1f} · ΔΙΟΡΘΩΣΗ {Bn["MU"]["pir"]:.1f}/{Bn["SD"]["pir"]:.1f}')
P(f'συντελεστες (ολα τα δεδομενα, ποντοι ανα 40′ απουσιας): R0 β0 {b0[0]:+.2f} · β1 {b0[1]:+.2f} ανα 1 τυπ.απ. | ΔΙΟΡΘΩΣΗ β0 {b1[0]:+.2f} · β1 {b1[1]:+.2f}')
# ---- ποσο αλλαζει το PIR των αποντων ----
dp = [(p1['pir'] - p0['pir'], p0, p1) for r0, r1 in zip(rows0, rows1) for p0, p1 in zip(r0['ah'] + r0['aa'], r1['ah'] + r1['aa'])]
big = [x for x in dp if x[0] > 2]
P(f'αποντες με PIR/40 που ανεβαινει >2 μοναδες με τη διορθωση: {len(big)} απο {len(dp)} ({len(big) / len(dp):.0%})')
def cost(p, ns, b):
    g = 1.0 if p['k'] <= 3 else (.5 if p['k'] <= 10 else 0.0)
    return (b[0] + b[1] * (p['pir'] - ns['MU']['pir']) / ns['SD']['pir']) * p['min'] / 40 * g
neg0 = sum(1 for _, p0, _ in dp if cost(p0, A, b0) < 0); neg1 = sum(1 for _, _, p1 in dp if cost(p1, Bn, b1) < 0)
P(f'αποντες με ΑΡΝΗΤΙΚΟ κοστος (η απουσια «βοηθα» την ομαδα): R0 {neg0} ({neg0 / len(dp):.0%}) · ΔΙΟΡΘΩΣΗ {neg1} ({neg1 / len(dp):.0%})')
for lab, mask in (('ΟΛΑ τα ματς', ALL), ('αγωνιστικες 1-10 (γηπεδουχος ≤9 φετινα πριν)', rnd <= 10), ('αγωνιστικες 11+', rnd > 10)):
    P(''); P(f'## {lab}: {int(mask.sum())} ματς — LOSO · RMSE διαφορας (ποντοι) ανα σεζον · picks χαντικαπ ≥8% ανοιγμα (1 μοναδα/pick)')
    d = [rmse(Y - H1, mask & (ys == s)) - rmse(Y - H0, mask & (ys == s)) for s in SE]
    P('  RMSE R0        ' + ' · '.join(f'{s}: {rmse(Y - H0, mask & (ys == s)):.3f}' for s in SE))
    P('  ΔRMSE διορθ.   ' + ' · '.join(f'{s}: {x:+.4f}' for s, x in zip(SE, d)) + f'  (− = καλυτερο· καλυτερο σε {sum(x < 0 for x in d)}/5)')
    for nm, h, rr in (('R0 live', H0, rows0), ('ΔΙΟΡΘΩΣΗ', H1, rows1), ('χωρις απουσιες', np.zeros(len(Y)), rows0)):
        n, u, roi, pos, per = summ(picks(rr, h, mask))
        P(f'  {nm:14s} picks {n:4d} · μοναδες {u:+6.1f} · ROI {roi:+5.1f}% · θετικες {pos}/5 · ' + ' '.join(f'{s[-2:]}:{per[s]:+.1f}' for s in SE))
    if lab == 'ΟΛΑ τα ματς':
        n0, u0, _, _, _ = summ(picks(rows0, H0, ALL)); n1, u1, _, pos1, _ = summ(picks(rows1, H1, ALL)); better = sum(x < 0 for x in d)
        if not (n0 == 626 and abs(u0 - 65.8) < 0.05):
            P(f'!!! R0 ΔΕΝ αναπαραγει το live (626 / +65.8): {n0} / {u0:+.1f} — STOP'); open('el_pir_shrink_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out)); sys.exit(1)
        P('  (R0 αναπαραγει το live: 626 picks / +65.8μ ✓)')
        U0 = picks(rows0, H0, ALL); U1 = picks(rows1, H1, ALL)
        du = np.array([(b_ or 0) - (a_ or 0) for s in SE for a_, b_ in zip(U0[s], U1[s])]); chg = sum(1 for s in SE for a_, b_ in zip(U0[s], U1[s]) if (a_ is None) != (b_ is None) or (a_ is not None and a_ != b_))
        P(f'  ζευγαρωτα: Δμοναδες {du.sum():+.1f} ± {du.std(ddof=1) * math.sqrt(len(du)):.1f} (τυπ. σφαλμα) · ματς με διαφορετικο pick/αποτελεσμα {chg}')
        VER = (better >= 4, u1 >= u0, pos1 >= 4)
P(''); P(f'## ΚΡΙΣΗ (προ-δηλωμενα): RMSE ≥4/5 {"✓" if VER[0] else "✗"} · μοναδες ≥ R0 {"✓" if VER[1] else "✗"} · θετικες ≥4/5 {"✓" if VER[2] else "✗"} → '
  + ('ΠΕΡΝΑ' if all(VER) else 'ΔΕΝ ΠΕΡΝΑ'))
# ---- παραδειγματα: αποντες με τη μεγαλυτερη αλλαγη κοστους ----
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ (κοστος απουσιας σε ποντους διαφορας, συντελεστες ολων των σεζον)')
ex = []
for r0, r1, (sea, hc, ac, ts) in zip(rows0, rows1, keys):
    for side, L0, L1 in (('γηπ ' + hc, r0['ah'], r1['ah']), ('φιλ ' + ac, r0['aa'], r1['aa'])):
        for p0, p1 in zip(L0, L1): ex.append((cost(p1, Bn, b1) - cost(p0, A, b0), sea, hc, ac, ts, side, p0, p1))
ex.sort(key=lambda x: -x[0])
import datetime as dt
for c in ex[:3] + [x for x in ex if x[6]['pir'] > 18][:0]:
    dd, sea, hc, ac, ts, side, p0, p1 = c
    P(f'  {NAME.get(p0["pid"], p0["pid"])} ({side}) · {sea} {hc}-{ac} {dt.datetime.utcfromtimestamp(ts):%Y-%m-%d} · λεπτα {p0["min"]:.1f} · k {p0["k"]}'
      f' · PIR/40 R0 {p0["pir"]:.1f} → κοστος {cost(p0, A, b0):+.2f} π. · ΔΙΟΡΘ. {p1["pir"]:.1f} → {cost(p1, Bn, b1):+.2f} π.')
open('el_pir_shrink_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
