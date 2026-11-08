# -*- coding: utf-8 -*-
"""el_total_level_test.py — ΤΕΣΤ C: διορθωση του «συνολο χαμηλα» στο v2 (25/9/2026, αιτημα Στελιου: «αν αποδεικνυεται σε ROI, δοκιμασε»).

Διαγνωση (el_total_bias_diag): πραγμ − v2 = +2.1 π. (κανονικη περιοδος)· παρατασεις +1.1 (το μοντελο προβλεπει 40′, 4.6% ματς
με παραταση × ~24 π.)· υπολοιπο +1.0 στον κανονικο χρονο. Η αγορα εχει τις παρατασεις μεσα (χωρις παρατ.: −0.1).

ΠΑΡΑΛΛΑΓΕΣ (ολες LOSO: καθε σταθερα υπολογιζεται ΜΟΝΟ απο τις αλλες 5 σεζον, κανονικη περιοδος):
  V0  v2 οπως τρεχει live (βαση)
  V1  v2 + παρατασεις σταθερα  = μεσος ορος (ποσοστο παρατασης × ποντοι παρατασης) των αλλων σεζον
  V2  v2 + παρατασεις ανα ματς = ιδιο μεσο επιπεδο, αλλα αναλογο της πιθανοτητας ισοπαλιας στο 40′ (κοντινα ματς περισσοτερο)
  V3  v2 + ολη η μεροληψια     = μεσο (πραγμ − v2) των αλλων σεζον (παρατασεις + υπολοιπο)
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΜΙΑ εκτελεση) — μια παραλλαγη ΠΕΡΝΑ αν σε σχεση με V0:
  (α) μεση μεροληψια πιο κοντα στο 0 σε ≥4/6 σεζον-εξω
  (β) κλιση b (ενωμενα held-out) οχι μικροτερη
  (γ) ROI συνολου με edge ≥8% ΚΑΙ ≥10% (Pinnacle closing): μεγαλυτερο στο συνολο ΚΑΙ κερδοφορες σεζον οχι λιγοτερες απο V0
Αν περασουν πολλες: αυτη με τον μεγαλυτερο μεσο ROI (≥8% και ≥10%). Αν καμια: μενει το V0.
Εξοδος: el_total_level_test_out.txt"""
import sys, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
_out = []
src = open('el_roi_v2.py', encoding='utf-8').read().split("P('Edge = P")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _out
def P(s=''):
    print(s, flush=True); out.append(str(s))

gmin = D.gmin.values[IDX]; ot = gmin > 40.5
OTC = np.where(ot, TOT - TOT * 40 / gmin, 0.0)            # ποντοι που ηρθαν απο παρατασεις σε καθε ματς
SS = [s for s in EVAL if (RS & (SE == s)).sum() >= 30]
tie = np.exp(-0.5 * (M_V1 / SM) ** 2)                     # σχετικη πιθανοτητα ισοπαλιας στο 40′ (απο τη διαφορα του μοντελου)

def variant(k):
    t = np.array(T_LO, float)
    for s in SS:
        tr = RS & (SE != s) & np.isin(SE, SS); te = SE == s
        if k == 'V1': t[te] += OTC[tr].mean()
        if k == 'V2': t[te] += tie[te] * OTC[tr].mean() / tie[tr].mean()
        if k == 'V3': t[te] += (TOT - T_LO)[tr].mean()
    return t
VAR = {k: variant(k) for k in ('V0', 'V1', 'V2', 'V3')}
NAME = {'V0': 'v2 (live)', 'V1': '+ παρατασεις σταθ.', 'V2': '+ παρατασεις ανα ματς', 'V3': '+ ολη η μεροληψια'}

def tot_bets(tt):
    b = bets(M_V1, tt); return b[b.mkt == 'tot']
res = {}
P('=== ΜΕΣΗ ΜΕΡΟΛΗΨΙΑ (πραγμ − μοντελο), κανονικη περιοδος ===')
P(f'{"":24s} ' + ' '.join(f'{s[-4:]:>7s}' for s in SS) + '   ΟΛΑ  κοντα στο 0 vs V0')
for k, t in VAR.items():
    bias = [np.mean((TOT - t)[RS & (SE == s)]) for s in SS]
    b0 = [np.mean((TOT - VAR['V0'])[RS & (SE == s)]) for s in SS]
    closer = sum(abs(a) < abs(c) for a, c in zip(bias, b0))
    res[k] = dict(closer=closer)
    P(f'{NAME[k]:24s} ' + ' '.join(f'{x:+7.2f}' for x in bias) + f' {np.mean((TOT - t)[RS]):+6.2f}  {closer}/6')
P('')
P('=== ΚΛΙΣΗ b (πραγμ − closing πανω στο μοντελο − closing), κανονικη περιοδος ===')
for k, t in VAR.items():
    m = RS & np.isin(SE, SS)
    b = np.polyfit((t - MT)[m], (TOT - MT)[m], 1)[0]; res[k]['b'] = b
    P(f'{NAME[k]:24s} b {b:+.3f}')
P('')
for thr in (0.03, 0.05, 0.08, 0.10, 0.15):
    P(f'=== ROI ΣΥΝΟΛΟΥ · edge ≥ {thr*100:.0f}% ===')
    for k, t in VAR.items():
        g = tot_bets(t); g = g[g.edge >= thr]
        pos = sum(1 for s in SS if len(g[g.season == s]) and g[g.season == s].p.mean() > 0)
        roi = g.p.mean() * 100
        res[k][thr] = (roi, pos)
        sides = ' · '.join(f'{r} {g[g.role == r].p.mean()*100:+.1f}% ({(g.role == r).sum()})' for r in ('over', 'under'))
        P(f'  {NAME[k]:24s} {roi:+5.1f}% ({len(g)}, {g.p.sum():+.1f}u) {pos}/6 | {sides} | ' +
          ' '.join(f'{s[-2:]}:{g[g.season == s].p.mean()*100:+.0f}%' for s in SS))
P('')
P('=== ΚΡΙΤΗΡΙΟ ===')
passed = []
for k in ('V1', 'V2', 'V3'):
    a = res[k]['closer'] >= 4
    b = res[k]['b'] >= res['V0']['b']
    c = all(res[k][t][0] > res['V0'][t][0] and res[k][t][1] >= res['V0'][t][1] for t in (0.08, 0.10))
    P(f'  {NAME[k]:24s} (α) {"✓" if a else "✗"}  (β) {"✓" if b else "✗"}  (γ) {"✓" if c else "✗"}')
    if a and b and c: passed.append(k)
if passed:
    best = max(passed, key=lambda k: res[k][0.08][0] + res[k][0.10][0])
    P(f'→ ΠΕΡΝΑ: {NAME[best]}')
else:
    P('→ ΚΑΜΙΑ δεν περνα· μενει το v2 οπως ειναι')
open('el_total_level_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
