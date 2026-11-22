# -*- coding: utf-8 -*-
"""el_whoplays_test.py — ΕΥΡΩΛΙΓΚΑ: ΜΕΘΟΔΟΣ NBA «ΠΟΙΟΣ ΠΑΙΖΕΙ» + ΑΠΟΥΣΙΕΣ (30/9/2026, αιτημα Στελιου).
Ιδιο με nba_oracle_test.py. Αξια παικτη ΠΡΙΝ απο καθε ματς: ρυθμοι ανα λεπτο απο ολα τα προηγουμενα ματς Ευρωλιγκας του
  (φθορα: μιση αξια σε 180 μερες, μαζεμα 300′ προς τον μεσο) — 2Π/3Π/βολες ευστ.-αστ., ΕΡ, ΑΡ, ΑΣ, ΚΛ, ΛΑ, ΚΟ, ΦΑ, +/-.
Ομαδα στο ματς: Σ μεριδιο λεπτων × (ρυθμοι − μεσος), γηπ − φιλ.
  Τ2 «γνωση απουσιων» = ποιοι επαιξαν ΓΝΩΣΤΟ, λεπτα = προσφατος μεσος ορος τους · Τ1 = πραγματικα λεπτα (ταβανι).
Βαρη χαρακτηριστικων (ridge) και συνδυασμος με το live μοντελο ομαδων (Β1 με ειδικους): ΜΟΝΟ απο αλλες σεζον (LOSO, τεστ 2021-25).
ΑΠΟΥΣΙΕΣ: «συνηθισμενο ρόστερ» = οσοι επαιξαν στα 10 τελευταια ματς της ομαδας (με τα μεσα λεπτα τους)· επιδραση απουσιων =
  ομαδα Τ2 − ομαδα με το συνηθισμενο ρόστερ (ποντοι, γηπ − φιλ). Κλισεις: πραγματικοτητα / αγορα (Pinnacle closing) / πραγμ.−αγορα.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: «ομαδα + παικτες Τ2» ΠΕΡΝΑ αν RMSE (κανονικη περιοδος) καλυτερο απο το live σε ≥4/5 σεζον.
Εξοδος: el_whoplays_test_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_domestic_rating_test.py', encoding='utf-8').read().split("S20, _ = dom_series(20)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, GN, IDX, PRC, ACT, SE, RS = NS['D'], NS['SE5'], NS['GN'], NS['IDX'], NS['PRC'], NS['ACT'], NS['SE'], NS['RS']
BASE = NS['run'](0.0, NS['S0'])                                 # live Β1 (ομαδες + ειδικοι)
keycol = D['key'].values if 'key' in D.columns else D.index.values
KPOS = {k: i for i, k in enumerate(keycol)}
PL = json.load(open('el_players.json', encoding='utf-8'))
F = ['p2m', 'p2x', 'p3m', 'p3x', 'ftm', 'ftx', 'orb', 'drb', 'ast', 'stl', 'tov', 'blk', 'pf', 'pm']
rows = []
for k, g in PL.items():
    if g.get('comp') != 'E' or 'err' in g or 'ph' not in g or k not in KPOS: continue
    pos = KPOS[k]
    for side, sg in (('ph', 1), ('pa', -1)):
        for p in g[side]:
            m = p[3] or 0
            if m <= 0: continue
            rows.append(dict(pos=pos, date=D.date.values[pos], sign=sg, pid=p[0], starter=p[2], MIN=m,
                             p2m=p[5], p2x=p[6] - p[5], p3m=p[7], p3x=p[8] - p[7], ftm=p[9], ftx=p[10] - p[9], orb=p[11], drb=p[12],
                             ast=p[13], stl=p[14], tov=p[15], blk=p[16], pf=p[17], pm=p[19] if len(p) > 19 and p[19] is not None else 0))
A = pd.DataFrame(rows).sort_values(['date', 'pos']).reset_index(drop=True)
A[F] = A[F].fillna(0).astype(float)
P(f'γραμμες παικτη-ματς: {len(A)} · ματς {A.pos.nunique()}')
HLD, M0 = 180.0, 300.0
MU = A[F].sum() / A.MIN.sum()
state = {}; pre = np.zeros((len(A), len(F))); premin = np.full(len(A), np.nan)
for d, blk in A.groupby('date', sort=True):
    dd = pd.Timestamp(d)
    for k, r in blk.iterrows():
        s = state.get(r.pid)
        if s is None: pre[k] = MU.values
        else:
            fac = 0.5 ** ((dd - s[0]).days / HLD)
            pre[k] = (s[2] * fac + M0 * MU.values) / (s[1] * fac + M0); premin[k] = s[3]
    for k, r in blk.iterrows():
        s = state.get(r.pid); v = r[F].values.astype(float)
        if s is None: state[r.pid] = [dd, r.MIN, v.copy(), r.MIN]
        else:
            fac = 0.5 ** ((dd - s[0]).days / HLD)
            state[r.pid] = [dd, s[1] * fac + r.MIN, s[2] * fac + v, 0.8 * s[3] + 0.2 * r.MIN]
X = pre - MU.values
A['premin'] = premin
tm = A.groupby(['pos', 'sign']).MIN.transform('sum')
A['s1'] = A.MIN / (tm / 5)
pm_ = A.premin.fillna(A.groupby(['pos', 'sign']).premin.transform('median')).fillna(15.0)
A['s2'] = pm_ / (pm_.groupby([A.pos, A.sign]).transform('sum') / 5)
def feats(w):
    Z = np.zeros((len(D), len(F))); np.add.at(Z, A.pos.values, (A.sign.values * w)[:, None] * X); return Z
Z1, Z2 = feats(A.s1.values), feats(A.s2.values)
# «συνηθισμενο ρόστερ»: οσοι επαιξαν στα 10 τελευταια ματς της ομαδας, με τον προσφατο μεσο ορο λεπτων — ΠΡΙΝ το ματς
team_of = {}
for i_, (h_, a_) in enumerate(zip(D.home.values, D.away.values)):
    team_of[(i_, 1)] = h_; team_of[(i_, -1)] = a_
A['team'] = [team_of.get((p, s)) for p, s in zip(A.pos, A.sign)]
A['season'] = D.season.values[A.pos.values]
ZU = np.zeros((len(D), len(F))); miss_core = np.zeros((len(D), 2)); hist = {}
last_rate = {}                                                     # pid -> (ρυθμοι πριν απο το πιο προσφατο ματς, premin)
by_game = {p: g for p, g in A.groupby('pos')}
for pos in sorted(by_game):
    g = by_game[pos]
    for sg in (1, -1):
        gs = g[g.sign == sg]
        if gs.empty: continue
        key = (D.season.values[pos], gs.team.iloc[0]); H = hist.setdefault(key, [])
        if len(H) >= 3:
            usual = {}
            for gg in H[-10:]:
                for pid, mn in gg.items(): usual[pid] = usual.get(pid, 0) + mn
            ups = [p for p in usual if p in last_rate]
            if ups:
                w = np.array([last_rate[p][1] or usual[p] / len(H[-10:]) for p in ups]); w = 5 * w / w.sum()
                ZU[pos] += sg * (w[:, None] * np.array([last_rate[p][0] for p in ups])).sum(0)
            core = sorted(usual, key=usual.get, reverse=True)[:5]
            miss_core[pos, 0 if sg == 1 else 1] = sum(1 for p in core if p not in set(gs.pid))
        else:
            ZU[pos] += sg * (gs.s2.values[:, None] * X[gs.index.values]).sum(0)
            miss_core[pos, 0 if sg == 1 else 1] = np.nan
        H.append(dict(zip(gs.pid, gs.MIN)))
        for idx_, pid in zip(gs.index.values, gs.pid.values):
            last_rate[pid] = (X[idx_], A.premin.values[idx_])
# ---- βαρη LOSO ----
ok = np.zeros(len(D), bool); ok[A.pos.unique()] = True
Y100 = 100 * (D.hs - D.as_).values / D.poss.values
HOMEI = (~(D.ff.values | D.relocated.values)).astype(float)
SEASD = D.season.values; ACTD = (D.hs - D.as_).values.astype(float); RSM = (D.phase.values == 'RS')
PACE = float(np.nanmean(D.pace.values))
TRAIN_ALL = [s for s in sorted(set(SEASD)) if s >= 'E2018']
def player_pred(Z, test):
    tr = ok & np.isin(SEASD, [s for s in TRAIN_ALL if s != test]); Axx = np.column_stack([HOMEI, Z])
    c = np.linalg.lstsq(np.vstack([Axx[tr], np.column_stack([np.zeros(len(F)), 3 * np.eye(len(F))])]),
                        np.concatenate([Y100[tr], np.zeros(len(F))]), rcond=None)[0]
    return c
PL1, PL2, PLU = (np.full(len(D), np.nan) for _ in range(3)); BETAS = []
for Y in SE5:
    c = player_pred(Z2, Y); BETAS.append(c); te = SEASD == Y
    PL2[te] = (np.column_stack([HOMEI, Z2]) @ c)[te] * PACE / 100
    PLU[te] = (np.column_stack([HOMEI, ZU]) @ c)[te] * PACE / 100
    c1 = player_pred(Z1, Y); PL1[te] = (np.column_stack([HOMEI, Z1]) @ c1)[te] * PACE / 100
def combo(cols):
    pred = np.full(len(D), np.nan); Xm = np.column_stack([np.ones(len(D))] + cols)
    good = ok & RSM & np.isin(SEASD, SE5) & ~np.isnan(Xm).any(1)
    for Y in SE5:
        tr = good & (SEASD != Y); te = SEASD == Y
        cc = np.linalg.lstsq(Xm[tr], ACTD[tr], rcond=None)[0]; pred[te] = (Xm @ cc)[te]
    return pred
V = {'live (ομαδες+ειδικοι)': BASE, 'μονο παικτες Τ2': PL2, 'live + παικτες Τ2 (ποιος παιζει)': combo([BASE, PL2]),
     'live + παικτες Τ1 (πραγματικα λεπτα)': combo([BASE, PL1]), 'live + παικτες «συνηθισμενο ρόστερ»': combo([BASE, PLU])}
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; MK = -L_
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, thr):
    m = v[IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; p = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0)); sel = (e >= thr) & ~np.isnan(m)
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and p[sel & (SJ == s)].mean() > 0)
    return f'{p[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5'
def rm(v, s): m = RSM & ok & (SEASD == s) & ~np.isnan(v); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
P(f'αγορα Pinnacle closing RMSE (ιδια ματς): {np.sqrt(np.mean((AC - MK) ** 2)):.3f}')
for nm, v in V.items():
    m5 = RSM & ok & np.isin(SEASD, SE5) & ~np.isnan(v)
    per = [rm(v, s) for s in SE5]; wins = sum(rm(v, s) < rm(BASE, s) for s in SE5)
    vj = v[IDX][jj]; fin = ~np.isnan(vj); b = np.polyfit((vj - MK)[fin], (AC - MK)[fin], 1)[0]
    P(f'  {nm:38s} RMSE {np.sqrt(np.mean((ACTD - v)[m5] ** 2)):.3f} (' + ' '.join(f'{s[-2:]}:{x:.2f}' for s, x in zip(SE5, per))
      + f') · καλυτερο απο live {wins}/5' + (f' → {"ΠΕΡΝΑ" if wins >= 4 else "✗"}' if 'Τ2 (ποιος' in nm else '')
      + f' · b {b:+.3f} · ROI ≥5% {roi(v, 0.05)} · ≥8% {roi(v, 0.08)}')
P('')
P('=== ΑΠΟΥΣΙΕΣ: επιδραση = (παικτες Τ2) − (παικτες «συνηθισμενο ρόστερ»), ποντοι γηπ − φιλ ===')
cU = combo([BASE, PL2]); eff = np.full(len(D), np.nan)
for Y in SE5:
    te = SEASD == Y
    # ιδιος συντελεστης παικτων με το combo της σεζον (εκτος δειγματος)
    Xm = np.column_stack([np.ones(len(D)), BASE, PL2]); good = ok & RSM & np.isin(SEASD, SE5) & ~np.isnan(Xm).any(1) & (SEASD != Y)
    cc = np.linalg.lstsq(Xm[good], ACTD[good], rcond=None)[0]
    eff[te] = cc[2] * (PL2 - PLU)[te]
e_ = eff[IDX][jj]; okj = ~np.isnan(e_); base_j = BASE[IDX][jj]
P(f'  ματς {okj.sum()} · επιδραση απουσιων: sd {np.nanstd(e_):.2f} π. · |επιδραση| ≥2π σε {np.mean(np.abs(e_[okj]) >= 2):.0%} των ματς · ≥4π σε {np.mean(np.abs(e_[okj]) >= 4):.0%}')
for lab, y in (('πραγματικο − live', AC - base_j), ('αγορα − live', MK - base_j), ('πραγματικο − αγορα', AC - MK)):
    b_ = np.polyfit(e_[okj], y[okj], 1)[0]; r_ = y[okj] - np.polyval(np.polyfit(e_[okj], y[okj], 1), e_[okj])
    se = np.sqrt(np.sum(r_ ** 2) / (okj.sum() - 2) / np.sum((e_[okj] - e_[okj].mean()) ** 2))
    P(f'  κλιση {lab:20s} πανω στην επιδραση: {b_:+.2f} (t {b_ / se:+.1f})   (1 = μετραει ολη)')
mc = miss_core[IDX][jj]; mh, ma = mc[:, 0], mc[:, 1]
P('  απουσιες «βασικων» (απο τους 5 με τα περισσοτερα λεπτα στα 10 τελευταια): συχνοτητα ' +
  ' · '.join(f'{k}: {np.mean(np.nan_to_num(mh) == k) * 50 + np.mean(np.nan_to_num(ma) == k) * 50:.0f}%' for k in (0, 1, 2, 3)))
for k in (1, 2):
    for sd, arr, sgn in (('γηπ', mh, 1), ('φιλ', ma, -1)):
        m_ = (arr == k) & (np.nan_to_num(mh if sd == 'φιλ' else ma) == 0)
        if m_.sum() < 20: continue
        P(f'  {sd}. λειπουν {k} βασικοι (αντιπαλος πληρης), n {m_.sum()}: πραγμ − live {np.mean((AC - base_j)[m_]) * sgn:+.2f} π. · αγορα − live {np.mean((MK - base_j)[m_]) * sgn:+.2f} · πραγμ − αγορα {np.mean((AC - MK)[m_]) * sgn:+.2f}   (για την ομαδα με τις απουσιες)')
P('')
P('=== PICKS ΤΟΥ LIVE (Pinnacle closing) ανα απουσιες βασικων — «η ομαδα μας» = αυτη που στηριζουμε ===')
mj = BASE[IDX][jj]
pw = np.where(isint, Phi((mj + L_ - 0.5) / 11.5), Phi((mj + L_) / 11.5)); pl_ = np.where(isint, Phi((-mj - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl_
eh, ea = pw * OH + pp - 1, pl_ * OA + pp - 1
side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
vv = (AC + L_) * side; pr = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0))
ours = np.where(side == 1, mh, ma); theirs = np.where(side == 1, ma, mh)
for thr in (0.05, 0.08):
    sel = (e >= thr) & ~np.isnan(ours) & ~np.isnan(theirs)
    for lab, g_ in (('και οι δυο πληρεις', (ours == 0) & (theirs == 0)), ('ΛΕΙΠΕΙ βασικος ΣΤΗ ΔΙΚΗ ΜΑΣ', (ours >= 1) & (theirs == 0)),
                    ('λειπει βασικος στον ΑΝΤΙΠΑΛΟ', (ours == 0) & (theirs >= 1)), ('λειπουν και στις δυο', (ours >= 1) & (theirs >= 1))):
        m_ = sel & g_
        if m_.sum() < 10: continue
        pos_ = sum(1 for s_ in SE5 if (m_ & (SJ == s_)).any() and pr[m_ & (SJ == s_)].mean() > 0)
        P(f'  edge ≥{thr*100:.0f}% · {lab:32s}: {m_.sum():4d} picks · ROI {pr[m_].mean()*100:+.1f}% ({pos_}/5)')

P('')
P('βαρη χαρακτηριστικων (μεσος LOSO, π./100 ανα +1 ανα λεπτο × 40): ' + ' · '.join(f'{f} {b * 40:+.1f}' for f, b in zip(F, np.mean(BETAS, axis=0)[1:])))
open('el_whoplays_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
