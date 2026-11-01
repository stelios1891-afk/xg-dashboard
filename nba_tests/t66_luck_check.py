# -*- coding: utf-8 -*-
"""t66_luck_check.py — ΕΛΕΓΧΟΣ ΤΥΧΗΣ για το t65 (24/10/2026, Στελιος «ok»): οι 3 εκδοχες του φετινου κομματιου στο ΧΑΝΤΙΚΑΠ NBA
(Α δικος μας μιξη LOSO M · «μονο δικος μας» · Β δικο μας box LOSO M) vs ΣΗΜΕΡΙΝΗ, 2023-26, ιδιες προβλεψεις/picks με t65_bet.py.
Ζευγαρωτη διαφορα μοναδων ανα ματς ± τυπ. σφαλμα · reality check bootstrap 5000 (κεντραρισμενες διαφορες → πιθανοτητα ο ΚΑΛΥΤΕΡΟΣ
απο τους 3 να φτασει το προβαδισμα απο τυχη) · και ο ιδιος ελεγχος ανα ΜΠΛΟΚ ΕΒΔΟΜΑΔΑΣ (ματς της ιδιας εβδομαδας μαζι — μοιραζονται απουσιες).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: Β στο live αν πιθανοτητα τυχης (καλυτερος απο 3, ανα ματς) < 0.10· αλλιως σκια.
Εξοδος: nba_tests/t66_luck_check_out.txt"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't65_bet.py'), encoding='utf-8').read().split('# (ii) ΣΥΝΟΛΑ')[0]
r = "def SAVE():\n    open(OUTF, 'a', encoding='utf-8').write('" + chr(92) + "n'.join(out) + '" + chr(92) + "n'); out.clear()"
assert src.count(r) == 1
G = {'__file__': os.path.join(SC, 't65_bet.py'), '__name__': 't65'}
with contextlib.redirect_stdout(_B()): exec(src.replace(r, 'def SAVE(): out.clear()'), G)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
SUMH, REF, TM, ys, D, TEST = G['SUMH'], G['REF'], G['TM'], G['ys'], G['D'], G['TEST']
C = ['δικος μας μιξη LOSO M', 'μονο δικος μας', 'δικο μας box LOSO M']
LAB = {C[0]: 'Α δικος μας συνδυασμος', C[1]: 'μονο δικος μας', C[2]: 'Β δικο μας box (νεα βαρη)'}
P(f'ματς 2023-26: {int(TM.sum())} · ΣΗΜΕΡΙΝΗ picks {REF["n"]} · μοναδες {REF["u"]:+.1f} (στοχος +120.1)')
Dm = np.c_[[(SUMH[c]['vec'] - REF['vec'])[TM] for c in C]].T; obs = Dm.sum(0)
wk = pd.to_datetime(pd.Series(D.date.values[TM]).astype(str).str[:10]).dt.to_period('W').astype(str).values
rng = np.random.default_rng(20261024)
def rc(M, blocks=None, B=5000):
    Mc = M - M.mean(0); MX = np.empty(B); SG = np.empty((B, M.shape[1]))
    if blocks is None:
        for b in range(B):
            s_ = Mc[rng.integers(0, len(Mc), len(Mc))].sum(0); MX[b] = s_.max(); SG[b] = s_
    else:
        ub = np.unique(blocks); idx = {u: np.where(blocks == u)[0] for u in ub}; S_b = np.array([Mc[idx[u]].sum(0) for u in ub])
        for b in range(B):
            s_ = S_b[rng.integers(0, len(ub), len(ub))].sum(0); MX[b] = s_.max(); SG[b] = s_
    return MX, SG
MX, SG = rc(Dm); MXw, SGw = rc(Dm, wk)
P(''); P('## ΖΕΥΓΑΡΩΤΗ ΔΙΑΦΟΡΑ vs ΣΗΜΕΡΙΝΗ (μοναδες, 2023-26) · πιθανοτητα τυχης (bootstrap 5000)')
P('  εκδοχη                     | Δμοναδες ± σφαλμα | ματς με αλλο αποτελεσμα | τυχη ΜΟΝΟΣ του | τυχη ως καλυτερος απο 3 | ιδιο ανα εβδομαδα (μονος / καλυτερος απο 3)')
for j, c in enumerate(C):
    se = Dm[:, j].std(ddof=1) * np.sqrt(len(Dm))
    P(f'  {LAB[c]:26s} | {obs[j]:+6.1f} ± {se:4.1f}    | {int((Dm[:, j] != 0).sum()):4d}                    | {np.mean(SG[:, j] >= obs[j]):.3f}          | {np.mean(MX >= obs[j]):.3f}                   | '
      f'{np.mean(SGw[:, j] >= obs[j]):.3f} / {np.mean(MXw >= obs[j]):.3f}')
P(''); P('## ΑΝΑ ΣΕΖΟΝ (Δμοναδες vs ΣΗΜΕΡΙΝΗ)')
for j, c in enumerate(C):
    P(f'  {LAB[c]:26s} ' + ' · '.join(f'{s}: {Dm[ys[TM] == s, j].sum():+5.1f}' for s in TEST) + f' · θετικες {sum(Dm[ys[TM] == s, j].sum() > 0 for s in TEST)}/4')
pB = float(np.mean(MX >= obs[2]))
P(''); P(f'## ΚΡΙΣΗ (προ-δηλωμενη): Β πιθανοτητα τυχης ως καλυτερος απο 3 = {pB:.3f} → ' + ('Β ΣΤΟ LIVE (< 0.10)' if pB < 0.10 else 'ΣΚΙΑ για το Β (≥ 0.10)'))
open(os.path.join(SC, 't66_luck_check_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
