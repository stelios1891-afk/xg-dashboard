# -*- coding: utf-8 -*-
"""dom_bk_newcomers_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 2: ΟΜΑΔΕΣ ΠΟΥ ΑΝΕΒΗΚΑΝ ΚΑΤΗΓΟΡΙΑ (5/10/2026, Στελιος «συνεχισε»).
Σημερα: ομαδα χωρις περσινη σεζον στο πρωταθλημα ξεκινα στη ΜΕΣΗ (0). Δεν εχουμε δεδομενα 2ης κατηγοριας → τεστ σταθερης «ποινης» δ.
Βαση (απο το βημα 1): Ισπανια = σημερινη (περσι .7, λ 8, χωρις μνημη, τυχη .5) · Ιταλια = νεα (περσι 1.0, λ 12, HL 120, χωρις τυχη).
ΠΛΕΓΜΑ: δ ∈ {0, −2, −4, −6, −8, −10, −12} ποντοι/100 κατοχες (≈ ×0.72 ποντοι/ματς) για την αφετηρια της νεοφερμενης.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 με RMSE ΟΛΩΝ των ματς → ΑΛΛΑΓΗ αν καλυτερο απο δ=0 σε ≥4/5 σεζον.
  Αναφορα: ματς με νεοφερμενη (ολα / αγων 1-10) · Κ2 · ROI · ποσο «ειναι» οι νεοφερμενες στο τελος (vs μεση).
Εξοδος: dom_bk_newcomers_test_out.txt"""
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
def run(lg, carry, lam, HL, w, team_home, delta):
    EH, EA, PC = EFF[w]
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int); new = np.zeros(len(G), bool)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]])); fin = {}
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        isnew = {t: (y > YRS[0] and t not in prior) for t in teams}
        o0 = np.array([delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[0] for t in teams])
        d0 = np.array([-delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[1] for t in teams])
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
            new[i] = isnew[a_] or isnew[b_]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, h, O, D, Hh = fit(hi[past], ai[past], eh[past], ea[past], ww, n, o0, d0, h0, mu0, lam, team_home); pace = float(np.mean(pc[past][-200:]))
            else:
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), float(np.mean(PC[idx_all]))
            for j in cur:
                pred[sidx[j]] = pace * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin
DELTAS = (0, -2, -4, -6, -8, -10, -12)
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} ############')
    PR = {dl: run(lg, *BASE[lg], dl) for dl in DELTAS}
    _, gn, new, fin = PR[0]
    nn = [(y, v) for (y, t), v in fin.items() if v[1] and y in EV]
    P(f'  νεοφερμενες 2021-26: {len(nn)} ({", ".join(f"{y}: {sum(1 for yy, v in nn if yy == y)}" for y in EV)}) · '
      f'τελικη δυναμη (π./ματς vs μεση) {np.mean([v[0] for y, v in nn]):+.2f} · παλιες {np.mean([v[0] for (y, t), v in fin.items() if not v[1] and y in EV]):+.2f}')
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    P('  IN-SAMPLE RMSE ανα δ (ολα · ματς με νεοφερμενη · με νεοφερμενη αγων 1-10):')
    for dl in DELTAS:
        P(f'    δ {dl:+4d}: {rmm(PR[dl][0], EV):.3f} · {rmm(PR[dl][0], EV, new):.3f} · {rmm(PR[dl][0], EV, new & (gn <= 10)):.3f}')
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; dl = min(DELTAS, key=lambda dl: rmm(PR[dl][0], tr)); ch.append(dl)
        m = (G.lg.values == lg) & (G.y.values == Y); held[m] = PR[dl][0][m]
    base = PR[0][0]
    for lab, msk in (('ΟΛΑ', None), ('με νεοφερμενη', new), ('με νεοφερμενη αγων 1-10', new & (gn <= 10))):
        d = [rmm(held, [Y], msk) - rmm(base, [Y], msk) for Y in EV]
        P(f'  LOSO {lab:24s} δ {ch} · {rmm(base, EV, msk):.3f} → {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d)
          + f' → {sum(x < 0 for x in d)}/5' + (('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗') if lab == 'ΟΛΑ' else ''))
    market_report(base, lg, 'δ 0 (σημερα)')
    market_report(held, lg, 'LOSO δ')
open('dom_bk_newcomers_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
