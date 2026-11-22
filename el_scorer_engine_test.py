# -*- coding: utf-8 -*-
"""el_scorer_engine_test.py — EUROLEAGUE ΣΥΝΟΛΑ: ΜΗΧΑΝΗ ΠΟΥ «ΚΑΤΑΛΑΒΑΙΝΕΙ» ΤΗΝ ΑΠΟΥΣΙΑ ΣΚΟΡΕΡ 10-20 ΠΟΝΤΩΝ (27/10/2026, Στελιος «δοκιμασε»).
ΑΡΧΗ (Στελιος): η βαση της μηχανης ΔΕΝ αλλαζει· διορθωση ΜΟΝΟ οταν λειπει ΝΕΟΣ (1-3 ματς) παικτης με ≥10 ποντους/ματς, αλλιως 0.
  Μακροχρονιες απουσιες (≥4 ματς) = 0 (ειναι ηδη στη δυναμη της ομαδας). Διορθωνονται ΜΟΝΟ οι ποντοι της ομαδας του αποντα (επιθεση).
ΜΗΧΑΝΕΣ (συντελεστης c εκτιμαται LOSO, ridge 1, πανω στους ποντους ομαδας − μοντελο):
  Α «χαμενοι ποντοι − αντικαταστατης»: Σ [ποντοι/ματς − λεπτα/ματς × ρυθμος παγκου ομαδας] (10 τελευταια ματς του στη σεζον·
     ρυθμος παγκου = ποντοι/λεπτο οσων ΔΕΝ ξεκινησαν, 10 τελευταια ματς ομαδας, μαζεμα 100′ προς τον μεσο λιγκας) · κατω οριο 0.
  Β «επιθεση με/χωρις» (play-by-play, el_pbp_stints): ποντοι ομαδας/100 κατοχες με τον παικτη στο παρκε − χωρις (στα ματς που επαιξε),
     περσινη + φετινη σεζον ΠΡΙΝ το ματς, μαζεμα × n/(n+1500) (ιδιο με on/off τεστ) · × λεπτα/40.
  Ν2-10: το N2 (λεπτα/40 × (ποντοι/40 − μεσος)) μονο για τους ιδιους αποντες (νεοι, ≥10 π/μ).
  Αναφορες: χωρις · live on/off (W4, ιδιος ορισμος γνωσης) · N2 (ολες οι νεες).
ΓΝΩΣΗ ΑΠΟΝΤΩΝ: ΚΥΡΙΟ = ΣΕΛΙΔΑ RotoWire ΣΤΟ ΑΝΟΙΓΜΑ (OUT, οπως το live· ξαναχτισμενη απο el_gtd_model_test) · ΔΕΥΤΕΡΕΥΟΝ = «δεν επαιξε» (box).
ΒΑΣΗ: 1.563 ματς E2021-25 (live μηχανη συνολων), picks συνολων ≥8% ανοιγμα Crown, σ 16.7.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο, στο ΚΥΡΙΟ): μηχανη ΠΕΡΝΑ αν (1) διορθωση = 0 στα ματς χωρις νεο αποντα 10+ (εξ ορισμου, ελεγχεται)
  ΚΑΙ (2) walk-forward μοναδες ≥ live on/off ΚΑΙ (3) placebo < 10% ΚΑΙ (4) μεση διορθωση στα ματς με ≥1 νεο αποντα 10+ ≥ 50% της πραγματικης
  (πραγματικο − μοντελο). Πληροφορια: LOSO μοναδες/θετ. σεζον/CLV, σφαλμα ανα σεζον, bootstrap εβδομαδων, αγορα (ανοιγμα/κινηση), 5 παραδειγματα.
Εξοδος: el_scorer_engine_test_out.txt"""
import os, sys, io, contextlib, collections, pickle, json, bisect, time
import numpy as np, pandas as pd
from statistics import NormalDist
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T00 = time.time()
gsrc = open('el_gtd_model_test.py', encoding='utf-8').read().split('def picksB(adj):')[0]
r_ = "def save(): open(os.path.join(ROOT, 'el_gtd_model_test_out.txt'), 'w', encoding='utf-8').write('\\n'.join(out))"
assert gsrc.count(r_) == 1
G = {'__name__': 'g', '__file__': os.path.join(ROOT, 'el_gtd_model_test.py')}
with contextlib.redirect_stdout(_B()): exec(gsrc.replace(r_, 'def save(): return'), G)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_scorer_engine_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
rows, ys, YT, YH, YA, SE, HELD_B, NAME = G['rowsB'], G['ysB'], G['YT'], G['YH'], G['YAw'], G['SE'], G['HELD_B'], G['NAMEB']
N = len(rows); Phi = NormalDist().cdf
P(f'el_scorer_engine_test · Ευρωλιγκα 2021-25 · ματς {N} · φορτωμα {time.time() - T00:.0f} δευτ.')
# ---- box ανα ομαδα-σεζον ----
PL = json.load(open('el_players.json', encoding='utf-8'))
TGx = collections.defaultdict(list); PP = collections.defaultdict(list); GTS = {}
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    ts = pd.Timestamp(g['utc']).timestamp(); GTS[k] = ts
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        TGx[(g['season'], g[tc])].append((ts, {p[0]: (int(p[2] or 0), float(p[3] or 0), float(p[4] or 0)) for p in g[side] if (p[3] or 0) > 0}))
        for p in g[side]:
            if (p[3] or 0) > 0: PP[p[0]].append((ts, float(p[3]), float(p[4] or 0)))
for v in TGx.values(): v.sort(key=lambda x: x[0])
for v in PP.values(): v.sort()
LG = float(sum(x[2] for v in PP.values() for x in v) / sum(x[1] for v in PP.values() for x in v) * 40)
bm = [(d[1], d[2]) for (s, t), L in TGx.items() if s.startswith('E') for _, gd in L for d in gd.values() if d[0] == 0]
LGB = sum(x[1] for x in bm) / sum(x[0] for x in bm)                       # ποντοι/λεπτο παγκου, λιγκα
def pts40(pid, ts):
    h = [x for x in PP.get(pid, []) if x[0] < ts - 3600][-15:]; m = sum(x[1] for x in h); p = sum(x[2] for x in h)
    return (40 * p + 5 * LG) / (m + 5) if m > 0 else LG
def recent(sea, team, pid, ts):
    prev = [gd for t, gd in TGx.get((sea, team), []) if t < ts - 3600]
    ap = [gd[pid] for gd in prev if pid in gd][-10:]
    bench = [d for gd in prev[-10:] for d in gd.values() if d[0] == 0]
    br = (sum(d[2] for d in bench) + 100 * LGB) / (sum(d[1] for d in bench) + 100)
    if len(ap) < 3: return None
    return dict(ppg=float(np.mean([a[2] for a in ap])), mpg=float(np.mean([a[1] for a in ap])), br=br)
# ---- επιθεση με/χωρις απο play-by-play ----
ST = pickle.load(open('el_pbp_stints.pkl', 'rb'))
ACC = collections.defaultdict(list)                                       # (pid, σεζον) → [(ts, on_pts, on_poss, team_pts, team_poss)]
for k, g in ST.items():
    ts = GTS.get(k)
    if ts is None: continue
    agg = collections.defaultdict(lambda: np.zeros(2)); tot = {'H': np.zeros(2), 'A': np.zeros(2)}; side = {}
    for h5, a5, ph, pa, qh, qa, sec in g['stints']:
        tot['H'] += (ph, qh); tot['A'] += (pa, qa)
        for p in h5: agg[p] += (ph, qh); side[p] = 'H'
        for p in a5: agg[p] += (pa, qa); side[p] = 'A'
    for p, v in agg.items(): ACC[(p, g['season'])].append((ts, v[0], v[1], *tot[side[p]]))
CUM = {}
for key, L in ACC.items():
    L.sort(); a = np.cumsum(np.array([x[1:] for x in L]), axis=0); CUM[key] = ([x[0] for x in L], a)
def onoffO(pid, sea, ts):
    s = np.zeros(4)
    for sk, lim in ((f'E{int(sea[1:]) - 1}', None), (sea, ts - 3600)):
        c = CUM.get((pid, sk))
        if not c: continue
        i = len(c[0]) if lim is None else bisect.bisect_left(c[0], lim)
        if i > 0: s += c[1][i - 1]
    onp, onq, tp_, tq = s; ofp, ofq = tp_ - onp, tq - onq
    if onq < 50 or ofq < 50: return 0.0
    n = 1 / (1 / onq + 1 / ofq); return (100 * onp / onq - 100 * ofp / ofq) * n / (n + 1500)
# ---- αποντες ανα γνωση ----
def absent(p, mode): return (p['pstate'] == 'OUT') if mode == 'page' else (not p['played'])
SDO = None
def feats(r, own, team, mode):
    a = b = n2 = n2all = 0.0; names = []
    for p in own:
        if not absent(p, mode) or p['k'] > 3: continue
        n2all += p['w'] * (pts40(p['pid'], r['ts']) - LG)
        rc = recent(r['y'], team, p['pid'], r['ts'])
        if rc is None or rc['ppg'] < 10: continue
        a += max(rc['ppg'] - rc['mpg'] * rc['br'], 0.0); b += p['w'] * onoffO(p['pid'], r['y'], r['ts']); n2 += p['w'] * (pts40(p['pid'], r['ts']) - LG)
        names.append((NAME.get(p['pid'], p['pid']), rc['ppg'], rc['mpg'], rc['br'] * rc['mpg']))
    return np.array([a, b, n2, n2all]), names
FEAT, NAMES, NIMP = {}, {}, {}
for mode in ('page', 'box'):
    FH, FA, NH, NA = [], [], [], []
    for r in rows:
        x, nm = feats(r, r['CH'], r['hc'], mode); FH.append(x); NH.append(nm)
        x, nm = feats(r, r['CA'], r['ac'], mode); FA.append(x); NA.append(nm)
    FEAT[mode] = (np.array(FH), np.array(FA)); NAMES[mode] = list(zip(NH, NA)); NIMP[mode] = np.array([len(a) + len(b) for a, b in zip(NH, NA)])
P(f'μεσος λιγκας {LG:.1f} π/40′ · παγκος {LGB * 40:.1f} π/40′ · χρονος {time.time() - T00:.0f} δευτ.')
def fit(XH, XA, tr):
    X = np.r_[XH[tr], XA[tr]][:, None] if XH.ndim == 1 else np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + np.eye(X.shape[1]), X.T @ y)
def apply(XH, XA, b, m): return (XH[m][:, None] @ b if XH.ndim == 1 else XH[m] @ b) + (XA[m][:, None] @ b if XA.ndim == 1 else XA[m] @ b)
def loso(XH, XA):
    h = np.zeros(N)
    for s in SE: h[ys == s] = apply(XH, XA, fit(XH, XA, ys != s), ys == s)
    return h
def wf(XH, XA):
    h = np.zeros(N)
    for i, s in enumerate(SE[1:], 1): h[ys == s] = apply(XH, XA, fit(XH, XA, np.isin(ys, SE[:i])), ys == s)
    return h
TOT = np.array([r['hs'] + r['as_'] for r in rows]); T0 = np.array([r['T'] for r in rows])
OPF = np.array([r['op'][1] for r in rows]); CLF = np.array([r['cl'][1] for r in rows]); LIN = np.array([r['op'][2] for r in rows])
OU = np.array([r['op'][4] for r in rows])
def picks(adj):
    sd_, u = np.zeros(N), np.zeros(N)
    for j, r in enumerate(rows):
        T_, oo, ou = r['op'][2], r['op'][3], r['op'][4]; t = r['T'] + adj[j]
        if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7)
        else: po = 1 - Phi((T_ - t) / 16.7); pu = 1 - po
        pp = 1 - po - pu; eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        s, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e < .08: continue
        x = (TOT[j] - T_) * s; sd_[j] = s; u[j] = (od - 1) if x > 0 else (0 if x == 0 else -1)
    return sd_, u
day = pd.to_datetime([pd.Timestamp(r['op'][0], unit='s') for r in rows]).normalize(); wk = ((day - day.min()).days // 7).values
rm = lambda e, m: float(np.sqrt(np.mean(e[m] ** 2)))
rng = np.random.default_rng(11); WF4 = np.isin(ys, SE[1:])
ENG = {'Α χαμενοι−αντικαταστατης': 0, 'Β επιθεση με/χωρις': 1, 'Ν2-10': 2}
xu = LIN - TOT; BU = np.where(xu > 0, OU - 1, np.where(xu == 0, 0.0, -1.0))
VERD = {}
for mode, lab, live_key in (('page', 'ΚΥΡΙΟ — ΣΕΛΙΔΑ RotoWire ΣΤΟ ΑΝΟΙΓΜΑ (OUT)', ('N', 'G0')), ('box', 'ΔΕΥΤΕΡΕΥΟΝ — «ΔΕΝ ΕΠΑΙΞΕ» (box, εκ των υστερων)', ('ref', None))):
    FH, FA = FEAT[mode]; ni = NIMP[mode]
    P(f'\n################ {lab} ################')
    P(f'  ματς με ≥1 νεο αποντα 10+ π/μ: {int((ni >= 1).sum())} (1: {int((ni == 1).sum())} · 2+: {int((ni >= 2).sum())}) · χωρις: {int((ni == 0).sum())}')
    H = {'χωρις': np.zeros(N), 'live on/off': HELD_B[live_key]}; W = {'χωρις': np.zeros(N)}
    # live on/off walk-forward: ιδια χαρακτηριστικα W4 με τον ιδιο ορισμο γνωσης
    F4 = [G['featB'](r, *live_key) for r in rows]; X4H = np.array([f[0] for f in F4]); X4A = np.array([f[1] for f in F4])
    assert np.allclose(loso(X4H, X4A), H['live on/off']), 'W4 LOSO ≠ HELD_B'
    W['live on/off'] = wf(X4H, X4A)
    H['N2 (ολες οι νεες)'] = loso(FH[:, 3], FA[:, 3]); W['N2 (ολες οι νεες)'] = wf(FH[:, 3], FA[:, 3])
    COEF = {}
    for nm, j in ENG.items():
        H[nm] = loso(FH[:, j], FA[:, j]); W[nm] = wf(FH[:, j], FA[:, j]); COEF[nm] = (fit(FH[:, j], FA[:, j], ys != '')[0], [fit(FH[:, j], FA[:, j], ys == s)[0] for s in SE])
    P('  συντελεστες (ολα τα ματς · ανα σεζον): ' + ' │ '.join(f"{nm} {c:+.3f} ({' '.join(f'{x:+.2f}' for x in per)})" for nm, (c, per) in COEF.items()))
    PK = {k: picks(h) for k, h in H.items()}; uR = PK['live on/off'][1]
    P(f'\n  ## LOSO 2021-25 + WALK-FORWARD 2022-25')
    P(f'  {"μηχανη":26s} | σφαλμα | καλυτερο απο «χωρις» | picks | μοναδες | θετ | ανα σεζον                          | CLV    | WF μοναδες | WF σφαλμα')
    R = {}
    for k, h in H.items():
        sd, u = PK[k]; ps = pd.Series(u[sd != 0]).groupby(ys[sd != 0]).sum(); clv = np.nanmean(np.where(sd != 0, sd * (CLF - OPF), np.nan))
        sw, uw = picks(W[k]); d0 = sum(rm(YT - h, ys == s) < rm(YT, ys == s) - 1e-12 for s in SE)
        R[k] = dict(u=u.sum(), wf=uw[WF4].sum())
        P(f'  {k:26s} | {rm(YT - h, ys != ""):.3f} | {d0}/5 σεζον            | {int((sd != 0).sum()):5d} | {u.sum():+7.1f} | {int((ps > 0).sum())}/5 | '
          + ' '.join(f'{s[-2:]}:{ps.get(s, 0):+5.1f}' for s in SE) + f' | {clv:+.3f} | {uw[WF4].sum():+8.1f}   | {rm(YT - W[k], WF4):.3f}')
    P(f'\n  ## ΜΗΔΕΝ ΣΤΑ «ΚΑΝΟΝΙΚΑ» ΜΑΤΣ (χωρις νεο αποντα 10+): max |διορθωση| ' + ' · '.join(f'{nm} {np.max(np.abs(H[nm][ni == 0])):.3f}' for nm in ENG))
    P(f'\n  ## ΑΝΑ ΟΜΑΔΑ ΜΑΤΣ: πραγματικο − μοντελο · μεση διορθωση · μοναδες picks (LOSO) · τυφλο Under ανοιγμα · αγορα')
    for gl, m in (('0 νεοι αποντες 10+', ni == 0), ('1 νεος αποντας 10+', ni == 1), ('2+ νεοι αποντες 10+', ni >= 2), ('≥1', ni >= 1)):
        P(f'  {gl:20s} ({int(m.sum()):4d}) πραγμ − μοντελο {np.mean(TOT[m] - T0[m]):+5.2f} · πραγμ − ανοιγμα {np.mean(TOT[m] - LIN[m]):+5.2f} · '
          f'ανοιγμα − μοντελο {np.mean(LIN[m] - T0[m]):+5.2f} · κινηση ανοιγμα→κλεισιμο {np.mean(CLF[m] - OPF[m]):+5.2f} · τυφλο Under {100 * BU[m].mean():+5.1f}%')
        P(f'  {"":20s} ' + ' │ '.join(f'{k} {np.mean(H[k][m]):+5.2f} / {PK[k][1][m].sum():+5.1f}μ ({int((m & (PK[k][0] != 0)).sum())})' for k in H))
    P(f'\n  ## BOOTSTRAP εβδομαδων (2000) & PLACEBO (αποντες ανακατεμενοι μεταξυ ματς ιδιας σεζον, 200)')
    W_ = np.unique(wk)
    for nm, j in ENG.items():
        dw = pd.Series(PK[nm][1] - uR).groupby(wk).sum().reindex(W_, fill_value=0).values
        bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(2000)])
        a, b = FH[:, j], FA[:, j]; real = R[nm]['u']; vals = []
        for _ in range(200):
            pa, pb = a.copy(), b.copy()
            for s in SE:
                idx = np.where(ys == s)[0]; pm = rng.permutation(idx); pa[idx] = a[pm]; pb[idx] = b[pm]
            vals.append(picks(loso(pa, pb))[1].sum())
        plc = float(np.mean(np.array(vals) >= real)); R[nm]['plc'] = plc; R[nm]['boot'] = float((bs > 0).mean())
        P(f'  {nm:26s} Δμοναδες vs live {dw.sum():+6.1f} · P(> live) {100 * (bs > 0).mean():.0f}% · placebo μεσος {np.mean(vals):+.1f} (95% {np.percentile(vals, 95):+.1f}) · P {100 * plc:.1f}%')
    P(f'\n  ## ΚΡΙΣΗ (προ-δηλωμενη){" — ΚΥΡΙΟ" if mode == "page" else " — δευτερευον, πληροφορια"}')
    m1 = ni >= 1; gap = np.mean(TOT[m1] - T0[m1])
    for nm in ENG:
        t = {'0 στα κανονικα': np.max(np.abs(H[nm][ni == 0])) < 1e-9, 'WF ≥ live': R[nm]['wf'] >= R['live on/off']['wf'], 'placebo < 10%': R[nm]['plc'] < .10,
             'διορθωση ≥ 50% πραγματικης': np.mean(H[nm][m1]) <= 0.5 * gap if gap < 0 else False}
        VERD[(mode, nm)] = all(t.values())
        P(f'  {nm:26s} ' + ' · '.join(f"{k} {'✓' if v else '✗'}" for k, v in t.items()) + f" (διορθ. {np.mean(H[nm][m1]):+.2f} vs πραγμ. {gap:+.2f}) → {'ΠΕΡΝΑ' if all(t.values()) else 'δεν περνα'}")
    if mode == 'page':
        P('\n  ## ΕΛΕΓΧΟΣ: 6 ματς με τη μεγαλυτερη διορθωση Α (σελιδα)')
        for j in np.argsort(H['Α χαμενοι−αντικαταστατης'])[:6]:
            r = rows[j]; nh, na = NAMES[mode][j]
            P(f'    {r["y"]} {pd.Timestamp(r["ts"], unit="s"):%d/%m/%Y} {r["hc"]}-{r["ac"]} · γραμμη {LIN[j]:.1f} · μοντελο {T0[j]:.1f} · Α {H["Α χαμενοι−αντικαταστατης"][j]:+.1f} · Β {H["Β επιθεση με/χωρις"][j]:+.1f} · '
              f'N2-10 {H["Ν2-10"][j]:+.1f} · on/off {H["live on/off"][j]:+.1f} · πραγματικο {TOT[j]:.0f} · ' + '; '.join(f'{n} {p:.1f}π/{mn:.0f}′ (παγκος {b:.1f})' for n, p, mn, b in nh + na))
    save()
P(f'\nχρονος {time.time() - T00:.0f} δευτ.'); save()
