"""ucl_totals_threshold_loso.py — 10/10/2026 (Στελιος: «θες να αφησουμε το loso να το διαλεξει?»). Βαση: ucl_totals_threshold.py (Στελιος: «το κατωφλι edge εχει δοκιμαστει στα συνολα?»).
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


PC = R[R.h == 0].set_index(['i', 'bk', 'side']).pnl
TH = (0, .02, .04, .06, .08, .10, .12, .14)
SEAS = ('2223', '2324', '2425', '2526')
def stream(side, th, seas):
    P = R[R.inz & (R.e >= th) & (R.side == side) & R.sea.isin(seas)].sort_values('h', ascending=False)
    return P.groupby(['i', 'bk']).head(1)
def roi(f):
    return f.groupby('bk').pnl.mean().mean() if len(f) else np.nan
for side in ('over', 'under'):
    for lab, pool in (('ΜΟΝΟ ΝΕΑ ΜΟΡΦΗ (2 σεζον)', ('2425', '2526')), ('ΚΑΙ ΟΙ 4 ΣΕΖΟΝ', SEAS)):
        print(f'\n=== {side.upper()} · LOSO {lab}: διαλεγει κατωφλι στις αλλες σεζον (max ROI), το κρινει στην κρυμμενη')
        tot = []; out = []
        for hold in pool:
            train = [s for s in pool if s != hold]
            sc = {th: roi(stream(side, th, train)) for th in TH}
            best = max(sc, key=lambda t: sc[t])
            f = stream(side, best, (hold,)); f4 = stream(side, .04, (hold,))
            out.append((hold, best, roi(f), len(f) / 2, roi(f4), len(f4) / 2))
            print(f'   κρυμμενη {hold}: διαλεξε ≥{int(best * 100)}% (train {100 * sc[best]:+.1f}%) → στην {hold} {100 * roi(f):+.1f}% ({len(f) / 2:.0f} picks) · σταθερο 4%: {100 * roi(f4):+.1f}% ({len(f4) / 2:.0f})')
        w = sum(o[2] * o[3] for o in out) / sum(o[3] for o in out); w4 = sum(o[4] * o[5] for o in out) / sum(o[5] for o in out)
        print(f'   ΣΥΝΟΛΟ εκτος δειγματος: LOSO {100 * w:+.1f}% ({sum(o[3] for o in out):.0f} picks) vs σταθερο 4% {100 * w4:+.1f}% ({sum(o[5] for o in out):.0f})')
