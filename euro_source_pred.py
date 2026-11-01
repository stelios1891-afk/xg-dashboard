"""
euro_source_pred.py — 9/10/2026 (Στελιος: «μπορουμε να φερουμε τις προβλεψεις Ben xG και γκολ/Elo πιο κοντα στο FotMob; οχι ROI, τεστ προβλεψης»).
Σημερινη ευρωπαικη αλυσιδα, ολα τα ευρωπαικα 2223-2526. ΠΡΟΒΛΕΨΗ μονο (καμια αποδοση στα κριτηρια).
1. ΜΕΡΟΛΗΨΙΑ ανα πηγη: για καθε ομαδα σε ματς, γκολ − λ_μοντελου και xG − λ (επιθεση) · και ποσα δεχεται ο αντιπαλος της (αμυνα).
   Και ανα ζευγος πηγων: υπεροχη (σκοπια της ομαδας εκτος-FotMob) πραγματικο − μοντελο · αγορα − μοντελο.
2. ΑΚΡΙΒΕΙΑ: RMSE διαφορας γκολ (μοντελο vs αγορα) ανα ζευγος πηγων.
3. ΔΙΟΡΘΩΣΗ (LOSO ανα σεζον): log μ = log λ + α[πηγη ομαδας] + δ[πηγη αντιπαλου] (FotMob = 0) — Poisson με offset, ridge.
   Παραλλαγη: χωριστα για εντος/εκτος. ΚΡΙΤΗΡΙΟ (προ-δηλωμενο): πιθανοφανεια γκολ των ματς με εστω μια ομαδα εκτος-FotMob καλυτερη σε ≥3/4
   σεζον ΚΑΙ RMSE διαφορας γκολ μικροτερο ΚΑΙ μεροληψια μετα τη διορθωση |·| < 0.10 γκολ.
"""
import sys, io, json, pickle, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'sp'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, GH, GA, SEA, COMP, LH_N, LA_N, SNAP, TEAMS = (g[k] for k in ('MIDS', 'GD', 'GH', 'GA', 'SEA', 'COMP', 'LH_N', 'LA_N', 'SNAP', 'TEAMS'))
mkt_sup = None
V = pickle.load(open('euro_v6_preds.pkl', 'rb')); NAME = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ/Elo'}
SH = np.array([NAME[s] for s in V['src_h']]); SA = np.array([NAME[s] for s in V['src_a']])
XG = {}
for sea in ('2223', '2324', '2425', '2526'):
    for mid, m in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not m.get('shots') or m.get('hs') is None: continue
        h, a = int(m['home']['id']), int(m['away']['id']); agg = {h: 0.0, a: 0.0}
        for s in m['shots']:
            if s.get('xg') is not None and s.get('tid') in agg: agg[s['tid']] += 0.25 if s.get('sit') == 'Penalty' else s['xg']
        XG[str(mid)] = (agg[h], agg[a])
XH = np.array([XG.get(m, (np.nan, np.nan))[0] for m in MIDS]); XA = np.array([XG.get(m, (np.nan, np.nan))[1] for m in MIDS])
# υπεροχη αγορας (Crown κλεισιμο)
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        s = (lo + hi) / 2; d = g['picks'].gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = g['picks'].p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
SM = np.array([msup(*SNAP[m], LH_N[i] + LA_N[i]) if m in SNAP else np.nan for i, m in enumerate(MIDS)])
# ---- πλευρες ----
S = []
for i in range(len(MIDS)):
    for home in (1, 0):
        S.append(dict(i=i, sea=SEA[i], comp=COMP[i], home=home, me=SH[i] if home else SA[i], opp=SA[i] if home else SH[i],
                      y=GH[i] if home else GA[i], x=XH[i] if home else XA[i], lam=LH_N[i] if home else LA_N[i]))
S = pd.DataFrame(S)
print('1. ΜΕΡΟΛΗΨΙΑ ανα πηγη (πραγματικο − μοντελο, ανα ομαδα ανα ματς)')
print(f'   {"πηγη":10s} {"n":>5s} | ΕΠΙΘΕΣΗ: γκολ−λ   xG−λ   | ΑΜΥΝΑ (τι σκοραρει ο αντιπαλος της): γκολ−λ')
for s in ('FotMob', 'Ben', 'γκολ/Elo'):
    a = S[S.me == s]; d = S[S.opp == s]
    print(f'   {s:10s} {len(a):5d} |        {np.mean(a.y - a.lam):+.3f}   {np.nanmean(a.x - a.lam):+.3f} |        {np.mean(d.y - d.lam):+.3f}  (n{len(d)})')
print('\n   ανα ζευγος (σκοπια ομαδας ΕΚΤΟΣ FotMob · FotMob-FotMob σκοπια γηπεδουχου): υπεροχη πραγμ − μοντελο · αγορα − μοντελο · πραγμ − αγορα')
SUPM = LH_N - LA_N
for lab, msk, sgn in (('FotMob vs FotMob', (SH == 'FotMob') & (SA == 'FotMob'), np.ones(len(MIDS))),
                      ('Ben vs FotMob', ((SH == 'Ben') & (SA == 'FotMob')) | ((SA == 'Ben') & (SH == 'FotMob')), np.where(SH == 'Ben', 1, -1)),
                      ('γκολ/Elo vs FotMob', ((SH == 'γκολ/Elo') & (SA == 'FotMob')) | ((SA == 'γκολ/Elo') & (SH == 'FotMob')), np.where(SH == 'γκολ/Elo', 1, -1)),
                      ('μη-FotMob μεταξυ τους', (SH != 'FotMob') & (SA != 'FotMob'), np.ones(len(MIDS)))):
    m = msk & np.isfinite(SM)
    e1 = (GD - SUPM)[m] * sgn[m]; e2 = (SM - SUPM)[m] * sgn[m]; e3 = (GD - SM)[m] * sgn[m]
    rm = np.sqrt(np.mean((GD - SUPM)[m] ** 2)); rk = np.sqrt(np.mean((GD - SM)[m] ** 2))
    print(f'   {lab:22s} n{m.sum():4d} · πραγμ−μοντ {e1.mean():+.2f}±{e1.std() / np.sqrt(m.sum()):.2f} · αγορα−μοντ {e2.mean():+.2f} · πραγμ−αγορα {e3.mean():+.2f}'
          f' · RMSE μοντελο {rm:.3f} vs αγορα {rk:.3f} (κενο {rm - rk:+.3f})')
# ---- 3. διορθωση LOSO ----
def design(D, split_venue):
    cols = {}
    for s in ('Ben', 'γκολ/Elo'):
        if split_venue:
            for hv, hl in ((1, 'εντος'), (0, 'εκτος')):
                cols[f'επιθ {s} {hl}'] = ((D.me == s) & (D.home == hv)).astype(float).values
                cols[f'αμυνα {s} {hl}'] = ((D.opp == s) & (D.home == 1 - hv)).astype(float).values
        else:
            cols[f'επιθ {s}'] = (D.me == s).astype(float).values; cols[f'αμυνα {s}'] = (D.opp == s).astype(float).values
    return np.column_stack(list(cols.values())), list(cols)
def fit(X, y, off, ridge=2.0):
    b = np.zeros(X.shape[1])
    for _ in range(40):
        mu = np.exp(off + X @ b); z = X @ b + (y - mu) / mu; A = X.T @ (mu[:, None] * X) + np.eye(X.shape[1]) * ridge
        bn = np.linalg.solve(A, X.T @ (mu * z))
        if np.max(np.abs(bn - b)) < 1e-8: b = bn; break
        b = bn
    return b, np.sqrt(np.diag(np.linalg.inv(A)))
OFF = np.log(S.lam.values); Y = S.y.values.astype(float); SEAS = ('2223', '2324', '2425', '2526')
INV = ((S.me != 'FotMob') | (S.opp != 'FotMob')).values          # επηρεαζομενες πλευρες
print('\n3. ΔΙΟΡΘΩΣΗ ΠΗΓΗΣ (LOSO) — Δπιθανοφανεια γκολ στις επηρεαζομενες πλευρες (θετικο = καλυτερο)')
for split in (False, True):
    X, names = design(S, split); adj = np.zeros(len(S)); dll = {}
    for te in SEAS:
        tr = (S.sea != te).values; tm = (~tr) & INV
        b, _ = fit(X[tr], Y[tr], OFF[tr]); adj[~tr] = X[~tr] @ b
        mu0 = np.exp(OFF[tm]); mu1 = np.exp(OFF[tm] + adj[tm])
        dll[te] = float(np.sum(Y[tm] * np.log(mu1) - mu1) - np.sum(Y[tm] * np.log(mu0) - mu0))
    # RMSE διαφορας γκολ & μεροληψια μετα
    LH2 = LH_N.copy(); LA2 = LA_N.copy()
    for r, a in zip(S.itertuples(), adj):
        if r.home: LH2[r.i] = LH_N[r.i] * math.exp(a)
        else: LA2[r.i] = LA_N[r.i] * math.exp(a)
    aff = (SH != 'FotMob') | (SA != 'FotMob')
    r0 = np.sqrt(np.mean((GD - (LH_N - LA_N))[aff] ** 2)); r1 = np.sqrt(np.mean((GD - (LH2 - LA2))[aff] ** 2))
    S2 = S.assign(lam2=np.exp(OFF + adj)); bias_after = {s: np.mean((S2.y - S2.lam2)[S2.me == s]) for s in ('Ben', 'γκολ/Elo')}
    c1 = sum(v > 0 for v in dll.values()) >= 3; c2 = r1 < r0; c3 = all(abs(v) < 0.10 for v in bias_after.values())
    bfull, se = fit(X, Y, OFF)
    print(f'   {"χωριστα εντος/εκτος" if split else "ενιαια"}: Δπιθ ' + ' '.join(f'{s}:{v:+.1f}' for s, v in dll.items())
          + f' · RMSE επηρεαζ. ματς {r0:.3f} → {r1:.3f} · μεροληψια επιθεσης μετα: ' + ' / '.join(f'{k} {v:+.3f}' for k, v in bias_after.items())
          + f' → (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} (3){"✓" if c3 else "✗"} {"ΠΕΡΝΑ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑ"}')
    print('      συντελεστες (ολο το δειγμα): ' + ' · '.join(f'{n} ×{math.exp(bb):.2f} (t {bb / s_:+.1f})' for n, bb, s_ in zip(names, bfull, se)))
