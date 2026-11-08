# -*- coding: utf-8 -*-
"""el_absence_v2_test.py — EUROLEAGUE ΑΠΟΥΣΙΕΣ v2 + ΕΠΙΣΤΡΟΦΕΣ (21/10/2026, Στελιος «οκ ξεκινα» — μετα τα ευρηματα NBA).
Βαση: el_player_absence_value.py (ιδια ματς E2021-25, live προβλεψεις el_newmodel_preds, Crown, αποντες απο τα box scores = πληρης γνωση).
ΕΚΔΟΧΕΣ κοστους παικτη (λεπτα/40 × g(k), g: k 1-3 → 1 · 4-10 → .5 · >10 → 0, οπως το live):
  V0 LIVE      : β0 (μονο λεπτα)
  V1 +PIR      : β0 + β1·zPIR/40   (ΕΝΑΣ δεικτης αξιας — το παλιο «3 δεικτες» ηταν ασταθες 3/5)
  V2 +3        : β0 + β1·zPIR + β2·z(+/-) + β3·zποντοι (το παλιο, για συγκριση)
  R  ΕΠΙΣΤΡΟΦΕΣ: + ρ1·Σ λεπτα/40 παικτων που ΓΥΡΙΖΟΥΝ σημερα μετα απο 1-3 χαμενα ματς + ρ2·(4+ χαμενα) (τακτικοι πριν την απουσια)
       (NBA t49: οι επιστροφες αξιζαν ~1/4 της αξιας τους· στο live EL δεν μετρανε καθολου)
ΠΡΟ-ΔΗΛΩΜΕΝΑ (γραφτηκαν πριν το τρεξιμο) — μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ το V0 αν, LOSO 5 σεζον:
  RMSE καλυτερο απο V0 σε ≥4/5 ΚΑΙ picks χαντικαπ ≥8% ανοιγμα: μοναδες ≥ V0 ΚΑΙ θετικες σεζον ≥4/5.
  Περιγραφικα: συντελεστες, Φουρνιε & αλλοι κορυφαιοι (κοστος V0 vs V1), ποσο κινειται η αγορα.
Εξοδος: el_absence_v2_test_out.txt"""
import sys, io, contextlib, collections
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_player_absence_value.py', encoding='utf-8').read().split("Y = np.array([r['act'] - r['m'] for r in rows])")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
rows, TG, PH, NAME, value, MU, SD, SE, D, REC, NP = (ns[k] for k in ('rows', 'TG', 'PH', 'NAME', 'value', 'MU', 'SD', 'SE', 'D', 'REC', 'NP'))
pd = ns['pd']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- επιστροφες: παιζει σημερα, ελειπε τα αμεσως προηγουμενα k ματς, ηταν τακτικος (≥3 απο τα 10 πριν την απουσια) ----
def returns(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None or len(prev) < 3: return []
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
        res.append(dict(k=k, min=float(np.mean(mins))))
    return res
# αντιστοιχιση rows → (σεζον, γηπ, φιλ, ts) για τις επιστροφες (ιδια σειρα με το el_player_absence_value)
keys = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    ts = t.timestamp()
    if ns['absents'](sea, hc, ts) is None or ns['absents'](sea, ac, ts) is None: continue
    keys.append((sea, hc, ac, ts))
assert len(keys) == len(rows)
for r, (sea, hc, ac, ts) in zip(rows, keys):
    r['rh'], r['ra'] = returns(sea, hc, ts), returns(sea, ac, ts)
P(f'ματς {len(rows)} · αποντες {sum(len(r["ah"]) + len(r["aa"]) for r in rows)} · επιστροφες {sum(len(r["rh"]) + len(r["ra"]) for r in rows)} '
  f'(1-3 χαμενα {sum(1 for r in rows for p in r["rh"] + r["ra"] if p["k"] <= 3)} · 4+ {sum(1 for r in rows for p in r["rh"] + r["ra"] if p["k"] > 3)})')
COLS = ['λεπτα', 'PIR', '+/-', 'ποντοι', 'επιστρ 1-3', 'επιστρ 4+']
def feats(r):
    x = np.zeros(6)
    for lst, s in ((r['aa'], 1), (r['ah'], -1)):                 # απων φιλοξ → καλο για γηπ (+)
        for p in lst:
            g = 1.0 if p['k'] <= 3 else (.5 if p['k'] <= 10 else 0.0); w = p['min'] / 40 * g * s
            x[:4] += w * np.array([1.0, (p['pir'] - MU['pir']) / SD['pir'], (p['pm'] - MU['pm']) / SD['pm'], (p['pts'] - MU['pts']) / SD['pts']])
    for lst, s in ((r['rh'], 1), (r['ra'], -1)):                 # επιστροφη γηπ → καλο για γηπ (+)
        for p in lst: x[4 if p['k'] <= 3 else 5] += p['min'] / 40 * s
    return x
XF = np.array([feats(r) for r in rows]); Y = np.array([r['act'] - r['m'] for r in rows]); ys = np.array([r['y'] for r in rows])
VAR = {'V0 LIVE (λεπτα)': [0], 'V1 +PIR': [0, 1], 'V2 +3 δεικτες': [0, 1, 2, 3], 'V0 + επιστροφες': [0, 4, 5], 'V1 + επιστροφες': [0, 1, 4, 5]}
def fit(cols, tr):
    X = XF[:, cols]; m = np.isin(ys, tr); b = np.linalg.solve(X[m].T @ X[m] + 1.0 * np.eye(len(cols)), X[m].T @ Y[m]); return b, X @ b
rmse = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2)))
from statistics import NormalDist
Phi = NormalDist().cdf
def picks(adj):
    U = collections.defaultdict(list)
    for r, a in zip(rows, adj):
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08: x = (r['act'] + L) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1))
    return U
def cell(U):
    u = [x for v in U.values() for x in v]
    return f"{np.mean(u) * 100:+5.1f}% ({len(u)}, {sum(u):+6.1f}μ, θετ {sum(1 for s in SE if U[s] and sum(U[s]) > 0)}/5) · " + ' '.join(f"{s[-2:]}:{sum(U[s]):+.1f}" for s in SE)
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ (ολα τα δεδομενα) — ποντοι ανα 40′ (αξια: ανα 1 τυπ. αποκλιση)')
for nm, cols in VAR.items():
    b, _ = fit(cols, SE); P(f'  {nm:18s} ' + ' · '.join(f'{COLS[c]} {v:+.2f}' for c, v in zip(cols, b)))
P(''); P('## LOSO: RMSE (− = καλυτερο απο V0) και picks χαντικαπ ≥8% στο ανοιγμα')
HELD = {}
for nm, cols in VAR.items():
    h = np.zeros(len(Y))
    for s in SE:
        b, pr = fit(cols, [x for x in SE if x != s]); h[ys == s] = pr[ys == s]
    HELD[nm] = h
U0 = picks(HELD['V0 LIVE (λεπτα)'])
for nm, h in HELD.items():
    d = [rmse(Y - h, ys == s) - rmse(Y - HELD['V0 LIVE (λεπτα)'], ys == s) for s in SE]; U = picks(h)
    u, u0 = sum(x for v in U.values() for x in v), sum(x for v in U0.values() for x in v)
    ok = nm != 'V0 LIVE (λεπτα)' and sum(x < 0 for x in d) >= 4 and u >= u0 and sum(1 for s in SE if U[s] and sum(U[s]) > 0) >= 4
    P(f'  {nm:18s} RMSE {" ".join(f"{x:+.3f}" for x in d)} ({sum(x < 0 for x in d)}/5) | {cell(U)}' + ('  → ΠΕΡΝΑ' if ok else ('' if nm.startswith('V0 LIVE') else '  ✗')))
P(f'  (χωρις καμια διορθωση απουσιων: {cell(picks(np.zeros(len(Y))))})')
# ---- παραδειγματα ----
P(''); P('## ΚΟΣΤΟΣ ΑΠΟΥΣΙΑΣ ΠΑΙΚΤΩΝ (ολα τα δεδομενα, ματς 1-3 της απουσιας): V0 live vs V1 +PIR')
b0, _ = fit([0], SE); b1, _ = fit([0, 1], SE)
now = pd.Timestamp('2026-10-21').timestamp()
cands = collections.Counter()
for pid, h in PH.items():
    if h and h[-1][0] > pd.Timestamp('2026-03-01').timestamp(): cands[pid] = sum(x[1] for x in h[-12:])
show = [p for p in PH if 'FOURNIER' in NAME.get(p, '')] + [p for p, _ in cands.most_common(14)]
seen = set()
for pid in show:
    if pid in seen: continue
    seen.add(pid); v = value(pid, now)
    if not v: continue
    z = (v['pir'] - MU['pir']) / SD['pir']
    P(f'  {NAME.get(pid, pid)[:24]:24s} λεπτα {v["min"]:4.1f} · PIR/40 {v["pir"]:5.1f} → V0 {v["min"] / 40 * b0[0]:+.2f} · V1 {v["min"] / 40 * (b1[0] + b1[1] * z):+.2f} π.')
open('el_absence_v2_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
