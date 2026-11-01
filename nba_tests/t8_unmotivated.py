# -*- coding: utf-8 -*-
"""t8_unmotivated.py — ΤΕΣΤ 8 (Στελιος 20/10: «αν το μοντελο χανει την πληροφορια των αδιαφορων και η αγορα τις εχει πιο αουτσαιντερ
απο μας, πως δεν το πιανει; δοκιμασε κατι πιο επιθετικο»). ΜΟΝΟ μετρηση, τιποτα live.
Βαση = production CFG_H + 0.75·LOSS[2] + B2B 3.0 (cache t_common). Picks στο ΑΝΟΙΓΜΑ (Crown), πλευρα με μεγαλυτερο edge, κατωφλι 8%.
Σημερα Ιαν+ (8%): 1.796 picks, −2.2%, −40.3u.
ΣΤΟΧΟΣ («TARGET») = αγωνες οπου τουλαχιστον μια ομαδα ειναι «αδιαφορη» (TANK/ELIM/LOCK/LATE_TOP οπως t7, μονο με αποτελεσματα ΠΡΙΝ
τη μερα του αγωνα· ο αριθμος ματς της σεζον = γνωστο προγραμμα) Η καποια ομαδα ειναι στα τελευταια 10 της ματς.
DOWN = TANK|ELIM (παραιτηση/εκτος), REST = LOCK|LATE_TOP (ξεκουραση). Εκτος TARGET ολες οι εκδοχες = βαση.
ΕΚΔΟΧΕΣ
 (A) ΦΙΛΤΡΟ (χωρις παραμετρο): A1 κανενα pick σε TARGET · A1i μονο «αδιαφορες» · A1t μονο τελ.10 · A2 κανενα pick ΠΑΝΩ σε ομαδα T/E/L/LT
     · A3 κανενας αουτσαιντερ γηπεδουχος σε TARGET.
 (B) ΕΠΙΘΕΤΙΚΗ ΑΓΚΥΡΑ μονο σε TARGET: μ = αγορα_ανοιγματος + w·(βαση − αγορα), w ∈ {0, .1, .25, .5}, κατωφλι 8%.
     LOSO: w ∈ {0, .1, .25, .5, 1(=βαση)} με τις περισσοτερες μοναδες Ιαν+ στις αλλες 4 σεζον.
 (C) ΠΟΙΝΗ ΚΙΝΗΤΡΟΥ: μ = βαση + c_d·(DOWN_h − DOWN_a) + c_r·(REST_h − REST_a), c με OLS (με σταθερα που ΔΕΝ εφαρμοζεται)
     στο υπολοιπο (πραγματικο − βαση), ολοι οι αγωνες Ιαν+ των αλλων 4 σεζον (LOSO). C4 = 4 χωριστοι συντελεστες T/E/L/LT.
     C+10 = C + μετατοπιση εδρας οταν καποια ομαδα στα τελ.10. Cmkt = ιδια χαρακτηριστικα αλλα c απο (ανοιγμα − βαση) δηλ.
     «υιοθετω τη διορθωση που κανει η αγορα» (LOSO).
 ΠΕΡΙΓΡΑΦΙΚΑ: σε ολους τους αγωνες Ιαν+ με γραμμη, απο τη σκοπια της «αδιαφορης» ομαδας: μοντελο−ανοιγμα, πραγματικο−ανοιγμα
     (εχει δικιο η αγορα;), πραγματικο−μοντελο, κλεισιμο−ανοιγμα, + OLS συντελεστες για τις 3 διαφορες.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): μια εκδοχη ΠΕΡΝΑ αν στο Ιαν+ βελτιωνει ΚΑΙ μοναδες ΚΑΙ ROI vs βαση στην ιδια σεζον
 σε ≥4/5 σεζον, Η σε ≥3/5 με καθαρα θετικο συνολο (Δμοναδες 5 σεζον ≥ +10u). Παραμετροι μονο LOSO (fixed w/m = πληροφοριακα).
 Οκτ-Δεκ: ανεπαφο (αναφερεται ποσοι αγωνες TARGET υπαρχουν εκει).
ΠΡΟΣΟΧΗ (δηλωμενο εκ των προτερων): οι κατηγοριες TARGET επιλεχθηκαν ΑΦΟΥ ο t7 τις ειδε να χανουν στα ιδια 5 χρονια → τα φιλτρα (A)
 ειναι in-sample ως προς την επιλογη κατηγοριας. Επιπλεον ελεγχος σε σεζον 2020-21 (εκτος των 5, δεν ειδε ο t7· γραμμες nowgoal Crown,
 72 ματς, ΔΕΝ μετραει στο κριτηριο, μονο ενδειξη).
Εξοδος: t8_unmotivated_out.txt"""
import os, sys, json, collections
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
PROJ = os.path.dirname(SC); os.chdir(PROJ)
sys.stdout.reconfigure(encoding='utf-8')
from t_common import load, side_pick, settle, np
import pandas as pd
from statistics import NormalDist
nd = NormalDist()
D = load()
MG, OC, S, EV, ACT, SIG, G = D['MG'], dict(D['OC']), D['SEAS_G'], D['EV'], D['ACT'], D['SIG'], D['G']
ADJ = 3.0 * (D['B2A'] - D['B2H']) + 0.75 * D['LOSS2']; BASE = MG + ADJ
MON = G.date.dt.month.values; dD = G.date.values.astype('datetime64[D]'); n = len(G)
HOME, AWAY = G.home.values, G.away.values
JANM = np.isin(MON, [1, 2, 3, 4, 5, 6]); OD = np.isin(MON, [10, 11, 12])

# ---------- 2020-21: ανοιγμα/κλεισιμο απο nowgoal (ιδια λογικη με t_common/t6b) ----------
S21 = json.load(open('nowgoal_nba/sched_20-21.json', encoding='utf-8')); need = {g['ngid'] for g in S21}; ODD = {}
for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ngid'] in need and r['t'] == 21:
        ODD[r['ngid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
def tup(x, sw):
    L = -x[1] * (-1 if sw else 1); oh, oa = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])
    ph = (1 / oh) / (1 / oh + 1 / oa); return (float(L), float(-L + SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))), float(oh), float(oa))
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
    if rows: OC[cand[0]] = dict(o=tup(rows[0], sw), c=tup(rows[-1], sw))

# ---------- βαθμολογια πριν τη μερα (αντιγραφο t6b/t7) ----------
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
FLAG = TANK | ELIM | LOCK | LTOP; DOWN = TANK | ELIM; REST = LOCK | LTOP
INDIF = FLAG.any(1); LAST10 = GLEFT.min(1) <= 10; TARGET = INDIF | LAST10
XD = DOWN[:, 0].astype(float) - DOWN[:, 1]; XR = REST[:, 0].astype(float) - REST[:, 1]
X4 = np.stack([M[:, 0].astype(float) - M[:, 1] for M in (TANK, ELIM, LOCK, LTOP)], 1)

# ---------- εργαλεια ----------
JIDX = [i for i in OC if JANM[i] and S[i] in EV]; H21 = [i for i in OC if JANM[i] and S[i] == 2021]
def picks(mu, ii, thr=.08, skip=None):
    R = []
    for i in ii:
        L, mk, o1, o2 = OC[i]['o']; m_ = mu[i]
        if not np.isfinite(m_): continue
        s_, e, od_, p, pp = side_pick(m_, L, o1, o2, SIG)
        if e < thr: continue
        k = 0 if s_ == 1 else 1
        if skip is not None and skip(i, s_, k, L): continue
        u, _ = settle(ACT[i], L, s_, od_)
        R.append(dict(i=i, Y=S[i], u=u, clv=s_ * (OC[i]['c'][1] - mk), tg=TARGET[i]))
    return R
def agg(R, Y=None):
    x = [r['u'] for r in R if Y is None or r['Y'] == Y]; return len(x), (np.mean(x) * 100 if x else 0.0), sum(x)
B0 = picks(BASE, JIDX); B21 = picks(BASE, H21)
VER = []
def rep(nm, R, R21, note=''):
    per = {Y: agg(R, Y) for Y in EV}; b = {Y: agg(B0, Y) for Y in EV}
    both = sum(per[Y][2] > b[Y][2] + 1e-9 and per[Y][1] > b[Y][1] + 1e-9 for Y in EV)
    n_, r_, u_ = agg(R); du = u_ - agg(B0)[2]
    ok = both >= 4 or (both >= 3 and du >= 10)
    t = [r for r in R if r['tg']]; nt, rt, ut = agg(t); n21, r21, u21 = agg(R21); b21 = agg(B21)
    VER.append(f'{nm:9s}|{n_:5d} {r_:+5.1f}% {u_:+6.1f} Δ{du:+5.1f} | ' + ' '.join(f'{per[Y][2] - b[Y][2]:+5.1f}' for Y in EV)
               + f' | {both}/5 {"ΠΕΡΝΑ" if ok else "✗"} | TG {nt:4d} {rt:+5.1f}% | 20-21 {n21:3d} {r21:+5.1f}% Δ{u21 - b21[2]:+5.1f} {note}')

def ols(y, X, m):
    A = np.column_stack([np.ones(m.sum()), X[m]]); beta, *_ = np.linalg.lstsq(A, y[m], rcond=None)
    res = y[m] - A @ beta; cov = np.linalg.inv(A.T @ A) * res.var(ddof=A.shape[1]); return beta[1:], np.sqrt(np.diag(cov))[1:]

# ================= ΠΕΡΙΓΡΑΦΙΚΑ =================
MKO = np.full(n, np.nan); MKC = np.full(n, np.nan)
for i, d in OC.items(): MKO[i] = d['o'][1]; MKC[i] = d['c'][1]
EVM = np.isin(S, EV); JM = JANM & EVM & np.isfinite(MKO)
print(f'Ιαν+ αγωνες με γραμμη (5 σεζον): {JM.sum()} · TARGET {(JM & TARGET).sum()} (αδιαφορη {(JM & INDIF).sum()}, τελ.10 {(JM & LAST10).sum()})'
      f' · Οκτ-Δεκ TARGET: {(OD & EVM & TARGET).sum()} · 20-21 Ιαν+ με γραμμη {len(H21)}')
print('\nΠΕΡΙΓΡΑΦΙΚΑ (ολοι οι αγωνες Ιαν+, σκοπια της σημαδεμενης ομαδας· μονο οπου η ΜΙΑ απο τις δυο εχει τη σημαια· ±SE)')
print(f'  {"κατηγορια":22s}   n | μοντ−ανοιγ | πραγμ−ανοιγ  | πραγμ−μοντ   | κλεισ−ανοιγ')
def desc(nm, M, sel=None):
    one = M[:, 0] ^ M[:, 1]; m = JM & one & (True if sel is None else sel)
    sg = np.where(M[:, 0], 1.0, -1.0)[m]
    a, b_, c, dlt = sg * (BASE[m] - MKO[m]), sg * (ACT[m] - MKO[m]), sg * (ACT[m] - BASE[m]), sg * (MKC[m] - MKO[m])
    se = lambda x: x.std() / np.sqrt(len(x))
    print(f'  {nm:22s} {m.sum():4d} | {a.mean():+5.2f}±{se(a):.2f} | {b_.mean():+5.2f}±{se(b_):.2f} | {c.mean():+5.2f}±{se(c):.2f} | {dlt.mean():+5.2f}±{se(dlt):.2f}')
for nm, M in (('TANK', TANK), ('ELIM', ELIM), ('LOCK', LOCK), ('LATE_TOP', LTOP), ('DOWN (T|E)', DOWN), ('REST (L|LT)', REST)):
    desc(nm, M)
desc('DOWN γηπεδουχος', DOWN, sel=DOWN[:, 0])
desc('DOWN φιλοξενουμενος', DOWN, sel=DOWN[:, 1])
m10 = JM & LAST10 & ~INDIF; e = lambda x: f'{x.mean():+5.2f}±{x.std() / np.sqrt(len(x)):.2f}'
print(f'  {"τελ.10 χωρις σημαια":22s} {m10.sum():4d} | {e(BASE[m10] - MKO[m10])} | {e(ACT[m10] - MKO[m10])} | {e(ACT[m10] - BASE[m10])} | {e(MKC[m10] - MKO[m10])}  (σκοπια γηπεδουχου)')
mn = JM & ~TARGET
print(f'  {"εκτος TARGET (ελεγχος)":22s} {mn.sum():4d} | {e(BASE[mn] - MKO[mn])} | {e(ACT[mn] - MKO[mn])} | {e(ACT[mn] - BASE[mn])} | {e(MKC[mn] - MKO[mn])}  (σκοπια γηπεδουχου)')
print('  OLS (Ιαν+ ολα, σταθερα+χαρακτηριστικα, π. για τον γηπεδουχο οταν ΑΥΤΟΣ εχει τη σημαια):')
for nm, y in (('ανοιγμα−βαση  (τι προσθετει η αγορα)', MKO - BASE), ('πραγμ−βαση    (τι θα επρεπε)', ACT - BASE), ('πραγμ−ανοιγμα (λαθος αγορας)', ACT - MKO)):
    b2, s2 = ols(y, np.column_stack([XD, XR]), JM); b4, s4 = ols(y, X4, JM)
    print(f'    {nm:38s} DOWN {b2[0]:+5.2f}±{s2[0]:.2f} REST {b2[1]:+5.2f}±{s2[1]:.2f} | T {b4[0]:+5.2f}±{s4[0]:.2f} E {b4[1]:+5.2f}±{s4[1]:.2f} L {b4[2]:+5.2f}±{s4[2]:.2f} LT {b4[3]:+5.2f}±{s4[3]:.2f}')

# ================= ΕΚΔΟΧΕΣ =================
rep('ΣΗΜΕΡΑ', B0, B21)
FILT = {'A1': lambda i, s_, k, L: TARGET[i], 'A1i': lambda i, s_, k, L: INDIF[i], 'A1t': lambda i, s_, k, L: LAST10[i] and not INDIF[i],
        'A2': lambda i, s_, k, L: FLAG[i, k], 'A3': lambda i, s_, k, L: TARGET[i] and s_ == 1 and L > 0}
for nm, f in FILT.items(): rep(nm, picks(BASE, JIDX, skip=f), picks(BASE, H21, skip=f))
def mu_anchor(w):
    mu = BASE.copy(); m = TARGET & np.isfinite(MKO); mu[m] = MKO[m] + w * (BASE[m] - MKO[m]); return mu
WS = [0.0, 0.1, 0.25, 0.5, 1.0]; PB = {w: picks(mu_anchor(w), JIDX) for w in WS}; PB21 = {w: picks(mu_anchor(w), H21) for w in WS}
for w in WS[:-1]: rep(f'B w={w}', PB[w], PB21[w])
held, ch = [], []
for Y in EV:
    w = max(WS, key=lambda w: sum(r['u'] for r in PB[w] if r['Y'] != Y and r['Y'] in EV)); ch.append(w); held += [r for r in PB[w] if r['Y'] == Y]
wall = max(WS, key=lambda w: sum(r['u'] for r in PB[w])); rep('B LOSO', held, PB21[wall], f'w={ch} (20-21: w ολων={wall})')
YM = {'C': (ACT - BASE, np.column_stack([XD, XR])), 'C4': (ACT - BASE, X4),
      'C+10': (ACT - BASE, np.column_stack([XD, XR, LAST10.astype(float)])), 'Cmkt': (MKO - BASE, np.column_stack([XD, XR]))}
JALL = JANM & EVM & np.isfinite(MKO)
for nm, (y, X) in YM.items():
    held, coefs = [], []
    for Y in EV:
        b, _ = ols(y, X, JALL & (S != Y)); coefs.append(b)
        mu = BASE + X @ b; held += [r for r in picks(mu, JIDX) if r['Y'] == Y]
    bA, _ = ols(y, X, JALL); R21 = picks(BASE + X @ bA, H21)
    cs = np.array(coefs); rep(nm, held, R21, 'c=' + ' '.join(f'{lo:+.1f}..{hi:+.1f}' for lo, hi in zip(cs.min(0), cs.max(0))))
for k2 in (1.5, 2.0):                                   # «πιο επιθετικο»: η διορθωση της αγορας ×1.5 / ×2 (LOSO, πληροφοριακο)
    y, X = YM['Cmkt']; held = []
    for Y in EV:
        b, _ = ols(y, X, JALL & (S != Y)); held += [r for r in picks(BASE + k2 * (X @ b), JIDX) if r['Y'] == Y]
    bA, _ = ols(y, X, JALL); rep(f'Cmkt×{k2}', held, picks(BASE + k2 * (X @ bA), H21))
print(f'\nΕΚΔΟΧΕΣ Ιαν+ (ανοιγμα, 8%) — n ROI μοναδες Δu | Δμοναδες ανα σεζον {" ".join(str(Y)[2:] for Y in EV)} | σεζον με u↑ΚΑΙ ROI↑ | picks σε TARGET | 2020-21')
for v in VER: print(v)
print('(Δ = διαφορα απο ΣΗΜΕΡΑ· c = ευρος συντελεστων στα 5 LOSO folds, σειρα DOWN, REST[, ...]· θετικο c = υπερ γηπεδουχου οταν ΑΥΤΟΣ εχει τη σημαια)')

# ---------- ΠΕΡΙΓΡΑΦΙΚΟ: τυφλο ποντα ΚΟΝΤΡΑ στην ομαδα DOWN (μονο η μια απο τις δυο), ανοιγμα, Ιαν+ (οχι εκδοχη, μονο ενδειξη) ----------
print('\nΤΥΦΛΟ κοντρα σε DOWN (T|E) στο ανοιγμα, Ιαν+ (n ROI u ανα σεζον):')
for lab, ii in (('5 σεζον', JIDX), ('20-21', H21)):
    R = []
    for i in ii:
        if DOWN[i, 0] == DOWN[i, 1]: continue
        L, mk, o1, o2 = OC[i]['o']; s_ = -1 if DOWN[i, 0] else 1; u, _ = settle(ACT[i], L, s_, o1 if s_ == 1 else o2)
        R.append(dict(Y=S[i], u=u, hd=DOWN[i, 0]))
    ys = sorted({r['Y'] for r in R}); nA, rA, uA = agg(R)
    print(f'  {lab:8s} {nA:4d} {rA:+5.1f}% {uA:+6.1f}u | ' + ' '.join(f'{str(Y)[2:]}:{agg(R, Y)[2]:+5.1f}' for Y in ys)
          + f' | DOWN γηπ: {agg([r for r in R if r["hd"]])[1]:+5.1f}% · DOWN φιλ: {agg([r for r in R if not r["hd"]])[1]:+5.1f}%')
