# -*- coding: utf-8 -*-
"""el_regular_rule_test.py — EUROLEAGUE ΑΠΟΥΣΙΕΣ: ΚΑΝΟΝΑΣ «ΤΑΚΤΙΚΟΣ» (22/10/2026).
Ερωτημα: ο live team_cost (el_absence.py) μετραει απωντα μονο αν επαιξε σε ≥3 απο τα 10 τελευταια ΦΕΤΙΝΑ ματς της ομαδας, και 0 αν δεν
επαιξε καθολου φετος. Αρχη σεζον / μετα απο μακρυ τραυματισμο ενας σταρ μπορει να μετραει 0.
ΣΤΗΣΙΜΟ = ΑΚΡΙΒΩΣ el_absence_v2_test (εκδοχη V1 = λεπτα + PIR): ιδια ματς E2021-25 (κανονικη περιοδος, ≥2 φετινα ματς και οι δυο ομαδες),
  live προβλεψεις el_newmodel_preds, αγορα = ανοιγμα Crown (el_line_timing), αποντες απο τα box scores (πληρης γνωση), picks χαντικαπ ≥8%, σ 11.5.
  Κοστος παικτη = (β0 + β1·z)·λεπτα/40·g(k), z = (PIR/40 − MU)/SD, PIR/40 = ΣPIR/(Σλεπτα+200)·40 στα τελευταια 60 ματς EL,
  λεπτα = μ.ο. 10 τελευταιων ματς EL που επαιξε (περσινα+φετινα), ≥10′, g(k): k 1-3 ×1 · 4-10 ×0.5 · 11+ ×0, k = συνεχομενα ΦΕΤΙΝΑ ματς
  της ομαδας που λειπει (μαζι με το σημερινο). ΑΛΛΑΖΕΙ ΜΟΝΟ ο κανονας «τακτικος»:
 R0 = live: ≥3 απο τα 10 τελευταια φετινα ματς της ομαδας (οποιος δεν επαιξε φετος → 0).
 R1 = αν η ομαδα εχει <10 φετινα ματς: ≥3 απο τα 10 τελευταια ματς της ομαδας ΠΕΡΣΙΝΑ+ΦΕΤΙΝΑ μαζι (ιδια ομαδα)· πρεπει να εχει παιξει φετος.
 R2 = φετος ≥3/10 Ή περσινος μ.ο. λεπτων ≥15′ (σε οποιαδηποτε ομαδα EL)· πρεπει να εχει παιξει φετος για την ομαδα.
 R3 = R2 + και οσοι ΔΕΝ εχουν παιξει φετος (περσινος μ.ο. ≥15′, λεπτα/PIR απο τα περσινα, k = φετινα ματς ομαδας + 1).
      Ρόστερ στο backtest: ο παικτης εμφανιζεται ΑΡΓΟΤΕΡΑ φετος με την ομαδα (live αυτο το δινει η RotoWire OUT) και δεν εχει παιξει
      φετος για αλλη ομαδα (EL/EuroCup) πριν την πρωτη του εμφανιση εδω (μεταγραφες μεσα στη σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο, ιδια με el_absence_v2_test), LOSO E2021-25 ανα σεζον:
  μια εκδοχη ΠΕΡΝΑ αν: RMSE καλυτερο απο R0 σε ≥4/5 σεζον ΚΑΙ μοναδες picks χαντικαπ ≥8% (ανοιγμα) ≥ R0 ΚΑΙ θετικες σεζον ≥4/5.
  Κυριο = β0/β1 ξαναεκτιμωνται LOSO ανα εκδοχη (οπως το v2). Δευτερευον (περιγραφικο) = σταθεροι live συντελεστες 0.56 / 1.06.
  ΕΛΕΓΧΟΣ: η R0 πρεπει να αναπαραγει V1 του v2 (picks ≥8% +10.5%, 626, +65.8μ, 5/5).
  Περιγραφικα: ποσες απουσιες αλλαζουν ανα εκδοχη · τα ιδια μονο για αγωνιστικες 1-10 · επεκταση με αγωνιστικες 1-2 (εκτος του v2).
Εξοδος: el_regular_rule_test_out.txt"""
import sys, io, contextlib, collections, json
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_v2_test.py', encoding='utf-8').read().split("P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
rows, keys, TG, PH, NAME, value, MU, SD, SE, D, REC, NP = (ns[k] for k in ('rows', 'keys', 'TG', 'PH', 'NAME', 'value', 'MU', 'SD', 'SE', 'D', 'REC', 'NP'))
pd = ns['pd']; PL = ns['ns']['PL']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
VERS = ['R0', 'R1', 'R2', 'R3']
B_LIVE = np.array([0.56, 1.06])
def psea(s): return f'E{int(s[1:]) - 1}'
# ---- περσινος μ.ο. λεπτων (οποιαδηποτε ομαδα EL) ----
SMIN = collections.defaultdict(list)                     # (σεζον, pid) → [λεπτα]
for (sea, team), L in TG.items():
    for ts, k, d in L:
        for pid, v in d.items():
            if v[0] > 0: SMIN[(sea, pid)].append(v[0])
def prev_avg(sea, pid):
    m = SMIN.get((psea(sea), pid)); return (float(np.mean(m)), len(m)) if m else (None, 0)
# ---- ρόστερ: εμφανισεις φετος ανα ομαδα + εμφανισεις σε αλλες ομαδες (EL + EuroCup ιδιου ετους) ----
APPS = collections.defaultdict(list)                     # (ετος, pid) → [(ts, ομαδα)]
for k, g in PL.items():
    if g.get('comp') not in ('E', 'U') or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp(); yr = g['season'][1:]
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        for p in g[side]:
            if (p[3] or 0) > 0: APPS[(yr, p[0])].append((ts, g[tc], g['comp']))
ROST = {key: {p for _, _, d in L for p, v in d.items() if v[0] > 0} for key, L in TG.items()}   # ολοι οσοι επαιξαν φετος με την ομαδα
def roster_later(sea, team, pid, ts):
    """δεν εχει παιξει φετος για την ομαδα πριν το ts· παιζει ΑΡΓΟΤΕΡΑ μαζι της· και δεν επαιξε για αλλη ομαδα πριν την πρωτη του εμφανιση εδω"""
    A = APPS.get((sea[1:], pid), [])
    mine = [t for t, tm, c in A if tm == team and c == 'E']
    if not mine or min(mine) < ts - 3600: return False
    first = min(mine)
    return not any(tm != team and t < first for t, tm, c in A)
def absents_v(sea, team, ts, rule, allow_short=False):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None or (len(prev) < 2 and not allow_short): return None
    last10 = prev[-10:]; cnt = collections.Counter(p for _, _, d in last10 for p, v in d.items() if v[0] > 0)
    played = {p for _, _, d in prev for p, v in d.items() if v[0] > 0}
    cand = {}
    for pid, c in cnt.items():
        if c >= 3: cand[pid] = 'R0'
    if rule == 'R1' and len(prev) < 10:
        comb = TG.get((psea(sea), team), []) + prev
        cc = collections.Counter(p for _, _, d in comb[-10:] for p, v in d.items() if v[0] > 0)
        for pid, c in cc.items():
            if c >= 3 and pid in played and pid not in cand: cand[pid] = 'R1'
    if rule in ('R2', 'R3'):
        for pid in played:
            if pid not in cand and (prev_avg(sea, pid)[0] or 0) >= 15: cand[pid] = 'R2'
    if rule == 'R3':
        for pid in ROST.get((sea, team), ()):
            if pid in cand or pid in played: continue
            if (prev_avg(sea, pid)[0] or 0) >= 15 and roster_later(sea, team, pid, ts): cand[pid] = 'R3'
    res = []
    for pid, tag in cand.items():
        if today.get(pid, (0,))[0] > 0: continue
        k = 0
        for _, _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = value(pid, ts)
        if v is None or v['min'] < 10: continue
        res.append(dict(pid=pid, k=k + 1, tag=tag, nseason=len(prev), napp=cnt.get(pid, 0), **v))
    return res
# ---- κατασκευη: κυρια ματς (ιδια με v2) ----
def build(sea, hc, ac, ts, allow_short):
    A = {}
    for R in VERS:
        ah, aa = absents_v(sea, hc, ts, R, allow_short), absents_v(sea, ac, ts, R, allow_short)
        if ah is None or aa is None: return None
        A[R] = (ah, aa)
    return A
for r, (sea, hc, ac, ts) in zip(rows, keys):
    r['A'] = build(sea, hc, ac, ts, False)
    r['md'] = max(sum(1 for x in TG[(sea, hc)] if x[0] < ts - 3600), sum(1 for x in TG[(sea, ac)] if x[0] < ts - 3600)) + 1
    r['team'] = (hc, ac); r['sea'] = sea; r['ts'] = ts
    # ελεγχος: R0 == v2 αποντες
    a0 = sorted((p['pid'], p['k']) for p in r['A']['R0'][0]); b0 = sorted((p['pid'], p['k']) for p in r['ah'])
    assert a0 == b0, ('R0 ≠ v2', sea, hc, ts)
P(f'κυρια ματς (ιδια με v2): {len(rows)} · ελεγχος R0 = αποντες v2: OK')
# ---- επεκταση: αγωνιστικες 1-2 (μια τουλαχιστον ομαδα με <2 φετινα) ----
in_main = {(s, h, a, t) for s, h, a, t in keys}
ext = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    ts = t.timestamp()
    if (sea, hc, ac, ts) in in_main: continue
    A = build(sea, hc, ac, ts, True)
    if A is None: continue
    md = max(sum(1 for x in TG[(sea, hc)] if x[0] < ts - 3600), sum(1 for x in TG[(sea, ac)] if x[0] < ts - 3600)) + 1
    ext.append(dict(y=sea, act=float(D.hs.values[pos] - D.as_.values[pos]), m=float(NP[key]['h_new']), op=d_['open'][2:], A=A, md=md, team=(hc, ac), sea=sea, ts=ts))
P(f'επιπλεον ματς αγωνιστικων 1-2 (εκτος v2): {len(ext)}')
# ---- χαρακτηριστικα ----
def gk(k): return 1.0 if k <= 3 else (.5 if k <= 10 else 0.0)
def feats(r, R):
    x = np.zeros(2); ah, aa = r['A'][R]
    for lst, s in ((aa, 1), (ah, -1)):
        for p in lst:
            w = p['min'] / 40 * gk(p['k']) * s; x[0] += w; x[1] += w * (p['pir'] - MU['pir']) / SD['pir']
    return x
from statistics import NormalDist
Phi = NormalDist().cdf
def picks(RW, adj, msk=None):
    U = collections.defaultdict(list)
    for i, (r, a) in enumerate(zip(RW, adj)):
        if msk is not None and not msk[i]: continue
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08: x = (r['act'] + L) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1))
    return U
def tot(U): return sum(x for v in U.values() for x in v)
def npos(U): return sum(1 for s in SE if U[s] and sum(U[s]) > 0)
def cell(U):
    u = [x for v in U.values() for x in v]
    if not u: return 'κανενα pick'
    return (f"ROI {np.mean(u) * 100:+5.1f}% · picks {len(u)} · μοναδες {sum(u):+6.1f}μ · θετικες σεζον {npos(U)}/5 · ανα σεζον "
            + ' '.join(f"{s[-2:]}:{sum(U[s]):+.1f}" for s in SE))
rmse = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2))) if m.any() else float('nan')
def run(RW, label, md_mask_fn=None):
    Y = np.array([r['act'] - r['m'] for r in RW]); ys = np.array([r['y'] for r in RW]); md = np.array([r['md'] for r in RW])
    XF = {R: np.array([feats(r, R) for r in RW]) for R in VERS}
    HELD, FIX, BF = {}, {}, {}
    for R in VERS:
        X = XF[R]; h = np.zeros(len(Y))
        for s in SE:
            m = ys != s; b = np.linalg.solve(X[m].T @ X[m] + np.eye(2), X[m].T @ Y[m]); h[ys == s] = (X @ b)[ys == s]
        HELD[R] = h; FIX[R] = X @ B_LIVE
        BF[R] = np.linalg.solve(X.T @ X + np.eye(2), X.T @ Y)
    return Y, ys, md, XF, HELD, FIX, BF
def report(RW, Y, ys, HELD, base_key, msk, title, crit=True):
    P(f'  {title}')
    U0 = picks(RW, HELD['R0'], msk)
    for R in VERS:
        h = HELD[R]
        d = [rmse(Y - h, (ys == s) & msk) - rmse(Y - HELD['R0'], (ys == s) & msk) for s in SE]
        U = picks(RW, h, msk); nb = sum(1 for x in d if x < 0)
        ok = R != 'R0' and nb >= 4 and tot(U) >= tot(U0) and npos(U) >= 4
        verdict = '' if R == 'R0' or not crit else ('  → ΠΕΡΝΑ' if ok else '  ✗ (δεν περνα)')
        P(f'    {R}: ΔRMSE vs R0 ανα σεζον {" ".join(f"{x:+.3f}" for x in d)} (καλυτερο σε {nb}/5) | {cell(U)}{verdict}')
    P(f'    (χωρις καμια διορθωση απουσιων: {cell(picks(RW, np.zeros(len(RW)), msk))})')
# ================= ΚΥΡΙΟ =================
Y, ys, md, XF, HELD, FIX, BF = run(rows, 'κυριο')
ALL = np.ones(len(Y), bool); M10 = md <= 10
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ (ολα τα δεδομενα, ridge 1 οπως v2): β0 = ποντοι ανα 40′ απουσιας παικτη μεσου PIR · β1 = επιπλεον ανα 1 τυπ. αποκλιση PIR/40')
for R in VERS: P(f'  {R}: β0 {BF[R][0]:+.2f} · β1 {BF[R][1]:+.2f}')
P(f'  (MU PIR/40 {MU["pir"]:.2f} · SD {SD["pir"]:.2f})')
P(''); P('## Α. ΚΥΡΙΟ — LOSO επανεκτιμηση β ανα εκδοχη (στησιμο v2), picks χαντικαπ ≥8% στο ανοιγμα Crown')
report(rows, Y, ys, HELD, 'R0', ALL, f'ολα τα ματς ({len(rows)})')
P(''); P('## Β. ΔΕΥΤΕΡΕΥΟΝ — σταθεροι live συντελεστες (0.56 + 1.06·z), χωρις επανεκτιμηση (ιδια κριτηρια, περιγραφικα)')
report(rows, Y, ys, FIX, 'R0', ALL, f'ολα τα ματς ({len(rows)})')
P(''); P('## Γ. ΜΟΝΟ ΑΓΩΝΙΣΤΙΚΕΣ 3-10 των κυριων ματς (LOSO β απο ολα τα ματς· περιγραφικο)')
report(rows, Y, ys, HELD, 'R0', M10, f'αγωνιστικες ≤10 ({int(M10.sum())} ματς) — LOSO', crit=False)
report(rows, Y, ys, FIX, 'R0', M10, f'αγωνιστικες ≤10 ({int(M10.sum())} ματς) — σταθεροι live', crit=False)
report(rows, Y, ys, HELD, 'R0', ~M10, f'αγωνιστικες 11+ ({int((~M10).sum())} ματς) — LOSO', crit=False)
# ---- ποσες απουσιες αλλαζουν ----
P(''); P('## Δ. ΠΟΣΕΣ ΑΠΟΥΣΙΕΣ ΑΛΛΑΖΟΥΝ (κυρια ματς· «μετρουν» = g(k) > 0, δηλ. k ≤ 10)')
def cnts(RW, R, msk=None):
    tot_, add, addw, by = 0, 0, 0.0, collections.Counter()
    for i, r in enumerate(RW):
        if msk is not None and not msk[i]: continue
        for side in (0, 1):
            for p in r['A'][R][side]:
                if gk(p['k']) == 0: continue
                tot_ += 1
                if p['tag'] != 'R0':
                    add += 1; by[p['tag']] += 1; z = (p['pir'] - MU['pir']) / SD['pir']
                    addw += (B_LIVE[0] + B_LIVE[1] * z) * p['min'] / 40 * gk(p['k'])
    return tot_, add, addw, by
for lab, msk in (('ολες οι αγωνιστικες', None), ('αγωνιστικες ≤10', M10)):
    for R in VERS:
        t_, a_, w_, by = cnts(rows, R, msk)
        P(f'  {lab:20s} {R}: απουσιες που μετρουν {t_} · ΝΕΕΣ vs R0 {a_} ({dict(by)}) · ματς με αλλαγη '
          f'{sum(1 for i, r in enumerate(rows) if (msk is None or msk[i]) and any(p["tag"] != "R0" and gk(p["k"]) > 0 for s in (0, 1) for p in r["A"][R][s]))}'
          f' · μεσο κοστος νεας απουσιας (live τυπος) {w_ / a_ if a_ else 0:+.2f} π.')
# ελεγχος R2/R3: ποσες απο τις νεες ειναι παικτες που ΔΕΝ ξαναπαιζουν φετος με την ομαδα (πιθανως εφυγαν)
nn, gone = 0, 0
for r in rows:
    for side in (0, 1):
        team = r['team'][side]
        for p in r['A']['R2'][side]:
            if p['tag'] != 'R2' or gk(p['k']) == 0: continue
            nn += 1
            if not any(t > r['ts'] + 3600 for t, tm, c in APPS.get((r['sea'][1:], p['pid']), []) if tm == team and c == 'E'): gone += 1
P(f'  R2 νεες απουσιες (k≤10): {nn} · απο αυτες δεν ξαναπαιζουν φετος με την ομαδα (τραυμ. σεζον ή εφυγαν): {gone}')
# ================= ΕΠΕΚΤΑΣΗ: + αγωνιστικες 1-2 =================
RX = rows + ext
# ελεγχος R3: ποσα ματς της ομαδας μεχρι το ντεμπουτο (πολυ αργο = πιθανη μεταγραφη μεσα στη σεζον, οχι απουσια)
dd = collections.Counter()
for r in RX:
    for side in (0, 1):
        team = r['team'][side]
        for p in r['A']['R3'][side]:
            if p['tag'] != 'R3' or gk(p['k']) == 0: continue
            first = min(t for t, tm, c in APPS[(r['sea'][1:], p['pid'])] if tm == team and c == 'E')
            n = sum(1 for x in TG[(r['sea'], team)] if r['ts'] - 3600 < x[0] < first - 3600)
            dd['0-3' if n <= 3 else ('4-10' if n <= 10 else ('11-20' if n <= 20 else '21+'))] += 1
P(f'  R3 νεες απουσιες (k≤10, κυρια+αγων 1-2): ματς ομαδας μεχρι να ξαναπαιξει → {dict(dd)}')
Yx, ysx, mdx, XFx, HELDx, FIXx, BFx = run(RX, 'επεκταση')
P(''); P(f'## Ε. ΕΠΕΚΤΑΣΗ (περιγραφικο, ΟΧΙ το στησιμο του v2): κυρια + αγωνιστικες 1-2 ({len(RX)} ματς), LOSO β ξανα σε ολο το συνολο')
report(RX, Yx, ysx, HELDx, 'R0', np.ones(len(RX), bool), f'ολα ({len(RX)})', crit=False)
report(RX, Yx, ysx, HELDx, 'R0', mdx <= 2, f'μονο αγωνιστικες 1-2 ({int((mdx <= 2).sum())})', crit=False)
report(RX, Yx, ysx, FIXx, 'R0', mdx <= 2, f'μονο αγωνιστικες 1-2 — σταθεροι live', crit=False)
report(RX, Yx, ysx, HELDx, 'R0', mdx <= 10, f'αγωνιστικες 1-10 ({int((mdx <= 10).sum())})', crit=False)
for R in VERS:
    t_, a_, w_, by = cnts(ext, R)
    P(f'  αγων. 1-2 {R}: απουσιες που μετρουν {t_} · νεες vs R0 {a_} ({dict(by)}) · μεσο κοστος νεας {w_ / a_ if a_ else 0:+.2f} π.')
# ================= ΠΑΡΑΔΕΙΓΜΑΤΑ =================
P(''); P('## ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ: R2/R3 μετραει κοστος, R0 μετρησε 0 (κοστος με live τυπο 0.56 + 1.06·z)')
EX = []
for r in RX:
    for side in (0, 1):
        team = r['team'][side]
        for p in r['A']['R3'][side]:
            if p['tag'] not in ('R2', 'R3') or gk(p['k']) == 0: continue
            z = (p['pir'] - MU['pir']) / SD['pir']; c = (B_LIVE[0] + B_LIVE[1] * z) * p['min'] / 40 * gk(p['k'])
            EX.append((c, p, r, team))
EX.sort(key=lambda x: -x[0])
picked, seen_t = [], set()
for want in ('R3', 'R2', None):
    for c, p, r, team in EX:
        if (want and p['tag'] != want) or (p['pid'], r['sea']) in seen_t: continue
        picked.append((c, p, r, team)); seen_t.add((p['pid'], r['sea'])); break
for c, p, r, team in EX:
    if len(picked) >= 5: break
    if (p['pid'], r['sea']) in seen_t: continue
    picked.append((c, p, r, team)); seen_t.add((p['pid'], r['sea']))
for c, p, r, team in picked:
    pa, pn = prev_avg(r['sea'], p['pid'])
    L = TG[(r['sea'], team)]; prev = [x for x in L if x[0] < r['ts'] - 3600]
    seq = ''.join('Π' if d.get(p['pid'], (0,))[0] > 0 else '·' for _, _, d in prev)
    nxt = [t for t, tm, cc in APPS.get((r['sea'][1:], p['pid']), []) if tm == team and cc == 'E' and t > r['ts']]
    prev_teams = sorted({tm for (s_, tm), LL in TG.items() if s_ == psea(r['sea']) for _, _, d in LL if d.get(p['pid'], (0,))[0] > 0})
    P(f"  {NAME.get(p['pid'], p['pid'])} · ομαδα {team} · {r['sea']} · αγωνιστικη ομαδας {len(prev) + 1} · εκδοχη {p['tag']}"
      f" · φετινα ματς που επαιξε {seq.count('Π')}/{len(prev)} (σειρα {seq or '-'}) · περσινος μ.ο. {pa:.1f}′ σε {pn} ματς (ομαδα/ες περσι {','.join(prev_teams)})"
      f" · λεπτα (10 τελ.) {p['min']:.1f}′ · PIR/40 {p['pir']:.1f} · k {p['k']} ×{gk(p['k']):g} → κοστος {c:+.2f} π. (R0: 0)"
      f" · ξαναπαιζει με την ομαδα: {pd.Timestamp(min(nxt), unit='s').strftime('%Y-%m-%d') if nxt else 'ΟΧΙ φετος'}")
open('el_regular_rule_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
