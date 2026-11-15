# -*- coding: utf-8 -*-
"""el_absence_regular_test.py — EUROLEAGUE απουσιες: (α) «ΤΑΚΤΙΚΟΣ» ΜΕ ΠΕΡΣΙΝΑ ΤΗΣ ΙΔΙΑΣ ΟΜΑΔΑΣ · (β) ΛΕΠΤΑ ΧΩΡΙΣ ΤΟ ΜΑΤΣ ΤΟΥ ΤΡΑΥΜΑΤΙΣΜΟΥ
(9/10/2026, Στελιος: «ο Γκος τραυματιστηκε στο 1ο και ειναι σημαντικη απουσια · ο Τζειμς τραυματιστηκε μεσα στο ματς, τα λεπτα του δεν ειναι
αντιπροσωπευτικα · ερχεται διαβολοβδομαδα, να το ψαξουμε»).
LIVE σημερα (R0·M0): ταχτικος = ≥3 απο τα 10 τελευταια ΦΕΤΙΝΑ ματς της ομαδας · λεπτα = μ.ο. 10 τελευταιων που επαιξε · κοστος = c·λεπτα/40·g(k), γ .5.
ΕΚΔΟΧΕΣ:
 R1 ταχτικος = ≥3 απο τα 10 τελευταια ματς Ευρωλιγκας της ομαδας ΜΑΖΙ ΜΕ ΠΕΡΣΙΝΑ (ιδια ομαδα) · ο παικτης πρεπει να ανηκει στο φετινο ρόστερ
    (στο backtest: εμφανιζεται σε ματς της ομαδας φετος — live αυτο το λεει η RotoWire) · k μετραει και πισω στην περσινη σεζον.
 M1 λεπτα χωρις «κομμενα» ματς: απο τα 10 τελευταια βγαινουν οσα < 50% της διαμεσου τους.
 M2 διαμεσος 10 τελευταιων.
 M3 χωρις το ΜΑΤΣ ΤΟΥ ΤΡΑΥΜΑΤΙΣΜΟΥ: αν το τελευταιο ματς πριν την απουσια ειναι < 60% του μ.ο. των αλλων, βγαινει.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση): εκδοχη ΠΕΡΝΑ vs LIVE αν (1) LOSO RMSE καλυτερο σε ≥4/5 σεζον ΚΑΙ (2) μοναδες picks ≥8% ανοιγμα ≥ LIVE.
Αναφορα: ανα ομαδα αγωνιστικων (1-3 / 4-6 / 7-10 / 11-20 / 21+), αποσταση απο κλεισιμο, CLV picks. Ιδια ματς για ολες τις εκδοχες (και αγων. 1-2).
Εξοδος: el_absence_regular_out.txt"""
import sys, io, contextlib, json, pickle, collections, math
import numpy as np, pandas as pd
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D, REC = ns['D'], ns['REC']
NP = pickle.load(open('el_newmodel_preds.pkl', 'rb'))
PL = json.load(open('el_players.json', encoding='utf-8'))
SE = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
Phi = NormalDist().cdf
TG = collections.defaultdict(list)          # (σεζον, ομαδα) → [(ts, {pid: λεπτα})]
for k, g in PL.items():
    if g.get('comp') != 'E' or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        TG[(g['season'], g[tc])].append((ts, {p[0]: (p[3] or 0.0) for p in g[side]}))
for v in TG.values(): v.sort(key=lambda x: x[0])
ROSTER = {key: {p for _, d in L for p, mn in d.items() if mn > 0} for key, L in TG.items()}
PH = collections.defaultdict(list)          # pid → [(ts, λεπτα)] ολες οι ομαδες/σεζον
for L in TG.values():
    for ts, d in L:
        for pid, mn in d.items():
            if mn > 0: PH[pid].append((ts, mn))
for v in PH.values(): v.sort()
def minutes(pid, ts, M):
    h = [mn for t, mn in PH[pid] if t < ts - 3600]
    if not h: return None
    if M == 'M3' and len(h) >= 4:
        rest = h[-10:-1]
        if h[-1] < .6 * np.mean(rest): h = h[:-1]
    x = np.array(h[-10:], float)
    if M == 'M1': x = x[x >= .5 * np.median(x)]
    if M == 'M2': return float(np.median(x))
    return float(x.mean())
def prev_season(s): return f'E{int(s[1:]) - 1}'
def absents(sea, team, ts, R, M):
    cur = TG.get((sea, team), []); today = next((x[1] for x in cur if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    hist = [x for x in cur if x[0] < ts - 3600]
    if R == 'R1': hist = [x for x in TG.get((prev_season(sea), team), [])] + hist
    last10 = hist[-10:]; cnt = collections.Counter(p for _, d in last10 for p, v in d.items() if v > 0)
    res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, 0) > 0: continue
        if R == 'R1' and pid not in ROSTER.get((sea, team), set()): continue      # εφυγε απο την ομαδα
        k = 0
        for _, d in reversed(hist):
            if d.get(pid, 0) > 0: break
            k += 1
        mn = minutes(pid, ts, M)
        if mn is None or mn < 10: continue
        res.append((mn, k + 1))
    return res
VARS = [('R0', 'M0'), ('R1', 'M0'), ('R0', 'M1'), ('R0', 'M2'), ('R0', 'M3'), ('R1', 'M1'), ('R1', 'M3')]
rows = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); A = {}
    for v in VARS:
        ah, aa = absents(sea, hc, ts, *v), absents(sea, ac, ts, *v)
        if ah is None or aa is None: break
        A[v] = (ah, aa)
    if len(A) < len(VARS): continue
    rnd = 1 + sum(1 for x in TG[(sea, hc)] if x[0] < ts - 3600)
    rows.append(dict(y=sea, rnd=rnd, act=float(D.hs.values[pos] - D.as_.values[pos]), m=float(NP[key]['h_new']), mo=d_['open'][1], mc=d_[0][1], op=d_['open'][2:], A=A))
Y = np.array([r['act'] - r['m'] for r in rows]); ys = np.array([r['y'] for r in rows]); rn = np.array([r['rnd'] for r in rows])
act = np.array([r['act'] for r in rows]); m0 = np.array([r['m'] for r in rows]); mo = np.array([r['mo'] for r in rows]); mc = np.array([r['mc'] for r in rows])
P(f'ματς E2021-25 (ολες οι αγωνιστικες) με προβλεψη, αγορα & παικτες: {len(rows)}')
def X_(v):
    x = np.zeros(len(rows))
    for i, r in enumerate(rows):
        ah, aa = r['A'][v]
        for lst, s in ((aa, 1), (ah, -1)):
            for mn, k in lst: x[i] += s * mn / 40 * (1.0 if k <= 3 else (.5 if k <= 10 else 0.0))
    return x
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
HELD, COEF = {}, {}
for v in VARS:
    x = X_(v); h = np.zeros(len(Y))
    for Yr in SE:
        tr = ys != Yr; b = (x[tr] @ Y[tr]) / (x[tr] @ x[tr] + 1.0); h[ys == Yr] = b * x[ys == Yr]
    HELD[v] = h; COEF[v] = (x @ Y) / (x @ x + 1.0)
    na = sum(1 for r in rows for side in r['A'][v] for p in side if p[1] <= 10)
    P(f"  {v[0]}·{v[1]}: συντελεστης {COEF[v]:.3f} π. ανα 40′ · απουσιες (k≤10) {na} · ματς με διορθωση {int(np.sum(x != 0))}")
def units(adj, msk):
    U = collections.defaultdict(list); mv = []
    for r, a, ok in zip(rows, adj, msk):
        if not ok: continue
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08:
            x = (r['act'] + L) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1)); mv.append((r['mc'] - r['mo']) * sd)
    u = [x for v in U.values() for x in v]
    return u, U, mv
ALL = np.ones(len(Y), bool)
BASE = HELD[('R0', 'M0')]
P(''); P('## ΣΥΓΚΡΙΣΗ (LOSO) — ολες οι εκδοχες στα ιδια ματς · Δ = καλυτερα αν − (RMSE) / + (μοναδες)')
u0, _, _ = units(np.zeros(len(Y)), ALL)
P(f'  χωρις απουσιες: RMSE {rmse(Y, ALL):.3f} · picks {len(u0)} · {sum(u0):+.1f}μ · ROI {np.mean(u0)*100:+.1f}%')
for v in VARS:
    h = HELD[v]; u, U, mv = units(h, ALL)
    dpr = [rmse(Y - h, ys == s) - rmse(Y - BASE, ys == s) for s in SE]
    dnone = [rmse(Y - h, ys == s) - rmse(Y, ys == s) for s in SE]
    ub, _, _ = units(BASE, ALL)
    lab = f'{v[0]}·{v[1]}'
    verdict = '' if v == ('R0', 'M0') else (' <- ΠΕΡΝΑ' if sum(d < 0 for d in dpr) >= 4 and sum(u) >= sum(ub) else ' ✗')
    P(f'  {lab}: RMSE {rmse(Y - h, ALL):.3f} (vs χωρις {sum(d < 0 for d in dnone)}/5 · vs LIVE ' + ' '.join(f'{d:+.3f}' for d in dpr) + f' → {sum(d < 0 for d in dpr)}/5)'
      + f' · picks {len(u)} {sum(u):+.1f}μ ROI {np.mean(u)*100:+.1f}% (θετ {sum(1 for s in SE if U[s] and np.mean(U[s]) > 0)}/5) · αποστ. κλεισ. {rmse(mc - m0 - h, ALL):.3f} · CLV {np.mean(mv):+.2f}' + verdict)
P(''); P('## ΑΝΑ ΑΓΩΝΙΣΤΙΚΕΣ: μοναδες picks (και RMSE vs LIVE, − = καλυτερα)')
BL = [(1, 3), (4, 6), (7, 10), (11, 20), (21, 40)]
P('  εκδοχη    ' + ' | '.join(f'αγων {a}-{b}' if b < 40 else f'αγων {a}+' for a, b in BL))
P('  χωρις     ' + ' | '.join(f'{sum(units(np.zeros(len(Y)), (rn >= a) & (rn <= b))[0]):+6.1f}μ ({len(units(np.zeros(len(Y)), (rn >= a) & (rn <= b))[0])})' for a, b in BL))
for v in VARS:
    h = HELD[v]; cells = []
    for a, b in BL:
        msk = (rn >= a) & (rn <= b); u = units(h, msk)[0]
        cells.append(f'{sum(u):+6.1f}μ ({len(u)}) {rmse(Y - h, msk) - rmse(Y - BASE, msk):+.3f}')
    P(f'  {v[0]}·{v[1]}     ' + ' | '.join(cells))
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ (σημερα, συντελεστης ολων των σεζον)')
for nm, mins in (('Mike James (M0)', [25.4, 28.6, 38.2, 31.4, 32.1, 18.3, 36.5, 31.8, 31.3, 22.5]), ('Mike James (M3 χωρις 22.5′)', [26.5, 25.4, 28.6, 38.2, 31.4, 32.1, 18.3, 36.5, 31.8, 31.3]),
                 ('Williams-Goss', [28.9, 27.3, 24.0, 27.4, 22.2, 30.9, 24.0, 33.0, 32.6, 25.3])):
    for v in (('R0', 'M0'), ('R1', 'M0'), ('R0', 'M3'), ('R1', 'M3')):
        if ('M3' in nm) != (v[1] == 'M3') and 'James' in nm: continue
        P(f'  {nm:28s} {v[0]}·{v[1]}: {np.mean(mins):.1f}′ × {COEF[v]:.3f} / 40 = {np.mean(mins) / 40 * COEF[v]:.2f} π.')
open('el_absence_regular_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
