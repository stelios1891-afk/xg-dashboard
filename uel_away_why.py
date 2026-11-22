"""uel_away_why.py — 11/10/2026 (Στελιος: «πρεπει να βρουμε γιατι υπαρχει αυτο το προβλημα, οχι απλα να το φτιαξουμε»).
UEL φαση λιγκας νεας μορφης: ο φιλοξενουμενος βαζει λιγοτερα γκολ απο το μοντελο (1.12 vs 1.27). ΓΙΑΤΙ; Ιδια μετρηση σε UCL/UECL.
Δ1 παιχνιδι (xG) ή φινιρισμα (γκολ−xG) · Δ2 ταξιδι (km γηπεδων, weather_euro_stadiums) · Δ3 χωρα γηπεδουχου · Δ4 τυπος φιλοξενουμενου ·
Δ5 αγωνιστικη · Δ6 διαιτησια (πεναλτι/κοκκινες) · Δ7 ημιχρονα. FotMob+FotMob, 2425-2526. ΔΙΑΓΝΩΣΤΙΚΟ.
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
LH_N, LA_N, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float)
NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
DIST = np.asarray(w['DIST_KM'], float); RND = w['RND']
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        EUM[str(mid)] = m
def side_stats(m, tid):
    sh = [s for s in (m.get('shots') or []) if s.get('xg') is not None and int(s['tid']) == tid]
    xg = sum(s['xg'] for s in sh); pen = sum(1 for s in sh if s.get('sit') == 'Penalty')
    npxg = sum(s['xg'] for s in sh if s.get('sit') != 'Penalty')
    x1 = sum(s['xg'] for s in sh if (s.get('min') or 0) <= 45); x2 = xg - x1
    g1 = sum(1 for s in sh if s.get('goal') and (s.get('min') or 0) <= 45); g2 = sum(1 for s in sh if s.get('goal') and (s.get('min') or 0) > 45)
    return xg, npxg, pen, x1, x2, g1, g2
rows = []
for i in range(len(MIDS)):
    j = VI.get(str(MIDS[i]))
    if j is None or SEA[i] not in NEW or V6['phase'][j] != 'league' or SRCC[i] != 'FF': continue
    m = EUM.get(str(MIDS[i]))
    if not m or not m.get('shots'): continue
    hid, aid = int(m['home']['id']), int(m['away']['id'])
    hx = side_stats(m, hid); ax = side_stats(m, aid)
    reds = m.get('reds') or {}
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    rows.append(dict(comp=COMP[i], sea=SEA[i], lg_h=V6['lg_h'][j], lg_a=V6['lg_a'][j], home=m['home']['name'], away=m['away']['name'],
                     gh=GH[i], ga=GA[i], lh=LH_N[i], la=LA_N[i], xh=hx[0], xa=ax[0], npxh=hx[1], npxa=ax[1], penh=hx[2], pena=ax[2],
                     xh1=hx[3], xh2=hx[4], xa1=ax[3], xa2=ax[4], gh1=hx[5], gh2=hx[6], ga1=ax[5], ga2=ax[6],
                     km=DIST[i], rnd=RND.get(str(MIDS[i])), line=(s[0] if s else np.nan), reds=json.dumps(reds)))
X = pd.DataFrame(rows)
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
se = lambda a: a.std() / max(np.sqrt(len(a)), 1)
def line(x, lab):
    if len(x) < 8: return f'   {lab:34s} n{len(x):3d} (λιγα)'
    return (f'   {lab:34s} n{len(x):3d} · φιλοξ ΓΚΟΛ − μοντελο {(x.ga - x.la).mean():+.2f}±{se(x.ga - x.la):.2f} · φιλοξ xG − μοντελο {(x.xa - x.la).mean():+.2f} · '
            f'γηπ γκολ − μοντ {(x.gh - x.lh).mean():+.2f} · γηπ xG − μοντ {(x.xh - x.lh).mean():+.2f}')
print('ΦΑΣΗ ΛΙΓΚΑΣ, ΝΕΑ ΜΟΡΦΗ (2425-2526), FotMob+FotMob — «φιλοξ ΓΚΟΛ − μοντελο» αρνητικο = ο φιλοξενουμενος βαζει λιγοτερα απ οσο περιμενουμε')
for cm in CL:
    print(line(X[X.comp == cm], f'{CL[cm]} ΟΛΑ'))
U = X[X.comp == 'EuropaLeague']
print(NL + 'Δ1. ΠΑΙΧΝΙΔΙ ή ΦΙΝΙΡΙΣΜΑ (ανα διοργανωση): φιλοξενουμενος')
for cm in CL:
    x = X[X.comp == cm]
    print(f'   {CL[cm]:5s} γκολ {x.ga.mean():.2f} · xG {x.xa.mean():.2f} (χωρις πεναλτι {x.npxa.mean():.2f}) · μοντελο {x.la.mean():.2f} · '
          f'φινιρισμα (γκολ−xG) {(x.ga - x.xa).mean():+.2f}±{se(x.ga - x.xa):.2f} · παιχνιδι (xG−μοντελο) {(x.xa - x.la).mean():+.2f}±{se(x.xa - x.la):.2f}')
print(NL + 'Δ2. ΤΑΞΙΔΙ (UEL, και UCL για συγκριση)')
for cm in ('EuropaLeague', 'ChampionsLeague'):
    x = X[X.comp == cm]
    for lo, hi in ((0, 800), (800, 1600), (1600, 2500), (2500, 9e9)):
        print(line(x[(x.km >= lo) & (x.km < hi)], f'{CL[cm]} {int(lo)}-{int(hi) if hi < 9e9 else "+"} km'))
print(NL + 'Δ3. ΧΩΡΑ/ΛΙΓΚΑ ΤΟΥ ΓΗΠΕΔΟΥΧΟΥ (UEL, ≥8 ματς)')
g = U.groupby('lg_h')
for lg, x in sorted(g, key=lambda t: (t[1].ga - t[1].la).mean()):
    if len(x) >= 8: print(line(x, f'γηπεδο σε {lg}'))
print(NL + 'Δ4. ΤΙ ΟΜΑΔΑ ΕΙΝΑΙ Ο ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ (UEL)')
for lab, m in (('φιλοξ ΦΑΒΟΡΙ αγορας (γραμμη >0)', U.line > 0), ('φιλοξ ΑΟΥΤΣΑΙΝΤΕΡ αγορας (γραμμη <0)', U.line < 0), ('ισορροπημενο (γραμμη 0)', U.line == 0),
               ('φιλοξ απο TOP-5', U.lg_a.isin(TOP5)), ('φιλοξ απο αλλη λιγκα', ~U.lg_a.isin(TOP5))):
    print(line(U[m], lab))
print(NL + 'Δ5. ΑΓΩΝΙΣΤΙΚΗ (UEL)')
U2 = U.assign(r=pd.to_numeric(U.rnd, errors='coerce'))
for lab, m in (('αγων 1-4', U2.r <= 4), ('αγων 5-6', U2.r.between(5, 6)), ('αγων 7-8', U2.r >= 7)):
    print(line(U2[m], lab))
print(NL + 'Δ6. ΔΙΑΙΤΗΣΙΑ: πεναλτι ανα ματς (γηπ / φιλοξ) και κοκκινες')
for cm in CL:
    x = X[X.comp == cm]
    rh = ra = 0
    for r in x.itertuples():
        d = json.loads(r.reds) if r.reds else []
        for c in (d if isinstance(d, list) else []):
            if c.get('home'): rh += 1
            else: ra += 1
    print(f'   {CL[cm]:5s} πεναλτι γηπ {x.penh.mean():.3f} / φιλοξ {x.pena.mean():.3f} · κοκκινες γηπ {rh / len(x):.3f} / φιλοξ {ra / len(x):.3f} (n{len(x)})')
print(NL + 'Δ7. ΗΜΙΧΡΟΝΑ (φιλοξενουμενος): μεριδιο xG και γκολ στο 2ο ημιχρονο, και φινιρισμα ανα ημιχρονο')
for cm in CL:
    x = X[X.comp == cm]
    print(f'   {CL[cm]:5s} xG 1ο {x.xa1.mean():.2f} / 2ο {x.xa2.mean():.2f} · γκολ 1ο {x.ga1.mean():.2f} / 2ο {x.ga2.mean():.2f} · '
          f'γηπ xG 1ο {x.xh1.mean():.2f} / 2ο {x.xh2.mean():.2f} · γηπ γκολ 1ο {x.gh1.mean():.2f} / 2ο {x.gh2.mean():.2f}')
X.to_pickle('uel_away_diag_rows.pkl')
