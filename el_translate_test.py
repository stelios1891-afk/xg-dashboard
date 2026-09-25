# -*- coding: utf-8 -*-
"""el_translate_test.py — ΒΗΜΑ 2: «ΜΕΤΑΦΡΑΣΗ» παικτων απο αλλα πρωταθληματα στην Ευρωλιγκα + ξανα το τεστ Γ (25/9/2026).
(Στελιος: «μπηκαμε σε συγκριση χωρις να εχουμε μεταφρασει NBA/EuroCup κτλ» — σωστα: ως τωρα οι νεοφερμενοι ηταν «μεσος ορος».)

ΑΞΙΑ ΣΤΑΤΙΣΤΙΚΩΝ σε αλλο πρωταθλημα L, σεζον Y−1: ιδιοι ρυθμοι ανα 40′ (2P/3P/ΒΟΛΕΣ ευστ./αστ., ΕΡ/ΑΡ, ΑΣ, ΚΛ, ΚΟ, ΛΑ, ΦΑ,
  μαζεμα 100′), ιδια βαρη β της Ευρωλιγκας.
ΜΕΤΑΦΡΑΣΗ ανα πρωταθλημα: αξια στην Ευρωλιγκα (σεζον Y, στατιστικα) = a_L + b_L × αξια στο L (Y−1)· απο ολους τους παικτες που
  εκαναν αυτη τη μεταβαση (≥300′ Ευρωλιγκα)· μαζεμα a_L, b_L προς τον κοινο μεσο (λιγα ζευγη = πιο κοντα στον κοινο).
  Πηγες: EuroCup (επισημο API) · NBA/G League/ACB/Ιταλια/Γαλλια/Ελλαδα/Τουρκια/Ισραηλ/ABA/Κινα/Αυστραλια (Basketball-Reference).
ΟΛΑ LOSO: για τη σεζον-τεστ Y, βαρη β και μεταφραση μετρημενα ΧΩΡΙΣ τη Y.
ΤΕΣΤ Γ ξανα (2021-2025, αγων 1-10, πραγματικα λεπτα): «δικη μας» = Ευρωλιγκα περσι + μεταφρασμενοι νεοφερμενοι.
Εξοδος: el_translate_test_out.txt"""
import sys, math, json
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_3s_rating_test.py', encoding='utf-8').read().split('MODELS = [')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
exec(ex[ex.index('RANK = {'):ex.index('ES = list(RANK)')])

# ---------- στατιστικα αλλων πρωταθληματων (Y−1) για οσους δεν εχουν Ευρωλιγκα Y−1 ----------
PLJ = json.load(open('el_players.json', encoding='utf-8'))
ec = []
for k, g in PLJ.items():
    if g.get('comp') != 'U' or 'err' in g or 'ph' not in g: continue
    for side in ('ph', 'pa'):
        for p in g[side]:
            if not p[3]: continue
            ec.append(dict(pid=p[0], yr=int(g['season'][1:]), min=p[3], p2m=p[5], p2x=p[6] - p[5], p3m=p[7], p3x=p[8] - p[7], ftm=p[9], ftx=p[10] - p[9],
                           orb=p[11], drb=p[12], ast=p[13], stl=p[14], tov=p[15], blk=p[16], pf=p[17]))
EC = pd.DataFrame(ec).groupby(['pid', 'yr']).sum().reset_index(); EC['league'] = 'eurocup'
BRT = pd.read_csv('bbref_totals.csv')
MAP = pd.read_csv('el_bbref_map.csv')
MAP = MAP[(MAP.how != '—') & MAP.league.notna() & (MAP.league != 'ncaa') & (MAP.league != 'eurocup')]
br = MAP.merge(BRT, left_on=['bbref_pid', 'league', 'season'], right_on=['pid', 'league', 'season_end'], how='left', suffixes=('', '_b'))
br = br.sort_values('mp_b', ascending=False).drop_duplicates(['el_pid', 'season'])
BR2 = pd.DataFrame(dict(pid=br.el_pid, yr=br.season - 1, league=br.league, min=br.mp_b, p2m=br.fg2, p2x=br.fg2a - br.fg2, p3m=br.fg3, p3x=br.fg3a - br.fg3,
                        ftm=br.ft, ftx=br.fta - br.ft, orb=br.orb, drb=br.drb, ast=br.ast, stl=br.stl, tov=br.tov, blk=br.blk, pf=br.pf)).dropna()
SRC = pd.concat([EC, BR2], ignore_index=True)
SRC = SRC[SRC['min'] >= 100]
ELMU = {s: np.average(X.loc[X.index.get_level_values(1) == s, F], axis=0, weights=X.loc[X.index.get_level_values(1) == s, 'min']) for s in SEAS}
def src_value(row, beta):
    rates = (row[F].values.astype(float) + 100 * mu[F].values) / (row['min'] + 100) * 40
    s = f"E{int(row['yr'])}"; m = ELMU.get(s, ELMU[SEAS[-1]])
    return float((rates - m) @ beta)

EL_MIN = X['min']
def translation(beta, excl):
    """ζευγη: πηγη Y−1 (οχι Ευρωλιγκα) → Ευρωλιγκα Y (στατιστικα, ≥300′)· εκτος σεζον excl."""
    rows = []
    for r in SRC.itertuples(index=False):
        s1 = f'E{int(r.yr) + 1}'
        if s1 == excl or (r.pid, s1) not in X.index or EL_MIN[(r.pid, s1)] < 300: continue
        if (r.pid, f'E{int(r.yr)}') in X.index and EL_MIN[(r.pid, f'E{int(r.yr)}')] >= 100: continue   # επαιξε και EL την Y−1
        rows.append(dict(league=r.league, x=src_value(pd.Series(r._asdict()), beta), y=float(box_val([(r.pid, s1)], beta, 'box')[0])))
    Z = pd.DataFrame(rows)
    A = np.column_stack([np.ones(len(Z)), Z.x]); a0, b0 = np.linalg.lstsq(A, Z.y, rcond=None)[0]
    coef = {}
    for L, z in Z.groupby('league'):
        n = len(z); lam = 15.0
        Aw = np.vstack([np.column_stack([np.ones(n), z.x]), math.sqrt(lam) * np.eye(2)]); yw = np.concatenate([z.y, math.sqrt(lam) * np.array([a0, b0])])
        coef[L] = (*np.linalg.lstsq(Aw, yw, rcond=None)[0], n, np.corrcoef(z.x, z.y)[0, 1] if n > 2 else np.nan)
    return coef, (a0, b0), Z

beta_all = fit_box(SEAS, 'box')
coef, pooled, Z = translation(beta_all, None)
P('=== ΜΕΤΑΦΡΑΣΗ ανα πρωταθλημα (ολες οι σεζον): αξια Ευρωλιγκας ≈ a + b × αξια στο πρωταθλημα την προηγουμενη χρονια ===')
P('  (αξια = π./100 κατοχες πανω απο τον μεσο παικτη Ευρωλιγκας· b = ποσο «περναει»· συσχ. = ποσο προβλεπει)')
for L, (a, b, n, r) in sorted(coef.items(), key=lambda kv: -kv[1][2]):
    P(f'  {L:22s} ζευγη {n:3d} · a {a:+.2f} · b {b:.2f} · συσχετιση {r:.2f}')
P(f'  κοινο: a {pooled[0]:+.2f} · b {pooled[1]:.2f} · ζευγη {len(Z)}')
V2 = pd.DataFrame([dict(pid=i[0], s=i[1]) for i in X.index if X.loc[i, 'min'] >= 300])
pairs = []
for s0, s1 in zip(SEAS[:-1], SEAS[1:]):
    a = [p for p in V2[V2.s == s0].pid if (p, s1) in X.index and X.loc[(p, s1), 'min'] >= 300]
    if a: pairs.append(pd.DataFrame(dict(x=box_val([(p, s0) for p in a], beta_all, 'box'), y=box_val([(p, s1) for p in a], beta_all, 'box'))))
PP = pd.concat(pairs); bE = np.polyfit(PP.x, PP.y, 1)
P(f'  (συγκριση: Ευρωλιγκα → Ευρωλιγκα ιδιος παικτης: b {bE[0]:.2f} · συσχετιση {np.corrcoef(PP.x, PP.y)[0,1]:.2f} · ζευγη {len(PP)})')

# ---------- χαρακτηριστικα ανα ματς για το τεστ ----------
TEST5 = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
ENDS = {s: np.sort(np.array(list(team_end(s).values())))[::-1] for s in SEAS}
def exp_rating(s, rank, N):
    q = (rank - 0.5) / N
    return float(np.mean([np.interp(q, (np.arange(len(ENDS[r])) + .5) / len(ENDS[r]), ENDS[r]) for r in SEAS if r != s and r >= 'E2018']))
EX = {(s, t): exp_rating(s, r_, len(rk)) for s, rk in RANK.items() for t, r_ in rk.items()}
rows = []; cov = []
for Y in TEST5:
    beta = fit_box([t for t in SEAS if t != Y], 'box')
    cf, pl, _ = translation(beta, Y)
    valEL = vals_for(Y, '2σ', 15, beta)
    src = SRC[SRC.yr == int(Y[1:]) - 1]
    valTR = {}
    for r in src.sort_values('min').itertuples(index=False):
        if r.pid in valEL: continue
        a, b = (cf[r.league][:2] if r.league in cf else pl)
        valTR[r.pid] = a + b * src_value(pd.Series(r._asdict()), beta)
    g, r_, rr, w = design([Y])
    kEL = r_.pid.isin(valEL).values; kTR = r_.pid.isin(valTR).values
    vEL = r_.pid.map(valEL).fillna(0).values; vTR = r_.pid.map(valTR).fillna(0).values
    f = {}
    for nm, arr in (('el', w * vEL), ('tr', w * vTR), ('unk_old', w * (~kEL)), ('unk_new', w * (~kEL & ~kTR))):
        f[nm] = np.zeros(len(g)); np.add.at(f[nm], rr, arr)
    aw = np.abs(w)
    cov.append(f'{Y[-2:]}: EL {np.average(kEL, weights=aw):.0%} · +μεταφρ. {np.average(kEL | kTR, weights=aw):.0%}')
    base = Q.set_index('key')
    for j, k in enumerate(g.index):
        rows.append(dict(key=k, season=Y, rnd=RN[k], home=float(not g.loc[k, 'neu']), y=g.loc[k, 'y'], poss=g.loc[k, 'poss'], margin=g.loc[k, 'margin'],
                         team=base.loc[k, 'team'], rA=base.loc[k, 'rA'], uA=base.loc[k, 'uA'],
                         exp=EX.get((Y, D.loc[k, 'home']), np.nan) - EX.get((Y, D.loc[k, 'away']), np.nan),
                         el=f['el'][j], tr=f['tr'][j], unk_old=f['unk_old'][j], unk_new=f['unk_new'][j]))
    print(f'  {Y} ετοιμο', flush=True)
Q2 = pd.DataFrame(rows)
P('')
P('καλυψη λεπτων με αξια παικτη: ' + ' | '.join(cov))
MODELS = [('ομαδα', ['team']),
          ('ομαδα + δικη μας (μονο EL, παλια)', ['team', 'el', 'unk_old']),
          ('ομαδα + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ', ['team', 'el', 'tr', 'unk_new']),
          ('δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ μονο', ['el', 'tr', 'unk_new']),
          ('ειδικοι μονο', ['exp']),
          ('ομαδα + ειδικοι', ['team', 'exp']),
          ('ομαδα + ειδικοι + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ', ['team', 'exp', 'el', 'tr', 'unk_new']),
          ('ομαδα + ειδικοι + μεταφρ. + 3steps', ['team', 'exp', 'el', 'tr', 'unk_new', 'rA', 'uA'])]
PRED = {}
P('')
P('=== ΤΕΣΤ Γ ξανα — RMSE διαφορας (ποντοι), αγων 1-10, 2021-2025, βαρη LOSO ===')
for m, cols in MODELS:
    E, cs = [], []
    for Y in TEST5:
        tr, te_ = Q2[Q2.season != Y], Q2[Q2.season == Y]
        c = np.linalg.lstsq(tr[['home'] + cols].values, tr.y.values, rcond=None)[0]; cs.append(c)
        pr = te_[['home'] + cols].values @ c * te_.poss.values / 100
        E.append(pd.DataFrame(dict(e=te_.margin.values - pr, pr=pr, rnd=te_.rnd.values, season=Y, key=te_.key.values)))
    E = pd.concat(E).set_index('key'); PRED[m] = E; e10 = E[E.rnd <= 10]
    P(f'  {m:40s} 1-10 {np.sqrt(np.mean(e10.e ** 2)):.2f} · ολη {np.sqrt(np.mean(E.e ** 2)):.2f} | ' +
      ' '.join(f'{Y[-2:]}:{np.sqrt(np.mean(e10[e10.season == Y].e ** 2)):.2f}' for Y in TEST5) + f' | βαρη {np.round(np.mean(cs, axis=0)[1:], 2).tolist()}')
P('')
P('=== ΖΕΥΓΑΡΩΤΑ (ιδια ματς αγων 1-10): βελτιωση τετραγωνικου λαθους ===')
for base_m, m in (('ομαδα', 'ομαδα + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ'), ('ομαδα + δικη μας (μονο EL, παλια)', 'ομαδα + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ'),
                  ('ομαδα + ειδικοι', 'ομαδα + ειδικοι + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ'), ('ομαδα + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ', 'ομαδα + ειδικοι + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ'),
                  ('ομαδα + ειδικοι', 'ομαδα + δικη μας ΜΕ ΜΕΤΑΦΡΑΣΗ')):
    b10 = PRED[base_m][PRED[base_m].rnd <= 10]; x = PRED[m].loc[b10.index]; d = b10.e ** 2 - x.e ** 2
    wins = sum(1 for Y in TEST5 if np.mean(x[x.season == Y].e ** 2) < np.mean(b10[b10.season == Y].e ** 2))
    P(f'  «{m}» vs «{base_m}»: {d.mean():+.2f} (t {d.mean() / (d.std(ddof=1) / math.sqrt(len(d))):+.2f}) · καλυτερο σε {wins}/5')
P('')
P('=== ΕΛΛΕΙΨΗ ΠΛΗΡΟΦΟΡΙΑΣ (ποντοι): y = πραγματικη − v1 · x = προβλεψη − «ομαδα» · αγων 1-10 ===')
v1 = ns['run']()[:, 0]; Dk = ns['D'].reset_index(drop=True); V1 = dict(zip(Dk.key, v1))
b0 = PRED['ομαδα']; b0 = b0[b0.rnd <= 10]; yv = Q2.set_index('key').loc[b0.index, 'margin'] - b0.index.map(V1)
for m, _ in MODELS[1:]:
    e1 = PRED[m].loc[b0.index]; x = e1.pr - b0.pr
    b = np.polyfit(x, yv, 1)[0]; res = yv - b * x
    se = math.sqrt(np.sum((res - res.mean()) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    pos = sum(1 for Y in TEST5 if np.polyfit(x[e1.season == Y], yv[e1.season == Y], 1)[0] > 0)
    P(f'  {m:40s} κλιση {b:+.2f} (t {b/se:+.1f}) · θετικη σε {pos}/5')
open('el_translate_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
