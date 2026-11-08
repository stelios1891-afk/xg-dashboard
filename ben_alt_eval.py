# -*- coding: utf-8 -*-
"""ben_alt_eval.py — 19/10/2026: ΠΟΙΑ ΕΝΑΛΛΑΚΤΙΚΗ για τις 9 λιγκες του Ben (ο Ben σταματησε 21/9).
Σημερινη ευρωπαικη αλυσιδα (euro_variant_build: K=8, W=2, μιξη 0.6, γ, κ, ισοπαλιες) — αλλαζει ΜΟΝΟ η πηγη των 9 λιγκων:
  BEN (σημειο αναφορας) · ΓΚΟΛ (σημερινη προσωρινη λυση, χωρις Elo) · ΓΚΟΛ+ELO (οπως Κυπρος/Βουλγαρια) · FOOTYSTATS xG.
Δειγμα: ευρωπαικα ματς 2024-26 με ≥1 ομαδα απο λιγκα του Ben (Ben υπαρχει μονο απο 2425).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: (α) μονιμη αντικατασταση του Ben μονο αν RPS καλυτερο ΚΑΙ στις 2 σεζον με t ≤ −2·
              (β) για το κενο οσο λειπει ο Ben → η εναλλακτικη με το καλυτερο RPS (ολο το δειγμα).
Εξοδος: ben_alt_eval_out.txt"""
import sys, pickle
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import picks
B = pickle.load(open('euro_v6w2_preds_ben_base.pkl', 'rb'))
SRC = {str(m): (h, a) for m, h, a in zip(B['mids'], B['src_h'], B['src_a'])}
ARMS = [('BEN', 'ben_base'), ('ΓΚΟΛ (τωρινη προσωρινη)', 'ben_goals'), ('ΓΚΟΛ + ELO', 'ben_elo'), ('FOOTYSTATS', 'ben_fs')]
D = {lab: pickle.load(open(f'euro_blend_dump_{t}.pkl', 'rb')) for lab, t in ARMS}
base = D['BEN']; idx = {str(m): i for i, m in enumerate(base['MIDS'])}
sel = [m for m in idx if m in SRC and 'griffis' in SRC[m]]
def met(d, mids):
    j = {str(m): i for i, m in enumerate(d['MIDS'])}
    out = []
    for m in mids:
        i = j[m]; lh, la = max(d['LH'][i], .05), max(d['LA'][i], .05); gh, ga = d['GH'][i], d['GA'][i]
        dist = picks.gd_dist(lh, la); ph = sum(p for k, p in dist.items() if k > 0); pd_ = dist.get(0, 0.0)
        o = 0 if gh > ga else (1 if gh == ga else 2)
        rps = 0.5 * ((ph - (o == 0)) ** 2 + (ph + pd_ - (o <= 1)) ** 2)
        out.append((rps, abs((gh - ga) - (lh - la)), abs((gh + ga) - (lh + la))))
    return np.array(out)
SEA = {str(m): s for m, s in zip(base['MIDS'], base['SEA'])}
print(f'Δειγμα: {len(sel)} ευρωπαικα ματς με ομαδα απο λιγκα του Ben (2425: {sum(SEA[m] == "2425" for m in sel)} · 2526: {sum(SEA[m] == "2526" for m in sel)})')
print('(μικροτερο = καλυτερο · Δ = εναλλακτικη − Ben · t = ποσο σιγουρο, ≤ −2 σημαινει σιγουρα καλυτερο)\n')
for title, mids in (('ΟΛΑ', sel), ('2024-25', [m for m in sel if SEA[m] == '2425']), ('2025-26', [m for m in sel if SEA[m] == '2526'])):
    M0 = met(base, mids)
    print(f'== {title} (n={len(mids)}) ==')
    print(f'   {"πηγη":26s} {"RPS 1Χ2":>8s} {"Δ RPS":>8s} {"t":>6s} │ {"λαθος διαφορας":>14s} {"Δ":>7s} │ {"λαθος συνολου":>13s} {"Δ":>7s} {"t":>6s}')
    for lab, _ in ARMS:
        M = met(D[lab], mids); d = M - M0
        t = lambda v: v.mean() / (v.std() / np.sqrt(len(v))) if v.std() > 0 else 0.0
        print(f'   {lab:26s} {M[:, 0].mean():8.4f} {d[:, 0].mean():+8.4f} {t(d[:, 0]):6.2f} │ {M[:, 1].mean():14.3f} {d[:, 1].mean():+7.3f} │ '
              f'{M[:, 2].mean():13.3f} {d[:, 2].mean():+7.3f} {t(d[:, 2]):6.2f}')
    print()
