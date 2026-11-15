"""ucl_gap_totals_diag.py — 10/10/2026 (Στελιος: «να ξεκινησουμε με το τσαμπιονς λιγκ? η πετυχαινουμε τη διορθωση ... η κραταμε μονο τα over»).
ΔΙΑΓΝΩΣΗ πριν το τεστ: το λαθος ΣΥΝΟΛΟΥ γκολ (πραγματικα − μοντελο, live ζευγος συνολων W2+κ) ανα |D| = διαφορα δυναμης λιγκας
(το ιδιο D της μηχανης, που σημερα μετακινει ΜΟΝΟ την υπεροχη μεσω γ=−0.47 και αφηνει το συνολο ιδιο), ανα διοργανωση, FotMob-FotMob vs μη-FotMob.
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

Dg = np.asarray(w['g']['D'], float)
X = pd.DataFrame(dict(comp=COMP, sea=SEA, src=SRCC, D=Dg, lh=OH, la=OA, gh=GH, ga=GA))
X['aD'] = X.D.abs(); X['res'] = X.gh + X.ga - X.lh - X.la
X['nf'] = X.src != 'FF'
print('|D| ποσοστημορια (ολα):', np.round(np.nanpercentile(X.aD, [25, 50, 75, 90, 97]), 2))
B = [0, .25, .5, .75, 1.0, 9]
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
for cm in CL:
    print(f'\n{CL[cm]}: λαθος συνολου (πραγμ − μοντ) ανα |D|  [n · FF / μη-FotMob]')
    for lo, hi in zip(B[:-1], B[1:]):
        x = X[(X.comp == cm) & (X.aD >= lo) & (X.aD < hi)]
        f = x[~x.nf]; nf = x[x.nf]
        se = lambda a: a.std() / np.sqrt(max(len(a), 1))
        print(f'   |D| {lo:.2f}-{hi:.2f}: FF n{len(f):4d} {f.res.mean():+.2f}±{se(f.res):.2f} · μη-FM n{len(nf):4d} {nf.res.mean():+.2f}±{se(nf.res):.2f}')
print('\nΚΛΙΣΗ (OLS λαθος συνολου ~ |D|) ανα διοργανωση:')
for cm in list(CL) + ['ΟΛΑ']:
    x = X if cm == 'ΟΛΑ' else X[X.comp == cm]
    for lab, y in (('ολα', x), ('FF', x[~x.nf]), ('μη-FM', x[x.nf])):
        b = np.polyfit(y.aD, y.res, 1)
        print(f'   {CL.get(cm, cm):5s} {lab:6s} n{len(y):5d} · λαθος = {b[1]:+.2f} {b[0]:+.2f}·|D|')
