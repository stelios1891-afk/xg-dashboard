"""
core7_diag.py — ΔΙΑΓΝΩΣΗ ΕΓΧΩΡΙΩΝ vs ΑΓΟΡΑ (28/9/2026, Στελιος: «ιδια αναλυση με τις εθνικες — που μενουμε πισω και γιατι»).
Μοντελο = live engine (europe_test_preds.csv: xg_h/xg_a ανα ματς, CORE7, 2223-2526). Αγορα = Pinnacle closing (football-data):
1Χ2 PSC*, AH AHCh + PCAHH/PCAHA, O/U 2.5 AvgC (Pinnacle O/U λειπει) · opening AHh + PAHH/PAHA.
Υπεροχη αγορας = απο AH closing (σωστα τεταρτα, T = O/U closing)· T αγορας = Poisson απο O/U 2.5 χωρις γκανιοτα.
Περιγραφικο — δεν αλλαζει τιποτα.
"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

src = open('sos_test.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('# ---------- team ratings')], ns)
build_odds_layer, reg_of = ns['build_odds_layer'], ns['reg_of']
P = pd.read_csv('europe_test_preds.csv', dtype={'season': str}); P = P[P.gd.notna()].copy()
LG = sorted(P.league.unique()); SEAS = sorted(P.season.unique())
reg, resolvers = build_odds_layer(LG, SEAS)

def T_from_ou(po):          # P(συνολο>2.5) = po → T (Poisson)
    lo, hi = 0.5, 6.0
    for _ in range(40):
        m = (lo + hi) / 2; p = 1 - math.exp(-m) * (1 + m + m * m / 2)
        lo, hi = (m, hi) if p < po else (lo, m)
    return (lo + hi) / 2
_c = {}
def sup(line, oh, oa, T):
    key = (line, oh, oa, round(T, 2))
    if key in _c: return _c[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(36):
        md = (lo + hi) / 2; d = picks.gd_dist(max((T + md) / 2, .05), max((T - md) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _c[key] = (lo + hi) / 2; return _c[key]
def p3(xh, xa):
    d = picks.gd_dist(max(xh, .05), max(xa, .05)); return (sum(v for k, v in d.items() if k > 0), d.get(0, 0.0), sum(v for k, v in d.items() if k < 0))

rows = []
for _, r in P.iterrows():
    g = reg_of(r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], resolvers[g](r['home_name']), resolvers[g](r['away_name']), r['date'])
    if o is None: continue
    oh, od, oa = (o.get(c) for c in ('PSCH', 'PSCD', 'PSCA'))
    if any(pd.isna(v) for v in (oh, od, oa)): continue
    k = 1 / oh + 1 / od + 1 / oa; mk = (1 / oh / k, 1 / od / k, 1 / oa / k)
    ov, un = o.get('AvgC>2.5'), o.get('AvgC<2.5')
    T_m = T_from_ou((1 / ov) / (1 / ov + 1 / un)) if pd.notna(ov) and pd.notna(un) else np.nan
    L, ah, aa = o.get('AHCh'), o.get('PCAHH'), o.get('PCAHA')
    s_m = sup(float(L), float(ah), float(aa), T_m if T_m == T_m else 2.7) if pd.notna(L) and pd.notna(ah) and pd.notna(aa) else np.nan
    Lo, oh0, oa0 = o.get('AHh'), o.get('PAHH'), o.get('PAHA')
    s_o = sup(float(Lo), float(oh0), float(oa0), T_m if T_m == T_m else 2.7) if pd.notna(Lo) and pd.notna(oh0) and pd.notna(oa0) else np.nan
    xh, xa = min(max(r.xg_h, .05), 6), min(max(r.xg_a, .05), 6); pm = p3(xh, xa)
    hg, ag = o.get('FTHG'), o.get('FTAG')
    rows.append(dict(league=r.league, season=r.season, md=int(r.md), home=r.home_name, away=r.away_name, gd=int(r.gd),
                     tot=(float(hg) + float(ag)) if pd.notna(hg) and pd.notna(ag) else np.nan, xh=xh, xa=xa, s_mod=xh - xa, T_mod=xh + xa, s_mkt=s_m, s_open=s_o, T_mkt=T_m,
                     ph=pm[0], pdr=pm[1], pa=pm[2], mh=mk[0], mdr=mk[1], ma=mk[2], L=L, ah=ah, aa=aa))
D = pd.DataFrame(rows)
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
D['win'] = np.where(D.md >= 15, 'md15+', np.where(D.md >= 7, 'md7-14', 'md<7'))
print(f'ματς με closing 1Χ2: {len(D)} · με AH: {D.s_mkt.notna().sum()} · με O/U: {D.T_mkt.notna().sum()} · με opening AH: {D.s_open.notna().sum()}')
print('ματς ανα παραθυρο:', D.win.value_counts().to_dict())

def rps(pm, y):
    o = np.zeros_like(pm); o[np.arange(len(y)), 2 - y] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
def blend_w(df):
    pm = df[['ph', 'pdr', 'pa']].values; mk = df[['mh', 'mdr', 'ma']].values; y = df.y.values; best = (0, 9)
    for w in np.linspace(0, 1, 21):
        q = np.exp(w * np.log(pm) + (1 - w) * np.log(mk)); q /= q.sum(1, keepdims=True); s = rps(q, y)
        if s < best[1]: best = (w, s)
    return best

print('\nΑ. ΑΚΡΙΒΕΙΑ 1Χ2 (RPS· χαμηλοτερο = καλυτερο) — baseline = συχνοτητες')
def acc(df, lab):
    y = df.y.values; base = np.tile([np.mean(y == 2), np.mean(y == 1), np.mean(y == 0)], (len(df), 1))
    rb, rm, rk = rps(base, y), rps(df[['ph', 'pdr', 'pa']].values, y), rps(df[['mh', 'mdr', 'ma']].values, y)
    w, rw = blend_w(df)
    print(f'  {lab:22s} n{len(df):5d} · baseline {rb:.4f} · ΜΟΝΤΕΛΟ {rm:.4f} · ΑΓΟΡΑ {rk:.4f} · κενο {rm - rk:+.4f} · % αποστασης {100*(rb - rm)/(rb - rk):.0f}% · blend w_μοντ {w:.2f}')
acc(D, 'ΟΛΑ')
for w_ in ('md<7', 'md7-14', 'md15+'): acc(D[D.win == w_], w_)
for lg in LG: acc(D[(D.league == lg) & (D.win == 'md15+')], f'{lg} (md15+)')

M = D[D.s_mkt.notna()].copy()
def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X); b, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ b
    XtXi = np.linalg.inv(A.T @ A); cov = XtXi @ ((A * e[:, None]).T @ (A * e[:, None])) @ XtXi
    return b, np.sqrt(np.diag(cov))
print('\nΒ. ΚΛΙΣΗ b (γκολ διαφορα ~ υπεροχη αγορας + b·(μοντελο − αγορα)): b>0 = το μοντελο ξερει κατι πανω απο την αγορα')
for lab, df in [('ΟΛΑ', M)] + [(w_, M[M.win == w_]) for w_ in ('md<7', 'md7-14', 'md15+')] + [(f'{lg} md15+', M[(M.league == lg) & (M.win == 'md15+')]) for lg in LG]:
    b, se = ols(df.gd.values.astype(float), [df.s_mkt.values, (df.s_mod - df.s_mkt).values])
    b2, se2 = ols(df.gd.values.astype(float), [df.s_mod.values])
    print(f'  {lab:22s} n{len(df):5d} · αγορα {b[1]:.2f} · b(μοντ−αγορα) {b[2]:+.2f} (t {b[2]/se[2]:+.1f}) · κλιση μοντελου μονου {b2[1]:.2f} · sd διαφωνιας {np.std(df.s_mod - df.s_mkt):.2f} γκολ')

print('\nΓ. ΜΕΡΟΛΗΨΙΑ υπεροχης (προβλεψη − πραγματικο, γκολ· + = υπερεκτιμα τον γηπεδουχο) ανα ζωνη ΦΑΒΟΡΙ ΑΓΟΡΑΣ (απο τη σκοπια του φαβορι)')
M['sf'] = np.sign(M.s_mkt).replace(0, 1)
M['fav_mkt'] = M.s_mkt.abs(); M['fav_mod'] = M.sf * M.s_mod; M['fav_gd'] = M.sf * M.gd
bins = [(0, .25), (.25, .75), (.75, 1.25), (1.25, 2.0), (2.0, 9)]
for w_ in ('ΟΛΑ', 'md15+'):
    df = M if w_ == 'ΟΛΑ' else M[M.win == w_]
    print(f'  [{w_}]')
    for lo, hi in bins:
        d = df[(df.fav_mkt >= lo) & (df.fav_mkt < hi)]
        if len(d) < 30: continue
        e_mod = d.fav_mod - d.fav_gd; e_mkt = d.fav_mkt - d.fav_gd
        print(f'    φαβορι αγορας {lo:.2f}-{hi if hi < 9 else "∞"}: n{len(d):5d} · πραγματικο {d.fav_gd.mean():+.2f} · μοντελο {d.fav_mod.mean():+.2f} ({e_mod.mean():+.2f} ±{e_mod.std()/np.sqrt(len(d)):.2f}) · '
              f'αγορα {d.fav_mkt.mean():+.2f} ({e_mkt.mean():+.2f} ±{e_mkt.std()/np.sqrt(len(d)):.2f})')
print('  ανα πλευρα/εδρα (ολα): μεση υπεροχη γηπεδουχου — πραγματικο {:+.3f} · μοντελο {:+.3f} · αγορα {:+.3f}'.format(M.gd.mean(), M.s_mod.mean(), M.s_mkt.mean()))
print('  φαβορι γηπεδουχος vs φιλοξενουμενος (μοντελο − πραγματικο, σκοπια φαβορι):')
for side, d in (('γηπεδουχο φαβορι', M[M.s_mkt > 0]), ('φιλοξενουμενο φαβορι', M[M.s_mkt < 0])):
    print(f'    {side:22s} n{len(d)} · μοντελο {(d.fav_mod - d.fav_gd).mean():+.3f} · αγορα {(d.fav_mkt - d.fav_gd).mean():+.3f}')
print('  ανα λιγκα (md15+, μοντελο−πραγμ. / αγορα−πραγμ., σκοπια γηπεδουχου):')
for lg in LG:
    d = M[(M.league == lg) & (M.win == 'md15+')]
    print(f'    {lg:13s} n{len(d)} · μοντελο {(d.s_mod - d.gd).mean():+.3f} · αγορα {(d.s_mkt - d.gd).mean():+.3f} · διαφωνια μοντ−αγορα μεση {(d.s_mod - d.s_mkt).mean():+.3f}')
print('  ανα παραθυρο (σκοπια φαβορι αγορας): ' + ' · '.join(f"{w_}: μοντ {(M[M.win==w_].fav_mod - M[M.win==w_].fav_gd).mean():+.3f} / αγορα {(M[M.win==w_].fav_mkt - M[M.win==w_].fav_gd).mean():+.3f}" for w_ in ('md<7', 'md7-14', 'md15+')))

print('\nΔ. ΚΑΤΑΝΟΜΗ ΔΙΑΦΟΡΑΣ ΓΚΟΛ (σκοπια φαβορι αγορας, md15+· αγορα = Poisson απο υπεροχη+T closing)')
Q = M[(M.win == 'md15+') & M.T_mkt.notna()]
def dist_fav(xf, xd):
    d = picks.gd_dist(max(xf, .05), max(xd, .05)); return d
acc_ = {'ισοπαλια': [0, 0, 0], 'νικη με 1': [0, 0, 0], 'νικη με 2': [0, 0, 0], 'νικη 3+': [0, 0, 0], 'ηττα φαβορι': [0, 0, 0]}
for r in Q.itertuples():
    xf, xd = (r.xh, r.xa) if r.sf > 0 else (r.xa, r.xh)
    dm = dist_fav(xf, xd); T = r.T_mkt; s = r.fav_mkt; dk = dist_fav((T + s) / 2, (T - s) / 2); g = r.fav_gd
    for lab, f in (('ισοπαλια', lambda k: k == 0), ('νικη με 1', lambda k: k == 1), ('νικη με 2', lambda k: k == 2), ('νικη 3+', lambda k: k >= 3), ('ηττα φαβορι', lambda k: k < 0)):
        acc_[lab][0] += sum(v for k, v in dm.items() if f(k)); acc_[lab][1] += sum(v for k, v in dk.items() if f(k)); acc_[lab][2] += int(f(g))
n = len(Q)
for lab, (a, b, c) in acc_.items():
    print(f'  {lab:12s} μοντελο {100*a/n:5.1f}% · αγορα {100*b/n:5.1f}% · πραγματικο {100*c/n:5.1f}%')
print(f'  1Χ2 ισοπαλια (αγορα χωρις γκανιοτα) {100*Q.mdr.mean():.1f}% · μοντελο {100*Q.pdr.mean():.1f}% · πραγματικο {100*(Q.gd == 0).mean():.1f}%')

print('\nΕ. ΣΥΝΟΛΟ ΓΚΟΛ (T): μοντελο (xg_h+xg_a) vs αγορα (O/U 2.5 closing) vs πραγματικο')
E = D[D.T_mkt.notna() & D.tot.notna()].copy()
print(f'  n={len(E)} · πραγματικα {E.tot.mean():.3f} · μοντελο {E.T_mod.mean():.3f} (μεροληψια {(E.T_mod - E.tot).mean():+.3f}) · αγορα {E.T_mkt.mean():.3f} ({(E.T_mkt - E.tot).mean():+.3f})')
print(f'  MAE μοντελο {np.mean(np.abs(E.T_mod - E.tot)):.3f} · αγορα {np.mean(np.abs(E.T_mkt - E.tot)):.3f} · corr μοντ {np.corrcoef(E.T_mod, E.tot)[0,1]:.3f} · αγορα {np.corrcoef(E.T_mkt, E.tot)[0,1]:.3f}')
b, se = ols(E.tot.values, [E.T_mkt.values, (E.T_mod - E.T_mkt).values])
print(f'  κλιση: γκολ ~ T αγορας {b[1]:.2f} + b·(μοντ−αγορα) {b[2]:+.2f} (t {b[2]/se[2]:+.1f})')
E['close'] = E.s_mkt.abs() < 0.5
E['lvl'] = pd.qcut(E.T_mkt, 3, labels=['χαμηλη γραμμη', 'μεσαια', 'ψηλη'])
for lab, d in [('κοντινα (|υπεροχη|<0.5)', E[E.close]), ('ανισα', E[~E.close])] + [(str(k), g) for k, g in E.groupby('lvl', observed=True)] + \
              [(w_, E[E.win == w_]) for w_ in ('md<7', 'md7-14', 'md15+')]:
    print(f'    {lab:24s} n{len(d):5d} · πραγμ {d.tot.mean():.2f} · μοντελο {(d.T_mod - d.tot).mean():+.3f} · αγορα {(d.T_mkt - d.tot).mean():+.3f}')
print('    ανα λιγκα: ' + ' · '.join(f"{lg} μοντ {(g.T_mod - g.tot).mean():+.2f}/αγορα {(g.T_mkt - g.tot).mean():+.2f}" for lg, g in E.groupby('league')))

print('\nΣΤ. «ΠΟΥ ΜΠΑΖΕΙ»: ολα τα AH picks του μοντελου στο closing (edge≥10%, 1.70-2.10, κανονες live: +handicap ≥0.5) — δηλωμενη vs αγορα vs πραγματικη καλυψη')
bets = []
for r in M.itertuples():
    for bt in picks.evaluate_bet(r.xh, r.xa, float(r.L), float(r.ah), float(r.aa)):
        side, ud, odds = bt['side'], bt['hcap'], bt['odds']
        dk = picks.gd_dist(max((r.T_mkt + r.s_mkt) / 2, .05), max((r.T_mkt - r.s_mkt) / 2, .05)) if r.T_mkt == r.T_mkt else None
        pwk, ppk = picks.p_cover(dk, side, ud) if dk else (np.nan, np.nan)
        res = picks.settle(r.gd, side, ud, odds)
        bets.append(dict(win=r.win, league=r.league, season=r.season, ud=ud, edge=bt['edge'], p_mod=bt['pw'] / max(1 - bt['pp'], 1e-9),
                         p_mkt=pwk / max(1 - ppk, 1e-9) if pwk == pwk else np.nan, won=1.0 if res > 0.01 else (0.0 if res < -0.01 else np.nan), pnl=res))
B = pd.DataFrame(bets)
for lab, d in [('ΟΛΑ', B)] + [(w_, B[B.win == w_]) for w_ in ('md<7', 'md7-14', 'md15+')] + \
              [(f'edge {lo}-{hi}%', B[(B.edge >= lo / 100) & (B.edge < hi / 100)]) for lo, hi in ((10, 15), (15, 20), (20, 30), (30, 100))] + \
              [(f'γραμμη +{lo}..', B[(B.ud >= lo) & (B.ud < hi)]) for lo, hi in ((0.5, 1), (1, 1.5), (1.5, 2.5), (2.5, 9))]:
    if len(d) < 20: continue
    print(f'  {lab:18s} n{len(d):5d} · μοντελο λεει {100*d.p_mod.mean():.0f}% · αγορα {100*d.p_mkt.mean():.0f}% · πραγματικο {100*d.won.mean():.0f}% · ROI {100*d.pnl.mean():+.1f}% (±{100*d.pnl.std()/np.sqrt(len(d)):.1f})')

print('\nΖ. OPENING → CLOSING: κινειται η αγορα ΠΡΟΣ το μοντελο; (Pinnacle AH)')
O = M[M.s_open.notna()].copy(); O['dl'] = O.s_mkt - O.s_open; O['gap'] = O.s_mod - O.s_open
for lab, d in [('ΟΛΑ', O)] + [(w_, O[O.win == w_]) for w_ in ('md<7', 'md7-14', 'md15+')]:
    b, se = ols(d.dl.values, [d.gap.values])
    big = d[d.gap.abs() >= 0.5]
    toward = np.mean(np.sign(big.dl) == np.sign(big.gap)) if len(big) else np.nan
    print(f'  {lab:8s} n{len(d):5d} · corr(κινηση, χασμα) {np.corrcoef(d.dl, d.gap)[0,1]:+.3f} · κλιση {b[1]:+.3f} (t {b[1]/se[1]:+.1f}) · σε χασμα ≥0.5 (n{len(big)}) κινειται προς εμας {100*toward:.0f}% (κινηθηκε καθολου: {100*(big.dl.abs() > 0.01).mean():.0f}%)')

print('\nΗ. 1Χ2 ΒΑΘΜΟΝΟΜΗΣΗ (favourite-longshot): πιθανοτητα αγορας/μοντελου ανα ζωνη vs πραγματικη συχνοτητα (ολες οι εκβασεις)')
pr_k = np.concatenate([D.mh, D.mdr, D.ma]); pr_m = np.concatenate([D.ph, D.pdr, D.pa]); hit = np.concatenate([D.y == 2, D.y == 1, D.y == 0]).astype(float)
for lo, hi in ((0, .1), (.1, .2), (.2, .3), (.3, .45), (.45, .6), (.6, .75), (.75, 1)):
    mk = (pr_k >= lo) & (pr_k < hi); mm = (pr_m >= lo) & (pr_m < hi)
    print(f'  ζωνη {lo:.2f}-{hi:.2f}: αγορα {100*pr_k[mk].mean():5.1f}% → πραγμ {100*hit[mk].mean():5.1f}% (n{mk.sum()}) · μοντελο {100*pr_m[mm].mean():5.1f}% → πραγμ {100*hit[mm].mean():5.1f}% (n{mm.sum()})')
D.to_csv('core7_diag_rows.csv', index=False); B.to_csv('core7_diag_bets.csv', index=False)
