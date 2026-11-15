# -*- coding: utf-8 -*-
"""el_absence_totals_test.py — EUROLEAGUE: ΑΠΟΥΣΙΕΣ ΣΤΑ ΣΥΝΟΛΑ (9/10/2026, Στελιος: «τρεξε τεστ για τα συνολα — εκει τα λεπτα δεν αρκουν,
μετραει η επιδραση του παικτη: αμυντικογενης → πεφτει η αμυνα, σκορερ → πεφτει η επιθεση»).
Ιδεα: χωριζουμε το συνολο σε ΠΟΝΤΟΥΣ ΚΑΘΕ ΟΜΑΔΑΣ (μοντελο: γηπ = (συνολο + διαφορα)/2, φιλ = (συνολο − διαφορα)/2). Οι ποντοι μιας ομαδας
επηρεαζονται απο (α) τους ΔΙΚΟΥΣ της αποντες (επιθεση) και (β) τους αποντες του ΑΝΤΙΠΑΛΟΥ (αμυνα του αντιπαλου).
Απουσια = ιδιος ορισμος με το LIVE (ταχτικος ≥3/10 φετινα, λεπτα μ.ο. 10 τελευταιων ≥10′, k: 1-3 πληρες / 4-10 μισο / >10 τιποτα).
Προφιλ παικτη (ματς ΠΡΙΝ, 60 τελευταια, μαζεμα 200′, τυποποιημενα z): ποντοι/40 · ασιστ/40 · «αμυνα» (κλεψ.+κοψ.+αμ. ριμπ.)/40 · +/-/40.
ΕΚΔΟΧΕΣ (ποντοι ομαδας − μοντελο = ...):
 V1 μονο λεπτα: a·Σ δικα λεπτα/40 + b·Σ λεπτα αντιπαλου/40
 V2 + ΕΠΙΘΕΣΗ: + c·Σ δικα λεπτα/40·z(ποντοι) + d·Σ δικα λεπτα/40·z(ασιστ)
 V3 + ΑΜΥΝΑ: + e·Σ λεπτα αντιπαλου/40·z(αμυνα)
 V4 ολα (V2 + V3) · V5 +/- : + f·Σ δικα·z(+/-) + h·Σ αντιπαλου·z(+/-)
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση), LOSO 5 σεζον (E2021-25):
 Κ1 V1 ΠΕΡΝΑ αν RMSE συνολου (πραγμ − μοντελο − διορθωση) καλυτερο απο «τιποτα» σε ≥4/5 σεζον.
 Κ2 V2..V5 ΠΕΡΝΑ αν καλυτερο απο V1 σε ≥4/5 σεζον ΚΑΙ ο νεος συντελεστης εχει ιδιο προσημο σε ≥4/5 σεζον.
 Για live: ΚΑΙ μοναδες picks συνολων (≥8%, σ 16.7, ανοιγμα Crown) ≥ χωρις διορθωση.
Αναφορα: CLV picks συνολων, αποσταση απο κλεισιμο, ποσο απο τη διορθωση εχει ηδη η αγορα. Εξοδος: el_absence_totals_out.txt"""
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
# p = [id, ονομα, βασικος, λεπτα, ποντοι, 2π εο, 2π επ, 3π εο, 3π επ, βολ εο, βολ επ, επ.ριμπ, αμ.ριμπ, ασιστ, κλεψ, λαθη, κοψ, φαουλ, PIR, +/-]
TG = collections.defaultdict(list)
for k, g in PL.items():
    if g.get('comp') != 'E' or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        TG[(g['season'], g[tc])].append((ts, {p[0]: (p[3] or 0.0, p[4] or 0, p[13] or 0, (p[14] or 0) + (p[16] or 0) + (p[12] or 0), p[19] or 0) for p in g[side]}))
for v in TG.values(): v.sort(key=lambda x: x[0])
PH = collections.defaultdict(list)
for L in TG.values():
    for ts, d in L:
        for pid, x in d.items():
            if x[0] > 0: PH[pid].append((ts,) + x)
for v in PH.values(): v.sort()
FE = ('pts', 'ast', 'dfn', 'pm')
def prof(pid, ts):
    h = [x for x in PH[pid] if x[0] < ts - 3600][-60:]
    if not h: return None
    a = np.array([x[1:] for x in h], float); per = a[:, 1:].sum(0) / (a[:, 0].sum() + 200.0) * 40
    return dict(min=float(a[-10:, 0].mean()), **dict(zip(FE, per)))
def absents(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v[0] > 0); res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, (0,))[0] > 0: continue
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = prof(pid, ts)
        if v is None or v['min'] < 10: continue
        v['w'] = v['min'] / 40 * (1.0 if k + 1 <= 3 else (.5 if k + 1 <= 10 else 0.0))
        if v['w'] > 0: res.append(v)
    return res
rows = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('t_new') is None or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); ah, aa = absents(sea, hc, ts), absents(sea, ac, ts)
    if ah is None or aa is None: continue
    T, M = float(NP[key]['t_new']), float(NP[key]['h_new'])
    rows.append(dict(y=sea, hs=float(D.hs.values[pos]), as_=float(D.as_.values[pos]), T=T, M=M, ah=ah, aa=aa,
                     op=d_['open'], cl=d_[0], gn=NP[key].get('gn', NP[key].get('rnd', 99))))
P(f'ματς E2021-25 με live προβλεψη συνολου, αγορα συνολων (Crown) & παικτες: {len(rows)} · με τουλαχιστον 1 απων: {sum(1 for r in rows if r["ah"] or r["aa"])}')
allp = [p for r in rows for p in r['ah'] + r['aa']]
MU = {f: np.mean([p[f] for p in allp]) for f in FE}; SD = {f: np.std([p[f] for p in allp]) for f in FE}
P(f'απουσες (με βαρος): {len(allp)} · μεσα λεπτα {np.mean([p["min"] for p in allp]):.1f}′')
z = lambda p, f: (p[f] - MU[f]) / SD[f]
# ---- ομαδα-ματς: ποντοι ομαδας − μοντελο ----
NAMES = ['δικα λεπτα', 'λεπτα αντιπ.', 'δικα×ποντοι', 'δικα×ασιστ', 'αντιπ.×αμυνα', 'δικα×(+/-)', 'αντιπ.×(+/-)']
def tfeat(own, opp):
    return np.array([sum(p['w'] for p in own), sum(p['w'] for p in opp), sum(p['w'] * z(p, 'pts') for p in own), sum(p['w'] * z(p, 'ast') for p in own),
                     sum(p['w'] * z(p, 'dfn') for p in opp), sum(p['w'] * z(p, 'pm') for p in own), sum(p['w'] * z(p, 'pm') for p in opp)])
XH = np.array([tfeat(r['ah'], r['aa']) for r in rows]); XA = np.array([tfeat(r['aa'], r['ah']) for r in rows])
YH = np.array([r['hs'] - (r['T'] + r['M']) / 2 for r in rows]); YA = np.array([r['as_'] - (r['T'] - r['M']) / 2 for r in rows])
ys = np.array([r['y'] for r in rows]); YT = YH + YA
VAR = {'V1 μονο λεπτα': [0, 1], 'V2 +επιθεση (ποντοι, ασιστ)': [0, 1, 2, 3], 'V3 +αμυνα αντιπαλου': [0, 1, 4], 'V4 επιθεση+αμυνα': [0, 1, 2, 3, 4],
       'V5 +/- (δικα & αντιπ.)': [0, 1, 5, 6]}
def fit(cols, tr):
    X = np.r_[XH[tr][:, cols], XA[tr][:, cols]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(len(cols)), X.T @ y)
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
ALL = np.ones(len(rows), bool)
P(''); P(f'## ΣΥΝΤΕΛΕΣΤΕΣ (ποντοι ομαδας ανα 40′ απουσιας· z = ανα 1 τυπ. αποκλιση) — ολα τα δεδομενα και ανα σεζον')
HELD = {}
for nm, cols in VAR.items():
    b = fit(cols, ALL); per = {s: fit(cols, ys == s) for s in SE}
    P(f'  {nm}:')
    for j, c in enumerate(cols):
        same = sum(1 for s in SE if np.sign(per[s][j]) == np.sign(b[j]))
        P(f'     {NAMES[c]:14s} {b[j]:+.2f}  · ανα σεζον ' + ' '.join(f'{s[-2:]}:{per[s][j]:+.2f}' for s in SE) + f' (ιδιο προσημο {same}/5)')
    h = np.zeros(len(rows))
    for Yr in SE:
        bb = fit(cols, ys != Yr); m = ys == Yr; h[m] = XH[m][:, cols] @ bb + XA[m][:, cols] @ bb
    HELD[nm] = h
P(''); P('## LOSO — RMSE ΣΥΝΟΛΟΥ (εκτιμηση 4 σεζον → ελεγχος στην 5η)')
P(f'  χωρις διορθωση: {rmse(YT, ALL):.3f}')
for nm in VAR:
    h = HELD[nm]; d0 = [rmse(YT - h, ys == s) - rmse(YT, ys == s) for s in SE]
    line = f'  {nm:30s} {rmse(YT - h, ALL):.3f} · vs τιποτα ' + ' '.join(f'{x:+.3f}' for x in d0) + f' → {sum(x < 0 for x in d0)}/5'
    if nm.startswith('V1'): line += '  <- Κ1 ΠΕΡΝΑ' if sum(x < 0 for x in d0) >= 4 else '  Κ1 ✗'
    else:
        d1 = [rmse(YT - h, ys == s) - rmse(YT - HELD['V1 μονο λεπτα'], ys == s) for s in SE]
        line += ' · vs V1 ' + ' '.join(f'{x:+.3f}' for x in d1) + f' → {sum(x < 0 for x in d1)}/5'
    P(line)
P('  (Κ2 = vs V1 ≥4/5 ΚΑΙ νεοι συντελεστες ιδιο προσημο ≥4/5 — βλ. πανω)')
# ---- και η ΔΙΑΦΟΡΑ: η χωρισμενη επιθεση/αμυνα βοηθα και το χαντικαπ; (αναφορα) ----
YM = YH - YA
P(''); P('## (αναφορα) ΔΙΑΦΟΡΑ γηπ−φιλ με τα ιδια μοντελα vs LIVE «μονο λεπτα» 0.922')
live = np.array([sum(p['w'] for p in r['aa']) - sum(p['w'] for p in r['ah']) for r in rows]) * 0.922
P(f'  χωρις {rmse(YM, ALL):.3f} · LIVE {rmse(YM - live, ALL):.3f}')
for nm, cols in VAR.items():
    h = np.zeros(len(rows))
    for Yr in SE:
        bb = fit(cols, ys != Yr); m = ys == Yr; h[m] = XH[m][:, cols] @ bb - XA[m][:, cols] @ bb
    d = [rmse(YM - h, ys == s) - rmse(YM - live, ys == s) for s in SE]
    P(f'  {nm:30s} {rmse(YM - h, ALL):.3f} · vs LIVE ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5')
# ---- picks συνολων: ≥8%, σ 16.7, ανοιγμα Crown (row = [ts, αναμ. συνολο, γραμμη, over, under]) ----
def tp(t, T_):
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7); return po, 1 - po - pu, pu
    po = 1 - Phi((T_ - t) / 16.7); return po, 0.0, 1 - po
def picks(adj):
    U = collections.defaultdict(list); mv = []; cnt = collections.Counter()
    for r, a in zip(rows, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; t = r['T'] + a
        po, pp, pu = tp(t, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e < .08: continue
        x = (r['hs'] + r['as_'] - T_) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1)); mv.append((r['cl'][1] - o[1]) * sd)
        cnt['over' if sd == 1 else 'under'] += 1
    u = [x for v in U.values() for x in v]
    return (f"{len(u):4d} picks · {sum(u):+6.1f}μ · ROI {np.mean(u)*100:+5.1f}% (θετ {sum(1 for s in SE if U[s] and np.mean(U[s]) > 0)}/5) · "
            + ' '.join(f"{s[-2:]}:{sum(U[s]):+.1f}" for s in SE) + f" · CLV {np.mean(mv):+.2f} π. · over/under {cnt['over']}/{cnt['under']}")
P(''); P('## PICKS ΣΥΝΟΛΩΝ ≥8% (σ 16.7, ανοιγμα Crown) — LOSO διορθωση')
P('  χωρις διορθωση               ' + picks(np.zeros(len(rows))))
for nm in VAR: P(f'  {nm:30s}' + picks(HELD[nm]))
P(''); P('## ΑΓΟΡΑ: ποσο απο τη διορθωση (V4, ολα τα δεδομενα) «εχει» ηδη η γραμμη (1 = ολη, 0 = τιποτα)')
cols = VAR['V4 επιθεση+αμυνα']; b = fit(cols, ALL); adj = XH[:, cols] @ b + XA[:, cols] @ b
TT = np.array([r['T'] for r in rows]); MO = np.array([r['op'][1] for r in rows]); MC = np.array([r['cl'][1] for r in rows]); ACT = np.array([r['hs'] + r['as_'] for r in rows])
for nm, ref in (('ανοιγμα', MO), ('κλεισιμο', MC)):
    P(f'  {nm}: (αγορα − μοντελο) = {np.polyfit(adj, ref - TT, 1)[0]:.2f} × διορθωση · (πραγμ − αγορα) = {np.polyfit(adj, ACT - ref, 1)[0]:+.2f} × διορθωση')
P(f'  αποσταση μοντελου απο κλεισιμο: χωρις {rmse(MC - TT, ALL):.3f} · V1 {rmse(MC - TT - HELD["V1 μονο λεπτα"], ALL):.3f} · V4 {rmse(MC - TT - HELD["V4 επιθεση+αμυνα"], ALL):.3f}')
P(f'  μεγεθος διορθωσης V4 (LOSO): |μ.ο.| {np.mean(np.abs(HELD["V4 επιθεση+αμυνα"])):.2f} π. · 95% {np.percentile(np.abs(HELD["V4 επιθεση+αμυνα"]), 95):.2f} π.')
open('el_absence_totals_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
