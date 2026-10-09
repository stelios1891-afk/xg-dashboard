"""
euro_favfix_test.py — 9/10/2026 (Στελιος: «η συγκεκριμενη διορθωση στα φαβορι πως θα ερθει;»). ΣΤΟΧΕΥΜΕΝΗ ΔΙΟΡΘΩΣΗ ΦΑΒΟΡΙ.
Για καθε ματς με s = διαφορα λ μοντελου (φαβορι − αουτσαιντερ):  λ_φαβ × e^(−a·s) · λ_αουτ × e^(+b·s), με a,b ΧΩΡΙΣΤΑ για φαβορι ΕΝΤΟΣ / ΕΚΤΟΣ
και ΑΝΑ ΔΙΟΡΓΑΝΩΣΗ. Μαθαινονται απο τις ΠΡΑΓΜΑΤΙΚΕΣ ευκαιριες (xG ευρωπαικου ματς, Poisson ψευδο-πιθανοφανεια) με LOSO (3 σεζον → 4η).
Βασεις: σημερινη μιξη 60% (euro_v6w2_preds_emps) και 80% xG (euro_v6w2_preds_bl0.8).
ΠΡΟ-ΔΗΛΩΣΗ (ανα διοργανωση): (1) πιθανοφανεια ΓΚΟΛ εκτος δειγματος καλυτερη σε ≥3/4 σεζον · (2) μεροληψια φαβορι εκτος |·| < 0.15 ΚΑΙ
εντος μενει εντος ±0.15 · (3) πληροφορια β πανω απο το κλεισιμο ≥ σημερα · (4) picks: μοναδες ≥ σημερα ΚΑΙ καλυτερες σε ≥3/4 σεζον.
UCL: εφαρμοζεται μονο αν περασει χωριστα.
"""
import sys, os, io, json, math, contextlib, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
BASE = sys.argv[1] if len(sys.argv) > 1 else 'euro_v6w2_preds_emps.pkl'
TARGET = sys.argv[2] if len(sys.argv) > 2 else 'xg'      # 'xg' = μαθαινει απο ευκαιριες · 'goals' = απο γκολ
os.environ['W2_IN'] = BASE
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'ff'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, GH, GA, SEA, COMP, LH_N, LA_N, SNAP, make_picks, fm, picks = (g[k] for k in (
    'MIDS', 'GD', 'GH', 'GA', 'SEA', 'COMP', 'LH_N', 'LA_N', 'SNAP', 'make_picks', 'fm', 'picks'))
XG = {}
for sea in ('2223', '2324', '2425', '2526'):
    for mid, m in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not m.get('shots') or m.get('hs') is None: continue
        h, a = int(m['home']['id']), int(m['away']['id']); agg = {h: 0.0, a: 0.0}
        for s in m['shots']:
            if s.get('xg') is not None and s.get('tid') in agg: agg[s['tid']] += 0.25 if s.get('sit') == 'Penalty' else s['xg']
        XG[str(mid)] = (agg[h], agg[a])
XH = np.array([XG.get(m, (np.nan, np.nan))[0] for m in MIDS]); XA = np.array([XG.get(m, (np.nan, np.nan))[1] for m in MIDS])
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
SM = np.array([msup(*SNAP[m], LH_N[i] + LA_N[i]) if m in SNAP else np.nan for i, m in enumerate(MIDS)])
FH = LH_N >= LA_N; S_ = np.abs(LH_N - LA_N)
def apply(par, comp):
    """par = (a_εντος, b_εντος, a_εκτος, b_εκτος) για φαβορι εντος/εκτος, μονο στη διοργανωση comp."""
    ah, bh, aa, ba = par; m = COMP == comp
    a = np.where(FH, ah, aa); b = np.where(FH, bh, ba)
    lf = np.where(FH, LH_N, LA_N) * np.exp(-a * S_); ld = np.where(FH, LA_N, LH_N) * np.exp(b * S_)
    lh = np.where(FH, lf, ld); la = np.where(FH, ld, lf)
    return np.where(m, lh, LH_N), np.where(m, la, LA_N)
def pll(yh, ya, lh, la, m):
    ok = m & np.isfinite(yh) & np.isfinite(ya)
    return float(np.sum(yh[ok] * np.log(lh[ok]) - lh[ok] + ya[ok] * np.log(la[ok]) - la[ok]))
AG = np.round(np.arange(-0.06, 0.31, 0.03), 2); BG = np.round(np.arange(-0.09, 0.25, 0.03), 2)
def fit(tr, comp):
    best = {}
    for venue in ('εντος', 'εκτος'):
        vm = tr & (FH if venue == 'εντος' else ~FH) & (S_ >= 0.25)
        YH, YA = (XH, XA) if TARGET == 'xg' else (GH.astype(float), GA.astype(float))
        bb = max(itertools.product(AG, BG), key=lambda p: pll(YH, YA, *apply((p[0], p[1], p[0], p[1]), comp), vm))
        best[venue] = bb
    return (best['εντος'][0], best['εντος'][1], best['εκτος'][0], best['εκτος'][1])
def bias(lh, la, m):
    s = lh - la
    return (GD - s)[m & (s >= .5)].mean(), (-(GD - s))[m & (s <= -.5)].mean()
def beta(lh, la, m):
    m = m & np.isfinite(SM); y = GD[m] - SM[m]; X = np.c_[np.ones(m.sum()), (lh - la)[m] - SM[m]]
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    return b[1], b[1] / math.sqrt(np.linalg.inv(X.T @ X)[1, 1] * (e @ e) / (len(y) - 2))
SEAS = ('2223', '2324', '2425', '2526')
P0 = make_picks(LH_N, LA_N)
print(f'ΒΑΣΗ: {BASE} · στοχος εκμαθησης: {TARGET}')
for comp in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague'):
    m = COMP == comp; LHa, LAa = LH_N.copy(), LA_N.copy(); dll = {}; ch = {}
    for te in SEAS:
        tr = m & (SEA != te); tm = m & (SEA == te)
        par = fit(tr, comp); ch[te] = par; lh, la = apply(par, comp)
        dll[te] = pll(GH.astype(float), GA.astype(float), lh, la, tm) - pll(GH.astype(float), GA.astype(float), LH_N, LA_N, tm)
        LHa[tm] = lh[tm]; LAa[tm] = la[tm]
    P = make_picks(LHa, LAa); x = P[P.comp == comp]; x0 = P0[P0.comp == comp]
    eh0, ea0 = bias(LH_N, LA_N, m); eh1, ea1 = bias(LHa, LAa, m); b0, t0 = beta(LH_N, LA_N, m); b1, t1 = beta(LHa, LAa, m)
    ps, p0 = x.groupby('sea').pnl.mean(), x0.groupby('sea').pnl.mean()
    c1 = sum(v > 0 for v in dll.values()) >= 3; c2 = abs(ea1) < 0.15 and abs(eh1) <= 0.15; c3 = b1 >= b0
    c4 = x.pnl.sum() >= x0.pnl.sum() and int((ps.reindex(p0.index).fillna(-9) > p0).sum()) >= 3
    print(f'\n[{comp}]  LOSO τιμες (a/b εντος · a/b εκτος): ' + ' '.join(f'{s}:{v[0]:.2f}/{v[1]:+.2f}·{v[2]:.2f}/{v[3]:+.2f}' for s, v in ch.items()))
    print(f'   Δπιθ γκολ ' + ' '.join(f'{s}:{v:+.1f}' for s, v in dll.items()) + f' · μεροληψια φαβ εντος {eh0:+.3f}→{eh1:+.3f} · εκτος {ea0:+.3f}→{ea1:+.3f}'
          f' · πληροφορια β {b0:+.2f} (t {t0:+.1f}) → {b1:+.2f} (t {t1:+.1f})')
    for role, hm, lab in (('fav', True, 'φαβ εντος'), ('fav', False, 'φαβ εκτος'), ('dog', True, 'αουτ εντος'), ('dog', False, 'αουτ εκτος')):
        print(f'   {lab:10s} {fm(x[(x.role == role) & (x.home == hm)])[:32]} · σημερα {fm(x0[(x0.role == role) & (x0.home == hm)])[:32]}')
    print(f'   ΟΛΑ {fm(x)} · σημερα {fm(x0)} → (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} (3){"✓" if c3 else "✗"} (4){"✓" if c4 else "✗"} {"ΠΕΡΝΑ" if all((c1, c2, c3, c4)) else "ΔΕΝ ΠΕΡΝΑ"}')
