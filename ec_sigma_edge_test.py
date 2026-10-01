# -*- coding: utf-8 -*-
"""ec_sigma_edge_test.py — EuroCup ΑΠΟ ΤΗΝ ΑΡΧΗ, βημα 2: ΑΝΟΧΗ (σ) και ΟΡΙΟ EDGE μετρημενα στο EuroCup (1/10/2026, Στελιος).
Σημερα (απο Ευρωλιγκα): σ 11.5 (πιθανοτητα καλυψης = Φ((μοντελο + γραμμη)/σ)) · picks edge ≥8%.
Δεδομενα: προβλεψεις live ec1 (ec_fresh_market.pkl ← ec_fresh_engine_test.py 0) · Crown ανοιγμα/κλεισιμο U2020-U2025.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση):
 (α) σ ∈ {10.5, 11.5, 12.5, 13.5, 14.5}: log-loss των αποτελεσματων καλυψης στη γραμμη ΑΝΟΙΓΜΑΤΟΣ (χωρις push), LOSO 6 σεζον.
     ΑΛΛΑΓΗ αν η επιλογη ≠ 11.5 σε ≥4/6 και log-loss καλυτερο σε ≥4/6.
 (β) οριο edge ∈ {4, 6, 8, 10, 12, 15}% (με το σ του (α)): LOSO επιλογη με ΜΟΝΑΔΕΣ στο ανοιγμα → ΑΛΛΑΓΗ αν ≠ 8% σε ≥4/6 και μοναδες καλυτερες ≥4/6.
 Αναφορα: πινακας βαθμονομησης (προβλεπομενη vs πραγματικη καλυψη) · ROI ανα κλιμακα edge (και πολυ μεγαλα edges ≥25%).
Εξοδος: ec_sigma_edge_out.txt"""
import sys, json, math, pickle
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
Phi = NormalDist().cdf
Z = pickle.load(open('ec_fresh_market.pkl', 'rb'))
MK, act, GN, seasn, m_live = Z['MK'], Z['act'], Z['GN'], Z['seasn'], Z['live']
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
out = []
def P(s=''): print(s); out.append(s)
def probs(m, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((m + L - .5) / s); pl = Phi((-m - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m + L) / s); return pw, 0.0, 1 - pw
II = [i for i in MK if seasn[i] in EVM and np.isfinite(m_live[i])]
def logloss(s, ss, when='o'):
    ll = []
    for i in II:
        if seasn[i] not in ss: continue
        L = MK[i][when][0]; v = act[i] + L
        if v == 0: continue
        pw, pp, pl = probs(m_live[i], L, s); p = pw / (pw + pl)
        p = min(max(p, 1e-6), 1 - 1e-6); ll.append(-math.log(p if v > 0 else 1 - p))
    return float(np.mean(ll))
SIG = (10.5, 11.5, 12.5, 13.5, 14.5)
P('=== (α) σ — log-loss καλυψης στη γραμμη ανοιγματος (μικροτερο = καλυτερο) ===')
P('  ολες οι σεζον: ' + ' · '.join(f'σ {s}: {logloss(s, EVM):.4f}' for s in SIG) + f' · (μαντεψια 50/50 = {math.log(2):.4f})')
ch, better = [], []
for Y in EVM:
    tr = [x for x in EVM if x != Y]; s = min(SIG, key=lambda s: logloss(s, tr)); ch.append(s)
    better.append(logloss(s, [Y]) - logloss(11.5, [Y]))
P(f'  LOSO επιλογες {ch} · log-loss vs 11.5 ανα σεζον ' + ' '.join(f'{Y[-2:]}:{x:+.4f}' for Y, x in zip(EVM, better)))
chg = sum(c != 11.5 for c in ch) >= 4 and sum(x < 0 for x in better) >= 4
SIGMA = max(set(ch), key=ch.count) if chg else 11.5
P(f'  → {"ΑΛΛΑΓΗ σε σ " + str(SIGMA) if chg else "ΜΕΝΕΙ σ 11.5"}')
P('  ΕΠΕΚΤΑΣΗ (μετα το αποτελεσμα: η επιλογη ηταν στο ακρο του πλεγματος — μονο πληροφοριακα): ' + ' · '.join(f'σ {s}: {logloss(s, EVM):.4f}' for s in (15.5, 16.5, 18, 20, 23, 26)))
P(f'  (ενδεικτικα: τυπικη αποκλιση πραγματικου γυρω απο το μοντελο {np.std([act[i] - m_live[i] for i in II]):.2f} · γυρω απο την αγορα κλεισ. {np.std([act[i] - MK[i]["c"][1] for i in II]):.2f})')
P(''); P('=== ΒΑΘΜΟΝΟΜΗΣΗ (ανοιγμα): προβλεπομενη πιθανοτητα καλυψης της πλευρας μας vs πραγματικη ===')
for s in (11.5, SIGMA) if SIGMA != 11.5 else (11.5,):
    bins = [(.5, .55), (.55, .6), (.6, .65), (.65, .7), (.7, .8), (.8, 1.0)]
    rows = {b: [] for b in bins}
    for i in II:
        L = MK[i]['o'][0]; v = act[i] + L
        if v == 0: continue
        pw, pp, pl = probs(m_live[i], L, s); p = pw / (pw + pl); side_p, won = (p, v > 0) if p >= .5 else (1 - p, v < 0)
        for b in bins:
            if b[0] <= side_p < b[1]: rows[b].append((side_p, won))
    P(f'  σ {s}: ' + ' · '.join(f'{b[0]:.2f}-{b[1]:.2f}: προβλ. {np.mean([r[0] for r in v])*100:.0f}% / πραγμ. {np.mean([r[1] for r in v])*100:.0f}% (n {len(v)})' for b, v in rows.items() if v))
def picks(s, thr, when='o', lo=None, hi=None):
    R = []
    for i in II:
        L, _, o1, o2 = MK[i][when]; pw, pp, pl = probs(m_live[i], L, s)
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= thr and (lo is None or e >= lo) and (hi is None or e < hi):
            v = (act[i] + L) * side; R.append(((od - 1) if v > 0 else (0 if v == 0 else -1), seasn[i], e))
    return R
P(''); P(f'=== (β) ROI ανα κλιμακα edge (σ {SIGMA}) ===')
for when in ('o', 'c'):
    cells = []
    for lo, hi in ((0, .04), (.04, .08), (.08, .12), (.12, .18), (.18, .25), (.25, 9)):
        R = picks(SIGMA, -9, when, lo, hi); a = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R))
        pos = sum(1 for Y in ys if np.mean([q[0] for q in R if q[1] == Y]) > 0)
        cells.append(f'{lo*100:.0f}-{hi*100 if hi < 9 else 99:.0f}%: {a.mean()*100:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/{len(ys)})')
    P(f'  {"ανοιγμα " if when == "o" else "κλεισιμο"}: ' + ' · '.join(cells))
TH = (.04, .06, .08, .10, .12, .15)
units = lambda thr, ss: sum(q[0] for q in picks(SIGMA, thr, 'o') if q[1] in ss)
P('  μοναδες στο ανοιγμα ανα οριο (ολες): ' + ' · '.join(f'{t*100:.0f}%: {units(t, EVM):+.1f}u ({len(picks(SIGMA, t, "o"))})' for t in TH))
ch2, bt = [], []
for Y in EVM:
    tr = [x for x in EVM if x != Y]; t = max(TH, key=lambda t: units(t, tr)); ch2.append(t); bt.append(units(t, [Y]) - units(.08, [Y]))
P(f'  LOSO επιλογες {[f"{t*100:.0f}%" for t in ch2]} · μοναδες vs 8% ανα σεζον ' + ' '.join(f'{Y[-2:]}:{x:+.1f}' for Y, x in zip(EVM, bt)))
chg2 = sum(c != .08 for c in ch2) >= 4 and sum(x > 0 for x in bt) >= 4
P(f'  → {"ΑΛΛΑΓΗ οριου" if chg2 else "ΜΕΝΕΙ 8%"}')
P(''); P('=== ΠΟΛΥ ΜΕΓΑΛΑ edges (≥25%, ανοιγμα) ανα σεζον ===')
for Y in EVM:
    R = [q for q in picks(SIGMA, .25, 'o') if q[1] == Y]; a = np.array([q[0] for q in R])
    P(f'  {Y}: {len(a)} picks · {a.mean()*100 if len(a) else 0:+.1f}% · {a.sum():+.1f}u')
for i in []:
    L, _, o1, o2 = MK[i]['o']; pw, pp, pl = probs(m_live[i], L, SIGMA)
    e = max(pw * o1 + pp - 1, pl * o2 + pp - 1)
    if e >= .25:
        P(f"  {seasn[i]} {Z['t'][i][:10]} {Z['home'][i]}-{Z['away'][i]} · μοντελο {-m_live[i]:+.1f} · γραμμη {L:+.1f} · πραγματικο {-act[i]:+.0f} · edge {e*100:.0f}%")
open('ec_sigma_edge_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
# ---------------------------------------------------------------------------------------------------------------
# (γ) ΠΡΟΣΘΗΚΗ (γραφτηκε ΜΕΤΑ το (α), πριν τρεξει): το log-loss πεφτει ως σ ≈ 23 → το μοντελο ειναι «υπερ-σιγουρο».
# Πιο σωστος τροπος απο ενα τεραστιο σ: η αποσταση μοντελου–αγορας ειναι αληθινη μονο κατα ενα μερος (Κ2 b ≈ .35-.39).
# ΜΙΞΗ: μ* = αγορα(ανοιγμα) + w·(μοντελο − αγορα), σ = 12.3 (λαθος αγορας EuroCup). w ∈ {.2,.3,.4,.5,.6,.8,1}.
# ΠΡΟ-ΔΗΛΩΜΕΝΟ: LOSO log-loss καλυψης (ανοιγμα) → καλυτερο απο ΣΗΜΕΡΑ (σ 11.5, w 1) σε ≥4/6· picks: οριο edge LOSO με μοναδες,
# ΑΛΛΑΓΗ κανονα picks αν μοναδες στο ανοιγμα καλυτερες απο σημερα (σ 11.5 · 8%) σε ≥4/6 σεζον.
def mix_m(i, w, when='o'): return MK[i][when][1] + w * (m_live[i] - MK[i][when][1])
def logloss_mix(w, s, ss, when='o'):
    ll = []
    for i in II:
        if seasn[i] not in ss: continue
        L = MK[i][when][0]; v = act[i] + L
        if v == 0: continue
        pw, pp, pl = probs(mix_m(i, w, when), L, s); p = min(max(pw / (pw + pl), 1e-6), 1 - 1e-6); ll.append(-math.log(p if v > 0 else 1 - p))
    return float(np.mean(ll))
W = (.2, .3, .4, .5, .6, .8, 1.0); SM = 12.3
P(''); P('=== (γ) ΜΙΞΗ μοντελου με την αγορα ανοιγματος (σ 12.3) ===')
P('  log-loss ολες: ' + ' · '.join(f'w {w}: {logloss_mix(w, SM, EVM):.4f}' for w in W) + f' · σημερα (σ 11.5, w 1): {logloss(11.5, EVM):.4f}')
chw, bw = [], []
for Y in EVM:
    tr = [x for x in EVM if x != Y]; w = min(W, key=lambda w: logloss_mix(w, SM, tr)); chw.append(w); bw.append(logloss_mix(w, SM, [Y]) - logloss(11.5, [Y]))
P(f'  LOSO w {chw} · vs σημερα ' + ' '.join(f'{Y[-2:]}:{x:+.4f}' for Y, x in zip(EVM, bw)) + f' → καλυτερο {sum(x < 0 for x in bw)}/6')
WB = max(set(chw), key=chw.count)
def picks_mix(w, thr, when='o'):
    R = []
    for i in II:
        L, _, o1, o2 = MK[i][when]; pw, pp, pl = probs(mix_m(i, w, when), L, SM)
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= thr:
            v = (act[i] + L) * side; R.append(((od - 1) if v > 0 else (0 if v == 0 else -1), seasn[i], e))
    return R
TH2 = (.0, .01, .02, .03, .04, .06, .08)
for when in ('o', 'c'):
    P(f'  w {WB} · {"ανοιγμα " if when == "o" else "κλεισιμο"} ανα οριο: ' + ' · '.join(
        f'{t*100:.0f}%: {np.mean([q[0] for q in picks_mix(WB, t, when)])*100:+.1f}% ({len(picks_mix(WB, t, when))}, {sum(q[0] for q in picks_mix(WB, t, when)):+.1f}u)' for t in TH2 if picks_mix(WB, t, when)))
cur_u = lambda ss: sum(q[0] for q in picks(11.5, .08, 'o') if q[1] in ss)
chT, bT = [], []
for Y in EVM:
    tr = [x for x in EVM if x != Y]
    t = max(TH2, key=lambda t: sum(q[0] for q in picks_mix(WB, t, 'o') if q[1] in tr)); chT.append(t)
    bT.append(sum(q[0] for q in picks_mix(WB, t, 'o') if q[1] == Y) - cur_u([Y]))
P(f'  LOSO οριο {[f"{t*100:.0f}%" for t in chT]} · μοναδες ανοιγματος vs σημερινο κανονα (σ 11.5, 8%) ανα σεζον ' + ' '.join(f'{Y[-2:]}:{x:+.1f}' for Y, x in zip(EVM, bT))
  + f' → καλυτερο {sum(x > 0 for x in bT)}/6' + ('  <- ΑΛΛΑΓΗ' if sum(x > 0 for x in bT) >= 4 else '  <- ✗'))
P(f'  σημερινος κανονας: {cur_u(EVM):+.1f}u ({len(picks(11.5, .08, "o"))} picks, ROI {np.mean([q[0] for q in picks(11.5, .08, "o")])*100:+.1f}%)')
open('ec_sigma_edge_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
