# -*- coding: utf-8 -*-
"""el_absence_return_test.py — EUROLEAGUE: ΕΠΙΣΤΡΟΦΕΣ ΩΣ ΠΟΣΟΣΤΟ ΤΗΣ ΑΞΙΑΣ (22/10/2026, Στελιος «οκ τρεξε και αυτο το τεστ»).
Συνεχεια του el_absence_v2_test (V1 = λεπτα + PIR). Εκει το «μειον επιστροφης» ηταν ΙΔΙΟ για ολους (μονο λεπτα) → παραλογο για ρολιστες
(επιστροφη −1 ενω η απουσια ≈0). Εδω η επιστροφη (1ο ματς που ξαναπαιζει) επιτρεπεται να εξαρταται απο την ΑΞΙΑ του παικτη.
ΕΚΔΟΧΕΣ (ολες = V1 για τις απουσιες + ...):
  R0 χωρις επιστροφες (V1)
  R1 σταθερο μειον (λεπτα, 1-3 / 4+) — το προηγουμενο
  R2 ΑΝΑΛΟΓΙΚΟ: επιστροφη = −φ × (κοστος απουσιας V1 του ιδιου παικτη)· φ = ποσοστο της αξιας που ΔΕΝ αποδιδει στο 1ο ματς (ενα φ, ή φ 1-3 / φ 4+)
  R3 = R1 + ελεγχος «βαρια περιοδος»: φορτιο απουσιων της ομαδας στο ΠΡΟΗΓΟΥΜΕΝΟ ματς (Σ λεπτα/40 αποντων) — αν το μειον εξαφανιζεται, ηταν η περιοδος
ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο): μια εκδοχη επιστροφων ΜΠΑΙΝΕΙ αν, LOSO 5 σεζον: RMSE καλυτερο απο R0 σε ≥4/5 ΚΑΙ μοναδες picks ≥8% ≥ R0
  ΚΑΙ θετικες σεζον ≥4/5 ΚΑΙ ΛΟΓΙΚΗ: για παικτη μεσης αξιας η επιστροφη ΔΕΝ ειναι χειροτερη απο την απουσια (0 ≤ φ ≤ 1 στο R2).
Εξοδος: el_absence_return_test_out.txt"""
import sys, io, contextlib, collections
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_v2_test.py', encoding='utf-8').read().split("P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
rows, TG, value, MU, SD, SE, keys, picks, cell = (ns[k] for k in ('rows', 'TG', 'value', 'MU', 'SD', 'SE', 'keys', 'picks', 'cell'))
pd = ns['pd']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# επιστροφες με ΑΞΙΑ (PIR) + φορτιο απουσιων στο προηγουμενο ματς
def returns_v(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None or len(prev) < 3: return [], 0.0
    res = []
    for pid, v in today.items():
        if v[0] <= 0: continue
        k = 0
        for _, _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        if k == 0 or k >= len(prev): continue
        before = prev[:len(prev) - k][-10:]
        if sum(1 for _, _, d in before if d.get(pid, (0,))[0] > 0) < 3: continue
        mins = [d[pid][0] for _, _, d in before if d.get(pid, (0,))[0] > 0][-10:]
        if np.mean(mins) < 10: continue
        vv = value(pid, ts); z = 0.0 if not vv else (vv['pir'] - MU['pir']) / SD['pir']
        res.append(dict(k=k, min=float(np.mean(mins)), z=z))
    # φορτιο απουσιων στο προηγουμενο ματς: τακτικοι (≥3/10 πριν) που ΔΕΝ επαιξαν εκει
    last = prev[-1][2]; before10 = prev[-11:-1]
    cnt = collections.Counter(p for _, _, d in before10 for p, v in d.items() if v[0] > 0)
    load = 0.0
    for pid, c in cnt.items():
        if c >= 3 and last.get(pid, (0,))[0] <= 0:
            mm = [d[pid][0] for _, _, d in before10 if d.get(pid, (0,))[0] > 0]
            if mm and np.mean(mm) >= 10: load += np.mean(mm) / 40
    return res, load
for r, (sea, hc, ac, ts) in zip(rows, keys):
    r['rvh'], r['lh'] = returns_v(sea, hc, ts); r['rva'], r['la'] = returns_v(sea, ac, ts)
# στηλες: 0 λεπτα, 1 λεπτα·zPIR (απουσιες) · 2 επιστρ 1-3 λεπτα · 3 επιστρ 4+ λεπτα · 4 επιστρ 1-3 λεπτα·z · 5 επιστρ 4+ λεπτα·z · 6 φορτιο προηγ.
def feats(r):
    x = np.zeros(7)
    for lst, s in ((r['aa'], 1), (r['ah'], -1)):
        for p in lst:
            g = 1.0 if p['k'] <= 3 else (.5 if p['k'] <= 10 else 0.0); w = p['min'] / 40 * g * s
            x[0] += w; x[1] += w * (p['pir'] - MU['pir']) / SD['pir']
    for lst, s in ((r['rvh'], 1), (r['rva'], -1)):
        for p in lst:
            w = p['min'] / 40 * s; j = 0 if p['k'] <= 3 else 1
            x[2 + j] += w; x[4 + j] += w * p['z']
    x[6] = r['lh'] - r['la']
    return x
XF = np.array([feats(r) for r in rows]); Y = np.array([r['act'] - r['m'] for r in rows]); ys = np.array([r['y'] for r in rows])
rmse = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2)))
def fit_lin(cols, tr):
    X = XF[:, cols]; m = np.isin(ys, tr); b = np.linalg.solve(X[m].T @ X[m] + 1.0 * np.eye(len(cols)), X[m].T @ Y[m]); return b, X @ b
def fit_phi(tr, split):
    """R2: απουσιες V1 (β0, β1) + επιστροφη = −φ·(β0 + β1·z)·λεπτα/40. Εναλλαγη: β απο V1+φ, φ με OLS — 30 επαναληψεις."""
    m = np.isin(ys, tr); b = fit_lin([0, 1], tr)[0]; phi = np.zeros(2)
    for _ in range(30):
        r1 = (XF[:, 2] * b[0] + XF[:, 4] * b[1]); r4 = (XF[:, 3] * b[0] + XF[:, 5] * b[1])
        R = np.c_[r1, r4] if split else np.c_[r1 + r4]
        res = Y - XF[:, [0, 1]] @ b
        ph = np.linalg.lstsq(-R[m], res[m], rcond=None)[0]; phi = np.r_[ph, ph] if not split else ph
        Yb = Y + phi[0] * r1 + phi[1] * r4
        Xb = XF[:, [0, 1]]; b = np.linalg.solve(Xb[m].T @ Xb[m] + np.eye(2), Xb[m].T @ Yb[m])
    pred = XF[:, [0, 1]] @ b - phi[0] * (XF[:, 2] * b[0] + XF[:, 4] * b[1]) - phi[1] * (XF[:, 3] * b[0] + XF[:, 5] * b[1])
    return (b, phi), pred
VAR = {'R0 χωρις επιστροφες (V1)': ('lin', [0, 1]), 'R1 σταθερο μειον': ('lin', [0, 1, 2, 3]),
       'R2 αναλογικο (ενα φ)': ('phi', False), 'R2β αναλογικο (φ 1-3 / 4+)': ('phi', True),
       'R3 = R1 + βαρια περιοδος': ('lin', [0, 1, 2, 3, 6]), 'R4 βαρια περιοδος μονο': ('lin', [0, 1, 6])}
P(f'ματς {len(rows)} · επιστροφες {sum(len(r["rvh"]) + len(r["rva"]) for r in rows)}')
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ (ολα τα δεδομενα)')
for nm, (kind, arg) in VAR.items():
    if kind == 'lin':
        b, _ = fit_lin(arg, SE); names = ['λεπτα', 'λεπτα·PIR', 'επιστρ 1-3', 'επιστρ 4+', '', '', 'φορτιο προηγ. ματς']
        P(f'  {nm:28s} ' + ' · '.join(f'{names[c]} {v:+.2f}' for c, v in zip(arg, b)))
    else:
        (b, phi), _ = fit_phi(SE, arg); P(f'  {nm:28s} λεπτα {b[0]:+.2f} · λεπτα·PIR {b[1]:+.2f} · φ 1-3 {phi[0]:+.2f} · φ 4+ {phi[1]:+.2f}  (φ = ποσοστο αξιας που ΧΑΝΕΤΑΙ στο 1ο ματς)')
P(''); P('## LOSO: RMSE vs R0 (− = καλυτερο) · picks χαντικαπ ≥8% ανοιγμα')
HELD = {}; PHI = {}
for nm, (kind, arg) in VAR.items():
    h = np.zeros(len(Y)); ph = []
    for s in SE:
        tr = [x for x in SE if x != s]
        if kind == 'lin': _, pr = fit_lin(arg, tr)
        else: (bb, phi), pr = fit_phi(tr, arg); ph.append(phi)
        h[ys == s] = pr[ys == s]
    HELD[nm] = h; PHI[nm] = ph
U0 = picks(HELD['R0 χωρις επιστροφες (V1)'])
for nm, h in HELD.items():
    d = [rmse(Y - h, ys == s) - rmse(Y - HELD['R0 χωρις επιστροφες (V1)'], ys == s) for s in SE]; U = picks(h)
    u, u0 = sum(x for v in U.values() for x in v), sum(x for v in U0.values() for x in v)
    logic = True
    if PHI[nm]: logic = all(0 <= p <= 1 for ph in PHI[nm] for p in ph)
    ok = not nm.startswith('R0') and sum(x < 0 for x in d) >= 4 and u >= u0 and sum(1 for s in SE if U[s] and sum(U[s]) > 0) >= 4 and logic
    P(f'  {nm:28s} RMSE {" ".join(f"{x:+.3f}" for x in d)} ({sum(x < 0 for x in d)}/5) | {cell(U)}' +
      (f' · φ ανα LOSO {[tuple(round(float(p), 2) for p in ph) for ph in PHI[nm]]}' if PHI[nm] else '') + ('' if nm.startswith('R0') else ('  → ΠΕΡΝΑ' if ok else '  ✗')))
P(f'  (live σημερα, μονο λεπτα V0, ιδια ματς: {cell(picks(ns["HELD"]["V0 LIVE (λεπτα)"]))})' if 'HELD' in ns else '')
open('el_absence_return_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
