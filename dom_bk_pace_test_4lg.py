# -*- coding: utf-8 -*-
"""dom_bk_pace_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 5: ΡΥΘΜΟΣ ΑΝΑ ΟΜΑΔΑ στο χαντικαπ (5/10/2026, Στελιος «συνεχισε»).
Σημερα: διαφορα = ΚΟΙΝΟΣ ρυθμος πρωταθληματος (μεσος 200 τελευταιων) × διαφορα αποδοτικοτητας /100.
ΜΗΧΑΝΙΣΜΟΣ: ρυθμος ματς = μεσος + p_γηπ + p_φιλ (ridge λp, αφετηρια ½ του περσινου p) — γρηγορες ομαδες «μεγαλωνουν» τη διαφορα.
ΠΛΕΓΜΑ λp ∈ {κοινος (σημερα), 20, 8, 3}. Βαση: Ισπανια = σημερινη + ποινη νεοφερμενων −8 · Ιταλια = (1.0, λ 12, HL 120, ωμο).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 με RMSE ΟΛΩΝ των ματς → ΑΛΛΑΓΗ αν καλυτερο σε ≥4/5 σεζον. Αναφορα: αγων 1-10 · Κ2 · ROI.
Εξοδος: dom_bk_pace_test_out.txt"""
import sys, json, math, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ARGS = ['GBL', 'TBL', 'LNB', 'BBL']
src = open('dom_bk_engine_test.py', encoding='utf-8').read()
head = src.split("LIVE = (.7, 8, 9999, .5, False)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
mk = src[src.index("# ---- αγορα (για αναφορα) ----"):src.index("for lg in ARGS:\n    P(''); P(f'############")]
NS = {'__name__': 'x'}
sys.argv = [sys.argv[0]] + ARGS
if True:
    exec(head, NS); exec(mk, NS)
G, EFF, YRS, NAME, fit, act, rm, EV, P, out, market_report, MK = (NS[k] for k in ('G', 'EFF', 'YRS', 'NAME', 'fit', 'act', 'rm', 'EV', 'P', 'out', 'market_report', 'MK'))
out.clear()
NAME.update(GBL='Ελλαδα', TBL='Τουρκια', LNB='Γαλλια', BBL='Γερμανια')
BASE = {'GBL': (1.0, 4, 9999, None, True), 'TBL': (1.0, 4, 60, .5, True), 'LNB': (.7, 8, 9999, .5, False), 'BBL': (.7, 8, 9999, .5, False)}
def run(lg, carry, lam, HL, w, team_home, delta, lp=None):
    EH, EA, PC = EFF[w]
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
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), float(np.mean(PC[idx_all]))
            for j in cur:
                pg = (pm + tp[hi[j]] + tp[ai[j]]) if (lp is not None and past.any()) else pace
                pred[sidx[j]] = pg * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        if lp is not None:
            pmY = float(np.mean(pc)); Ap = np.zeros((n, n)); bp = np.zeros(n)
            np.add.at(Ap, (hi, hi), 1); np.add.at(Ap, (ai, ai), 1); np.add.at(Ap, (hi, ai), 1); np.add.at(Ap, (ai, hi), 1)
            np.add.at(bp, hi, pc - pmY); np.add.at(bp, ai, pc - pmY); tpY = np.linalg.solve(Ap + lp * np.eye(n), bp + lp * p0)
            pprior = {t: tpY[i] for t, i in ix.items()}
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin
BASE = {'GBL': (1.0, 4, 9999, None, True, 0), 'TBL': (1.0, 4, 60, .5, True, 0), 'LNB': (.7, 8, 9999, .5, False, 0), 'BBL': (.7, 8, 9999, .5, False, 0)}
LP = (None, 20, 8, 3)
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} ############')
    PR = {lp: run(lg, *BASE[lg], lp) for lp in LP}
    _, gn, new, fin = PR[None]
    m_ = (G.lg.values == lg) & np.isin(G.y.values, EV)
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    P('  IN-SAMPLE RMSE ανα λp (ολα · αγων 1-10):')
    for lp in LP:
        P(f'    λp {str(lp):>4s}: {rmm(PR[lp][0], EV):.3f} · {rmm(PR[lp][0], EV, gn <= 10):.3f}')
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; lp = min(LP, key=lambda lp: rmm(PR[lp][0], tr)); ch.append(lp)
        mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PR[lp][0][mm]
    base = PR[None][0]
    for lab, msk in (('ΟΛΑ', None), ('αγων 1-10', gn <= 10)):
        d = [rmm(held, [Y], msk) - rmm(base, [Y], msk) for Y in EV]
        P(f'  LOSO {lab:10s} λp {ch} · {rmm(base, EV, msk):.3f} → {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d)
          + f' → {sum(x < 0 for x in d)}/5' + (('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗') if lab == 'ΟΛΑ' else ''))
    market_report(base, lg, 'κοινος ρυθμος (σημερα)')
    market_report(held, lg, 'LOSO λp')
open('dom_bk_pace_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
