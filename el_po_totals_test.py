# -*- coding: utf-8 -*-
"""el_po_totals_test.py — ΕΥΡΩΛΙΓΚΑ: ΠΛΕΙ-ΟΦ/F4 ΣΤΑ ΣΥΝΟΛΑ (5/10/2026). el_clean_tests ΤΕΣΤ 4: το μοντελο υπερεκτιμα τα συνολα των πλει-οφ
κατα 7.8 π. (t −4.9, 5/5) — η αγορα κατα 2.8 (t −1.7). ΜΗΧΑΝΙΣΜΟΣ: διορθωση συνολου πλει-οφ = μεσο υπολοιπο πλει-οφ των ΑΛΛΩΝ σεζον (LOSO).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: ΑΛΛΑΓΗ αν RMSE πλει-οφ καλυτερο σε ≥4/5 σεζον. Αναφορα: ROI picks πλει-οφ (≥8%, ανοιγμα) πριν/μετα, χαντικαπ πλει-οφ ROI.
Εξοδος: el_po_totals_test_out.txt"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'p'}
exec(open('el_clean_tests.py', encoding='utf-8').read().split("# ---------------- ΤΕΣΤ 2 μιξη ----------------")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1), NS)
HELD_T, TOT, SEAS_, PH, SE5, bets, CUR_T, MK = (NS[k] for k in ('HELD_T', 'TOT', 'SEAS_', 'PH', 'SE5', 'bets', 'CUR_T', 'MK'))
NS['out'].clear()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
PO = PH != 'RS'
R = TOT - HELD_T
adj = HELD_T.copy(); offs = {}
for Y in SE5:
    tr = PO & np.isin(SEAS_, [x for x in SE5 if x != Y]) & np.isfinite(R); offs[Y] = R[tr].mean()
    m = PO & (SEAS_ == Y); adj[m] = HELD_T[m] + offs[Y]
rm = lambda v, Y: float(np.sqrt(np.mean((TOT - v)[PO & (SEAS_ == Y) & np.isfinite(v)] ** 2)))
d = [rm(adj, Y) - rm(HELD_T, Y) for Y in SE5]
P(f'διορθωση πλει-οφ ανα σεζον (απο τις αλλες): ' + ' · '.join(f'{Y[-2:]}:{v:+.1f}' for Y, v in offs.items()))
P(f'RMSE πλει-οφ ανα σεζον (μετα − πριν): ' + ' '.join(f'{Y[-2:]}:{x:+.2f}' for Y, x in zip(SE5, d)) + f' → {sum(x < 0 for x in d)}/5' + ('  <- ΑΛΛΑΓΗ' if sum(x < 0 for x in d) >= 4 else '  <- ✗'))
for lab, v in (('πριν', HELD_T), ('με διορθωση', adj)):
    Rr = bets(23, v, CUR_T, 'o', PO); u = [r[1] for r in Rr]
    P(f'  συνολα πλει-οφ ≥8% {lab:12s}: {len(u)} picks · ROI {np.mean(u)*100 if u else 0:+.1f}% · {sum(u):+.1f}u · over {sum(1 for r in Rr if (TOT[r[0]] - MK[23][r[0]]["o"][1]) * 0 == 0 and r[2] is not None and (NS["HELD_T"][r[0]] if lab == "πριν" else adj[r[0]]) > MK[23][r[0]]["o"][1])}')
open('el_po_totals_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
