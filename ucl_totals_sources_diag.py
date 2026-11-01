"""ucl_totals_sources_diag.py — 10/10/2026 (Στελιος: «πως θα μπορουσαμε αυτη την υποτιμηση να την διορθωσουμε?»).
ΔΙΑΓΝΩΣΗ (χωρις αποδοσεις): σε ματς με μια ομαδα χωρις FotMob (Ben / γκολ+Elo) και αντιπαλο FotMob, ποιο σκελος υποτιμα η live μηχανη
συνολων (W2 + κ UCL): τα γκολ που ΒΑΖΕΙ η μη-FotMob ομαδα ή αυτα που ΔΕΧΕΤΑΙ; Ανα διοργανωση, ανα πηγη, ανα σεζον,
και συγκριση με ματς FotMob-FotMob ιδιας «ανισορροπιας» (μηπως ειναι απλα συμπιεση φαβορι σε αναντιστοιχα ματς).
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

_V2 = _V
rows = []
for i in range(len(MIDS)):
    c = SRCC[i]
    j = _VI.get(str(MIDS[i]))
    if j is None: continue
    sh, sa = _LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')
    rows.append(dict(comp=COMP[i], sea=SEA[i], src=c, sh=sh, sa=sa, lh=OH[i], la=OA[i], gh=GH[i], ga=GA[i]))
D = pd.DataFrame(rows)
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
print('A. ΜΑΤΣ ΜΕ ΜΙΑ ΟΜΑΔΑ ΧΩΡΙΣ FotMob (η αλλη FotMob): πραγματικα − μοντελο ανα σκελος (γκολ ανα ματς)')
M = D[D.src.isin(['BF', 'FG'])].copy()
nf_home = M.sh != 'F'
M['nf_src'] = np.where(nf_home, M.sh, M.sa)
M['nf_lam'] = np.where(nf_home, M.lh, M.la); M['nf_g'] = np.where(nf_home, M.gh, M.ga)
M['op_lam'] = np.where(nf_home, M.la, M.lh); M['op_g'] = np.where(nf_home, M.ga, M.gh)
M['nf_is_home'] = nf_home
def line(x, lab):
    if len(x) == 0: return
    se = lambda a: a.std() / np.sqrt(len(a))
    d1 = x.nf_g - x.nf_lam; d2 = x.op_g - x.op_lam
    print(f'   {lab:28s} n{len(x):4d} · μη-FotMob ΒΑΖΕΙ {x.nf_g.mean():.2f} vs μοντ {x.nf_lam.mean():.2f} ({d1.mean():+.2f}±{se(d1):.2f}) · '
          f'ΔΕΧΕΤΑΙ {x.op_g.mean():.2f} vs μοντ {x.op_lam.mean():.2f} ({d2.mean():+.2f}±{se(d2):.2f})')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    for src, sl in (('B', 'Ben'), ('G', 'γκολ+Elo')):
        line(M[(M.comp == cm) & (M.nf_src == src)], f'{CL[cm]} {sl}')
line(M, 'ΟΛΑ')
print('   ανα σεζον (ολα): ')
for s_, x in M.groupby('sea'): line(x, f'  {s_}')
print('   ανα πηγη (ολες οι διοργανωσεις):')
for src, sl in (('B', 'Ben'), ('G', 'γκολ+Elo')): line(M[M.nf_src == src], f'  {sl}')
print('   μη-FotMob ΕΝΤΟΣ / ΕΚΤΟΣ:'); line(M[M.nf_is_home], '  εντος'); line(M[~M.nf_is_home], '  εκτος')
print('\nB. ΙΔΙΑ ΑΝΙΣΟΡΡΟΠΙΑ σε FotMob-FotMob: ο «αδυνατος» (μικροτερο λ) vs ο «δυνατος» — πραγματικα − μοντελο')
F = D[D.src == 'FF'].copy()
for lab, X, wl, wg, sl, sg in (('FF', F, None, None, None, None),):
    pass
F['w_lam'] = np.minimum(F.lh, F.la); F['w_g'] = np.where(F.lh < F.la, F.gh, F.ga)
F['s_lam'] = np.maximum(F.lh, F.la); F['s_g'] = np.where(F.lh < F.la, F.ga, F.gh)
M['w_is_nf'] = M.nf_lam < M.op_lam
print(f'   στα μη-FotMob ματς η μη-FotMob ομαδα ειναι ο αδυνατος σε {100 * M.w_is_nf.mean():.0f}%')
M['ratio'] = M[['nf_lam', 'op_lam']].max(axis=1) / M[['nf_lam', 'op_lam']].min(axis=1)
F['ratio'] = F.s_lam / F.w_lam
for lo, hi in ((1, 1.5), (1.5, 2.5), (2.5, 99)):
    f = F[(F.ratio >= lo) & (F.ratio < hi)]; m = M[(M.ratio >= lo) & (M.ratio < hi)]
    print(f'   λ-λογος {lo}-{hi}: FF n{len(f):4d} συνολο πραγμ−μοντ {(f.gh + f.ga - f.lh - f.la).mean():+.2f} (αδυνατος {(f.w_g - f.w_lam).mean():+.2f} / δυνατος {(f.s_g - f.s_lam).mean():+.2f})'
          f' || μη-FotMob n{len(m):3d} συνολο {(m.gh + m.ga - m.lh - m.la).mean():+.2f} (μη-FM {(m.nf_g - m.nf_lam).mean():+.2f} / FotMob {(m.op_g - m.op_lam).mean():+.2f})')
