"""uecl_full_review.py — 11/10/2026 (Στελιος: «παμε στο conference — βαθια αναλυση οπως στο τσαμπιονς λιγκ, μηχανισμοι, προβληματα κοντρα στην αγορα»).
Conference League 2223-2526, Crown & SBOBET (Nowgoal). Α βαθμονομηση & πληροφορια μοντελου ανα κατηγορια πηγης/φαση · Β χαντικαπ (σημερινοι κανονες UECL,
κατωφλια, LOSO, χρονισμος) · Γ γραμμες 0/±0.25 · Δ συνολα κατηγορια Α · Ε συνολα κατηγοριες Β & Γ · ΣΤ τυφλα στο κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ για υποψηφιο κανονα: κατωφλι LOSO θετικο εκτος δειγματος ΚΑΙ θετικο στα 2 βιβλια, ≥3/4 σεζον, ΚΑΙ οι 2 σεζον νεας μορφης (✓ ΠΕΡΝΑ).
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
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
CMP = 'ConferenceLeague'
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
def cat(i):
    s = SRCC[i]
    return 'A' if s == 'FF' else ('B' if 'F' in s else 'G')
UI = [i for i in range(len(MIDS)) if COMP[i] == CMP and VI.get(str(MIDS[i])) is not None]
PH = {i: V6['phase'][VI[str(MIDS[i])]] for i in UI}
def cc(x, col='pnl'):
    if len(x) == 0: return '—'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
def passes(x):
    if len(x) == 0: return False
    m = x.groupby('bk').pnl.mean(); ps = x.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    return bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
def first(x, th, keys=('i', 'bk', 'side')):
    y = x[x.e >= th].sort_values('h', ascending=False)
    return y.groupby(list(keys)).head(1)
def loso(X, grid, keys=('i', 'bk', 'side')):
    outs = []
    for hold in SEAS:
        tr = X[X.sea != hold]
        if len(tr) == 0: continue
        sc = {t: first(tr, t, keys).groupby('bk').pnl.mean().mean() for t in grid}
        sc = {k: v for k, v in sc.items() if np.isfinite(v)}
        if not sc: continue
        t = max(sc, key=lambda k: sc[k]); te = first(X[X.sea == hold], t, keys)
        outs.append((hold, t, te))
    allx = pd.concat([o[2] for o in outs]) if outs else pd.DataFrame()
    return outs, allx
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ =================
print('Α. ΒΑΘΜΟΝΟΜΗΣΗ — Conference League, ματς με κλεισιμο (Crown, αλλιως SBOBET)')
cal = []
for i in UI:
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    so = snap_ou(MIDS[i], 'Crown', 0) or snap_ou(MIDS[i], 'SBOBET', 0)
    if not s or LH_N[i] <= 0: continue
    cal.append(dict(i=i, sea=SEA[i], ph=PH[i], cat=cat(i), gh=GH[i], ga=GA[i], lh=LH_N[i], la=LA_N[i], oh_=OH[i], oa_=OA[i],
                    kgd=implied_margin(i, *s), ktot=mtot(*so) if so else np.nan))
C = pd.DataFrame(cal); C['gd'] = C.gh - C.ga; C['mgd'] = C.lh - C.la; C['rk'] = C.gd - C.kgd; C['dis'] = C.mgd - C.kgd
for lab, m in (('4 σεζον, ολα', C.sea.isin(SEAS)), ('νεα μορφη, ολα', C.sea.isin(NEW)), ('νεα μορφη, φαση λιγκας', C.sea.isin(NEW) & (C.ph == 'league')),
               ('νεα μορφη, νοκ-αουτ', C.sea.isin(NEW) & (C.ph == 'KO'))):
    for cg in ('A', 'B', 'G'):
        x = C[m & (C.cat == cg)]
        if len(x) < 15: continue
        b, sb = ols(x.dis.values, x.rk.values)
        print(f'   {lab:24s} κατηγορια {cg} n{len(x):3d} · γηπ γκολ {x.gh.mean():.2f}/μοντ {x.lh.mean():.2f} · φιλοξ {x.ga.mean():.2f}/{x.la.mean():.2f} · '
              f'διαφορα πραγμ {x.gd.mean():+.2f} μοντ {x.mgd.mean():+.2f} αγορα {x.kgd.mean():+.2f} · συνολο πραγμ {(x.gh + x.ga).mean():.2f} μοντ(W2) {(x.oh_ + x.oa_).mean():.2f} αγορα {x.ktot.mean():.2f} · '
              f'πληροφορια μοντελου κλιση {b:+.2f} (t {b / sb:+.1f})')
# ================= Β. ΧΑΝΤΙΚΑΠ =================
print(NL + 'Β. ΧΑΝΤΙΚΑΠ (κατηγορια Α, σημερινοι κανονες UECL: φαβ ≥4% σωστα τεταρτα · dog ≥10% p_cover · |γραμμη| ≥0.5 · 1.70-2.10 · πρωτη εμφανιση ≤72ω)')
rows = []; SNA = {}
for i in UI:
    if cat(i) != 'A': continue
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            SNA[(i, bk, h)] = s
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10): continue
                if abs(ln) < .01: kind = 'DNB'
                elif ln <= -0.5: kind = 'φαβορι'
                elif ln >= 0.5: kind = 'αουτσαιντερ'
                elif ln < 0: kind = '−0.25'
                else: kind = '+0.25'
                pw, pp = cover_q(D, side, ln) if kind != 'αουτσαιντερ' else picks.p_cover(D, side, ln)
                rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], ph=PH[i], kind=kind, home=side == 1, e=edge(pw, pp, o), od=o,
                                 pnl=picks.settle(GD[i], side, ln, o)))
A = pd.DataFrame(rows)
for kind, thr in (('φαβορι', .04), ('αουτσαιντερ', .10)):
    X = A[A.kind == kind]; F = first(X, thr)
    print(f'   {kind} @{int(thr * 100)}% (σημερινος κανονας): 4 σεζον {cc(F)} · νεα μορφη {cc(F[F.sea.isin(NEW)])}')
    for hv, hl in ((True, 'εντος'), (False, 'εκτος')):
        print(f'      {hl}: {cc(F[F.home == hv])}')
    for ph in ('league', 'KO'):
        print(f'      φαση {ph}: {cc(F[F.ph == ph])}')
    print('      κατωφλια: ' + ' · '.join(f'≥{int(t * 100)}% {cc(first(X, t))[:24]}' for t in (0, .04, .08, .12, .16)))
    outs, allx = loso(X, (0, .02, .04, .06, .08, .10, .12, .14))
    print('      LOSO: ' + ' '.join(f'{h}:{int(t * 100)}%' for h, t, _ in outs) + f' → εκτος δειγματος {cc(allx)} {"✓ ΠΕΡΝΑ" if passes(allx) and allx.groupby("bk").pnl.mean().mean() > 0 else ""}')
    # χρονισμος στο σημερινο κατωφλι
    C0 = A[A.h == 0].set_index(['i', 'bk', 'side']).pnl
    F = F.copy(); F['pc'] = [C0.get((r.i, r.bk, r.side), np.nan) for r in F.itertuples()]
    cells = []
    for hi, lo, wl in ((72, 48, '72-48ω'), (36, 12, '36-12ω'), (8, 0, '8ω-κλεισ')):
        y = F[(F.h <= hi) & (F.h >= lo)]
        if len(y): cells.append(f'{wl}: {cc(y)[:30]}')
    print(f'      χρονισμος: ' + ' · '.join(cells) + f' · αν περιμενα το κλεισιμο {100 * F.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+.1f}%')
# ================= Γ. ΓΡΑΜΜΕΣ 0/±0.25 =================
print(NL + 'Γ. ΓΡΑΜΜΕΣ 0 (DNB) / −0.25 / +0.25 (κατηγορια Α, σωστα τεταρτα, @4%)')
for kind in ('DNB', '−0.25', '+0.25'):
    X = A[A.kind == kind]; F = first(X, .04)
    outs, allx = loso(X, (0, .02, .04, .06, .08, .10, .12, .14))
    print(f'   {kind:6s} {cc(F)} · νεα μορφη {cc(F[F.sea.isin(NEW)])[:30]} · LOSO εκτος δειγματος {cc(allx)[:30]}')
# ================= Δ/Ε. ΣΥΝΟΛΑ =================
rows = []
for i in UI:
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(MIDS[i], bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            for side, od, pw, pl in (('over', o, po, pu), ('under', un, pu, po)):
                if not (1.70 <= od <= 2.10): continue
                rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], ph=PH[i], cat=cat(i), e=pw * (od - 1) * (1 - picks.MARGIN) - pl,
                                 pnl=settle(tot, L, od, side == 'over'), mt=mtot(L, o, un)))
O = pd.DataFrame(rows)
for cg, lab in (('A', 'Δ. ΣΥΝΟΛΑ κατηγορια Α (FotMob και οι 2)'), ('B', 'Ε1. ΣΥΝΟΛΑ κατηγορια Β (μια χωρις FotMob)'), ('G', 'Ε2. ΣΥΝΟΛΑ κατηγορια Γ (καμια με FotMob)')):
    print(NL + lab)
    for side in ('over', 'under'):
        X = O[(O.cat == cg) & (O.side == side)]
        if len(X) == 0: continue
        print(f'   {side.upper()} κατωφλια: ' + ' · '.join(f'≥{int(t * 100)}% {cc(first(X, t, ("i", "bk")))[:26]}' for t in (0, .04, .08, .12)))
        outs, allx = loso(X, (0, .02, .04, .06, .08, .10, .12, .14), ('i', 'bk'))
        ok = len(allx) and passes(allx) and allx.groupby('bk').pnl.mean().mean() > 0
        print(f'      LOSO: ' + ' '.join(f'{h}:{int(t * 100)}%' for h, t, _ in outs) + f' → εκτος δειγματος {cc(allx)} {"✓ ΠΕΡΝΑ" if ok else ""}')
        F = first(X, .04, ('i', 'bk'))
        print(f'      @4% νεα μορφη: {cc(F[F.sea.isin(NEW)])} · φαση λιγκας νεας μορφης {cc(F[F.sea.isin(NEW) & (F.ph == "league")])[:30]}')
# ================= ΣΤ. ΤΥΦΛΑ =================
print(NL + 'ΣΤ. ΤΥΦΛΑ ΣΤΟ ΚΛΕΙΣΙΜΟ (ολες οι κατηγοριες) — τι κανει η ιδια η αγορα')
bl = []
for i in UI:
    for bk in ('Crown', 'SBOBET'):
        s = snap_ah(MIDS[i], bk, 0)
        if s:
            L, oh, oa = s
            if abs(L) >= 0.25:
                fs = 1 if L < 0 else -1
                for side, o, lab in ((fs, oh if fs == 1 else oa, 'φαβορι'), (-fs, oa if fs == 1 else oh, 'αουτσαιντερ')):
                    ln = L if side == 1 else -L
                    if 1.70 <= o <= 2.10: bl.append(dict(bk=bk, sea=SEA[i], k=f'{lab} {"εντος" if side == 1 else "εκτος"}', pnl=picks.settle(GD[i], side, ln, o)))
        so = snap_ou(MIDS[i], bk, 0)
        if so:
            L, o, un = so; tot = GH[i] + GA[i]
            if 1.70 <= o <= 2.10: bl.append(dict(bk=bk, sea=SEA[i], k='over', pnl=settle(tot, L, o, True)))
            if 1.70 <= un <= 2.10: bl.append(dict(bk=bk, sea=SEA[i], k='under', pnl=settle(tot, L, un, False)))
BL = pd.DataFrame(bl)
for k, x in BL.groupby('k'):
    print(f'   {k:18s} {cc(x)}')
