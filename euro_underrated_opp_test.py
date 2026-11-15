"""euro_underrated_opp_test.py — 10/10/2026 (Στελιος: «υποτιμαμε πολυ την psv» → «οκ δες το»).
Picks χαντικαπ (σημερινοι κανονες, FotMob+FotMob, UCL/UEL/UECL) ΕΝΑΝΤΙΟΝ ομαδων που το μοντελο υποτιμουσε τις ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον.
«Υποτιμηση» g = μεσο λαθος μοντελου (πραγματικη − μοντελο διαφορα, σκοπια ομαδας) σε ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον μονο, συρρικνωση n/(n+6)
— γνωστο ΠΡΙΝ απο καθε ματς (οχι κυκλικο). x = g αντιπαλου − g δικης μας ομαδας. Σεζον κρισης 2324-2526 (2223 χωρις προηγουμενες).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΦΙΛΤΡΟ «οχι pick οταν x ≥ +0.2»: (α) αυτα τα picks αρνητικα σε 2 βιβλια & ≥2/3 σεζον ΚΑΙ (β) χωρις αυτα περισσοτερες
μοναδες συνολικα και σε ≥2/3 σεζον.
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
TEST = ('2324', '2425', '2526')
EUT = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        EUT[str(mid)] = (int(m['home']['id']), int(m['away']['id']), m['home']['name'], m['away']['name'])
# ---- «υποτιμηση» ομαδας απο ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον μονο (λαθος μοντελου, σκοπια ομαδας, συρρικνωση n/(n+6)) ----
XR = pd.read_pickle('euro_team_hfa_rows.pkl')
K = 6.0
def prior_g(tid, sea):
    p = XR[XR.sea < sea]
    r = pd.concat([p[p.hid == tid].res, -p[p.aid == tid].res])
    return (r.mean() * len(r) / (len(r) + K)) if len(r) else 0.0, len(r)
G = {}
# ---- picks χαντικαπ με τους σημερινους κανονες (FotMob+FotMob) ----
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i in range(len(MIDS)):
    if SRCC[i] != 'FF' or SEA[i] not in TEST: continue
    t = EUT.get(str(MIDS[i]))
    if not t: continue
    c = COMP[i]; ucl_ = c == 'ChampionsLeague'
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10): continue
                if abs(ln) < .01 and ucl_: kind, thr = 'DNB', .04
                elif ln <= -0.5: kind, thr = 'φαβορι', (.10 if ucl_ else .04)
                elif ln >= 0.5: kind, thr = 'αουτσαιντερ', (.04 if ucl_ else .10)
                else: continue
                pw, pp = cover_q(D, side, ln) if kind != 'αουτσαιντερ' else picks.p_cover(D, side, ln)
                e = edge(pw, pp, o)
                if e >= thr:
                    own, opp = (t[0], t[1]) if side == 1 else (t[1], t[0])
                    rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], comp=c, kind=kind, e=e, od=o, own=own, opp=opp,
                                     opp_name=t[3] if side == 1 else t[2], pnl=picks.settle(GD[i], side, ln, o)))
P = pd.DataFrame(rows).sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1).copy()
for r in P.itertuples():
    for tid in (r.own, r.opp):
        if (tid, r.sea) not in G: G[(tid, r.sea)] = prior_g(tid, r.sea)
P['g_opp'] = [G[(r.opp, r.sea)][0] for r in P.itertuples()]; P['g_own'] = [G[(r.own, r.sea)][0] for r in P.itertuples()]
P['x'] = P.g_opp - P.g_own            # + = ο ΑΝΤΙΠΑΛΟΣ ηταν ιστορικα πιο υποτιμημενος απο τη δικη μας ομαδα
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print('Picks χαντικαπ (σημερινοι κανονες, FotMob+FotMob, ολες οι διοργανωσεις), σεζον 2324-2526, πρωτη εμφανιση ≤72ω, Crown & SBOBET')
print(f'   ολα: {cc(P)} · x: μεσος {P.x.mean():+.2f}, sd {P.x.std():.2f}')
b, a = np.polyfit(P.x, P.pnl, 1); e_ = P.pnl - (a + b * P.x)
se = np.sqrt((e_ ** 2).sum() / (len(P) - 2) / ((P.x - P.x.mean()) ** 2).sum())
print(f'   κλιση ROI ανα +1 γκολ «υποτιμησης αντιπαλου»: {b:+.2f} ± {se:.2f} (t {b / se:+.1f}) — αρνητικο = χανουμε οταν ο αντιπαλος ηταν υποτιμημενος')
print(NL + 'ΑΝΑ ΚΛΙΜΑΚΑ x (ποσο πιο υποτιμημενος ιστορικα ο αντιπαλος απο εμας):')
for lo, hi in ((-9, -0.2), (-0.2, 0), (0, 0.2), (0.2, 9)):
    print(f'   x {lo:+.1f}…{hi:+.1f}: {cc(P[(P.x >= lo) & (P.x < hi)])}')
print(NL + 'ΑΝΑ ΕΙΔΟΣ (x ≥ +0.2 vs υπολοιπα):')
for k in ('φαβορι', 'αουτσαιντερ', 'DNB'):
    y = P[P.kind == k]
    print(f'   {k:12s} x≥0.2: {cc(y[y.x >= 0.2])}  ||  υπολοιπα: {cc(y[y.x < 0.2])}')
F = P[P.x >= 0.2]; R_ = P[P.x < 0.2]
mF = F.groupby('bk').pnl.mean(); psF = F.groupby('sea').pnl.mean()
ka = bool((mF < 0).all()) and (psF < 0).sum() >= 2
uall = P.groupby('bk').pnl.sum().mean(); ucut = R_.groupby('bk').pnl.sum().mean()
better = sum(1 for s in TEST if R_[R_.sea == s].groupby('bk').pnl.sum().mean() > P[P.sea == s].groupby('bk').pnl.sum().mean())
kb = ucut > uall and better >= 2
print(NL + f'(α) picks με x≥0.2 αρνητικα σε 2 βιβλια & ≥2/3 σεζον: {"✓" if ka else "✗"} · (β) μοναδες χωρις αυτα {ucut:+.1f} vs ολα {uall:+.1f}, καλυτερα σε {better}/3 σεζον: {"✓" if kb else "✗"}')
print('ΑΠΟΦΑΣΗ: ' + ('ΦΙΛΤΡΟ ΠΕΡΝΑ' if ka and kb else 'κανενα φιλτρο'))
top = P[P.x >= 0.2].groupby('opp_name').agg(n=('pnl', 'size'), x=('x', 'mean'), roi=('pnl', 'mean')).sort_values('n', ascending=False).head(10)
print(NL + 'αντιπαλοι με τα περισσοτερα τετοια picks (x≥0.2): ' + ' · '.join(f'{t} n{r.n / 2:.0f} {100 * r.roi:+.0f}%' for t, r in top.iterrows()))
