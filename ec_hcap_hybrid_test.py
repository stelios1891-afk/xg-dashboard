# -*- coding: utf-8 -*-
"""ec_hcap_hybrid_test.py — EuroCup ΧΑΝΤΙΚΑΠ: ΣΥΝΔΥΑΣΜΟΣ «σημερινος στις αγων 1-6, μιξη απο την 7η»; ΚΑΘΑΡΟ τεστ (5/10/2026, Στελιος).
Η ιδεα προεκυψε ΑΦΟΥ ειδαμε τα αποτελεσματα (ec_hcap_mix_nested_test) — γι' αυτο κρινεται μονο με nested επιλογη.
Ιδιες καθαρες προβλεψεις (μηχανη επιλεγμενη στις αλλες σεζον). Δυο κανονες: ΣΗΜ (w1 σ11.5 ≥8%) · ΜΙΞ (w.5 σ12.3 ≥6%).
NESTED: για καθε σεζον-ελεγχου, ΧΩΡΙΣΤΑ για αγων 1-6 και 7+, διαλεγεται ΣΗΜ ή ΜΙΞ με τις μοναδες των ΑΛΛΩΝ 5 σεζον.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΠΡΙΝ την εκτελεση) — ο συνδυασμος περνα ΜΟΝΟ αν ισχυουν ΟΛΑ:
  (Α) σταθεροτητα: η nested επιλογη βγαζει «ΣΗΜ στις 1-6 / ΜΙΞ στις 7+» σε ≥4/6 σεζον
  (Β) nested μοναδες > ΣΗΜ ολη τη σεζον σε ≥4/6 σεζον ΚΑΙ στο συνολο
  (Γ) bootstrap 5000 ζευγαρωτα: P(nested − ΣΗΜ > 0) ≥ 0.90  ΚΑΙ  P(nested − ΜΙΞ > 0) ≥ 0.90 (να ειναι καλυτερος ΚΑΙ απο τα δυο)
Εξοδος: ec_hcap_hybrid_out.txt"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
src = open('ec_hcap_mix_nested_test.py', encoding='utf-8').read()
src = src.split("# ---- (2) nested κανονας ----")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
NS = {'__name__': 'h'}
exec(src, NS)
HELD, MI, seasn, GN, game_res, EVM, CUR, PROP = (NS[k] for k in ('HELD', 'MI', 'seasn', 'GN', 'game_res', 'EVM', 'CUR', 'PROP'))
NS['out'].clear()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
U = {}
for nm, r in (('ΣΗΜ', CUR), ('ΜΙΞ', PROP)):
    U[nm] = np.array([((game_res(HELD, i, *r) or (0,))[0]) if np.isfinite(HELD[i]) else 0 for i in MI], float)
S = seasn[MI]; E = GN[MI] <= 5
def u(nm, ys, early): return float(U[nm][np.isin(S, ys) & (E == early)].sum())
NEST = np.zeros(len(MI)); choice = {}
for Y in EVM:
    tr = [x for x in EVM if x != Y]
    ce = max(('ΣΗΜ', 'ΜΙΞ'), key=lambda nm: u(nm, tr, True)); cl = max(('ΣΗΜ', 'ΜΙΞ'), key=lambda nm: u(nm, tr, False))
    choice[Y] = (ce, cl); m = S == Y
    NEST[m & E] = U[ce][m & E]; NEST[m & ~E] = U[cl][m & ~E]
P('################ NESTED ΕΠΙΛΟΓΗ ανα φαση ################')
for Y in EVM:
    m = S == Y
    P(f'  {Y}: αγων 1-6 → {choice[Y][0]} · 7+ → {choice[Y][1]} · μοναδες: nested {NEST[m].sum():+.1f} · ΣΗΜ {U["ΣΗΜ"][m].sum():+.1f} · ΜΙΞ {U["ΜΙΞ"][m].sum():+.1f}')
tN, tC, tM = NEST.sum(), U['ΣΗΜ'].sum(), U['ΜΙΞ'].sum()
nP = lambda v: int((v != 0).sum())
P(f'  ΣΥΝΟΛΟ: nested {tN:+.1f}u ({nP(NEST)} picks) · ΣΗΜ {tC:+.1f}u ({nP(U["ΣΗΜ"])}) · ΜΙΞ {tM:+.1f}u ({nP(U["ΜΙΞ"])})')
fixed = np.where(E, U['ΣΗΜ'], U['ΜΙΞ'])
P(f'  (αναφορα — σταθερος συνδυασμος ΣΗΜ 1-6 / ΜΙΞ 7+, φουσκωμενος γιατι επιλεχθηκε βλεποντας: {fixed.sum():+.1f}u, {nP(fixed)} picks)')
rng = np.random.default_rng(23); n = len(MI)
def boot(a, b):
    d = a - b; bs = np.array([d[rng.integers(0, n, n)].sum() for _ in range(5000)]); return float(np.mean(bs > 0)), np.percentile(bs, 5), np.percentile(bs, 95)
pC = boot(NEST, U['ΣΗΜ']); pM = boot(NEST, U['ΜΙΞ'])
P(f'  bootstrap: P(nested > ΣΗΜ) {pC[0]:.2f} [{pC[1]:+.1f}, {pC[2]:+.1f}] · P(nested > ΜΙΞ) {pM[0]:.2f} [{pM[1]:+.1f}, {pM[2]:+.1f}]')
A = sum(choice[Y] == ('ΣΗΜ', 'ΜΙΞ') for Y in EVM)
B = sum(NEST[S == Y].sum() > U['ΣΗΜ'][S == Y].sum() for Y in EVM)
okA, okB, okC = A >= 4, B >= 4 and tN > tC, pC[0] >= .9 and pM[0] >= .9
P(''); P('################ ΠΡΟ-ΔΗΛΩΜΕΝΗ ΚΡΙΣΗ ################')
P(f'  (Α) η nested επιλογη = «ΣΗΜ 1-6 / ΜΙΞ 7+» σε {A}/6 → {"✓" if okA else "✗"}')
P(f'  (Β) nested > ΣΗΜ σε {B}/6 σεζον, συνολο {tN:+.1f} vs {tC:+.1f} → {"✓" if okB else "✗"}')
P(f'  (Γ) bootstrap ≥ .90 και vs ΣΗΜ ({pC[0]:.2f}) και vs ΜΙΞ ({pM[0]:.2f}) → {"✓" if okC else "✗"}')
P(f'  → {"Ο ΣΥΝΔΥΑΣΜΟΣ ΠΕΡΝΑ" if okA and okB and okC else "Ο ΣΥΝΔΥΑΣΜΟΣ ΔΕΝ ΠΕΡΝΑ"}')
open('ec_hcap_hybrid_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
