"""euro_value_apply_example.py — 10/10/2026: πως αλλαζει το στρωμα αξιας (παραλλαγη _D, c=0.1) τις προβλεψεις Roma–Real και City–PSG (14/10).
Συντελεστες υπολοιπου (a, b, d) απο ΟΛΕΣ τις 4 σεζον· αξιες τωρα απο core7_team_vfull.json (24/9, p80 XI 365 ημερων)."""
import sys, io, json, math, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_value_all_test_D.py', encoding='utf-8').read().split('RB = roi_tab(BASE)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'ex'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
LV, LR, DD = g['LV'], g['LR'], g['DD']; aff = np.isfinite(LV)
a, b, d = np.linalg.lstsq(np.c_[np.ones(aff.sum()), LR[aff], DD[aff]], LV[aff], rcond=None)[0]
print(f'υπολοιπο: z = ln(V_γηπ/V_φιλ) − ({a:+.3f} + {b:.3f}·ln(λγ/λφ) + {d:.3f}·διαφορα λιγκας) · διορθωση λ ×e^(±0.1·z/2)')
import picks
V = json.load(open('core7_team_vfull.json', encoding='utf-8'))['leagues']
val = {x['name']: x['vfull'] for L in V.values() for x in L.values()}
P = json.load(open('euro_projections.json', encoding='utf-8')); O = json.load(open('euro_odds_latest.json', encoding='utf-8'))['odds']
DG = {('Roma', 'Real Madrid'): 0.026, ('Manchester City', 'Paris Saint-Germain'): 0.255}
def probs(lh, la):
    dist = picks.gd_dist(lh, la); px = dist.get(0, 0); k = (1 - 0.85 * px) / (1 - px)
    p1 = sum(p for kk, p in dist.items() if kk > 0) * k; p2 = sum(p for kk, p in dist.items() if kk < 0) * k
    return p1, 0.85 * px, p2
for m in P['matches']:
    key = (m['home'], m['away'])
    if key not in DG: continue
    lh, la = m['xgh'], m['xga']; Vh, Va = val[m['home']], val[m['away']]
    z = math.log(Vh / Va) - (a + b * math.log(lh / la) + d * DG[key])
    lh2, la2 = lh * math.exp(0.1 * z / 2), la * math.exp(-0.1 * z / 2)
    mk = O.get(m['mid'], {})
    print(f'\n{m["home"]} – {m["away"]}: αξια {Vh / 1e6:.0f} vs {Va / 1e6:.0f} εκ. (ln {math.log(Vh / Va):+.2f}) · αναμενομενο απο μοντελο+λιγκα {a + b * math.log(lh / la) + d * DG[key]:+.2f} → υπολοιπο z {z:+.2f}')
    for lab, (x, y) in (('σημερα', (lh, la)), ('με αξια', (lh2, la2))):
        p1, px, p2 = probs(x, y)
        print(f'   {lab:8s} xG {x:.2f}-{y:.2f} (υπεροχη {x - y:+.2f}) · 1Χ2 {100 * p1:.0f}/{100 * px:.0f}/{100 * p2:.0f}% · δικαιες {1 / p1:.2f}/{1 / px:.2f}/{1 / p2:.2f}')
    print(f'   αγορα    1Χ2 {mk.get("h")}/{mk.get("d")}/{mk.get("a")} · χαντικαπ γηπ {mk.get("line")} @{mk.get("oh")}/{mk.get("oa")}')
