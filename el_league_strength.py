# -*- coding: utf-8 -*-
"""el_league_strength.py — «ELO» ΜΠΑΣΚΕΤ: ΚΟΙΝΗ ΚΛΙΜΑΚΑ ΠΡΩΤΑΘΛΗΜΑΤΩΝ + ΤΕΣΤ στα φετινα εγχωρια (30/9/2026, αιτημα Στελιου).
Δεδομενα: Flashscore (fs_bk_games.json, κωδικος ομαδας PX/PY ιδιος σε ολες τις διοργανωσεις): 10 πρωταθληματα + Ευρωλιγκα,
  EuroCup, Basketball Champions League, FIBA Europe Cup · 2020-21 … 2025-26 · σκορ.
1. ΚΟΙΝΗ ΚΛΙΜΑΚΑ ανα σεζον: ridge διαφορας (ταβανι ±20, εδρα κοινη) σε ΟΛΑ τα ματς → rating καθε ομαδας· επιπεδο λιγκας = μεσος
   των ομαδων της (ποντοι/ματς απεναντι σε μεση ομαδα του συνολου).
2. ΜΕΤΑΦΡΑΣΗ ανα λιγκα (β): ομαδες με ≥8 εγχωρια & ≥6 ευρωπαικα ματς: εγχωριο rating (μονο πρωταθλημα, κεντραρισμενο)
   vs ευρωπαικο rating (μονο ευρωπαικα ματς, αντιπαλοι στην κοινη κλιμακα) → κλιση ανα λιγκα, μαζεμα 50% προς την κοινη.
3. ΤΕΣΤ: φετινα εγχωρια (οπως live: κ .5, ταβανι 20) με πολλαπλασιαστη β_λιγκας/β_κοινο (LOSO: β χωρις τη σεζον-τεστ).
   ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: RMSE αγων 11+ καλυτερο απο το ιδιο βαρος σε ≥4/5 σεζον (κ απο τις αλλες σεζον).
Εξοδος: el_league_strength_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
DOMS = ['ACB', 'GBL', 'TBL', 'LBA', 'ISR', 'LNB', 'BBL', 'LKL', 'ABA', 'VTB']; EUR = ['EL', 'EC', 'BCL', 'FEC']
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
rows = []
for key, L in FG.items():
    c, y = key.split('_'); y = int(y)
    if y > 2025 or c not in DOMS + EUR: continue
    for e in L:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        if not e.get('hid') or not e.get('aid'): continue
        rows.append(dict(comp=c, y=y, ts=e['ts'], h=e['hid'], a=e['aid'], hn=e['home'], an=e['away'], m=float(np.clip(hs - as_, -20, 20))))
G = pd.DataFrame(rows)
P(f'ματς: {len(G)} · ' + ' '.join(f'{c}:{(G.comp == c).sum()}' for c in DOMS + EUR))
NAME = dict(zip(G.h, G.hn)); NAME.update(dict(zip(G.a, G.an)))
def ridge(h, a, m, n_idx, lam, prior=None):
    teams = sorted(set(h) | set(a)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(m)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r = np.arange(k)
    A[r, [ix[t] for t in h]] = 1; A[r, [ix[t] for t in a]] = -1; A[r, n] = 1; b[:k] = m
    A[k + np.arange(n), np.arange(n)] = math.sqrt(lam); b[k:] = math.sqrt(lam) * np.array([(prior or {}).get(t, 0.0) for t in teams])
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: x[ix[t]] for t in teams}, x[n]
COMMON, LEVEL, BETA_PTS = {}, {}, []
for y in sorted(G.y.unique()):
    g = G[G.y == y]
    R, hadv = ridge(g.h.values, g.a.values, g.m.values, None, 2.0)
    COMMON[y] = R
    league_of = {}
    for c in DOMS:
        gd = g[g.comp == c]
        for t in set(gd.h) | set(gd.a): league_of.setdefault(t, c)
    for c in DOMS + EUR:
        tt = sorted({t for t, l in league_of.items() if l == c}) if c in DOMS else sorted(set(g[g.comp == c].h) | set(g[g.comp == c].a))
        if tt: LEVEL[(c, y)] = (float(np.mean([R[t] for t in tt])), float(np.std([R[t] for t in tt])), len(tt))
    # β: εγχωριο (μονο πρωταθλημα) vs ευρωπαικο (μονο ευρωπη, αντιπαλοι σταθεροι στην κοινη κλιμακα)
    ge = g[g.comp.isin(EUR)]
    for c in DOMS:
        gd = g[g.comp == c]
        if gd.empty: continue
        Rd, _ = ridge(gd.h.values, gd.a.values, gd.m.values, None, 4.0)
        mu = np.mean(list(Rd.values()))
        nd = pd.concat([gd.h, gd.a]).value_counts()
        for t in Rd:
            if nd.get(t, 0) < 8: continue
            eh = ge[ge.h == t]; ea = ge[ge.a == t]
            if len(eh) + len(ea) < 6: continue
            vals = list(eh.m.values - hadv + np.array([R[o] for o in eh.a])) + list(-ea.m.values + hadv + np.array([R[o] for o in ea.h]))
            reu = np.sum(vals) / (len(vals) + 4.0)                     # μαζεμα προς 0 (μεση ομαδα του συνολου)
            BETA_PTS.append(dict(y=y, L=c, t=t, name=NAME.get(t), dom=Rd[t] - mu, eu=reu, lvl=LEVEL[(c, y)][0]))
P('')
P('=== 1. ΕΠΙΠΕΔΟ ΛΙΓΚΑΣ στην κοινη κλιμακα (ποντοι/ματς απεναντι σε μεση ομαδα ολων· μεσος 2020-26) ===')
lv = pd.DataFrame([dict(c=c, y=y, lvl=v[0], sd=v[1], n=v[2]) for (c, y), v in LEVEL.items()])
ref = lv[lv.c == 'ACB'].set_index('y').lvl
tab = lv.assign(vs_acb=lv.lvl - lv.y.map(ref)).groupby('c').agg(lvl=('vs_acb', 'mean'), sd=('sd', 'mean'), n=('n', 'mean')).sort_values('lvl', ascending=False)
for c, r in tab.iterrows():
    per = ' '.join(f'{y}:{(lv[(lv.c == c) & (lv.y == y)].lvl.values[0] - ref[y]):+.1f}' for y in sorted(lv.y.unique()) if ((lv.c == c) & (lv.y == y)).any())
    P(f'  {c:4s} επιπεδο vs ACB {r.lvl:+5.1f} π. · διασπορα ομαδων {r.sd:4.1f} · ομαδες {r.n:4.0f} | {per}')
BP = pd.DataFrame(BETA_PTS)
P('')
P(f'=== 2. ΜΕΤΑΦΡΑΣΗ εγχωριου → ευρωπαικου rating ({len(BP)} ομαδες-σεζον) ===')
def betas(excl=None):
    d = BP[BP.y != excl] if excl else BP
    b_all = np.polyfit(d.dom, d.eu - d.lvl, 1)[0]
    res = {}
    for L, g in d.groupby('L'):
        bl = np.polyfit(g.dom, g.eu - g.lvl, 1)[0] if len(g) >= 6 and g.dom.std() > 0 else b_all
        res[L] = (0.5 * bl + 0.5 * b_all, len(g), bl)
    return res, b_all
bb, ba = betas()
P(f'  κοινη κλιση {ba:.2f} (1.00 = ενας ποντος στο πρωταθλημα = ενας ποντος στην Ευρωπη)')
for L, (b_, n_, raw) in sorted(bb.items(), key=lambda x: -x[1][0]):
    P(f'  {L:4s} β {b_:.2f} (χωρις μαζεμα {raw:.2f}) · ομαδες-σεζον {n_}')
# ---- 3. τεστ στο μοντελο Ευρωλιγκας ----
NS = {}
src = open('el_domestic_league_test.py', encoding='utf-8').read().split("PRED = {}\nfor var in")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace("open('el_domestic_league_test_out.txt'", "open('_unused.txt'")
exec(src, NS)
SE5 = NS['SE5']
def mult_new(variant, Y, L):
    if variant == 'a' or L is None: return 1.0
    y_excl = int(Y[1:])
    bl, ba_ = betas(excl=y_excl)
    return (bl[L][0] / ba_) if L in bl and ba_ else 1.0
NS['mult'] = mult_new
PRED = {}
for var in ('a', 'd'):
    for kp in (0.25, 0.5, 0.75, 1.0, 1.5):
        PRED[(var, kp)] = NS['run'](kp, var); print(f'  {var} κ {kp} ετοιμο', flush=True)
D, GN, IDX, PRC, ACT, SE, RS = (NS[k] for k in ('D', 'GN', 'IDX', 'PRC', 'ACT', 'SE', 'RS'))
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values; M11 = RSM & (GN > 10)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
held = {}
for var in ('a', 'd'):
    h = np.full(len(D), np.nan); ch = []
    for Y in SE5:
        tr = [s for s in SE5 if s != Y]
        k = min([k for k in PRED if k[0] == var], key=lambda k: rm(PRED[k], tr, M11)); ch.append(k[1]); h[SEASD == Y] = PRED[k][SEASD == Y]
    held[var] = (h, ch)
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
GJ = GN[IDX[jj]]; MK = -PRC[jj, 0]; AC = ACT[jj]
P('')
P('=== 3. ΤΕΣΤ: φετινα εγχωρια με μεταφραση β ανα λιγκα (LOSO) — αγων 11+ ===')
base = held['a'][0]
for var, lab in (('a', 'ιδιο βαρος (σημερα)'), ('d', 'με μεταφραση β λιγκας')):
    h, ch = held[var]
    diffs = [rm(h, [Y], M11) - rm(base, [Y], M11) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
    b = np.polyfit((h[IDX][jj] - MK)[GJ > 10], (AC - MK)[GJ > 10], 1)[0]
    P(f'  {lab:24s} κ {ch} · RMSE 11+ {rm(h, SE5, M11):.3f} · vs σημερα ' + ' '.join(f'{d:+.3f}' for d in diffs)
      + (f' → καλυτερο {w_}/5 → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if var != 'a' else '') + f' · b {b:+.3f}')
open('el_league_strength_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
