# -*- coding: utf-8 -*-
"""t118_pace_halflife.py (παραγωγο του t112) · ΞΕΧΩΡΙΣΤΗ ΜΝΗΜΗ ΡΥΘΜΟΥ (HL κατοχων) ΟΛΗ ΤΗ ΣΕΖΟΝ στα ΣΥΝΟΛΑ (27/10/2026, Στελιος «δες το»).
Οι βαθμολογιες επιθεσης/αμυνας μενουν live (HL 45)· αλλαζει ΜΟΝΟ το βαρος των ματς στον υπολογισμο του ρυθμου: HL ρυθμου {45 = live, 30, 20, 15}.
ΚΡΙΤΗΡΙΟ: σφαλμα καλυτερο ≥4/5 σεζον ΚΑΙ μοναδες ≥ live ΚΑΙ CLV οχι χειροτερο.
--- ΠΑΡΑΚΑΤΩ το αρχικο κειμενο του t112 ---
 — NBA: «ΠΙΟ ΓΡΗΓΟΡΗ ΕΝΗΜΕΡΩΣΗ ΤΟ ΧΕΙΜΩΝΑ» (27/10/2026, Στελιος «ναι» στον ορισμο· θεμα 7 της λιστας).
ΑΦΟΡΜΗ (t105 Υ1): Δεκ-Φεβ το μοντελο μενει πιο πισω απο το κλεισιμο (χαντ +.18/+.26/+.36, συνολα +.32/+.59/+.43), Ιαν CLV το χαμηλοτερο
  και η αγορα κοντρα 40-43%. Ιδεα: οι ομαδες αλλαζουν μεσα στη σεζον και το μοντελο «ξεχναει» τα παλια ματς πολυ αργα.
ΜΗΧΑΝΙΣΜΟΣ: χρονος ημιζωης (HL, μερες) των βαρων των ματς ΜΟΝΟ για προβλεψεις με ημερομηνια Δεκ/Ιαν/Φεβ· τους αλλους μηνες ο live.
  Η μηχανη ξαναλυνει καθε μερα απο την αρχη → οι αλλοι μηνες μενουν ΑΚΡΙΒΩΣ ιδιοι (ελεγχος).
  ΧΑΝΤΙΚΑΠ: CFG_H live (HL 60) · χειμωνας HL {60 = live, 45, 30, 20} · picks πανω στο αντιγραφο live του t22/t90 + Δ μηχανης.
  ΣΥΝΟΛΑ: live μηχανη συνολων (run_all_split, HL 45, αμυνα .25) · χειμωνας HL {45 = live, 30, 20} · picks πανω στο _t104 (eng − .5·LO + 1.0·LD) + Δ.
  Ανοιγμα Crown · edge ≥8% · χαντικαπ Ιαν-Φεβ 12% (οπως live) · 5 σεζον 2021-22 … 2025-26.
ΜΕΤΡΗΣΕΙΣ: σφαλμα (RMSE) Δεκ/Ιαν/Φεβ και ανα σεζον (Δεκ-Φεβ) · χασμα με το κλεισιμο · μοναδες/ROI/CLV picks (ολα & Δεκ-Φεβ, ανα μηνα).
ΚΡΙΤΗΡΙΟ (προ-δηλωμενο): ΠΕΡΝΑ αν σφαλμα Δεκ-Φεβ καλυτερο σε ≥4/5 σεζον ΚΑΙ μοναδες (ολη η σεζον) ≥ live.
  + LOSO: HL χειμωνα επιλεγεται απο το σφαλμα Δεκ-Φεβ των ΑΛΛΩΝ 4 σεζον → εφαρμογη στην 5η (μοναδες & σφαλμα εκτος δειγματος).
Εξοδος: nba_tests/t112_winter_halflife_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import nba_full_clean_test as F
WIN = (12, 1, 2)
CFG_H = (0.8, 8, 60, .75, 5.0, 1.0, .75, .25)
CFG_T = (0.7, 6, 45, .5, 5.0, 0.0, 0.0, 0.0); WDEF = 0.25
HL_H = (60,); HL_T = (45, 30, 20, 15)

def eng(args):
    """kind 'h' (run_all) ή 't' (run_all_split) με HL χειμωνα hw για προβλεψεις Δεκ-Φεβ."""
    kind, hw = args
    if 'C' not in F._W: F._init()
    C = F._W['C']; Z = F._W['Z']; G = C.G
    cfg = CFG_H if kind == 'h' else CFG_T
    carry, lam, HL, lw, muw, beta, kx, kp = cfg; h = 2.0
    wd = lw if kind == 'h' else WDEF
    for w_ in (lw, wd):
        if w_ not in C.EHA: C.EHA[w_] = C.luck_eff(w_)
    EHo, EAo = C.EHA[lw]; EHd, EAd = C.EHA[wd]; R2 = C._radj2()['V0|W1']
    MON = G.date.dt.month.values
    mg = np.full(len(G), np.nan); tt = np.full(len(G), np.nan); prO, prD, prP = {}, {}, {}
    m0o = float((EHo.mean() + EAo.mean()) / 2); m0d = float((EHd.mean() + EAd.mean()) / 2); pm0 = float(G.pace.mean())
    for s in C.SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        adj = np.array([beta * R2.get(f'{s}|{t}', 0.0) + kx * Z['C'].get(f'{s}|{t}', 0.0) + kp * Z['P'].get(f'{s}|{t}', 0.0) for t in teams])
        g_ = lambda pr, j: carry * np.array([pr.get(t, (0, 0))[j] for t in teams])
        o0, d0o, o0d, d0 = g_(prO, 0) + adj / 2, g_(prO, 1) - adj / 2, g_(prD, 0) + adj / 2, g_(prD, 1) - adj / 2
        p0 = carry * np.array([prP.get(t, 0.0) for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        nt = (~G.neutral.values[sidx]).astype(float); hb = nt * h / 2; dn = C.dnum[sidx]; pc = G.pace.values[sidx]; mo = MON[sidx]
        eho, eao, ehd, ead = EHo[sidx], EAo[sidx], EHd[sidx], EAd[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            HLd = HL; HLp = hw
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HLd)
                mA, O, Do_ = F.fit_mu(hi[past], ai[past], eho[past], eao[past], hb[past], w, n, o0, d0o, lam, m0o, muw)
                if kind == 'h': mB, Dd = mA, Do_
                else: mB, _, Dd = F.fit_mu(hi[past], ai[past], ehd[past], ead[past], hb[past], w, n, o0d, d0, lam, m0d, muw)
                pm, Pc = C.fit_pace(hi[past], ai[past], pc[past], 0.5 ** ((d - dn[past]) / HLp), n, p0, lam, pm0)
            else:
                mA, mB, O, Dd, pm, Pc = m0o, m0d, o0, (d0o if kind == 'h' else d0), pm0, p0
            mu = mA if kind == 'h' else (mA + mB) / 2
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100; tt[sidx[cur]] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)                                  # τελος σεζον (αφετηρια επομενης) = live HL
        mA, O, Do = F.fit_mu(hi, ai, eho, eao, hb, w, n, o0, d0o, lam, m0o, muw)
        if kind == 'h': Od, Dd, mB = O, Do, mA
        else: mB, Od, Dd = F.fit_mu(hi, ai, ehd, ead, hb, w, n, o0d, d0, lam, m0d, muw)
        pm, Pc = C.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prO = {t: (O[i], Do[i]) for t, i in ix.items()}; prD = {t: (Od[i], Dd[i]) for t, i in ix.items()}; prP = {t: Pc[i] for t, i in ix.items()}
        m0o, m0d, pm0 = mA, mB, pm
    return args, mg, tt

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    JOBS = [('t', v) for v in HL_T]
    with Pool(7, initializer=F._init) as pool: R = pool.map(eng, JOBS)
    RES = {a: (mg, tt) for a, mg, tt in R}
    F._init(); C = F._W['C']; G = C.G; MONG = G.date.dt.month.values
    ND = NormalDist()
    def report(lab, live, keys, Y, MU, U, CL, ys, mon):
        SE = sorted(set(ys)); W = np.isin(mon, WIN)  # (αναφορα Δεκ-Φεβ οπως t112)
        rm = lambda k, m: float(np.sqrt(np.nanmean((Y[m] - MU[k][m]) ** 2)))
        roi = lambda k, m: f"{100 * U[k][m & (U[k] != 0)].mean() if (m & (U[k] != 0)).any() else 0:+5.1f}% ({int((m & (U[k] != 0)).sum())})"
        P(f'\n################ {lab} ################')
        P('  εκδοχη          │ σφαλμα Δεκ / Ιαν / Φεβ │ Δεκ-Φεβ ανα σεζον (καλυτερο απο live) │ μοναδες ολη │ μοναδες Δεκ-Φεβ │ ROI Δεκ / Ιαν / Φεβ │ CLV Δεκ-Φεβ')
        for k in keys:
            per = [rm(k, W & (ys == s)) for s in SE]; perL = [rm(live, W & (ys == s)) for s in SE]
            bet = sum(a < b - 1e-9 for a, b in zip(per, perL))
            ok = k != live and bet >= 4 and U[k].sum() >= U[live].sum()
            P(f"  {k:16s} │ {rm(k, mon == 12):.3f} / {rm(k, mon == 1):.3f} / {rm(k, mon == 2):.3f} │ " + ' '.join(f'{s % 100}:{x:.3f}' for s, x in zip(SE, per))
              + (f' ({bet}/5)' if k != live else '      ') + f" │ {U[k].sum():+6.1f} ({int((U[k] != 0).sum())}) │ {U[k][W].sum():+6.1f} ({int((W & (U[k] != 0)).sum())})"
              + f" │ {roi(k, mon == 12)} / {roi(k, mon == 1)} / {roi(k, mon == 2)} │ {np.nanmean(CL[k][W]):+.2f}" + ('  → ΠΕΡΝΑΕΙ' if ok else ('  ✗' if k != live else '')))
        ch, uo, ul, eo, el = [], 0.0, 0.0, [], []
        for s in SE:
            oth = W & (ys != s); cur = ys == s
            b = min(keys, key=lambda k: rm(k, oth)); ch.append(f'{s % 100}:{b}')
            uo += U[b][cur].sum(); ul += U[live][cur].sum(); eo.append(rm(b, W & cur)); el.append(rm(live, W & cur))
        P(f'  LOSO: επιλογες {" · ".join(ch)} → μοναδες {uo:+.1f} vs live {ul:+.1f} · σφαλμα Δεκ-Φεβ καλυτερο σε {sum(a < b - 1e-9 for a, b in zip(eo, el))}/5')
    # ---- ΣΥΝΟΛΑ ----
    T4 = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv'))
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    T4['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(T4.date, T4.home, T4.away)]; T4 = T4[T4.g.notna()].copy(); T4['g'] = T4.g.astype(int)
    gi = T4.g.values; base = RES[('t', 45)][1][gi]
    MUT = {f'HL ρυθμου {v}' + (' (live)' if v == 45 else ''): T4.mu.values + (RES[('t', v)][1][gi] - base) for v in HL_T}
    TOT, TL, OO, OU, FA, CF = (T4[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    def cover_t(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / 18); pu = ND.cdf((T - mu - 0.5) / 18); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / 18); return po, 0.0, 1 - po
    UT, CT = {}, {}
    for k, mu in MUT.items():
        u_, c_ = np.zeros(len(T4)), np.full(len(T4), np.nan)
        for j in range(len(T4)):
            po, pp, pu = cover_t(mu[j], TL[j]); eo, eu = po * OO[j] + pp - 1, pu * OU[j] + pp - 1
            sd, e, od = (1, eo, OO[j]) if eo >= eu else (-1, eu, OU[j])
            if e < .08: continue
            x = (TOT[j] - TL[j]) * sd; u_[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c_[j] = sd * (CF[j] - FA[j])
        UT[k], CT[k] = u_, c_
    P(f'\nελεγχος συνολα live: μοναδες {UT["HL ρυθμου 45 (live)"].sum():+.1f} picks {int((UT["HL ρυθμου 45 (live)"] != 0).sum())} (t104: +143.2, 2505)')
    report('ΣΥΝΟΛΑ (live μηχανη, ανοιγμα Crown, ≥8%)', 'HL ρυθμου 45 (live)', list(MUT), TOT, MUT, UT, CT, T4.sea.values, T4.mon.values)
    # κλεισιμο: χασμα μοντελο − κλεισιμο Δεκ-Φεβ
    W = np.isin(T4.mon.values, WIN)
    P('  χασμα με κλεισιμο Δεκ-Φεβ (σφαλμα μοντελου − σφαλμα κλεισιματος): ' + ' · '.join(
        f'{k}: {np.sqrt(np.mean((TOT[W] - MUT[k][W]) ** 2)) - np.sqrt(np.mean((TOT[W] - CF[W]) ** 2)):+.3f}' for k in MUT))
    ys_ = T4.sea.values; mo_ = T4.mon.values; SE_ = sorted(set(ys_)); L_ = 'HL ρυθμου 45 (live)'
    rm_ = lambda k, m: float(np.sqrt(np.mean((TOT[m] - MUT[k][m]) ** 2)))
    P(chr(10) + 'ΟΛΗ Η ΣΕΖΟΝ (κυριο κριτηριο): σφαλμα ανα σεζον · καλυτερο απο live · μοναδες · CLV · σφαλμα ανα μηνα · ROI Over Ιαν / Μαρ')
    for k in MUT:
        per = [rm_(k, ys_ == s) for s in SE_]; bet = sum(rm_(k, ys_ == s) < rm_(L_, ys_ == s) - 1e-9 for s in SE_)
        u = UT[k]; sdv = np.sign(np.where(u != 0, 1, 0))
        ok = k != L_ and bet >= 4 and u.sum() >= UT[L_].sum() and np.nanmean(CT[k]) >= np.nanmean(CT[L_]) - 1e-9
        P(f"  {k:20s} {rm_(k, ys_ == ys_):.3f} (" + ' '.join(f'{s % 100}:{x:.3f}' for s, x in zip(SE_, per)) + f") {bet}/5 · {u.sum():+.1f} · CLV {np.nanmean(CT[k]):+.2f} · "
          + ' '.join(f'{m}:{rm_(k, mo_ == m):.2f}' for m in (10, 11, 12, 1, 2, 3, 4)) + ('  → ΠΕΡΝΑΕΙ' if ok else ('  ✗' if k != L_ else '')))
    open(os.path.join(SC, 't118_pace_halflife_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
