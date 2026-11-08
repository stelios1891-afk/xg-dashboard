# -*- coding: utf-8 -*-
"""el_tests_1021b.py — EUROLEAGUE ΣΥΝΟΛΑ: Τ3β αμυντικες απουσιες vs ΑΓΟΡΑ · Τ3γ μηχανη με αγκυρα στην αγορα (τυπου NBA Μ2δ) (21/10/2026, «ολα τρεξτα»).
Βαση: el_absence_onoff_test.py (E2021-25, αποντες απο box score, on/off ΠΕΡΣΙΝΗΣ σεζον 3StepsBasket, βαρος w = λεπτα/40 × g(k)).
 Σ_O = Σ w·z(onO) ολων των αποντων (+ = λειπουν καλοι επιθετικοι) · Σ_D = Σ w·z(onD) (− = λειπουν καλοι αμυντικοι) · Σ_W = Σ w.
Τ3β (ΠΡΟ-ΔΗΛΩΜΕΝΟ): (πραγμ − ΚΛΕΙΣΙΜΟ) = a + bW·Σ_W + bO·Σ_O + bD·Σ_D. «Η αγορα υποτιμα τους αμυντικους» αν bD < 0 με t ≤ −2 ΚΑΙ ιδιο προσημο ≥4/5.
Τ3γ (ΠΡΟ-ΔΗΛΩΜΕΝΟ): Α = αγορα ανοιγματος + ridge(λ 50) πανω σε [μοντελο − αγορα, Σ_W, Σ_O, Σ_D, Νοε, Μαρ-Απρ, γραμμη − 165, αγωνας ≤5].
   LIVE συγκριση = μοντελο + on/off live (−0.43·Σ_O − 0.80·Σ_D). Picks ≥ κατωφλι {4, 6, 8}% στο ανοιγμα (LOSO κατωφλι με μοναδες).
   Α ΠΕΡΝΑ αν: RMSE καλυτερο απο την αγορα ανοιγματος σε ≥3/5 ΚΑΙ μοναδες LOSO > LIVE (≥8%) ΚΑΙ θετικο ≥4/5 ΚΑΙ walk-forward (E2023-25) θετικο ≥2/3.
Εξοδος: el_tests_1021b_out.txt"""
import sys, io, contextlib, collections
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_onoff_test.py', encoding='utf-8').read().split("P(''); P('################ ΣΥΝΟΛΑ ################')")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
pd, D, REC, NP, SE, absents, zf = ns['pd'], ns['D'], ns['REC'], ns['NP'], ns['SE'], ns['absents'], ns['zf']
from statistics import NormalDist
Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
R = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('t_new') is None or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); ah, aa = absents(sea, hc, ts), absents(sea, ac, ts)
    if ah is None or aa is None: continue
    A = ah + aa
    R.append(dict(s=sea, mon=t.month, gn=NP[key].get('gn', 99), tot=float(D.hs.values[pos] + D.as_.values[pos]), mt=float(NP[key]['t_new']),
                  op=d_['open'], cl=d_[0], SW=sum(p['w'] for p in A), SO=sum(p['w'] * zf(p, 'onO') for p in A), SD=sum(p['w'] * zf(p, 'onD') for p in A)))
X = pd.DataFrame(R); X['fo'] = [o[1] for o in X.op]; X['fc'] = [c[1] for c in X.cl]; X['L'] = [o[2] for o in X.op]
X['oo'] = [o[3] for o in X.op]; X['ou'] = [o[4] for o in X.op]
P(f'ματς {len(X)} · με αποντες {int((X.SW > 0).sum())}')
# ================= Τ3β =================
P(''); P('=== Τ3β · (πραγμ − ΚΛΕΙΣΙΜΟ) πανω στις απουσιες ===')
def ols(d, y):
    A = np.c_[np.ones(len(d)), d.SW, d.SO, d.SD]; b = np.linalg.lstsq(A, y, rcond=None)[0]; r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.inv(A.T @ A) * np.sum(r ** 2) / (len(y) - 4))); return b, se
for lab, col in (('κλεισιμο', 'fc'), ('ανοιγμα', 'fo')):
    b, se = ols(X, (X.tot - X[col]).values)
    per = {s: ols(X[X.s == s], (X[X.s == s].tot - X[X.s == s][col]).values)[0] for s in SE}
    P(f'  πραγμ − {lab}: λεπτα bW {b[1]:+.2f} ± {se[1]:.2f} · επιθεση bO {b[2]:+.2f} ± {se[2]:.2f} · ΑΜΥΝΑ bD {b[3]:+.2f} ± {se[3]:.2f} (t {b[3] / se[3]:+.1f}) · '
      f'bD ανα σεζον ' + ' '.join(f'{s[-2:]}:{v[3]:+.2f}' for s, v in per.items()) + f' (αρνητικο {sum(v[3] < 0 for v in per.values())}/5)')
    if col == 'fc':
        ok = b[3] < 0 and b[3] / se[3] <= -2 and sum(v[3] < 0 for v in per.values()) >= 4
        P(f'  → «η αγορα υποτιμα τους απoντες αμυντικους»: {"ΝΑΙ" if ok else "ΟΧΙ (με τα κριτηρια)"}')
b, _ = ols(X, (X.mt - X.fc).values)
P(f'  (για συγκριση: το ΜΟΝΤΕΛΟ μας − κλεισιμο πανω στις ιδιες: bO {b[2]:+.2f} · bD {b[3]:+.2f} — το μοντελο συνολων δεν ξερει απουσιες)')
# ================= Τ3γ =================
P(''); P('=== Τ3γ · ΣΥΝΟΛΑ ΜΕ ΑΓΚΥΡΑ ΣΤΗΝ ΑΓΟΡΑ (ανοιγμα) ===')
X['live'] = X['mt'] - 0.43 * X.SO - 0.80 * X.SD
def feats(d): return np.c_[d['mt'] - d.fo, d.SW, d.SO, d.SD, (d.mon == 11).astype(float), d.mon.isin([3, 4]).astype(float), d.L - 165, (d.gn <= 5).astype(float)]
y = (X.tot - X.fo).values; ys = X.s.values; F = feats(X)
def fitp(tr, te):
    A = np.c_[np.ones(tr.sum()), F[tr]]; b = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y[tr])
    return X.fo.values[te] + np.c_[np.ones(te.sum()), F[te]] @ b, b
X['A'] = 0.0; X['W'] = np.nan
for s in SE: X.loc[ys == s, 'A'] = fitp(ys != s, ys == s)[0]
for s in SE[2:]: X.loc[ys == s, 'W'] = fitp(np.isin(ys, SE[:SE.index(s)]), ys == s)[0]
b_all = fitp(np.ones(len(X), bool), np.ones(len(X), bool))[1]
P('  συντελεστες (ολα): ' + ' · '.join(f'{n} {v:+.2f}' for n, v in zip(['σταθ.', 'μοντ−αγορα', 'ΣW', 'ΣO', 'ΣD', 'Νοε', 'Μαρ-Απρ', 'γραμμη−165', 'αγων≤5'], b_all)))
rm = lambda c, s: float(np.sqrt(np.mean((X.tot[ys == s] - X[c][ys == s]) ** 2)))
P('  RMSE ανα σεζον (αγορα / live / Α): ' + ' · '.join(f'{s[-2:]}: {rm("fo", s):.2f}/{rm("live", s):.2f}/{rm("A", s):.2f}' for s in SE) +
  f' · Α καλυτερο απο αγορα {sum(rm("A", s) < rm("fo", s) for s in SE)}/5')
def picks(col, thr, d=None):
    d = X if d is None else d; res = []
    for r in d.itertuples():
        mu = getattr(r, col)
        if not np.isfinite(mu): continue
        T_ = r.L
        if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - mu) / 16.7); pu = Phi((T_ - .5 - mu) / 16.7)
        else: po = 1 - Phi((T_ - mu) / 16.7); pu = 1 - po
        pq = 1 - po - pu; eo, eu = po * r.oo + pq - 1, pu * r.ou + pq - 1
        sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
        if e < thr: continue
        x = (r.tot - T_) * sd; res.append(dict(s=r.s, sd=sd, res=(od - 1) if x > 0 else (0 if x == 0 else -1), clv=sd * (r.fc - r.fo)))
    return pd.DataFrame(res)
def cell(p):
    if not len(p): return '—'
    ps = p.groupby('s').res.sum()
    return f'{100 * p.res.mean():+6.1f}% ({len(p):4d}, {p.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{p.s.nunique()}) CLV {p.clv.mean():+.2f} · over {int((p.sd == 1).sum())}/under {int((p.sd == -1).sum())}'
LIVE = picks('live', .08); P(f'  LIVE (μοντελο + on/off) ≥8%: {cell(LIVE)}')
P(f'  μοντελο χωρις απουσιες ≥8%: {cell(picks("mt", .08))}')
U = {th: picks('A', th) for th in (.04, .06, .08)}
for th, p in U.items(): P(f'  Α ≥{100 * th:.0f}%: {cell(p)}')
held = []; ch = []
for s in SE:
    best = max(U, key=lambda th: U[th][U[th].s != s].res.sum() if len(U[th]) else -1e9); ch.append(best); held.append(U[best][U[best].s == s])
H = pd.concat(held); ps = H.groupby('s').res.sum()
WF = picks('W', .06, X[X.s.isin(SE[2:])]); wps = WF.groupby('s').res.sum() if len(WF) else pd.Series(dtype=float)
ok = sum(rm('A', s) < rm('fo', s) for s in SE) >= 3 and H.res.sum() > LIVE.res.sum() and (ps > 0).sum() >= 4 and (wps > 0).sum() >= 2
P(f'  Α LOSO κατωφλι {[int(100 * c) for c in ch]}: {cell(H)}')
P(f'  Α walk-forward (6%) E2023-25: {cell(WF)} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{v:+.1f}' for s, v in wps.items()))
P(f'  → Α: {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"} (μοναδες Α {H.res.sum():+.1f} vs LIVE {LIVE.res.sum():+.1f})')
open('el_tests_1021b_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
