"""uel_full_review.py — 10/10/2026 (Στελιος: «τι εχουμε να δουμε στο europa ... δες τα ολα»). Ιδια ελεγχοι με το Champions League:
1. ΣΥΝΟΛΑ με τη live μηχανη (W2, ισοπαλιες ×0.85), FotMob+FotMob: κατωφλια, LOSO, χρονισμος. ΠΡΟ-ΔΗΛΩΜΕΝΟ για κανονα: κατωφλι LOSO θετικο εκτος δειγματος
   ΚΑΙ θετικο στα 2 βιβλια, στις 2 σεζον νεας μορφης, ≥3/4 σεζον (✓ στον πινακα).
2. ΓΡΑΜΜΕΣ 0 / ±0.25: Κ1 (ιδιο με πανω) · Κ2 LOSO >0 · Κ4 βαθμονομηση · + αξια xG.
3. ΚΑΤΗΓΟΡΙΑ Β χαντικαπ (περιγραφικο). 4. Ο live κανονας φαβορι εντος vs ΤΕΛΙΚΑ xG (μετρο: UCL φαβορι −2.2%).
Crown & SBOBET (Nowgoal), 1.70-2.10, μεσος. Νεα μορφη = 2425-2526 (36 ομαδες και στο Europa).
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
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def _cat(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return '?'
    a, b = sorted((_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')))
    return a + b
SRCC = [_cat(i) for i in range(len(MIDS))]

import pickle as _pkl
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
UEL = np.where(COMP == 'EuropaLeague')[0]
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
def cc(x, col='pnl'):
    if len(x) == 0: return '—'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return (f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} ('
            + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')')
def passes(x):
    if len(x) == 0: return False
    m = x.groupby('bk').pnl.mean(); ps = x.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    return bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
XG = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []
        if not sh: continue
        hid = int(m['home']['id'])
        XG[str(mid)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid),
                        sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
def xg_value(i, side, ln, o):
    x = XG.get(str(MIDS[i]))
    if not x: return np.nan
    pw, pp = picks.p_cover(picks.gd_dist(max(x[0], .05), max(x[1], .05)), side, ln)
    return o / ((1 - pp) / pw) - 1 if pw > 0 else np.nan
# ======================= 1. ΣΥΝΟΛΑ =======================
print('=' * 100 + NL + '1. ΣΥΝΟΛΑ EUROPA LEAGUE — live μηχανη (W2, ισοπαλιες ×0.85), ματς FotMob+FotMob, 1.70-2.10, πρωτη εμφανιση ≤72ω, Crown/SBOBET')
rows = []
for i in UEL:
    if SRCC[i] != 'FF': continue
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(MIDS[i], bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            for side, od, pw, pl in (('over', o, po, pu), ('under', un, pu, po)):
                if not (1.70 <= od <= 2.10): continue
                rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], L=L, od=od, e=pw * (od - 1) * (1 - picks.MARGIN) - pl,
                                 pnl=settle(tot, L, od, side == 'over'), mt=mtot(L, o, un)))
RT = pd.DataFrame(rows)
K1 = RT[(RT.h == 0) & (RT.side == 'over') & (RT.bk == 'Crown')]
print(f'   βαθμονομηση (κλεισιμο Crown, {len(K1)} ματς): γκολ {(GH[K1.i] + GA[K1.i]).mean():.2f} · μοντελο {(OH[K1.i] + OA[K1.i]).mean():.2f} · αγορα {K1.mt.mean():.2f} · νεα μορφη: '
      f'γκολ {(GH[K1[K1.sea.isin(NEW)].i] + GA[K1[K1.sea.isin(NEW)].i]).mean():.2f} μοντελο {(OH[K1[K1.sea.isin(NEW)].i] + OA[K1[K1.sea.isin(NEW)].i]).mean():.2f} αγορα {K1[K1.sea.isin(NEW)].mt.mean():.2f}')
def tstream(side, th, seas=SEAS):
    y = RT[(RT.side == side) & (RT.e >= th) & RT.sea.isin(seas)].sort_values('h', ascending=False)
    return y.groupby(['i', 'bk']).head(1)
TH = (0, .02, .04, .06, .08, .10, .12, .14)
for side in ('over', 'under'):
    print(f'   {side.upper()} ανα κατωφλι (4 σεζον):')
    for th in TH:
        x = tstream(side, th)
        print(f'      ≥{int(th * 100):2d}% {cc(x)} {"✓" if passes(x) else ""}')
    outs = []
    for hold in SEAS:
        tr = [s for s in SEAS if s != hold]
        sc = {th: tstream(side, th, tr).groupby('bk').pnl.mean().mean() for th in TH}
        t = max(sc, key=lambda k: sc[k]); te = tstream(side, t, (hold,))
        outs.append((hold, t, te))
    n = sum(o[2].groupby('bk').size().mean() for o in outs if len(o[2]))
    tot = sum(o[2].groupby('bk').pnl.mean().mean() * o[2].groupby('bk').size().mean() for o in outs if len(o[2]))
    print('      LOSO: ' + ' · '.join(f'{h} ≥{int(t * 100)}% → {cc(x)[:28]}' for h, t, x in outs) + f' · ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ {100 * tot / max(n, 1):+.1f}% ({n:.0f})')
    best = pd.Series([o[1] for o in outs]).mode().iloc[0]
    F = tstream(side, best).copy()
    C0 = RT[RT.h == 0].set_index(['i', 'bk', 'side'])
    F['pc'] = [C0.pnl.get((r.i, r.bk, side), np.nan) for r in F.itertuples()]
    F['mva'] = [(C0.mt.get((r.i, r.bk, side), np.nan) - r.mt) * (1 if side == 'over' else -1) for r in F.itertuples()]
    print(f'      ΧΡΟΝΙΣΜΟΣ στο συχνοτερο κατωφλι LOSO (≥{int(best * 100)}%): ολα {cc(F)} · αν περιμενα κλεισ. {100 * F.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+.1f}% · '
          f'αγορα μετα προς εμας {F.mva.mean():+.2f} γκολ')
    for hi, lo, wl in ((72, 48, '72-48ω'), (36, 12, '36-12ω'), (8, 0, '8ω-κλεισ')):
        y = F[(F.h <= hi) & (F.h >= lo)]
        if len(y): print(f'         {wl:9s} {cc(y)}')
# ======================= 2. DNB / ±0.25 =======================
print(NL + '=' * 100 + NL + '2. ΓΡΑΜΜΕΣ 0 (DNB) / −0.25 / +0.25 — EUROPA LEAGUE, FotMob+FotMob, live μηχανη χαντικαπ, σωστα τεταρτα, @4%, πρωτη εμφανιση ≤72ω')
rows = []; SN = {}
for i in UEL:
    if SRCC[i] != 'FF': continue
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s; SN[(i, bk, h)] = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) >= 0.5: continue
                g = '0 (DNB)' if abs(ln) < .01 else ('−0.25' if ln < 0 else '+0.25')
                pw, pp = cover_q(D, side, ln)
                rows.append(dict(i=i, bk=bk, h=h, grp=g, side=side, sea=SEA[i], ln=ln, od=o, home=side == 1, pw=pw, pp=pp,
                                 e=edge(pw, pp, o), pnl=picks.settle(GD[i], side, ln, o)))
RL = pd.DataFrame(rows)
def lfirst(x, th):
    y = x[x.e >= th].sort_values('h', ascending=False)
    return y.groupby(['i', 'bk', 'side']).head(1).copy()
for g in ('0 (DNB)', '−0.25', '+0.25'):
    X = RL[RL.grp == g]; F = lfirst(X, .04)
    print(f'   {g}: 4 σεζον {cc(F)} · νεα μορφη {cc(F[F.sea.isin(NEW)])}')
    outs = []
    for hold in SEAS:
        tr = X[X.sea != hold]
        sc = {t: lfirst(tr, t).groupby('bk').pnl.mean().mean() for t in (0, .02, .04, .06, .08, .10, .12, .14)}
        t = max(sc, key=lambda k: sc[k]); te = lfirst(X[X.sea == hold], t)
        outs.append((te.groupby('bk').pnl.mean().mean() if len(te) else 0, te.groupby('bk').size().mean() if len(te) else 0))
    loso = sum(a * b for a, b in outs) / max(sum(b for a, b in outs), 1)
    pred = (F.pw / (1 - F.pp)).mean(); real = (F.pnl > 0).sum() / max((F.pnl != 0).sum(), 1)
    opp = [SN[(r.i, r.bk, r.h)][2] if r.side == 1 else SN[(r.i, r.bk, r.h)][1] for r in F.itertuples()]
    mk = (1 / F.od / (1 / F.od + 1 / np.array(opp))).mean()
    F['xv'] = [xg_value(r.i, r.side, r.ln, r.od) for r in F.itertuples()]
    k1 = passes(F); k2 = loso > 0; k4 = abs(pred - real) <= max(.05, abs(mk - real))
    print(f'      LOSO εκτος δειγματος {100 * loso:+.1f}% · P κερδους μοντελο {100 * pred:.0f}% / αγορα {100 * mk:.0f}% / πραγματικο {100 * real:.0f}% · αξια xG {100 * F.xv.mean():+.1f}% · '
          f'εντος {cc(F[F.home])[:34]} · εκτος {cc(F[~F.home])[:34]} · Κ1 {"✓" if k1 else "✗"} Κ2 {"✓" if k2 else "✗"} Κ4 {"✓" if k4 else "✗"}')
# ======================= 3. ΚΑΤΗΓΟΡΙΑ Β ΧΑΝΤΙΚΑΠ =======================
print(NL + '=' * 100 + NL + '3. ΚΑΤΗΓΟΡΙΑ Β (μια ομαδα χωρις FotMob) — EUROPA LEAGUE, χαντικαπ ΧΩΡΙΣ διορθωση, «μεγαλη» = η ομαδα FotMob')
def cat_b(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return None
    sh, sa = _LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')
    return (sh == 'F') if (sh == 'F') != (sa == 'F') else None
B = [(i, cat_b(i)) for i in UEL if cat_b(i) is not None]
bi = np.array([i for i, _ in B]); fh = np.array([f for _, f in B])
bg = np.where(fh, GH[bi], GA[bi]); sg = np.where(fh, GA[bi], GH[bi]); bl = np.where(fh, LH_N[bi], LA_N[bi]); sl = np.where(fh, LA_N[bi], LH_N[bi])
print(f'   {len(bi)} ματς · μεγαλη βαζει {bg.mean():.2f} (μοντελο {bl.mean():.2f}) · μικρη {sg.mean():.2f} (μοντελο {sl.mean():.2f}) · διαφορα {(bg - sg).mean():+.2f} vs μοντελο {(bl - sl).mean():+.2f}')
for lab, msk in (('μεγαλη = φαβορι μοντελου', bl > sl), ('μεγαλη = αουτσαιντερ', bl <= sl), ('μεγαλη εντος', fh), ('μεγαλη εκτος', ~fh)):
    print(f'      {lab:26s} n{msk.sum():3d} · διαφορα πραγμ {(bg - sg)[msk].mean():+.2f} vs μοντελο {(bl - sl)[msk].mean():+.2f}')
rows = []
for i, f_h in B:
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                role = 'fav' if ln < 0 else 'dog'; big = (side == 1) == f_h
                pw, pp = cover_q(D, side, ln) if role == 'fav' else picks.p_cover(D, side, ln)
                rows.append(dict(i=i, bk=bk, h=h, k=role + ('_μεγαλης' if big else '_μικρης'), side=side, home=side == 1, sea=SEA[i], ln=ln, od=o,
                                 e=edge(pw, pp, o), pnl=picks.settle(GD[i], side, ln, o)))
RB = pd.DataFrame(rows)
for k, th in (('fav_μεγαλης', .04), ('fav_μεγαλης', .10), ('dog_μικρης', .10), ('dog_μικρης', .04), ('fav_μικρης', .04), ('dog_μεγαλης', .10)):
    y = RB[(RB.k == k) & (RB.e >= th)].sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
    print(f'   {k:12s} ≥{int(th * 100):2d}% {cc(y)} · εντος {cc(y[y.home])[:30]} · εκτος {cc(y[~y.home])[:30]}')
# ======================= 4. ΦΑΒΟΡΙ ΕΝΤΟΣ (live κανονας) vs ΤΕΛΙΚΑ xG =======================
print(NL + '=' * 100 + NL + '4. ΚΑΝΟΝΑΣ UEL ΦΑΒΟΡΙ ΕΝΤΟΣ (80% xG, ≤−0.5, ≥4%, 12-36ω, FotMob+FotMob) vs ΤΕΛΙΚΑ xG (μεθοδος Pick History)')
D8 = _pkl.load(open('euro_blend_dump_0.8.pkl', 'rb'))
assert list(D8['MIDS']) == list(MIDS)
rows = []
for i in UEL:
    if not D8['FM'][i]: continue
    D = sdist(D8['LH'][i], D8['LA'][i])
    for bk in ('Crown', 'SBOBET'):
        for h in (36, 24, 18, 12):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or ln > -0.5: continue
                pw, pp = cover_q(D, side, ln); e = edge(pw, pp, o)
                if e >= .04:
                    rows.append(dict(i=i, bk=bk, h=h, home=side == 1, side=side, sea=SEA[i], ln=ln, od=o, e=e, pnl=picks.settle(GD[i], side, ln, o)))
RF = pd.DataFrame(rows).sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1).copy()
RF['xv'] = [xg_value(r.i, r.side, r.ln, r.od) for r in RF.itertuples()]
for lab, y in (('ΦΑΒΟΡΙ ΕΝΤΟΣ (ο κανονας)', RF[RF.home]), ('φαβορι εκτος (για συγκριση, εκτος κανονα)', RF[~RF.home])):
    y = y.dropna(subset=['xv'])
    print(f'   {lab:42s} {cc(y)} · ΑΞΙΑ xG {100 * y.groupby("bk").xv.mean().mean():+.1f}% (θετικη {100 * (y.xv > 0).mean():.0f}%) · ανα σεζον xG ' +
          ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in y.groupby('sea').xv.mean().items()))
print('   μετρο συγκρισης: UCL live φαβορι ROI +15.0% / αξια xG −2.2% (ucl_other_lines_xg) — το xG «τιμωρει» τα φαβορι')
