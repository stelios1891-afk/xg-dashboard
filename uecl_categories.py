"""uecl_categories.py — 11/10/2026 (Στελιος: «ποσες ομαδες ειναι σε καθε κατηγορια φετος; πως αποδιδει η καθε κατηγορια — οχι μονο ROI αλλα και
προβλεψη, υποτιμαμε ή υπερτιμαμε κατι; ειδικα αυτες εκτος fotmob, που ειναι η αδυναμια του μοντελου;»). Conference League.
1) φετος: ομαδες ανα πηγη, ματς ανα κατηγορια · 2) ανα κατηγορια: γκολ που βαζει καθε πλευρα vs μοντελο / xG / αγορα (κλεισιμο), συνολο, διαφορα
· 3) ομαδες χωρις FotMob ανα πηγη: επιθεση/αμυνα, εντος/εκτος, αντιπαλος. ΔΙΑΓΝΩΣΤΙΚΟ.
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

import pickle as _pkl, collections
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
LAB = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ+Elo'}
# ================= 1. ΦΕΤΟΣ =================
P = json.load(open('euro_projections.json', encoding='utf-8'))
T = {}; catc = collections.Counter(); fin = collections.Counter()
for m in P['matches']:
    if m['comp'] != 'ConferenceLeague' or not m.get('covered'): continue
    for nm, s, lg in ((m['home'], m['src_h'], m.get('lg_h')), (m['away'], m['src_a'], m.get('lg_a'))):
        T[nm] = (s, lg)
    fm = [m['src_h'] == 'FotMob', m['src_a'] == 'FotMob']
    c = 'Α' if all(fm) else ('Β' if any(fm) else 'Γ'); catc[c] += 1
    if m.get('finished'): fin[c] += 1
print('1. ΦΕΤΟΣ (Conference League 2026-27, φαση λιγκας)')
by = collections.defaultdict(list)
for nm, (s, lg) in T.items(): by[s].append(f'{nm} ({lg})')
for s, lst in sorted(by.items(), key=lambda x: -len(x[1])):
    print(f'   {s:9s} {len(lst):2d} ομαδες: ' + ', '.join(sorted(lst)))
print('   ματς ανα κατηγορια: ' + ' · '.join(f'{c} {catc[c]} (παιχτηκαν {fin[c]})' for c in ('Α', 'Β', 'Γ')))
# ================= 2. ΙΣΤΟΡΙΚΑ ανα πλευρα =================
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(mid)] = m
def xg_side(m, tid):
    return sum(s['xg'] for s in (m.get('shots') or []) if s.get('xg') is not None and int(s['tid']) == tid)
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); Tt = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((Tt + M) / 2, .05), max((Tt - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
S = []; MT = []
for i in range(len(MIDS)):
    j = VI.get(str(MIDS[i]))
    if j is None or COMP[i] != 'ConferenceLeague' or LH_N[i] <= 0: continue
    m = EUM.get(str(MIDS[i]))
    if not m or not m.get('shots'): continue
    sh, sa = LAB.get(V6['src_h'][j], '?'), LAB.get(V6['src_a'][j], '?')
    hid, aid = int(m['home']['id']), int(m['away']['id'])
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    so = snap_ou(MIDS[i], 'Crown', 0) or snap_ou(MIDS[i], 'SBOBET', 0)
    kgd = implied_margin(i, *s) if s else np.nan; ktot = mtot(*so) if so else np.nan
    # αγορα ανα πλευρα: συνολο & διαφορα → γκολ γηπ = (T+M)/2, φιλοξ = (T−M)/2
    kh = (ktot + kgd) / 2 if np.isfinite(ktot) and np.isfinite(kgd) else np.nan; ka = (ktot - kgd) / 2 if np.isfinite(ktot) and np.isfinite(kgd) else np.nan
    c = 'Α' if sh == sa == 'FotMob' else ('Β' if 'FotMob' in (sh, sa) else 'Γ')
    ph = V6['phase'][j]
    for venue, src, osrc, g, lam, xg, k in (('εντος', sh, sa, GH[i], LH_N[i], xg_side(m, hid), kh), ('εκτος', sa, sh, GA[i], LA_N[i], xg_side(m, aid), ka)):
        S.append(dict(sea=SEA[i], ph=ph, cat=c, venue=venue, src=src, osrc=osrc, g=g, lam=lam, xg=xg, k=k))
    MT.append(dict(sea=SEA[i], ph=ph, cat=c, tot=GH[i] + GA[i], mtot_=OH[i] + OA[i], ktot=ktot, gd=GH[i] - GA[i], mgd=LH_N[i] - LA_N[i], kgd=kgd))
S = pd.DataFrame(S); MTD = pd.DataFrame(MT)
se = lambda a: a.std() / max(np.sqrt(len(a)), 1)
def row(x, lab):
    if len(x) < 10: return f'   {lab:46s} n{len(x):3d} (λιγα)'
    return (f'   {lab:46s} n{len(x):3d} · ΒΑΖΕΙ {x.g.mean():.2f} · μοντελο {x.lam.mean():.2f} ({(x.g - x.lam).mean():+.2f}±{se(x.g - x.lam):.2f}) · '
            f'xG {x.xg.mean():.2f} (xG−μοντ {(x.xg - x.lam).mean():+.2f}) · αγορα {x.k.mean():.2f} ({(x.g - x.k).mean():+.2f})')
for lab, m in (('4 ΣΕΖΟΝ', S.sea.isin(SEAS)), ('ΝΕΑ ΜΟΡΦΗ, ΦΑΣΗ ΛΙΓΚΑΣ', S.sea.isin(NEW) & (S.ph == 'league'))):
    print(NL + f'2. ΠΡΟΒΛΕΨΗ ΑΝΑ ΚΑΤΗΓΟΡΙΑ — {lab}: γκολ που ΒΑΖΕΙ καθε πλευρα vs μοντελο / xG / αγορα (+ = το υποτιμαμε)')
    x = MTD[MTD.sea.isin(SEAS if lab.startswith('4') else NEW) & ((MTD.ph == 'league') if 'ΛΙΓΚΑΣ' in lab else True)]
    for c in ('Α', 'Β', 'Γ'):
        y = x[x.cat == c]
        if len(y): print(f'   κατηγορια {c}: n{len(y):3d} ματς · ΣΥΝΟΛΟ πραγμ {y.tot.mean():.2f} / μοντ {y.mtot_.mean():.2f} / αγορα {y.ktot.mean():.2f} · ΔΙΑΦΟΡΑ πραγμ {y.gd.mean():+.2f} / μοντ {y.mgd.mean():+.2f} / αγορα {y.kgd.mean():+.2f}')
        for v in ('εντος', 'εκτος'):
            print(row(S[m & (S.cat == c) & (S.venue == v)], f'      {c} · {v}'))
print(NL + '3. ΟΜΑΔΕΣ ΧΩΡΙΣ FotMob — ανα πηγη, επιθεση (ποσα ΒΑΖΟΥΝ) και αμυνα (ποσα ΤΡΩΝΕ), 4 σεζον')
for src in ('Ben', 'γκολ+Elo', 'FotMob'):
    att = S[S.src == src]; dfn = S[S.osrc == src]
    print(f'   {src}:')
    for v in ('εντος', 'εκτος'):
        print(row(att[att.venue == v], f'      ΕΠΙΘΕΣΗ {v} (γκολ που βαζει)'))
    for v in ('εντος', 'εκτος'):
        d = dfn[dfn.venue != v]          # τα γκολ του αντιπαλου οταν η ομαδα ειναι {v}
        print(row(d, f'      ΑΜΥΝΑ {v} (γκολ που τρωει)'))
print(NL + '   ... και ανα αντιπαλο: ομαδα χωρις FotMob απεναντι σε FotMob vs απεναντι σε αλλη χωρις FotMob (γκολ που βαζει)')
for src in ('Ben', 'γκολ+Elo'):
    for olab, om in (('vs FotMob', S.osrc == 'FotMob'), ('vs χωρις FotMob', S.osrc != 'FotMob')):
        print(row(S[(S.src == src) & om], f'      {src} {olab}'))
