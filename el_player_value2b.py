# -*- coding: utf-8 -*-
"""el_player_value2b.py — ΒΗΜΑ 1 (συνεχεια): αξια παικτη απο 1 ή 2 σεζον & συγκριση στην ΑΡΧΗ ΣΕΖΟΝ (25/9/2026).
Χρησιμοποιει τους ορισμους του el_player_value2.py (στατιστικα, κεντραρισμα, βαρη).
Παραλλαγες αξιας (για τη σεζον Y, μονο με δεδομενα ως Y−1):
  1σ λ15 : +/- μονο απο Y−1 (οπως el_player_value2)
  2σ λ15 / 2σ λ30 : ενα +/- ανα παικτη απο Y−2 (βαρος 0.5) + Y−1 (βαρος 1)· στατιστικα της πιο προσφατης σεζον του
Συγκριση αρχης σεζον (RMSE διαφορας, ποντοι· καμια φετινη πληροφορια· πραγματικα λεπτα): ομαδα περσι · παικτες · συνδυασμος
(βαρη συνδυασμου LOSO). «Αγνωστοι» (χωρις Ευρωλιγκα Y−1/Y−2) = μεση αξια παικτων στην 1η τους σεζον (αλλες σεζον).
Εξοδος: el_player_value2b_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_player_value2.py', encoding='utf-8').read().split("VARIANTS = [('PIR'")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
TEST = [s for s in SEAS if s >= 'E2019']
seen = set(); firsts = {}
for s in SEAS:
    ps = set(R[R.season == s].pid); firsts[s] = ps - seen; seen |= ps

def fit_u_multi(seasons_w, beta, lam):
    gs = [(design([s_]), wt) for s_, wt in seasons_w]
    nG = sum(len(d[0]) for d, _ in gs)
    ps = list(dict.fromkeys(p for (g, r, rr, w), _ in gs for p in r.pid)); pi = {p: i for i, p in enumerate(ps)}
    A = np.zeros((nG + len(ps), 1 + len(ps))); y = np.zeros(nG + len(ps)); o = 0
    for (g, r, rr, w), wt in gs:
        sw = math.sqrt(wt); idx = list(zip(r.pid, r.season)); off = np.zeros(len(g))
        np.add.at(off, rr, w * box_val(idx, beta, 'box'))
        A[o + np.arange(len(g)), 0] = sw * (~g.neu.values); y[o:o + len(g)] = sw * (g.y.values - off)
        np.add.at(A, (o + rr, 1 + np.array([pi[p] for p in r.pid])), sw * w); o += len(g)
    A[nG + np.arange(len(ps)), 1 + np.arange(len(ps))] = math.sqrt(lam)
    sol = np.linalg.lstsq(A, y, rcond=None)[0]
    return dict(zip(ps, sol[1:]))

def vals_for(Y, kind, lam, beta):
    """αξιες παικτων γνωστες ΠΡΙΝ τη σεζον Y."""
    prev = SEAS[SEAS.index(Y) - 1]; pp = SEAS[SEAS.index(Y) - 2] if SEAS.index(Y) >= 2 else None
    if kind == '1σ':
        u = {k[0]: v for k, v in fit_u(prev, beta, 'box', lam).items()}; seas = [prev]
    else:
        u = fit_u_multi(([(pp, 0.5)] if pp else []) + [(prev, 1.0)], beta, lam); seas = [s_ for s_ in (pp, prev) if s_]
    val = {}
    for s_ in seas:                      # η πιο προσφατη σεζον γραφει τελευταια
        idx = [i for i in X.index if i[1] == s_]
        for i, bv in zip(idx, box_val(idx, beta, 'box')): val[i[0]] = float(bv) + u.get(i[0], 0.0)
    return val

def repl_for(Y, beta):
    fv, fm = [], []
    for t in SEAS[1:]:
        if t == Y: continue
        u = fit_u(t, beta, 'box', 15)
        for p in firsts[t]:
            if (p, t) in X.index:
                fv.append(float(box_val([(p, t)], beta, 'box')[0]) + u.get((p, t), 0.0)); fm.append(X.loc[(p, t), 'min'])
    return float(np.average(fv, weights=fm))

def team_end(season, lam=2.0):
    g = G[G.season == season]; teams = sorted(set(D.loc[g.index, 'home']) | set(D.loc[g.index, 'away'])); ix = {t: i for i, t in enumerate(teams)}
    A = np.zeros((len(g) + len(teams), 1 + len(teams))); y = np.zeros(A.shape[0])
    A[np.arange(len(g)), 0] = (~g.neu.values)
    for j, k in enumerate(g.index):
        A[j, 1 + ix[D.loc[k, 'home']]] += 1; A[j, 1 + ix[D.loc[k, 'away']]] -= 1
    y[:len(g)] = g.y.values; A[len(g) + np.arange(len(teams)), 1 + np.arange(len(teams))] = math.sqrt(lam)
    sol = np.linalg.lstsq(A, y, rcond=None)[0]
    return {t: sol[1 + i] for t, i in ix.items()}
RN = {}
for s in SEAS:
    cnt = {}
    for k in G[G.season == s].sort_values('utc').index:
        h_, a_ = D.loc[k, 'home'], D.loc[k, 'away']; cnt[h_] = cnt.get(h_, 0) + 1; cnt[a_] = cnt.get(a_, 0) + 1
        RN[k] = max(cnt[h_], cnt[a_])

rows = []
for Y in TEST:
    beta = fit_box([t for t in SEAS if t != Y], 'box'); rp = repl_for(Y, beta)
    te = team_end(SEAS[SEAS.index(Y) - 1])
    raws = {}
    for lab, kind, lam in (('1σ λ15', '1σ', 15), ('2σ λ15', '2σ', 15), ('2σ λ30', '2σ', 30)):
        g, raw = raw_pred(Y, vals_for(Y, kind, lam, beta), rp); raws[lab] = raw
    for j, k in enumerate(g.index):
        rows.append(dict(key=k, season=Y, rnd=RN[k], home=float(not g.loc[k, 'neu']), team=te.get(D.loc[k, 'home'], 0.0) - te.get(D.loc[k, 'away'], 0.0),
                         y=g.loc[k, 'y'], poss=g.loc[k, 'poss'], margin=g.loc[k, 'margin'], **{l: raws[l][j] for l in raws}))
    print(f'  {Y} ετοιμο', flush=True)
Q = pd.DataFrame(rows)
P('=== ΑΡΧΗ ΣΕΖΟΝ: RMSE διαφορας (ποντοι), καμια φετινη πληροφορια, πραγματικα λεπτα ===')
MODELS = [('ομαδα περσι', ['team'])] + [(f'παικτες {l}', [l]) for l in ('1σ λ15', '2σ λ15', '2σ λ30')] + \
         [(f'ομαδα + παικτες {l}', ['team', l]) for l in ('1σ λ15', '2σ λ15', '2σ λ30')]
for m, cols in MODELS:
    E = []; cs = []
    for Y in TEST:
        tr, te_ = Q[Q.season != Y], Q[Q.season == Y]
        c = np.linalg.lstsq(tr[['home'] + cols].values, tr.y.values, rcond=None)[0]; cs.append(c)
        E.append(pd.DataFrame(dict(e=te_.margin.values - te_[['home'] + cols].values @ c * te_.poss.values / 100, rnd=te_.rnd.values, season=Y)))
    E = pd.concat(E)
    w1 = sum(1 for Y in TEST if np.sqrt(np.mean(E[(E.season == Y) & (E.rnd <= 10)].e ** 2)) < np.sqrt(np.mean(BASE[(BASE.season == Y) & (BASE.rnd <= 10)].e ** 2))) if m != 'ομαδα περσι' else 0
    if m == 'ομαδα περσι': BASE = E
    P(f'  {m:26s} αγων 1-10 {np.sqrt(np.mean(E[E.rnd <= 10].e ** 2)):.2f} · 11+ {np.sqrt(np.mean(E[E.rnd > 10].e ** 2)):.2f} · ολη {np.sqrt(np.mean(E.e ** 2)):.2f}'
      + (f' · καλυτερο απο «ομαδα» (αγων 1-10) σε {w1}/{len(TEST)} σεζον' if m != 'ομαδα περσι' else '')
      + (f' · βαρη {np.round(np.mean(cs, axis=0)[1:], 2).tolist()}'))
open('el_player_value2b_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ==== ΙΔΙΟ ΤΕΣΤ «ΕΛΛΕΙΨΗΣ ΠΛΗΡΟΦΟΡΙΑΣ» με τους ειδικους: εξηγει η διαφορα (παικτες − ομαδα) το λαθος του v1 στις αγων 1-10; ====
P('')
P('=== ΕΛΛΕΙΨΗ ΠΛΗΡΟΦΟΡΙΑΣ: y = πραγματικη − v1 (walk-forward) · x = προβλεψη παικτων − προβλεψη ομαδας (ποντοι) ===')
v1 = ns['run']()[:, 0]; Dk = ns['D'].reset_index(drop=True); V1 = dict(zip(Dk.key, v1))
for lab in ('1σ λ15', '2σ λ15'):
    cs = []
    for Y in TEST:
        tr = Q[Q.season != Y]
        cs.append((Y, np.linalg.lstsq(tr[['home', 'team']].values, tr.y.values, rcond=None)[0], np.linalg.lstsq(tr[['home', lab]].values, tr.y.values, rcond=None)[0]))
    rows3 = []
    for Y, ct, cp in cs:
        q = Q[(Q.season == Y) & (Q.rnd <= 10)]
        x = (q[['home', lab]].values @ cp - q[['home', 'team']].values @ ct) * q.poss.values / 100
        yv = q.margin.values - q.key.map(V1).values
        rows3.append(pd.DataFrame(dict(x=x, y=yv, season=Y)))
    Z = pd.concat(rows3)
    for per, m in (('2019-2025', Z.season >= 'E2019'), ('2021-2025 (ιδιες με ειδικους)', Z.season >= 'E2021')):
        z = Z[m]; b = np.polyfit(z.x, z.y, 1)[0]; res = z.y - b * z.x
        se = math.sqrt(np.sum((res - res.mean()) ** 2) / (len(z) - 2) / np.sum((z.x - z.x.mean()) ** 2))
        pos = sum(1 for s in z.season.unique() if np.polyfit(z[z.season == s].x, z[z.season == s].y, 1)[0] > 0)
        P(f'  παικτες {lab} · {per}: κλιση {b:+.2f} (t {b/se:+.1f}) · θετικη σε {pos}/{z.season.nunique()} σεζον · {len(z)} ματς')
open('el_player_value2b_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
