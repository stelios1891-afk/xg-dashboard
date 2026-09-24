# -*- coding: utf-8 -*-
"""el_expert_prior_test.py — ΤΕΣΤ: κατατάξη ΕΙΔΙΚΩΝ πριν τη σεζόν ως πληροφορία αρχής (25/9/2026, ιδέα Στελιου απο BasketNews).

ΠΗΓΗ: BasketNews pre-season Power Rankings (ψηφοφορία δημοσιογράφων/παικτών, 17-35 ψήφοι), δημοσιευμένες ΠΡΙΝ την 1η αγωνιστική:
  2021-22 news-155174 (19/8/2021) · 2022-23 news-178599 (30/9/2022) · 2023-24 news-195121 (29/9/2023)
  2024-25 news-212105 (27/9/2024) · 2025-26 πινακας «Power Ranking Position» στο news-245393 · 2026-27 news-255835 (22/9/2026)
  (2020-21: δεν βρεθηκε αντιστοιχη BasketNews → εκτος τεστ.)
ΜΕΘΟΔΟΣ: θεση → rating «ειδικων» = ο μεσος ορος, στις ΑΛΛΕΣ σεζον, του rating (v1, τελος κανονικης περιοδου) της ομαδας στο ιδιο
  ποσοστημοριο (θεση/Ν). Αρχικο rating = (1−α)·(v1: 70% περσινου) + α·(ειδικοι). Νεες ομαδες: (1−α)·0 + α·(ειδικοι).
  Η αλλαγη μπαινει μισή στην επιθεση, μισή στην αμυνα· ρυθμος αμεταβλητος. Μετα η σεζον τρεχει οπως πριν (βαρος 8 ματς).
ΠΛΕΓΜΑ: α {0.25, 0.5, 0.75, 1.0}. ΕΠΙΛΟΓΗ: LOSO στις 5 σεζον (καλυτερο ROI edge ≥5% στις αλλες 4).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΜΙΑ εκτελεση): ΠΕΡΝΑ αν στα ενωμενα held-out, σε σχεση με v1 (ιδιες 5 σεζον):
  ROI χαντικαπ μεγαλυτερο σε edge ≥5% ΚΑΙ ≥8% ΚΑΙ ≥10%, με κερδοφορες σεζον οχι λιγοτερες (σε καθε οριο).
Αναφορα: αγων 1-10 χωριστα, κλιση b, καθε α σε ολες. Κανονικη περιοδος, Pinnacle closing. Εξοδος: el_expert_prior_test_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o = []
src = open('el_roi_v2.py', encoding='utf-8').read().split("P('Edge = P")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o
def P(s=''):
    print(s, flush=True); out.append(str(s))

RANK = {
 'E2021': dict(IST=1, BAR=2, CSK=3, MAD=4, MIL=5, ULK=6.5, DYR=6.5, TEL=8, MUN=9, BAS=10, ZAL=11, OLY=12, UNK=13, PAN=14, ASV=15, BER=16, RED=17, MCO=18),
 'E2022': dict(MAD=1, IST=2, BAR=3, MIL=4, OLY=5, MCO=6, ULK=7, MUN=8, VIR=9, PAR=10, TEL=11, PAN=12, PAM=13, BAS=14, RED=15, ZAL=16, ASV=17, BER=18),
 'E2023': dict(MAD=1, MCO=2, OLY=3, PAN=4, BAR=5, IST=6, ULK=7, MIL=8, TEL=9, PAR=10, RED=11, ZAL=12, MUN=13, BAS=14, PAM=15, VIR=16, ASV=17, BER=18),
 'E2024': dict(PAN=1, OLY=2, MAD=3, ULK=4, MCO=5, BAR=6, IST=7, PAR=8, MIL=9, RED=10, TEL=11, BAS=12, ZAL=13, VIR=14, MUN=15, PRS=16, ASV=17, BER=18),
 'E2025': dict(PAN=1, OLY=2, MCO=3, ULK=4, IST=5, MAD=6, BAR=7, HTA=8, RED=9, MIL=10, PAR=11, ZAL=12, DUB=13, MUN=14, PRS=15, PAM=16, TEL=17, BAS=18, VIR=19, ASV=20),
}
ES = list(RANK)

def run_x(alpha=0.0, mapping=None, carry=0.7, lam=8, HL=120, h=6.0):
    """v1 (el_mech_tests.run) + αρχικο rating μετακινημενο προς τους ειδικους· επιστρεφει (προβλεψεις, net τελους ανα σεζον)."""
    if 'L' not in _PTS:
        ph, pa = points(D, 'L'); _PTS['L'] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
    EH, EA = _PTS['L']
    preds = np.full((len(D), 2), np.nan); prior = {}; ends = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        if alpha and s in RANK and mapping is not None:
            N = len(RANK[s])
            for t, i in ix.items():
                if t not in RANK[s]: continue
                target = mapping(s, (RANK[s][t] - 0.5) / N)
                cur = o0[i] - d0[i]; dl = alpha * (target - cur)
                o0[i] += dl / 2; d0[i] -= dl / 2
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        neu = D.ff.values[sidx] | D.relocated.values[sidx]
        hb = np.where(neu, 0.0, h / 2); dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur_ = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa, hbb = hi[cur_], ai[cur_], hb[cur_]
            e_h = mu + O[hh] + Dd[aa] + hbb; e_a = mu + O[aa] + Dd[hh] - hbb
            poss = pm + Pc[hh] + Pc[aa]
            preds[sidx[cur_], 0] = poss * (e_h - e_a) / 100; preds[sidx[cur_], 1] = poss * (e_h + e_a) / 100
        rs = sidx[D.phase.values[sidx] == 'RS']; m = np.isin(sidx, rs)
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        ends[s] = np.sort(O - Dd)[::-1]
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds, ends

base, ENDS = run_x(0.0)
assert np.allclose(base[IDX, 0], M_V1), 'το run_x(0) πρεπει να ειναι ακριβως το v1'
REF = [s for s in SEAS if s >= 'E2018' and s <= 'E2025']
def mapping(s, q):
    """rating στο ποσοστημοριο q (0 = καλυτερη) — μεσος ορος των ΑΛΛΩΝ σεζον."""
    vals = [np.interp(q, (np.arange(len(ENDS[r])) + 0.5) / len(ENDS[r]), ENDS[r]) for r in REF if r != s]
    return float(np.mean(vals))
P('θεση ειδικων → rating (π./100 κατοχες), π.χ. για 2025: ' + ' · '.join(f'{k}η {mapping("E2025", (k - .5) / 20):+.1f}' for k in (1, 3, 5, 10, 15, 20)))

rs_all = D[D.phase == 'RS'].sort_values('date'); cnt, gno = {}, {}
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    gno[i] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
RND = np.array([gno.get(i, 99) for i in IDX])
def sp(m):
    b = bets(m, T_LO); b = b[b.mkt == 'sp'].copy()
    jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
    b['rnd'] = RND[jj]; return b[b.season.isin(ES)]
ALPHAS = [0.25, 0.5, 0.75, 1.0]
PRED = {a: run_x(a, mapping)[0][IDX, 0] for a in ALPHAS}
BV1 = sp(M_V1); BG = {a: sp(PRED[a]) for a in ALPHAS}
def roi(b, thr, ss):
    x = b[(b.edge >= thr) & b.season.isin(ss)]; return x.p.mean() if len(x) else -9
def cell(x):
    return f'{x.p.mean()*100:+5.1f}% ({len(x)}, {x.p.sum():+.1f}u)' if len(x) else '—'

P('')
P('=== LOSO επιλογη α (ROI edge ≥5% στις αλλες 4 σεζον) ===')
held = []
for s in ES:
    tr = [t for t in ES if t != s]
    a = max(ALPHAS, key=lambda a: roi(BG[a], .05, tr))
    held.append(BG[a][BG[a].season == s])
    P(f'  {s[-4:]} εξω: α {a} → ROI εξω {roi(BG[a], .05, [s])*100:+.1f}% vs v1 {roi(BV1, .05, [s])*100:+.1f}%')
H = pd.concat(held)
P('')
P('=== ΑΠΟΤΕΛΕΣΜΑ (ενωμενα held-out, 2021-2025) ===')
ok = True
for thr in (0.03, 0.05, 0.08, 0.10, 0.15):
    a, v = H[H.edge >= thr], BV1[BV1.edge >= thr]
    pa = sum(1 for s in ES if len(a[a.season == s]) and a[a.season == s].p.mean() > 0)
    pv = sum(1 for s in ES if len(v[v.season == s]) and v[v.season == s].p.mean() > 0)
    if thr in (0.05, 0.08, 0.10): ok &= (a.p.mean() > v.p.mean()) and pa >= pv
    P(f'  edge ≥{thr*100:2.0f}%: με ειδικους {cell(a)} {pa}/5 · v1 {cell(v)} {pv}/5')
P('')
for lo, hi_ in ((1, 10), (11, 99)):
    P(f'  αγωνιστικες {lo}-{hi_ if hi_ < 99 else "τελος"}, edge ≥5%: με ειδικους {cell(H[(H.edge >= .05) & (H.rnd >= lo) & (H.rnd <= hi_)])} · v1 {cell(BV1[(BV1.edge >= .05) & (BV1.rnd >= lo) & (BV1.rnd <= hi_)])}')
m = RS & np.isin(SE, ES)
P('')
P('  (αναφορα) καθε α σε ολες τις 5 σεζον · edge ≥5% / ≥8% / ≥10% · αγων 1-10 (≥5%) · κλιση b · λαθος διαφορας αγων 1-10')
for a, mm in [(0.0, M_V1)] + [(a, PRED[a]) for a in ALPHAS]:
    b = BV1 if a == 0 else BG[a]
    bb = np.polyfit((mm - MM)[m], (ACT - MM)[m], 1)[0]
    e = m & (RND <= 10); mae = np.mean(np.abs(ACT - mm)[e])
    P(f'    α {a:<4}: {cell(b[b.edge >= .05])} · {cell(b[b.edge >= .08])} · {cell(b[b.edge >= .10])} · {cell(b[(b.edge >= .05) & (b.rnd <= 10)])} · b {bb:+.3f} · MAE {mae:.2f}')
P(f'    (αγορα MAE αγων 1-10: {np.mean(np.abs(ACT - MM)[m & (RND <= 10)]):.2f})')
P('')
P(f'→ {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ — μενει το v1"}')
open('el_expert_prior_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
