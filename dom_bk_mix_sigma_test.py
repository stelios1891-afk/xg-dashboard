# -*- coding: utf-8 -*-
"""dom_bk_mix_sigma_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 7: ΜΙΞΗ ΜΕ ΑΓΟΡΑ (w), ΑΒΕΒΑΙΟΤΗΤΑ (σ), ΚΑΤΩΦΛΙ (5/10/2026, Στελιος «συνεχισε»).
Σημερα (απο EuroCup): μ = αγορα + .5·(μοντελο − αγορα), σ 12.3, edge ≥6%.
Μηχανη: Ισπανια = σημερινη + ποινη νεοφερμενων −8 + πλει-οφ (εδρα ×0, δυναμη ×1.25) · Ιταλια = (1.0, λ 12, HL 120, ωμο).
ΜΕΤΡΟ (στατιστικο, οχι ROI): log-loss της καλυψης στη γραμμη Crown (ανοιγμα και κλεισιμο ξεχωριστα, push εξω).
ΠΛΕΓΜΑ w {0…1} × σ {11…16}. ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 (επιλογη (w,σ) στις αλλες 4) → ΑΛΛΑΓΗ αν
  log-loss καλυτερο απο το σημερινο (.5, 12.3) σε ≥4/5 σεζον. Κατωφλι edge: ΜΟΝΟ αναφορα ROI ανα κατωφλι (οχι επιλογη).
Εξοδος: dom_bk_mix_sigma_test_out.txt"""
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
Phi = NS['Phi']
out.clear()
BASE = {'ACB': (.7, 8, 9999, .5, False), 'LBA': (1.0, 12, 120, None, False)}
def run(lg, carry, lam, HL, w, team_home, delta):
    EH, EA, PC = EFF[w]; HP = np.full(len(G), np.nan)
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
                HP[sidx[j]] = pace * h / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin, HP
BASE = {'ACB': (.7, 8, 9999, .5, False, -8), 'LBA': (1.0, 12, 120, None, False, 0)}
POADJ = {'ACB': (0.0, 1.25), 'LBA': (1.0, 1.0)}
PO = np.array(['Play Offs' in str(s) for s in G.stage.values])
WS = (0, .1, .2, .3, .4, .5, .6, .75, 1.0); SS = (11.0, 11.5, 12.0, 12.3, 12.5, 13.0, 13.5, 14.0, 15.0, 16.0); CUR = (.5, 12.3)
def probs(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s)
    else: pw = Phi((m_ + L) / s); pl = 1 - pw
    return pw, 1 - pw - pl, pl
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} · πλει-οφ {POADJ[lg]} ############')
    pred, gn, new, fin, HP = run(lg, *BASE[lg])
    mh, sc = POADJ[lg]; pred = pred.copy(); pred[PO] = HP[PO] * mh + (pred[PO] - HP[PO]) * sc
    for when, mk_ in (('op', 'mo'), ('cl', 'mc')):
        ii = [i for i in MK if G.lg.values[i] == lg and G.y.values[i] in EV and np.isfinite(pred[i])]
        LL = {}
        for w in WS:
            for s in SS:
                arr = []
                for i in ii:
                    L, o1, o2 = MK[i][when]; m_ = MK[i][mk_] + w * (pred[i] - MK[i][mk_]); v = act[i] + L
                    if v == 0: continue
                    pw, pp, pl = probs(m_, L, s); p = pw / (pw + pl) if v > 0 else pl / (pw + pl)
                    arr.append((-math.log(max(p, 1e-9)), G.y.values[i]))
                LL[(w, s)] = arr
        mean = lambda k, ys: float(np.mean([q[0] for q in LL[k] if q[1] in ys]))
        best = min(LL, key=lambda k: mean(k, EV))
        P(f'  [{"ΑΝΟΙΓΜΑ" if when == "op" else "ΚΛΕΙΣΙΜΟ"}] log-loss καλυψης (n {len(LL[CUR])}): σημερα w .5/σ 12.3 {mean(CUR, EV):.4f} · καλυτερο {best} {mean(best, EV):.4f} · αγορα μονη (w 0) καλυτερο σ '
          + f'{min(SS, key=lambda s: mean((0, s), EV))} {min(mean((0, s), EV) for s in SS):.4f}')
        P('    ανα w (καλυτερο σ): ' + ' · '.join(f'{w}: {min(mean((w, s), EV) for s in SS):.4f}/σ{min(SS, key=lambda s: mean((w, s), EV))}' for w in WS))
        ch = []; d = []
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(LL, key=lambda k: mean(k, tr)); ch.append(k); d.append(mean(k, [Y]) - mean(CUR, [Y]))
        P(f'    LOSO επιλογες {ch} · ' + ' '.join(f'{x:+.4f}' for x in d) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
        # ROI ανα κατωφλι (σημερινα w/σ και LOSO)
        for lab, sel in (('σημερα .5/12.3', {Y: CUR for Y in EV}), ('LOSO', dict(zip(EV, ch)))):
            cells = []
            for thr in (.03, .06, .09, .12, .15):
                R = []
                for i in ii:
                    w, s = sel[G.y.values[i]]; L, o1, o2 = MK[i][when]; m_ = MK[i][mk_] + w * (pred[i] - MK[i][mk_])
                    pw, pp, pl = probs(m_, L, s); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                    side, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                    if e >= thr:
                        vv = (act[i] + L) * side; R.append(((od_ - 1) if vv > 0 else (0 if vv == 0 else -1), G.y.values[i]))
                a = np.array([q[0] for q in R]); p_ = sum(1 for y in EV if [q for q in R if q[1] == y] and np.mean([q[0] for q in R if q[1] == y]) > 0)
                cells.append(f'≥{thr:.0%} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {p_}/5)')
            P(f'    ROI {lab:15s} ' + ' · '.join(cells))
open('dom_bk_mix_sigma_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
