"""euro_team_hfa_test.py — 10/10/2026 (Στελιος: «τη Μποντο σαν εδρα την υποτιμαμε σιγουρα, μηπως θα δουλευε καλυτερα ενα ιστορικο hfa?»).
Α. Bodø/Glimt: πραγματικη / μοντελο / αγορα διαφορα γκολ στα ευρωπαικα (εντος, εκτος).
Β. ΓΕΝΙΚΟ (για να μην ειναι διορθωση μιας ομαδας): «ιστορικη εξτρα εδρα» καθε ομαδας απο το ΕΓΧΩΡΙΟ πρωταθλημα
   (εντος−εκτος διαφορα γκολ ανα ματς μειον 2× μεση εδρα λιγκας, τελευταια 2 χρονια ως την ημερα του ματς, συρρικνωση n/(n+10)).
   x = (εξτρα γηπεδουχου + εξτρα φιλοξενουμενου)/2. Προβλεπει το λαθος του μοντελου (live ζευγος χαντικαπ) και της αγορας (κλεισιμο) στην Ευρωπη;
   ΠΡΟ-ΔΗΛΩΜΕΝΑ: Κ1 β>0 με t≥2 και LOSO β>0 σε ≥3/4 · Κ2 MAE διαφορας καλυτερο εκτος δειγματος σε ≥3/4 σεζον ·
   Κ3 η αγορα ΔΕΝ το εχει (β αγορας >0 με t≥1.5) — αλλιως ακριβεια χωρις αξια. (Αν περασουν → τεστ picks.)
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

import datetime as _dt
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526')
# ---- ομαδες ευρωπαικων ματς ----
EUT = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        EUT[str(mid)] = (int(m['home']['id']), int(m['away']['id']), m['home']['name'], m['away']['name'])
# ---- εγχωρια: ιστορικη εδρα ανα ομαδα ----
SKIP = ('Europe', 'Friendlies', 'Nations', 'WC', 'EURO', 'AFCON', 'Copa', 'AsianCup', 'GoldCup', 'WorldCup', 'Brazil', 'MLS')
DOM = {}; LGM = {}
for f in glob.glob('data_*.json'):
    key = os.path.basename(f)[5:-5]
    if key.startswith(SKIP): continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    gds = []
    for m in d.values():
        if m.get('hs') is None or m.get('as') is None: continue
        try:
            ts = _dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=_dt.timezone.utc).timestamp()
        except Exception:
            continue
        g = int(m['hs']) - int(m['as']); gds.append(g)
        DOM.setdefault(int(m['home']['id']), []).append((ts, 1, g, key))
        DOM.setdefault(int(m['away']['id']), []).append((ts, 0, -g, key))
    if gds: LGM[key] = float(np.mean(gds))
def team_H(tid, ko, K=10.0, days=730):
    xs = [x for x in DOM.get(tid, []) if ko - days * 86400 <= x[0] < ko - 3600]
    hm = [x[2] for x in xs if x[1] == 1]; aw = [x[2] for x in xs if x[1] == 0]
    if len(hm) < 5 or len(aw) < 5: return 0.0, 0
    A = np.mean([LGM.get(x[3], 0.3) for x in xs])
    H = (np.mean(hm) - np.mean(aw)) - 2 * A
    n = min(len(hm), len(aw))
    return H * n / (n + K), n
rows = []
for i, mid in enumerate(MIDS):
    t = EUT.get(str(mid)); ko = KO.get(mid)
    if not t or not ko or LH_N[i] <= 0: continue
    Hh, nh = team_H(t[0], ko); Ha, na = team_H(t[1], ko)
    c = SN0.get(i) if 'SN0' in globals() else None
    rows.append(dict(i=i, mid=mid, sea=SEA[i], comp=COMP[i], home=t[2], away=t[3], hid=t[0], aid=t[1], Hh=Hh, Ha=Ha, nh=nh, na=na,
                     x=(Hh + Ha) / 2, gd=GD[i], mgd=LH_N[i] - LA_N[i], cat=SRCC[i]))
X = pd.DataFrame(rows)
# αγορα: διαφορα που δικαιολογει το κλεισιμο (Crown, αλλιως SBOBET)
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
mk = []
for r in X.itertuples():
    s = snap_ah(r.mid, 'Crown', 0) or snap_ah(r.mid, 'SBOBET', 0)
    mk.append(implied_margin(r.i, *s) if s else np.nan)
X['kgd'] = mk
X['res'] = X.gd - X.mgd; X['res_k'] = X.gd - X.kgd
# ================= Α. BODØ =================
print('Α. BODØ/GLIMT στην Ευρωπη (2223-2526): διαφορα γκολ — πραγματικη / μοντελο / αγορα (κλεισιμο)')
for lab, m in (('ΕΝΤΟΣ', X.home.str.contains('Bod')), ('ΕΚΤΟΣ', X.away.str.contains('Bod'))):
    b = X[m]; sg = 1 if lab == 'ΕΝΤΟΣ' else -1
    print(f'   {lab}: n{len(b)} · πραγματικη {sg * b.gd.mean():+.2f} · μοντελο {sg * b.mgd.mean():+.2f} · αγορα {sg * b.kgd.mean():+.2f} · '
          f'λαθος μοντελου {sg * b.res.mean():+.2f} · λαθος αγορας {sg * b.res_k.mean():+.2f} · ιστορικη εγχωρια «εξτρα εδρα» Bodø {b.Hh.mean() if lab == "ΕΝΤΟΣ" else b.Ha.mean():+.2f}')
    for r in b.itertuples():
        print(f'      {r.sea} {r.comp[:6]} {r.home[:18]:18s} - {r.away[:18]:18s} πραγμ {r.gd:+.0f} · μοντ {r.mgd:+.2f} · αγορα {r.kgd:+.2f}')
# ================= Β. ΓΕΝΙΚΟ ΤΕΣΤ =================
print(NL + 'Β. ΓΕΝΙΚΟ ΤΕΣΤ: «ιστορικη εξτρα εδρα» απο το ΕΓΧΩΡΙΟ πρωταθλημα (τελευταια 2 χρονια, ως την ημερα του ματς, συρρικνωση n/(n+10))')
print('   x = (εξτρα εδρα γηπεδουχου + εξτρα «κακο εκτος» φιλοξενουμενου)/2 · ερωτημα: προβλεπει το λαθος του μοντελου/της αγορας στην Ευρωπη;')
Y = X[(X.nh > 0) & (X.na > 0) & np.isfinite(X.kgd)].copy()
print(f'   ματς με ιστορικο και για τις 2: {len(Y)} · x: μεσος {Y.x.mean():+.2f}, sd {Y.x.std():.2f} · Bodø εντος x {Y[Y.home.str.contains("Bod")].x.mean():+.2f}')
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    se = np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
    return b[0], se
for lab, col in (('λαθος ΜΟΝΤΕΛΟΥ', 'res'), ('λαθος ΑΓΟΡΑΣ', 'res_k')):
    b, se = ols(Y.x.values, Y[col].values)
    fold = []
    for s in SEAS:
        tr = Y[Y.sea != s]; te = Y[Y.sea == s]
        bb, _ = ols(tr.x.values, tr[col].values)
        fold.append((s, bb, (np.abs(te[col] - bb * te.x)).mean() - np.abs(te[col]).mean()))
    print(f'   {lab}: κλιση β = {b:+.2f} ± {se:.2f} (t {b / se:+.1f}) · LOSO β ' + ' '.join(f'{s}:{bb:+.2f}' for s, bb, _ in fold) +
          ' · ΔMAE εκτος δειγματος ' + ' '.join(f'{s}:{d:+.3f}' for s, _, d in fold))
print('   ανα διοργανωση (λαθος μοντελου / αγορας):')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    y = Y[Y.comp == cm]
    b1, s1 = ols(y.x.values, y.res.values); b2, s2 = ols(y.x.values, y.res_k.values)
    print(f'      {cm[:8]:8s} n{len(y):4d} · μοντελο β {b1:+.2f}±{s1:.2f} · αγορα β {b2:+.2f}±{s2:.2f}')
print('   ανα πενταδα x (λαθος μοντελου / αγορας):')
Y['q'] = pd.qcut(Y.x, 5, labels=False)
for q, y in Y.groupby('q'):
    print(f'      x {y.x.min():+.2f}…{y.x.max():+.2f} n{len(y):4d} · μοντελο {y.res.mean():+.2f} · αγορα {y.res_k.mean():+.2f}')
X.to_pickle('euro_team_hfa_rows.pkl')
