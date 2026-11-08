# -*- coding: utf-8 -*-
"""nba_box_value_map_build.py — ΣΥΝΤΕΛΕΣΤΕΣ box score → αξια παικτη για το LIVE (22/10/2026, Στελιος «περνα και τη μιξη στο live»).
Ιδιος μηχανισμος με το nba_tests/t59_inseason_value.py (που περασε): 14 ρυθμοι box ανα λεπτο πανω απο τον μεσο της λιγκας, φθορα 180 μερες,
μαζεμα 300′ προς τον μεσο· γραμμικη αντιστοιχιση στην κλιμακα value() εκπαιδευμενη σε ΟΛΕΣ τις προηγουμενες σεζον (2021-26).
Τρεχει ΤΟΠΙΚΑ μια φορα τον χρονο (θελει nba_player_games.csv + cache t59) → nba_box_value_map.json (committed, το διαβαζει το nba_absence)."""
import os, sys, json
SC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nba_tests')
os.environ.setdefault('T59_CACHE', r'C:\Users\steli\AppData\Local\Temp\claude\C--Users-steli-My-Drive-Betting-Model\3709488e-4308-46b6-86c5-d42c3653842d\scratchpad\t59_cache.pkl')
src = open(os.path.join(SC, 't59_inseason_value.py'), encoding='utf-8').read().split("FIT = {}; DIAG = []")[0]
g = {'__file__': os.path.join(SC, 't59_inseason_value.py'), '__name__': 'x'}
exec(src, g)
np, BX, F, END, VAL, feats, HLD, M0 = g['np'], g['BX'], g['F'], g['END'], g['VAL'], g['feats'], g['HLD'], g['M0']
S_NEW = 2027
mu = (BX[BX.s < S_NEW][F].sum() / BX[BX.s < S_NEW].MIN.sum()).values
Xs, ys, ws = [], [], []
for (p, s_), dEnd in END.items():
    if s_ >= S_NEW or (p, s_) not in VAL: continue
    ft, mn, _, _ = feats(p, s_, dEnd, mu); Xs.append(ft); ys.append(VAL[(p, s_)]); ws.append(mn)
Xs, ys, ws = np.array(Xs), np.array(ys), np.array(ws)
Z = np.c_[np.ones(len(Xs)), Xs]; sw = np.sqrt(ws)
coef = np.linalg.lstsq(Z * sw[:, None], ys * sw, rcond=None)[0]
pr = Z @ coef; r2 = 1 - np.sum(ws * (ys - pr) ** 2) / np.sum(ws * (ys - np.average(ys, weights=ws)) ** 2)
json.dump(dict(built='2026-10-22', season=S_NEW, src='nba_tests/t59_inseason_value.py (LOSO M=500 5/5)', features=F, mu=[float(x) for x in mu],
               coef=[float(x) for x in coef], half_life_days=HLD, prior_min=M0, mix_M=500.0, pairs=int(len(Xs)), r2=round(float(r2), 3),
               note='αξια_φετος = coef[0] + Σ coef[1+i]·((Σ_φθ stat_i + prior·mu_i)/(Σ_φθ λεπτα + prior) − mu_i) · μιξη = (λεπτα·φετος + M·περσι)/(λεπτα + M)'),
          open(os.path.join(os.path.dirname(SC), 'nba_box_value_map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'nba_box_value_map.json: ζευγαρια {len(Xs)} · R² {r2:.3f} · coef {np.round(coef, 3).tolist()}')
