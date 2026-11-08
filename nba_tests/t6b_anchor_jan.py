# -*- coding: utf-8 -*-
"""t6b_anchor_jan.py — ΤΕΣΤ 6β (Στελιος 20/10: «μηπως η αγκυρα θα αξιζε ενα τεστ απο Γεναρη και μετα οπου το μοντελο χανει πληροφορια;»)
Η αγκυρα εφαρμοζεται ΜΟΝΟ σε αγωνες απο 1 Ιανουαριου και μετα· Οκτ-Δεκ = σημερινο μοντελο (ανεπαφο). ΜΟΝΟ μετρηση, τιποτα live.
Βαση = production + B2B 3.0 + 0.75·απουσιες (cache t_common). Picks στο ΑΝΟΙΓΜΑ (Crown), πλευρα με το μεγαλυτερο edge.
Σημερινο Ιαν+ (edge ≥8%): 1.796 picks, −2.2%, −40.3u.
ΕΚΔΟΧΕΣ (Ιαν+ μονο):
 A_λ / B_λ : ratings αγορας απο παλιες γραμμες κλεισιματος (ιδια με t6: walk-forward, ridge κ=3, ημιζωη 60μ, prior 0.8×περσι)
             V = (1−λ)·MG + λ·MR + B2B/απουσιες, λ ∈ {0.25, 0.5, 0.75}. A = ακατεργαστο κλεισιμο, B = κλεισιμο − B2B/απουσιες.
             LOSO: λ με το καλυτερο RMSE Ιαν+ των αλλων 4 σεζον· κατωφλι edge 8% (σημερινο).
 C_w,κ     : μ = αγορα_ανοιγματος + w·(V − αγορα), w ∈ {0.25, 0.5, 0.75} × κατωφλι {4, 6, 8%}.
             LOSO: (w, κ) με το μεγαλυτερο ROI Ιαν+ στις αλλες 4 (ελαχιστο 300 picks σε αυτες).
 D_ραμπα   : MR εκδοχης B με λ ανα μηνα (σταθερο, χωρις LOSO): Ιαν .25 · Φεβ .42 · Μαρ .58 · Απρ+ .75, κατωφλι 8%.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο): ΠΕΡΝΑ αν (1) RMSE Ιαν+ καλυτερο σε ≥4/5 σεζον ΚΑΙ (2) ROI Ιαν+ (ανοιγμα, επιλεγμενο κατωφλι)
 καλυτερο απο το σημερινο Ιαν+ στην ιδια σεζον σε ≥3/5 σεζον ΚΑΙ (3) μοναδες Ιαν+ (συνολο 5 σεζον) οχι λιγοτερες απο σημερα (−40.3u).
 Για C το RMSE μετραται στο μ (στους αγωνες με γραμμη ανοιγματος).
Επιπλεον: Ιαν-Φεβ / Μαρ-Απρ, CLV, και οι κατηγοριες απωλειας του Τ7 (αουτσαιντερ γηπεδουχος · «αδιαφορη» T/E/L/LT · τελευταια 10).
Εξοδος: t6b_anchor_jan_out.txt"""
import os, sys, json, collections
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
PROJ = os.path.dirname(SC); os.chdir(PROJ)
sys.stdout.reconfigure(encoding='utf-8')
from t_common import load, side_pick, settle, np
import pandas as pd
from statistics import NormalDist
nd = NormalDist()
D = load()
MG, OC, S, EV, ACT, SIG, G = D['MG'], D['OC'], D['SEAS_G'], D['EV'], D['ACT'], D['SIG'], D['G']
ADJ = 3.0 * (D['B2A'] - D['B2H']) + 0.75 * D['LOSS2']; BASE = MG + ADJ
MON = G.date.dt.month.values; dD = G.date.values.astype('datetime64[D]'); n = len(G)
HOME, AWAY = G.home.values, G.away.values
JAN = np.isin(MON, [1, 2, 3, 4, 5, 6]) & np.isin(S, EV); JF = np.isin(MON, [1, 2]); MA = np.isin(MON, [3, 4, 5, 6])

# ================= ratings αγορας (αντιγραφο t6) =================
CL = {i: d['c'][1] for i, d in OC.items()}
S21 = json.load(open('nowgoal_nba/sched_20-21.json', encoding='utf-8')); need = {g['ngid'] for g in S21}; ODD = {}
for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ngid'] in need and r['t'] == 21:
        ODD[r['ngid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
keyd = collections.defaultdict(list)
for i in np.where(S == 2021)[0]: keyd[(int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
for g in S21:
    if g['hs'] is None or not ODD.get(g['ngid']): continue
    ts = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
    us = ts.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize(); tip = ts.timestamp()
    near = lambda i: abs((G.date.values[i] - np.datetime64(us)) / np.timedelta64(1, 'D')) <= 1
    cand = [i for i in keyd.get((g['hs'], g['as_']), []) if near(i)]; sw = False
    if not cand: cand = [i for i in keyd.get((g['as_'], g['hs']), []) if near(i)]; sw = True
    if len(cand) != 1: continue
    rows = [x for x in ODD[g['ngid']] if x[0] + 8 * 3600 <= tip + 900]
    if not rows: continue
    x = rows[-1]; L = -x[1] * (-1 if sw else 1); oh, oa = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])
    ph = (1 / oh) / (1 / oh + 1 / oa); CL[cand[0]] = -L + SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
HL, KAP = 60.0, 3.0
def fit(rows, prior, teams):
    T = {t: k for k, t in enumerate(teams)}; m_ = len(teams); A = np.zeros((m_ + 1, m_ + 1)); b = np.zeros(m_ + 1)
    for age, h, a, y in rows:
        w = 0.5 ** (age / HL); x = np.zeros(m_ + 1); x[T[h]] = 1; x[T[a]] = -1; x[m_] = 1; A += w * np.outer(x, x); b += w * x * y
    for t, k in T.items(): A[k, k] += KAP; b[k] += KAP * prior.get(t, 0.0)
    A[m_, m_] += 1.0; b[m_] += 2.0
    sol = np.linalg.solve(A, b); r = {t: sol[k] for t, k in T.items()}; mm = np.mean(list(r.values()))
    return {t: v - mm for t, v in r.items()}, sol[m_]
def market_ratings(clean):
    MR = np.full(n, np.nan); prior = {}
    for Y in sorted(set(S)):
        idx = np.where(S == Y)[0]; teams = sorted(set(HOME[idx]) | set(AWAY[idx])); days = sorted(set(dD[idx])); hist = []
        byd = collections.defaultdict(list)
        for i in idx: byd[dD[i]].append(i)
        for d in days:
            r, h0 = fit([((d - dd).astype(int), h, a, y) for dd, h, a, y in hist], prior, teams)
            for i in byd[d]: MR[i] = h0 + r[HOME[i]] - r[AWAY[i]]
            for i in byd[d]:
                if i in CL: hist.append((d, HOME[i], AWAY[i], CL[i] - (ADJ[i] if clean else 0.0)))
        last = days[-1] + np.timedelta64(1, 'D')
        rf, _ = fit([((last - dd).astype(int), h, a, y) for dd, h, a, y in hist], prior, teams); prior = {t: 0.8 * v for t, v in rf.items()}
    return MR
MRA, MRB = market_ratings(False), market_ratings(True)

# ================= κατηγοριες Τ7 (αντιγραφο της βαθμολογιας του t7_jan_breakdown) =================
EAST = {'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS'}
TANK = np.zeros((n, 2), bool); ELIM = np.zeros((n, 2), bool); LOCK = np.zeros((n, 2), bool); LTOP = np.zeros((n, 2), bool); GLEFT = np.zeros((n, 2))
for s in np.unique(S):
    idx = np.where(S == s)[0]; tot = collections.Counter(list(HOME[idx]) + list(AWAY[idx])); rec = {t: [0, 0, 0.0] for t in tot}
    for d in np.unique(dD[idx]):
        cur = idx[dD[idx] == d]; st = {}
        wp = {t: (r[0] / max(1, r[0] + r[1]), r[2] / max(1, r[0] + r[1])) for t, r in rec.items()}
        for conf in (EAST, set(rec) - EAST):
            rows = sorted([t for t in rec if t in conf], key=lambda t: wp[t], reverse=True); w10, l10 = rec[rows[9]][0], rec[rows[9]][1]
            for j, t in enumerate(rows):
                w, l = rec[t][0], rec[t][1]; rem = tot[t] - w - l; gb = ((w10 - w) + (l - l10)) / 2
                elim = j >= 10 and w + rem < w10; below = rows[j + 1:]; above = rows[:j]
                lock = (w + l >= 60) and all(rec[u][0] + tot[u] - rec[u][0] - rec[u][1] < w for u in below) and all(w + rem < rec[v][0] for v in above)
                st[t] = (gb, elim, lock, rem)
        for i in cur:
            for k, t in enumerate((HOME[i], AWAY[i])):
                gp = rec[t][0] + rec[t][1]; gb, el, lk, rem = st[t]; GLEFT[i, k] = rem
                TANK[i, k] = gp >= 50 and gb >= 6; ELIM[i, k] = el; LOCK[i, k] = lk; LTOP[i, k] = gp >= tot[t] - 5 and rec[t][0] / max(1, gp) >= .62
        for i in cur:
            m = ACT[i]; rec[HOME[i]][0 if m > 0 else 1] += 1; rec[AWAY[i]][0 if m < 0 else 1] += 1; rec[HOME[i]][2] += m; rec[AWAY[i]][2] -= m
INDIF = TANK.any(1) | ELIM.any(1) | LOCK.any(1) | LTOP.any(1); LAST10 = GLEFT.min(1) <= 10

# ================= εργαλεια =================
IDX = [i for i in OC if JAN[i]]
def picks(mu_fn, thr):
    R = []
    for i in IDX:
        L, mk, o1, o2 = OC[i]['o']; mu = mu_fn(i, mk)
        if not np.isfinite(mu): continue
        s_, e, od_, p, pp = side_pick(mu, L, o1, o2, SIG)
        if e < thr: continue
        u, _ = settle(ACT[i], L, s_, od_)
        R.append(dict(i=i, Y=S[i], u=u, clv=s_ * (OC[i]['c'][1] - mk), hd=(s_ == 1 and L > 0), ind=INDIF[i], l10=LAST10[i]))
    return R
def ps_(R): return {Y: sum(r['u'] for r in R if r['Y'] == Y) for Y in EV}
def roi(R): return np.mean([r['u'] for r in R]) * 100 if R else 0.0
def rmse_y(mu, Y, ii):
    m = [i for i in ii if S[i] == Y]; return float(np.sqrt(np.mean([(ACT[i] - mu[i]) ** 2 for i in m])))
JI = [i for i in range(n) if JAN[i]]; JIO = [i for i in JI if i in OC]
B0 = picks(lambda i, mk: BASE[i], .08); B0Y = ps_(B0); NB = {Y: sum(1 for r in B0 if r['Y'] == Y) for Y in EV}
def rep(nm, R, rmse_d, sel):
    u = sum(r['u'] for r in R); PY = ps_(R); NY = {Y: sum(1 for r in R if r['Y'] == Y) for Y in EV}
    better = sum((PY[Y] / NY[Y] if NY[Y] else -9) > (B0Y[Y] / NB[Y]) for Y in EV)
    ok = sum(x < 0 for x in rmse_d) >= 4 and better >= 3 and u >= sum(r['u'] for r in B0)
    jf = [r for r in R if JF[r['i']]]; ma = [r for r in R if MA[r['i']]]
    cat = lambda f: (lambda b: f'{len(b):4d} {roi(b):+5.1f}%')([r for r in R if f(r)])
    print(f'  {nm:12s} {sel:14s}| ΔRMSE {np.mean(rmse_d):+.3f} {sum(x < 0 for x in rmse_d)}/5 | {len(R):4d} {roi(R):+5.1f}% {u:+6.1f}u ROI>σημ {better}/5 | '
          f'ΙΦ {roi(jf):+5.1f}% ΜΑ {roi(ma):+5.1f}% | CLV {np.mean([r["clv"] for r in R]):+.2f} | αουτ.γηπ {cat(lambda r: r["hd"])} · αδιαφ {cat(lambda r: r["ind"])} · τελ10 {cat(lambda r: r["l10"])} | {"ΠΕΡΝΑ" if ok else "✗"}')
    print(f'  {"":12s} {"":14s}  μοναδες ανα σεζον ' + ' '.join(f'{PY[Y]:+6.1f}' for Y in EV) + ' (σημερα ' + ' '.join(f'{B0Y[Y]:+6.1f}' for Y in EV) + ')')

print(f'Ιαν+ αγωνες {len(JI)} (με γραμμη {len(JIO)}) · RMSE Ιαν+: βαση {np.sqrt(np.mean([(ACT[i] - BASE[i]) ** 2 for i in JI])):.3f} · '
      f'MR-A {np.sqrt(np.mean([(ACT[i] - MRA[i] - ADJ[i]) ** 2 for i in JI])):.3f} · MR-B {np.sqrt(np.mean([(ACT[i] - MRB[i] - ADJ[i]) ** 2 for i in JI])):.3f} · '
      f'ανοιγμα {np.sqrt(np.mean([(ACT[i] - OC[i]["o"][1]) ** 2 for i in JIO])):.3f}')
print(f'  {"εκδοχη":12s} {"επιλογη":14s}| RMSE Ιαν+       | n    ROI    μοναδες            | Ιαν-Φεβ / Μαρ-Απρ       | CLV π.   | κατηγοριες Τ7 (n ROI)')
rep('ΣΗΜΕΡΑ', B0, [0.0] * 5, '8%')

# ---- A / B ----
for nm, MR in (('A', MRA), ('B', MRB)):
    VS = {lam: (1 - lam) * MG + lam * MR + ADJ for lam in (0.25, 0.5, 0.75)}
    for lam, v in VS.items():
        d = [rmse_y(v, Y, JI) - rmse_y(BASE, Y, JI) for Y in EV]
        rep(f'{nm} λ={lam}', picks(lambda i, mk, v=v: v[i], .08), d, 'σταθερο 8%')
    held = BASE.copy(); ch = []
    for Y in EV:
        oth = [x for x in EV if x != Y]
        lam = min(VS, key=lambda l: np.sqrt(np.mean([(ACT[i] - VS[l][i]) ** 2 for i in JI if S[i] in oth]))); ch.append(lam)
        m = (S == Y) & JAN; held[m] = VS[lam][m]
    d = [rmse_y(held, Y, JI) - rmse_y(BASE, Y, JI) for Y in EV]
    rep(f'{nm} LOSO', picks(lambda i, mk: held[i], .08), d, f'λ {",".join(str(x) for x in ch)}')

# ---- C ----
GRID = [(w, t) for w in (0.25, 0.5, 0.75) for t in (.04, .06, .08)]
PC = {(w, t): picks(lambda i, mk, w=w: mk + w * (BASE[i] - mk), t) for w, t in GRID}
MUC = {w: {i: OC[i]['o'][1] + w * (BASE[i] - OC[i]['o'][1]) for i in JIO} for w in (0.25, 0.5, 0.75)}
rC = lambda w, Y: float(np.sqrt(np.mean([(ACT[i] - MUC[w][i]) ** 2 for i in JIO if S[i] == Y])))
for w, t in GRID:
    rep(f'C w={w}', PC[(w, t)], [rC(w, Y) - rmse_y(BASE, Y, JIO) for Y in EV], f'{int(t * 100)}%')
held = []; ch = []; dR = []
for Y in EV:
    oth = [x for x in EV if x != Y]
    cand = [k for k in GRID if sum(1 for r in PC[k] if r['Y'] in oth) >= 300]
    k = max(cand, key=lambda k: roi([r for r in PC[k] if r['Y'] in oth])); ch.append(f'{k[0]}/{int(k[1] * 100)}')
    held += [r for r in PC[k] if r['Y'] == Y]; dR.append(rC(k[0], Y) - rmse_y(BASE, Y, JIO))
rep('C LOSO', held, dR, ' '.join(ch))

# ---- D ραμπα ----
LM = {1: .25, 2: .42, 3: .58}; lamv = np.array([LM.get(m, .75) for m in MON])
VD = BASE.copy(); VD[JAN] = ((1 - lamv) * MG + lamv * MRB + ADJ)[JAN]
rep('D ραμπα(B)', picks(lambda i, mk: VD[i], .08), [rmse_y(VD, Y, JI) - rmse_y(BASE, Y, JI) for Y in EV], 'Ιαν.25→Απρ.75')
print('\n(ΔRMSE = μεσος ορος των 5 σεζον, αρνητικο = καλυτερο· «ROI>σημ» = σεζον οπου το ROI Ιαν+ ξεπερνα το σημερινο Ιαν+ της ιδιας σεζον)')
