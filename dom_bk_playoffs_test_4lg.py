# -*- coding: utf-8 -*-
"""dom_bk_playoffs_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 6: ΠΛΕΙ-ΟΦ (5/10/2026, Στελιος «συνεχισε»).
Σημερα: τα πλει-οφ τιμολογουνται ακριβως οπως η κανονικη περιοδος (ιδια εδρα, ιδια κλιμακα διαφορας δυναμης).
ΜΗΧΑΝΙΣΜΟΙ: (α) εδρα στα πλει-οφ × {0, .5, 1, 1.5, 2} · (β) διαφορα δυναμης × {.9, 1, 1.1, 1.25} (οι καλοι παιζουν περισσοτερα λεπτα / rotation).
Βαση: Ισπανια = σημερινη + ποινη νεοφερμενων −8 · Ιταλια = (1.0, λ 12, HL 120, ωμο).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 με RMSE ΜΟΝΟ των ματς πλει-οφ (επιλογη ζευγους στις αλλες 4) → ΑΛΛΑΓΗ αν
  καλυτερο σε ≥4/5 σεζον. ΠΡΟΣΟΧΗ: ~20-28 ματς/σεζον → θορυβος· αναφορα και Κ2 vs κλεισιμο.
Εξοδος: dom_bk_playoffs_test_out.txt"""
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
BASE = {'GBL': (1.0, 4, 9999, None, True, 0), 'TBL': (1.0, 4, 60, .5, True, 0), 'LNB': (.7, 8, 9999, .5, False, 0), 'BBL': (.7, 8, 9999, .5, False, 0)}
PO = np.array(['Play Offs' in str(s) for s in G.stage.values])
MH = (0, .5, 1.0, 1.5, 2.0); SC = (.9, 1.0, 1.1, 1.25)
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} ############')
    pred, gn, new, fin, HP = run(lg, *BASE[lg])
    m_ = (G.lg.values == lg) & np.isin(G.y.values, EV) & PO & np.isfinite(pred)
    a = act[m_]; v = pred[m_]; hp = HP[m_]; netp = v - hp
    P(f'  πλει-οφ 2021-26: {m_.sum()} ματς · ' + ' '.join(f'{y}: {((G.y.values == y) & m_).sum()}' for y in EV))
    P(f'  υπολοιπο (πραγμ − μοντ) {np.mean(a - v):+.2f} · εδρα μοντελου {np.mean(hp):.2f} · πραγματικη εδρα (μεσος γηπ.) {np.mean(a):+.2f} '
      f'· κλιση πραγμ. στη διαφορα δυναμης {np.polyfit(netp, a - hp, 1)[0]:.2f}')
    PRV = {}
    for mh in MH:
        for sc in SC:
            q = pred.copy(); q[PO] = HP[PO] * mh + (pred[PO] - HP[PO]) * sc; PRV[(mh, sc)] = q
    rmm = lambda v_, ys: rm(v_, lg, ys, PO)
    P('  IN-SAMPLE RMSE πλει-οφ (γραμμη = εδρα ×, στηλη = διαφορα δυναμης ×):')
    P('           ' + ''.join(f'{sc:>8.2f}' for sc in SC))
    for mh in MH:
        P(f'    εδρα ×{mh:3.1f}' + ''.join(f'{rmm(PRV[(mh, sc)], EV):8.3f}' for sc in SC))
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; k = min(PRV, key=lambda k: rmm(PRV[k], tr)); ch.append(k)
        mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PRV[k][mm]
    d = [rmm(held, [Y]) - rmm(pred, [Y]) for Y in EV]
    P(f'  LOSO πλει-οφ επιλογες {ch} · {rmm(pred, EV):.3f} → {rmm(held, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d)
      + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
    ii = [i for i in MK if PO[i] and G.lg.values[i] == lg and G.y.values[i] in EV]
    if ii:
        x = np.array([pred[i] - MK[i]['mc'] for i in ii]); z = np.array([act[i] - MK[i]['mc'] for i in ii])
        P(f'  πλει-οφ με αγορα: {len(ii)} · λαθος μοντελου {np.sqrt(np.mean((act[ii] - pred[ii]) ** 2)):.2f} vs κλεισιμο {np.sqrt(np.mean((act[ii] - np.array([MK[i]["mc"] for i in ii])) ** 2)):.2f} · Κ2 b {np.polyfit(x, z, 1)[0]:+.2f}')
open('dom_bk_playoffs_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
# ---- ελεγχος: τι περιμενε η αγορα στα πλει-οφ ----
for lg in ARGS:
    ii = [i for i in MK if PO[i] and G.lg.values[i] == lg and G.y.values[i] in EV]
    ir = [i for i in MK if not PO[i] and G.lg.values[i] == lg and G.y.values[i] in EV]
    mc = np.array([MK[i]['mc'] for i in ii]); a = act[ii]
    P(f'  {NAME[lg]} πλει-οφ: αγορα (κλεισ.) περιμενε γηπ. {mc.mean():+.2f} · εγινε {a.mean():+.2f} · υπολοιπο vs αγορα {np.mean(a - mc):+.2f} '
      f'(t {np.mean(a - mc) / (np.std(a - mc) / np.sqrt(len(a))):+.1f}) · ανα σεζον ' + ' '.join(f'{np.mean([act[i] - MK[i]["mc"] for i in ii if G.y.values[i] == y]):+.1f}' for y in EV)
      + f' · κανονικη περιοδος υπολοιπο vs αγορα {np.mean([act[i] - MK[i]["mc"] for i in ir]):+.2f}')
open('dom_bk_playoffs_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
