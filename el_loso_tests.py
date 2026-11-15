# -*- coding: utf-8 -*-
"""el_loso_tests.py — LOSO επιλογη μηχανισμων Ευρωλιγκας (24/9/2026, προταση Στελιου).

Γιατι: το el_mech_tests διαλεξε «νικητες» κοιτωντας ΚΑΙ τις 6 σεζον — η βελτιωση μπορει να ειναι φουσκωμενη απο την επιλογη.
Εδω: για καθε σεζον-εξω, ο καλυτερος συνδυασμος διαλεγεται ΜΟΝΟ απο τις αλλες 5 και κρινεται στη σεζον-εξω.

ΠΛΕΓΜΑ (216): διορθωση αντιπαλου {ναι, οχι} × ημιζωη {60, 120, καμια} × περσινη εικονα {0.5, 0.7, 1.0} × βαρος περσινης {4, 8, 14}
               × εδρα {4, 5, 6, απο 2 προηγ. σεζον}. ΣΤΑΘΕΡΑ: τυχη 3P/FT, ρυθμος ανα ομαδα, ουδετερο εκτος πολης, νεες ομαδες = 0.
ΜΕΤΡΟ: b = κλιση του (πραγματικο − closing) πανω στο (μοντελο − closing) — χωριστα διαφορα & συνολο (δυο «μηχανες»).
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ (ΜΙΑ εκτελεση): για καθε αγορα, η LOSO-επιλογη ΥΙΟΘΕΤΕΙΤΑΙ αν στις 6 σεζον-εξω το b της ειναι
  μεγαλυτερο απο του v1 ΣΤΟ ΣΥΝΟΛΟ (ενωμενα τα 6 held-out) ΚΑΙ σε ≥4/6 σεζον. Αλλιως μενει το v1.
Εξοδος: el_loso_tests_out.txt
"""
import sys, itertools, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

src = open('el_mech_tests.py', encoding='utf-8').read().split('VARIANTS = [')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
SS = [s for s in EVAL if (SE == s).sum() >= 30]

GRID = list(itertools.product([True, False], [60, 120, 9999], [0.5, 0.7, 1.0], [4, 8, 14], [4.0, 5.0, 6.0, 'roll']))
P(f'πλεγμα {len(GRID)} συνδυασμοι · σεζον {SS}')
PRED = {}
for i, (adj, HL, carry, lam, h) in enumerate(GRID):
    kw = dict(adj=adj, HL=HL, carry=carry, lam=lam)
    kw.update(h_roll=True) if h == 'roll' else kw.update(h=h)
    pr = run(**kw); PRED[(adj, HL, carry, lam, h)] = (pr[IDX, 0], pr[IDX, 1])
    if (i + 1) % 24 == 0: P(f'  {i + 1}/{len(GRID)}')
V1 = (True, 120, 0.7, 8, 6.0)

def b_of(mo, mkv, a, mask):
    x, y = (mo - mkv)[mask], (a - mkv)[mask]
    return np.polyfit(x, y, 1)[0]
def lab(c):
    adj, HL, carry, lam, h = c
    return f'αντιπ {"ναι" if adj else "οχι"} · φθορα {"καμια" if HL == 9999 else HL} · περσι {int(carry*100)}% · βαρος {lam} · εδρα {h}'

for mi, (name, mkv, a) in enumerate((('ΔΙΑΦΟΡΑ (χαντικαπ)', MM, ACT), ('ΣΥΝΟΛΟ ΠΟΝΤΩΝ', MT, TOT))):
    P(f'\n=== {name} ===')
    held_x, held_y, v1_x, v1_y, wins, picks = [], [], [], [], 0, []
    for s in SS:
        tr = (SE != s) & np.isin(SE, SS); te = SE == s
        best = max(GRID, key=lambda c: b_of(PRED[c][mi], mkv, a, tr))
        picks.append(best)
        bb = b_of(PRED[best][mi], mkv, a, te); b1 = b_of(PRED[V1][mi], mkv, a, te)
        wins += bb > b1
        held_x.append(PRED[best][mi][te] - mkv[te]); held_y.append(a[te] - mkv[te])
        v1_x.append(PRED[V1][mi][te] - mkv[te]); v1_y.append(a[te] - mkv[te])
        P(f'  {s[1:]} εξω: επιλογη [{lab(best)}] → b {bb:+.2f} · v1 {b1:+.2f}')
    X, Y = np.concatenate(held_x), np.concatenate(held_y); X1, Y1 = np.concatenate(v1_x), np.concatenate(v1_y)
    bL = np.polyfit(X, Y, 1)[0]; b1 = np.polyfit(X1, Y1, 1)[0]
    ok = bL > b1 and wins >= 4
    P(f'  ΣΥΝΟΛΟ 6 σεζον-εξω: LOSO b {bL:+.3f} · v1 b {b1:+.3f} · LOSO καλυτερο σε {wins}/{len(SS)} → {"ΥΙΟΘΕΤΕΙΤΑΙ" if ok else "ΜΕΝΕΙ ΤΟ v1"}')
    from collections import Counter
    for j, nm in enumerate(('διορθωση αντιπαλου', 'φθορα', 'περσινη εικονα', 'βαρος περσινης', 'εδρα')):
        P(f'    σταθεροτητα επιλογης — {nm}: ' + ', '.join(f'{k}×{v}' for k, v in Counter(str(p[j]) for p in picks).most_common()))
    best_all = max(GRID, key=lambda c: b_of(PRED[c][mi], mkv, a, np.isin(SE, SS)))
    P(f'  (αναφορα) καλυτερο σε ολες μαζι: [{lab(best_all)}] b {b_of(PRED[best_all][mi], mkv, a, np.isin(SE, SS)):+.3f}')
open('el_loso_tests_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
