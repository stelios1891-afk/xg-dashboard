# -*- coding: utf-8 -*-
"""t103_pace_player_build.py — ΒΗΜΑ 1 του t103: «ΡΥΘΜΟΣ» ΚΑΘΕ ΠΑΙΚΤΗ NBA (25/10/2026, Στελιος «το 1 ξεκινα» — ρυθμος αποντα στα συνολα).
Απο τα κομματια ιδιας πενταδας του t65 (nba_pbp_full, ανασυσταση ελεγμενη στο t65 σταδιο 1):
  y = κατοχες ανα 48′ του κομματιου (μεσος των 2 ομαδων) · βαρος = δευτερολεπτα
  y = σεζον-μεσος + ομαδα(γηπ) + ομαδα(φιλοξ) + Σ 10 παικτες → ridge (ομαδες σχεδον χωρις ποινη → ο παικτης μετρα ON vs OFF ΜΕΣΑ στην ομαδα του)
  λ παικτη απο holdout 20% των ματς (ιδια σεζον).
ΕΛΕΓΧΟΙ ΛΟΓΙΚΗΣ: σταθεροτητα σεζον→σεζον (r, παικτες ≥1000′ και στις δυο) · κορυφη/πατος ονοματα · μεσος ρυθμος σεζον.
Εξοδος: nba_tests/_t103_pace.pkl {σεζον: {nba_id: (ρυθμος κατοχες/48, λεπτα)}} · nba_tests/t103_pace_player_build_out.txt"""
import os, sys, pickle, collections
import numpy as np, scipy.sparse as sp
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
import t65_lineups as L1
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
FIN = pickle.load(open(os.path.join(L1.T65, 'final.pkl'), 'rb')); E2N, NAMEE = FIN['E2N'], FIN['NAMEE']
SEAS = [2022, 2023, 2024, 2025, 2026]
def poss(fga, fta, oreb, tov): return fga + 0.44 * fta - oreb + tov
def fit(R, lam, train=None):
    G = R['G']; ST = R['ST']
    teams = sorted({g['home'] for g in G} | {g['away'] for g in G}); TI = {t: k for k, t in enumerate(teams)}
    pl = sorted({p for x in ST for p in list(x[1]) + list(x[2])}); PI = {p: len(teams) + k for k, p in enumerate(pl)}
    n = len(teams) + len(pl); rows = []
    for x in ST:
        gi, h5, a5, sec = x[0], x[1], x[2], x[3]
        if sec < 1: continue
        y = (poss(*x[6:10]) + poss(*x[10:14])) / 2 / (sec / 2880.0)
        rows.append((gi, h5, a5, sec, y))
    keep = [r for r in rows if train is None or train[r[0]]]
    mu = sum(r[3] * r[4] for r in keep) / sum(r[3] for r in keep)
    ri, ci = [], []
    for j, (gi, h5, a5, sec, y) in enumerate(keep):
        idx = [TI[G[gi]['home']], TI[G[gi]['away']]] + [PI[p] for p in list(h5) + list(a5)]
        ri += [j] * len(idx); ci += idx
    X = sp.csr_matrix((np.ones(len(ri)), (ri, ci)), shape=(len(keep), n))
    w = np.array([r[3] for r in keep]) / 60.0; yv = np.array([r[4] for r in keep]) - mu
    A = (X.T @ sp.diags(w) @ X).toarray(); b = X.T @ (w * yv)
    pen = np.r_[np.full(len(teams), 1.0), np.full(len(pl), lam)]
    beta = np.linalg.solve(A + np.diag(pen), b)
    return mu, {t: beta[TI[t]] for t in teams}, {p: beta[PI[p]] for p in pl}, rows
def pred_err(R, lam, seed=7):
    rng = np.random.default_rng(seed); ng = len(R['G']); tr = rng.random(ng) < 0.8
    mu, tb, pb, rows = fit(R, lam, tr)
    se = sw = 0.0
    for gi, h5, a5, sec, y in rows:
        if tr[gi]: continue
        g = R['G'][gi]; yh = mu + tb.get(g['home'], 0) + tb.get(g['away'], 0) + sum(pb.get(p, 0) for p in list(h5) + list(a5))
        se += sec * (y - yh) ** 2; sw += sec
    return se / sw
OUT = {}
P('t103 ΒΗΜΑ 1 — ρυθμος παικτη (κατοχες/48′ οταν ειναι στο γηπεδο, σε σχεση με την ομαδα του)')
for s in SEAS:
    R = L1.run(s)
    errs = {lam: pred_err(R, lam) for lam in (500, 1000, 2000, 4000, 8000)}
    lam = min(errs, key=errs.get)
    mu, tb, pb, rows = fit(R, lam)
    mins = collections.Counter()
    for gi, h5, a5, sec, y in rows:
        for p in list(h5) + list(a5): mins[p] += sec / 60.0
    OUT[s] = {E2N[p]: (float(v), float(mins[p])) for p, v in pb.items() if p in E2N}
    big = sorted([p for p in pb if mins[p] >= 1000], key=lambda p: pb[p])
    nm = lambda p: f"{NAMEE.get(p, p)} {pb[p]:+.2f}"
    P(f'\n{s - 1}-{s % 100:02d} · μεσος ρυθμος {mu:.1f} κατοχες/48 · λ {lam} (holdout σφαλμα ' + ' '.join(f'{k}:{v:.1f}' for k, v in errs.items()) + f')'
      f' · παικτες {len(pb)} (≥1000′: {len(big)}) · διασπορα (≥1000′) sd {np.std([pb[p] for p in big]):.2f}')
    P('   πιο ΑΡΓΟΙ: ' + ' · '.join(nm(p) for p in big[:8]))
    P('   πιο ΓΡΗΓΟΡΟΙ: ' + ' · '.join(nm(p) for p in big[::-1][:8]))
P('\nΣΤΑΘΕΡΟΤΗΤΑ σεζον → επομενη (παικτες ≥1000′ και στις δυο):')
for a, b in zip(SEAS[:-1], SEAS[1:]):
    com = [k for k in OUT[a] if k in OUT[b] and OUT[a][k][1] >= 1000 and OUT[b][k][1] >= 1000]
    x = np.array([OUT[a][k][0] for k in com]); y = np.array([OUT[b][k][0] for k in com])
    P(f'  {a - 1}-{a % 100:02d} → {b - 1}-{b % 100:02d}: r {np.corrcoef(x, y)[0, 1]:+.2f} · κλιση {np.polyfit(x, y, 1)[0]:+.2f} · παικτες {len(com)}')
pickle.dump(OUT, open(os.path.join(SC, '_t103_pace.pkl'), 'wb'))
open(os.path.join(SC, 't103_pace_player_build_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
