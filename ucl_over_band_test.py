"""ucl_over_band_test.py — 10/10/2026 (Στελιος: «για δες το και το οβερ»). ucl_edge_vs_reality: τα over (κατηγορια Α) με edge 4-8% −23% (121 picks, 4 σεζον).
Ερωτημα: ανεβαινει το κατωφλι των over 4% → 8%; Live μηχανη (W2 + κ, ισοπαλιες ×0.85), ματς FotMob+FotMob, 1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET.
ΠΡΟ-ΔΗΛΩΜΕΝΑ: (α) ζωνη 4-8% αρνητικη ΚΑΙ στα 2 βιβλια, ≥3/4 σεζον, ΚΑΙ στις 2 σεζον νεας μορφης · (β) LOSO (4/6/8/10/12%) εκτος δειγματος ≥ σταθερο 4% ·
(γ) μοναδες με 8% ≥ μοναδες με 4% στη νεα μορφη. ΟΛΑ → κατωφλι 8%. Αλλιως μενει 4%.
"""
import sys, io, os, json, glob, contextlib
DRAW_SCALE = 0.85
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
picks, KO = u['picks'], u['KO']
MIDS, COMP, FM, SEA = u['MIDS'], np.asarray(u['COMP']), u['FM'], np.asarray(u['SEA'])
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA = np.asarray(w['GH']), np.asarray(w['GA'])
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
import euro_shadow_scan as ES
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
TOU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        if bk is None: continue
        seq = sorted((int(mt), pl(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or []) if mt and pl(gg) is not None)
        if seq: TOU[(str(r['mid']), bk)] = seq
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
def mtot(L, o, un):
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i, mid in enumerate(MIDS):
    if not FM[i] or not ucl[i]: continue
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(mid, bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L); mt = mtot(L, o, un)
            for side, od, p_w, p_l in (('over', o, po, pu), ('under', un, pu, po)):
                e = p_w * (od - 1) * (1 - picks.MARGIN) - p_l
                rows.append(dict(i=i, bk=bk, h=h, side=side, comp=COMP[i], sea=SEA[i], L=L, od=od, e=e, inz=1.70 <= od <= 2.10,
                                 pnl=settle(tot, L, od, side == 'over'), pos=(mt if side == 'over' else -mt), mt=mt, model=OH[i] + OA[i], tot=tot))
R = pd.DataFrame(rows)


NL = chr(10)
NEW = ('2425', '2526'); SEAS = ('2223', '2324', '2425', '2526')
O = R[(R.side == 'over') & R.inz & (R.comp == 'ChampionsLeague')]
def stream(th, seas=SEAS, hi=9):
    y = O[(O.e >= th) & O.sea.isin(seas)].sort_values('h', ascending=False)
    y = y.groupby(['i', 'bk']).head(1)
    return y[y.e < hi]
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
band = stream(.04, hi=.08)
print('ΖΩΝΗ 4-8% (picks που μπαινουν με 4% και ΔΕΝ θα εμπαιναν με 8% — πρωτη εμφανιση με edge 4-8%):')
print('   4 σεζον: ' + cc(band)); print('   νεα μορφη: ' + cc(band[band.sea.isin(NEW)]))
m = band.groupby('bk').pnl.mean(); ps = band.groupby('sea').pnl.mean()
ka = bool((m < 0).all()) and (ps < 0).sum() >= 3 and bool((ps[ps.index.isin(NEW)] < 0).all())
print(NL + 'ΜΟΝΑΔΕΣ ανα κατωφλι (νεα μορφη / 4 σεζον):')
for th in (.04, .06, .08, .10, .12):
    print(f'   ≥{int(th * 100):2d}%  νεα μορφη {cc(stream(th, NEW))}  ||  4 σεζον {cc(stream(th))}')
outs = []
for hold in SEAS:
    tr = [s for s in SEAS if s != hold]
    sc = {t: stream(t, tr).groupby('bk').pnl.mean().mean() for t in (.04, .06, .08, .10, .12)}
    t = max(sc, key=lambda k: sc[k]); te = stream(t, (hold,)); f4 = stream(.04, (hold,))
    outs.append((hold, t, te, f4))
def agg(xs):
    n = sum(x.groupby('bk').size().mean() for x in xs if len(x)); u = sum(x.groupby('bk').pnl.mean().mean() * x.groupby('bk').size().mean() for x in xs if len(x))
    return u / max(n, 1), n, u
lo, ln_, lu = agg([o[2] for o in outs]); fo, fn, fu = agg([o[3] for o in outs])
print(NL + 'LOSO: ' + ' · '.join(f'{h} διαλεξε ≥{int(t * 100)}%' for h, t, _, _ in outs) + f' · εκτος δειγματος {100 * lo:+.1f}% ({ln_:.0f} picks, {lu:+.1f}μ) vs σταθερο 4% {100 * fo:+.1f}% ({fn:.0f}, {fu:+.1f}μ)')
kb = lu >= fu
u8 = stream(.08, NEW).groupby('bk').pnl.sum().mean(); u4 = stream(.04, NEW).groupby('bk').pnl.sum().mean()
kc = u8 >= u4
print(NL + f'(α) ζωνη 4-8% αρνητικη παντου: {"✓" if ka else "✗"} · (β) LOSO ≥ σταθερο 4% (μοναδες): {"✓" if kb else "✗"} · (γ) νεα μορφη μοναδες 8% {u8:+.1f} vs 4% {u4:+.1f}: {"✓" if kc else "✗"}')
print('ΑΠΟΦΑΣΗ: ' + ('ΚΑΤΩΦΛΙ OVER → 8%' if (ka and kb and kc) else 'μενει 4%'))
