# -*- coding: utf-8 -*-
"""dom_bk_engine_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 1: ΒΑΣΗ ΜΗΧΑΝΗΣ ανα πρωταθλημα (5/10/2026, Στελιος: «καθε μηχανισμος
στα εγχωρια πρεπει να μπει σε τεστ — βαρη, αγωνιστικες, οτιδηποτε»).
Σημερινη μηχανη (dom_bk_screen, απο Ευρωλιγκα): περσι 0.7 · τραβηγμα λ 8 · χωρις μνημη (HL ∞) · τυχη 50% · εδρα ΜΙΑ ανα πρωταθλημα.
ΣΤΑΔΙΟ Α: περσι {0, .2, .35, .5, .7, .85} × λ {2, 4, 8, 12, 16} × μνημη HL {30, 60, 120, ∞ μερες}  (τυχη .5, εδρα πρωταθληματος)
ΣΤΑΔΙΟ Β: τυχη {ωμο, .5, .25} × εδρα {πρωταθληματος, + ανα ομαδα (ridge 20 ματς)} πανω στις 3 καλυτερες του Α + τη σημερινη.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ΧΩΡΙΣΤΑ ανα πρωταθλημα: LOSO στις 2021-22…2025-26 (επιλογη με RMSE διαφορας ΟΛΩΝ των ματς των
  αλλων 4 σεζον) → ΑΛΛΑΓΗ αν καλυτερο απο τη σημερινη σε ≥4/5 σεζον. Αναφορα: αγων 1-10 · Κ2 vs κλεισιμο (Crown/Bet365) · ROI.
Χρηση: python dom_bk_engine_test.py ACB LBA [--time]   Εξοδος: dom_bk_engine_test_out.txt"""
import sys, json, math, io, contextlib, itertools, time, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']
src = open('dom_bk_screen.py', encoding='utf-8').read().split("LAM, CARRY, HW = 8.0, 0.7, 50.0")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace("if y not in YRS or lg not in L6 + EU: continue", "if y not in YRS or lg not in LG_: continue")
NS = {'LG_': ARGS}
with contextlib.redirect_stdout(io.StringIO()):
    exec(src, NS)
G, effs, YRS, NAME = NS['G'], NS['effs'], NS['YRS'], NS['NAME']
act = (G.hs - G.as_).values.astype(float)
EFF = {w: effs(w) for w in (None, .5, .25)}
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
HW, MUW, LH = 50.0, 5.0, 20.0
def fit(hi, ai, eh, ea, ww, n, o0, d0, h0, mu0, lam, team_home):
    m = len(hi); nc = 2 + 2 * n + (n if team_home else 0)
    A = np.zeros((2 * m + 2 * n + 2 + (n if team_home else 0), nc)); y = np.zeros(A.shape[0]); r0 = np.arange(m); sw = np.sqrt(ww)
    A[r0, 0] = sw; A[r0, 1] = .5 * sw; A[r0, 2 + hi] = sw; A[r0, 2 + n + ai] = sw; y[r0] = sw * eh
    A[m + r0, 0] = sw; A[m + r0, 1] = -.5 * sw; A[m + r0, 2 + ai] = sw; A[m + r0, 2 + n + hi] = sw; y[m + r0] = sw * ea
    if team_home:
        A[r0, 2 + 2 * n + hi] = .5 * sw; A[m + r0, 2 + 2 * n + hi] = -.5 * sw
    sl = math.sqrt(lam); k = np.arange(n); b = 2 * m
    A[b + k, 2 + k] = sl; y[b + k] = sl * o0; A[b + n + k, 2 + n + k] = sl; y[b + n + k] = sl * d0
    A[b + 2 * n, 1] = math.sqrt(HW); y[b + 2 * n] = math.sqrt(HW) * h0
    A[b + 2 * n + 1, 0] = math.sqrt(MUW); y[b + 2 * n + 1] = math.sqrt(MUW) * mu0
    if team_home:
        A[b + 2 * n + 2 + k, 2 + 2 * n + k] = math.sqrt(LH)
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1], x[2:2 + n], x[2 + n:2 + 2 * n], (x[2 + 2 * n:] if team_home else np.zeros(n))
def run(lg, carry, lam, HL, w, team_home):
    EH, EA, PC = EFF[w]
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]]))
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        o0 = np.array([carry * prior.get(t, (0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0))[1] for t in teams])
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, h, O, D, Hh = fit(hi[past], ai[past], eh[past], ea[past], ww, n, o0, d0, h0, mu0, lam, team_home); pace = float(np.mean(pc[past][-200:]))
            else:
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), float(np.mean(PC[idx_all]))
            for j in cur:
                pred[sidx[j]] = pace * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
    return pred, gn
EV = [2021, 2022, 2023, 2024, 2025]
def rm(v, lg, ys, msk=None):
    m = (G.lg.values == lg) & np.isin(G.y.values, ys) & np.isfinite(v) & (msk if msk is not None else True)
    return float(np.sqrt(np.mean((act - v)[m] ** 2)))
LIVE = (.7, 8, 9999, .5, False)
if '--time' in sys.argv:
    t0 = time.time(); run(ARGS[0], *LIVE); print(f'1 run {ARGS[0]}: {time.time() - t0:.1f}s'); sys.exit()
# ---- αγορα (για αναφορα) ----
N = NormalDist(); Phi = N.cdf
D_ = json.load(open('bk_domestic.json', encoding='utf-8'))
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_dom/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 21: ROWS[r['ngid']][r['cid']] = r['rows']
idx = collections.defaultdict(list)
for i in range(len(G)): idx[(G.lg.values[i], int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
def conv(rows):
    R = sorted([x for x in rows if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    return ((-R[0][1], 1 + R[0][2], 1 + R[0][3]), (-R[-1][1], 1 + R[-1][2], 1 + R[-1][3])) if R else None
def mu_of(L, o1, o2, s=12.2):
    ph = (1 / o1) / (1 / o1 + 1 / o2); return -L + s * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
MK = {}
for key, v in D_.items():
    lg, sea = key.split('_')
    if lg not in ARGS: continue
    for g in v['games']:
        ng = int(g[0])
        if ng not in ROWS: continue
        try: hs, as_ = int(g[4]), int(g[5])
        except Exception: continue
        dd = pd.Timestamp(g[1]).normalize()
        hit = next((i for i in idx.get((lg, hs, as_), []) if abs((G.t.values[i] - dd) / np.timedelta64(1, 'D')) <= 1.5), None)
        if hit is None: continue
        od = {c: conv(ROWS[ng].get(c, [])) for c in (3, 8)}; od = {c: x for c, x in od.items() if x}
        if od: MK[hit] = dict(mo=float(np.mean([mu_of(*x[0]) for x in od.values()])), mc=float(np.mean([mu_of(*x[1]) for x in od.values()])),
                              op=(od.get(3) or od.get(8))[0], cl=(od.get(3) or od.get(8))[1])
def market_report(v, lg, lab):
    ii = [i for i in MK if G.lg.values[i] == lg and G.y.values[i] in EV and np.isfinite(v[i])]
    x = np.array([v[i] - MK[i]['mc'] for i in ii]); z = np.array([act[i] - MK[i]['mc'] for i in ii]); yy = np.array([G.y.values[i] for i in ii])
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    pos = sum(np.polyfit(x[yy == y], z[yy == y], 1)[0] > 0 for y in EV)
    cells = []
    for when in ('op', 'cl'):
        R = []
        for i in ii:
            L, o1, o2 = MK[i][when]; mm = MK[i]['mo' if when == 'op' else 'mc']; m_ = mm + .5 * (v[i] - mm)
            if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / 12.3); pl = Phi((-m_ - L - .5) / 12.3)
            else: pw = Phi((m_ + L) / 12.3); pl = 1 - pw
            pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e >= .06:
                vv = (act[i] + L) * side; R.append(((od_ - 1) if vv > 0 else (0 if vv == 0 else -1), G.y.values[i]))
        a = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R)); p_ = sum(1 for y in ys if np.mean([q[0] for q in R if q[1] == y]) > 0)
        cells.append(f'{"ανοιγμα" if when == "op" else "κλεισιμο"} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {p_}/{len(ys)})')
    P(f'    {lab:24s} Κ2 b {b:+.3f} (t {b/se:+.1f}, θετ. {pos}/5) · ROI μιξη 50/50 ≥6%: ' + ' · '.join(cells))
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} ############')
    t0 = time.time(); PRED = {}
    CAR = (0, .2, .35, .5, .7, .85, 1.0) if '--ext' in sys.argv else (0, .2, .35, .5, .7, .85)   # --ext: ΕΠΕΚΤΑΣΗ μετα το 1ο αποτελεσμα (το .85 ηταν στο ακρο)
    GA = list(itertools.product(CAR, (2, 4, 8, 12, 16), (30, 60, 120, 9999)))
    for i, (c, l, hl) in enumerate(GA):
        PRED[(c, l, hl, .5, False)] = run(lg, c, l, hl, .5, False)
        if i % 20 == 0: print(f'  A {i + 1}/{len(GA)} ({time.time() - t0:.0f}s)', flush=True)
    top3 = sorted(PRED, key=lambda g: rm(PRED[g][0], lg, EV))[:3]
    P('=== ΣΤΑΔΙΟ Α (τυχη .5, εδρα πρωταθληματος) · IN-SAMPLE RMSE 2021-26 · καλυτερα 8 ===')
    for g in sorted(PRED, key=lambda g: rm(PRED[g][0], lg, EV))[:8]:
        P(f'  περσι {g[0]} · λ {g[1]} · HL {g[2]}: {rm(PRED[g][0], lg, EV):.3f} (αγων 1-10 {rm(PRED[g][0], lg, EV, PRED[g][1] <= 10):.3f})')
    P(f'  σημερινη {LIVE[:3]}: {rm(PRED[LIVE][0], lg, EV):.3f}')
    for nm, k_, vals in (('περσι', 0, (0, .2, .35, .5, .7, .85, 1.0)), ('λ', 1, (2, 4, 8, 12, 16)), ('HL', 2, (30, 60, 120, 9999))):
        P(f'  προφιλ {nm}: ' + ' · '.join(f'{v}: {min(rm(PRED[g][0], lg, EV) for g in PRED if g[k_] == v):.3f}' for v in vals if any(g[k_] == v for g in PRED)))
    for eng in top3 + [LIVE]:
        for w, th in itertools.product((None, .5, .25), (False, True)):
            g = eng[:3] + (w, th)
            if g not in PRED: PRED[g] = run(lg, *g)
    P('=== ΣΤΑΔΙΟ Β (τυχη × εδρα ανα ομαδα) · καλυτερα 8 ===')
    for g in sorted(PRED, key=lambda g: rm(PRED[g][0], lg, EV))[:8]:
        P(f'  {g}: {rm(PRED[g][0], lg, EV):.3f}')
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; g = min(PRED, key=lambda g: rm(PRED[g][0], lg, tr)); ch.append(g)
        m = (G.lg.values == lg) & (G.y.values == Y); held[m] = PRED[g][0][m]
    base, gn = PRED[LIVE]
    d = [rm(held, lg, [Y]) - rm(base, lg, [Y]) for Y in EV]; d10 = [rm(held, lg, [Y], gn <= 10) - rm(base, lg, [Y], gn <= 10) for Y in EV]
    P('=== LOSO ===')
    for Y, g in zip(EV, ch): P(f'  {Y}-{(Y + 1) % 100:02d}: περσι {g[0]} · λ {g[1]} · HL {g[2]} · τυχη {g[3]} · εδρα ομαδας {g[4]}')
    P(f'  ΟΛΑ: σημερινη {rm(base, lg, EV):.3f} → {rm(held, lg, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5'
      + ('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
    P(f'  ΑΓΩΝ 1-10: {rm(base, lg, EV, gn <= 10):.3f} → {rm(held, lg, EV, gn <= 10):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d10) + f' → {sum(x < 0 for x in d10)}/5')
    market_report(base, lg, 'σημερινη')
    market_report(held, lg, 'LOSO νεα')
    P(f'  (χρονος {time.time() - t0:.0f}s)')
open('dom_bk_engine_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
