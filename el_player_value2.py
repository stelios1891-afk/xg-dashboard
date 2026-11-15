# -*- coding: utf-8 -*-
"""el_player_value2.py — ΑΞΙΑ ΠΑΙΚΤΩΝ v2, ΒΗΜΑ 1: αξια καθε παικτη στην Ευρωλιγκα (25/9/2026).

ΜΟΝΑΔΑ: ποντοι διαφορας ανα 100 κατοχες που προσθετει ο παικτης οταν ειναι στο παρκε (ιδια κλιμακα με το rating ομαδας).
ΜΟΝΤΕΛΟ (ανα ματς Ευρωλιγκας, ολες οι φασεις):
  διαφορα/100 κατ. γηπ = εδρα + Σ_γηπ s_i·v_i − Σ_φιλ s_j·v_j ,  s_i = λεπτα_i / (λεπτα ομαδας / 5)  (5 παικτες στο παρκε)
  v_i = β·x_i + u_i :  x_i = ρυθμοι ανα 40′ του παικτη στη σεζον (2P/3P/ΒΟΛΕΣ ευστοχα & αστοχα, ΕΡ/ΑΡ, ΑΣ, ΚΛ, ΚΟ, ΛΑ, ΦΑ)
                        β = βαρη των στατιστικων, ΜΕΤΡΗΜΕΝΑ απο τα ματς (οχι PIR)
                        u_i = «πραγματικη επιδραση» (+/-) πανω απο τα στατιστικα, με ridge λ (σε ισοδυναμα ματς) → οριο στο θορυβο
ΤΕΣΤ (δικαιο, εκτος δειγματος): τα ματς της σεζον Y προβλεπονται με τις αξιες της Y−1 (+ πραγματικα λεπτα καθε παικτη)·
  οσοι δεν επαιξαν Ευρωλιγκα την Y−1 = «αγνωστη μεταγραφη» (μεσος ορος τετοιων, απο τις αλλες σεζον). Σεζον 2019-2025.
  Συγκρινουμε: PIR · μονο στατιστικα · μονο +/- · συνδυασμος (λ 5/15/40). Μετρο: RMSE διαφορας (ποντοι) + συσχετιση.
Εξοδος: el_player_value2_out.txt, el_player_values_v2.csv (αξια ανα παικτη-σεζον)"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
src = open('el_mech_tests.py', encoding='utf-8').read().split('VARIANTS = [')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
ns = {}; exec(src, ns); D = ns['D'].set_index('key')

PL = json.load(open('el_players.json', encoding='utf-8'))
F = ['p2m', 'p2x', 'p3m', 'p3x', 'ftm', 'ftx', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf']
rows, games = [], []
for k, g in PL.items():
    if g.get('comp') != 'E' or 'err' in g or 'ph' not in g or k not in D.index: continue
    d = D.loc[k]
    games.append(dict(key=k, season=g['season'], y=100 * (g['hs'] - g['as_']) / d.poss, poss=d.poss, neu=bool(d.ff or d.relocated),
                      margin=g['hs'] - g['as_'], phase=g['phase'], utc=g['utc']))
    for side, sg in (('ph', 1), ('pa', -1)):
        tm = sum(p[3] or 0 for p in g[side]) or 200
        for p in g[side]:
            m = p[3] or 0
            if m <= 0: continue
            rows.append(dict(key=k, season=g['season'], pid=p[0], name=p[1], sign=sg, s=m / (tm / 5), min=m,
                             p2m=p[5], p2x=p[6] - p[5], p3m=p[7], p3x=p[8] - p[7], ftm=p[9], ftx=p[10] - p[9],
                             orb=p[11], drb=p[12], ast=p[13], stl=p[14], tov=p[15], blk=p[16], pf=p[17], pir=p[18]))
R = pd.DataFrame(rows); G = pd.DataFrame(games).set_index('key')
SEAS = sorted(G.season.unique())
P(f'ματς Ευρωλιγκας {len(G)} · γραμμες παικτων {len(R)} · σεζον {SEAS[0]}–{SEAS[-1]}')

# ---- στατιστικα παικτη-σεζον ανα 40′ (μαζεμα 100′ προς τον μεσο) ----
M0 = 100.0
agg = R.groupby(['pid', 'season'])[F + ['pir', 'min']].sum()
mu = agg[F + ['pir']].sum() / agg['min'].sum()
X = (agg[F + ['pir']].add(M0 * mu, axis=1)).div(agg['min'] + M0, axis=0) * 40
X['min'] = agg['min']; X['name'] = R.groupby(['pid', 'season']).name.first()

# κεντραρισμα: 0 = μεσος παικτης της σεζον (σταθμιση με λεπτα)
XC = X[F].copy()
for s_ in X.index.get_level_values(1).unique():
    m = X.index.get_level_values(1) == s_
    XC.loc[m] = X.loc[m, F] - np.average(X.loc[m, F], axis=0, weights=X.loc[m, 'min'])
PIRC = X['pir'].copy()
for s_ in X.index.get_level_values(1).unique():
    m = X.index.get_level_values(1) == s_
    PIRC.loc[m] = X.loc[m, 'pir'] - np.average(X.loc[m, 'pir'], weights=X.loc[m, 'min'])

def design(season_list):
    g = G[G.season.isin(season_list)]; r = R[R.key.isin(g.index)]
    gi = {k: i for i, k in enumerate(g.index)}
    return g, r, r.key.map(gi).values, (r.sign * r.s).values

def fit_box(season_list, feats='box'):
    """κοινα βαρη στατιστικων (ή κλιμακα PIR) απο ολες τις season_list."""
    g, r, rr, w = design(season_list); idx = list(zip(r.pid, r.season))
    xs = XC.loc[idx].values if feats == 'box' else PIRC.loc[idx].values[:, None]
    nF = xs.shape[1]
    A = np.zeros((len(g) + nF, 1 + nF)); y = np.zeros(len(g) + nF)
    A[np.arange(len(g)), 0] = (~g.neu.values); y[:len(g)] = g.y.values
    np.add.at(A, (rr[:, None], 1 + np.arange(nF)[None, :]), w[:, None] * xs)
    A[len(g) + np.arange(nF), 1 + np.arange(nF)] = 1.0
    sol = np.linalg.lstsq(A, y, rcond=None)[0]
    return sol[1:]

def box_val(idx, beta, feats):
    return (XC.loc[idx].values @ beta) if feats == 'box' else PIRC.loc[idx].values * beta[0]

def fit_u(season, beta, feats, lam):
    """+/- πανω απο τα στατιστικα, μονο με τα ματς της season (ridge λ)."""
    g, r, rr, w = design([season]); idx = list(zip(r.pid, r.season))
    off = np.zeros(len(g))
    if beta is not None: np.add.at(off, rr, w * box_val(idx, beta, feats))
    ps = list(dict.fromkeys(idx)); pi = {p: i for i, p in enumerate(ps)}
    A = np.zeros((len(g) + len(ps), 1 + len(ps))); y = np.zeros(len(g) + len(ps))
    A[np.arange(len(g)), 0] = (~g.neu.values); y[:len(g)] = g.y.values - off
    np.add.at(A, (rr, 1 + np.array([pi[p] for p in idx])), w)
    A[len(g) + np.arange(len(ps)), 1 + np.arange(len(ps))] = math.sqrt(lam)
    sol = np.linalg.lstsq(A, y, rcond=None)[0]
    return dict(zip(ps, sol[1:]))

def season_values(season, beta, feats, u):
    idx = [i for i in X.index if i[1] == season]
    b = box_val(idx, beta, feats) if beta is not None else np.zeros(len(idx))
    return {i[0]: float(bv) + (u.get(i, 0.0) if u else 0.0) for i, bv in zip(idx, b)}

def raw_pred(season, val, repl):
    g, r, rr, w = design([season])
    v = r.pid.map(val).fillna(repl).values
    raw = np.zeros(len(g)); np.add.at(raw, rr, w * v)
    return g, raw

VARIANTS = [('PIR', 'pir', False, None), ('μονο στατιστικα', 'box', False, None), ('μονο +/- (λ 15)', None, True, 15)] + \
           [(f'στατιστικα + +/- (λ {l})', 'box', True, l) for l in (5, 15, 40)]
TEST = [s for s in SEAS if s >= 'E2019']
seen = set(); firsts = {}
for s in SEAS:
    ps = set(R[R.season == s].pid); firsts[s] = ps - seen; seen |= ps

OOS = {}
for lab, feats, use_u, lam in VARIANTS:
    for Y in TEST:
        tr = [t for t in SEAS if t != Y]
        beta = fit_box(tr, feats) if feats else None
        vals = {t: season_values(t, beta, feats, fit_u(t, beta, feats, lam) if use_u else None) for t in SEAS if t != Y}
        fv, fm = [], []
        for t in tr:
            for p in firsts[t]:
                if t == SEAS[0] or p not in vals[t]: continue
                fv.append(vals[t][p]); fm.append(X.loc[(p, t), 'min'])
        repl = float(np.average(fv, weights=fm))
        prev = SEAS[SEAS.index(Y) - 1]
        g, raw = raw_pred(Y, vals[prev], repl)
        OOS[(lab, Y)] = (g, raw)

P('')
P('=== ΤΕΣΤ: ματς σεζον Y με αξιες σεζον Y−1 + πραγματικα λεπτα · RMSE διαφορας (ποντοι) και συσχετιση ===')
P('  (εδρα + «ποσο κρατιεται» η περσινη αξια = k, μετρημενα στις ΑΛΛΕΣ σεζον-τεστ)')
P(f'{"":30s} ' + ' '.join(f'{s[-4:]:>12s}' for s in TEST) + f' {"ΟΛΑ":>14s}   k')
summary = {}
for lab, *_ in VARIANTS:
    E, PA, AA, cells, ks = [], [], [], [], []
    for Y in TEST:
        oth = [t for t in TEST if t != Y]
        gg = pd.concat([OOS[(lab, t)][0] for t in oth]); rw = np.concatenate([OOS[(lab, t)][1] for t in oth])
        A = np.column_stack([(~gg.neu.values).astype(float), rw]); h, k = np.linalg.lstsq(A, gg.y.values, rcond=None)[0]
        g, raw = OOS[(lab, Y)]
        pr = (np.where(g.neu, 0, h) + k * raw) * g.poss.values / 100; act = g.margin.values
        E.append(act - pr); PA.append(pr); AA.append(act); ks.append(k)
        cells.append(f'{np.sqrt(np.mean((act - pr) ** 2)):5.2f} ({np.corrcoef(pr, act)[0, 1]:.2f})')
    e = np.concatenate(E); summary[lab] = np.sqrt(np.mean(e ** 2))
    P(f'{lab:30s} ' + ' '.join(f'{c:>12s}' for c in cells) + f' {summary[lab]:6.2f} ({np.corrcoef(np.concatenate(PA), np.concatenate(AA))[0,1]:.2f})  {np.mean(ks):.2f}')
gT = G[G.season.isin(TEST)]
P(f'  αναφορα: μονο εδρα RMSE {np.sqrt(np.mean((gT.margin.values - np.where(gT.neu, 0, gT.margin.mean()))**2)):.2f}')
v1 = ns['run']()[:, 0]; Dk = ns['D'].reset_index(drop=True)
mm = Dk.key.isin(gT.index).values
P(f'  αναφορα: μοντελο ομαδων v1 (walk-forward, ΧΩΡΙΣ να ξερει ποιοι επαιξαν) RMSE {np.sqrt(np.mean((Dk.hs - Dk.as_ - v1)[mm] ** 2)):.2f}')

best = min(VARIANTS, key=lambda v: summary[v[0]])
P('')
P(f'καλυτερη παραλλαγη: {best[0]}')
lab, feats, use_u, lam = best
beta = fit_box(SEAS, feats) if feats else None
if feats == 'box':
    P('βαρη στατιστικων (π./100 κατοχες ανα +1 στατιστικο ανα 40′ πανω απο τον μεσο): ' + ' · '.join(f'{f} {b:+.2f}' for f, b in zip(F, beta)))
vals = []
for s in SEAS:
    uu = fit_u(s, beta, feats, lam) if use_u else {}
    for i in [i for i in X.index if i[1] == s]:
        bv = float(box_val([i], beta, feats)[0]) if beta is not None else 0.0
        vals.append(dict(pid=i[0], season=s, name=X.loc[i, 'name'], min=X.loc[i, 'min'], value=bv + uu.get(i, 0.0), box=bv, pm=uu.get(i, 0.0), pir40=X.loc[i, 'pir']))
V = pd.DataFrame(vals); V.to_csv('el_player_values_v2.csv', index=False)
top = V[(V.season == 'E2025') & (V['min'] >= 600)]
P('κορυφαιοι 2025-26 (≥600′): ' + ' · '.join(f'{r.name.title()} {r.value:+.1f}' for r in top.sort_values('value', ascending=False).head(15).itertuples()))
P('χαμηλοτεροι 2025-26 (≥600′): ' + ' · '.join(f'{r.name.title()} {r.value:+.1f}' for r in top.sort_values('value').head(8).itertuples()))
P(f'ευρος (≥600′, 1%/50%/99%): {V[V["min"] >= 600].value.quantile([.01, .5, .99]).round(1).tolist()}')
open('el_player_value2_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ==== ΑΡΧΗ ΣΕΖΟΝ: περσινη εικονα ΟΜΑΔΑΣ vs περσινη αξια ΠΑΙΚΤΩΝ του τωρινου ροστερ vs συνδυασμος ====
P('')
P('=== ΑΡΧΗ ΣΕΖΟΝ (καμια φετινη πληροφορια): ομαδα περσι · παικτες περσι · συνδυασμος — RMSE διαφορας ===')
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
lab_b = best[0]
rows2 = []
for Y in TEST:
    prev = SEAS[SEAS.index(Y) - 1]; te = team_end(prev)
    g, raw = OOS[(lab_b, Y)]
    tp = np.array([te.get(D.loc[k, 'home'], 0.0) - te.get(D.loc[k, 'away'], 0.0) for k in g.index])
    for k, a, b in zip(g.index, tp, raw):
        rows2.append(dict(key=k, season=Y, team=a, play=b, home=float(not g.loc[k, 'neu']), y=g.loc[k, 'y'], poss=g.loc[k, 'poss'], margin=g.loc[k, 'margin'], rnd=RN[k]))
Q = pd.DataFrame(rows2)
res = {m: [] for m in ('ομαδα περσι', 'παικτες περσι', 'συνδυασμος')}
coefs = []
for Y in TEST:
    tr, te_ = Q[Q.season != Y], Q[Q.season == Y]
    for m, cols in (('ομαδα περσι', ['home', 'team']), ('παικτες περσι', ['home', 'play']), ('συνδυασμος', ['home', 'team', 'play'])):
        c = np.linalg.lstsq(tr[cols].values, tr.y.values, rcond=None)[0]
        if m == 'συνδυασμος': coefs.append(c)
        pr = te_[cols].values @ c * te_.poss.values / 100
        res[m].append(pd.DataFrame(dict(e=te_.margin.values - pr, rnd=te_.rnd.values, season=Y)))
for m, L in res.items():
    E = pd.concat(L)
    per = ' '.join(f'{s[-2:]}:{np.sqrt(np.mean(E[(E.season == s) & (E.rnd <= 10)].e ** 2)):.2f}' for s in TEST)
    P(f'  {m:16s} αγων 1-10 {np.sqrt(np.mean(E[E.rnd <= 10].e ** 2)):.2f} · αγων 11+ {np.sqrt(np.mean(E[E.rnd > 10].e ** 2)):.2f} · ολη {np.sqrt(np.mean(E.e ** 2)):.2f}  | αγων 1-10 ανα σεζον {per}')
c = np.mean(coefs, axis=0)
P(f'  συνδυασμος: βαρος ομαδας {c[1]:.2f} · βαρος παικτων {c[2]:.2f}  (μεσος ορος των LOSO προσαρμογων)')
open('el_player_value2_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
