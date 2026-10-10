"""uel_vs_ucl_diag.py — 10/10/2026 (Στελιος: «ποιο ειναι το προβλημα στις υπολοιπες αγορες [του Europa]? τι διαφερει με το τσαμπιονς λιγκ?
θελω μια βαθεια αναλυση, να βρουμε το λογο που χανουμε κατι»). ΔΙΑΓΝΩΣΤΙΚΟ, ματς FotMob+FotMob, 2223-2526, κλεισιμο Crown (αλλιως SBOBET).
Η1 πληροφορια (διαφορα γκολ ~ μοντελο + αγορα) · Η2 εδρα · Η3 φαβορι εκτος · Η4 ROTATION (αξια ευρωπαικης ενδεκαδας / εγχωριας, ενδεκαδες FotMob)
· Η5 ομαδες top-5 λιγκων · Η6 γκολ · + φαση. Ιδια μετρηση σε UCL / UEL / UECL ωστε να φαινεται τι ΔΙΑΦΕΡΕΙ.
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

import datetime as _dt, pickle as _pkl
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
V6 = _pkl.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
EUT = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        EUT[str(mid)] = (int(m['home']['id']), int(m['away']['id']), m['home']['name'], m['away']['name'])
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
# ---- ενδεκαδες: αξια ευρωπαικης ενδεκαδας / διαμεσος των 5 τελευταιων εγχωριων (≤45 μερες) ----
SQ = {}
for fn in ('euro_squads.json', 'core7_squads.json'):
    for mid, v in json.load(open(fn, encoding='utf-8')).items():
        if v: SQ[str(mid)] = v
DATE = {}
for f in glob.glob('data_*.json'):
    if 'Europe' in f: continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for mid, m in d.items():
        try: DATE[str(mid)] = pd.Timestamp(_dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC'))
        except Exception: pass
DOMXI = {}
for mid, v in SQ.items():
    t = DATE.get(mid)
    if t is None: continue
    for k in ('h', 'a'):
        x = v.get(k) or {}
        if x.get('t') and x.get('mv'): DOMXI.setdefault(int(x['t']), []).append((t, float(x['mv']), set(x.get('st') or [])))
for k in DOMXI: DOMXI[k].sort(key=lambda z: z[0])
def xi_ratio(mid, side, ko):
    v = SQ.get(str(mid)) or {}; x = v.get(side) or {}
    if not x.get('t') or not x.get('mv'): return np.nan, np.nan
    prev = [z for z in DOMXI.get(int(x['t']), []) if ko - pd.Timedelta(days=45) <= z[0] < ko - pd.Timedelta(hours=12)][-5:]
    if len(prev) < 3: return np.nan, np.nan
    core = {}
    for z in prev:
        for p in z[2]: core[p] = core.get(p, 0) + 1
    top = set(sorted(core, key=lambda p: -core[p])[:11])
    changes = len(set(x.get('st') or []) - top)
    return float(x['mv']) / np.median([z[1] for z in prev]), changes
rows = []
for i in range(len(MIDS)):
    if SRCC[i] != 'FF': continue
    mid = MIDS[i]; t = EUT.get(str(mid)); j = VI.get(str(mid))
    if not t or j is None: continue
    s = snap_ah(mid, 'Crown', 0) or snap_ah(mid, 'SBOBET', 0)
    so = snap_ou(mid, 'Crown', 0) or snap_ou(mid, 'SBOBET', 0)
    if not s: continue
    ko = pd.Timestamp(V6['date'][j])
    rh, ch = xi_ratio(mid, 'h', ko); ra, ca = xi_ratio(mid, 'a', ko)
    rows.append(dict(i=i, comp=COMP[i], sea=SEA[i], phase=V6['phase'][j], home=t[2], away=t[3], lg_h=V6['lg_h'][j], lg_a=V6['lg_a'][j],
                     gd=GD[i], mgd=LH_N[i] - LA_N[i], kgd=implied_margin(i, *s), tot=GH[i] + GA[i], mtot_=OH[i] + OA[i],
                     ktot=mtot(*so) if so else np.nan, rh=rh, ra=ra, ch=ch, ca=ca))
X = pd.DataFrame(rows)
X['dis'] = X.mgd - X.kgd                       # διαφωνια μοντελου − αγορας (σκοπια γηπεδουχου)
X['rk'] = X.gd - X.kgd; X['rm'] = X.gd - X.mgd
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
def ols2(y, a, b):
    A = np.c_[np.ones(len(y)), a, b]; coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    e = y - A @ coef; s2 = (e ** 2).sum() / (len(y) - 3); cov = s2 * np.linalg.inv(A.T @ A)
    return coef[1:], np.sqrt(np.diag(cov))[1:]
def ols1(y, x):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
# ================= Η1 πληροφορια =================
print('Η1. ΠΟΙΟΣ ΠΡΟΒΛΕΠΕΙ ΤΟ ΑΠΟΤΕΛΕΣΜΑ — διαφορα γκολ ~ μοντελο + αγορα (κλεισιμο) μαζι. β μοντελου >0 = το μοντελο ξερει κατι που η αγορα δεν ξερει')
for lab, seas in (('4 σεζον', SEAS), ('νεα μορφη', NEW)):
    for cm in CL:
        x = X[(X.comp == cm) & X.sea.isin(seas)]
        (bm, bk), (sm, sk) = ols2(x.gd.values, x.mgd.values, x.kgd.values)
        bd, sd = ols1(x.rk.values, x.dis.values)
        print(f'   {lab:9s} {CL[cm]:5s} n{len(x):4d} · β μοντελο {bm:+.2f}±{sm:.2f} · β αγορα {bk:+.2f}±{sk:.2f} · '
              f'οταν διαφωνουμε, η αλη θεια πηγαινει προς εμας κατα {bd:+.2f}±{sd:.2f} (t {bd / sd:+.1f}) του χασματος')
# ================= Η2/Η3 εδρα & φαβορι εκτος =================
print(NL + 'Η2/Η3. ΕΔΡΑ ΚΑΙ ΦΑΒΟΡΙ ΕΚΤΟΣ — λαθος μοντελου / αγορας (σκοπια γηπεδουχου) ανα διοργανωση')
for cm in CL:
    x = X[X.comp == cm]
    fh = x.mgd > 0
    def ln(y): return f'n{len(y):4d} · μοντελο {y.rm.mean():+.2f}±{y.rm.std() / np.sqrt(len(y)):.2f} · αγορα {y.rk.mean():+.2f}'
    print(f'   {CL[cm]:5s} ολα {ln(x)} || φαβορι (μοντελου) ΕΝΤΟΣ {ln(x[fh])} || φαβορι ΕΚΤΟΣ {ln(x[~fh])}')
# ================= Η4 rotation =================
print(NL + 'Η4. ROTATION — αξια ευρωπαικης ενδεκαδας / διαμεσος 5 τελευταιων εγχωριων (1.00 = ιδια ενδεκαδα) · αλλαγες απο τη «βασικη» ενδεκαδα')
T = []
for r in X.itertuples():
    for side, rr, ch, fav, venue, lg in (('h', r.rh, r.ch, r.kgd > 0, 'εντος', r.lg_h), ('a', r.ra, r.ca, r.kgd < 0, 'εκτος', r.lg_a)):
        if np.isfinite(rr):
            sg = 1 if side == 'h' else -1
            T.append(dict(comp=r.comp, sea=r.sea, phase=r.phase, ratio=rr, ch=ch, fav=fav, venue=venue, top5=lg in TOP5,
                          rm=sg * r.rm, rk=sg * r.rk, dis=sg * r.dis))
T = pd.DataFrame(T)
for cm in CL:
    t = T[T.comp == cm]
    for lab, m in (('φαβορι', t.fav), ('αουτσαιντερ', ~t.fav)):
        y = t[m]
        print(f'   {CL[cm]:5s} {lab:11s} n{len(y):4d} · αξια ενδεκαδας {y.ratio.median():.2f} (διαμεσος) · ≤0.85 σε {100 * (y.ratio <= .85).mean():.0f}% · αλλαγες {y.ch.mean():.1f}')
print('   λαθος (σκοπια ομαδας) ανα αξια ενδεκαδας — ΦΑΒΟΡΙ (αγορας):')
for cm in CL:
    t = T[(T.comp == cm) & T.fav]
    cells = []
    for lo, hi, lb in ((0, .85, '≤0.85'), (.85, .97, '0.85-0.97'), (.97, 9, '≥0.97')):
        y = t[(t.ratio > lo) & (t.ratio <= hi)] if lo else t[t.ratio <= hi]
        if len(y): cells.append(f'{lb}: n{len(y)} μοντ {y.rm.mean():+.2f} αγορα {y.rk.mean():+.2f}')
    b, s = ols1(t.rm.values, np.log(t.ratio.values)); bk_, sk_ = ols1(t.rk.values, np.log(t.ratio.values))
    print(f'      {CL[cm]:5s} ' + ' · '.join(cells) + f' · κλιση λαθους ~ ln(αξια): μοντελο {b:+.2f} (t {b / s:+.1f}) / αγορα {bk_:+.2f} (t {bk_ / sk_:+.1f})')
# προβλεψιμο πριν το ματς; αξια ενδεκαδας στο ΠΡΟΗΓΟΥΜΕΝΟ ευρωπαικο ματς της ομαδας
# ================= Η5 μεσαιες ομαδες top-5 =================
print(NL + 'Η5. ΟΜΑΔΕΣ TOP-5 ΛΙΓΚΩΝ — λαθος μοντελου / αγορας (σκοπια ομαδας), φαβορι και αουτσαιντερ')
for cm in CL:
    t = T[T.comp == cm]
    cells = []
    for lab, m in (('top-5 φαβ', t.top5 & t.fav), ('top-5 αουτσ', t.top5 & ~t.fav), ('αλλες φαβ', ~t.top5 & t.fav), ('αλλες αουτσ', ~t.top5 & ~t.fav)):
        y = t[m]
        if len(y): cells.append(f'{lab}: n{len(y)} {y.rm.mean():+.2f}/{y.rk.mean():+.2f}')
    print(f'   {CL[cm]:5s} ' + ' · '.join(cells))
# ================= Η6 γκολ =================
print(NL + 'Η6. ΓΚΟΛ — πραγματικα / μοντελο (W2) / αγορα, και ποσο προβλεπει το καθε ενα (συνολο ~ μοντελο + αγορα)')
for cm in CL:
    x = X[(X.comp == cm) & np.isfinite(X.ktot)]
    (bm, bk), (sm, sk) = ols2(x.tot.values, x.mtot_.values, x.ktot.values)
    print(f'   {CL[cm]:5s} n{len(x):4d} · γκολ {x.tot.mean():.2f} · μοντελο {x.mtot_.mean():.2f} · αγορα {x.ktot.mean():.2f} · β μοντελο {bm:+.2f}±{sm:.2f} · β αγορα {bk:+.2f}±{sk:.2f}')
# ================= φαση =================
print(NL + 'ΦΑΣΗ (ομιλοι/λιγκα vs νοκ-αουτ): οταν διαφωνουμε, η αληθεια πηγαινει προς εμας κατα (κλιση) — και λαθος μοντελου')
for cm in CL:
    for ph, x in X[X.comp == cm].groupby('phase'):
        if len(x) < 40: continue
        bd, sd = ols1(x.rk.values, x.dis.values)
        print(f'   {CL[cm]:5s} {ph:8s} n{len(x):4d} · κλιση {bd:+.2f} (t {bd / sd:+.1f}) · λαθος μοντελου {x.rm.mean():+.2f}')
X.to_pickle('uel_vs_ucl_diag_rows.pkl'); T.to_pickle('uel_vs_ucl_diag_teams.pkl')

# ================= ΕΠΙΠΛΕΟΝ: τυφλο χαντικαπ ΦΑΒΟΡΙ ΑΓΟΡΑΣ στο κλεισιμο ανα αξια ενδεκαδας του φαβορι =================
print(NL + 'ΕΠΙΠΛΕΟΝ: ΤΥΦΛΟ χαντικαπ φαβορι αγορας στο ΚΛΕΙΣΙΜΟ (≤−0.25), ανα αξια της ενδεκαδας του φαβορι (γνωστη ~1ω πριν, με τις ενδεκαδες)')
rows2 = []
for r in X.itertuples():
    i = r.i
    for bk in ('Crown', 'SBOBET'):
        s = snap_ah(MIDS[i], bk, 0)
        if not s: continue
        L, oh, oa = s
        if abs(L) < 0.2: continue
        side = 1 if L < 0 else -1; ln = L if side == 1 else -L; o = oh if side == 1 else oa
        ratio = r.rh if side == 1 else r.ra
        if not np.isfinite(ratio) or not (1.5 <= o <= 2.5): continue
        rows2.append(dict(comp=r.comp, sea=r.sea, bk=bk, ratio=ratio, home=side == 1, pnl=picks.settle(GD[i], side, ln, o)))
B2 = pd.DataFrame(rows2)
def cc2(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
for cm in CL:
    b = B2[B2.comp == cm]
    print(f'   {CL[cm]:5s} ≤0.85 {cc2(b[b.ratio <= .85])} · 0.85-0.97 {cc2(b[(b.ratio > .85) & (b.ratio < .97)])} · ≥0.97 {cc2(b[b.ratio >= .97])}')
