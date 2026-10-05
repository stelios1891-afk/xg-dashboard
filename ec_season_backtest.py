# -*- coding: utf-8 -*-
"""ec_season_backtest.py — EuroCup: ΤΙ ΛΕΕΙ ΤΟ BACKTEST ΤΟΥ LIVE ec1 ανα αγορα, ολη η σεζον vs ΑΡΧΗ (5/10/2026, Στελιος:
«βλεπω πολλες διαφωνιες με την αγορα — ποσο μπορουμε να τις εμπιστευτουμε; στην αρχη της σεζον εχουμε γνωση οταν διαφωνουμε;»).
Μηχανη = ακριβως live ec1 (HL ∞ · λ 4 · εδρα 5 · τυχη .5 · μ_w 5 · περσι .2 · ειδικοι 4 · φιλικα .5 · εγχωρια κ1) — χαντικαπ ΚΑΙ συνολο.
Αγορα = Crown (Nowgoal) U2020-U2025, ανοιγμα & κλεισιμο. Περιοδοι: αγων 1-3 · 4-6 · 7+ (αριθμος αγωνα = max των 2 ομαδων).
ΜΕΤΡΑ ανα περιοδο: λαθος (RMSE) μοντελο/ανοιγμα/κλεισιμο · Κ2 b (ποσο % της διαφωνιας μας «βγαινει» στο αποτελεσμα· 0 = η αγορα
  ειχε δικιο, 1 = εμεις) vs ανοιγμα ΚΑΙ vs κλεισιμο · κινηση γραμμης προς εμας (ανοιγμα→κλεισιμο) · ανα μεγεθος διαφωνιας:
  ποσο «βγηκε», ποσο κινηθηκε η γραμμη, ROI της πλευρας μας στο ανοιγμα/κλεισιμο (ολα τα ματς, χωρις κατωφλι).
  + ο σημερινος κανονας picks (χαντικαπ, μοντελο σ 11.5, ≥8%) ανα περιοδο.
Εξοδος: ec_season_backtest_out.txt"""
import sys, io, contextlib, json, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('ec_fresh_engine_test.py', encoding='utf-8').read()
src = src.split("LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
NS = {'__name__': 'x'}
if True:
    exec(src, NS)
D, EFF, SEAS, PRE, ZC, dnum, GN, fit_eff_mu, fit_pace, dsh = (NS[k] for k in ('D', 'EFF', 'SEAS', 'PRE', 'ZC', 'dnum', 'GN', 'fit_eff_mu', 'fit_pace', 'dsh'))
def run2T(HLv, lamv, hv, w, muw, carry, kx, kp):
    EH_, EA_ = EFF[w]; pm_ = np.full(len(D), np.nan); pt_ = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH_.mean() + EA_.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, hv / 2)
        ex = np.array([(kp * PRE.get((s, t), 0.0) + kx * ZC.get((s, t), 0.0)) * 100 / 72 for t in teams])
        o0b = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]) + ex / 2
        d0b = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams]) - ex / 2
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH_[sidx]; ea = EA_[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            sh = np.array([dsh(s, t, int(d)) * 100 / 72 for t in teams]); o0 = o0b + sh / 2; d0 = d0b - sh / 2
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HLv)
                mu, O, Dd = fit_eff_mu(hi[past], ai[past], eh[past], ea[past], hb[past], ww, n, o0, d0, lamv, mu0, muw)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], ww, n, p0, lamv, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            for j in cur:
                e_h = mu + O[hi[j]] + Dd[ai[j]] + hb[j]; e_a = mu + O[ai[j]] + Dd[hi[j]] - hb[j]
                pace = pm + Pc[hi[j]] + Pc[ai[j]]
                pm_[sidx[j]] = pace * (e_h - e_a) / 100; pt_[sidx[j]] = pace * (e_h + e_a) / 100
        ww = 0.5 ** ((dn.max() - dn) / HLv)
        mu, O, Dd = fit_eff_mu(hi, ai, eh, ea, hb, ww, n, o0b, d0b, lamv, mu0, muw)
        pm, Pc = fit_pace(hi, ai, pc, ww, n, p0, lamv, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return pm_, pt_
LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)
MARG, TOTP = run2T(*LIVE)
ACT = (D.hs - D.as_).values.astype(float); TOT = (D.hs + D.as_).values.astype(float)
seasn = D.season.values
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf; NN = NormalDist()
# ---- αγορα χαντικαπ (ιδια με ec_sigma_edge_test) ----
import pickle
Z = pickle.load(open('ec_fresh_market.pkl', 'rb'))
chk = np.nanmax(np.abs(Z['live'] - MARG)); P(f'ελεγχος: live προβλεψεις χαντικαπ ιδιες με ec_fresh_market.pkl (μεγιστη διαφορα {chk:.4f})')
MKH = Z['MK']   # i -> {'o': (γραμμη γηπ, αναμ. διαφορα, τιμη γηπ, τιμη φιλ), 'c': ...}
# ---- αγορα συνολων (ιδια με ec_totals_test) ----
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] == 23: ROWS[r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
SIGT = 16.7
MKT = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
    for key_ in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
        for i in ix2.get(key_, []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit = i; break
        if hit is not None: break
    if hit is None: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        oo, ou = 1 + x[2], 1 + x[3]; ph = (1 / oo) / (1 / oo + 1 / ou)
        return (float(x[1]), float(x[1]) + SIGT * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)), oo, ou)
    MKT[hit] = dict(o=conv(rows[0]), c=conv(rows[-1]))
PER = (('αγων 1-3', lambda g: g <= 2), ('αγων 4-6', lambda g: (g >= 3) & (g <= 5)), ('αγων 7+', lambda g: g >= 6), ('ΟΛΗ η σεζον', lambda g: g >= 0))
def settle_h(i, side, L, od):            # side +1 γηπ (γραμμη L γηπ), −1 φιλ
    v = (ACT[i] + L) * side
    return (od - 1) if v > 0 else (0 if v == 0 else -1)
def settle_t(i, side, T, od):            # side +1 over, −1 under
    v = (TOT[i] - T) * side
    return (od - 1) if v > 0 else (0 if v == 0 else -1)
def k2(x, z, ss):
    if len(x) < 15: return float('nan'), float('nan'), 0, 0
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = [np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EVM if (ss == Y).sum() >= 10]
    return b, b / se, sum(p > 0 for p in per), len(per)
def analyse(name, MK, model, actual, settle, buckets, side_of):
    P(''); P(f'################ {name} ################')
    for lab, f in PER:
        ii = np.array([i for i in MK if seasn[i] in EVM and np.isfinite(model[i]) and f(GN[i])])
        if len(ii) < 15: continue
        mo = np.array([MK[i]['o'][1] for i in ii]); mc = np.array([MK[i]['c'][1] for i in ii]); m = model[ii]; a = actual[ii]; ss = seasn[ii]
        rm = lambda v: float(np.sqrt(np.mean((a - v) ** 2)))
        P(f'  [{lab}] n {len(ii)} · λαθος: μοντελο {rm(m):.2f} · ανοιγμα {rm(mo):.2f} · κλεισιμο {rm(mc):.2f} · μεση διαφωνια με ανοιγμα {np.mean(np.abs(m - mo)):.1f} ποντοι')
        bo, to, po, no = k2(m - mo, a - mo, ss); bc, tc, pc_, nc = k2(m - mc, a - mc, ss)
        mv = np.mean((mc - mo) * np.sign(m - mo)) / np.mean(np.abs(m - mo))
        P(f'     Κ2 vs ΑΝΟΙΓΜΑ b {bo:+.2f} (t {to:+.1f}, θετ. {po}/{no}) · vs ΚΛΕΙΣΙΜΟ b {bc:+.2f} (t {tc:+.1f}, θετ. {pc_}/{nc}) · η γραμμη κινηθηκε προς εμας {mv*100:+.0f}% της διαφωνιας')
        for lo, hi in buckets:
            dd = np.abs(m - mo); sel = (dd >= lo) & (dd < hi)
            if sel.sum() < 8: continue
            sg = np.sign(m - mo)[sel]
            got = np.mean((a - mo)[sel] * sg); moved = np.mean((mc - mo)[sel] * sg); dis = np.mean(dd[sel])
            R = {'o': [], 'c': []}
            for k, i in enumerate(ii[sel]):
                s_ = side_of(sg[k])
                for wh in ('o', 'c'):
                    L, _, p1, p2 = MK[i][wh]
                    R[wh].append((settle(i, s_, L, p1 if s_ > 0 else p2), seasn[i]))
            roi = {wh: (np.mean([q[0] for q in R[wh]]) * 100, sum(1 for Y in EVM if [q for q in R[wh] if q[1] == Y] and np.mean([q[0] for q in R[wh] if q[1] == Y]) > 0),
                        len({q[1] for q in R[wh]})) for wh in R}
            P(f'     διαφωνια {lo:>2}-{hi if hi < 99 else "+":<2} n {sel.sum():4d} · μεση {dis:4.1f} · «βγηκε» {got:+5.1f} ({got/dis*100:+4.0f}%) · γραμμη κινηθηκε {moved:+4.1f} ({moved/dis*100:+4.0f}%) · '
              f'ROI πλευρας μας ανοιγμα {roi["o"][0]:+5.1f}% ({roi["o"][1]}/{roi["o"][2]}) · κλεισιμο {roi["c"][0]:+5.1f}% ({roi["c"][1]}/{roi["c"][2]})')
# χαντικαπ: MK['o'] = (γραμμη γηπ L, αναμ. διαφορα γηπ, τιμη γηπ, τιμη φιλ) — πλευρα μας γηπ αν μοντελο > αγορα
analyse('ΧΑΝΤΙΚΑΠ (διαφορα γηπεδουχου)', MKH, MARG, ACT, settle_h, ((0, 2), (2, 4), (4, 6), (6, 9), (9, 99)), lambda s: 1 if s > 0 else -1)
# συνολα: MKT['o'] = (γραμμη T, αναμ. συνολο, τιμη over, τιμη under)
analyse('ΣΥΝΟΛΑ ΠΟΝΤΩΝ', MKT, TOTP, TOT, settle_t, ((0, 3), (3, 6), (6, 10), (10, 99)), lambda s: 1 if s > 0 else -1)
# ---- σημερινος κανονας picks (χαντικαπ, μοντελο μονο του σ 11.5, ≥8%) ανα περιοδο ----
P(''); P('################ ΣΗΜΕΡΙΝΟΣ ΚΑΝΟΝΑΣ PICKS (χαντικαπ, σ 11.5, edge ≥8%, ανοιγμα) + προτεινομενη μιξη 50/50 σ 12.3 ≥6% ################')
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
for lab, f in PER:
    cells = []
    for rl, wm, sg_, thr in (('σημερα', 1.0, 11.5, .08), ('μιξη', .5, 12.3, .06)):
        for wh in ('o', 'c'):
            R = []
            for i in MKH:
                if seasn[i] not in EVM or not np.isfinite(MARG[i]) or not f(GN[i]): continue
                L, mk_, o1, o2 = MKH[i][wh]; m_ = mk_ + wm * (MARG[i] - mk_)
                pw, pp, pl = cover(m_, L, sg_); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e >= thr: R.append((settle_h(i, s_, L, od), seasn[i]))
            a = np.array([q[0] for q in R]); pos = sum(1 for Y in EVM if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
            cells.append(f'{rl} {"ανοιγμα" if wh == "o" else "κλεισιμο"} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/{len({q[1] for q in R})})')
    P(f'  [{lab}] ' + ' · '.join(cells))
open('ec_season_backtest_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
