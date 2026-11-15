# -*- coding: utf-8 -*-
"""ec_hcap_mix_nested_test.py — EuroCup ΧΑΝΤΙΚΑΠ: ΜΙΞΗ με την αγορα ή οχι; ΚΑΘΑΡΟ & ΑΣΦΑΛΕΣ τεστ (5/10/2026, Στελιος:
«θελουμε ενα καθαρο και ασφαλες τεστ, οχι βιασυνες και γρηγορα συμπερασματα»).
ΔΕΔΟΜΕΝΑ: 690 εκδοχες μηχανης χαντικαπ (ec_fresh_engine_preds.pkl: HL × λ × εδρα × τυχη × μ_w × περσι × ειδικοι × φιλικα· εγχωρια κ1 σε ολες)
  · Crown ανοιγμα/κλεισιμο U2020-25 (ec_fresh_market.pkl). Κανονικη + νοκ-αουτ, ολες οι αγωνιστικες.
ΚΑΘΑΡΟ (nested): για καθε σεζον-ελεγχου Y ∈ U2020-25:
  (1) μηχανη = ελαχιστο RMSE διαφορας στις ΑΛΛΕΣ σεζον U2018-25 (οχι η Y)
  (2) κανονας picks επιλεγεται στις ΑΛΛΕΣ 5 σεζον με αγορα — δυο τροποι:
      (2α) μοναδες: w {.3,.4,.5,.6,.75,1} × σ {11.5,12.3,13.5,14.5} × κατωφλι {4,6,8,10,12}% → οι περισσοτερες μοναδες
      (2β) δυο σταδια (πιο σταθερο): (w, σ) με log-loss καλυψης, μετα κατωφλι με μοναδες
  (3) αποτελεσμα ΜΟΝΟ στη σεζον Y (ανοιγμα Crown).
  + ΣΤΑΘΕΡΟΙ κανονες (κανενα data-snooping στον κανονα) πανω στις καθαρες προβλεψεις: ΣΗΜΕΡΙΝΟΣ (w 1, σ 11.5, ≥8%) · ΠΡΟΤΕΙΝΟΜΕΝΟΣ (w .5, σ 12.3, ≥6%).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΠΡΙΝ την εκτελεση) — αλλαγη σε μιξη ΜΟΝΟ αν ισχυουν ΟΛΑ:
  (Α) σταθεροι κανονες: ΠΡΟΤΕΙΝΟΜΕΝΟΣ > ΣΗΜΕΡΙΝΟΣ σε μοναδες σε ≥4/6 σεζον ΚΑΙ στο συνολο
  (Β) η nested διαδικασια (2α ή 2β) διαλεγει w < 1 σε ≥4/6 σεζον ΚΑΙ βγαζει περισσοτερες μοναδες απο τον σημερινο στο συνολο
  (Γ) bootstrap 5000 (ανα ματς, ζευγαρωτα): P(μοναδες ΠΡΟΤΕΙΝΟΜΕΝΟΥ − ΣΗΜΕΡΙΝΟΥ > 0) ≥ 0.90
  (Δ) CLV: η γραμμη κινειται προς τα picks του προτεινομενου τουλαχιστον οσο προς του σημερινου
  Αναφορα (οχι κριση): ανα φαση (αγων 1-6 / 7+) και ανα σεζον.
Εξοδος: ec_hcap_mix_nested_out.txt"""
import sys, math, pickle, itertools, collections
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
Phi = NormalDist().cdf
PRED = pickle.load(open('ec_fresh_engine_preds.pkl', 'rb'))
Z = pickle.load(open('ec_fresh_market.pkl', 'rb'))
MK, act, GN, seasn = Z['MK'], Z['act'], Z['GN'], np.asarray(Z['seasn'])
EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']; EVM = EV8[2:]
LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def rm(v, ys):
    m = np.isin(seasn, ys) & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
MI = np.array([i for i in MK if seasn[i] in EVM])
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def game_res(v, i, w, s, thr):
    """(μοναδα, πλευρα, CLV ποντοι) ή None."""
    L, mk, o1, o2 = MK[i]['o']; m_ = mk + w * (v[i] - mk)
    pw, pp, pl = cover(m_, L, s); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < thr: return None
    x = (act[i] + L) * side; u = (od - 1) if x > 0 else (0 if x == 0 else -1)
    return u, side, (MK[i]['c'][1] - mk) * side
def units(v, rule, ys):
    return sum(r[0] for i in MI if seasn[i] in ys and np.isfinite(v[i]) for r in [game_res(v, i, *rule)] if r)
def logloss(v, w, s, ys):
    a = []
    for i in MI:
        if seasn[i] not in ys or not np.isfinite(v[i]): continue
        L, mk, o1, o2 = MK[i]['o']; x = act[i] + L
        if x == 0: continue
        pw, pp, pl = cover(mk + w * (v[i] - mk), L, s); q = pw / (pw + pl) if x > 0 else pl / (pw + pl); a.append(-math.log(max(q, 1e-9)))
    return float(np.mean(a))
WS = (.3, .4, .5, .6, .75, 1.0); SS = (11.5, 12.3, 13.5, 14.5); TH = (.04, .06, .08, .10, .12)
RULES = list(itertools.product(WS, SS, TH))
CUR, PROP = (1.0, 11.5, .08), (.5, 12.3, .06)
# ---- (1) καθαρη μηχανη ανα σεζον ----
HELD = np.full(len(act), np.nan); ENG = {}
for Y in EVM:
    tr = [x for x in EV8 if x != Y]; g = min(PRED, key=lambda k: rm(PRED[k], tr)); ENG[Y] = g
    m = seasn == Y; HELD[m] = PRED[g][m]
P('################ (1) ΚΑΘΑΡΗ ΜΗΧΑΝΗ ανα σεζον (επιλογη στις αλλες 7) ################')
for Y in EVM: P(f'  {Y}: (HL, λ, εδρα, τυχη, μ_w, περσι, ειδικοι, φιλικα) = {ENG[Y]}' + ('  [= live]' if ENG[Y] == LIVE else ''))
P(f'  RMSE καθαρο {rm(HELD, EVM):.3f} · live {rm(PRED[LIVE], EVM):.3f}')
# ---- (2) nested κανονας ----
P(''); P('################ (2) NESTED ΕΠΙΛΟΓΗ ΚΑΝΟΝΑ ################')
NA, NB = {}, {}
for Y in EVM:
    tr = [x for x in EVM if x != Y]
    ra = max(RULES, key=lambda r: units(HELD, r, tr))
    ws = min(itertools.product(WS, SS), key=lambda p: logloss(HELD, p[0], p[1], tr))
    rb = max([(ws[0], ws[1], t) for t in TH], key=lambda r: units(HELD, r, tr))
    NA[Y], NB[Y] = ra, rb
    P(f'  {Y}: (2α) {ra} → {units(HELD, ra, [Y]):+.1f}u · (2β) {rb} → {units(HELD, rb, [Y]):+.1f}u · σημερινος {units(HELD, CUR, [Y]):+.1f}u · προτεινομενος {units(HELD, PROP, [Y]):+.1f}u')
def tot(rule_by_Y): return sum(units(HELD, rule_by_Y[Y], [Y]) for Y in EVM)
uA, uB = tot(NA), tot(NB); uC = units(HELD, CUR, EVM); uP = units(HELD, PROP, EVM)
P(f'  ΣΥΝΟΛΟ: (2α) {uA:+.1f}u · (2β) {uB:+.1f}u · σημερινος {uC:+.1f}u · προτεινομενος {uP:+.1f}u')
# ---- σταθεροι κανονες αναλυτικα ----
P(''); P('################ ΣΤΑΘΕΡΟΙ ΚΑΝΟΝΕΣ πανω στις καθαρες προβλεψεις ################')
def detail(rule, lab):
    R = [(r, seasn[i], GN[i]) for i in MI if np.isfinite(HELD[i]) for r in [game_res(HELD, i, *rule)] if r]
    u = np.array([x[0][0] for x in R]); clv = np.array([x[0][2] for x in R])
    ps = {Y: sum(x[0][0] for x in R if x[1] == Y) for Y in EVM}
    e = [x[0][0] for x in R if x[2] <= 5]; l = [x[0][0] for x in R if x[2] >= 6]
    P(f'  {lab:28s} {len(u):4d} picks · ROI {u.mean()*100:+.1f}% · {u.sum():+.1f}u · θετ. {sum(v > 0 for v in ps.values())}/6 · CLV {clv.mean():+.2f} π. · '
      + ' '.join(f'{Y[-2:]}:{v:+.1f}' for Y, v in ps.items()) + f' · αγων 1-6 {np.mean(e)*100 if e else 0:+.1f}% ({len(e)}) · 7+ {np.mean(l)*100 if l else 0:+.1f}% ({len(l)})')
    return ps, clv.mean()
psC, clvC = detail(CUR, 'ΣΗΜΕΡΙΝΟΣ (w1 σ11.5 ≥8%)')
psP, clvP = detail(PROP, 'ΠΡΟΤΕΙΝΟΜΕΝΟΣ (w.5 σ12.3 ≥6%)')
for r, lab in (((.5, 12.3, .08), 'μιξη .5 σ12.3 ≥8%'), ((.5, 12.3, .04), 'μιξη .5 σ12.3 ≥4%'), ((.75, 12.3, .06), 'μιξη .75 σ12.3 ≥6%'), ((1.0, 11.5, .06), 'χωρις μιξη ≥6%'), ((1.0, 14.5, .08), 'χωρις μιξη σ14.5 ≥8%')):
    detail(r, lab)
# ---- bootstrap ----
diff = []
for i in MI:
    if not np.isfinite(HELD[i]): continue
    a = game_res(HELD, i, *PROP); b = game_res(HELD, i, *CUR)
    diff.append((a[0] if a else 0) - (b[0] if b else 0))
diff = np.array(diff); rng = np.random.default_rng(11)
bs = np.array([diff[rng.integers(0, len(diff), len(diff))].sum() for _ in range(5000)])
pBS = float(np.mean(bs > 0))
P(''); P(f'BOOTSTRAP (ζευγαρωτα, 5000): διαφορα μοναδων ΠΡΟΤΕΙΝΟΜΕΝΟΥ − ΣΗΜΕΡΙΝΟΥ {diff.sum():+.1f}u · P(>0) = {pBS:.2f} · 90% ευρος [{np.percentile(bs, 5):+.1f}, {np.percentile(bs, 95):+.1f}]')
# ---- κριση ----
A = sum(psP[Y] > psC[Y] for Y in EVM) >= 4 and uP > uC
nW = max(sum(NA[Y][0] < 1 for Y in EVM), sum(NB[Y][0] < 1 for Y in EVM))
B = nW >= 4 and max(uA, uB) > uC
C = pBS >= .90
Dd = clvP >= clvC
P(''); P('################ ΠΡΟ-ΔΗΛΩΜΕΝΗ ΚΡΙΣΗ ################')
P(f'  (Α) προτεινομενος > σημερινος σε {sum(psP[Y] > psC[Y] for Y in EVM)}/6 σεζον και συνολο {uP:+.1f} vs {uC:+.1f} → {"✓" if A else "✗"}')
P(f'  (Β) nested διαλεγει μιξη (w<1) σε {nW}/6 και μοναδες {max(uA, uB):+.1f} vs σημερινος {uC:+.1f} → {"✓" if B else "✗"}')
P(f'  (Γ) bootstrap P {pBS:.2f} ≥ 0.90 → {"✓" if C else "✗"}')
P(f'  (Δ) CLV προτεινομενου {clvP:+.2f} ≥ σημερινου {clvC:+.2f} → {"✓" if Dd else "✗"}')
P(f'  → {"ΑΛΛΑΓΗ ΣΕ ΜΙΞΗ" if (A and B and C and Dd) else "ΚΑΜΙΑ ΑΛΛΑΓΗ (δεν ικανοποιουνται ολα)"}')
open('ec_hcap_mix_nested_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
