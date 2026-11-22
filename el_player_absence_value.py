# -*- coding: utf-8 -*-
"""el_player_absence_value.py — EUROLEAGUE: ΠΟΣΟ ΚΟΣΤΙΖΕΙ ΜΙΑ ΑΠΟΥΣΙΑ (9/10/2026, Στελιος: «ο Mike James θα λειπει πολυ — δεν ξερουμε ποσο να
διορθωσουμε χειροκινητα, θελει τεστ, ξεκινα»).
Ιδεα: το live μοντελο ΔΕΝ ξερει τις απουσιες → το λαθος του (πραγμ − προβλ) εξηγειται απο το ποιοι ελειπαν. Μαθαινουμε «ποσους ποντους κοστιζει» ενας
απων με βαση την αξια του (απο τα ματς ΠΡΙΝ): κοστος_παικτη = (λεπτα/40) × (β0 + β1·PIR/40 + β2·(+/-)/40 + β3·ποντοι/40) [τυποποιημενα] × g(k),
k = ποσα ματς λειπει ηδη (το μοντελο «μαθαινει» σιγα σιγα): g = 1 για k 1-3 · γ για k 4-10 (γ πλεγμα).
ΑΠΩΝ = εχει παιξει ≥3 απο τα 10 τελευταια ματς της ομαδας στη σεζον (και ≥10′ μεσο ορο) και ΔΕΝ παιζει σημερα (k = συνεχομενα ματς εκτος).
Δεδομενα: el_players.json (επισημο API 2017-26, λεπτα/ποντοι/PIR/+-) · προβλεψεις el_newmodel_preds (live, E2021-25) · αγορα Crown (el_line_timing).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση), LOSO 5 σεζον (εκτιμηση στις 4, ελεγχος στην 5η):
 Κ1 η διορθωση (μοντελο + κοστος φιλ − κοστος γηπ) ΠΕΡΝΑ αν RMSE καλυτερο σε ≥4/5 σεζον.
 Κ2 η ΑΞΙΑ (PIR, +/-, ποντοι) ΠΕΡΝΑ αν ειναι καλυτερη απο «μονο λεπτα» (β1..3 = 0) σε ≥4/5 σεζον.
 Αναφορα: ποσο τιμολογει η αγορα (κινηση ανοιγματος/κλεισιματος vs προβλεπομενο κοστος) · παραδειγμα Mike James. Εξοδος: el_player_absence_value_out.txt"""
import sys, io, contextlib, json, pickle, collections, math
import numpy as np, pandas as pd
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
# ---- ματς ανα ομαδα-σεζον με παικτες ----
TG = collections.defaultdict(list)          # (σεζον, ομαδα) → [(ts, key, {pid: (min, pts, pir, pm)})]
NAME = {}
for k, g in PL.items():
    if g.get('comp') != 'E' or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        d = {}
        for p in g[side]:
            NAME[p[0]] = p[1]; d[p[0]] = (p[3] or 0.0, p[4] or 0, p[18] or 0, p[19] or 0)
        TG[(g['season'], g[tc])].append((ts, k, d))
for v in TG.values(): v.sort(key=lambda x: x[0])
# ---- ιστορικο παικτη (ολες οι σεζον, ως το ματς) για αξια ----
PH = collections.defaultdict(list)          # pid → [(ts, min, pts, pir, pm)]
for (sea, t), L in TG.items():
    for ts, k, d in L:
        for pid, (mn, pts, pir, pm) in d.items():
            if mn > 0: PH[pid].append((ts, mn, pts, pir, pm))
for v in PH.values(): v.sort()
PRIOR_MIN = 200.0
def value(pid, ts):
    h = [x for x in PH[pid] if x[0] < ts - 3600][-60:]
    if not h: return None
    a = np.array([x[1:] for x in h], float); mins = a[:, 0].sum()
    per40 = a[:, 1:].sum(0) / (mins + PRIOR_MIN) * 40          # μαζεμα προς 0 (ποντοι/PIR/+- ανα 40)
    return dict(min=float(a[-10:, 0].mean()), pts=per40[0], pir=per40[1], pm=per40[2])
def absents(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None or len(prev) < 2: return None
    last10 = prev[-10:]; cnt = collections.Counter(p for _, _, d in last10 for p, v in d.items() if v[0] > 0)
    res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, (0,))[0] > 0: continue
        k = 0
        for _, _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = value(pid, ts)
        if v is None or v['min'] < 10: continue
        res.append(dict(pid=pid, k=k + 1, **v))
    return res
rows = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); ah, aa = absents(sea, hc, ts), absents(sea, ac, ts)
    if ah is None or aa is None: continue
    rows.append(dict(y=sea, act=float(D.hs.values[pos] - D.as_.values[pos]), m=float(NP[key]['h_new']), mo=d_['open'][1], mc=d_[0][1], ah=ah, aa=aa, op=d_['open'][2:]))
P(f'ματς E2021-25 με προβλεψη, αγορα & παικτες: {len(rows)} · ματς με τουλαχιστον 1 απων: {sum(1 for r in rows if r["ah"] or r["aa"])}')
allp = [p for r in rows for p in r['ah'] + r['aa']]
MU = {f: np.mean([p[f] for p in allp]) for f in ('pir', 'pm', 'pts')}; SD = {f: np.std([p[f] for p in allp]) for f in ('pir', 'pm', 'pts')}
P(f'απουσες παικτες: {len(allp)} · k 1-3: {sum(p["k"] <= 3 for p in allp)} · k 4-10: {sum(3 < p["k"] <= 10 for p in allp)} · k >10: {sum(p["k"] > 10 for p in allp)}')
def feats(r, gam, use):
    """→ διανυσμα [κοστος φιλ − κοστος γηπ] ανα συντελεστη (β0, β1, β2, β3)"""
    x = np.zeros(4)
    for lst, s in ((r['aa'], 1), (r['ah'], -1)):
        for p in lst:
            g = 1.0 if p['k'] <= 3 else (gam if p['k'] <= 10 else 0.0)
            w = p['min'] / 40 * g * s
            z = [1.0, (p['pir'] - MU['pir']) / SD['pir'], (p['pm'] - MU['pm']) / SD['pm'], (p['pts'] - MU['pts']) / SD['pts']]
            x += w * np.array(z) * use
    return x
Y = np.array([r['act'] - r['m'] for r in rows]); ys = np.array([r['y'] for r in rows])
def fit(gam, use, tr):
    X = np.array([feats(r, gam, use) for r in rows]); m = np.isin(ys, tr)
    A = X[m].T @ X[m] + 1.0 * np.eye(4); b = np.linalg.solve(A, X[m].T @ Y[m]); return b, X
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
P(''); P('## ΟΛΑ ΤΑ ΔΕΔΟΜΕΝΑ (για να δουμε τα μεγεθη)')
for gam in (0.0, .5, 1.0):
    for nm, use in (('μονο λεπτα', np.array([1, 0, 0, 0])), ('λεπτα + αξια', np.array([1, 1, 1, 1]))):
        b, X = fit(gam, use, SE)
        P(f'  γ {gam:<3} {nm:13s}: β0 {b[0]:+.2f} · PIR {b[1]:+.2f} · +/- {b[2]:+.2f} · ποντοι {b[3]:+.2f} (ποντοι ανα 40′ απουσιας, ανα 1 τυπ. αποκλιση) · RMSE {rmse(Y, np.ones(len(Y), bool)):.3f} → {rmse(Y - X @ b, np.ones(len(Y), bool)):.3f}')
P(''); P('## LOSO (εκτιμηση 4 σεζον → ελεγχος στην 5η)')
res = {}
for gam in (0.0, .5, 1.0):
    for nm, use in (('μονο λεπτα', np.array([1, 0, 0, 0])), ('λεπτα + αξια', np.array([1, 1, 1, 1]))):
        held = np.zeros(len(Y))
        for Yr in SE:
            b, X = fit(gam, use, [s for s in SE if s != Yr]); m = ys == Yr; held[m] = (X @ b)[m]
        res[(gam, nm)] = held
        d = [rmse(Y - held, ys == s) - rmse(Y, ys == s) for s in SE]
        P(f'  γ {gam:<3} {nm:13s}: ' + ' '.join(f'{x:+.3f}' for x in d) + f' → καλυτερα {sum(x < 0 for x in d)}/5' + ('  <- Κ1 ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 4 else '  ✗'))
for gam in (0.0, .5, 1.0):
    a, b_ = res[(gam, 'λεπτα + αξια')], res[(gam, 'μονο λεπτα')]
    d = [rmse(Y - a, ys == s) - rmse(Y - b_, ys == s) for s in SE]
    P(f'  Κ2 γ {gam}: αξια vs μονο λεπτα ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 4 else '  ✗'))
# ---- picks (live κανονας ≥8%, σ 11.5, ανοιγμα): βαση vs με διορθωση απουσιων (LOSO) ----
from statistics import NormalDist
Phi = NormalDist().cdf
def roi(adj):
    U = collections.defaultdict(list)
    for r, a in zip(rows, adj):
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08: x = (r['act'] + L) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1))
    u = [x for v in U.values() for x in v]
    return f"{np.mean(u)*100:+.1f}% ({len(u)}, {sum(u):+.1f}μ, θετ {sum(1 for s_ in SE if U[s_] and np.mean(U[s_]) > 0)}/5) · " + ' '.join(f"{s_[-2:]}:{sum(U[s_]):+.1f}" for s_ in SE)
P(''); P('## PICKS χαντικαπ ≥8% ανοιγμα: βαση vs μοντελο + κοστος απουσιων (LOSO)')
P('  βαση (σημερα)            ' + roi(np.zeros(len(rows))))
for key_ in [(0.0, 'λεπτα + αξια'), (0.5, 'λεπτα + αξια'), (0.5, 'μονο λεπτα')]:
    P(f'  + απουσιες γ {key_[0]} {key_[1]:13s} ' + roi(res[key_]))
# ---- αγορα: ποσο τιμολογει (κινηση απο το μοντελο) ----
P(''); P('## ΑΓΟΡΑ: ποσο απο το προβλεπομενο κοστος «περιεχει» η γραμμη (κλιση (αγορα − μοντελο) πανω στο κοστος· 1 = ολο, 0 = τιποτα)')
b, X = fit(.5, np.array([1, 1, 1, 1]), SE); cost = X @ b
for nm, col in (('ανοιγμα', 'mo'), ('κλεισιμο', 'mc')):
    z = np.array([r[col] - r['m'] for r in rows]); kk = np.polyfit(cost, z, 1)[0]
    zz = np.array([r['act'] - r[col] for r in rows]); kr = np.polyfit(cost, zz, 1)[0]
    P(f'  {nm}: η αγορα μετακινειται {kk:.2f} × κοστος · υπολοιπο (πραγμ − αγορα) {kr:+.2f} × κοστος (0 = σωστα, + = την υποτιμα, − = υπερβαλλει)')
# ---- Mike James ----
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ (αξια απο ολα τα ματς ως σημερα, γ .5, λεπτα + αξια, εκτιμηση σε ολες τις σεζον)')
cands = collections.Counter()
for pid, h in PH.items():
    if h and h[-1][0] > pd.Timestamp('2025-09-01').timestamp(): cands[pid] = sum(x[1] for x in h[-40:])
now = pd.Timestamp('2026-10-09').timestamp()
for pid in [p for p in PH if 'JAMES, MIKE' in NAME.get(p, '')] + [p for p, _ in cands.most_common(8)]:
    v = value(pid, now)
    if not v: continue
    z = [1.0, (v['pir'] - MU['pir']) / SD['pir'], (v['pm'] - MU['pm']) / SD['pm'], (v['pts'] - MU['pts']) / SD['pts']]
    c = v['min'] / 40 * float(np.dot(b, z))
    P(f'  {NAME.get(pid, pid)[:24]:24s} λεπτα {v["min"]:.0f} · PIR/40 {v["pir"]:.1f} · +/-/40 {v["pm"]:+.1f} · ποντοι/40 {v["pts"]:.1f} → ΚΟΣΤΟΣ ΑΠΟΥΣΙΑΣ ~{c:+.1f} π. (ματς 1-3)')
open('el_player_absence_value_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
