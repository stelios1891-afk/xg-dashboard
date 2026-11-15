"""ucl_totals_threshold.py — 10/10/2026 (Στελιος: «το κατωφλι edge εχει δοκιμαστει στα συνολα?»).
LIVE μηχανη συνολων (ισοπαλιες ×0.85), UCL, Crown & SBOBET, ζωνη 1.70-2.10. Για καθε κατωφλι 0-14%: ροη «πρωτη εμφανιση ≤72ω με edge ≥ κατωφλι»
(η ροη ΑΛΛΑΖΕΙ με το κατωφλι — ενα ματς με 5% στις 72ω και 9% στις 20ω μπαινει στις 72ω @4% αλλα στις 20ω @8%).
ROI στην εμφανιση + αν περιμενα το κλεισιμο, ανα βιβλιο & σεζον. Νεα μορφη = κρισιμο, παλια = πλαισιο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ιδιο με euro_totals_test): ενα κατωφλι «περνα» αν θετικο ΚΑΙ στα 2 βιβλια, ΚΑΙ στις 2 σεζον νεας μορφης, ΚΑΙ στα 2 γειτονικα κατωφλια.
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

NEW = ('2425', '2526')
PC = R[R.h == 0].set_index(['i', 'bk', 'side']).pnl
TH = (0, .02, .04, .06, .08, .10, .12, .14)
res = {}
for side in ('over', 'under'):
    for fmt, seas in (('ΝΕΑ ΜΟΡΦΗ', NEW), ('παλια μορφη', ('2223', '2324'))):
        print(f'\n=== {side.upper()} · UCL {fmt}')
        print(f'   {"κατωφλι":8s} {"picks":>5s} {"εμφανιση":>9s} {"Crown":>6s} {"SBOBET":>6s}   ανα σεζον       {"κλεισιμο":>9s}')
        for th in TH:
            P = R[R.inz & (R.e >= th) & (R.side == side) & R.sea.isin(seas)].sort_values('h', ascending=False)
            f = P.groupby(['i', 'bk']).head(1).copy()
            if len(f) == 0: continue
            f['pc'] = [PC.get((r.i, r.bk, r.side), np.nan) for r in f.itertuples()]
            b = f.groupby('bk').pnl.mean(); ps = f.groupby('sea').pnl.mean(); n = f.groupby('bk').size().mean()
            res[(side, fmt, th)] = (b.min() > 0 and (ps > 0).all())
            print(f'   ≥{int(th * 100):2d}%     {n:5.0f} {100 * b.mean():+8.1f}% {100 * b.get("Crown", np.nan):+5.0f}% {100 * b.get("SBOBET", np.nan):+5.0f}%   ' +
                  ' '.join(f'{s[2:]}:{100 * v:+4.0f}' for s, v in ps.items()) + f'   {100 * f.groupby("bk").pc.mean().mean():+8.1f}%')
        if fmt == 'ΝΕΑ ΜΟΡΦΗ':
            ok = [th for th in TH if res.get((side, fmt, th))]
            pas = [th for i, th in enumerate(TH) if res.get((side, fmt, th)) and (i == 0 or res.get((side, fmt, TH[i - 1]))) and (i == len(TH) - 1 or res.get((side, fmt, TH[i + 1])))]
            print(f'   θετικα σε 2 βιβλια & 2 σεζον: {[int(t * 100) for t in ok]} · ΠΕΡΝΟΥΝ (και οι 2 γειτονες): {[int(t * 100) for t in pas]}')
