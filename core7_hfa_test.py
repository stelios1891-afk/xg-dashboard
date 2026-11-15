"""
core7_hfa_test.py — ΤΕΣΤ 28/9/2026 (βημα 3 σχεδιου): ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ στα εγχωρια. Διαγνωση core7_diag: μεση υπεροχη γηπεδουχου
μοντελο +0.278 vs πραγματικο/αγορα +0.342.
Εκδοχες: s = s_mod + h (T αμεταβλητο). (Α) ΕΝΙΑΙΟ h = μεση(gd − s_mod) στις ΑΛΛΕΣ σεζον (LOSO) · (Β) ΑΝΑ ΛΙΓΚΑ h_L ιδιο LOSO ·
(Γ) σταθερα h ∈ {0.03, 0.06, 0.09} για πληροφορια.
ΠΡΟ-ΔΗΛΩΣΗ: ΠΕΡΝΑ αν (1) RPS < βαση ΚΑΙ καλυτερο σε ≥3/4 σεζον, (2) picks md15+ (κανονες live, closing) ROI ΚΑΙ μοναδες οχι χειροτερα.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'hfa'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, probs, rps, bets = g['D'], g['probs'], g['rps'], g['bets']
SEAS = sorted(D.season.unique()); s0 = (D.xh - D.xa).values; resid = D.gd.values - s0
V = {'βαση (σημερα)': s0.copy()}
hA = np.zeros(len(D)); hB = np.zeros(len(D)); info = []
for s_ in SEAS:
    te = (D.season == s_).values; tr = ~te
    hA[te] = resid[tr].mean()
    for lg in D.league.unique():
        m = te & (D.league == lg).values; mt = tr & (D.league == lg).values
        hB[m] = resid[mt].mean()
    info.append(f'{s_}: ενιαιο {resid[tr].mean():+.3f}')
V['(Α) ενιαιο h LOSO'] = s0 + hA
V['(Β) h ανα λιγκα LOSO'] = s0 + hB
for h in (0.03, 0.06, 0.09): V[f'(Γ) h=+{h}'] = s0 + h
print('h LOSO: ' + ' · '.join(info))
print('h ανα λιγκα (ολο το δειγμα): ' + ' · '.join(f'{lg} {resid[(D.league == lg).values].mean():+.3f}' for lg in sorted(D.league.unique())))
y = D.y.values; res = {}
for name, s in V.items():
    pm = probs(s); row = {'ALL': rps(pm, y)}
    for s_ in SEAS: m = (D.season == s_).values; row[s_] = rps(pm[m], y[m])
    for w_ in ('md7-14', 'md15+'):
        bb = bets(s, (D.win == w_).values); pn = np.array([x[0] for x in bb])
        row[f'n_{w_}'] = len(pn); row[f'ROI_{w_}'] = 100 * pn.mean(); row[f'u_{w_}'] = pn.sum()
        if w_ == 'md15+':
            row['σεζον+'] = sum(np.mean([x[0] for x in bb if x[1] == s_]) > 0 for s_ in SEAS)
    res[name] = row
T = pd.DataFrame(res).T; pd.set_option('display.width', 250)
print(T[['ALL'] + SEAS].round(5).to_string()); print(T[['n_md7-14', 'ROI_md7-14', 'u_md7-14', 'n_md15+', 'ROI_md15+', 'u_md15+', 'σεζον+']].round(2).to_string())
b = res['βαση (σημερα)']
for name in ('(Α) ενιαιο h LOSO', '(Β) h ανα λιγκα LOSO'):
    r = res[name]; w = sum(r[s_] < b[s_] for s_ in SEAS)
    c1 = r['ALL'] < b['ALL'] and w >= 3; c2 = r['ROI_md15+'] >= b['ROI_md15+'] and r['u_md15+'] >= b['u_md15+']
    print(f'ΚΡΙΣΗ {name}: RPS {r["ALL"]:.5f} vs {b["ALL"]:.5f} ({w}/4) {"✓" if c1 else "✗"} · picks md15+ {r["ROI_md15+"]:+.1f}%/{r["u_md15+"]:+.1f}u vs {b["ROI_md15+"]:+.1f}%/{b["u_md15+"]:+.1f}u {"✓" if c2 else "✗"} → {"ΠΕΡΝΑ" if c1 and c2 else "ΔΕΝ ΠΕΡΝΑ"}')
