"""
euro_rotation_model.py — 9/10/2026 (Στελιος «τρεξε το τεστ πως θα ηταν»): ADVANCED διορθωση καταστασης πανω στο ευρωπαικο μοντελο.
Για καθε ομαδα σε καθε ευρωπαικο ματς (2223-2526): γκολ (και xG) ~ Poisson( λ_μοντελου × exp(X·β) ) — η προβλεψη μενει βαση (offset),
εκτιμαται μονο η ΔΙΟΡΘΩΣΗ ανα κατασταση, με ridge συρρικνωση. LOSO ανα σεζον.
Παραγοντες (ΟΛΟΙ γνωστοι ΠΡΙΝ την ενδεκαδα):
  • διοργανωση × εντος/εκτος
  • κατηγορια ομαδας: top-5 πανω (θεση 1-4) / top-5 ΜΕΣΑΙΑ (5-10) / top-5 κατω (11+) / PT-NL / αλλη — θεση στη ΦΕΤΙΝΗ βαθμολογια τη μερα
    του ματς (περσινη αν <5 εγχωρια)
  • ΡΟΠΗ ΣΕ ΡΟΤΕΙΣΟΝ: μεσος αριθμος βασικων που ΔΕΝ ξεκινησαν στα ΠΡΟΗΓΟΥΜΕΝΑ ευρωπαικα της ομαδας (βασικοι = top-11 σε εγχωριες
    εκκινησεις πριν το ματς, player_matches.json), συρρικνωμενο προς τον μεσο (k=3) — μονο CORE7 ομαδες
  • επομενο εγχωριο ≤4 μερες μετα ΚΑΙ αντιπαλος top-6 της φετινης βαθμολογιας («μεγαλο ματς Κυριακη») · προηγουμενο εγχωριο ≤3 μερες πριν
  • αποσταση ταξιδιου (εκτος) · αγωνιστικη 7-8 νεας μορφης
Μοντελα: M1 διοργανωση×εδρα · M2 +κατηγορια · M3 +ροπη ροτεισον +προγραμμα +ταξιδι.
ΠΡΟ-ΔΗΛΩΣΗ: (1) πιθανοφανεια γκολ εκτος δειγματος καλυτερη απο σημερα σε ≥3/4 σεζον στο UEL ΚΑΙ οχι χειροτερη συνολικα σε UCL+UECL·
(2) πληροφορια β πανω απο το κλεισιμο στο UEL αυξανεται· (3) picks UEL (μεσος Crown/SBOBET, κλεισιμο) >0 ΚΑΙ καλυτερα απο σημερα σε ≥3/4 σεζον.
Διαγνωστικο: ο ΠΡΑΓΜΑΤΙΚΟΣ αριθμος αλλαγων (εκ των υστερων) εξηγει το λαθος; προβλεπεται απο τη ροπη;
"""
import sys, io, json, math, contextlib, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_home_why.py', encoding='utf-8').read(); src = src[:src.index("print('1. ΕΔΡΑ")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'rot'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, COMP, SEA, PHASE, NEW, GD, GH, GA, LH_N, LA_N, SM, DIST_KM, LGH, LGA, TEAMS, FM, XH, XA = (g[k] for k in (
    'MIDS', 'COMP', 'SEA', 'PHASE', 'NEW', 'GD', 'GH', 'GA', 'LH_N', 'LA_N', 'SM', 'DIST_KM', 'LGH', 'LGA', 'TEAMS', 'FM', 'XH', 'XA'))
B = g['g']; make_picks, fm, P_LIVE = B['make_picks'], B['fm'], B['P0']
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}; CORE7 = TOP5 | {'PrimeiraLiga', 'Eredivisie'}
N = len(MIDS)
FX = json.load(open('europe_fixtures.json', encoding='utf-8')); KO = {}; RND = {}
for k, lst in FX.items():
    for m in lst: KO[str(m['mid'])] = datetime.datetime.fromisoformat(m['utc'].replace('Z', '+00:00')).timestamp(); RND[str(m['mid'])] = m.get('round')
PM = json.load(open('player_matches.json', encoding='utf-8'))
def starters(mid, side):
    r = PM.get(str(mid))
    if not r or side not in r or not r[side]: return None
    return {int(p[0]) for p in r[side]['p'] if p[4] == 1}
# ---- εγχωρια: προγραμμα, βαθμολογια, εκκινησεις ----
DOM = {}          # (team, sea) -> λιστα (ts, mid, side, opp, gf, ga)
LGOF = {}         # (team, sea) -> lg
for lg in CORE7:
    for sea in ('2122', '2223', '2324', '2425', '2526'):
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for mid, m in d.items():
            if m.get('hs') is None: continue
            ts = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=datetime.timezone.utc).timestamp()
            h, a = m['home']['id'], m['away']['id']
            DOM.setdefault((h, sea), []).append((ts, mid, 'h', a, m['hs'], m['as'])); DOM.setdefault((a, sea), []).append((ts, mid, 'a', h, m['as'], m['hs']))
            LGOF[(h, sea)] = lg; LGOF[(a, sea)] = lg
for k in DOM: DOM[k].sort()
TEAMS_LG = {}
for (t, sea), lg in LGOF.items(): TEAMS_LG.setdefault((lg, sea), set()).add(t)
def prev(s): return f'{int(s[:2]) - 1:02d}{int(s[2:]) - 1:02d}'
def table_pos(lg, sea, t, ts):
    pts = {}
    for tt in TEAMS_LG.get((lg, sea), ()):
        p = gd_ = 0
        for x in DOM.get((tt, sea), []):
            if x[0] >= ts: break
            p += 3 if x[4] > x[5] else (1 if x[4] == x[5] else 0); gd_ += x[4] - x[5]
        pts[tt] = (p, gd_)
    order = sorted(pts, key=lambda z: (-pts[z][0], -pts[z][1]))
    return order.index(t) + 1 if t in order else None
FINAL = {}
for (lg, sea), ts_ in TEAMS_LG.items():
    for t in ts_: FINAL[(t, sea)] = table_pos(lg, sea, t, 9e12)
REG_CACHE = {}
def regulars(t, sea, ts):
    key = (t, sea, int(ts // 86400))
    if key in REG_CACHE: return REG_CACHE[key]
    cnt = {}; n = 0
    for x in DOM.get((t, sea), []):
        if x[0] >= ts: break
        s = starters(x[1], x[2])
        if s: n += 1; [cnt.__setitem__(p, cnt.get(p, 0) + 1) for p in s]
    if n < 5:
        for x in DOM.get((t, prev(sea)), []):
            s = starters(x[1], x[2])
            if s: [cnt.__setitem__(p, cnt.get(p, 0) + 0.5) for p in s]
    r = set(sorted(cnt, key=lambda p: -cnt[p])[:11]) if cnt else None
    REG_CACHE[key] = r; return r
# ---- πλευρες ----
rows = []
for i, mid in enumerate(MIDS):
    if mid not in TEAMS or mid not in KO: continue
    ts = KO[mid]; sea = SEA[i]
    for side, t, opp, lg, home in (('h', TEAMS[mid][0], TEAMS[mid][1], LGH[i], 1), ('a', TEAMS[mid][1], TEAMS[mid][0], LGA[i], 0)):
        rec = dict(i=i, mid=mid, sea=sea, comp=COMP[i], home=home, lg=lg, team=t, ts=ts,
                   y=float(GH[i] if home else GA[i]), x=float(XH[i] if home else XA[i]) if np.isfinite(XH[i]) else np.nan,
                   lam=float(LH_N[i] if home else LA_N[i]), dist=float(DIST_KM[i]) if not home else 0.0,
                   r78=int(NEW[i] and RND.get(mid) in ('7', '8')))
        if lg in CORE7 and (t, sea) in DOM:
            nplayed = sum(1 for x in DOM[(t, sea)] if x[0] < ts)
            pos = table_pos(lg, sea, t, ts) if nplayed >= 5 else FINAL.get((t, prev(sea)))
            nxt = [x for x in DOM[(t, sea)] if x[0] > ts]; prv = [x for x in DOM[(t, sea)] if x[0] < ts]
            rec['big_next'] = int(bool(nxt) and (nxt[0][0] - ts) / 86400 <= 4.5 and (table_pos(lg, sea, nxt[0][3], ts) or 99) <= 6)
            rec['short_rest'] = int(bool(prv) and (ts - prv[-1][0]) / 86400 <= 3.2)
            reg = regulars(t, sea, ts); st = starters(mid, side)
            rec['nb'] = len(reg & st) if reg and st else np.nan
            rec['cls'] = ('top5_top' if pos and pos <= 4 else ('top5_mid' if pos and pos <= 10 else 'top5_low')) if lg in TOP5 else 'ptnl'
            if pos is None and lg in TOP5: rec['cls'] = 'top5_mid'
        else:
            rec.update(big_next=0, short_rest=0, nb=np.nan, cls='other')
        rows.append(rec)
S = pd.DataFrame(rows).sort_values('ts').reset_index(drop=True)
S['rot'] = 11 - S.nb
# ροπη ροτεισον ex-ante: προηγουμενα ευρωπαικα της ομαδας (και περσινα), συρρικνωση k=3 προς τον γενικο μεσο
mean_rot = S.rot.mean(); K = 3.0; hist = {}; prop = []
for r in S.itertuples():
    h = hist.get(r.team, [])
    prop.append((sum(h) + K * mean_rot) / (len(h) + K) if r.cls != 'other' else np.nan)
    if np.isfinite(r.rot): hist.setdefault(r.team, []).append(r.rot)
S['prop'] = prop
print(f'πλευρες {len(S)} · με ενδεκαδα/βασικους {S.nb.notna().sum()} · μεσες αλλαγες {mean_rot:.2f}/11 · ροπη: μεσος {np.nanmean(S.prop):.2f} sd {np.nanstd(S.prop):.2f}')
print('   μεσες αλλαγες (εκ των υστερων) ανα διοργανωση × εδρα × κατηγορια:')
print(S[S.nb.notna()].groupby(['comp', 'home', 'cls']).rot.agg(['size', 'mean']).round(2).unstack('home').to_string())
# ---- διαγνωστικο: οι αλλαγες εξηγουν το λαθος; προβλεπονται; ----
Z = S[S.nb.notna()]
for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    z = Z[Z.comp == c]
    if len(z) < 30: continue
    b = np.polyfit(z.rot, np.log((z.y + 0.5) / (z.lam + 0.5)), 1); bx = np.polyfit(z.rot[z.x.notna()], np.log((z.x[z.x.notna()] + 0.1) / (z.lam[z.x.notna()] + 0.1)), 1)
    print(f'   [{c}] ανα 1 επιπλεον αλλαγη: γκολ ×{math.exp(b[0]):.3f} · xG ×{math.exp(bx[0]):.3f} · corr(ροπη, πραγματικες αλλαγες) {z.prop.corr(z.rot):.2f} (n{len(z)})')
# ---- σχεδιασμος ----
def design(D, model):
    away = 1 - D.home.values; uel = (D.comp == 'EuropaLeague').values; uecl = (D.comp == 'ConferenceLeague').values
    cols = {'σταθ': np.ones(len(D)), 'εκτος': away, 'UEL': uel, 'UECL': uecl, 'εκτος×UEL': away * uel, 'εκτος×UECL': away * uecl}
    if model >= 2:
        mid = (D.cls == 'top5_mid').values; oth = (D.cls == 'other').values; top = (D.cls == 'top5_top').values
        cols.update({'μεσαια': mid, 'μεσαια×εκτος': mid * away, 'μεσαια×UEL': mid * uel, 'μεσαια×εκτος×UEL': mid * away * uel,
                     'πανω top5': top, 'αλλη λιγκα': oth, 'αλλη×εκτος': oth * away})
    if model >= 3:
        pr = np.nan_to_num(D.prop.values - mean_rot)
        cols.update({'ροπη': pr, 'ροπη×εκτος': pr * away, 'ροπη×UEL': pr * uel, 'μεγαλο ματς μετα': D.big_next.values, 'λιγη ξεκουραση': D.short_rest.values,
                     'ταξιδι': np.log1p(np.nan_to_num(D.dist.values) / 1000) * away, 'αγων 7-8': D.r78.values})
    return np.column_stack([np.asarray(v, float) for v in cols.values()]), list(cols)
def fit(X, y, off, ridge=3.0):
    b = np.zeros(X.shape[1]); R = np.eye(X.shape[1]) * ridge; R[0, 0] = 0
    for _ in range(30):
        eta = off + X @ b; mu = np.exp(eta); W = mu; z = X @ b + (y - mu) / mu
        A = X.T @ (W[:, None] * X) + R; bn = np.linalg.solve(A, X.T @ (W * z))
        if np.max(np.abs(bn - b)) < 1e-7: b = bn; break
        b = bn
    cov = np.linalg.inv(A); return b, np.sqrt(np.diag(cov))
def pll(y, mu): return float(np.sum(y * np.log(mu) - mu))
SEAS = ('2223', '2324', '2425', '2526'); OFF = np.log(S.lam.values)
res = {}; ADJ = {m: np.zeros(len(S)) for m in (1, 2, 3)}
print('\nΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ (LOSO) — Δ πιθανοφανεια γκολ vs σημερα (θετικο = καλυτερο) · ανα σεζον')
for model in (1, 2, 3):
    X, names = design(S, model); out = {}
    for te in SEAS:
        tr = (S.sea != te).values; tm = ~tr
        b, _ = fit(X[tr], S.y.values[tr], OFF[tr]); ADJ[model][tm] = X[tm] @ b
        for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
            mm = tm & (S.comp == c).values
            out[(c, te)] = pll(S.y.values[mm], np.exp(OFF[mm] + ADJ[model][mm])) - pll(S.y.values[mm], np.exp(OFF[mm]))
    res[model] = out
    for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
        v = [out[(c, s)] for s in SEAS]
        print(f'   M{model} [{c:17s}] σεζον ' + ' '.join(f'{x:+6.1f}' for x in v) + f' · συνολο {sum(v):+6.1f} · καλυτερο σε {sum(x > 0 for x in v)}/4')
# xG ως στοχος (πιο σταθερος)
print('\n   Ιδια με στοχο xG (Δ ψευδο-πιθανοφανεια, μονο ματς με xG):')
for model in (1, 2, 3):
    X, _ = design(S, model); okx = S.x.notna().values; v = {}
    for te in SEAS:
        tr = (S.sea != te).values & okx; tm = (S.sea == te).values & okx & (S.comp == 'EuropaLeague').values
        b, _ = fit(X[tr], S.x.values[tr], OFF[tr]); v[te] = pll(S.x.values[tm], np.exp(OFF[tm] + X[tm] @ b)) - pll(S.x.values[tm], np.exp(OFF[tm]))
    print(f'   M{model} [EuropaLeague xG] ' + ' '.join(f'{x:+6.1f}' for x in v.values()) + f' · {sum(x > 0 for x in v.values())}/4')
# ---- συντελεστες πληρους M3 ----
X, names = design(S, 3); b, se = fit(X, S.y.values, OFF)
print('\nΣΥΝΤΕΛΕΣΤΕΣ M3 (ολο το δειγμα, πολλαπλασιαστης γκολ = e^β):')
for n_, bb, ss in zip(names, b, se): print(f'   {n_:20s} ×{math.exp(bb):.3f}  (β {bb:+.3f} ±{ss:.3f}, t {bb / ss:+.1f})')
# ---- picks με τη διορθωση (LOSO) ----
print('\nPICKS με τη διορθωση (εκτος δειγματος) — κλεισιμο, μεσος Crown/SBOBET, σημερινοι κανονες')
L0 = LH_N.copy(); A0 = LA_N.copy()
for model in (2, 3):
    LH = LH_N.copy(); LA = LA_N.copy()
    for r, adj in zip(S.itertuples(), ADJ[model]):
        if r.home: LH[r.i] = LH_N[r.i] * math.exp(adj)
        else: LA[r.i] = LA_N[r.i] * math.exp(adj)
    P = make_picks(LH, LA)
    for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
        x = P[P.comp == c]; x0 = P_LIVE[P_LIVE.comp == c]
        ps = x.groupby('sea').pnl.mean(); p0 = x0.groupby('sea').pnl.mean()
        better = int((ps.reindex(p0.index).fillna(-9) > p0).sum())
        print(f'   M{model} [{c:17s}] {fm(x)} · σημερα {fm(x0)[:24]} · καλυτερα σε {better}/4 σεζον')
    # πληροφορια β πανω απο αγορα στο UEL
    U = (COMP == 'EuropaLeague') & np.isfinite(SM)
    def beta(sm):
        y = GD[U] - SM[U]; X_ = np.c_[np.ones(U.sum()), sm[U] - SM[U]]; bb, *_ = np.linalg.lstsq(X_, y, rcond=None); e = y - X_ @ bb
        return bb[1], bb[1] / np.sqrt(np.linalg.inv(X_.T @ X_)[1, 1] * (e @ e) / (len(y) - 2))
    b0, t0 = beta(LH_N - LA_N); b1, t1 = beta(LH - LA)
    print(f'   M{model} UEL πληροφορια πανω απο κλεισιμο: σημερα β {b0:+.2f} (t {t0:+.1f}) → {b1:+.2f} (t {t1:+.1f})')
