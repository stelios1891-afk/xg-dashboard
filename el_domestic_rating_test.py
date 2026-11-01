# -*- coding: utf-8 -*-
"""el_domestic_rating_test.py — ΕΓΧΩΡΙΑ ΜΑΤΣ ΣΤΟ RATING ΤΗΣ ΕΥΡΩΛΙΓΚΑΣ (30/9/2026, αιτημα Στελιου· αναλογο: στο ποδοσφαιρο
η Ευρωπη βγαινει απο τα εγχωρια). ΕΚΔΟΧΗ 1 = ΣΚΟΡ (bk_domestic.json, Nowgoal, 10 λιγκες, ωρα UTC).
ΕΓΧΩΡΙΑ ΔΥΝΑΜΗ: για καθε λιγκα-σεζον, walk-forward ridge διαφορας: διαφ = R_γηπ − R_φιλ + εδρα (εδρα ελευθερη ανα λιγκα),
  αφετηρια R0 = 0.7 × περσινο τελος (βαρος 8 ματς) — ιδιες σταθερες με το μοντελο μας, ΟΧΙ ρυθμισμενες.
ΣΗΜΑ για ομαδα Ευρωλιγκας την ημερα d: Δ = R(με ματς ΠΡΙΝ τη d) − R0 = ποσο καλυτερη/χειροτερη δειχνει ΦΕΤΟΣ στο πρωταθλημα.
ΣΤΟ ΜΟΝΤΕΛΟ: η αφετηρια του live χαντικαπ (Β1: 0.5 περσι + 0.42 ειδικοι, K12, HL60, εδρα 5, τυχη .5, ×1.1 απο 7ο) μετακινειται
  κατα κ·Δ·(100/72) (μισο επιθεση, μισο αμυνα) — σβηνει φυσικα οσο μαζευονται ματς Ευρωλιγκας (βαρος αφετηριας 12).
ΠΛΕΓΜΑ: κ {0, .25, .5, .75, 1, 1.5} × ταβανι διαφορας {κανενα, 20}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (κ/ταβανι απο τις ΑΛΛΕΣ 4 σεζον, ελαχιστο RMSE αγων 1-10)· ΠΕΡΝΑ αν το εκτος-δειγματος RMSE αγων 1-10
  ειναι καλυτερο απο το live (κ=0) σε ≥4/5 σεζον (2021-22…2025-26). Επισης: ολη η σεζον, κλιση b vs Pinnacle closing, ROI ≥8%.
Εξοδος: el_domestic_rating_test_out.txt"""
import sys, json, re, unicodedata, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
BIG = {}
exec(open('el_hcap_big_test.py', encoding='utf-8').read().split('ENG = list(')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), BIG)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, EM, GN, dnum = BIG['D'], BIG['SE5'], BIG['EM'], BIG['GN'], BIG['dnum']
IDX, PRC, ACT, SE, RS = BIG['IDX'], BIG['PRC'], BIG['ACT'], BIG['SE'], BIG['RS']
fit_eff, fit_pace, LUCK, ends_for = BIG['fit_eff'], BIG['fit_pace'], BIG['LUCK'], BIG['ends_for']
LIVE = dict(wt=0.5, we=0.42, lam=12, HL=60, h=5.0, lw=0.5, sf=1.1)
DOM = json.load(open('bk_domestic.json', encoding='utf-8'))
D0 = pd.Timestamp(D.date.iloc[0])
def tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = s.replace('milano', 'milan').replace('olympiakos', 'olympiacos').replace('olimpia', 'olympia')
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in ('basketball', 'basket', 'club', 'the', 'sport', 'bc', 'kk', 'fc', 'bk', 'sad', 'baloncesto'))
# ---- 1. εγχωρια δυναμη walk-forward ----
def season_key(Y): y = int(Y[1:]); return f'{str(y)[2:]}-{str(y + 1)[2:]}'
LEAGUES = sorted({k.split('_')[0] for k in DOM})
def dom_series(cap):
    """{(EL season, domestic team id, league): [(dnum, Δ)]} + ονοματα"""
    S = {}; names = {}
    for L in LEAGUES:
        keys = sorted([k for k in DOM if k.startswith(L + '_')], key=lambda k: k.split('_')[1])
        prev_end = {}
        for k in keys:
            G_ = [g for g in DOM[k]['games'] if str(g[4]).strip() not in ('', '-1', 'None') and str(g[5]).strip() not in ('', '-1', 'None')]
            names.update({(L, int(t)): n for t, n in DOM[k]['teams'].items()})
            if not G_: prev_end = {}; continue
            gd = np.array([(pd.Timestamp(g[1][:10]) - D0).days for g in G_]); hid = [int(g[2]) for g in G_]; aid = [int(g[3]) for g in G_]
            y = np.array([float(g[4]) - float(g[5]) for g in G_])
            if cap: y = np.clip(y, -cap, cap)
            teams = sorted(set(hid) | set(aid)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
            hi = np.array([ix[t] for t in hid]); ai = np.array([ix[t] for t in aid])
            R0 = np.array([0.7 * prev_end.get(t, 0.0) for t in teams])
            def fit(msk):
                m = msk.sum(); A = np.zeros((m + n, n + 1)); b = np.zeros(m + n)
                r = np.arange(m); A[r, hi[msk]] = 1; A[r, ai[msk]] = -1; A[r, n] = 1; b[:m] = y[msk]
                s8 = math.sqrt(8.0); A[m + np.arange(n), np.arange(n)] = s8; b[m:] = s8 * R0
                return np.linalg.lstsq(A, b, rcond=None)[0][:n]
            es = 'E20' + k.split('_')[1][:2]
            for d in np.unique(gd):
                msk = gd < d
                Rd = fit(msk) if msk.any() else R0
                for t, i in ix.items(): S.setdefault((es, t, L), []).append((d, Rd[i] - R0[i]))
            Rend = fit(np.ones(len(G_), bool)); last_d = gd.max() + 1
            for t, i in ix.items(): S.setdefault((es, t, L), []).append((last_d, Rend[i] - R0[i]))
            prev_end = {t: Rend[i] for t, i in ix.items()}
    return S, names
S0, NAMES = dom_series(None)
# ---- 2. αντιστοιχιση ομαδων Ευρωλιγκας → εγχωριας ομαδας ----
MAP = {}
for Y in SE5:
    sub = D[D.season == Y]
    elteams = {}
    for r in sub.itertuples():
        elteams.setdefault(r.home, r.hname); elteams.setdefault(r.away, r.aname)
    cands = [(es, t, L) for (es, t, L) in S0 if es == Y]
    for code, nm in elteams.items():
        te = tok(nm)
        sc = sorted([(len(te & tok(NAMES.get((L, t), ''))) / max(1, len(tok(NAMES.get((L, t), '')))), (es, t, L)) for (es, t, L) in cands], reverse=True)
        if sc and sc[0][0] >= 0.5: MAP[(Y, code)] = sc[0][1]
P('αντιστοιχιση (σεζον: ομαδα EL → εγχωρια):')
for Y in SE5:
    P(f'  {Y}: ' + ' · '.join(f'{c}→{NAMES.get((k[2], k[1]), "?")[:18]}({k[2]})' for (y, c), k in sorted(MAP.items()) if y == Y))
    miss = sorted({c for c in set(D[D.season == Y].home)} - {c for (y, c) in MAP if y == Y})
    if miss: P(f'     χωρις εγχωριο: {miss}')
# ---- 3. EL μοντελο με μετατοπιση αφετηριας ----
def dom_shift(S, Y, code, d):
    k = MAP.get((Y, code))
    if not k or k not in S: return 0.0
    v = 0.0
    for dd, x in S[k]:
        if dd <= d - 1: v = x
        else: break
    return v
cfg = LIVE; ENDS = ends_for(cfg['HL'], cfg['h'], cfg['lw'], cfg['lam'])
def run(kappa, S):
    EH, EA = LUCK[cfg['lw']]; v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; prior = st['prior']
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * cfg['we']
        o0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2
        d0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2
        p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2); dn = dnum[sidx]
        pred = np.full(len(sidx), np.nan)
        for d in np.unique(dn):
            sh = np.array([kappa * dom_shift(S, Y, t, d) * 100 / 72 for t in teams]) if kappa else np.zeros(n)
            o0 = o0b + sh / 2; d0 = d0b - sh / 2
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / cfg['HL'])
                mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, cfg['lam'], st['mu0'])
                pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, cfg['lam'], st['pm0'])
            else:
                mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
        v[sidx] = pred
    return np.where(GN >= 7, v * cfg['sf'], v)
S20, _ = dom_series(20)
PRED = {}
for cap, S in ((0, S0), (20, S20)):
    for kp in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        if kp == 0 and cap == 20: continue
        PRED[(kp, cap)] = run(kp, S); print(f'  κ {kp} ταβανι {cap} ετοιμο', flush=True)
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
E10 = RSM & (GN <= 10)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
P('')
P('=== IN-SAMPLE (5 σεζον): RMSE αγων 1-10 · ολη η σεζον ===')
for k, v in PRED.items():
    P(f'  κ {k[0]:<4} ταβανι {k[1] or "—":>3}: 1-10 {rm(v, SE5, E10):.3f} · ολη {rm(v, SE5, RSM):.3f}')
base = PRED[(0.0, 0)]
held = np.full(len(D), np.nan); ch = []
for Y in SE5:
    tr = [s for s in SE5 if s != Y]
    best = min(PRED, key=lambda k: rm(PRED[k], tr, E10)); ch.append(best)
    held[SEASD == Y] = PRED[best][SEASD == Y]
P('')
P('LOSO επιλογες: ' + ' | '.join(f'{Y[-4:]}: κ {k[0]} ταβανι {k[1] or "—"}' for Y, k in zip(SE5, ch)))
for nm, msk in (('αγων 1-10', E10), ('αγων 11+', RSM & (GN > 10)), ('ολη η σεζον', RSM)):
    diffs = [rm(held, [Y], msk) - rm(base, [Y], msk) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
    P(f'  {nm:12s}: live {rm(base, SE5, msk):.3f} → με εγχωρια {rm(held, SE5, msk):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs)
      + f' → καλυτερο {w_}/5' + (f' → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if nm == 'αγων 1-10' else ''))
# b & ROI vs Pinnacle closing (κανονικη περιοδος)
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; GJ = GN[IDX[jj]]
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, msk, thr=0.08):
    m = v[IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; p = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0))
    sel = (e >= thr) & msk
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and p[sel & (SJ == s)].mean() > 0)
    return f'{p[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5'
P('')
for nm, v in (('live (κ=0)', base), ('με εγχωρια (LOSO)', held)):
    mk = -L_
    for lab, msk in (('αγων 1-10', GJ <= 10), ('11+', GJ > 10), ('ολη', np.ones(len(jj), bool))):
        b = np.polyfit((v[IDX][jj] - mk)[msk], (AC - mk)[msk], 1)[0]
        P(f'  {nm:18s} {lab:10s}: b {b:+.3f} · ROI ≥8% {roi(v, msk)} · ≥5% {roi(v, msk, 0.05)}')
open('el_domestic_rating_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
