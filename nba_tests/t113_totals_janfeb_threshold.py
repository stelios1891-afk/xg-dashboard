# -*- coding: utf-8 -*-
"""t113_totals_janfeb_threshold.py — ΣΥΝΟΛΑ NBA: ΨΗΛΟΤΕΡΟ ΚΑΤΩΦΛΙ ΤΟΝ ΙΑΝ(-ΦΕΒ) (27/10/2026, Στελιος «ναι» · θεμα 6, μετα το t112 ✗).
Ιδιο με t30 Τ9 (χαντικαπ, live 12% Ιαν-Φεβ). Βαση: _t104_totals_live.csv (LIVE μηχανη συνολων, ανοιγμα Crown, 5 σεζον, live = 8% παντου).
ΟΙΚΟΓΕΝΕΙΕΣ: Α «μονο Ιανουαριος» · Β «Ιανουαριος-Φεβρουαριος» · κατωφλι στην περιοδο ∈ {8 (= live), 10, 12, 14, 16}% · αλλους μηνες 8%.
LOSO: για καθε σεζον διαλεγω (περιοδο, κατωφλι) με τις περισσοτερες μοναδες στις ΑΛΛΕΣ 4 → εφαρμογη στην 5η. Και walk-forward (μονο προηγουμενες).
ΚΡΙΤΗΡΙΟ (ιδιο με t30): ΠΕΡΝΑ αν μοναδες LOSO > live ΚΑΙ οχι χειροτερο σε ≥4/5 σεζον. Πληροφορια: CLV & ROI των picks που κοβονται.
Εξοδος: nba_tests/t113_totals_janfeb_threshold_out.txt"""
import os, sys
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
FAM = {'Ιαν': (1,), 'Ιαν-Φεβ': (1, 2)}; THR = (.08, .10, .12, .14, .16)
SE = sorted(X.sea.unique())
def units(fam, thr, m=None):
    t = np.where(X.mon.isin(FAM[fam]), thr, .08); k = X.edge >= t
    if m is not None: k = k & m
    return X.res[k].sum(), k
P(f't113 · ΣΥΝΟΛΑ NBA · Crown ανοιγμα · 5 σεζον · live = 8% παντου: {X.res[X.edge >= .08].sum():+.1f}μ ({int((X.edge >= .08).sum())} picks) (t104: +143.2, 2505)')
P('\nΟΛΕΣ ΟΙ ΕΚΔΟΧΕΣ (in-sample, μονο για εικονα): μοναδες · picks · ανα σεζον · picks που κοβονται (ROI, CLV)')
for fam in FAM:
    for thr in THR:
        u, k = units(fam, thr); cut = (X.edge >= .08) & ~k
        per = ' '.join(f'{s % 100}:{X.res[k & (X.sea == s)].sum():+.1f}' for s in SE)
        P(f'  {fam:8s} {100 * thr:3.0f}%: {u:+6.1f}μ · {int(k.sum())} picks · {per}' + (f' · κοβονται {int(cut.sum())}: ROI {100 * X.res[cut].mean():+.1f}% CLV {X.clv[cut].mean():+.2f}π' if cut.any() else ''))
opts = [(f, t) for f in FAM for t in THR]
ch, tot, totL, perb = [], 0.0, 0.0, []
for s in SE:
    oth = X.sea != s; cur = X.sea == s
    b = max(opts, key=lambda o: units(*o, oth)[0]); u = units(*b, cur)[0]; uL = units('Ιαν', .08, cur)[0]
    ch.append(f'{s % 100}:{b[0]} {100 * b[1]:.0f}%'); tot += u; totL += uL; perb.append(u >= uL - 1e-9)
P(f'\nLOSO: επιλογες {" · ".join(ch)} → μοναδες {tot:+.1f} vs live {totL:+.1f} · οχι χειροτερο σε {sum(perb)}/5 → {"ΠΕΡΝΑΕΙ" if tot > totL and sum(perb) >= 4 else "✗"}')
ch, tot, totL = [], 0.0, 0.0
for s in SE[2:]:
    prev = X.sea < s; cur = X.sea == s
    b = max(opts, key=lambda o: units(*o, prev)[0]); tot += units(*b, cur)[0]; totL += units('Ιαν', .08, cur)[0]; ch.append(f'{s % 100}:{b[0]} {100 * b[1]:.0f}%')
P(f'walk-forward (απο 3η σεζον): επιλογες {" · ".join(ch)} → μοναδες {tot:+.1f} vs live {totL:+.1f}')
P('\nIAN μονο, ζωνες edge (ROI, picks, θετ. σεζον): ' + ' · '.join(
    f"{100 * lo:.0f}-{100 * hi:.0f}%: {100 * X.res[(X.mon == 1) & (X.edge >= lo) & (X.edge < hi)].mean():+.1f}% ({int(((X.mon == 1) & (X.edge >= lo) & (X.edge < hi)).sum())}, "
    f"{int((X[(X.mon == 1) & (X.edge >= lo) & (X.edge < hi)].groupby('sea').res.sum() > 0).sum())}/5)" for lo, hi in ((.08, .10), (.10, .12), (.12, .16), (.16, 9))))
P('ΦΕΒ μονο, ζωνες edge: ' + ' · '.join(
    f"{100 * lo:.0f}-{100 * hi:.0f}%: {100 * X.res[(X.mon == 2) & (X.edge >= lo) & (X.edge < hi)].mean():+.1f}% ({int(((X.mon == 2) & (X.edge >= lo) & (X.edge < hi)).sum())})" for lo, hi in ((.08, .10), (.10, .12), (.12, .16), (.16, 9))))
open(os.path.join(SC, 't113_totals_janfeb_threshold_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
