# -*- coding: utf-8 -*-
"""el_clean_tests.py — ΕΥΡΩΛΙΓΚΑ «ΚΑΘΑΡΑ» ΤΕΣΤ, σταδιο 2 (5/10/2026, Στελιος «τρεξε ολα τα τεστ»).
Προβλεψεις: el_clean_grid.pkl (576 εκδοχες χαντικαπ, 24 συνολων). Αγορα: Crown (ανοιγμα/κλεισιμο) + Bet365 (ανοιγμα), Nowgoal, E2021-E2025.
«ΚΑΘΑΡΟ» = για καθε σεζον-ελεγχου ΟΛΕΣ οι επιλογες γινονται ΜΟΝΟ με τις αλλες 4 σεζον.
ΤΕΣΤ 1 — ρεαλιστικο ROI του σημερινου setup: μηχανη (RMSE στις αλλες) + κανονες live (μοντελο μονο, ≥8%, σ 11.5 / 16.7), ανοιγμα Crown.
   Συνολα: μηχανη + καμπυλη (a + b·αγων απο τις αλλες) + φιλικα κT {0,.25,.5} (αγων ≤10).
ΤΕΣΤ 2 — ΜΙΞΗ (ιδια κριτηρια με το EuroCup, ΠΡΟ-ΔΗΛΩΜΕΝΑ):
   (α) «περισσοτερα χρηματα»: Α προτεινομενη > σημερινη σε ≥4/5 σεζον & συνολο · Β nested διαλεγει w<1 σε ≥4/5 & μοναδες > σημερινης ·
       Γ bootstrap P ≥ .90 · Δ CLV ≥ σημερινου → ΟΛΑ.
   (β) «ιδια χρηματα, λιγοτερο ρισκο»: Τ1 P(ROI προτ. > σημ.) ≥ .90 · Τ2 χειροτερη σεζον & βυθιση καλυτερες ·
       Τ3 Bet365 P ≥ .80 · Τ4 κλεισιμο P ≥ .80 · Τ5 CLV P ≥ .90 → Τ1 & Τ2 & ≥2 απο Τ3-Τ5.
   Προτεινομενη μιξη = (w .5, σ 12.3, ≥6%) χαντικαπ · (w .5, σ 16.7, ≥6%) συνολα (ιδιες με EuroCup — δεν ρυθμιζονται εδω).
ΤΕΣΤ 3 — ΣΥΝΟΛΑ: μηχανισμοι πανω στην καθαρη βαση (LOSO, ΑΛΛΑΓΗ αν RMSE καλυτερο σε ≥4/5 σεζον): φετινα εγχωρια σκορ (απο 1ο) κd {0,.2,.4},
   επιπεδο πρωταθληματος κl {0,.25}, εδρα «ψηλων συνολων» (προηγουμενες σεζον) κv {0,.5,1}· + βαθμονομηση σ (log-loss).
ΤΕΣΤ 4 — ΔΙΑΚΥΒΕΥΜΑ: (α) κανονικη περιοδος, 5 τελευταιες αγων, ομαδα «κριμενη» (ποσοστο ≤.3 ή ≥.75) · (β) πλει-οφ/F4 —
   υπολοιπο vs κλεισιμο και vs μοντελο (χαντικαπ & συνολο): «η αγορα/το μοντελο τον χανει» αν |t| ≥ 2 & ιδιο προσημο ≥4/5 & ≥1 π.
Εξοδος: el_clean_tests_out.txt"""
import sys, json, math, pickle, itertools, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
Phi = NormalDist().cdf; NN = NormalDist()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
G = pickle.load(open('el_clean_grid.pkl', 'rb'))
H, T, GN, SEAS_, PH, ACT, TOT, KEY = G['H'], G['T'], G['GN'], G['season'], G['phase'], G['act'], G['tot'], G['key']
HOME, AWAY, PRE_T, SE5 = G['home'], G['away'], G['PRE_T'], G['SE5']
N = len(KEY); KIX = {k: i for i, k in enumerate(KEY)}
LIVE_H = (.5, .42, 12, 60, 5.0, 1.1, .5, .5); LIVE_T = (.25, .7, 8, 50.0)
# ---------------- αγορα ----------------
LT = {}
src = open('el_line_timing.py', encoding='utf-8').read().split('ATH = ')[0]
exec(src, LT)
Dl, mapping, series = LT['D'], LT['mapping'], LT['series']
ROWS3 = dict(LT['ROWS']); ROWS8 = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ot'] == 6 and r['cid'] == 8: ROWS8[(r['ngid'], r.get('t', 21))] = r['rows']
MK = {21: {}, 23: {}}      # i -> {'o': (mu, L, o1, o2), 'c': ..., 'b': ...}
for ng, (ii, swap) in mapping.items():
    pos = Dl.index.get_loc(ii)
    k = (Dl.season.values[pos], Dl.home.values[pos], Dl.away.values[pos], str(pd.Timestamp(Dl.t.values[pos]))[:16])
    i = KIX.get(k)
    if i is None: continue
    tip = pd.Timestamp(Dl.t.values[pos]); tip = (tip.tz_localize('UTC') if tip.tzinfo is None else tip).timestamp()
    for t in (21, 23):
        LT['ROWS'] = ROWS3; s3 = [r for r in series(ng, t, swap) if r[0] <= tip + 600]
        LT['ROWS'] = ROWS8; s8 = [r for r in series(ng, t, swap) if r[0] <= tip + 600]
        if len(s3) >= 1:
            MK[t][i] = dict(o=s3[0][1:], c=s3[-1][1:], b=(s8[0][1:] if s8 else None))
LT['ROWS'] = ROWS3
P(f'αγορα: χαντικαπ {len(MK[21])} ματς (Bet365 {sum(1 for v in MK[21].values() if v["b"])}) · συνολα {len(MK[23])} · σεζον {SE5}')
def rmse(v, ys, msk=None):
    m = np.isin(SEAS_, ys) & np.isfinite(v) & (msk if msk is not None else True); a = ACT if v is not None else None
    return m
def rm_h(v, ys): m = np.isin(SEAS_, ys) & np.isfinite(v); return float(np.sqrt(np.mean((ACT - v)[m] ** 2)))
def rm_t(v, ys, msk=None):
    m = np.isin(SEAS_, ys) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
def k2(x, z):
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return b, b / se
# ---------------- καθαρες προβλεψεις ----------------
HELD_H = np.full(N, np.nan); CH_H = {}
for Y in SE5:
    tr = [x for x in SE5 if x != Y]; g = min(H, key=lambda k: rm_h(H[k], tr)); CH_H[Y] = g
    m = SEAS_ == Y; HELD_H[m] = H[g][m]
RS = PH == 'RS'
GNC = np.minimum(GN, 34)            # πλει-οφ εχουν GN 99 → η καμπυλη τα βλεπει ως τελος κανονικης περιοδου
def curve_fit(v, ys):
    m = np.isin(SEAS_, ys) & np.isfinite(v) & RS; b, a = np.polyfit(GNC[m], (TOT - v)[m], 1); return a, b
RT = np.array([(PRE_T.get((SEAS_[i], HOME[i]), 0.0) + PRE_T.get((SEAS_[i], AWAY[i]), 0.0)) if GN[i] <= 10 else 0.0 for i in range(N)])
def tot_variant(g, kt, ys_fit, Y):
    v = T[g]; a, b = curve_fit(v, ys_fit)
    return v + a + b * GNC + kt * RT
HELD_T = np.full(N, np.nan); CH_T = {}
for Y in SE5:
    tr = [x for x in SE5 if x != Y]
    best = None
    for g in T:
        for kt in (0, .25, .5):
            sc = 0; vals = []
            # RMSE στις αλλες σεζον με καμπυλη που μετριεται χωρις την καθε μια (LOSO εσωτερικα: απλουστευση — καμπυλη απο τις tr)
            v = tot_variant(g, kt, tr, Y)
            sc = rm_t(v, tr)
            if best is None or sc < best[0]: best = (sc, g, kt)
    _, g, kt = best; CH_T[Y] = (g, kt)
    v = tot_variant(g, kt, tr, Y); m = SEAS_ == Y; HELD_T[m] = v[m]
# live (φουσκωμενο: σταθερη live ρυθμιση + καμπυλη απο ολες τις σεζον)
LIVEH = H[LIVE_H]
_a, _b = curve_fit(T[LIVE_T], SE5); LIVET = T[LIVE_T] + _a + _b * GNC + .25 * RT
P(''); P('################ ΚΑΘΑΡΗ ΜΗΧΑΝΗ ανα σεζον ################')
for Y in SE5: P(f'  {Y}: χαντικαπ (περσι, ειδικοι, λ, HL, εδρα, ×7ο, εγχωρια, φιλικα) = {CH_H[Y]}{"  [= live]" if CH_H[Y] == LIVE_H else ""} · συνολο (τυχη, περσι, λ, μ_w) + φιλικα = {CH_T[Y]}')
P(f'  RMSE χαντικαπ: καθαρο {rm_h(HELD_H, SE5):.3f} · live {rm_h(LIVEH, SE5):.3f} · συνολα: καθαρο {rm_t(HELD_T, SE5):.3f} · live {rm_t(LIVET, SE5):.3f}')
# ---------------- picks ----------------
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def bets(t, v, rule, book='o', msk=None):
    """t 21 χαντικαπ / 23 συνολο · rule (w, σ, κατωφλι) · book 'o'/'c'/'b' → λιστα (i, μοναδα, CLV)."""
    w, s, thr = rule; R = []
    for i, d in MK[t].items():
        if SEAS_[i] not in SE5 or not np.isfinite(v[i]) or (msk is not None and not msk[i]): continue
        row = d[book]
        if row is None: continue
        mk, L, o1, o2 = row
        if t == 21:
            pw, pp, pl = cover(mk + w * (v[i] - mk), L, s)   # L = γραμμη γηπ (−αναμ. διαφορα)
        else:
            mu = mk + w * (v[i] - mk); pw = 1 - Phi((L + (.5 if abs(L - round(L)) < 1e-9 else 0) - mu) / s)
            pl = Phi((L - (.5 if abs(L - round(L)) < 1e-9 else 0) - mu) / s); pp = 1 - pw - pl
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < thr: continue
        x = ((ACT[i] + L) if t == 21 else (TOT[i] - L)) * side
        u = (od - 1) if x > 0 else (0 if x == 0 else -1)
        R.append((i, u, (d['c'][0] - d['o'][0]) * side))
    return R
def summ(R, lab):
    u = np.array([r[1] for r in R]) if R else np.array([0.0]); ps = {Y: sum(r[1] for r in R if SEAS_[r[0]] == Y) for Y in SE5}
    order = sorted(R, key=lambda r: G['t'][r[0]]); cum = np.cumsum([r[1] for r in order]) if R else np.array([0]); dd = float(np.max(np.maximum.accumulate(cum) - cum))
    P(f'  {lab:34s} {len(R):4d} picks · ROI {u.mean()*100:+.1f}% · {u.sum():+.1f}u · θετ. {sum(v > 0 for v in ps.values())}/5 · χειροτ. {min(ps.values()):+.1f} · βυθιση {dd:.1f} · '
      + ' '.join(f'{Y[-2:]}:{v:+.1f}' for Y, v in ps.items()))
    return ps, dd
P(''); P('################ ΤΕΣΤ 1 — ΡΕΑΛΙΣΤΙΚΟ ROI σημερινου setup (κανονες live, ανοιγμα Crown) ################')
CUR_H, CUR_T = (1.0, 11.5, .08), (1.0, 16.7, .08)
summ(bets(21, LIVEH, CUR_H), 'χαντικαπ — live ρυθμιση (φουσκωμενο)'); summ(bets(21, HELD_H, CUR_H), 'χαντικαπ — ΚΑΘΑΡΟ')
summ(bets(23, LIVET, CUR_T), 'συνολα — live ρυθμιση (φουσκωμενο)'); summ(bets(23, HELD_T, CUR_T), 'συνολα — ΚΑΘΑΡΟ')
for t, v, lab in ((21, HELD_H, 'χαντικαπ'), (23, HELD_T, 'συνολα')):
    ii = [i for i in MK[t] if SEAS_[i] in SE5 and np.isfinite(v[i])]
    mc = np.array([MK[t][i]['c'][0] for i in ii]); a = (ACT if t == 21 else TOT)[ii]; m = v[ii]
    b, tt = k2(m - mc, a - mc)
    P(f'  {lab} ΚΑΘΑΡΟ: λαθος μοντελο {np.sqrt(np.mean((a - m) ** 2)):.2f} vs κλεισιμο {np.sqrt(np.mean((a - mc) ** 2)):.2f} · Κ2 b {b:+.2f} (t {tt:+.1f})')
# ---------------- ΤΕΣΤ 2 μιξη ----------------
rng = np.random.default_rng(41)
def boot_mean(Ra, Rb, key=1, n=5000):
    games = sorted({r[0] for r in Ra} | {r[0] for r in Rb}); gi = {g: k for k, g in enumerate(games)}
    va = np.full(len(games), np.nan); vb = np.full(len(games), np.nan)
    for r in Ra: va[gi[r[0]]] = r[key]
    for r in Rb: vb[gi[r[0]]] = r[key]
    w = 0
    for _ in range(n):
        s = rng.integers(0, len(games), len(games)); a, b = va[s], vb[s]
        if np.nanmean(a) > np.nanmean(b): w += 1
    return w / n
def boot_units(Ra, Rb, n=5000):
    games = sorted({r[0] for r in Ra} | {r[0] for r in Rb}); gi = {g: k for k, g in enumerate(games)}
    d = np.zeros(len(games))
    for r in Ra: d[gi[r[0]]] += r[1]
    for r in Rb: d[gi[r[0]]] -= r[1]
    bs = np.array([d[rng.integers(0, len(d), len(d))].sum() for _ in range(n)]); return float(np.mean(bs > 0))
WS = (.3, .5, .75, 1.0); TH = (.04, .06, .08, .10, .12)
for t, v, cur, prop, SS, lab in ((21, HELD_H, CUR_H, (.5, 12.3, .06), (11.5, 12.3, 13.5), 'ΧΑΝΤΙΚΑΠ'), (23, HELD_T, CUR_T, (.5, 16.7, .06), (15.0, 16.7, 18.0), 'ΣΥΝΟΛΑ')):
    P(''); P(f'################ ΤΕΣΤ 2 — ΜΙΞΗ · {lab} ################')
    Rc, Rp = bets(t, v, cur), bets(t, v, prop)
    psC, ddC = summ(Rc, 'ΣΗΜΕΡΙΝΟΣ'); psP, ddP = summ(Rp, 'ΜΙΞΗ 50/50 ≥6%')
    for ph, f in (('αγων 1-6', lambda g: g <= 6), ('αγων 7+', lambda g: g >= 7)):
        P(f'    {ph}: ' + ' · '.join(f'{nm} {len(R_)} picks {np.mean([r[1] for r in R_])*100 if R_ else 0:+.1f}% {sum(r[1] for r in R_):+.1f}u'
                                     for nm, R_ in (('σημ', [r for r in Rc if f(GN[r[0]])]), ('μιξη', [r for r in Rp if f(GN[r[0]])]))))
    # nested επιλογη κανονα
    RULES = list(itertools.product(WS, SS, TH)); ch = {}; uN = 0
    for Y in SE5:
        tr = [x for x in SE5 if x != Y]
        r_ = max(RULES, key=lambda r: sum(x[1] for x in bets(t, v, r) if SEAS_[x[0]] in tr)); ch[Y] = r_
        uN += sum(x[1] for x in bets(t, v, r_) if SEAS_[x[0]] == Y)
    P('  nested επιλογη: ' + ' · '.join(f'{Y[-2:]}:{r}' for Y, r in ch.items()) + f' → {uN:+.1f}u')
    uC, uP = sum(psC.values()), sum(psP.values())
    A_ = sum(psP[Y] > psC[Y] for Y in SE5) >= 4 and uP > uC
    B_ = sum(r[0] < 1 for r in ch.values()) >= 4 and uN > uC
    pG = boot_units(Rp, Rc); C_ = pG >= .9
    clvC, clvP = np.mean([r[2] for r in Rc]), np.mean([r[2] for r in Rp]); D_ = clvP >= clvC
    P(f'  (α) «περισσοτερα χρηματα»: Α {"✓" if A_ else "✗"} ({sum(psP[Y] > psC[Y] for Y in SE5)}/5, {uP:+.1f} vs {uC:+.1f}) · Β {"✓" if B_ else "✗"} · '
      f'Γ P {pG:.2f} {"✓" if C_ else "✗"} · Δ CLV {clvP:+.2f} vs {clvC:+.2f} {"✓" if D_ else "✗"} → {"ΠΕΡΝΑ" if A_ and B_ and C_ and D_ else "✗"}')
    p1 = boot_mean(Rp, Rc); T1 = p1 >= .9
    T2 = min(psP.values()) > min(psC.values()) and ddP < ddC
    Rb_c, Rb_p = bets(t, v, cur, 'b'), bets(t, v, prop, 'b'); p3 = boot_mean(Rb_p, Rb_c); T3 = p3 >= .8
    Rk_c, Rk_p = bets(t, v, cur, 'c'), bets(t, v, prop, 'c'); p4 = boot_mean(Rk_p, Rk_c); T4 = p4 >= .8
    p5 = boot_mean(Rp, Rc, key=2); T5 = p5 >= .9
    P('  Bet365 ανοιγμα:'); summ(Rb_c, '  σημερινος'); summ(Rb_p, '  μιξη')
    P('  Crown κλεισιμο:'); summ(Rk_c, '  σημερινος'); summ(Rk_p, '  μιξη')
    k_ = sum([T3, T4, T5])
    P(f'  (β) «ιδια χρηματα, λιγοτερο ρισκο»: Τ1 P {p1:.2f} {"✓" if T1 else "✗"} · Τ2 {"✓" if T2 else "✗"} · Τ3 Bet365 P {p3:.2f} {"✓" if T3 else "✗"} · '
      f'Τ4 κλεισιμο P {p4:.2f} {"✓" if T4 else "✗"} · Τ5 CLV P {p5:.2f} {"✓" if T5 else "✗"} → {"ΠΕΡΝΑ" if T1 and T2 and k_ >= 2 else "✗"}')
# ---------------- ΤΕΣΤ 3 συνολα: μηχανισμοι ----------------
P(''); P('################ ΤΕΣΤ 3 — ΣΥΝΟΛΑ: ΜΗΧΑΝΙΣΜΟΙ πανω στην καθαρη βαση ################')
A = {}
src = open('el_clean_grid.py', encoding='utf-8').read().split("# ---------- χαντικαπ ----------")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
exec(src, A)
MAPd = A['find'](A['A'], 'MAP')
_k0 = next(iter(MAPd)) if MAPd else None
P(f'  MAP: {len(MAPd) if MAPd else 0} εγγραφες · π.χ. {_k0} → {MAPd.get(_k0) if MAPd else None}')
assert MAPd and isinstance(_k0, tuple) and len(MAPd[_k0]) == 3, 'λαθος MAP'
DOMJ = json.load(open('bk_domestic.json', encoding='utf-8'))
LGG, TMG = collections.defaultdict(list), collections.defaultdict(list)
for k_, v_ in DOMJ.items():
    L_, sea = k_.split('_')
    for g in v_['games']:
        try: tt = int(g[4]) + int(g[5])
        except Exception: continue
        ts = pd.Timestamp(g[1]); ts = (ts.tz_localize(None) if ts.tzinfo else ts).timestamp()
        LGG[(L_, sea)].append((ts, tt))
        for tid in (g[2], g[3]): TMG[(L_, sea, int(tid))].append((ts, tt))
FULLM = {k: np.mean([x[1] for x in v]) for k, v in LGG.items() if len(v) >= 20}
TSX = np.array([pd.Timestamp(x).tz_localize(None).timestamp() if pd.Timestamp(x).tzinfo is None else pd.Timestamp(x).tz_localize(None).timestamp() for x in G['t']])
def prevsea(s): a = int(s[:2]); return f'{(a - 1) % 100:02d}-{a % 100:02d}'
FT = np.zeros(N); FL = np.zeros(N); nmap = 0
for i in range(N):
    for c in (HOME[i], AWAY[i]):
        m = MAPd.get((SEAS_[i], c)) if MAPd else None
        if not m: continue
        es, tid, L_ = m; y = int(es[1:]); sea = f'{y % 100:02d}-{(y + 1) % 100:02d}'; ps = prevsea(sea)
        lg = [x[1] for x in LGG.get((L_, sea), []) if x[0] < TSX[i] - 3600]
        lgm = np.mean(lg) if len(lg) >= 20 else FULLM.get((L_, ps), np.nan)
        tg = [x[1] for x in TMG.get((L_, sea, int(tid)), []) if x[0] < TSX[i] - 3600]
        tp = [x[1] for x in TMG.get((L_, ps, int(tid)), [])]
        dprev = (np.mean(tp) - FULLM[(L_, ps)]) if len(tp) >= 10 and (L_, ps) in FULLM else 0.0
        n_ = len(tg); dcur = (np.mean(tg) - lgm) if n_ and np.isfinite(lgm) else 0.0
        FT[i] += (n_ * dcur + 6 * .5 * dprev) / (n_ + 6)
        allm = [np.mean([x[1] for x in vv]) for (LL, ss), vv in LGG.items() if ss == sea and len(vv) >= 20]
        if np.isfinite(lgm) and allm: FL[i] += lgm - float(np.mean(allm))
        nmap += 1
P(f'  εγχωρια αντιστοιχιση: {nmap} ομαδες-ματς · sd ταση {FT[np.isin(SEAS_, SE5)].std():.1f} · sd επιπεδο {FL[np.isin(SEAS_, SE5)].std():.1f}')
SY = np.array([int(s[1:]) for s in SEAS_])
RES = TOT - HELD_T
V = np.zeros(N)
for i in range(N):
    msk = (HOME == HOME[i]) & (SY < SY[i]) & np.isfinite(RES); n_ = msk.sum()
    if n_: V[i] = RES[msk].sum() / (n_ + 15)
def loso3(feat, ks, lab):
    PR = {k: HELD_T + k * feat for k in ks}; held = np.full(N, np.nan); ch = []
    for Y in SE5:
        tr = [x for x in SE5 if x != Y]; k = min(PR, key=lambda k: rm_t(PR[k], tr)); ch.append(k); held[SEAS_ == Y] = PR[k][SEAS_ == Y]
    d = [rm_t(held, [Y]) - rm_t(HELD_T, [Y]) for Y in SE5]
    ok = sum(x < 0 for x in d) >= 4
    P(f'  {lab:36s} {rm_t(HELD_T, SE5):.3f} → {rm_t(held, SE5):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.2f}' for Y, x in zip(SE5, d)) + f' → {sum(x < 0 for x in d)}/5 · επιλογες {ch}' + ('  <- ΑΛΛΑΓΗ' if ok else '  <- ✗'))
    return held, ok
H1 = loso3(FT, (0, .2, .4), 'φετινα εγχωρια σκορ (απο 1ο)')
H2 = loso3(FL, (0, .25), 'επιπεδο πρωταθληματος')
H3 = loso3(V, (0, .5, 1.0), 'εδρα «ψηλων συνολων»')
LLs = {}
for s in (14.0, 15.0, 16.7, 18.0, 20.0):
    a_ = []
    for i, d in MK[23].items():
        if SEAS_[i] not in SE5 or not np.isfinite(HELD_T[i]): continue
        mk, L, o1, o2 = d['o']; x = TOT[i] - L
        if x == 0: continue
        po = 1 - Phi((L - HELD_T[i]) / s); a_.append(-math.log(max(po if x > 0 else 1 - po, 1e-9)))
    LLs[s] = np.mean(a_)
P('  βαθμονομηση σ (log-loss, μοντελο μονο): ' + ' · '.join(f'σ {s}: {v:.4f}' for s, v in LLs.items()) + f' → καλυτερο {min(LLs, key=LLs.get)}')
NEWT = HELD_T.copy()
for (h_, ok), feat in ((H1, FT), (H2, FL), (H3, V)):
    if ok: NEWT = h_ if np.array_equal(NEWT, HELD_T) else NEWT + (h_ - HELD_T)
if not np.array_equal(NEWT, HELD_T):
    summ(bets(23, NEWT, CUR_T), 'συνολα ΝΕΟ (ο,τι περασε) ≥8%'); summ(bets(23, HELD_T, CUR_T), 'συνολα καθαρη βαση ≥8%')
# ---------------- ΤΕΣΤ 4 διακυβευμα ----------------
P(''); P('################ ΤΕΣΤ 4 — ΔΙΑΚΥΒΕΥΜΑ ################')
order = np.argsort(TSX); rec = {}; DEC = np.zeros(N); ntot = {}
for Y in set(SEAS_):
    s = np.where((SEAS_ == Y) & RS)[0]
    for c in set(HOME[s]) | set(AWAY[s]): ntot[(Y, c)] = int(((HOME[s] == c) | (AWAY[s] == c)).sum())
for i in order:
    if not RS[i]: continue
    Y = SEAS_[i]
    for c in (HOME[i], AWAY[i]):
        w_, n_ = rec.get((Y, c), (0, 0)); left = ntot.get((Y, c), 99) - n_
        if left <= 5 and n_ >= 10 and (w_ / n_ <= .3 or w_ / n_ >= .75): DEC[i] += 1
    hw = ACT[i] > 0
    rec[(Y, HOME[i])] = (rec.get((Y, HOME[i]), (0, 0))[0] + hw, rec.get((Y, HOME[i]), (0, 0))[1] + 1)
    rec[(Y, AWAY[i])] = (rec.get((Y, AWAY[i]), (0, 0))[0] + (not hw), rec.get((Y, AWAY[i]), (0, 0))[1] + 1)
PO = ~RS
def flagtest(lab, sel, t):
    v = HELD_H if t == 21 else HELD_T; tgt = ACT if t == 21 else TOT
    for nm, base in (('vs ΚΛΕΙΣΙΜΟ', {i: d['c'][0] for i, d in MK[t].items()}), ('vs ΜΟΝΤΕΛΟ', None)):
        ii = [i for i in range(N) if sel[i] and SEAS_[i] in SE5 and np.isfinite(v[i]) and (base is None or i in base)]
        if len(ii) < 15: P(f'  {lab} {nm}: λιγα ({len(ii)})'); continue
        r = np.array([tgt[i] - (base[i] if base is not None else v[i]) for i in ii]); ss = SEAS_[ii]
        per = [r[ss == Y].mean() for Y in SE5 if (ss == Y).sum() >= 3]; m = r.mean(); se = r.std() / math.sqrt(len(r))
        same = sum(np.sign(p) == np.sign(m) for p in per); fl = abs(m / se) >= 2 and same >= 4 and abs(m) >= 1
        P(f'  {lab:40s} {nm:12s} n {len(ii):4d} · μεσο υπολοιπο {m:+.2f} (t {m/se:+.1f}, ιδιο προσημο {same}/{len(per)})' + ('  ← ' + ('Η ΑΓΟΡΑ ΤΟ ΧΑΝΕΙ' if base is not None else 'ΤΟ ΜΟΝΤΕΛΟ ΤΟ ΧΑΝΕΙ') if fl else ''))
P('  (χαντικαπ: υπολοιπο απο τη μερια του γηπεδουχου)')
flagtest('κριμενη ομαδα (5 τελευταιες) — χαντικαπ', DEC > 0, 21); flagtest('κριμενη ομαδα (5 τελευταιες) — συνολο', DEC > 0, 23)
flagtest('πλει-οφ / F4 — χαντικαπ', PO, 21); flagtest('πλει-οφ / F4 — συνολο', PO, 23)
for t, lab in ((21, 'χαντικαπ'), (23, 'συνολα')):
    v = HELD_H if t == 21 else HELD_T; R = bets(t, v, CUR_H if t == 21 else CUR_T)
    for nm, f in (('κριμενη ομαδα', lambda i: DEC[i] > 0), ('πλει-οφ/F4', lambda i: PO[i]), ('υπολοιπα', lambda i: DEC[i] == 0 and not PO[i])):
        R_ = [r for r in R if f(r[0])]; u = [r[1] for r in R_]
        P(f'  ROI {lab} {nm:14s}: {len(u)} picks · {np.mean(u)*100 if u else 0:+.1f}% · {sum(u):+.1f}u')
open('el_clean_tests_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
