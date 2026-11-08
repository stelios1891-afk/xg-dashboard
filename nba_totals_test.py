# -*- coding: utf-8 -*-
"""nba_totals_test.py — NBA ΣΥΝΟΛΑ ΠΟΝΤΩΝ με το μοντελο της Ευρωλιγκας (28/9/2026, ερωτημα Στελιου «αυτο ειναι χαντικαπ και ποντοι μαζι;»).
Ιδια δεδομενα/αντιστοιχιση με nba_model_test.py· αγορα = Crown closing συνολο (Nowgoal t=23).
Παραλλαγες: (1) οπως το χαντικαπ της EL (τυχη 50%, HL 120, περσι 0.7) · (2) οπως τα συνολα της EL v2 (τυχη 25%, χωρις φθορα).
Το μοντελο προβλεπει 48′ → + μεσος ορος παρατασεων (μετρημενος, οπως στην EL).
ΜΕΤΡΑ: RMSE συνολου vs αγορα · κλιση b · ROI over/under σε edge ≥5/8/10% · ανα περιοδο (Οκτ-Δεκ / Ιαν-Απρ) · ανα σεζον.
Εξοδος: nba_totals_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_model_test.py', encoding='utf-8').read().split("P('')\nP('=== ΒΑΣΙΚΟ ΜΟΝΤΕΛΟ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
TI = np.array([i for i in IDX if 'T' in MK[i]]); TSE = G.season.values[TI]
TOT = (G.hs + G.as_).values[TI].astype(float); MT = np.array([MK[i]['T'] for i in TI])
OTP = ((G.hs + G.as_) * (1 - 48 / G.mins)).values                      # ποντοι που ηρθαν απο παρατασεις
OT_ADD = float(OTP[np.isin(G.season.values, EVAL)].mean())
TSIG = float(np.std((TOT - MT)[np.isin(TSE, EVAL)]))
P(f'ματς με Crown closing συνολο: {len(TI)} · παρατασεις +{OT_ADD:.2f} π./ματς · διασπορα (πραγματικο − closing) {TSIG:.2f} π.')
MON = G.date.dt.month.values[TI]
def bets(t, thr, mask):
    rows = []
    for j, i in enumerate(TI):
        if not mask[j]: continue
        r = MK[i]; T = r['T']; mu = t[i]
        if abs(T - round(T)) < 1e-9:
            po = 1 - Phi((T + 0.5 - mu) / TSIG); pu = Phi((T - 0.5 - mu) / TSIG)
        else:
            po = 1 - Phi((T - mu) / TSIG); pu = 1 - po
        pq = 1 - po - pu; eo, eu = po * r['ov'] + pq - 1, pu * r['un'] + pq - 1
        side, e, od = ('over', eo, r['ov']) if eo >= eu else ('under', eu, r['un'])
        if e < thr: continue
        v = (TOT[j] - T) * (1 if side == 'over' else -1)
        rows.append(dict(season=TSE[j], side=side, p=(od - 1) if v > 0 else (0 if v == 0 else -1)))
    return pd.DataFrame(rows)
def report(lab, t):
    m = np.isin(TSE, EVAL); e = TOT - t[TI]
    b = np.polyfit((t[TI] - MT)[m], (TOT - MT)[m], 1)[0]
    P(f'=== {lab} ===')
    P(f'  RMSE {np.sqrt(np.mean(e[m] ** 2)):.2f} (αγορα {np.sqrt(np.mean((TOT - MT)[m] ** 2)):.2f}) · μεση μεροληψια (πραγμ − μοντ) {np.mean(e[m]):+.1f} · b {b:+.3f}')
    for thr in (0.05, 0.08, 0.10):
        R = bets(t, thr, m); pos = sum(1 for s in EVAL if len(R[R.season == s]) and R[R.season == s].p.mean() > 0)
        sides = ' · '.join(f'{sd} {R[R.side == sd].p.mean()*100:+.1f}% ({(R.side == sd).sum()})' for sd in ('over', 'under'))
        P(f'  edge ≥{thr*100:.0f}%: {R.p.mean()*100:+.1f}% ({len(R)}, {R.p.sum():+.0f}u) {pos}/{len(EVAL)} | {sides}')
    for nm, mm in (('Οκτ-Δεκ', np.isin(MON, [10, 11, 12])), ('Ιαν-Απρ', np.isin(MON, [1, 2, 3, 4, 5]))):
        k = m & mm; bb = np.polyfit((t[TI] - MT)[k], (TOT - MT)[k], 1)[0]; R = bets(t, 0.08, k)
        P(f'  {nm}: RMSE {np.sqrt(np.mean(e[k] ** 2)):.2f} / αγορα {np.sqrt(np.mean((TOT - MT)[k] ** 2)):.2f} · b {bb:+.2f} · ROI ≥8% {R.p.mean()*100:+.1f}% ({len(R)}) | ' +
          ' '.join(f'{s}:{R[R.season == s].p.mean()*100:+.0f}%' for s in EVAL))
    P('')
t1 = run(h=3.0, lam=8, HL=120, carry=0.7, lw=0.5)[1] + OT_ADD
report('(1) οπως το χαντικαπ της EL (τυχη 50%, HL 120)', t1)
t2 = run(h=3.0, lam=8, HL=9999, carry=0.7, lw=0.25)[1] + OT_ADD
report('(2) οπως τα συνολα της EL v2 (τυχη 25%, χωρις φθορα)', t2)
t3 = run(h=2.0, lam=8, HL=60, carry=0.7, lw=0.5)[1] + OT_ADD
report('(3) η καλυτερη ρυθμιση χαντικαπ NBA (εδρα 2, HL 60)', t3)
open('nba_totals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
