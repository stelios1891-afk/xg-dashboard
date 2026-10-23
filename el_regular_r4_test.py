# -*- coding: utf-8 -*-
"""el_regular_r4_test.py — EUROLEAGUE ΑΠΟΥΣΙΕΣ: ΚΑΝΟΝΑΣ «ΤΑΚΤΙΚΟΣ», εκδοχη R4 (22/10/2026, εγκριση Στελιου για τεστ).
Συνεχεια του el_regular_rule_test.py (R1/R2/R3 ✗). R4 διορθωνει ΜΟΝΟ δυο περιπτωσεις:
 R0 = live (el_absence.team_cost): απων μετραει αν επαιξε ≥3 απο τα 10 τελευταια φετινα ματς της ομαδας· οποιος δεν επαιξε φετος → 0.
 R4 — τακτικος αν:
  (α) η ομαδα εχει n < 10 φετινα ματς πριν το ματς: επαιξε σε ≥ max(1, ceil(n/2)) απο αυτα (οπως γραφτηκε· ΑΝΤΙΚΑΘΙΣΤΑ το ≥3 για n<10,
      αρα στα n = 7-9 ειναι ΑΥΣΤΗΡΟΤΕΡΟ απο το live: 3/7, 3/8, 3/9 δεν μετρανε πια).
  (β) δεν εχει παιξει ΚΑΘΟΛΟΥ φετος: μετραει ΜΟΝΟ αν περσι ηταν στην ΙΔΙΑ ομαδα και τακτικος στο τελος (≥3 απο τα 10 τελευταια ματς
      Ευρωλιγκας της ομαδας περσι)· λεπτα = μ.ο. των τελευταιων ≤10 περσινων ματς του· PIR/40 οπως live (τελευταια 60 ματς EL)·
      g(k), k = φετινα ματς της ομαδας + 1 (ολα τα λειπει). Ροστερ στο backtest (ο live το παιρνει απο RotoWire OUT): ο παικτης
      παιζει ΑΡΓΟΤΕΡΑ φετος με την ομαδα και δεν επαιξε για αλλη ομαδα (EL/EuroCup) πριν την πρωτη του εμφανιση εδω (ιδια συνθηκη με R3).
  (γ) n ≥ 10: οπως το live (≥3/10).
 R4b (ΔΕΥΤΕΡΗ ΑΝΑΓΝΩΣΗ, σημειωμενη): ιδια με R4 αλλα (α) κατωφλι max(1, ceil(n/3)). Λογος: με ceil(n/2) ο Williams-Goss (ZAL φετος, 2/6)
      ΔΕΝ μετραει (κατωφλι 3), ενω το παραδειγμα της εγκρισης λεει «2/6 μετραει». Με ceil(n/3): 1/2, 2/4, 3/6, 2/6 μετρανε ολα, και για
      n = 7-9 το κατωφλι ειναι 3 = live (καθαρη χαλαρωση, τιποτα δεν αφαιρειται).
 Κοστος χαντικαπ ΙΔΙΟΣ με live: (0.56 + 1.06·z)·λεπτα/40·g(k), g: k 1-3 ×1 · 4-10 ×0.5 · 11+ ×0.
ΜΕΤΡΗΣΗ:
 Α. ΧΑΝΤΙΚΑΠ = στησιμο el_regular_rule_test (V1 του el_absence_v2_test): 1481 ματς E2021-25, ≥2 φετινα ματς και οι δυο, ανοιγμα Crown,
    picks ≥8%, σ 11.5. Κυριο: LOSO επανεκτιμηση β0/β1 ανα εκδοχη. Δευτερευον: σταθεροι live 0.56/1.06.
    ΕΛΕΓΧΟΣ: R0 = V1 (626 picks, +65.8μ, +10.5%, 5/5) — αλλιως σταματαω.
 Β. ΣΥΝΟΛΑ = στησιμο el_absence_onoff_test εκδοχη W4 (ποντοι ομαδας += bO·Σ δικα w·onO/sd + bD·Σ αντιπ. w·onD/sd), LOSO επανεκτιμηση
    bO/bD (ridge 1), picks συνολων ≥8% ανοιγμα. sd on/off ΣΤΑΘΕΡΟ στην τιμη R0 (αλλαζει ΜΟΝΟ ποιοι αποντες μετρανε).
    Δευτερευον: σταθεροι live bO −0.426 / bD −0.7975. ΕΛΕΓΧΟΣ: R0 W4 = 511 picks, +59.0μ, ROI +11.5% — αλλιως σταματαω.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο), ΧΩΡΙΣΤΑ για χαντικαπ και συνολα, LOSO E2021-25:
  R4 ΠΕΡΝΑ αν: LOSO RMSE καλυτερο απο R0 σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ R0 ΚΑΙ θετικες σεζον ≥4/5.
  (R4b κρινεται με τα ιδια κριτηρια, αλλα ειναι δευτερη αναγνωση του κανονα — δεν ειναι αυτο που εγκριθηκε κατα γραμμα.)
  Περιγραφικα: ποσες απουσιες προσθετει (α) και (β) χωριστα (και ποσες αφαιρει η R4 στα n 7-9), μεσο κοστος· τα ιδια μονο για
  αγωνιστικες 1-10 (κυρια + αγωνιστικες 1-2 για το χαντικαπ, οπως η Ε του προηγουμενου) — ΔRMSE ανα σεζον, μοναδες, ROI.
  Ελεγχος 3 παραδειγματων (α / β / μεγαλο κοστος).
Εξοδος: el_regular_r4_test_out.txt"""
import sys, io, contextlib, collections, math
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def SAVE(): open('el_regular_r4_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
# ======================= Α. ΧΑΝΤΙΚΑΠ: φορτωμα (ιδιο με el_regular_rule_test) =======================
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_v2_test.py', encoding='utf-8').read().split("P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
rows, keys, TG, PH, NAME, value, MU, SD, SE, D, REC, NP = (ns[k] for k in ('rows', 'keys', 'TG', 'PH', 'NAME', 'value', 'MU', 'SD', 'SE', 'D', 'REC', 'NP'))
pd = ns['pd']; PL = ns['ns']['PL']
VERS = ['R0', 'R4', 'R4b']
B_LIVE = np.array([0.56, 1.06])
def psea(s): return f'E{int(s[1:]) - 1}'
def gk(k): return 1.0 if k <= 3 else (.5 if k <= 10 else 0.0)
APPS = collections.defaultdict(list)                     # (ετος, pid) → [(ts, ομαδα, comp)]
for k_, g in PL.items():
    if g.get('comp') not in ('E', 'U') or 'ph' not in g or 'pa' not in g: continue
    ts_ = pd.Timestamp(g['utc']).timestamp(); yr = g['season'][1:]
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        for p in g[side]:
            if (p[3] or 0) > 0: APPS[(yr, p[0])].append((ts_, g[tc], g['comp']))
def roster_later(sea, team, pid, ts):
    A = APPS.get((sea[1:], pid), [])
    mine = [t for t, tm, c in A if tm == team and c == 'E']
    if not mine or min(mine) < ts - 3600: return False
    first = min(mine)
    return not any(tm != team and t < first for t, tm, c in A)
# περσινα λεπτα παικτη (EL, ολες οι ομαδες, χρονολογικα)
PREVMIN = collections.defaultdict(list)                  # (σεζον, pid) → [(ts, λεπτα)]
for (s_, tm), L in TG.items():
    for t, _, d in L:
        for pid, v in d.items():
            if v[0] > 0: PREVMIN[(s_, pid)].append((t, v[0]))
for v in PREVMIN.values(): v.sort()
def prev_last10(sea, pid):
    m = [x[1] for x in PREVMIN.get((psea(sea), pid), [])][-10:]
    return float(np.mean(m)) if m else None
def beta_cands(sea, team, ts, played):
    """(β): τακτικος περσι στην ιδια ομαδα (≥3 απο τα 10 τελευταια), δεν επαιξε φετος, ροστερ (παιζει αργοτερα εδω, οχι αλλου πριν)"""
    LP = TG.get((psea(sea), team), [])
    cc = collections.Counter(p for _, _, d in LP[-10:] for p, v in d.items() if v[0] > 0)
    return {pid: c for pid, c in cc.items() if c >= 3 and pid not in played and roster_later(sea, team, pid, ts)}
def thr_a(n, rule): return max(1, math.ceil(n / 2)) if rule == 'R4' else max(1, math.ceil(n / 3))
def cand_set(prev, rule, sea, team, ts):
    """→ {pid: ετικετα} · 'R0' = μετραει και στο live · 'a' = νεο απο (α) · 'b' = νεο απο (β)"""
    n = len(prev); cnt = collections.Counter(p for _, _, d in prev[-10:] for p, v in d.items() if v[0] > 0)
    cand = {pid: 'R0' for pid, c in cnt.items() if c >= 3}
    if rule == 'R0': return cand, cnt, {}
    if n < 10:
        t = thr_a(n, rule); cand = {pid: ('R0' if c >= 3 else 'a') for pid, c in cnt.items() if c >= t}
    played = {p for _, _, d in prev for p, v in d.items() if v[0] > 0}
    bc = beta_cands(sea, team, ts, played)
    for pid in bc: cand[pid] = 'b'
    return cand, cnt, bc
def absents_v(sea, team, ts, rule, allow_short=False):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None or (len(prev) < 2 and not allow_short): return None
    cand, cnt, bc = cand_set(prev, rule, sea, team, ts)
    res = []
    for pid, tag in cand.items():
        if today.get(pid, (0,))[0] > 0: continue
        k = 0
        for _, _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = value(pid, ts)
        if v is None: continue
        if tag == 'b':
            pm = prev_last10(sea, pid)
            if pm is None: continue
            v = dict(v, min=pm)
        if v['min'] < 10: continue
        res.append(dict(pid=pid, k=k + 1, tag=tag, nseason=len(prev), napp=cnt.get(pid, 0), nprev=bc.get(pid), **v))
    return res
def build(sea, hc, ac, ts, allow_short):
    A = {}
    for R in VERS:
        ah, aa = absents_v(sea, hc, ts, R, allow_short), absents_v(sea, ac, ts, R, allow_short)
        if ah is None or aa is None: return None
        A[R] = (ah, aa)
    return A
def nprev_team(sea, team, ts): return sum(1 for x in TG[(sea, team)] if x[0] < ts - 3600)
for r, (sea, hc, ac, ts) in zip(rows, keys):
    r['A'] = build(sea, hc, ac, ts, False)
    r['md'] = max(nprev_team(sea, hc, ts), nprev_team(sea, ac, ts)) + 1
    r['team'] = (hc, ac); r['sea'] = sea; r['ts'] = ts
    a0 = sorted((p['pid'], p['k']) for p in r['A']['R0'][0]); b0 = sorted((p['pid'], p['k']) for p in r['ah'])
    assert a0 == b0, ('R0 ≠ v2', sea, hc, ts)
P(f'Α. ΧΑΝΤΙΚΑΠ — κυρια ματς (ιδια με v2): {len(rows)} · ελεγχος R0 = αποντες v2: OK')
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
    md = max(nprev_team(sea, hc, ts), nprev_team(sea, ac, ts)) + 1
    ext.append(dict(y=sea, act=float(D.hs.values[pos] - D.as_.values[pos]), m=float(NP[key]['h_new']), op=d_['open'][2:], A=A, md=md, team=(hc, ac), sea=sea, ts=ts))
P(f'επιπλεον ματς αγωνιστικων 1-2 (εκτος v2, μονο για τα περιγραφικα): {len(ext)}')
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
def run(RW):
    Y = np.array([r['act'] - r['m'] for r in RW]); ys = np.array([r['y'] for r in RW]); md = np.array([r['md'] for r in RW])
    XF = {R: np.array([feats(r, R) for r in RW]) for R in VERS}
    HELD, FIX, BF = {}, {}, {}
    for R in VERS:
        X = XF[R]; h = np.zeros(len(Y))
        for s in SE:
            m = ys != s; b = np.linalg.solve(X[m].T @ X[m] + np.eye(2), X[m].T @ Y[m]); h[ys == s] = (X @ b)[ys == s]
        HELD[R] = h; FIX[R] = X @ B_LIVE; BF[R] = np.linalg.solve(X.T @ X + np.eye(2), X.T @ Y)
    return Y, ys, md, HELD, FIX, BF
def report(RW, Y, ys, H, msk, title, crit=True, base=None):
    P(f'  {title}')
    U0 = picks(RW, H['R0'], msk); res = {}
    for R in VERS:
        h = H[R]
        d = [rmse(Y - h, (ys == s) & msk) - rmse(Y - H['R0'], (ys == s) & msk) for s in SE]
        U = picks(RW, h, msk); nb = sum(1 for x in d if x < 0)
        ok = R != 'R0' and nb >= 4 and tot(U) >= tot(U0) and npos(U) >= 4
        verdict = '' if R == 'R0' or not crit else ('  → ΠΕΡΝΑ τα κριτηρια' if ok else '  ✗ δεν περνα τα κριτηρια')
        P(f'    {R:3s}: ΔRMSE vs R0 ανα σεζον (ποντοι διαφορας, − = καλυτερο) {" ".join(f"{s[-2:]}:{x:+.3f}" for s, x in zip(SE, d))} (καλυτερο σε {nb}/5) | {cell(U)}{verdict}')
        res[R] = ok
    P(f'    (χωρις καμια διορθωση απουσιων: {cell(picks(RW, np.zeros(len(RW)), msk))})')
    return res
Y, ys, md, HELD, FIX, BF = run(rows)
ALL = np.ones(len(Y), bool)
U0chk = picks(rows, HELD['R0']); u0 = [x for v in U0chk.values() for x in v]
P(f'ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ R0 χαντικαπ: picks {len(u0)} · {sum(u0):+.1f}μ · ROI {np.mean(u0) * 100:+.1f}% · θετικες {npos(U0chk)}/5 (στοχος 626 · +65.8μ · +10.5% · 5/5)')
if not (len(u0) == 626 and abs(sum(u0) - 65.8) < 0.06):
    P('  ✗ R0 ΔΕΝ αναπαραγει — ΣΤΟΠ'); SAVE(); sys.exit(1)
P(''); P('## Α0. ΣΥΝΤΕΛΕΣΤΕΣ χαντικαπ (ολα τα δεδομενα, ridge 1): β0 = ποντοι ανα 40′ απουσιας μεσου PIR · β1 = ανα 1 τυπ. αποκλιση PIR/40')
for R in VERS: P(f'  {R}: β0 {BF[R][0]:+.2f} · β1 {BF[R][1]:+.2f}')
P(''); P('## Α1. ΧΑΝΤΙΚΑΠ ΚΥΡΙΟ — LOSO επανεκτιμηση β, picks ≥8% ανοιγμα Crown, E2021-25')
RES_H = report(rows, Y, ys, HELD, ALL, f'ολα τα κυρια ματς ({len(rows)})')
P(''); P('## Α2. ΧΑΝΤΙΚΑΠ ΔΕΥΤΕΡΕΥΟΝ — σταθεροι live 0.56 + 1.06·z (περιγραφικο)')
report(rows, Y, ys, FIX, ALL, f'ολα τα κυρια ματς ({len(rows)})')
# ---- ποσες απουσιες αλλαζουν ----
def live_cost(p): z = (p['pir'] - MU['pir']) / SD['pir']; return (B_LIVE[0] + B_LIVE[1] * z) * p['min'] / 40 * gk(p['k'])
def cnts(RW, R, msk=None):
    tot_, add, cost, removed, mch = 0, collections.Counter(), collections.defaultdict(float), 0, 0
    for i, r in enumerate(RW):
        if msk is not None and not msk[i]: continue
        ch = False
        for side in (0, 1):
            new = {p['pid'] for p in r['A'][R][side] if gk(p['k']) > 0}
            for p in r['A'][R][side]:
                if gk(p['k']) == 0: continue
                tot_ += 1
                if p['tag'] != 'R0': add[p['tag']] += 1; cost[p['tag']] += live_cost(p); ch = True
            gone = [p for p in r['A']['R0'][side] if gk(p['k']) > 0 and p['pid'] not in new]
            removed += len(gone); ch = ch or bool(gone)
        mch += ch
    return tot_, add, cost, removed, mch
def print_cnts(RW, lab, msk=None):
    for R in VERS:
        t_, a_, c_, rm, mch = cnts(RW, R, msk)
        P(f'  {lab:22s} {R:3s}: απουσιες που μετρουν (k≤10) {t_} · ΝΕΕΣ (α) {a_["a"]} (μεσο κοστος {c_["a"] / a_["a"] if a_["a"] else 0:+.2f} π.)'
          f' · ΝΕΕΣ (β) {a_["b"]} (μεσο κοστος {c_["b"] / a_["b"] if a_["b"] else 0:+.2f} π.) · ΑΦΑΙΡΟΥΝΤΑΙ vs R0 {rm} · ματς με αλλαγη {mch}')
P(''); P('## Α3. ΠΟΣΕΣ ΑΠΟΥΣΙΕΣ ΑΛΛΑΖΟΥΝ — χαντικαπ (κοστος με live τυπο, ποντοι διαφορας ανα απουσια)')
print_cnts(rows, f'κυρια ({len(rows)})')
print_cnts(rows, 'κυρια, αγωνιστ. ≤10', md <= 10)
RX = rows + ext
print_cnts(ext, f'αγωνιστ. 1-2 ({len(ext)})')
# (β): ποσα ματς της ομαδας μεχρι να ξαναπαιξει
dd = collections.Counter()
for r in RX:
    for side in (0, 1):
        team = r['team'][side]
        for p in r['A']['R4'][side]:
            if p['tag'] != 'b' or gk(p['k']) == 0: continue
            first = min(t for t, tm, c in APPS[(r['sea'][1:], p['pid'])] if tm == team and c == 'E')
            n = sum(1 for x in TG[(r['sea'], team)] if r['ts'] - 3600 < x[0] < first - 3600)
            dd['0-3' if n <= 3 else ('4-10' if n <= 10 else ('11-20' if n <= 20 else '21+'))] += 1
P(f'  (β) νεες απουσιες (k≤10, κυρια + αγων. 1-2): ματς ομαδας ΑΠΟ το ματς ως την επιστροφη του → {dict(sorted(dd.items()))}')
# R4: n της ομαδας οπου αφαιρουνται
rmn = collections.Counter()
for r in RX:
    for side in (0, 1):
        new = {p['pid'] for p in r['A']['R4'][side]}
        for p in r['A']['R0'][side]:
            if gk(p['k']) > 0 and p['pid'] not in new: rmn[f"n={p['nseason']} ({p['napp']}/{p['nseason']})"] += 1
P(f'  R4 αφαιρεσεις (μετρουσαν στο live, οχι στην R4), ανα φετινα ματς ομαδας: {dict(sorted(rmn.items()))}')
Yx, ysx, mdx, HELDx, FIXx, BFx = run(RX)
P(''); P(f'## Α4. ΧΑΝΤΙΚΑΠ ΜΟΝΟ ΑΓΩΝΙΣΤΙΚΕΣ 1-10 (κυρια + αγων. 1-2 = {len(RX)} ματς, LOSO β σε ολο αυτο το συνολο· περιγραφικο)')
report(RX, Yx, ysx, HELDx, mdx <= 10, f'αγωνιστικες 1-10 ({int((mdx <= 10).sum())} ματς) — LOSO', crit=False)
report(RX, Yx, ysx, FIXx, mdx <= 10, f'αγωνιστικες 1-10 ({int((mdx <= 10).sum())} ματς) — σταθεροι live', crit=False)
report(RX, Yx, ysx, HELDx, mdx <= 2, f'μονο αγωνιστικες 1-2 ({int((mdx <= 2).sum())} ματς) — LOSO', crit=False)
report(RX, Yx, ysx, HELDx, mdx > 10, f'αγωνιστικες 11+ ({int((mdx > 10).sum())} ματς) — LOSO', crit=False)
SAVE()
# ======================= Β. ΣΥΝΟΛΑ (στησιμο el_absence_onoff_test W4) =======================
n2 = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_onoff_test.py', encoding='utf-8').read().split("P(''); P('################ ΣΥΝΟΛΑ ################')")[0], n2)
sys.stdout.reconfigure(encoding='utf-8')
TG2, PH2, NAME2, profile, SD2, rows2_ref, D2, REC2, NP2 = (n2[k] for k in ('TG', 'PH', 'NAME', 'profile', 'SD', 'rows', 'D', 'REC', 'NP'))
def absents_t(sea, team, ts, rule):
    """ιδιο με el_absence_onoff_test.absents για R0· για R4/R4b ιδιοι κανονες (α)/(β) με το χαντικαπ"""
    L = TG2.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    n = len(prev); cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v > 0)
    cand = {pid: 'R0' for pid, c in cnt.items() if c >= 3}
    if rule != 'R0':
        if n < 10:
            t = thr_a(n, rule); cand = {pid: ('R0' if c >= 3 else 'a') for pid, c in cnt.items() if c >= t}
        played = {p for _, d in prev for p, v in d.items() if v > 0}
        for pid in beta_cands(sea, team, ts, played): cand[pid] = 'b'
    res = []
    for pid, tag in cand.items():
        if today.get(pid, 0) > 0: continue
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, 0) > 0: break
            k += 1
        if tag == 'b':
            pm = prev_last10(sea, pid); h = [pm] if pm is not None else []
        else:
            h = [mn for t_, mn in PH2[pid] if t_ < ts - 3600][-10:]
        if not h or np.mean(h) < 10: continue
        w = np.mean(h) / 40 * (1.0 if k + 1 <= 3 else (.5 if k + 1 <= 10 else 0.0))
        if w <= 0: continue
        pr = profile(NAME2[pid], int(sea[1:]))
        res.append(dict(pid=pid, tag=tag, k=k + 1, w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))
    return res
rows2 = []
for pos, d_ in REC2[23].items():
    sea = D2.season.values[pos]
    if sea not in SE: continue
    hc, ac = D2.home.values[pos], D2.away.values[pos]; t = pd.Timestamp(D2.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP2 or NP2[key].get('t_new') is None or NP2[key].get('h_new') is None: continue
    ts = t.timestamp(); A = {}
    for R in VERS:
        ah, aa = absents_t(sea, hc, ts, R), absents_t(sea, ac, ts, R)
        if ah is None or aa is None: A = None; break
        A[R] = (ah, aa)
    if A is None: continue
    nh = sum(1 for x in TG2[(sea, hc)] if x[0] < ts - 3600); na = sum(1 for x in TG2[(sea, ac)] if x[0] < ts - 3600)
    rows2.append(dict(y=sea, hs=float(D2.hs.values[pos]), as_=float(D2.as_.values[pos]), T=float(NP2[key]['t_new']), M=float(NP2[key]['h_new']), A=A, op=d_['open'], cl=d_[0],
                      md=max(nh, na) + 1, team=(hc, ac), sea=sea, ts=ts))
assert len(rows2) == len(rows2_ref), ('συνολα: αλλο πληθος ματς', len(rows2), len(rows2_ref))
for r, q in zip(rows2, rows2_ref):
    assert sorted(round(p['w'], 6) for p in r['A']['R0'][0]) == sorted(round(p['w'], 6) for p in q['ah']), 'συνολα: R0 ≠ onoff αποντες'
    assert sorted(round(p['w'], 6) for p in r['A']['R0'][1]) == sorted(round(p['w'], 6) for p in q['aa']), 'συνολα: R0 ≠ onoff αποντες'
P(''); P(f'Β. ΣΥΝΟΛΑ — ματς E2021-25 (στησιμο onoff, μαζι οι αγωνιστικες 1-2): {len(rows2)} · ελεγχος R0 = αποντες el_absence_onoff_test: OK')
zf = lambda p, f: p[f] / SD2[f]
def tf(own, opp): return np.array([sum(p['w'] * zf(p, 'onO') for p in own), sum(p['w'] * zf(p, 'onD') for p in opp)])
YH = np.array([r['hs'] - (r['T'] + r['M']) / 2 for r in rows2])
YA = np.array([r['as_'] - (r['T'] - r['M']) / 2 for r in rows2])
YT = YH + YA; ys2 = np.array([r['y'] for r in rows2]); md2 = np.array([r['md'] for r in rows2]); ALL2 = np.ones(len(rows2), bool)
B_LIVE_T = np.array([-0.426, -0.7975])
XH2, XA2, HT, FT, BT = {}, {}, {}, {}, {}
for R in VERS:
    XH2[R] = np.array([tf(r['A'][R][0], r['A'][R][1]) for r in rows2]); XA2[R] = np.array([tf(r['A'][R][1], r['A'][R][0]) for r in rows2])
    def fitT(tr, R=R):
        X = np.r_[XH2[R][tr], XA2[R][tr]]; y = np.r_[YH[tr], YA[tr]]; return np.linalg.solve(X.T @ X + np.eye(2), X.T @ y)
    BT[R] = fitT(ALL2); h = np.zeros(len(rows2))
    for s in SE:
        b = fitT(ys2 != s); m = ys2 == s; h[m] = XH2[R][m] @ b + XA2[R][m] @ b
    HT[R] = h; FT[R] = XH2[R] @ B_LIVE_T + XA2[R] @ B_LIVE_T
def tp(t, T_):
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7); return po, 1 - po - pu, pu
    po = 1 - Phi((T_ - t) / 16.7); return po, 0.0, 1 - po
def tpicks(adj, msk=None):
    U = collections.defaultdict(list)
    for i, (r, a) in enumerate(zip(rows2, adj)):
        if msk is not None and not msk[i]: continue
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e < .08: continue
        x = (r['hs'] + r['as_'] - T_) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1))
    return U
Uc = tpicks(HT['R0']); uc = [x for v in Uc.values() for x in v]
P(f'ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ R0 συνολα W4: picks {len(uc)} · {sum(uc):+.1f}μ · ROI {np.mean(uc) * 100:+.1f}% · θετικες {npos(Uc)}/5 (στοχος 511 · +59.0μ · +11.5% · 5/5)')
if not (len(uc) == 511 and abs(sum(uc) - 59.0) < 0.06):
    P('  ✗ R0 συνολων ΔΕΝ αναπαραγει — ΣΤΟΠ'); SAVE(); sys.exit(1)
P(''); P('## Β0. ΣΥΝΤΕΛΕΣΤΕΣ συνολων W4 (ολα, ridge 1): ποντοι ομαδας ανα 40′ απουσιας ανα 1 τυπ. αποκλιση on/off')
for R in VERS: P(f'  {R}: bO (δικα×onO) {BT[R][0]:+.2f} · bD (αντιπ.×onD) {BT[R][1]:+.2f}')
def treport(H, msk, title, crit=True):
    P(f'  {title}')
    U0 = tpicks(H['R0'], msk); res = {}
    P(f'    RMSE συνολου R0 (ποντοι) {rmse(YT - H["R0"], msk):.3f}')
    for R in VERS:
        h = H[R]; d = [rmse(YT - h, (ys2 == s) & msk) - rmse(YT - H['R0'], (ys2 == s) & msk) for s in SE]
        U = tpicks(h, msk); nb = sum(1 for x in d if x < 0)
        ok = R != 'R0' and nb >= 4 and tot(U) >= tot(U0) and npos(U) >= 4
        verdict = '' if R == 'R0' or not crit else ('  → ΠΕΡΝΑ τα κριτηρια' if ok else '  ✗ δεν περνα τα κριτηρια')
        P(f'    {R:3s}: ΔRMSE vs R0 ανα σεζον (ποντοι συνολου, − = καλυτερο) {" ".join(f"{s[-2:]}:{x:+.3f}" for s, x in zip(SE, d))} (καλυτερο σε {nb}/5) | {cell(U)}{verdict}')
        res[R] = ok
    P(f'    (χωρις καμια διορθωση απουσιων: {cell(tpicks(np.zeros(len(rows2)), msk))})')
    return res
P(''); P('## Β1. ΣΥΝΟΛΑ ΚΥΡΙΟ — LOSO επανεκτιμηση bO/bD (W4), picks συνολων ≥8% ανοιγμα, E2021-25')
RES_T = treport(HT, ALL2, f'ολα τα ματς ({len(rows2)})')
P(''); P('## Β2. ΣΥΝΟΛΑ ΔΕΥΤΕΡΕΥΟΝ — σταθεροι live bO −0.426 / bD −0.7975 (περιγραφικο)')
treport(FT, ALL2, f'ολα τα ματς ({len(rows2)})')
P(''); P('## Β3. ΣΥΝΟΛΑ ΜΟΝΟ ΑΓΩΝΙΣΤΙΚΕΣ 1-10 (περιγραφικο)')
treport(HT, md2 <= 10, f'αγωνιστικες 1-10 ({int((md2 <= 10).sum())} ματς) — LOSO', crit=False)
treport(FT, md2 <= 10, f'αγωνιστικες 1-10 ({int((md2 <= 10).sum())} ματς) — σταθεροι live', crit=False)
treport(HT, md2 > 10, f'αγωνιστικες 11+ ({int((md2 > 10).sum())} ματς) — LOSO', crit=False)
def live_tot(p): return B_LIVE_T[0] * p['w'] * zf(p, 'onO') + B_LIVE_T[1] * p['w'] * zf(p, 'onD')   # επιδραση στο ΣΥΝΟΛΟ (δικοι ποντοι + ποντοι αντιπαλου)
P(''); P('## Β4. ΠΟΣΕΣ ΑΠΟΥΣΙΕΣ ΑΛΛΑΖΟΥΝ — συνολα (επιδραση στο συνολο με live bO/bD, ποντοι)')
for lab, msk in ((f'ολα ({len(rows2)})', None), ('αγωνιστ. ≤10', md2 <= 10)):
    for R in VERS:
        t_, add, cs, cabs, rm, nopf = 0, collections.Counter(), collections.defaultdict(float), collections.defaultdict(float), 0, collections.Counter()
        for i, r in enumerate(rows2):
            if msk is not None and not msk[i]: continue
            for side in (0, 1):
                new = {p['pid'] for p in r['A'][R][side]}
                for p in r['A'][R][side]:
                    t_ += 1
                    if p['tag'] != 'R0':
                        add[p['tag']] += 1; v = live_tot(p); cs[p['tag']] += v; cabs[p['tag']] += abs(v); nopf[p['tag']] += p['usg'] is None
                rm += sum(1 for p in r['A']['R0'][side] if p['pid'] not in new)
        P(f'  {lab:14s} {R:3s}: απουσιες (w>0) {t_} · ΝΕΕΣ (α) {add["a"]} (μεση επιδραση {cs["a"] / add["a"] if add["a"] else 0:+.2f}, μεση |επιδραση| {cabs["a"] / add["a"] if add["a"] else 0:.2f} π., χωρις on/off προφιλ {nopf["a"]})'
          f' · ΝΕΕΣ (β) {add["b"]} (μεση {cs["b"] / add["b"] if add["b"] else 0:+.2f}, |..| {cabs["b"] / add["b"] if add["b"] else 0:.2f} π., χωρις προφιλ {nopf["b"]}) · ΑΦΑΙΡΟΥΝΤΑΙ {rm}')
SAVE()
# ======================= ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ =======================
P(''); P('## ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ (απουσιες που προσθετει η R4· κοστος χαντικαπ με live τυπο, συνολα με live bO/bD)')
P(f'  Williams-Goss (ZAL E2026, 2 απο 6 φετινα): κατωφλι R4 = {thr_a(6, "R4")} → {"μετραει" if 2 >= thr_a(6, "R4") else "ΔΕΝ μετραει"} · κατωφλι R4b = {thr_a(6, "R4b")} → {"μετραει" if 2 >= thr_a(6, "R4b") else "ΔΕΝ μετραει"}')
TOTIDX = {(r['sea'], r['team'][0], r['team'][1], r['ts']): r for r in rows2}
EX = []
for r in RX:
    for side in (0, 1):
        for p in r['A']['R4'][side]:
            if p['tag'] in ('a', 'b') and gk(p['k']) > 0: EX.append((live_cost(p), p, r, side))
EX.sort(key=lambda x: -x[0])
pick_ = []
for want in ('a', 'b'):
    c_ = [x for x in EX if x[1]['tag'] == want]
    if c_: pick_.append(c_[len(c_) // 2])                  # τυπικη (διαμεσος κοστους) του τυπου
for x in EX:
    if all((x[1]['pid'], x[2]['sea']) != (y[1]['pid'], y[2]['sea']) for y in pick_): pick_.append(x); break   # μεγαλυτερο κοστος
for c, p, r, side in pick_:
    team = r['team'][side]; L = TG[(r['sea'], team)]; prev = [x for x in L if x[0] < r['ts'] - 3600]
    seq = ''.join('Π' if d.get(p['pid'], (0,))[0] > 0 else '·' for _, _, d in prev)
    LP = TG.get((psea(r['sea']), team), []); seqp = ''.join('Π' if d.get(p['pid'], (0,))[0] > 0 else '·' for _, _, d in LP[-10:])
    pteams = sorted({tm for (s_, tm), LL in TG.items() if s_ == psea(r['sea']) for _, _, d in LL if d.get(p['pid'], (0,))[0] > 0})
    nprevg = len(PREVMIN.get((psea(r['sea']), p['pid']), []))
    today = next(x for x in L if abs(x[0] - r['ts']) < 3600)
    g = PL[today[1]]; sd_ = 'ph' if g['hcode'] == team else 'pa'
    inbox = [q for q in g[sd_] if q[0] == p['pid']]
    st = 'ΔΕΝ ειναι στο box score (απων)' if not inbox else f'στο box score με {inbox[0][3] or 0} λεπτα'
    nxt = [t for t, tm, cc in APPS.get((r['sea'][1:], p['pid']), []) if tm == team and cc == 'E' and t > r['ts'] + 3600]
    oth = sorted({(tm, cc) for t, tm, cc in APPS.get((r['sea'][1:], p['pid']), []) if tm != team})
    tr = TOTIDX.get((r['sea'], r['team'][0], r['team'][1], r['ts']))
    tc = None
    if tr:
        q = next((q for q in tr['A']['R4'][side] if q['pid'] == p['pid']), None)
        if q: tc = live_tot(q); onoff = (q['onO'], q['onD'], q['usg'] is None)
    P(f"  [{p['tag']}] {NAME.get(p['pid'], p['pid'])} · ομαδα {team} ({'γηπ' if side == 0 else 'φιλ'} vs {r['team'][1 - side]}) · {r['sea']} · {pd.Timestamp(r['ts'], unit='s').strftime('%Y-%m-%d')} · αγωνιστικη ομαδας {len(prev) + 1}")
    P(f"      φετος: ομαδα {len(prev)} ματς πριν, επαιξε {seq.count('Π')} (σειρα {seq or '-'}) · κατωφλι R4 {thr_a(len(prev), 'R4') if len(prev) < 10 else 3} / R4b {thr_a(len(prev), 'R4b') if len(prev) < 10 else 3}")
    P(f"      περσι: ομαδα/ες {','.join(pteams) or '-'} · {nprevg} ματς EL · στα 10 τελευταια της {team}: {seqp.count('Π')}/{len(seqp)} (σειρα {seqp or '-'})")
    P(f"      λεπτα {p['min']:.1f}′ · PIR/40 {p['pir']:.1f} (z {(p['pir'] - MU['pir']) / SD['pir']:+.2f}) · k {p['k']} ×{gk(p['k']):g} → κοστος ΧΑΝΤΙΚΑΠ {c:+.2f} π. (R0: 0)"
      + (f" · ΣΥΝΟΛΑ επιδραση {tc:+.2f} π. (on/off περσι επιθ {onoff[0]:+.2f} αμυνα {onoff[1]:+.2f}{', ΧΩΡΙΣ προφιλ' if onoff[2] else ''})" if tc is not None else ' · ΣΥΝΟΛΑ: δεν μετραει εκει (λεπτα/ματς εκτος)'))
    P(f"      εκεινο το ματς: {st} · ξαναπαιζει με την ομαδα: {pd.Timestamp(min(nxt), unit='s').strftime('%Y-%m-%d') if nxt else 'ΟΧΙ φετος'}"
      f" · φετος σε αλλη ομαδα: {oth or 'καμια'}")
P(''); P('## ΚΡΙΣΗ (προ-δηλωμενα: RMSE ≥4/5 & μοναδες ≥ R0 & θετικες ≥4/5)')
for R in ('R4', 'R4b'):
    P(f'  {R}: ΧΑΝΤΙΚΑΠ {"ΠΕΡΝΑ" if RES_H[R] else "δεν περνα"} · ΣΥΝΟΛΑ {"ΠΕΡΝΑ" if RES_T[R] else "δεν περνα"}' + ('  (R4b = δευτερη αναγνωση, οχι η εγκεκριμενη κατα γραμμα)' if R == 'R4b' else ''))
SAVE()
