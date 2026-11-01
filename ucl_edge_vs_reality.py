"""ucl_edge_vs_reality.py — 10/10/2026 (Στελιος: «αν το edge που βλεπουμε αντικατοπτριζει την πραγματικοτητα και αρα αξιζει να παιζουμε παραπανω στα
μεγαλυτερα edges ή οχι»). Champions League, ΟΛΑ τα picks με τους σημερινους κανονες (φαβ ≥10%, dog ≥4%, DNB ≥4% — κατηγορια Α· over ≥4% Α, under ≥10% Α,
over Β ≥4% με διορθωση δ LOSO), πρωτη εμφανιση ≤72ω, Crown & SBOBET.
1. δηλωμενο edge → πραγματικο ROI (κλιμακες, κλιση ανα αγορα/σεζον). 2. σχηματα πονταρισματος με ΙΔΙΟ συνολικο ποσο: σταθερο / αναλογο του edge / Kelly / Kelly κομμενο / μισο-μισο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: «μεγαλυτερο ποινταρισμα στα μεγαλα edges αξιζει» μονο αν (α) κλιση (ολα) >0 με t ≥2 ΚΑΙ (β) το σχημα βγαζει περισσοτερες μοναδες
απο το σταθερο σε ≥3/4 σεζον χωρις μεγαλυτερη χειροτερη βουτια ταμειου.
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
DL = {'2223': 0.16, '2324': 0.20, '2425': 0.30, '2526': 0.22}
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
                    if not (1.70 <= o <= 2.10): continue
                    if abs(ln) < .01: kind, thr = 'DNB', .04
                    elif ln <= -0.5: kind, thr = 'φαβορι', .10
                    elif ln >= 0.5: kind, thr = 'αουτσαιντερ', .04
                    else: continue
                    pw, pp = cover_q(D, side, ln) if kind != 'αουτσαιντερ' else picks.p_cover(D, side, ln)
                    e = edge(pw, pp, o)
                    if e >= thr:
                        rows.append(dict(i=i, bk=bk, h=h, grp='AH', kind=kind, side=side, sea=SEA[i], e=e, od=o, pnl=picks.settle(GD[i], side, ln, o)))
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
                    rows.append(dict(i=i, bk=bk, h=h, grp='OU', kind=('over Β' if c == 'B' else side), side=0, sea=SEA[i], e=e, od=od,
                                     pnl=settle(tot, L, od, side == 'over')))
P = pd.DataFrame(rows).sort_values('h', ascending=False)
AH = P[P.grp == 'AH'].groupby(['i', 'bk', 'side']).head(1)
OU = P[P.grp == 'OU'].groupby(['i', 'bk', 'kind']).head(1).sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
A = pd.concat([AH, OU]).reset_index(drop=True)
A['ko'] = [KO.get(MIDS[i]) for i in A.i]
print('Champions League · ΟΛΑ τα picks με τους σημερινους κανονες · πρωτη εμφανιση ≤72ω · Crown & SBOBET (ανα βιβλιο, μεσος)')
print(f'   picks ανα βιβλιο: {len(A) / 2:.0f} · ' + ' · '.join(f'{k} {len(x) / 2:.0f}' for k, x in A.groupby('kind')))
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], b[1], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
# ---- 1. edge → πραγματικο ROI ----
print(NL + '1. ΔΗΛΩΜΕΝΟ EDGE → ΠΡΑΓΜΑΤΙΚΟ ROI')
BK = [(.04, .08), (.08, .12), (.12, .16), (.16, .22), (.22, 9)]
for lab, x in [('ΟΛΑ', A)] + [(k, A[A.kind == k]) for k in ('φαβορι', 'αουτσαιντερ', 'DNB', 'over', 'under', 'over Β')]:
    if len(x) < 10: continue
    b, a, se = ols(x.e.values, x.pnl.values)
    cells = []
    for lo, hi in BK:
        y = x[(x.e >= lo) & (x.e < hi)]
        if len(y): cells.append(f'{int(lo * 100)}-{int(hi * 100) if hi < 9 else "+"}%: {len(y) / 2:.0f}/{100 * y.groupby("bk").pnl.mean().mean():+.0f}%')
    print(f'   {lab:12s} μεσο edge {100 * x.e.mean():4.1f}% → πραγματικο {100 * x.groupby("bk").pnl.mean().mean():+5.1f}% · κλιση {b:+.2f}±{se:.2f} (t {b / se:+.1f}) · ' + ' · '.join(cells))
x = A
print('   ανα σεζον (ολα), κλιση: ' + ' '.join(f'{s}:{ols(y.e.values, y.pnl.values)[0]:+.2f}' for s, y in x.groupby('sea')) +
      ' · νεα μορφη κλιση ' + f'{ols(x[x.sea.isin(NEW)].e.values, x[x.sea.isin(NEW)].pnl.values)[0]:+.2f}')
print('   (κλιση 1.0 = καθε +1% edge δινει +1% ROI· 0 = το edge δεν λεει τιποτα για το ποσο θα κερδισεις)')
# ---- 2. ποινταρισμα ----
print(NL + '2. ΠΟΝΤΑΡΙΣΜΑ (ιδιο συνολικο ποσο σε καθε σχημα, ανα βιβλιο) — μοναδες, ROI, χειροτερη βουτια ταμειου')
def schemes(x):
    k = (x.e / (x.od - 1)).clip(lower=0)
    S = {'σταθερο 1': np.ones(len(x)), 'αναλογο του edge': x.e.values, 'Kelly (edge/(τιμη−1))': k.values,
         'Kelly κομμενο στο 2×': np.minimum(k.values, 2 * k.mean()), 'μισο-μισο (1 + edge/μεσο)': 0.5 + 0.5 * x.e.values / x.e.mean()}
    return {n: s / s.mean() for n, s in S.items()}
def dd(pnl):
    c = np.cumsum(pnl); return float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max())
for lab, X in (('4 ΣΕΖΟΝ', A), ('ΝΕΑ ΜΟΡΦΗ', A[A.sea.isin(NEW)])):
    print(f'   == {lab}')
    res = {}
    for bk, x in X.groupby('bk'):
        x = x.sort_values('ko')
        for n, s in schemes(x).items():
            p = s * x.pnl.values
            r = res.setdefault(n, dict(u=[], roi=[], dd=[], sea={}))
            r['u'].append(p.sum()); r['roi'].append(p.sum() / s.sum()); r['dd'].append(dd(p))
            for se_ in x.sea.unique():
                m = (x.sea == se_).values
                r['sea'].setdefault(se_, []).append(p[m].sum() / s[m].sum())
    base = res['σταθερο 1']
    for n, r in res.items():
        better = sum(1 for se_ in r['sea'] if np.mean(r['sea'][se_]) > np.mean(base['sea'][se_]))
        print(f'      {n:28s} μοναδες {np.mean(r["u"]):+6.1f} · ROI {100 * np.mean(r["roi"]):+5.1f}% · χειροτερη βουτια {np.mean(r["dd"]):5.1f}μ · '
              f'ανα σεζον ROI ' + ' '.join(f'{s[2:]} {100 * np.mean(v):+.0f}' for s, v in sorted(r['sea'].items())) +
              ('' if n == 'σταθερο 1' else f' · καλυτερο απο σταθερο σε {better}/{len(r["sea"])} σεζον'))
