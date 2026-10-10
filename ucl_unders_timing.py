"""ucl_unders_timing.py — 10/10/2026 (Στελιος: «για το τσαμπιονς λιγκ μονο ... σιγουρα το χρονισμο των unders, και να μπουν μαζι με τα over στο Telegram»).
Ιδια ροη με euro_totals_test (Crown & SBOBET, Nowgoal, ζωνη 1.70-2.10, edge ≥4%) ΑΛΛΑ με τη LIVE μηχανη συνολων απο 10/10 (ισοπαλιες ×1.13 → μαζα ×0.85).
ΣΥΜΠΕΡΑΣΜΑΤΑ ΜΟΝΟ απο UCL νεα μορφη (2425-2526)· παλια μορφη μονο πλαισιο.
Ανα pick (πρωτη εμφανιση ≤72ω, ανα βιβλιο): ROI στην εμφανιση vs «αν περιμενα ως το κλεισιμο», κινηση αγορας πριν/μετα σε γκολ,
και τα αργα picks (≤8ω) μετα απο κοντρα. Κινηση: + = η αγορα πηγε ΚΟΝΤΡΑ στο pick (over: κατεβασε γκολ / under: ανεβασε), − = ηρθε ΠΡΟΣ το pick.
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
PX = R.set_index(['i', 'bk', 'side', 'h'])
P = R[R.inz & (R.e >= .04)].sort_values('h', ascending=False)
first = P.groupby(['i', 'bk', 'side']).head(1).copy()
MT0 = R.sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).mt.first()
MTC = R[R.h == 0].set_index(['i', 'bk', 'side']).mt
sg = np.where(first.side == 'over', -1.0, 1.0)          # + = κοντρα στο pick
first['against_before'] = sg * (first.mt.values - np.array([MT0.get((r.i, r.bk, r.side), np.nan) for r in first.itertuples()]))
first['against_after'] = sg * (np.array([MTC.get((r.i, r.bk, r.side), np.nan) for r in first.itertuples()]) - first.mt.values)
def at_close(r):
    try: return PX.loc[(r.i, r.bk, r.side, 0)]
    except KeyError: return None
cl = [at_close(r) for r in first.itertuples()]
first['pnl_close'] = [x.pnl if x is not None else np.nan for x in cl]
first['e_close'] = [x.e if x is not None else np.nan for x in cl]
first['od_close'] = [x.od if x is not None else np.nan for x in cl]
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    mc = x.dropna(subset=['pnl_close']).groupby('bk').pnl_close.mean()
    return (f'{n:4.0f} picks · στην εμφανιση {100 * m.mean():+6.1f}% (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) +
            f') · αν περιμενα κλεισιμο {100 * mc.mean():+6.1f}% · τιμη {x.od.mean():.2f}→{x.od_close.mean():.2f} · edge στο κλεισ. {100 * x.e_close.mean():+.1f}%')
WIN = ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 12, '18-12ω'), (8, 4, '8-4ω'), (2, 0, '2ω-κλεισ'))
for side in ('under', 'over'):
    X = first[(first.side == side) & (first.comp == 'ChampionsLeague')]
    for lab, Y in (('ΝΕΑ ΜΟΡΦΗ 2425-2526', X[X.sea.isin(NEW)]), ('παλια μορφη 2223-2324 (πλαισιο)', X[~X.sea.isin(NEW)])):
        print(f'\n=== {side.upper()} · UCL {lab} · ΟΛΑ: {cc(Y)}')
        print(f'   {"βγηκε":9s} | ROI / αναμονη / τιμες | κοντρα ΠΡΙΝ | κινηση ΜΕΤΑ (+κοντρα) | % ηρθε προς εμας / % κοντρα')
        for hi, lo, wl in WIN:
            y = Y[(Y.h <= hi) & (Y.h >= lo)]
            if len(y) == 0: continue
            print(f'   {wl:9s} | {cc(y)} | {y.against_before.mean():+.2f} | {y.against_after.mean():+.2f} | '
                  f'{100 * (y.against_after <= -0.05).mean():3.0f}% / {100 * (y.against_after >= 0.05).mean():3.0f}%')
        if 'ΝΕΑ' in lab:
            L = Y[Y.h <= 8]
            print(f'   ΤΕΛΕΥΤΑΙΕΣ 8ω: {cc(L)} · μετα απο κοντρα ≥0.05: {100 * (L.against_before >= 0.05).mean():.0f}%')
            for lb, m in (('κοντρα ≥0.25', L.against_before >= 0.25), ('κοντρα 0.05-0.25', (L.against_before >= 0.05) & (L.against_before < 0.25)), ('χωρις κοντρα', L.against_before < 0.05)):
                print(f'      {lb:16s} {cc(L[m])}')
            E = Y[Y.h > 8]
            print(f'   ΠΡΙΝ ΤΙΣ 8ω (>8ω): {cc(E)}')
            print(f'   ανα γραμμη (ολα): ' + ' · '.join(f'{lb}: {cc(Y[m]).split(" · ")[0]} {cc(Y[m]).split(" · ")[1] if len(Y[m]) else ""}' for lb, m in (('≤2.5', Y.L <= 2.5), ('2.75-3', (Y.L > 2.5) & (Y.L <= 3)), ('≥3.25', Y.L > 3))))
            print(f'   ανα edge: ' + ' · '.join(f'{lb}: {cc(Y[m]).split(" · ")[0]} {cc(Y[m]).split(" · ")[1] if len(Y[m]) else ""}' for lb, m in (('4-8%', Y.e < .08), ('8-12%', (Y.e >= .08) & (Y.e < .12)), ('≥12%', Y.e >= .12))))
# ιδιο ματς: over ΚΑΙ under στη ροη (σε διαφορετικη ωρα)
N = first[(first.comp == 'ChampionsLeague') & first.sea.isin(NEW)]
both = N.groupby(['i', 'bk']).side.nunique()
print(f'\nματς με ΚΑΙ over ΚΑΙ under pick (ιδιο βιβλιο, διαφορετικη ωρα): {int((both > 1).sum())} απο {both.size}')
first.to_pickle('ucl_unders_timing_first.pkl')
