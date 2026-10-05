# -*- coding: utf-8 -*-
"""dom_bk_euro_games_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 3: ΤΑ ΕΥΡΩΠΑΙΚΑ ΜΑΤΣ ΣΤΟ RATING (5/10/2026, Στελιος «συνεχισε»).
Σημερα: το εγχωριο rating βλεπει ΜΟΝΟ εγχωρια ματς. Οι ομαδες που παιζουν Ευρωπη (EL/EuroCup/BCL/FIBA Europe Cup) παιζουν ~30-40% περισσοτερα ματς.
ΜΗΧΑΝΙΣΜΟΣ: κοινη εκτιμηση εγχωριων + ΟΛΩΝ των ευρωπαικων ματς της σεζον. Ξενες ομαδες = δικες τους παραμετροι (αφετηρια 0, τραβηγμα λ),
  καθε διοργανωση δικο της επιπεδο + κοινη εδρα, και «διορθωση πρωταθληματος» s_c (ποσο καλυτερη ειναι μια ομαδα του πρωταθληματος στη διοργανωση c
  απ' οτι λεει το εγχωριο rating της). Βαρος ευρωπαικων ματς wE ∈ {0 (σημερα), .25, .5, 1}.
Βαση: Ισπανια = σημερινη + ποινη νεοφερμενων −8 (βημα 2 ✓) · Ιταλια = (περσι 1.0, λ 12, HL 120, χωρις τυχη) απο βημα 1.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 με RMSE ΟΛΩΝ των εγχωριων ματς → ΑΛΛΑΓΗ αν καλυτερο απο wE=0 σε ≥4/5 σεζον.
  Αναφορα: εγχωρια ματς με ομαδα Ευρωπης · αγων 1-10 · Κ2 · ROI.
Εξοδος: dom_bk_euro_games_test_out.txt"""
import sys, json, math, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ARGS = ['GBL', 'TBL', 'LNB', 'BBL']; EU = ['EL', 'EC', 'BCL', 'FEC']
src = open('dom_bk_engine_test.py', encoding='utf-8').read()
head = src.split("LIVE = (.7, 8, 9999, .5, False)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
head = head.replace("NS = {'LG_': ARGS}", "NS = {'LG_': ARGS + " + repr(EU) + "}")
mk = src[src.index("# ---- αγορα (για αναφορα) ----"):src.index("for lg in ARGS:\n    P(''); P(f'############")]
NS = {'__name__': 'x'}
sys.argv = [sys.argv[0]] + ARGS
exec(head, NS); exec(mk, NS)
G, EFF, YRS, NAME, rm, EV, P, out, market_report = (NS[k] for k in ('G', 'EFF', 'YRS', 'NAME', 'rm', 'EV', 'P', 'out', 'market_report'))
out.clear()
NAME.update(GBL='Ελλαδα', TBL='Τουρκια', LNB='Γαλλια', BBL='Γερμανια')
HW, MUW = 50.0, 5.0
BASE = {'GBL': (1.0, 4, 9999, None, 0), 'TBL': (1.0, 4, 60, .5, 0), 'LNB': (.7, 8, 9999, .5, 0), 'BBL': (.7, 8, 9999, .5, 0)}
LGV, YV, HID, AID, DV = G.lg.values, G.y.values, G.hid.values, G.aid.values, G.d.values
def run(lg, carry, lam, HL, w, delta, wE):
    EH, EA, PC = EFF[w]
    idx_all = np.where(LGV == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int); eut = np.zeros(len(G), bool)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]]))
    for y in YRS:
        sidx = idx_all[YV[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(HID[sidx]) | set(AID[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        eidx = np.where(np.isin(LGV, EU) & (YV == y))[0] if wE > 0 else np.array([], int)
        foreign = sorted((set(HID[eidx]) | set(AID[eidx])) - set(teams)); fx = {t: i for i, t in enumerate(foreign)}; m = len(foreign)
        inEU = set(HID[np.isin(LGV, EU) & (YV == y)]) | set(AID[np.isin(LGV, EU) & (YV == y)])
        # στηλες: 0 mu, 1 h, O(n), D(n), muc(4), hE, Of(m), Df(m), s(4)
        cM, cH, cO, cD = 0, 1, 2, 2 + n; cMC = 2 + 2 * n; cHE = cMC + 4; cOF = cHE + 1; cDF = cOF + m; cS = cDF + m; NC = cS + 4
        isnew = {t: (y > YRS[0] and t not in prior) for t in teams}
        o0 = np.array([delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[0] for t in teams])
        d0 = np.array([-delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[1] for t in teams])
        # γραμμες παρατηρησεων: (ημερα, βαρος-ειδος, δεικτες/συντελεστες, τιμη)
        R, Y, DAY, KIND = [], [], [], []
        def oc(t): return (cO + ix[t]) if t in ix else (cOF + fx[t])
        def dc(t): return (cD + ix[t]) if t in ix else (cDF + fx[t])
        for i in sidx:
            a_, b_ = HID[i], AID[i]
            R.append([(cM, 1), (cH, .5), (oc(a_), 1), (dc(b_), 1)]); Y.append(EH[i]); DAY.append(DV[i]); KIND.append(0)
            R.append([(cM, 1), (cH, -.5), (oc(b_), 1), (dc(a_), 1)]); Y.append(EA[i]); DAY.append(DV[i]); KIND.append(0)
        for i in eidx:
            a_, b_ = HID[i], AID[i]; c = EU.index(LGV[i]); sa = (a_ in ix) - (b_ in ix)
            R.append([(cMC + c, 1), (cHE, .5), (oc(a_), 1), (dc(b_), 1)] + ([(cS + c, .5 * sa)] if sa else [])); Y.append(EH[i]); DAY.append(DV[i]); KIND.append(1)
            R.append([(cMC + c, 1), (cHE, -.5), (oc(b_), 1), (dc(a_), 1)] + ([(cS + c, -.5 * sa)] if sa else [])); Y.append(EA[i]); DAY.append(DV[i]); KIND.append(1)
        X = np.zeros((len(R), NC))
        for r, cs in enumerate(R):
            for c, v in cs: X[r, c] += v
        Y = np.array(Y); DAY = np.array(DAY); KW = np.where(np.array(KIND) == 1, wE, 1.0)
        pw = np.zeros(NC); pv = np.zeros(NC)
        pw[cO:cO + n] = lam; pv[cO:cO + n] = o0; pw[cD:cD + n] = lam; pv[cD:cD + n] = d0
        pw[cH] = HW; pv[cH] = h0; pw[cM] = MUW; pv[cM] = mu0
        pw[cMC:cMC + 4] = 1.0; pv[cMC:cMC + 4] = mu0; pw[cHE] = HW; pv[cHE] = h0
        pw[cOF:cOF + 2 * m] = lam; pw[cS:cS + 4] = 2.0
        def solve(msk, dref):
            ww = KW[msk] * 0.5 ** ((dref - DAY[msk]) / HL); Xm = X[msk]
            A = Xm.T @ (Xm * ww[:, None]) + np.diag(pw); b = Xm.T @ (ww * Y[msk]) + pw * pv
            return np.linalg.solve(A, b)
        dn = DV[sidx]; cnt = {}
        for i in sidx:
            a_, b_ = HID[i], AID[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
            eut[i] = a_ in inEU or b_ in inEU
        for d in np.unique(dn):
            past = DAY < d; cur = sidx[dn == d]
            if (past & (np.array(KIND) == 0)).any():
                x = solve(past, d); h, O, D = x[cH], x[cO:cO + n], x[cD:cD + n]
                pdm = sidx[dn < d]; pace = float(np.mean(PC[pdm][-200:]))
            else:
                h, O, D, pace = h0, o0, d0, float(np.mean(PC[idx_all]))
            for i in cur:
                p, q = ix[HID[i]], ix[AID[i]]
                pred[i] = pace * ((h + O[p] + D[q]) - (O[q] + D[p])) / 100
        x = solve(np.ones(len(Y), bool), DAY.max())
        prior = {t: (x[cO + i], x[cD + i]) for t, i in ix.items()}; h0, mu0 = x[cH], x[cM]
        if wE > 0 and y == 2025: SINFO[(lg, wE)] = x[cS:cS + 4]
    return pred, gn, eut
SINFO = {}
WE = (0, .25, .5, 1.0)
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} (περσι, λ, HL, τυχη, ποινη νεοφερμ.) ############')
    PR = {we: run(lg, *BASE[lg], we) for we in WE}
    _, gn, eut = PR[0]
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    P(f'  εγχωρια ματς με ομαδα Ευρωπης: {(eut & (LGV == lg) & np.isin(YV, EV)).sum()} απο {((LGV == lg) & np.isin(YV, EV)).sum()}')
    P('  IN-SAMPLE RMSE ανα wE (ολα · με ομαδα Ευρωπης · αγων 1-10):')
    for we in WE:
        P(f'    wE {we:4.2f}: {rmm(PR[we][0], EV):.3f} · {rmm(PR[we][0], EV, eut):.3f} · {rmm(PR[we][0], EV, gn <= 10):.3f}'
          + (f'   (s_c 2025-26 EL/EC/BCL/FEC: ' + ' '.join(f'{v:+.1f}' for v in SINFO[(lg, we)]) + ')' if we > 0 else ''))
    held = np.full(len(G), np.nan); ch = []
    for Y_ in EV:
        tr = [x for x in EV if x != Y_]; we = min(WE, key=lambda we: rmm(PR[we][0], tr)); ch.append(we)
        mm = (LGV == lg) & (YV == Y_); held[mm] = PR[we][0][mm]
    base = PR[0][0]
    for lab, msk in (('ΟΛΑ', None), ('με ομαδα Ευρωπης', eut), ('αγων 1-10', gn <= 10)):
        d = [rmm(held, [Y_], msk) - rmm(base, [Y_], msk) for Y_ in EV]
        P(f'  LOSO {lab:18s} wE {ch} · {rmm(base, EV, msk):.3f} → {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d)
          + f' → {sum(x < 0 for x in d)}/5' + (('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗') if lab == 'ΟΛΑ' else ''))
    market_report(base, lg, 'wE 0 (σημερα)')
    market_report(held, lg, 'LOSO wE')
    for we in WE[1:]: market_report(PR[we][0], lg, f'wE {we}')
open('dom_bk_euro_games_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
