"""ucl_ah_ou_same_match.py — 10/10/2026 (Στελιος: «δες το 2»): ΧΑΝΤΙΚΑΠ ΚΑΙ ΓΚΟΛ ΣΤΟ ΙΔΙΟ ΜΑΤΣ (Champions League).
Live κανονες: χαντικαπ (κατηγορια Α: φαβ ≥10% σωστα τεταρτα, dog ≥4% p_cover, |γραμμη| ≥0.5, 1.70-2.10) · γκολ (over ≥4% Α+Β — Β με διορθωση δ LOSO ·
under ≥10% Α), ενα pick γκολ ανα ματς, πρωτη εμφανιση ≤72ω, Crown & SBOBET (Nowgoal), μεσος.
Ποσο συχνα εχουμε και τα δυο, ποσο κερδιζουν/χανουν μαζι (ανα συνδυασμο: φαβ+over, φαβ+under, dog+over, dog+under), συσχετιση αποτελεσματων,
ποσο μεγαλωνει το ρισκο του ζευγαριου. ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει ποια picks βγαινουν.
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

NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
DL = {'2223': 0.16, '2324': 0.20, '2425': 0.30, '2526': 0.22}          # δ LOSO ανα σεζον (ucl_nonfm_fix2_test)
def cat(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return None, None
    sh, sa = _LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')
    if sh == 'F' and sa == 'F': return 'A', None
    if (sh == 'F') != (sa == 'F'): return 'B', sh == 'F'
    return 'G', None
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i in np.where(ucl)[0]:
    c, fmh = cat(i)
    if c not in ('A', 'B'): continue
    mid = MIDS[i]
    if c == 'A':
        D = sdist(LH_N[i], LA_N[i])
        for bk in ('Crown', 'SBOBET'):
            for h in HS:
                s = snap_ah(mid, bk, h)
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                    role = 'fav' if ln < 0 else 'dog'
                    pw, pp = cover_q(D, side, ln) if role == 'fav' else picks.p_cover(D, side, ln)
                    e = edge(pw, pp, o)
                    if e >= (0.10 if role == 'fav' else 0.04):
                        rows.append(dict(i=i, bk=bk, h=h, mkt='AH', kind=role, side=side, sea=SEA[i], cat=c, e=e, od=o,
                                         pnl=picks.settle(GD[i], side, ln, o)))
    lh, la = OH[i], OA[i]
    if c == 'B':
        if fmh: lh = lh * (1 + DL[SEA[i]])
        else: la = la * (1 + DL[SEA[i]])
    td = ES.tot_dist(lh, la, DRAW_SCALE)
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(mid, bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L); tot = GH[i] + GA[i]
            for side, od, pw, pl in (('over', o, po, pu), ('under', un, pu, po)):
                if not (1.70 <= od <= 2.10): continue
                if c == 'B' and side == 'under': continue
                e = pw * (od - 1) * (1 - picks.MARGIN) - pl
                if e >= (.04 if side == 'over' else .10):
                    rows.append(dict(i=i, bk=bk, h=h, mkt='OU', kind=side, side=0, sea=SEA[i], cat=c, e=e, od=od, pnl=settle(tot, L, od, side == 'over')))
P = pd.DataFrame(rows).sort_values('h', ascending=False)
AH = P[P.mkt == 'AH'].groupby(['i', 'bk', 'side']).head(1)
OU = P[P.mkt == 'OU'].groupby(['i', 'bk', 'kind']).head(1).sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
J = AH.merge(OU, on=['i', 'bk'], suffixes=('_ah', '_ou'))
J['sea'] = J.sea_ah
def fav_is_home(r): return r.side_ah == 1
J['combo'] = J.kind_ah + '+' + J.kind_ou
print('Champions League · live κανονες (χαντικαπ φαβ ≥10% / dog ≥4% μονο κατηγορια Α · over ≥4% Α+Β (Β με διορθωση) · under ≥10% Α) · πρωτη εμφανιση ≤72ω · ανα βιβλιο, μεσος Crown/SBOBET')
for lab, seas in (('ΝΕΑ ΜΟΡΦΗ 2425-2526', NEW), ('ΚΑΙ ΟΙ 4 ΣΕΖΟΝ', SEAS)):
    a = AH[AH.sea.isin(seas)]; o = OU[OU.sea.isin(seas)]; j = J[J.sea.isin(seas)]
    na = a.groupby('bk').size().mean(); no = o.groupby('bk').size().mean(); nj = j.groupby('bk').size().mean() if len(j) else 0
    nm = len(set(a.i) | set(o.i))
    print(NL + f'===== {lab}')
    print(f'   picks χαντικαπ {na:.0f} · picks γκολ {no:.0f} · ΚΑΙ ΤΑ ΔΥΟ στο ιδιο ματς: {nj:.0f} φορες '
          f'({100 * nj / max(min(na, no), 1):.0f}% των λιγοτερων· {100 * nj / max(nm, 1):.0f}% των ματς με pick)')
    print(f'   {"συνδυασμος":14s} {"φορες":>5s} | κερδισαν ΚΑΙ τα 2 | εχασαν ΚΑΙ τα 2 | ενα-ενα/push | συσχετιση | ROI χαντικαπ | ROI γκολ | μαζι (2 μοναδες)')
    for cb in sorted(j.combo.unique()) + ['ΟΛΑ']:
        x = j if cb == 'ΟΛΑ' else j[j.combo == cb]
        if len(x) == 0: continue
        n = x.groupby('bk').size().mean()
        ww = ((x.pnl_ah > 0) & (x.pnl_ou > 0)).mean(); ll_ = ((x.pnl_ah < 0) & (x.pnl_ou < 0)).mean()
        rho = np.corrcoef(x.pnl_ah, x.pnl_ou)[0, 1] if len(x) > 2 else np.nan
        print(f'   {cb:14s} {n:5.0f} | {100 * ww:15.0f}% | {100 * ll_:14.0f}% | {100 * (1 - ww - ll_):11.0f}% | {rho:+9.2f} | '
              f'{100 * x.groupby("bk").pnl_ah.mean().mean():+11.1f}% | {100 * x.groupby("bk").pnl_ou.mean().mean():+7.1f}% | '
              f'{x.groupby("bk").apply(lambda y: (y.pnl_ah + y.pnl_ou).mean()).mean():+.2f}μ/ματς')
    if len(j) > 2:
        s1, s2 = j.pnl_ah.std(), j.pnl_ou.std(); rho = np.corrcoef(j.pnl_ah, j.pnl_ou)[0, 1]
        print(f'   διασπορα του ζευγαριου: πραγματικη {np.sqrt(s1 ** 2 + s2 ** 2 + 2 * rho * s1 * s2):.2f} vs αν ηταν ανεξαρτητα {np.sqrt(s1 ** 2 + s2 ** 2):.2f} '
              f'(×{np.sqrt(s1 ** 2 + s2 ** 2 + 2 * rho * s1 * s2) / np.sqrt(s1 ** 2 + s2 ** 2):.2f})')
    hd = (j.h_ah - j.h_ou)
    print(f'   ποιο βγαινει πρωτο: χαντικαπ πρωτο {100 * (hd > 0).mean():.0f}% · γκολ πρωτο {100 * (hd < 0).mean():.0f}% · ιδια ωρα {100 * (hd == 0).mean():.0f}%')
J.to_pickle('ucl_ah_ou_same_match.pkl')
