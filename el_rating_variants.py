# -*- coding: utf-8 -*-
"""el_rating_variants.py — ΠΩΣ ΜΕΤΑΤΡΕΠΟΥΜΕ ΣΤΑΤΙΣΤΙΚΑ ΣΕ RATING ΠΑΙΚΤΗ: συγκριση παραλλαγων (25/9/2026, αιτημα Στελιου).

ΠΑΡΑΛΛΑΓΕΣ (ολες ανα 40′, μαζεμα 100′ προς τον μεσο· 0 = μεσος παικτης Ευρωλιγκας της σεζον):
  PIR · Game Score (Hollinger, σταθερα βαρη) ·
  «ιδια χρονια»: βαρη που εξηγουν τη διαφορα σκορ της ιδιας σεζον (οπως ως τωρα) — απλα στατιστικα / με ΡΟΛΟ
  «επομενη χρονια»: βαρη που κανουν τα περσινα στατιστικα να προβλεπουν τα φετινα αποτελεσματα — απλα / με ΡΟΛΟ / + λεπτα & βασικος
  «λεπτα & βασικος»: μονο ποσο παιζει και αν ξεκιναει (η «γνωμη» του προπονητη)
  ΡΟΛΟΣ = ποντοι πανω απο την ευστοχια της λιγκας (αντι «καθε αστοχο = ποινη») + ογκος επιθεσεων που κλεινει (usage) + ΑΣ, ΕΡ, ΑΡ, ΚΛ, ΚΟ, ΛΑ, ΦΑ.
ΝΕΟΦΕΡΜΕΝΟΙ: το ιδιο rating στο προηγουμενο πρωταθλημα (EuroCup/NBA/G League/ACB/…) → μεταφραση a_L + b_L·rating (ανα παραλλαγη).
ΤΕΣΤ: σεζον Y (2021-2025) · rating περσι × πραγματικα λεπτα · + «ομαδα περσι» (+ «ειδικοι») · βαρη ΚΑΙ μεταφραση LOSO (χωρις τη Y).
ΜΕΤΡΑ: RMSE διαφορας αγων 1-10 & ολη · ζευγαρωτα vs «ομαδα» και vs «ομαδα+ειδικοι» · σταθεροτητα rating Y→Y+1 (≥600′).
Εξοδος: el_rating_variants_out.txt"""
import sys, math, json
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
exec(ex[ex.index('RANK = {'):ex.index('ES = list(RANK)')])

# ---------------- πινακας στατιστικων παικτη-σεζον (EL, EuroCup, B-R νεοφερμενοι) ----------------
PLJ = json.load(open('el_players.json', encoding='utf-8'))
BOX = ['p2m', 'p2a', 'p3m', 'p3a', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf']
acc = {}
for k, g in PLJ.items():
    if 'err' in g or 'ph' not in g or g.get('comp') not in ('E', 'U'): continue
    for side in ('ph', 'pa'):
        for p in g[side]:
            if not p[3] or p[3] <= 0: continue
            key_ = (p[0], g['season'][1:], 'euroleague' if g['comp'] == 'E' else 'eurocup')
            a = acc.setdefault(key_, dict(min=0, g=0, st=0, **{b: 0 for b in BOX}))
            a['min'] += p[3]; a['g'] += 1; a['st'] += 1 if p[2] else 0
            for b, i in zip(BOX, (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 15, 17)): a[b] += p[i] or 0
FT = pd.DataFrame([dict(pid=k[0], yr=int(k[1]), league=k[2], **v) for k, v in acc.items()])
BRT = pd.read_csv('bbref_totals.csv'); MAP = pd.read_csv('el_bbref_map.csv')
MAP = MAP[(MAP.how != '—') & MAP.league.notna() & ~MAP.league.isin(['ncaa', 'eurocup', 'euroleague'])]
br = MAP.merge(BRT, left_on=['bbref_pid', 'league', 'season'], right_on=['pid', 'league', 'season_end'], how='left', suffixes=('', '_b'))
br = br.sort_values('mp_b', ascending=False).drop_duplicates(['el_pid', 'season']).dropna(subset=['mp_b'])
FB = pd.DataFrame(dict(pid=br.el_pid, yr=br.season - 1, league=br.league, min=br.mp_b, g=br.g_b if 'g_b' in br else br.g, st=np.nan,
                       p2m=br.fg2, p2a=br.fg2a, p3m=br.fg3, p3a=br.fg3a, ftm=br.ft, fta=br.fta, orb=br.orb, drb=br.drb, ast=br.ast, stl=br.stl,
                       blk=br.blk, tov=br.tov, pf=br.pf))
FT = pd.concat([FT, FB], ignore_index=True)
FT = FT[FT['min'] >= 60].copy()
ELT = FT[FT.league == 'euroleague']
MU = ELT[BOX].sum() / ELT['min'].sum()                      # μεσος ρυθμος ανα λεπτο Ευρωλιγκας
for b in BOX: FT[b + '_r'] = (FT[b] + 100 * MU[b]) / (FT['min'] + 100) * 40
r = lambda b: FT[b + '_r']
LTS = float((2 * MU.p2m + 3 * MU.p3m + MU.ftm) / (MU.p2a + MU.p3a + 0.44 * MU.fta))   # ποντοι ανα «προσπαθεια» Ευρωλιγκας
FT['pts'] = 2 * r('p2m') + 3 * r('p3m') + r('ftm')
FT['tsa'] = r('p2a') + r('p3a') + 0.44 * r('fta')
FT['pts_above'] = FT.pts - LTS * FT.tsa
FT['usage'] = FT.tsa + r('tov')
FT['mpg'] = FT['min'] / FT.g.clip(lower=1)
FT['start'] = FT.st / FT.g.clip(lower=1)
FT['pir'] = FT.pts + r('orb') + r('drb') + r('ast') + r('stl') + r('blk') - (r('p2a') - r('p2m')) - (r('p3a') - r('p3m')) - (r('fta') - r('ftm')) - r('tov') - r('pf')
FT['gmsc'] = FT.pts + 0.4 * (r('p2m') + r('p3m')) - 0.7 * (r('p2a') + r('p3a')) - 0.4 * (r('fta') - r('ftm')) + 0.7 * r('orb') + 0.3 * r('drb') + r('stl') + 0.7 * r('ast') + 0.7 * r('blk') - 0.4 * r('pf') - r('tov')
SIMPLE = [b + '_r' for b in BOX]
ROLE = ['pts_above', 'usage', 'ast_r', 'orb_r', 'drb_r', 'stl_r', 'blk_r', 'tov_r', 'pf_r']
FT['start'] = FT.start.fillna(FT[FT.league == 'eurocup'].start.mean())
FT['season'] = 'E' + FT.yr.astype(int).astype(str)
FT = FT.set_index(['pid', 'season', 'league']).sort_index()
ELF = FT.xs('euroleague', level=2)

# κεντραρισμα ανα σεζον Ευρωλιγκας (σταθμιση λεπτα) — οι αλλες λιγκες κεντραρονται με τον μεσο της EL ιδιας σεζον
def centered(cols):
    Mx = {s: np.average(ELF.xs(s, level=1)[cols], axis=0, weights=ELF.xs(s, level=1)['min']) for s in ELF.index.get_level_values(1).unique()}
    last = Mx[max(Mx)]
    return FT[cols].values - np.array([Mx.get(s, last) for s in FT.index.get_level_values(1)])

TEST5 = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
def fit_same(cols, excl):
    """βαρη ιδιας χρονιας: διαφορα/100 αγωνα = εδρα + Σ s·(β·x) — x = στατιστικα της ιδιας σεζον (EL)."""
    C = pd.DataFrame(centered(cols), index=FT.index, columns=cols).xs('euroleague', level=2)
    g, r_, rr, w = design([s for s in SEAS if s != excl])
    xs = C.reindex(list(zip(r_.pid, r_.season))).fillna(0).values
    A = np.zeros((len(g) + len(cols), 1 + len(cols))); y = np.zeros(A.shape[0])
    A[np.arange(len(g)), 0] = ~g.neu.values; y[:len(g)] = g.y.values
    np.add.at(A, (rr[:, None], 1 + np.arange(len(cols))[None, :]), (w[:, None] * xs))
    A[len(g) + np.arange(len(cols)), 1 + np.arange(len(cols))] = 1.0
    return np.linalg.lstsq(A, y, rcond=None)[0][1:]
def fit_next(cols, excl):
    """βαρη επομενης χρονιας: διαφορα στη σεζον t = εδρα + Σ s·(β·x_{t−1}) + γ·(λεπτα αγνωστων) — t, t−1 ≠ excl."""
    C = pd.DataFrame(centered(cols), index=FT.index, columns=cols).xs('euroleague', level=2)
    A_all, y_all = [], []
    for t in SEAS[1:]:
        p = SEAS[SEAS.index(t) - 1]
        if excl in (t, p): continue
        g, r_, rr, w = design([t]); idx = list(zip(r_.pid, [p] * len(r_)))
        xs = C.reindex(idx); known = xs.notna().all(axis=1).values; xs = xs.fillna(0).values
        A = np.zeros((len(g), 2 + len(cols))); A[:, 0] = ~g.neu.values
        np.add.at(A, (rr[:, None], 2 + np.arange(len(cols))[None, :]), w[:, None] * xs)
        np.add.at(A[:, 1], rr, w * ~known)
        A_all.append(A); y_all.append(g.y.values)
    A = np.vstack(A_all + [np.hstack([np.zeros((len(cols), 2)), np.eye(len(cols))])]); y = np.concatenate(y_all + [np.zeros(len(cols))])
    return np.linalg.lstsq(A, y, rcond=None)[0][2:]

VARIANTS = [('PIR', 'fixed', ['pir'], None), ('Game Score', 'fixed', ['gmsc'], None),
            ('ιδια χρονια · απλα', 'same', SIMPLE, None), ('ιδια χρονια · ρολος', 'same', ROLE, None),
            ('επομενη χρονια · απλα', 'next', SIMPLE, None), ('επομενη χρονια · ρολος', 'next', ROLE, None),
            ('λεπτα & βασικος', 'next', ['mpg', 'start'], None),
            ('επομενη · ρολος + λεπτα & βασικος', 'next', ROLE + ['mpg', 'start'], None)]
TE = {Y: team_end(SEAS[SEAS.index(Y) - 1]) for Y in TEST5}
ENDS = {s: np.sort(np.array(list(team_end(s).values())))[::-1] for s in SEAS}
def exp_rating(s, rank, N):
    q = (rank - 0.5) / N
    return float(np.mean([np.interp(q, (np.arange(len(ENDS[r_])) + .5) / len(ENDS[r_]), ENDS[r_]) for r_ in SEAS if r_ != s and r_ >= 'E2018']))
EX = {(s, t): exp_rating(s, rk_, len(rk)) for s, rk in RANK.items() for t, rk_ in rk.items()}

def ratings_for(cols, beta):
    return pd.Series(centered(cols) @ beta, index=FT.index)

def translate(rat, excl):
    """αγνωστοι νεοφερμενοι: rating στο αλλο πρωταθλημα (Y−1) → rating Ευρωλιγκας (Y)· ζευγη χωρις excl."""
    el = rat.xs('euroleague', level=2); rows = []
    for (pid, s, L), v in rat.items():
        if L == 'euroleague': continue
        s1 = f'E{int(s[1:]) + 1}'
        if s1 == excl or (pid, s1) not in el.index or ELF.loc[(pid, s1), 'min'] < 300: continue
        if (pid, s) in el.index and ELF.loc[(pid, s), 'min'] >= 100: continue
        rows.append((L, v, el[(pid, s1)]))
    Z = pd.DataFrame(rows, columns=['L', 'x', 'y'])
    a0, b0 = np.polyfit(Z.x, Z.y, 1)[::-1]; cf = {}
    for L, z in Z.groupby('L'):
        n = len(z); A = np.vstack([np.column_stack([np.ones(n), z.x]), math.sqrt(15) * np.eye(2)]); yv = np.concatenate([z.y, math.sqrt(15) * np.array([a0, b0])])
        cf[L] = np.linalg.lstsq(A, yv, rcond=None)[0]
    return cf, (a0, b0), np.corrcoef(Z.x, Z.y)[0, 1]

res = {}
for lab, kind, cols, _ in VARIANTS:
    rows = []; corr_tr = []
    for Y in TEST5:
        if kind == 'fixed': beta = np.array([1.0])
        elif kind == 'same': beta = fit_same(cols, Y)
        else: beta = fit_next(cols, Y)
        rat = ratings_for(cols, beta)
        cf, pl, ct = translate(rat, Y); corr_tr.append(ct)
        prev = SEAS[SEAS.index(Y) - 1]; pp = SEAS[SEAS.index(Y) - 2]
        el = rat.xs('euroleague', level=2)
        val = {}
        for s_ in (pp, prev):                                   # Y−1 υπερισχυει, Y−2 για οσους ελειψαν
            if s_ in el.index.get_level_values(1): val.update(el.xs(s_, level=1).to_dict())
        other = rat[(rat.index.get_level_values(1) == prev) & (rat.index.get_level_values(2) != 'euroleague')]
        for (pid, s_, L), v in other.sort_values().items():
            if pid in val: continue
            a, b = cf.get(L, pl); val[pid] = a + b * v
        g, r_, rr, w = design([Y])
        known = r_.pid.isin(val).values; v = r_.pid.map(val).fillna(0).values
        pl_ = np.zeros(len(g)); np.add.at(pl_, rr, w * v)
        uk = np.zeros(len(g)); np.add.at(uk, rr, w * ~known)
        te = TE[Y]
        for j, k in enumerate(g.index):
            rows.append(dict(key=k, season=Y, rnd=RN[k], home=float(not g.loc[k, 'neu']), y=g.loc[k, 'y'], poss=g.loc[k, 'poss'], margin=g.loc[k, 'margin'],
                             team=te.get(D.loc[k, 'home'], 0.0) - te.get(D.loc[k, 'away'], 0.0), pl=pl_[j], uk=uk[j],
                             exp=EX.get((Y, D.loc[k, 'home']), np.nan) - EX.get((Y, D.loc[k, 'away']), np.nan)))
    Qv = pd.DataFrame(rows)
    # σταθεροτητα (με βαρη ολων των σεζον)
    beta_all = np.array([1.0]) if kind == 'fixed' else (fit_same(cols, None) if kind == 'same' else fit_next(cols, None))
    ra = ratings_for(cols, beta_all).xs('euroleague', level=2)
    pr = []
    for s0, s1 in zip(SEAS[:-1], SEAS[1:]):
        a = [p for p in ra.xs(s0, level=1).index if (p, s1) in ra.index and ELF.loc[(p, s0), 'min'] >= 600 and ELF.loc[(p, s1), 'min'] >= 600]
        pr += [(ra[(p, s0)], ra[(p, s1)]) for p in a]
    stab = np.corrcoef(np.array(pr).T)[0, 1]
    res[lab] = dict(Q=Qv, stab=stab, ctr=np.mean(corr_tr),
                    w=dict(zip(cols, np.round(beta_all, 2))) if kind != 'fixed' else {})
    print(f'  {lab} ετοιμο', flush=True)

def evaluate(Qv, cols):
    E = []
    for Y in TEST5:
        tr, te_ = Qv[Qv.season != Y], Qv[Qv.season == Y]
        c = np.linalg.lstsq(tr[['home'] + cols].values, tr.y.values, rcond=None)[0]
        E.append(pd.DataFrame(dict(e=te_.margin.values - te_[['home'] + cols].values @ c * te_.poss.values / 100, rnd=te_.rnd.values, season=Y, key=te_.key.values)))
    return pd.concat(E).set_index('key')
base_Q = res['PIR']['Q']
B_team = evaluate(base_Q, ['team']); B_te = evaluate(base_Q, ['team', 'exp'])
def paired(E, B):
    b = B[B.rnd <= 10]; x = E.loc[b.index]; d = b.e ** 2 - x.e ** 2
    return d.mean(), d.mean() / (d.std(ddof=1) / math.sqrt(len(d))), sum(1 for Y in TEST5 if np.mean(x[x.season == Y].e ** 2) < np.mean(b[b.season == Y].e ** 2))
rm = lambda E, m: np.sqrt(np.mean(E[m].e ** 2))
P('=== ΣΥΓΚΡΙΣΗ ΤΡΟΠΩΝ RATING (2021-2025 · πληροφορια μονο ως την προηγουμενη σεζον · LOSO) ===')
P(f'  αναφορα: «ομαδα» αγων 1-10 {rm(B_team, B_team.rnd <= 10):.2f} · ολη {rm(B_team, B_team.rnd > 0):.2f} | «ομαδα + ειδικοι» αγων 1-10 {rm(B_te, B_te.rnd <= 10):.2f} · ολη {rm(B_te, B_te.rnd > 0):.2f}')
P('')
P(f'{"τροπος rating":36s} {"σταθ.":>5s} {"μεταφρ.":>7s} | {"ομαδα + παικτες":^40s} | {"ομαδα + ειδικοι + παικτες":^40s}')
P(f'{"":36s} {"Y→Y+1":>5s} {"συσχ.":>7s} | {"1-10":>6s} {"ολη":>6s} {"vs ομαδα (t, σεζον)":>26s} | {"1-10":>6s} {"ολη":>6s} {"vs ομ+ειδ (t, σεζον)":>26s}')
for lab, *_ in VARIANTS:
    Qv = res[lab]['Q']
    E1 = evaluate(Qv, ['team', 'pl', 'uk']); E2 = evaluate(Qv, ['team', 'exp', 'pl', 'uk'])
    d1, t1, w1 = paired(E1, B_team); d2, t2, w2 = paired(E2, B_te)
    P(f'{lab:36s} {res[lab]["stab"]:5.2f} {res[lab]["ctr"]:7.2f} | {rm(E1, E1.rnd <= 10):6.2f} {rm(E1, E1.rnd > 0):6.2f} {f"{d1:+.2f} (t {t1:+.1f}, {w1}/5)":>26s} | '
      f'{rm(E2, E2.rnd <= 10):6.2f} {rm(E2, E2.rnd > 0):6.2f} {f"{d2:+.2f} (t {t2:+.1f}, {w2}/5)":>26s}')
P('')
P('βαρη (ολες οι σεζον) — π./100 κατοχες ανα +1 ανα 40′ πανω απο τον μεσο:')
for lab, *_ in VARIANTS:
    if res[lab]['w']: P(f'  {lab}: ' + ' · '.join(f'{k.replace("_r", "")} {v:+.2f}' for k, v in res[lab]['w'].items()))
open('el_rating_variants_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
