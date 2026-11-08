# -*- coding: utf-8 -*-
"""el_edge_threshold.py — ΚΑΤΩΦΛΙ EDGE Ευρωλιγκας (1/10/2026, Στελιος: «θελουμε κατι καλο και σε μοναδες και σε ROI,
οχι 20% ROI με ελαχιστα μπετς»). Σημερα: 8% σε χαντικαπ ΚΑΙ συνολα, σταθερο ποντο (αποφαση Στελιου για την 1η χρονια).
Για καθε κατωφλι Κ: ΞΑΝΑ προσομοιωση alert (Crown, πρωτη τιμη με edge ≥ Κ, live μοντελο) + κανονες καταγραφης
(χαντικαπ τελευταιου 2ωρου · συνολα μετα απο κοντρα ≥1.5π). Αναφορα: picks/σεζον, ROI, μοναδες (σταθερο 1 μον.), x/5, t, ανα σεζον.
Εξοδος: el_edge_threshold_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, pick, settle, D, SE5 = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'D', 'SE5'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
def sim(t, K):
    res = []
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(('h_' if t == 21 else 't_') + 'new')
        if m is None or not np.isfinite(m): continue
        ser, tip = r['ser'], r['tip']; o = ser[0]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(t, m, row)
            if e < K: continue
            hrs = (tip - row[0]) / 3600; mv = -(row[1] - o[1]) * side
            if k_ > 0 and ((t == 21 and hrs < 2) or (t == 23 and mv >= 1.5)): break
            res.append((D.season.values[p], settle(t, p, side, row, od))); break
    return pd.DataFrame(res, columns=['sea', 'pnl'])
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
    P(''); P(f'=== {nm} (5 σεζον, σταθερο 1 μον.) ===')
    P(f'  {"κατωφλι":8s} {"picks":>6s} {"/σεζον":>7s} {"ROI":>7s} {"μοναδες":>8s} {"x/5":>4s} {"t":>5s}   ανα σεζον (μοναδες)')
    for K in (0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15, 0.20):
        z = sim(t, K); u = z.pnl.sum(); pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0)
        tt = z.pnl.mean() / z.pnl.std() * np.sqrt(len(z))
        per = ' '.join(f'{s[-2:]}:{z[z.sea == s].pnl.sum():+5.1f}' for s in SE5)
        P(f'  {"≥" + f"{K*100:.0f}%":8s} {len(z):6d} {len(z)/5:7.0f} {z.pnl.mean()*100:+6.1f}% {u:+8.1f} {pos:>2d}/5 {tt:+5.1f}   {per}' + ('   ← ΣΗΜΕΡΑ' if K == 0.08 else ''))
open('el_edge_threshold_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
