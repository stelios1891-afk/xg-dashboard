# -*- coding: utf-8 -*-
"""el_all_sources_test.py — ΤΕΣΤ Γ (25/9/2026): ΟΛΕΣ οι πηγες αρχης σεζον στο ΙΔΙΟ τεστ, ιδιες σεζον (2021-22 … 2025-26), ιδια μοναδα.
Πηγες (ολες μονο με πληροφορια ΠΡΙΝ τη σεζον):
  ομαδα   = rating ομαδας περσι
  ειδικοι = καταταξη BasketNews → rating (το rating που ειχε ιστορικα η ομαδα σε εκεινη τη θεση, απο τις ΑΛΛΕΣ σεζον)
  δικη μας = αξια παικτων (στατιστικα + +/-, 2 σεζον) × πραγματικα λεπτα
  3steps  = βαθμολογια 3StepsBasket περσι (EL + αλλα πρωταθληματα) × πραγματικα λεπτα
Βαρη συνδυασμων: LOSO. ΜΕΤΡΑ: RMSE διαφορας αγων 1-10 (ποντοι) · ζευγαρωτη συγκριση με «ομαδα + ειδικοι» · «ελλειψη πληροφοριας»
(κλιση του λαθους του v1 πανω στη διαφωνια με το «ομαδα περσι», ολα σε ποντους).
Εξοδος: el_all_sources_test_out.txt"""
import sys, math, re
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_3s_rating_test.py', encoding='utf-8').read().split('MODELS = [')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
exec(ex[ex.index('RANK = {'):ex.index('ES = list(RANK)')])          # RANK: καταταξη BasketNews 2021-2025
ENDS = {s: np.sort(np.array(list(team_end(s).values())))[::-1] for s in SEAS}
def exp_rating(s, rank, N):
    q = (rank - 0.5) / N
    return float(np.mean([np.interp(q, (np.arange(len(ENDS[r])) + .5) / len(ENDS[r]), ENDS[r]) for r in SEAS if r != s and r >= 'E2018']))
EX = {}
for s, rk in RANK.items():
    for t, r_ in rk.items(): EX[(s, t)] = exp_rating(s, r_, len(rk))
Q['exp'] = [EX.get((s, D.loc[k, 'home']), np.nan) - EX.get((s, D.loc[k, 'away']), np.nan) for k, s in zip(Q.key, Q.season)]
S5 = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
Q5 = Q[Q.season.isin(S5)].copy()
P(f'ματς 2021-2025: {len(Q5)} (αγων 1-10: {(Q5.rnd <= 10).sum()}) · με rating ειδικων: {Q5.exp.notna().mean():.0%}')

MODELS = [('ομαδα', ['team']), ('ομαδα + δικη μας', ['team', 'ours']), ('ομαδα + 3steps', ['team', 'rB', 'uB']),
          ('ομαδα + δικη μας + 3steps', ['team', 'ours', 'rB', 'uB']), ('ειδικοι μονο', ['exp']), ('ομαδα + ειδικοι', ['team', 'exp']),
          ('ομαδα + ειδικοι + δικη μας', ['team', 'exp', 'ours']), ('ομαδα + ειδικοι + 3steps', ['team', 'exp', 'rB', 'uB']),
          ('ομαδα + ειδικοι + δικη μας + 3steps', ['team', 'exp', 'ours', 'rB', 'uB'])]
PRED = {}
P('')
P('=== ΣΦΑΛΜΑ ΠΡΟΒΛΕΨΗΣ ΔΙΑΦΟΡΑΣ (RMSE, ποντοι) — αγωνιστικες 1-10, 2021-2025, βαρη LOSO ===')
for m, cols in MODELS:
    E, cs = [], []
    for Y in S5:
        tr, te_ = Q5[Q5.season != Y], Q5[Q5.season == Y]
        c = np.linalg.lstsq(tr[['home'] + cols].values, tr.y.values, rcond=None)[0]; cs.append(c)
        pr = te_[['home'] + cols].values @ c * te_.poss.values / 100
        E.append(pd.DataFrame(dict(e=te_.margin.values - pr, pr=pr, rnd=te_.rnd.values, season=Y, key=te_.key.values)))
    E = pd.concat(E).set_index('key'); PRED[m] = E
    e10 = E[E.rnd <= 10]
    per = ' '.join(f'{Y[-2:]}:{np.sqrt(np.mean(e10[e10.season == Y].e ** 2)):.2f}' for Y in S5)
    w = np.round(np.mean(cs, axis=0)[1:], 2).tolist()
    P(f'  {m:36s} 1-10 {np.sqrt(np.mean(e10.e ** 2)):.2f} · ολη {np.sqrt(np.mean(E.e ** 2)):.2f} | {per} | βαρη {w}')

P('')
P('=== ΠΡΟΣΘΕΤΟΥΝ ΤΑ ΔΕΔΟΜΕΝΑ ΠΑΙΚΤΩΝ ΠΑΝΩ ΑΠΟ «ομαδα + ειδικοι»; (ζευγαρωτα, ιδια ματς αγων 1-10) ===')
base = PRED['ομαδα + ειδικοι']; b10 = base[base.rnd <= 10]
for m in ('ομαδα + ειδικοι + δικη μας', 'ομαδα + ειδικοι + 3steps', 'ομαδα + ειδικοι + δικη μας + 3steps', 'ομαδα'):
    x = PRED[m].loc[b10.index]; d = b10.e ** 2 - x.e ** 2
    wins = sum(1 for Y in S5 if np.mean(x[x.season == Y].e ** 2) < np.mean(b10[b10.season == Y].e ** 2))
    P(f'  {m:36s} βελτιωση τετρ. λαθους {d.mean():+.2f} (t {d.mean() / (d.std(ddof=1) / math.sqrt(len(d))):+.2f}) · καλυτερο σε {wins}/5 σεζον')

P('')
P('=== ΕΛΛΕΙΨΗ ΠΛΗΡΟΦΟΡΙΑΣ (ολα σε ποντους): y = πραγματικη − v1 · x = προβλεψη πηγης − προβλεψη «ομαδα» · αγων 1-10 ===')
v1 = ns['run']()[:, 0]; Dk = ns['D'].reset_index(drop=True); V1 = dict(zip(Dk.key, v1))
b0 = PRED['ομαδα']; b0 = b0[b0.rnd <= 10]
yv = Q5.set_index('key').loc[b0.index, 'margin'] - b0.index.map(V1)
for m, _ in MODELS[1:]:
    e1 = PRED[m].loc[b0.index]; x = e1.pr - b0.pr
    b = np.polyfit(x, yv, 1)[0]; res = yv - b * x
    se = math.sqrt(np.sum((res - res.mean()) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    pos = sum(1 for Y in S5 if np.polyfit(x[e1.season == Y], yv[e1.season == Y], 1)[0] > 0)
    P(f'  {m:36s} κλιση {b:+.2f} (t {b/se:+.1f}) · θετικη σε {pos}/5 · μεσο |διαφωνια| {np.mean(np.abs(x)):.1f} π.')
open('el_all_sources_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
