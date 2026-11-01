"""
uel_battery.py — 9/10/2026 (Στελιος «ξεκινα με τα τεστ του europa»): ΜΠΑΤΑΡΙΑ EUROPA LEAGUE με τη ΣΗΜΕΡΙΝΗ live ευρωπαικη αλυσιδα
(w=2 prior, γ=−0.47, ισοπαλια ×0.85, κ UCL νεου format, φαβορι σωστα τεταρτα / dogs p_cover — harness euro_ucl_kappa2), 2223-2526.
(Το τεστ χρονισμου εγινε ηδη 10/9 — euro_early_roi: UEL αρνητικο και νωρις → δεν επαναλαμβανεται.)
Α. Φωτογραφια σημερα: ROI as-live ανα διοργανωση × ρολο × βιβλιο (Crown, SBOBET κλεισιμο), FotMob+FotMob, 1.70-2.10,
   κατωφλια live (UCL φαβ@10 dog@4 · UEL/UECL φαβ@4 dog@10).
Β. Διαγνωση UEL: πραγματικο − μοντελο / πραγματικο − αγορα (σκοπια φαβορι ΜΟΝΤΕΛΟΥ) ανα: εδρα φαβορι, ισχυς, top-5, μορφη, φαση,
   αγωνιστικη 7-8 (νεα μορφη), αποσταση ταξιδιου.
Γ. Διορθωσεις UEL με LOSO (εκπαιδευση 3 σεζον UEL, κριση στην 4η): (1) εδρα UEL h · (2) αποσταση a·ln(1+km/1000) · (3) κλιμακα φαβορι
   κ_UEL (νεα μορφη, 2-fold) · (4) ισοπαλια UEL.
ΠΡΟ-ΔΗΛΩΣΗ Γ: περνα αν LOSO πιθανοφανεια (γκολ ή 1Χ2) καλυτερη σε ≥3/4 σεζον (2/2 για κ) ΚΑΙ UEL picks ROI (μεσος Crown/SBOBET)
βελτιωνεται σε ≥3/4 σεζον ΚΑΙ γινεται θετικο συνολο.
"""
import sys, io, json, glob, math, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_ucl_kappa2.py', encoding='utf-8').read()
pre = src[:src.index('# ---------------- 1-3)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'uelb'}
with contextlib.redirect_stdout(io.StringIO()): exec(pre, g)
MIDS, SNAP, GD, SEA, COMP, PHASE, FM, picks = g['MIDS'], g['SNAP'], g['GD'], g['SEA'], g['COMP'], g['PHASE'], g['FM'], g['picks']
LH_N, LA_N, GH, GA, KO, parse_line, CLOSE_TOL, EU_DRAW_SCALE = g['LH_N'], g['LA_N'], g['GH'], g['GA'], g['KO'], g['parse_line'], g['CLOSE_TOL'], g['EU_DRAW_SCALE']
V6 = pickle.load(open('euro_v6_preds.pkl', 'rb')); LGH = np.array(V6['lg_h']); LGA = np.array(V6['lg_a'])
N = len(MIDS); IDX = {m: i for i, m in enumerate(MIDS)}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
# ---- SBOBET κλεισιμο ----
SB = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] != 31: continue
        mid = str(r['mid']); ko = KO.get(mid); rows = []
        for mt, u, gg, dn in r.get('ah') or []:
            gl = parse_line(gg)
            try: rows.append((int(mt), -gl, float(u) + 1, float(dn) + 1))
            except (TypeError, ValueError): pass
        rows = sorted(x for x in rows if x[1] is not None and ko and x[0] <= ko + CLOSE_TOL)
        if rows: SB[mid] = rows[-1][1:]
# ---- γυρος, ομαδες, αποσταση ----
FX = json.load(open('europe_fixtures.json', encoding='utf-8')); RND = {}; TEAMS = {}
for k, lst in FX.items():
    for m in lst: RND[str(m['mid'])] = m.get('round'); TEAMS[str(m['mid'])] = (m['hid'], m['aid'])
ST = json.load(open('weather_euro_stadiums.json', encoding='utf-8'))
HOMEC = {}
for mid, (h, a) in TEAMS.items():
    s = ST.get(mid)
    if s and s.get('lat') is not None: HOMEC.setdefault(h, []).append((float(s['lat']), float(s['lon'])))
HOMEC = {t: (np.median([x[0] for x in v]), np.median([x[1] for x in v])) for t, v in HOMEC.items()}
def km(a, b):
    p = math.pi / 180; x = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
DIST_KM = np.array([km(HOMEC[TEAMS[m][0]], HOMEC[TEAMS[m][1]]) if m in TEAMS and TEAMS[m][0] in HOMEC and TEAMS[m][1] in HOMEC else np.nan for m in MIDS])
R78 = np.array([(RND.get(m) in ('7', '8')) for m in MIDS]); NEW = np.isin(SEA, ('2425', '2526'))
print(f'δειγμα {N} · UEL {int((COMP == "EuropaLeague").sum())} · με αποσταση {np.isfinite(DIST_KM).sum()} · SBOBET κλεισιμο {sum(1 for m in MIDS if m in SB)}')
def sdist(lh, la, ds=EU_DRAW_SCALE):
    d = picks.gd_dist(max(lh, .05), max(la, .05)); p0 = d.get(0, 0.0); n0 = p0 * ds; f = (1 - n0) / (1 - p0)
    return {k: (n0 if k == 0 else p * f) for k, p in d.items()}
def cover_q(dist, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]; pw = pp = 0.0
    for L in parts:
        for k, p in dist.items():
            m_ = (k if side == 1 else -k) + L
            if m_ > .01: pw += p / len(parts)
            elif abs(m_) <= .01: pp += p / len(parts)
    return pw, pp
def edge(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
def make_picks(LH, LA, ds=EU_DRAW_SCALE, mask=None):
    rows = []
    for i, mid in enumerate(MIDS):
        if not FM[i] or (mask is not None and not mask[i]): continue
        dist = None
        for bk, snap in (('Crown', SNAP.get(mid)), ('SBOBET', SB.get(mid))):
            if not snap: continue
            if dist is None: dist = sdist(LH[i], LA[i], ds)
            L, oh, oa = snap
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                role = 'fav' if ln < 0 else 'dog'
                pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                e = edge(pw, pp, o); c = COMP[i]
                thr = (0.10 if role == 'fav' else 0.04) if c == 'ChampionsLeague' else (0.04 if role == 'fav' else 0.10)
                if e >= thr: rows.append(dict(i=i, comp=c, sea=SEA[i], book=bk, role=role, home=side == 1, pnl=picks.settle(GD[i], side, ln, o)))
    return pd.DataFrame(rows)
def fm(d):
    if len(d) < 4: return f'n{len(d) / 2:4.0f}' + ' ' * 32
    ps = d.groupby('sea').pnl.mean(); pb = d.groupby('book').pnl.mean()
    return f'n{len(d) / d.book.nunique():4.0f} {100 * d.pnl.mean():+6.1f}% {d.pnl.sum() / d.book.nunique():+6.1f}u σεζ {int((ps > 0).sum())}/{ps.size} βιβλ {int((pb > 0).sum())}/{pb.size}'
P0 = make_picks(LH_N, LA_N)
print('\nΑ. ΦΩΤΟΓΡΑΦΙΑ ΣΗΜΕΡΑ (κλεισιμο, μεσος Crown/SBOBET)')
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    x = P0[P0.comp == c]; print(f'   {c:17s} ολα {fm(x)} · φαβ {fm(x[x.role == "fav"])} · dogs {fm(x[x.role == "dog"])}')
x = P0[P0.comp == 'EuropaLeague']; print('   UEL ανα σεζον: ' + ' · '.join(f'{s}: {fm(v)[:22]}' for s, v in x.groupby('sea')))
# ---- Β διαγνωση ----
def mkt_sup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
SM = np.array([mkt_sup(*SNAP[m], LH_N[i] + LA_N[i]) if m in SNAP else np.nan for i, m in enumerate(MIDS)])
SMOD = LH_N - LA_N; sg = np.sign(SMOD); sg[sg == 0] = 1
U = (COMP == 'EuropaLeague') & np.isfinite(SM)
def ols(y, X):
    X = np.c_[np.ones(len(y)), X]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    return b, np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (e @ e) / max(len(y) - X.shape[1], 1))
def drow(mask, lab):
    m = U & mask
    if m.sum() < 20: return f'   {lab:34s} n{m.sum():4d}'
    y = GD[m] * sg[m]; em = y - SMOD[m] * sg[m]; ek = y - SM[m] * sg[m]
    b, se = ols(GD[m] - SM[m], (SMOD[m] - SM[m]))
    return (f'   {lab:34s} n{m.sum():4d} · πραγμ−μοντελο {em.mean():+.2f}±{em.std() / np.sqrt(m.sum()):.2f} · πραγμ−αγορα {ek.mean():+.2f}'
            f' · μοντελο−αγορα {((SMOD[m] - SM[m]) * sg[m]).mean():+.2f} · πληροφορια β {b[1]:+.2f} (t {b[1] / se[1]:+.1f})')
print('\nΒ. ΔΙΑΓΝΩΣΗ UEL (σκοπια φαβορι ΜΟΝΤΕΛΟΥ· θετικο = το φαβορι πηγε καλυτερα· β = πληροφορια μοντελου πανω απο κλεισιμο)')
T5H = np.isin(LGH, list(TOP5)); T5A = np.isin(LGA, list(TOP5)); FAVH = SMOD >= 0
print(drow(np.ones(N, bool), 'ΟΛΑ UEL'))
print(drow(FM, 'μονο FotMob+FotMob'))
print(drow(FAVH, 'φαβορι γηπεδουχος')); print(drow(~FAVH, 'φαβορι φιλοξενουμενος'))
for lo, hi in ((0, .5), (.5, 1), (1, 9)): print(drow((np.abs(SMOD) >= lo) & (np.abs(SMOD) < hi), f'|υπεροχη μοντελου| {lo}-{hi}'))
FT5 = np.where(FAVH, T5H, T5A); DT5 = np.where(FAVH, T5A, T5H)
print(drow(FT5 & ~DT5, 'φαβορι top-5, αουτσαιντερ οχι')); print(drow(~FT5 & DT5, 'αουτσαιντερ top-5, φαβορι οχι'))
print(drow(FT5 & DT5, 'και οι δυο top-5')); print(drow(~FT5 & ~DT5, 'καμια top-5'))
print(drow(~NEW, 'παλια μορφη 2223-2324')); print(drow(NEW, 'νεα μορφη 2425-2526'))
print(drow(PHASE == 'league', 'ομιλοι/League Phase')); print(drow(PHASE == 'KO', 'νοκ-αουτ'))
print(drow(NEW & R78, 'νεα μορφη αγων 7-8')); print(drow(NEW & ~R78 & (PHASE == 'league'), 'νεα μορφη αγων 1-6'))
q = np.nanpercentile(DIST_KM[U], [33, 67])
print(drow(DIST_KM < q[0], f'αποσταση <{q[0]:.0f} km')); print(drow((DIST_KM >= q[0]) & (DIST_KM < q[1]), f'αποσταση {q[0]:.0f}-{q[1]:.0f} km')); print(drow(DIST_KM >= q[1], f'αποσταση ≥{q[1]:.0f} km'))
# εδρα (σκοπια γηπεδουχου)
m = U; print(f'   ΕΔΡΑ UEL: πραγμ−μοντελο (γηπεδουχος) {np.mean(GD[m] - SMOD[m]):+.3f}±{np.std(GD[m] - SMOD[m]) / np.sqrt(m.sum()):.3f} · UCL {np.mean((GD - SMOD)[(COMP == "ChampionsLeague") & np.isfinite(SM)]):+.3f} · UECL {np.mean((GD - SMOD)[(COMP == "ConferenceLeague") & np.isfinite(SM)]):+.3f}')
# ---- Γ διορθωσεις LOSO ----
UEL = COMP == 'EuropaLeague'; SEAS = ('2223', '2324', '2425', '2526')
def ll_goals(LH, LA, mask): return float(np.sum(GH[mask] * np.log(LH[mask]) - LH[mask] + GA[mask] * np.log(LA[mask]) - LA[mask]))
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))
def ll_1x2(LH, LA, ds, mask):
    s = 0.0
    for i in np.where(mask)[0]:
        d = sdist(LH[i], LA[i], ds); p = [sum(v for k, v in d.items() if k > 0), d.get(0, 0), sum(v for k, v in d.items() if k < 0)][OUT3[i]]
        s += math.log(max(p, 1e-9))
    return s
Z = np.nan_to_num(np.log1p(DIST_KM / 1000.0))
FIXES = {
    'εδρα UEL h': (np.round(np.arange(0.90, 1.205, 0.02), 3), lambda v: (np.where(UEL, LH_N * v, LH_N), np.where(UEL, LA_N / v, LA_N)), 'goals', SEAS),
    'αποσταση a': (np.round(np.arange(-0.15, 0.155, 0.025), 3), lambda v: (np.where(UEL, LH_N * np.exp(v * Z), LH_N), np.where(UEL, LA_N * np.exp(-v * Z), LA_N)), 'goals', SEAS),
    'κλιμακα φαβ κ_UEL (νεα)': (np.round(np.arange(0.90, 1.205, 0.02), 3), lambda v: (np.where(UEL & NEW & FAVH, LH_N * v, LH_N), np.where(UEL & NEW & ~FAVH, LA_N * v, LA_N)), 'goals', ('2425', '2526')),
    'ισοπαλια UEL': (np.round(np.arange(0.70, 1.005, 0.05), 3), None, '1x2', SEAS),
}
print('\nΓ. ΔΙΟΡΘΩΣΕΙΣ UEL — LOSO (τιμη απο τις αλλες σεζον) · Δπιθανοφανεια (θετικο = καλυτερο) · picks UEL')
base_p = P0[P0.comp == 'EuropaLeague']
for name, (grid, fn, kind, seas) in FIXES.items():
    res = []; chosen = {}; dll = {}
    for te in seas:
        tr = UEL & np.isin(SEA, [s for s in seas if s != te]); tm = UEL & (SEA == te)
        if kind == 'goals':
            best = max(grid, key=lambda v: ll_goals(*fn(v), tr)); LHv, LAv = fn(best)
            dll[te] = ll_goals(LHv, LAv, tm) - ll_goals(LH_N, LA_N, tm); P = make_picks(LHv, LAv, mask=tm)
        else:
            best = max(grid, key=lambda v: ll_1x2(LH_N, LA_N, v, tr))
            dll[te] = ll_1x2(LH_N, LA_N, best, tm) - ll_1x2(LH_N, LA_N, EU_DRAW_SCALE, tm); P = make_picks(LH_N, LA_N, ds=best, mask=tm)
        chosen[te] = best; res.append(P[P.comp == 'EuropaLeague'])
    R = pd.concat(res) if res else pd.DataFrame(columns=base_p.columns); B0 = base_p[base_p.sea.isin(seas)]
    rs = R.groupby('sea').pnl.mean() if len(R) else pd.Series(dtype=float); bs = B0.groupby('sea').pnl.mean()
    c1 = sum(v > 0 for v in dll.values()) >= (3 if len(seas) == 4 else 2)
    c2 = int((rs.reindex(bs.index).fillna(-9) > bs).sum()) >= (3 if len(seas) == 4 else 2) and len(R) and R.pnl.mean() > 0
    print(f'   {name:24s} τιμες {chosen} · Δπιθ. ' + ' '.join(f'{s}:{v:+.1f}' for s, v in dll.items())
          + f'\n   {"":24s} picks UEL {fm(R)} vs σημερα {fm(B0)} → {"ΠΕΡΝΑ" if c1 and c2 else "ΔΕΝ ΠΕΡΝΑ"}')
