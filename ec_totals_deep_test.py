# -*- coding: utf-8 -*-
"""ec_totals_deep_test.py — EuroCup ΣΥΝΟΛΑ: ΒΑΘΙΑ ΑΝΑΛΥΣΗ (5/10/2026, Στελιος «τρεξ' τα ολα, θελω βαθια αναλυση, που μενουμε πισω, τι χανουμε»).
ΒΑΣΗ Β* = καλυτερη του ec_totals_mech_test: μηχανη v2 λ8 + φετινα εγχωρια σκορ κd .4 + επιπεδο πρωταθληματος κl .25 + καμπυλη σεζον (LOSO).
ΜΗΧΑΝΙΣΜΟΙ πανω στη Β* (LOSO 8 σεζον U2018-25, RMSE συνολου· ΑΛΛΑΓΗ αν καλυτερο απο Β* σε ≥80% των σεζον ΠΟΥ ΕΧΟΥΝ το δεδομενο):
  Ν1 ΕΓΧΩΡΙΟΣ ΡΥΘΜΟΣ (κατοχες, box Flashscore, μονο U2020+ → χρειαζεται 5/6): κp·2.2·Σ(αποκλιση κατοχων)
  Ν2 ΕΓΧΩΡΙΑ ΕΠΙΘΕΣΗ/ΑΜΥΝΑ χωριστα (ποντοι/100 κατοχες, U2020+ → 5/6): κe·.72·Σ(επιθ + αμυν αποκλιση) — μαζι με/αντι του κd
  Ν3 ΦΙΛΙΚΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ στα συνολα (οπως Ευρωλιγκα: r_T = Σ(συνολο − μ_φιλικων − τ_ομ − τ_αντ)/(n+4), αγων 1-10, U2021+ → 4/5): κT {0,.1,.25,.4}
  Ν4-Ν8 ΣΥΝΘΗΚΕΣ (ξεκουραση, εγχωριο ≤2 μερες μετα, ματς χωρις διακυβευμα, νοκ-αουτ, εδρα «ψηλων συνολων»): υπολοιπο vs ΚΛΕΙΣΙΜΟ και vs Β*
     → «η αγορα τον χανει» αν |t| ≥ 2 ΚΑΙ ιδιο προσημο ≥4/6 ΚΑΙ ≥0.5 π.· «το μοντελο τον χανει» ιδιο κριτηριο vs Β*
  Ν9 ΠΑΡΑΤΑΣΕΙΣ: ποσο κοστιζουν (μοντελο = 40′) και αν η αγορα τις εχει
  Ν10 ΜΙΞΗ/σ ειδικα για συνολα: log-loss καλυψης στο ΑΝΟΙΓΜΑ, w × σ, LOSO 6 σεζον → ΑΛΛΑΓΗ αν καλυτερο απο (.5, 16.7) σε ≥4/6
ΔΙΑΓΝΩΣΗ «ΠΟΥ ΜΕΝΟΥΜΕ ΠΙΣΩ» (Β* vs αγορα Crown U2020-25): ανα φαση, νεες/παλιες ομαδες, πρωταθλημα, υψος γραμμης, ρυθμος vs αποδοτικοτητα.
Εξοδος: ec_totals_deep_out.txt"""
import sys, io, json, math, itertools, collections, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
M = {'__name__': 'm'}
exec(open('ec_totals_mech_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_mech_out.txt', 'w', encoding='utf-8')", "open('_unused_tm.txt', 'w', encoding='utf-8')"), M)
D, TOT, GN, seasn, MKT, TP, FT, FL = (M[k] for k in ('D', 'TOT', 'GN', 'seasn', 'MKT', 'TP', 'FT', 'FL'))
EC = M['EC']; INNER = M['INNER']; MAPD, DOMNS = M['MAPD'], M['DOMNS']
EVM, EV8, curve_fold, k2, cov = M['EVM'], M['EV8'], M['curve_fold'], M['k2'], M['cov']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf; NN = NormalDist()
TS = M['TS']
def with_curve(v):
    w = v.copy()
    for Y in EV8 + ['U2017']:
        a, b = curve_fold(v, Y); m = seasn == Y; w[m] = v[m] + a + b * GN[m]
    return w
BSTAR_RAW = TP['v2 λ8'] + .4 * FT + .25 * FL
BSTAR = with_curve(BSTAR_RAW)
def rm(v, ss, msk=None):
    m = np.isin(seasn, ss) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
P(f'Β* RMSE U2018-25 {rm(BSTAR, EV8):.3f} (live {rm(M["PRED"][M["BASE"]], EV8):.3f})')
# =============== Flashscore κωδικος ομαδας ανα σεζον EC ===============
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
FSID = {}
ix2 = collections.defaultdict(list)
for i in range(len(D)): ix2[(seasn[i], int(D.hs.values[i]), int(D.as_.values[i]))].append(i)
for i_y in range(2016, 2027):
    Y = f'U{i_y}'
    for e in FG.get(f'EC_{i_y}', []):
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        if not e.get('ts'): continue
        for i in ix2.get((Y, hs, as_), []):
            if abs(TS[i] - e['ts']) <= 2 * 86400:
                FSID[(Y, D.home.values[i])] = e['hid']; FSID[(Y, D.away.values[i])] = e['aid']; break
P(f'αντιστοιχιση Flashscore: {len(FSID)} ομαδες-σεζον · ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in FSID if k[0] == Y)}/{len(set(D[D.season == Y].home))}' for Y in EV8))
# =============== Ν1/Ν2 εγχωρια box: ρυθμος, επιθεση, αμυνα ===============
BOX = {}
for ln in open('fs_bk_stats.jsonl', encoding='utf-8'):
    r = json.loads(ln); st = r['stats']
    def g(k, j):
        try: return float(str((st.get(k) or [None, None])[j]).replace('%', ''))
        except Exception: return None
    p = [None, None]
    for j in (0, 1):
        v = [g('Field goals attempts', j), g('Free throws attempts', j), g('Offensive rebounds', j), g('Turnovers', j)]
        if all(x is not None for x in v): p[j] = v[0] + .44 * v[1] - v[2] + v[3]
    if p[0] and p[1] and (p[0] + p[1]) / 2 >= 50: BOX[r['id']] = (p[0] + p[1]) / 2
DOMLG = {'ABA', 'ACB', 'BBL', 'GBL', 'ISR', 'LBA', 'LKL', 'LNB', 'TBL', 'VTB'}
TG = collections.defaultdict(list); LGG = collections.defaultdict(list)   # (fsid, y) → [(ts, poss, ortg, drtg)] · (lg, y) → [(ts, poss, eff)]
for k, L in FG.items():
    lg, y = k.split('_'); y = int(y)
    if lg not in DOMLG: continue
    for e in L:
        ps = BOX.get(e['id'])
        if not ps or not e.get('ts'): continue
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        oh, oa = 100 * hs / ps, 100 * as_ / ps
        TG[(e['hid'], y)].append((e['ts'], ps, oh, oa)); TG[(e['aid'], y)].append((e['ts'], ps, oa, oh))
        LGG[(lg, y)].append((e['ts'], ps, (oh + oa) / 2))
TEAMLG = {}
for k, L in FG.items():
    lg, y = k.split('_')
    if lg in DOMLG:
        for e in L: TEAMLG[(e.get('hid'), int(y))] = lg; TEAMLG[(e.get('aid'), int(y))] = lg
def full_dev(fs, y):
    L = TG.get((fs, y), []); lg = TEAMLG.get((fs, y))
    if len(L) < 10 or not lg or not LGG.get((lg, y)): return None
    lp = np.mean([x[1] for x in LGG[(lg, y)]]); le = np.mean([x[2] for x in LGG[(lg, y)]])
    return (np.mean([x[1] for x in L]) - lp, np.mean([x[2] for x in L]) - le, np.mean([x[3] for x in L]) - le)
def box_feats(i, c):
    Y = seasn[i]; y = int(Y[1:]); fs = FSID.get((Y, c))
    if not fs: return None
    lg = TEAMLG.get((fs, y)) or TEAMLG.get((fs, y - 1))
    L = [x for x in TG.get((fs, y), []) if x[0] < TS[i] - 3600]
    lgL = [x for x in LGG.get((lg, y), []) if x[0] < TS[i] - 3600] if lg else []
    prev = full_dev(fs, y - 1)
    if len(lgL) < 20 and not prev: return None
    n = len(L)
    if n and len(lgL) >= 20:
        lp = np.mean([x[1] for x in lgL]); le = np.mean([x[2] for x in lgL])
        cur = (np.mean([x[1] for x in L]) - lp, np.mean([x[2] for x in L]) - le, np.mean([x[3] for x in L]) - le)
    else: cur, n = (0, 0, 0), 0
    pv = prev or (0, 0, 0)
    return tuple((n * c_ + 6 * .5 * p_) / (n + 6) for c_, p_ in zip(cur, pv))
FPp = np.zeros(len(D)); FEp = np.zeros(len(D)); HASB = np.zeros(len(D), bool)
for i in range(len(D)):
    bh, ba = box_feats(i, D.home.values[i]), box_feats(i, D.away.values[i])
    if bh is None or ba is None: continue
    HASB[i] = True; FPp[i] = 2.2 * (bh[0] + ba[0]); FEp[i] = .72 * (bh[1] + bh[2] + ba[1] + ba[2])
P(f'εγχωρια box (και οι 2 ομαδες): ' + ' '.join(f'{Y[-2:]}:{(HASB & (seasn == Y)).mean() / max((seasn == Y).mean(), 1e-9):.0%}' for Y in EV8)
  + f' · sd ρυθμου {FPp[HASB].std():.1f} π. · sd επιθ/αμυν {FEp[HASB].std():.1f} π.')
# =============== Ν3 φιλικα στα συνολα ===============
PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
def tau_prev(y):
    rows = []
    for k, L in FG.items():
        lg, yy = k.split('_')
        if int(yy) != y: continue
        for e in L:
            try: tt = int(e['hs']) + int(e['as_'])
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], lg, tt))
    if not rows: return {}
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; lgs = sorted({r[2] for r in rows}); il = {l: i for i, l in enumerate(lgs)}
    n, nl, k = len(teams), len(lgs), len(rows)
    A = np.zeros((k + n, n + nl)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = 1; A[r_, [n + il[r[2]] for r in rows]] = 1; b[:k] = [r[3] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(3)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}
RT = {}
for i_y in range(2020, 2026):
    Y = f'U{i_y}'; sub = np.where(seasn == Y)[0]
    if not len(sub): continue
    start = min(TS[sub]); C = tau_prev(i_y - 1); lo = dt.datetime(i_y, 8, 1).timestamp()
    rev = {fs: code for (YY, code), fs in FSID.items() if YY == Y}
    res, mine = [], collections.defaultdict(list)
    for k, L in PS.items():
        for e in L:
            if not e.get('ts') or not (lo <= e['ts'] < start): continue
            try: tt = int(e['hs']) + int(e['as_'])
            except Exception: continue
            h, a = e.get('hid'), e.get('aid')
            if h not in C or a not in C: continue
            r0 = tt - C[h] - C[a]; res.append(r0)
            for me in (h, a):
                if me in rev: mine[rev[me]].append(r0)
    if len(res) < 20: continue
    mu = float(np.mean(res))
    for code, L in mine.items(): RT[(Y, code)] = sum(x - mu for x in L) / (len(L) + 4)
FRT = np.array([(RT.get((seasn[i], D.home.values[i]), 0) + RT.get((seasn[i], D.away.values[i]), 0)) if GN[i] <= 9 else 0.0 for i in range(len(D))])
P(f'φιλικα (r_T): ομαδες ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in RT if k[0] == Y)}' for Y in EV8) + f' · sd σηματος αγων 1-10 {FRT[(GN <= 9) & (FRT != 0)].std():.1f} π.')
# =============== LOSO μηχανισμων Ν1-Ν3 ===============
def loso(PRED, keys, base_key, lab, ys_crit):
    held = np.full(len(D), np.nan); ch = []
    for Y in EV8:
        tr = [x for x in EV8 if x != Y]; k = min(keys, key=lambda k: rm(PRED[k], tr)); ch.append(k)
        m = seasn == Y; held[m] = PRED[k][m]
    d = {Y: rm(held, [Y]) - rm(PRED[base_key], [Y]) for Y in EV8}
    need = math.ceil(.8 * len(ys_crit)); nb = sum(d[Y] < 0 for Y in ys_crit); ok = nb >= need
    P(f'  {lab:40s} {rm(PRED[base_key], EV8):.3f} → {rm(held, EV8):.3f} · ' + ' '.join(f'{Y[-2:]}:{d[Y]:+.2f}' for Y in EV8)
      + f' → {nb}/{len(ys_crit)} (χρειαζεται {need})' + ('  <- ΑΛΛΑΓΗ' if ok else '  <- ✗'))
    P(f'     επιλογες: {collections.Counter(ch).most_common(3)}')
    return held, ok, collections.Counter(ch).most_common(1)[0][0]
P(''); P('################ Ν1-Ν3 ΜΗΧΑΝΙΣΜΟΙ ΠΑΝΩ ΣΤΗ Β* ################')
KP = (0, .2, .35, .5, .7); KE = (0, .2, .35, .5, .7); KDs = (0, .4)
PR = {}
for kd, kp, ke in itertools.product(KDs, KP, KE):
    PR[('box', kd, kp, ke)] = with_curve(TP['v2 λ8'] + kd * FT + .25 * FL + kp * FPp + ke * FEp)
BK = ('box', .4, 0, 0)
Y6 = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']; Y5 = Y6[1:]
P('  in-sample U2020-25 (κd .4 | κd 0) ανα κp (κe 0): ' + ' · '.join(f'{kp}: {rm(PR[("box", .4, kp, 0)], Y6):.3f} | {rm(PR[("box", 0, kp, 0)], Y6):.3f}' for kp in KP))
P('  in-sample U2020-25 (κd .4 | κd 0) ανα κe (κp 0): ' + ' · '.join(f'{ke}: {rm(PR[("box", .4, 0, ke)], Y6):.3f} | {rm(PR[("box", 0, 0, ke)], Y6):.3f}' for ke in KE))
P(f'  ελεγχος: συσχετιση εγχωριου ρυθμου με (πραγμ − Β*) {np.corrcoef(FPp[HASB], (TOT - BSTAR)[HASB])[0, 1]:+.3f} · επιθ/αμυν {np.corrcoef(FEp[HASB], (TOT - BSTAR)[HASB])[0, 1]:+.3f} · με την εγχωρια ταση κd (FT) {np.corrcoef(FPp[HASB] + FEp[HASB], FT[HASB])[0, 1]:+.2f}')
H1 = loso(PR, [k for k in PR if k[3] == 0], BK, 'Ν1 εγχωριος ρυθμος', Y6)
H2 = loso(PR, list(PR), BK, 'Ν2 εγχωρια επιθεση/αμυνα (+ρυθμος, ±κd)', Y6)
PT = {kt: with_curve(TP['v2 λ8'] + .4 * FT + .25 * FL + kt * FRT) for kt in (0, .1, .25, .4)}
H3 = loso(PT, list(PT), 0, 'Ν3 φιλικα στα συνολα (αγων 1-10)', Y5)
P('  Ν3 αγων 1-10 μονο: ' + ' · '.join(f'κT {k}: {rm(v, EV8, GN <= 9):.3f}' for k, v in PT.items()))
# =============== Ν4-Ν8 συνθηκες ===============
P(''); P('################ Ν4-Ν8 ΣΥΝΘΗΚΕΣ ΤΟΥ ΜΑΤΣ (συνολα) ################')
DOM = DOMNS['DOM']; domdates = {}
for key, v in DOM.items():
    L, sea = key.split('_')
    for g in v['games']:
        t = pd.Timestamp(g[1]).tz_localize(None).timestamp()
        for tid in (g[2], g[3]): domdates.setdefault((L, sea, int(tid)), []).append(t)
ecd = collections.defaultdict(list)
for i in range(len(D)):
    for c in (D.home.values[i], D.away.values[i]): ecd[(seasn[i], c)].append(TS[i])
def sched(i, c):
    m = MAPD.get((seasn[i], c)); dd = []
    if m:
        y = int(m[0][1:]); dd = domdates.get((m[2], f'{y % 100:02d}-{(y + 1) % 100:02d}', int(m[1])), [])
    prev = [x for x in ecd[(seasn[i], c)] + dd if x < TS[i] - 3600]; nxt = [x for x in dd if x > TS[i] + 3600]
    return (min(7, (TS[i] - max(prev)) / 86400) if prev else 7.0), (min(7, (min(nxt) - TS[i]) / 86400) if nxt else 7.0)
rs_total = {}
for Y in set(seasn):
    s = D[(D.season == Y) & (D.phase == 'RS')]
    for c in set(s.home) | set(s.away): rs_total[(Y, c)] = int(((s.home == c) | (s.away == c)).sum())
rec = {}; DEAD = np.zeros(len(D)); ACTM = (D.hs - D.as_).values
for i in np.argsort(TS):
    Y = seasn[i]; h, a = D.home.values[i], D.away.values[i]
    if D.phase.values[i] == 'RS':
        for c in (h, a):
            w_, n_ = rec.get((Y, c), (0, 0)); left = rs_total.get((Y, c), 99) - n_
            if left <= 3 and n_ >= 5 and (w_ / n_ <= .3 or w_ / n_ >= .8): DEAD[i] += 1
        hw = ACTM[i] > 0
        rec[(Y, h)] = (rec.get((Y, h), (0, 0))[0] + hw, rec.get((Y, h), (0, 0))[1] + 1); rec[(Y, a)] = (rec.get((Y, a), (0, 0))[0] + (not hw), rec.get((Y, a), (0, 0))[1] + 1)
REST = np.zeros(len(D)); NEXTD = np.zeros(len(D))
for i in range(len(D)):
    rh, nh = sched(i, D.home.values[i]); ra, na = sched(i, D.away.values[i]); REST[i] = rh + ra; NEXTD[i] = (nh <= 2.2) + (na <= 2.2)
KO = (D.phase.values != 'RS').astype(float)
MC = np.full(len(D), np.nan); MO = np.full(len(D), np.nan)
for i in MKT: MC[i] = MKT[i]['c'][1]; MO[i] = MKT[i]['o'][1]
def factor(name, x, cont):
    ii = np.array([i for i in MKT if seasn[i] in EVM and np.isfinite(BSTAR[i]) and np.isfinite(x[i])])
    cells = []; flags = []
    for lab, base in (('vs ΚΛΕΙΣΙΜΟ', MC), ('vs Β*', BSTAR)):
        r = TOT[ii] - base[ii]; xx = x[ii]
        if cont:
            b = np.polyfit(xx, r, 1)[0]; rr = r - np.polyval(np.polyfit(xx, r, 1), xx); se = math.sqrt(np.sum(rr ** 2) / (len(xx) - 2) / np.sum((xx - xx.mean()) ** 2))
            per = [np.polyfit(xx[seasn[ii] == Y], r[seasn[ii] == Y], 1)[0] for Y in EVM if (seasn[ii] == Y).sum() >= 20]; eff = b * xx.std(); n = len(ii)
        else:
            sel = xx > 0; v = r[sel] - r[~sel].mean(); b = v.mean(); se = r[sel].std() / math.sqrt(max(sel.sum(), 1))
            per = [r[sel & (seasn[ii] == Y)].mean() - r[~sel & (seasn[ii] == Y)].mean() for Y in EVM if (sel & (seasn[ii] == Y)).sum() >= 3]; eff = b; n = int(sel.sum())
        same = sum(np.sign(p) == np.sign(b) for p in per)
        cells.append(f'{lab} {b:+.2f} (t {b/se:+.1f}, ιδιο προσημο {same}/{len(per)})')
        if abs(b / se) >= 2 and same >= 4 and abs(eff) >= .5: flags.append('Η ΑΓΟΡΑ ΤΟΝ ΧΑΝΕΙ' if lab == 'vs ΚΛΕΙΣΙΜΟ' else 'ΤΟ ΜΟΝΤΕΛΟ ΤΟΝ ΧΑΝΕΙ')
    P(f'  {name:46s} n {n:4d} · ' + ' · '.join(cells) + (('  ← ' + ' & '.join(flags)) if flags else ''))
factor('Ν4 ξεκουραση (μερες, γηπ+φιλ)', REST, True)
factor('Ν5 εγχωριο ≤2 μερες μετα (πληθος ομαδων)', NEXTD, True)
factor('Ν6 ματς «χωρις διακυβευμα» (≥1 ομαδα)', (DEAD > 0).astype(float), False)
factor('Ν7 νοκ-αουτ / πλει-οφ', KO, False)
# Ν8 εδρα «ψηλων συνολων»: σταθεροτητα υπολοιπου γηπεδουχου απο σεζον σε σεζον
res_home = collections.defaultdict(list)
for i in range(len(D)):
    if np.isfinite(BSTAR[i]) and seasn[i] in EV8: res_home[(seasn[i], D.home.values[i])].append(TOT[i] - BSTAR[i])
pairs = [(np.mean(v), np.mean(res_home[(f'U{int(Y[1:]) - 1}', c)])) for (Y, c), v in res_home.items() if (f'U{int(Y[1:]) - 1}', c) in res_home and len(v) >= 5 and len(res_home[(f'U{int(Y[1:]) - 1}', c)]) >= 5]
pa = np.array(pairs)
P(f'  Ν8 εδρα «ψηλων συνολων»: συσχετιση υπολοιπου εδρας με την περσινη της {np.corrcoef(pa[:, 0], pa[:, 1])[0, 1]:+.2f} (n {len(pa)} ζευγη· 0 = τυχη)')
# =============== Ν9 παρατασεις ===============
OT = D.gmin.values > 40.5
iiM = np.array([i for i in MKT if seasn[i] in EVM])
P(''); P(f'################ Ν9 ΠΑΡΑΤΑΣΕΙΣ ################')
P(f'  ματς με παραταση {OT[iiM].mean():.1%} · ποντοι παραπανω σε αυτα (πραγμ − κλεισ.) {np.mean((TOT - MC)[iiM][OT[iiM]]):+.1f} · χωρις παραταση {np.mean((TOT - MC)[iiM][~OT[iiM]]):+.2f}'
  f' · Β* χωρις παραταση {np.mean((TOT - BSTAR)[iiM][~OT[iiM]]):+.2f} · Β* ολα {np.mean((TOT - BSTAR)[iiM]):+.2f}')
# =============== Ν10 μιξη/σ για συνολα ===============
P(''); P('################ Ν10 ΜΙΞΗ/σ ΓΙΑ ΣΥΝΟΛΑ (log-loss ανοιγματος, Β*) ################')
WS = (.3, .4, .5, .6, .8, 1.0); SS = (13.5, 15.0, 16.7, 18.0, 19.5)
LL = {}
for w in WS:
    for s in SS:
        arr = []
        for i in iiM:
            T, mk, oo, ou = MKT[i]['o']; v = TOT[i] - T
            if v == 0 or not np.isfinite(BSTAR[i]): continue
            po, pq, pu = cov(mk + w * (BSTAR[i] - mk), T, s); q = po / (po + pu) if v > 0 else pu / (po + pu)
            arr.append((-math.log(max(q, 1e-9)), seasn[i]))
        LL[(w, s)] = arr
mean = lambda k, ys: float(np.mean([q[0] for q in LL[k] if q[1] in ys]))
P('  ανα w (καλυτερο σ): ' + ' · '.join(f'{w}: {min(mean((w, s), EVM) for s in SS):.4f}/σ{min(SS, key=lambda s: mean((w, s), EVM))}' for w in WS) + f' · σημερινη ρυθμιση (.5, 16.7) {mean((.5, 16.7), EVM):.4f}')
ch, d = [], []
for Y in EVM:
    tr = [x for x in EVM if x != Y]; k = min(LL, key=lambda k: mean(k, tr)); ch.append(k); d.append(mean(k, [Y]) - mean((.5, 16.7), [Y]))
okM = sum(x < 0 for x in d) >= 4
P(f'  LOSO {ch} · ' + ' '.join(f'{Y[-2:]}:{x:+.4f}' for Y, x in zip(EVM, d)) + f' → {sum(x < 0 for x in d)}/6' + ('  <- ΑΛΛΑΓΗ' if okM else '  <- ✗'))
wb, sb = collections.Counter(ch).most_common(1)[0][0] if okM else (.5, 16.7)
def roi_tab(v, w, s, lab):
    for per, f in (('ολη', lambda g: g >= 0), ('1-6', lambda g: g <= 5), ('7+', lambda g: g >= 6)):
        cells = []
        for thr in (.03, .06, .09):
            R = {'over': [], 'under': []}
            for i in iiM:
                if not np.isfinite(v[i]) or not f(GN[i]): continue
                T, mk, oo, ou = MKT[i]['o']; po, pq, pu = cov(mk + w * (v[i] - mk), T, s); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
                if max(eo, eu) >= thr:
                    ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
                    R['over' if ov else 'under'].append(((od - 1) if q > 0 else (0 if q == 0 else -1), seasn[i]))
            c2 = []
            for sd_, L in R.items():
                a = np.array([x[0] for x in L]); pos = sum(1 for Y in EVM if [x for x in L if x[1] == Y] and np.mean([x[0] for x in L if x[1] == Y]) > 0)
                c2.append(f'{sd_} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {pos}/6)')
            cells.append(f'≥{thr:.0%}: ' + ' / '.join(c2))
        P(f'  {lab} {per:4s} ' + ' · '.join(cells))
roi_tab(BSTAR, wb, sb, f'ROI ανοιγμα Β* μιξη w{wb} σ{sb}')
# =============== ΤΕΛΙΚΟ μοντελο (ο,τι περασε) ===============
FIN = BSTAR.copy(); used = ['Β*']
if H1[1] or H2[1]:
    k = (H2 if H2[1] else H1)[2]; FIN = PR[k]; used.append(f'box {k}')
if H3[1]:
    FIN = FIN + H3[2] * FRT; used.append(f'φιλικα κT {H3[2]}')
P(''); P(f'################ ΤΕΛΙΚΟ ({" + ".join(used)}) vs ΑΓΟΡΑ ################')
def edge_tab(v, lab):
    for per, f in (('ολη η σεζον', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
        ii = [i for i in iiM if np.isfinite(v[i]) and f(GN[i])]
        mc = MC[ii]; a = TOT[ii]; m = v[ii]; ss = seasn[ii]
        b, t = k2(m - mc, a - mc); pers = [np.polyfit((m - mc)[ss == Y], (a - mc)[ss == Y], 1)[0] for Y in EVM if (ss == Y).sum() > 20]
        P(f'  [{lab}] {per:12s} λαθος μοντ. {np.sqrt(np.mean((a - m) ** 2)):.2f} / ανοιγμα {np.sqrt(np.mean((a - MO[ii]) ** 2)):.2f} / κλεισ. {np.sqrt(np.mean((a - mc) ** 2)):.2f}'
          f' · Κ2 b {b:+.2f} (t {t:+.1f}, θετ. {sum(x > 0 for x in pers)}/{len(pers)})')
edge_tab(M['PRED'][M['BASE']], 'live σημερα')
edge_tab(BSTAR, 'Β*')
if len(used) > 1: edge_tab(FIN, 'ΤΕΛΙΚΟ')
# =============== ΔΙΑΓΝΩΣΗ: που μενουμε πισω ===============
P(''); P('################ ΔΙΑΓΝΩΣΗ — ΠΟΥ ΜΕΝΟΥΜΕ ΠΙΣΩ (ΤΕΛΙΚΟ vs αγορα κλεισιματος, U2020-25) ################')
V = FIN
def gap(lab, sel):
    ii = iiM[sel[iiM]]; ii = ii[np.isfinite(V[ii])]
    if len(ii) < 25: return
    a = TOT[ii]; m = V[ii]; mc = MC[ii]
    b, t = k2(m - mc, a - mc) if len(ii) > 40 else (np.nan, np.nan)
    P(f'  {lab:42s} n {len(ii):4d} · λαθος μοντ. {np.sqrt(np.mean((a - m) ** 2)):.2f} vs κλεισ. {np.sqrt(np.mean((a - mc) ** 2)):.2f} (χασμα {np.sqrt(np.mean((a - m) ** 2)) - np.sqrt(np.mean((a - mc) ** 2)):+.2f})'
      f' · μεροληψια μοντ. {np.mean(a - m):+.1f} / αγορας {np.mean(a - mc):+.1f} · Κ2 {b:+.2f} (t {t:+.1f})')
P('  — ανα φαση —')
for lo, hi in ((0, 2), (3, 5), (6, 9), (10, 17), (18, 99)): gap(f'αγων {lo + 1}-{hi + 1 if hi < 99 else "+"}', (GN >= lo) & (GN <= hi))
P('  — νεες/παλιες ομαδες (επαιξαν EuroCup περσι;) —')
prevteams = {Y: set(D[D.season == f'U{int(Y[1:]) - 1}'].home) | set(D[D.season == f'U{int(Y[1:]) - 1}'].away) for Y in set(seasn)}
NEWC = np.array([(D.home.values[i] not in prevteams[seasn[i]]) + (D.away.values[i] not in prevteams[seasn[i]]) for i in range(len(D))])
for k_, lab in ((0, 'και οι 2 παλιες'), (1, '1 νεα'), (2, 'και οι 2 νεες')): gap(lab, NEWC == k_)
for k_, lab in ((0, 'και οι 2 παλιες · αγων 1-6'), (1, '1 νεα · αγων 1-6'), (2, 'και οι 2 νεες · αγων 1-6')): gap(lab, (NEWC == k_) & (GN <= 5))
P('  — εγχωρια δεδομενα box —')
gap('με εγχωριο box και οι 2', HASB); gap('χωρις (μια τουλαχιστον)', ~HASB)
P('  — πρωταθλημα γηπεδουχου —')
LGH = np.array([(MAPD.get((seasn[i], D.home.values[i])) or (0, 0, '—'))[2] for i in range(len(D))])
for lg in [l for l, c in collections.Counter(LGH[iiM]).most_common(9)]: gap(f'γηπεδουχος απο {lg}', LGH == lg)
P('  — υψος γραμμης κλεισιματος (πεμπτημορια) —')
qs = np.nanpercentile(MC[iiM], [20, 40, 60, 80])
edges = [-np.inf] + list(qs) + [np.inf]
for a_, b_ in zip(edges[:-1], edges[1:]): gap(f'γραμμη {a_:.0f}–{b_:.0f}', (MC > a_) & (MC <= b_))
P('  — ΡΥΘΜΟΣ vs ΑΠΟΔΟΤΙΚΟΤΗΤΑ (που ειναι το λαθος του μοντελου;) —')
RSRC = open('ec_season_backtest.py', encoding='utf-8').read()
fn = RSRC[RSRC.index('def run2T('):RSRC.index('LIVE = (9999', RSRC.index('def run2T('))]
fn = fn.replace('def run2T(', 'def run2P(').replace("pm_[sidx[j]] = pace * (e_h - e_a) / 100; pt_[sidx[j]] = pace * (e_h + e_a) / 100",
                                                   "pm_[sidx[j]] = pace; pt_[sidx[j]] = (e_h + e_a)")
exec(fn, EC)
PACEP, EFFP = EC['run2P'](*M['ENG']['v2 λ8'])
pace_a = D.pace.values.astype(float); eff_a = 100 * TOT / pace_a
ok = np.isin(seasn, EVM) & np.isfinite(PACEP) & (D.gmin.values <= 40.5)
e_pace = (pace_a - PACEP)[ok] * EFFP[ok] / 100; e_eff = (eff_a - EFFP)[ok] * PACEP[ok] / 100
P(f'  (κανονικος χρονος) λαθος συνολου απο ΡΥΘΜΟ sd {e_pace.std():.1f} π. · απο ΑΠΟΔΟΤΙΚΟΤΗΤΑ sd {e_eff.std():.1f} π. · '
  f'πραγματικη διακυμανση ρυθμου ματς {pace_a[ok].std():.1f} κατοχες (μοντελο εξηγει {1 - np.var(pace_a[ok] - PACEP[ok]) / np.var(pace_a[ok]):.0%}) · '
  f'αποδοτικοτητας {eff_a[ok].std():.1f}/100 (εξηγει {1 - np.var(eff_a[ok] - EFFP[ok]) / np.var(eff_a[ok]):.0%})')
okb = ok & HASB
if okb.sum() > 100:
    P(f'  εγχωριος ρυθμος → εξηγει το λαθος ρυθμου του μοντελου; κλιση {np.polyfit(FPp[okb] / 2.2, (pace_a - PACEP)[okb], 1)[0]:+.2f} κατοχες ανα κατοχη (t περιπου '
      f'{np.corrcoef(FPp[okb], (pace_a - PACEP)[okb])[0, 1] * math.sqrt(okb.sum()):+.1f})')
P('  — μεγαλες διαφωνιες (≥5 π. απο το κλεισιμο): ποιος ειχε δικιο —')
for lab, f in (('ολη', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
    ii = [i for i in iiM if np.isfinite(V[i]) and abs(V[i] - MC[i]) >= 5 and f(GN[i])]
    if not ii: continue
    sg = np.sign(V[ii] - MC[ii]); got = (TOT[ii] - MC[ii]) * sg
    P(f'  {lab:9s} n {len(ii):3d} (over {int((sg > 0).sum())}/under {int((sg < 0).sum())}) · μεση διαφωνια {np.mean(np.abs(V[ii] - MC[ii])):.1f} · βγηκε {got.mean():+.1f} π. · '
      f'σωστη πλευρα {np.mean(got > 0):.0%} · νεες ομαδες {np.mean(NEWC[ii] > 0):.0%} (γενικα {np.mean(NEWC[iiM] > 0):.0%})')
open('ec_totals_deep_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
