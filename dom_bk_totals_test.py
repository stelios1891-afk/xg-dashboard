# -*- coding: utf-8 -*-
"""dom_bk_totals_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 9: ΣΥΝΟΛΑ ΠΟΝΤΩΝ (5/10/2026, Στελιος «συνεχισε»).
Συνολο = ρυθμος × (αποδ. γηπ + αποδ. φιλ)/100 απο την ιδια μηχανη (η εδρα αλληλοαναιρειται). Σημερα: ιδιες ρυθμισεις με το χαντικαπ.
ΜΗΧΑΝΙΣΜΟΙ (ο καθενας ξεχωριστα, LOSO 2021-26 με RMSE ΣΥΝΟΛΟΥ ολων των ματς, ΑΛΛΑΓΗ αν καλυτερο σε ≥4/5 σεζον):
  (α) μηχανη: τυχη {ωμο, .5, .25} × περσι {.35, .7, 1} × επιπεδο λιγκας μ_w {5 (σημερα), 50 (σχεδον σταθερο)}
  (β) ρυθμος ανα ομαδα λp {κοινος, 20, 8, 3} (πανω στο (α))
  (γ) καμπυλη σεζον: συνολο += a + b·(αριθμος αγωνα) απο τις ΑΛΛΕΣ σεζον (πανω στο (β))
ΑΓΟΡΑ (Crown + Bet365 μεσος, Nowgoal t 23): Κ2 vs κλεισιμο: b ≥ .15 ΚΑΙ t ≥ 2 ΚΑΙ θετικη σε ≥4/5 σεζον = ΠΕΡΝΑ (το μοντελο ξερει κατι).
  ROI over/under (σ = τυπ. αποκλιση πραγμ − κλεισιμο ανα λιγκα): μοντελο μονο ≥8% · μιξη 50/50 ≥6% · ανοιγμα/κλεισιμο = αναφορα.
Εξοδος: dom_bk_totals_test_out.txt"""
import sys, json, math, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ARGS = ['ACB', 'LBA']
src = open('dom_bk_engine_test.py', encoding='utf-8').read()
head = src.split("LIVE = (.7, 8, 9999, .5, False)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
mk = src[src.index("# ---- αγορα (για αναφορα) ----"):src.index("for lg in ARGS:\n    P(''); P(f'############")]
NS = {'__name__': 'x'}
sys.argv = [sys.argv[0]] + ARGS
if True:
    exec(head, NS); exec(mk, NS)
G, EFF, YRS, NAME, fit, act, rm, EV, P, out, market_report, MK = (NS[k] for k in ('G', 'EFF', 'YRS', 'NAME', 'fit', 'act', 'rm', 'EV', 'P', 'out', 'market_report', 'MK'))
out.clear()
BASE = {'ACB': (.7, 8, 9999, .5, False), 'LBA': (1.0, 12, 120, None, False)}
def run(lg, carry, lam, HL, w, team_home, delta, lp=None):
    EH, EA, PC = EFF[w]; TOT = np.full(len(G), np.nan); pace_prev = None
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int); new = np.zeros(len(G), bool)
    pprior = {}; prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]])); fin = {}
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        isnew = {t: (y > YRS[0] and t not in prior) for t in teams}
        o0 = np.array([delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[0] for t in teams])
        d0 = np.array([-delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[1] for t in teams])
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        p0 = np.array([.5 * pprior.get(t, 0.0) for t in teams])
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
            new[i] = isnew[a_] or isnew[b_]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, h, O, D, Hh = fit(hi[past], ai[past], eh[past], ea[past], ww, n, o0, d0, h0, mu0, lam, team_home); pace = float(np.mean(pc[past][-200:]))
                if lp is not None:
                    pm = float(np.mean(pc[past])); Ap = np.zeros((n, n)); bp = np.zeros(n)
                    np.add.at(Ap, (hi[past], hi[past]), 1); np.add.at(Ap, (ai[past], ai[past]), 1); np.add.at(Ap, (hi[past], ai[past]), 1); np.add.at(Ap, (ai[past], hi[past]), 1)
                    rr = pc[past] - pm; np.add.at(bp, hi[past], rr); np.add.at(bp, ai[past], rr)
                    Ap += lp * np.eye(n); bp += lp * p0; tp = np.linalg.solve(Ap, bp)
            else:
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), (pace_prev if pace_prev is not None else float(np.mean(PC[idx_all])))
            for j in cur:
                pg = (pm + tp[hi[j]] + tp[ai[j]]) if (lp is not None and past.any()) else pace
                pred[sidx[j]] = pg * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
                TOT[sidx[j]] = pg * (2 * mu + O[hi[j]] + D[ai[j]] + O[ai[j]] + D[hi[j]]) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu; pace_prev = float(np.mean(pc))
        if lp is not None:
            pmY = float(np.mean(pc)); Ap = np.zeros((n, n)); bp = np.zeros(n)
            np.add.at(Ap, (hi, hi), 1); np.add.at(Ap, (ai, ai), 1); np.add.at(Ap, (hi, ai), 1); np.add.at(Ap, (ai, hi), 1)
            np.add.at(bp, hi, pc - pmY); np.add.at(bp, ai, pc - pmY); tpY = np.linalg.solve(Ap + lp * np.eye(n), bp + lp * p0)
            pprior = {t: tpY[i] for t, i in ix.items()}
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin, TOT
Phi = NS['Phi']; NormalDist_ = NS['NormalDist']; NN = NormalDist_()
# ---- αγορα συνολων ----
import collections
import pandas as pd
ROWS23 = collections.defaultdict(dict)
for ln in open('nowgoal_dom/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 23 and r['lg'] in ARGS: ROWS23[r['ngid']][r['cid']] = r['rows']
D_ = json.load(open('bk_domestic.json', encoding='utf-8'))
idx = collections.defaultdict(list)
for i in np.where(np.isin(G.lg.values, ARGS))[0]: idx[(G.lg.values[i], int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
def conv23(rows):
    R = sorted([x for x in rows if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    return ((float(R[0][1]), 1 + R[0][2], 1 + R[0][3]), (float(R[-1][1]), 1 + R[-1][2], 1 + R[-1][3])) if R else None
MKT = {}
for key, v in D_.items():
    lg, sea = key.split('_')
    if lg not in ARGS: continue
    for g in v['games']:
        ng = int(g[0])
        if ng not in ROWS23: continue
        try: hs, as_ = int(g[4]), int(g[5])
        except Exception: continue
        dd = pd.Timestamp(g[1]).normalize()
        hit = next((i for i in idx.get((lg, hs, as_), []) if abs((G.t.values[i] - dd) / np.timedelta64(1, 'D')) <= 1.5), None)
        if hit is None: continue
        od = {c: conv23(ROWS23[ng].get(c, [])) for c in (3, 8)}; od = {c: x for c, x in od.items() if x}
        if od: MKT[hit] = od
TOTA = (G.hs + G.as_).values.astype(float)
def mexp(T, oo, ou, s):
    po = (1 / oo) / (1 / oo + 1 / ou); return T + s * NN.inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
def cov(mu, T, s):
    if abs(T - round(T)) < 1e-9:
        po = Phi((mu - T - .5) / s); pu = Phi((T - mu - .5) / s); return po, 1 - po - pu, pu
    po = Phi((mu - T) / s); return po, 0.0, 1 - po
def evaluate(v, lg, lab):
    ii = [i for i in MKT if G.lg.values[i] == lg and G.y.values[i] in EV and np.isfinite(v[i])]
    sig = float(np.std([TOTA[i] - float(np.mean([x[1][0] for x in MKT[i].values()])) for i in ii]))
    mc = np.array([np.mean([mexp(*x[1], sig) for x in MKT[i].values()]) for i in ii]); mo = np.array([np.mean([mexp(*x[0], sig) for x in MKT[i].values()]) for i in ii])
    a = TOTA[ii]; vv = v[ii]; yy = G.y.values[ii]
    x = vv - mc; z = a - mc
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = [np.polyfit(x[yy == y], z[yy == y], 1)[0] for y in EV if (yy == y).sum() > 30]; pos = sum(p > 0 for p in per)
    ok = b >= .15 and b / se >= 2 and pos >= 4
    P(f'    {lab:30s} n {len(ii)} · σ {sig:.1f} · RMSE μοντ. {np.sqrt(np.mean((a - vv) ** 2)):.2f} / ανοιγμα {np.sqrt(np.mean((a - mo) ** 2)):.2f} / κλεισιμο {np.sqrt(np.mean((a - mc) ** 2)):.2f}'
      f' · μεση διαφορα μοντ.−κλεισ. {np.mean(x):+.2f} · Κ2 b {b:+.3f} (t {b/se:+.1f}) θετ. {pos}/{len(per)} [' + ' '.join(f'{p:+.2f}' for p in per) + ']' + ('  ΠΕΡΝΑ' if ok else '  ✗'))
    for mlab, wm, thr in (('μοντελο ≥8%', 1.0, .08), ('μιξη 50/50 ≥6%', .5, .06)):
        cells = []
        for wi, when in ((0, 'ανοιγμα'), (1, 'κλεισιμο')):
            R = {'over': [], 'under': []}
            for k, i in enumerate(ii):
                bk = MKT[i].get(3) or MKT[i].get(8); T, oo, ou = bk[wi]; mk_ = mo[k] if wi == 0 else mc[k]
                m_ = mk_ + wm * (vv[k] - mk_); po, pq, pu = cov(m_, T, sig); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
                if max(eo, eu) >= thr:
                    ov = eo >= eu; q = (a[k] - T) * (1 if ov else -1); od_ = oo if ov else ou
                    R['over' if ov else 'under'].append(((od_ - 1) if q > 0 else (0 if q == 0 else -1), yy[k]))
            for s_, L in R.items():
                ar = np.array([q[0] for q in L]); ys = sorted(set(q[1] for q in L)); p_ = sum(1 for y in ys if np.mean([q[0] for q in L if q[1] == y]) > 0)
                cells.append(f'{when} {s_} {ar.mean()*100 if len(ar) else 0:+.1f}% ({len(ar)}, {p_}/{len(ys)})')
        P(f'      ROI {mlab:15s} ' + ' · '.join(cells))
MUW0 = NS['MUW']
def runT(lg, carry, lam, HL, w, muw, lp=None, delta=0):
    globals()['MUW'] = muw; NS['MUW'] = muw
    try: r = run(lg, carry, lam, HL, w, False, delta, lp)
    finally: globals()['MUW'] = MUW0; NS['MUW'] = MUW0
    return r[4], r[1]
def rmT(v, lg, ys, msk=None):
    m = (G.lg.values == lg) & np.isin(G.y.values, ys) & np.isfinite(v) & (msk if msk is not None else True)
    return float(np.sqrt(np.mean((TOTA - v)[m] ** 2)))
def loso(PR, lg, keys, basek, lab):
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; k = min(keys, key=lambda k: rmT(PR[k], lg, tr)); ch.append(k)
        mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PR[k][mm]
    d = [rmT(held, lg, [Y]) - rmT(PR[basek], lg, [Y]) for Y in EV]
    ok = sum(x < 0 for x in d) >= 4
    P(f'  LOSO {lab}: {ch} · {rmT(PR[basek], lg, EV):.3f} → {rmT(held, lg, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if ok else '  <- ✗'))
    return held, ok, ch
BASE = {'ACB': (.7, 8, 9999, .5, -8), 'LBA': (1.0, 12, 120, None, 0)}
for lg in ARGS:
    car, lam, HL, w, dl = BASE[lg]
    P(''); P(f'############ {NAME[lg]} · βαση χαντικαπ {BASE[lg]} ############')
    # (α) μηχανη
    PA = {}; GN = None
    for ww_ in (None, .5, .25):
        for c in (.35, .7, 1.0):
            for muw in (5.0, 50.0):
                PA[(ww_, c, muw)], GN = runT(lg, c, lam, HL, ww_, muw, None, dl)
    b0 = (w, car, 5.0)
    P('  (α) IN-SAMPLE RMSE συνολου (τυχη, περσι, μ_w):')
    for k in sorted(PA, key=lambda k: rmT(PA[k], lg, EV))[:6]: P(f'    {k}: {rmT(PA[k], lg, EV):.3f}')
    P(f'    σημερα {b0}: {rmT(PA[b0], lg, EV):.3f}')
    heldA, okA, chA = loso(PA, lg, list(PA), b0, '(α) μηχανη')
    from collections import Counter
    bA = Counter(chA).most_common(1)[0][0] if okA else b0
    evaluate(PA[b0], lg, 'σημερα')
    if okA: evaluate(heldA, lg, '(α) LOSO')
    # (β) ρυθμος ανα ομαδα
    PB = {None: PA[bA]}
    for lp in (20, 8, 3): PB[lp], _ = runT(lg, bA[1], lam, HL, bA[0], bA[2], lp, dl)
    P('  (β) IN-SAMPLE ρυθμος: ' + ' · '.join(f'λp {k}: {rmT(v, lg, EV):.3f}' for k, v in PB.items()))
    heldB, okB, chB = loso(PB, lg, list(PB), None, '(β) ρυθμος ανα ομαδα')
    if okB: evaluate(heldB, lg, '(β) LOSO')
    cur = heldB if okB else PB[None]
    # (γ) καμπυλη σεζον
    m_ = (G.lg.values == lg) & np.isfinite(cur)
    held = cur.copy(); coefs = []
    for Y in EV:
        tr = m_ & np.isin(G.y.values, [x for x in EV if x != Y])
        bb, aa = np.polyfit(GN[tr], (TOTA - cur)[tr], 1); coefs.append((round(aa, 2), round(bb, 3)))
        mm = m_ & (G.y.values == Y); held[mm] = cur[mm] + aa + bb * GN[mm]
    d = [rmT(held, lg, [Y]) - rmT(cur, lg, [Y]) for Y in EV]
    okC = sum(x < 0 for x in d) >= 4
    P(f'  LOSO (γ) καμπυλη (a, b): {coefs} · {rmT(cur, lg, EV):.3f} → {rmT(held, lg, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if okC else '  <- ✗'))
    P('    υπολοιπο (πραγμ − μοντ) ανα αγων: ' + ' · '.join(f'{lo}-{hi}: {np.mean((TOTA - cur)[m_ & np.isin(G.y.values, EV) & (GN >= lo) & (GN <= hi)]):+.2f}' for lo, hi in ((1, 5), (6, 10), (11, 20), (21, 30), (31, 45))))
    if okC: evaluate(held, lg, '(γ) LOSO')
    fin = held if okC else cur
    P('  ΤΕΛΙΚΟ (ο,τι περασε):'); evaluate(fin, lg, 'τελικο')
open('dom_bk_totals_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
