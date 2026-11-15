# -*- coding: utf-8 -*-
"""el_expert_prior_early.py — ΤΕΣΤ #2 (25/9/2026, διορθωση Στελιου: «τους ειδικους τους χρειαζομαστε κυριως στις πρωτες αγωνιστικες»).
Ιδια πηγη/μεθοδος με el_expert_prior_test.py, αλλα:
  ΧΡΗΣΗ: προβλεψη με ειδικους ΜΟΝΟ στις αγωνιστικες ≤ R (R = 6 ή 10)· μετα σκετο v1.
  ΕΠΙΛΟΓΗ: LOSO του α (και R) με ROI edge ≥5% ΜΟΝΟ στις αγωνιστικες ≤ R των αλλων 4 σεζον.
  ΚΡΙΤΗΡΙΟ (προ-δηλωμενο, ΜΙΑ εκτελεση): στις αγωνιστικες 1-10 των held-out σεζον, ROI μεγαλυτερο απο v1 σε edge ≥5% ΚΑΙ ≥8% ΚΑΙ ≥10%,
  κερδοφορες σεζον οχι λιγοτερες. ΣΗΜΕΙΩΣΗ: 2η δοκιμη της ιδιας ιδεας + μικρο δειγμα (~300 στοιχηματα) → αν περασει, ΣΚΙΑ πρωτα.
Εξοδος: el_expert_prior_early_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_expert_prior_test.py', encoding='utf-8').read().split("P('')\nP('=== LOSO επιλογη α")[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("P('θεση ειδικων", "pass  # P('θεση ειδικων")
exec(src)
out.clear()

GR = [(a, R) for a in ALPHAS for R in (6, 10)]
def early(a, R):
    return np.where(RND <= R, PRED[a], M_V1)
BE = {c: sp(early(*c)) for c in GR}
W = lambda b: b[b.rnd <= 10]
def roiR(b, thr, ss, R):
    x = b[(b.edge >= thr) & b.season.isin(ss) & (b.rnd <= R)]; return x.p.mean() if len(x) else -9

P('=== LOSO (επιλογη με ROI ≥5% στις αγωνιστικες ≤ R των αλλων 4 σεζον) ===')
held = []
for s in ES:
    tr = [t for t in ES if t != s]
    c = max(GR, key=lambda c: roiR(BE[c], .05, tr, c[1]))
    b = BE[c]; held.append(b[b.season == s])
    P(f'  {s[-4:]} εξω: α {c[0]} εως αγων {c[1]} → αγων 1-10 ROI εξω {roiR(b, .05, [s], 10)*100:+.1f}% vs v1 {roiR(BV1, .05, [s], 10)*100:+.1f}%')
H = W(pd.concat(held)); V = W(BV1)
P('')
P('=== ΑΠΟΤΕΛΕΣΜΑ — ΜΟΝΟ ΑΓΩΝΙΣΤΙΚΕΣ 1-10, held-out 2021-2025 ===')
ok = True
for thr in (0.03, 0.05, 0.08, 0.10, 0.15):
    a, v = H[H.edge >= thr], V[V.edge >= thr]
    pa = sum(1 for s in ES if len(a[a.season == s]) and a[a.season == s].p.mean() > 0)
    pv = sum(1 for s in ES if len(v[v.season == s]) and v[v.season == s].p.mean() > 0)
    if thr in (0.05, 0.08, 0.10): ok &= (a.p.mean() > v.p.mean()) and pa >= pv
    P(f'  edge ≥{thr*100:2.0f}%: με ειδικους {cell(a)} {pa}/5 · v1 {cell(v)} {pv}/5')
P('')
P('  ανα σεζον (edge ≥5%, αγων 1-10): ' + ' · '.join(f'{s[-4:]}: {H[(H.edge >= .05) & (H.season == s)].p.mean()*100:+.0f}% vs {V[(V.edge >= .05) & (V.season == s)].p.mean()*100:+.0f}%' for s in ES))
P('')
P('  (αναφορα) καθε συνδυασμος σε ολες τις 5 σεζον, αγων 1-10 · edge ≥5% / ≥8% / ≥10% · ματς με θετικη σεζον')
P(f'    v1          : {cell(V[V.edge >= .05])} · {cell(V[V.edge >= .08])} · {cell(V[V.edge >= .10])}')
for c in GR:
    b = W(BE[c]); pos = sum(1 for s in ES if b[(b.edge >= .05) & (b.season == s)].p.mean() > 0)
    P(f'    α {c[0]:<4} εως {c[1]:2d}: {cell(b[b.edge >= .05])} · {cell(b[b.edge >= .08])} · {cell(b[b.edge >= .10])} · {pos}/5')
P('')
P(f'→ {"ΠΕΡΝΑ (→ σκια πρωτα: 2η δοκιμη, μικρο δειγμα)" if ok else "ΔΕΝ ΠΕΡΝΑ — μενει το v1"}')
open('el_expert_prior_early_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
