# -*- coding: utf-8 -*-
"""el_3s_rating_test.py — ΒΟΗΘΑΕΙ Η ΒΑΘΜΟΛΟΓΙΑ 3StepsBasket ΑΥΤΟΥΣΙΑ; (25/9/2026, ερωτημα Στελιου)
Αξια παικτη = overallRating του 3steps την προηγουμενη σεζον (χωρις δικα μας στατιστικα).
  Α: μονο βαθμολογια Ευρωλιγκας Y−1 · Β: + βαθμολογια απο αλλο πρωταθλημα Y−1 (ACB, NBA, BCL, BBL…) για οσους δεν επαιξαν EL
  Οσοι δεν εχουν βαθμολογια: ξεχωριστη μεταβλητη «λεπτα αγνωστων» (το μοντελο μαθαινει ποσο αξιζουν κατα μεσο ορο).
ΤΕΣΤ ΑΡΧΗΣ ΣΕΖΟΝ (ιδιο με el_player_value2b): ματς σεζον Y, πληροφορια μονο ως Y−1, πραγματικα λεπτα, βαρη LOSO.
  RMSE διαφορας αγων 1-10 · συγκριση: ομαδα περσι / δικη μας αξια (στατιστικα+/-, 2σ) / 3steps / συνδυασμοι.
  + ιδιο τεστ «ελλειψης πληροφοριας» (εξηγει το λαθος του v1 στις αγων 1-10;). Σεζον-τεστ: 2020-21 … 2025-26.
Εξοδος: el_3s_rating_test_out.txt"""
import sys, math, re, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()

def key(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    if ',' in s: a, b = s.split(',', 1); s = b + ' ' + a
    return ' '.join(sorted(re.findall(r'[a-z]+', s)))
T3 = pd.read_csv('threesteps_players.csv', low_memory=False)
T3['k'] = (T3.firstname.fillna('') + ' ' + T3.surname.fillna('')).map(key)
T3['tot_min'] = T3.mins * T3.gamesPlayed.fillna(0)
SM = {f'{y}-{str(y+1)[2:]}': f'E{y}' for y in range(2015, 2027)}
T3['es'] = T3.season.map(SM)
T3 = T3[T3.overallRating.notna() & (T3.tot_min >= 100)]
# ενα rating ανα (ονομα, σεζον, EL ή αλλο): κραταμε το πρωταθλημα με τα περισσοτερα λεπτα
ELR = T3[T3.slug == 'euroleague'].sort_values('tot_min').drop_duplicates(['k', 'es'], keep='last').set_index(['k', 'es']).overallRating
OTH = T3[T3.slug != 'euroleague'].sort_values('tot_min').drop_duplicates(['k', 'es'], keep='last').set_index(['k', 'es'])
names = R.groupby('pid').name.first().map(key)
TEST3 = [s for s in SEAS if 'E2020' <= s <= 'E2025']
MU = float(ELR.mean())

rows = []
for Y in TEST3:
    prev = SEAS[SEAS.index(Y) - 1]
    beta = fit_box([t for t in SEAS if t != Y], 'box'); rp = repl_for(Y, beta)
    g, raw_ours = raw_pred(Y, vals_for(Y, '2σ', 15, beta), rp)
    _, r_, rr, w = design([Y])
    k_ = r_.pid.map(names).values
    ra = np.array([ELR.get((kk, prev), np.nan) for kk in k_])
    rb = ra.copy(); lg = np.array([None] * len(k_), dtype=object)
    for i, kk in enumerate(k_):
        if np.isnan(rb[i]) and (kk, prev) in OTH.index:
            rb[i] = OTH.loc[(kk, prev), 'overallRating']; lg[i] = OTH.loc[(kk, prev), 'slug']
    feats = {}
    for lab, rat in (('A', ra), ('B', rb)):
        known = ~np.isnan(rat); v = np.where(known, rat - MU, 0.0)
        a1 = np.zeros(len(g)); np.add.at(a1, rr, w * v)
        a2 = np.zeros(len(g)); np.add.at(a2, rr, w * (~known))
        feats[lab] = (a1, a2)
    te = team_end(prev)
    for j, kk in enumerate(g.index):
        rows.append(dict(key=kk, season=Y, rnd=RN[kk], home=float(not g.loc[kk, 'neu']), y=g.loc[kk, 'y'], poss=g.loc[kk, 'poss'], margin=g.loc[kk, 'margin'],
                         team=te.get(D.loc[kk, 'home'], 0.0) - te.get(D.loc[kk, 'away'], 0.0), ours=raw_ours[j],
                         rA=feats['A'][0][j], uA=feats['A'][1][j], rB=feats['B'][0][j], uB=feats['B'][1][j]))
    print(f'  {Y} ετοιμο · καλυψη λεπτων με rating: EL {np.average(~np.isnan(ra), weights=np.abs(w)):.0%} · +αλλα {np.average(~np.isnan(rb), weights=np.abs(w)):.0%}', flush=True)
Q = pd.DataFrame(rows)
MODELS = [('ομαδα περσι', ['team']), ('δικη μας αξια (2σ)', ['ours']), ('3steps Α (μονο EL)', ['rA', 'uA']), ('3steps Β (+αλλα πρωτ.)', ['rB', 'uB']),
          ('ομαδα + δικη μας', ['team', 'ours']), ('ομαδα + 3steps Β', ['team', 'rB', 'uB']), ('ομαδα + δικη μας + 3steps Β', ['team', 'ours', 'rB', 'uB'])]
P('')
P('=== ΑΡΧΗ ΣΕΖΟΝ: RMSE διαφορας (ποντοι) — πληροφορια μονο ως την προηγουμενη σεζον, πραγματικα λεπτα, βαρη LOSO ===')
PRED = {}
for m, cols in MODELS:
    E = []; pr_all = []
    for Y in TEST3:
        tr, te_ = Q[Q.season != Y], Q[Q.season == Y]
        c = np.linalg.lstsq(tr[['home'] + cols].values, tr.y.values, rcond=None)[0]
        pr = te_[['home'] + cols].values @ c * te_.poss.values / 100
        E.append(pd.DataFrame(dict(e=te_.margin.values - pr, rnd=te_.rnd.values, season=Y, key=te_.key.values, pr=pr)))
    E = pd.concat(E); PRED[m] = E
    if m == 'ομαδα περσι': BASE = E
    wins = sum(1 for Y in TEST3 if np.sqrt(np.mean(E[(E.season == Y) & (E.rnd <= 10)].e ** 2)) < np.sqrt(np.mean(BASE[(BASE.season == Y) & (BASE.rnd <= 10)].e ** 2)))
    P(f'  {m:30s} αγων 1-10 {np.sqrt(np.mean(E[E.rnd <= 10].e ** 2)):.2f} · 11+ {np.sqrt(np.mean(E[E.rnd > 10].e ** 2)):.2f} · ολη {np.sqrt(np.mean(E.e ** 2)):.2f}'
      + (f' · καλυτερο απο «ομαδα» (1-10) σε {wins}/{len(TEST3)}' if m != 'ομαδα περσι' else ''))
P('')
P('=== ΕΛΛΕΙΨΗ ΠΛΗΡΟΦΟΡΙΑΣ: y = πραγματικη − v1 (walk-forward) · x = προβλεψη − προβλεψη «ομαδα περσι» · αγων 1-10 ===')
v1 = ns['run']()[:, 0]; Dk = ns['D'].reset_index(drop=True); V1 = dict(zip(Dk.key, v1))
for m in MODELS[1:]:
    E = PRED[m[0]]; e1 = E[E.rnd <= 10].set_index('key'); b0 = BASE[BASE.rnd <= 10].set_index('key')
    x = e1.pr - b0.loc[e1.index, 'pr']; yv = Q.set_index('key').loc[e1.index, 'margin'] - e1.index.map(V1)
    b = np.polyfit(x, yv, 1)[0]; res = yv - b * x
    se = math.sqrt(np.sum((res - res.mean()) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    pos = sum(1 for Y in TEST3 if np.polyfit(x[e1.season == Y], yv[e1.season == Y], 1)[0] > 0)
    P(f'  {m[0]:30s} κλιση {b:+.2f} (t {b/se:+.1f}) · θετικη σε {pos}/{len(TEST3)} σεζον')
P('  (ειδικοι BasketNews, 2021-25, ιδιο τεστ: κλιση +0.45 σε μοναδες rating, t +3.1, 5/5)')
open('el_3s_rating_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
