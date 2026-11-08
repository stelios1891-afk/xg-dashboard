"""
core7_sos_early_test.py — ΤΕΣΤ 1/10/2026 (Στελιος: «κανε ενα τεστ για το 3»): ΣΩΣΤΟ SoS και ΠΡΙΝ την 7η αγωνιστικη;
Live: σωστο SoS 0.75 μονο με 6-13 αντιπαλους. Το παλιο (1.5 στο μεικτο) «κατεστρεφε την ακριβεια» με <6 αντιπαλους
(RPS md2-4 0.1930→0.2143) — ισχυει και για το σωστο;
Εκδοχες (core7_mech_variant): χωρις SoS κατω απο 6 (= live) · 0.75 απο 2/3/4/5 αντιπαλους · 0.5 απο 3/4.
ΜΕΤΡΟ: RPS 1Χ2 (αποτελεσμα) στα ματς με md = 2..5 (η ομαδα με τα λιγοτερα ματς εχει 2-5 φετινα), ανα md & σεζον.
Εκει ΔΕΝ πονταρουμε (picks απο την 7η) — επηρεαζει μονο τις προβλεψεις του dashboard.
ΠΡΟ-ΔΗΛΩΣΗ: μια εκδοχη ΑΞΙΖΕΙ αν RPS (md2-5) καλυτερο απο το live σε ≥3/4 σεζον ΚΑΙ σε καθε md που αγγιζει δεν ειναι
χειροτερο κατα >0.0005. Δεν αλλαζει τιποτα live.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
VAR = [('LIVE (SoS απο 6)', 'cur_0.0_2_13'), ('0.75 απο 2', 'cur_0.75_2_13'), ('0.75 απο 3', 'cur_0.75_3_13'),
       ('0.75 απο 4', 'cur_0.75_4_13'), ('0.75 απο 5', 'cur_0.75_5_13'), ('0.5 απο 3', 'cur_0.5_3_13'), ('0.5 απο 4', 'cur_0.5_4_13')]
def rps1(h, a, gd):
    d = picks.gd_dist_dom(h, a); ph = sum(v for k, v in d.items() if k > 0); pdr = d.get(0, 0.0)
    yy = 2 if gd > 0 else (1 if gd == 0 else 0)
    o1, o2 = (1, 1) if yy == 2 else ((0, 1) if yy == 1 else (0, 0)); return ((ph - o1) ** 2 + (ph + pdr - o2) ** 2) / 2
R = {}
for lab, v in VAR:
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str})
    P = P[(P.md >= 2) & (P.md <= 5) & P.gd.notna()].copy()
    P['rps'] = [rps1(min(max(h, .05), 6), min(max(a, .05), 6), g) for h, a, g in zip(P.xg_h, P.xg_a, P.gd)]
    R[lab] = P.set_index('mid')[['season', 'md', 'rps']]
base = R[VAR[0][0]]; SEAS = sorted(base.season.unique())
print(f'ματς md2-5: {len(base)} · ανα md: ' + ' '.join(f'md{m}: {int((base.md == m).sum())}' for m in range(2, 6)))
print('\nRPS (μικροτερο = καλυτερο) — ολα md2-5 · ανα md · ανα σεζον · Δ vs live ×10⁻⁴')
for lab, _ in VAR:
    x = R[lab].loc[base.index]
    cells = ' '.join(f'md{m} {1e4*(x[x.md == m].rps.mean() - base[base.md == m].rps.mean()):+6.1f}' for m in range(2, 6))
    ss = ' '.join(f'{s}: {1e4*(x[x.season == s].rps.mean() - base[base.season == s].rps.mean()):+6.1f}' for s in SEAS)
    better = sum(x[x.season == s].rps.mean() < base[base.season == s].rps.mean() for s in SEAS)
    worst = max(x[x.md == m].rps.mean() - base[base.md == m].rps.mean() for m in range(2, 6))
    ok = lab != VAR[0][0] and better >= 3 and worst <= 0.0005
    print(f'  {lab:17s} {x.rps.mean():.5f} (Δ {1e4*(x.rps.mean() - base.rps.mean()):+6.1f}) · {cells} · {ss} · καλυτερο {better}/4'
          + (f' → {"ΑΞΙΖΕΙ" if ok else "οχι"}' if lab != VAR[0][0] else ''))
