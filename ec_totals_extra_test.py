# -*- coding: utf-8 -*-
"""ec_totals_extra_test.py — EuroCup ΣΥΝΟΛΑ: 5 ΕΠΙΠΛΕΟΝ ΔΟΚΙΜΕΣ πανω στο LIVE μοντελο (5/10/2026, Στελιος «τρεξ' τα ολα»).
Μοντελο = live (ec_totals_deep_test ΤΕΛΙΚΟ). Κανονας picks = live (αγων 1-6 μιξη 50/50 ≥6% · 7+ μοντελο μονο ≥6%). Crown U2020-25.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση) — ΑΛΛΑΓΗ = LOSO RMSE καλυτερο σε ≥80% των σεζον που εχουν το δεδομενο:
 Ε1 ΣΥΝΕΧΕΙΑ ΡΟΣΤΕΡ (παλιες ομαδες): συνεχεια = % περσινων λεπτων EuroCup της ομαδας απο παικτες που επαιξαν στο 1ο φετινο ματς της·
    X = Σ (1 − συνεχεια) × περσινη ταση συνολων ομαδας (συνολο ματς − μεσος σεζον). Διορθωση κ·X, κ {0,−.25,−.5,−.75,−1}, ΜΟΝΟ αγων 1-6
    → κριση στο RMSE αγων 1-6 (εκει στοχευει).
 Ε2 ΔΕΙΚΤΗΣ «ΧΑΜΗΛΗΣ ΔΙΑΘΕΣΗΣ» = (ομαδες με εγχωριο ≤2 μερες μετα) + (ματς χωρις διακυβευμα) + (νοκ-αουτ)· κ {0,−.5,−1,−1.5,−2} ανα μοναδα.
 Ε3 ΧΡΟΝΙΣΜΟΣ συνολων: picks (κανονας live) στο ανοιγμα / 12ω / 6ω / 3ω / 1ω / κλεισιμο, ιδια ματς (ανοιχτα ≥12ω)·
    «αργοτερα καλυτερα» μονο αν ROI > ανοιγματος σε ≥4/6 σεζον.
 Ε4 ΕΔΡΑ «ΨΗΛΩΝ ΣΥΝΟΛΩΝ»: υπολοιπο (πραγματικο − μοντελο) του γηπεδουχου ΣΤΙΣ ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον, συρρικνωση n/(n+15)· κ {0,.25,.5,.75,1}.
 Ε5 ΠΡΩΤΑΘΛΗΜΑ ΟΜΑΔΑΣ: υπολοιπο ανα εγχωριο πρωταθλημα (γηπ & φιλ) απο τις ΑΛΛΕΣ σεζον, n/(n+40)· κ {0,.5,1}.
 Ε2/Ε4/Ε5 κριση στο RMSE ολων των ματς. ΤΕΛΙΚΟ: οτι περασει μαζι → Κ2 & ROI (κανονας live) ανα φαση.
Εξοδος: ec_totals_extra_out.txt"""
import sys, json, math, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'x'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
D, FIN, TOT, GN, seasn, MKT, cov, EVM, EV8, k2 = (NS[k] for k in ('D', 'FIN', 'TOT', 'GN', 'seasn', 'MKT', 'cov', 'EVM', 'EV8', 'k2'))
NEXTD, DEAD, KO, LGH, TS = NS['NEXTD'], NS['DEAD'], NS['KO'], NS['LGH'], NS['TS']
MAPD = NS['MAPD']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
seasn = np.asarray(seasn)
def rm(v, ys, msk=None):
    m = np.isin(seasn, ys) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
def loso(PR, base_key, lab, ys_crit, msk=None):
    keys = list(PR); held = np.full(len(D), np.nan); ch = []
    for Y in EV8:
        tr = [x for x in EV8 if x != Y]; k = min(keys, key=lambda k: rm(PR[k], tr, msk)); ch.append(k)
        m = seasn == Y; held[m] = PR[k][m]
    d = {Y: rm(held, [Y], msk) - rm(PR[base_key], [Y], msk) for Y in EV8}
    need = math.ceil(.8 * len(ys_crit)); nb = sum(d[Y] < 0 for Y in ys_crit); ok = nb >= need
    P(f'  {lab:44s} {rm(PR[base_key], EV8, msk):.3f} → {rm(held, EV8, msk):.3f} · ' + ' '.join(f'{Y[-2:]}:{d[Y]:+.2f}' for Y in EV8)
      + f' → {nb}/{len(ys_crit)} (χρειαζεται {need})' + ('  <- ΑΛΛΑΓΗ' if ok else '  <- ✗'))
    P(f'     επιλογες: {collections.Counter(ch).most_common(3)}')
    return held, ok, collections.Counter(ch).most_common(1)[0][0]
MC = np.full(len(D), np.nan)
for i in MKT: MC[i] = MKT[i]['c'][1]
def resid_test(name, x, early=False):
    for lab, base in (('vs ΚΛΕΙΣΙΜΟ', MC), ('vs ΜΟΝΤΕΛΟ', FIN)):
        sel = np.isfinite(base) & np.isfinite(x) & np.isin(seasn, EVM if lab == 'vs ΚΛΕΙΣΙΜΟ' else EV8) & (x != 0) & ((GN <= 5) if early else True)
        xx, r = x[sel], (TOT - base)[sel]
        if len(xx) < 30: P(f'  {name} {lab}: λιγα ({len(xx)})'); continue
        b, t = k2(xx, r); per = [np.polyfit(xx[seasn[sel] == Y], r[seasn[sel] == Y], 1)[0] for Y in EV8 if (seasn[sel] == Y).sum() >= 10]
        P(f'  {name:40s} {lab:12s} n {len(xx):4d} · κλιση {b:+.2f} (t {t:+.1f}, ιδιο προσημο {sum(np.sign(p) == np.sign(b) for p in per)}/{len(per)})')
# ================= Ε1 συνεχεια ροστερ =================
P('################ Ε1 ΣΥΝΕΧΕΙΑ ΡΟΣΤΕΡ ################')
PL = json.load(open('el_players.json', encoding='utf-8'))
mins = collections.defaultdict(lambda: collections.defaultdict(float)); first = {}
for k, g in PL.items():
    if g.get('comp') != 'U': continue
    S = g['season']
    for side, code in (('ph', g['hcode']), ('pa', g['acode'])):
        for p in g.get(side) or []:
            try: mins[(S, code)][p[0]] += float(p[3] or 0)
            except Exception: pass
        key = (S, code)
        if key not in first or g['utc'] < first[key][0]: first[key] = (g['utc'], {p[0] for p in (g.get(side) or [])})
CONT = {}
for (S, code), (u, roster) in first.items():
    prevS = f'U{int(S[1:]) - 1}'; pm = mins.get((prevS, code))
    if pm and sum(pm.values()) > 0: CONT[(S, code)] = sum(v for p, v in pm.items() if p in roster) / sum(pm.values())
P(f'  συνεχεια: {len(CONT)} ομαδες-σεζον · μεση {np.mean(list(CONT.values())):.0%} · ευρος {min(CONT.values()):.0%}–{max(CONT.values()):.0%}')
smean = {Y: np.mean(TOT[seasn == Y]) for Y in set(seasn)}
tend = collections.defaultdict(list)
for i in range(len(D)):
    for c in (D.home.values[i], D.away.values[i]): tend[(seasn[i], c)].append(TOT[i] - smean[seasn[i]])
X1 = np.zeros(len(D))
for i in range(len(D)):
    Y = seasn[i]; pY = f'U{int(Y[1:]) - 1}'
    for c in (D.home.values[i], D.away.values[i]):
        if (Y, c) in CONT and (pY, c) in tend: X1[i] += (1 - CONT[(Y, c)]) * np.mean(tend[(pY, c)])
resid_test('Ε1 (1−συνεχεια)×περσινη ταση, αγων 1-6', X1, early=True)
E6 = GN <= 5
PR1 = {k: np.where(E6, FIN + k * X1, FIN) for k in (0, -.25, -.5, -.75, -1)}
ys1 = [Y for Y in EV8 if (np.abs(X1[(seasn == Y) & E6]) > 0).any()]
H1 = loso(PR1, 0, 'Ε1 συνεχεια ροστερ (RMSE αγων 1-6)', ys1, E6)
# ================= Ε2 χαμηλη διαθεση =================
P(''); P('################ Ε2 ΔΕΙΚΤΗΣ «ΧΑΜΗΛΗΣ ΔΙΑΘΕΣΗΣ» ################')
X2 = NEXTD + (DEAD > 0) + KO
P(f'  κατανομη: 0: {(X2 == 0).sum()} · 1: {(X2 == 1).sum()} · 2+: {(X2 >= 2).sum()}')
resid_test('Ε2 δεικτης (ανα μοναδα)', X2.astype(float))
PR2 = {k: FIN + k * X2 for k in (0, -.5, -1, -1.5, -2)}
H2 = loso(PR2, 0, 'Ε2 χαμηλη διαθεση', EV8)
# ================= Ε4 εδρα =================
P(''); P('################ Ε4 ΕΔΡΑ «ΨΗΛΩΝ ΣΥΝΟΛΩΝ» (μονο προηγουμενες σεζον) ################')
R = TOT - FIN
X4 = np.zeros(len(D))
for i in range(len(D)):
    Y = int(seasn[i][1:]); h = D.home.values[i]
    prev = (D.home.values == h) & np.array([int(s[1:]) < Y for s in seasn]) & np.isfinite(R)
    n = prev.sum()
    if n: X4[i] = R[prev].sum() / (n + 15)
resid_test('Ε4 εδρα (περσινα υπολοιπα)', X4)
PR4 = {k: FIN + k * X4 for k in (0, .25, .5, .75, 1)}
ys4 = [Y for Y in EV8 if (np.abs(X4[seasn == Y]) > 0).any()]
H4 = loso(PR4, 0, 'Ε4 εδρα', ys4)
# ================= Ε5 πρωταθλημα =================
P(''); P('################ Ε5 ΠΡΩΤΑΘΛΗΜΑ ΟΜΑΔΑΣ (απο τις αλλες σεζον) ################')
LGA = np.array([(MAPD.get((seasn[i], D.away.values[i])) or (0, 0, '—'))[2] for i in range(len(D))])
X5 = np.zeros(len(D))
for Y in EV8 + ['U2017']:
    tr = (seasn != Y) & np.isfinite(R) & np.isin(seasn, EV8 + ['U2017'])
    acc = collections.defaultdict(list)
    for i in np.where(tr)[0]:
        acc[LGH[i]].append(R[i]); acc[LGA[i]].append(R[i])
    eff = {L: sum(v) / (len(v) + 40) for L, v in acc.items() if L != '—'}
    for i in np.where(seasn == Y)[0]: X5[i] = (eff.get(LGH[i], 0) + eff.get(LGA[i], 0)) / 2
P('  επιδραση ανα πρωταθλημα (ολες οι σεζον): ' + ' · '.join(f'{L} {np.mean([R[i] for i in range(len(D)) if (LGH[i] == L or LGA[i] == L) and np.isfinite(R[i])]):+.1f}'
                                                          for L, c in collections.Counter(list(LGH) + list(LGA)).most_common(10) if L != '—'))
resid_test('Ε5 πρωταθλημα', X5)
PR5 = {k: FIN + k * X5 for k in (0, .5, 1)}
H5 = loso(PR5, 0, 'Ε5 πρωταθλημα', EV8)
# ================= Ε3 χρονισμος =================
P(''); P('################ Ε3 ΧΡΟΝΙΣΜΟΣ ΣΥΝΟΛΩΝ (κανονας live) ################')
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] == 23: ROWS[r['ngid']] = r['rows']
ix2 = collections.defaultdict(list)
for i in range(len(D)): ix2[(int(D.hs.values[i]), int(D.as_.values[i]))].append(i)
from statistics import NormalDist
NN = NormalDist()
HIST = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
    for key_ in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
        for i in ix2.get(key_, []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit = i; break
        if hit is not None: break
    if hit is None or seasn[hit] not in EVM: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        oo, ou = 1 + x[2], 1 + x[3]; ph = (1 / oo) / (1 / oo + 1 / ou)
        return (x[0] + 8 * 3600, float(x[1]), float(x[1]) + 16.7 * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)), oo, ou)
    HIST[hit] = (tip.timestamp(), [conv(x) for x in rows])
def at(i, cp):
    tip, h = HIST[i]
    if cp == 'open': return h[0]
    if cp == 'close': return h[-1]
    c = [x for x in h if x[0] <= tip - cp * 3600]; return c[-1] if c else None
def pick(i, x, v):
    _, T, mk, oo, ou = x; w, thr = (.5, .06) if GN[i] <= 5 else (1.0, .06)
    po, pq, pu = cov(mk + w * (v[i] - mk), T, 16.7); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
    if max(eo, eu) < thr: return None
    ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
    return ((od - 1) if q > 0 else (0 if q == 0 else -1), ov, mk)
same = [i for i in HIST if (HIST[i][0] - HIST[i][1][0][0]) / 3600 >= 12 and np.isfinite(FIN[i])]
P(f'  ιδια ματς (ανοιχτα ≥12ω πριν): {len(same)} · Crown συνολα ανοιγουν (διαμεσος) {np.median([(t - h[0][0]) / 3600 for t, h in HIST.values()]):.1f}ω πριν')
for per, f in (('ολη', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
    base = None
    for cp in ('open', 12, 6, 3, 1, 'close'):
        Rr = [(pick(i, at(i, cp), FIN), seasn[i]) for i in same if f(GN[i]) and at(i, cp)]
        Rr = [(p[0], Y) for p, Y in Rr if p]
        a = np.array([x[0] for x in Rr]); ps = {Y: np.mean([x[0] for x in Rr if x[1] == Y]) for Y in EVM if any(x[1] == Y for x in Rr)}
        if cp == 'open': base = ps
        better = sum(1 for Y in ps if Y in base and ps[Y] > base[Y]) if cp != 'open' else None
        P(f'   {per:9s} {str(cp) + ("ω" if isinstance(cp, int) else ""):6s} picks {len(a):4d} · ROI {a.mean()*100 if len(a) else 0:+6.1f}% · {a.sum():+6.1f}u · θετ. {sum(v > 0 for v in ps.values())}/{len(ps)}'
          + (f' · καλυτερο απο ανοιγμα {better}/{len(ps)}' if better is not None else ''))
clv = []
for i in same:
    p = pick(i, at(i, 'open'), FIN)
    if p: clv.append((at(i, 'close')[2] - p[2]) * (1 if p[1] else -1))
P(f'  picks ανοιγματος: η αγορα κινηθηκε προς εμας {np.mean(clv):+.2f} π. (υπερ {np.mean(np.array(clv) > .05):.0%} / κατα {np.mean(np.array(clv) < -.05):.0%})')
# ================= ΤΕΛΙΚΟ =================
FIN2 = FIN.copy(); used = []
for (h, ok, k), lab, X, msk in ((H1, 'Ε1', X1, E6), (H2, 'Ε2', X2, None), (H4, 'Ε4', X4, None), (H5, 'Ε5', X5, None)):
    if ok and k != 0:
        FIN2 = np.where(msk if msk is not None else True, FIN2 + k * X, FIN2); used.append(f'{lab} κ {k}')
P(''); P(f'################ ΤΕΛΙΚΟ: {"live + " + ", ".join(used) if used else "τιποτα δεν περασε — μενει το live"} ################')
def evaluate(v, lab):
    for per, f in (('ολη', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
        ii = [i for i in MKT if seasn[i] in EVM and np.isfinite(v[i]) and f(GN[i])]
        b, t = k2(v[ii] - MC[ii], TOT[ii] - MC[ii])
        Rr = []
        for i in ii:
            T, mk, oo, ou = MKT[i]['o']; p = pick(i, (0, T, mk, oo, ou), v)
            if p: Rr.append((p[0], seasn[i]))
        a = np.array([x[0] for x in Rr]); pos = sum(1 for Y in EVM if [x for x in Rr if x[1] == Y] and np.mean([x[0] for x in Rr if x[1] == Y]) > 0)
        P(f'  [{lab}] {per:9s} λαθος {np.sqrt(np.mean((TOT[ii] - v[ii]) ** 2)):.2f} (κλεισ. {np.sqrt(np.mean((TOT[ii] - MC[ii]) ** 2)):.2f}) · Κ2 {b:+.2f} (t {t:+.1f}) · ROI κανονα live {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/6)')
evaluate(FIN, 'live')
if used: evaluate(FIN2, 'ΝΕΟ')
open('ec_totals_extra_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
