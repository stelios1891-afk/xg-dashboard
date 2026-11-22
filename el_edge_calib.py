# -*- coding: utf-8 -*-
"""el_edge_calib.py — ΒΑΘΜΟΝΟΜΗΣΗ EDGE & ΠΟΝΤΑΡΙΣΜΑ Ευρωλιγκας (1/10/2026, Στελιος «τρεξε το 3»).
Picks = ιδια προσομοιωση alert με el_alert_types (Crown, πρωτη τιμη με edge ≥8%, live μοντελο), ΧΩΡΙΣ τις καταγραφες
(χαντικαπ τελευταιου 2ωρου · συνολα μετα απο κοντρα ≥1.5π). 5 σεζον E2021-E2025.
1. ROI & ποσοστο επιτυχιας ανα κλιμακιο edge: προβλεπομενη πιθανοτητα μοντελου vs πραγματικη (βαθμονομηση).
2. Ποντarisma: σταθερο 1 μοναδα · αναλογο του edge (μεσος ορος 1) · ¼ Kelly (μεσος ορος 1) — ROI, μοναδες, χειροτερη βυθιση, ανα σεζον.
Εξοδος: el_edge_calib_out.txt"""
import sys
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, pick, settle, at, D, SE5, SM, ST = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'at', 'D', 'SE5', 'SM', 'ST'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
def prob(t, m, row, side):
    _, _, L, o1, o2 = row; sg = SM if t == 21 else ST; thr = -L if t == 21 else L
    if abs(L - round(L)) < 1e-9:
        pw = 1 - NormalDist(m, sg).cdf(thr + 0.5); pl = NormalDist(m, sg).cdf(thr - 0.5)
    else:
        pw = 1 - NormalDist(m, sg).cdf(thr); pl = 1 - pw
    return (pw, 1 - pw - pl) if side == 1 else (pl, 1 - pw - pl)
rows = []
for t in (21, 23):
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(('h_' if t == 21 else 't_') + 'new')
        if m is None or not np.isfinite(m): continue
        ser, tip = r['ser'], r['tip']; o = ser[0]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(t, m, row)
            if e < 0.08: continue
            hrs = (tip - row[0]) / 3600; mv = -(row[1] - o[1]) * side
            if k_ > 0 and ((t == 21 and hrs < 2) or (t == 23 and mv >= 1.5)): break      # καταγραφες
            pw, pp = prob(t, m, row, side)
            L = row[2]; v = ((NS['ACT'][p] + L) if t == 21 else (NS['TOT'][p] - L)) * side
            rows.append(dict(mkt='χαντικαπ' if t == 21 else 'συνολα', sea=D.season.values[p], t=tip, edge=e, od=od, pw=pw, pp=pp,
                             win=float(v > 0), push=float(v == 0), pnl=settle(t, p, side, row, od)))
            break
Z = pd.DataFrame(rows).sort_values('t')
P(f'{len(Z)} picks (χωρις καταγραφες): χαντικαπ {sum(Z.mkt == "χαντικαπ")} · συνολα {sum(Z.mkt == "συνολα")}')
P(''); P('=== 1. ΑΝΑ ΚΛΙΜΑΚΙΟ EDGE: ROI, επιτυχια πραγματικη vs μοντελου vs αγορας (1/αποδοση) ===')
B = ((0.08, 0.10), (0.10, 0.12), (0.12, 0.15), (0.15, 0.20), (0.20, 0.30), (0.30, 9))
for mk in ('χαντικαπ', 'συνολα', 'ΟΛΑ'):
    z0 = Z if mk == 'ΟΛΑ' else Z[Z.mkt == mk]
    P(f'  {mk}:')
    for lo, hi in B:
        z = z0[(z0.edge >= lo) & (z0.edge < hi)]
        if len(z) == 0: continue
        pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0)
        nd = z[z.push == 0]
        P(f'    edge {lo*100:3.0f}-{"+" if hi > 1 else f"{hi*100:.0f}"}%: n {len(z):4d} · ROI {z.pnl.mean()*100:+6.1f}% ({pos}/5) · επιτυχια {nd.win.mean():.1%} · '
          f'μοντελο {(nd.pw / (1 - nd.pp)).mean():.1%} · αγορα(1/απ) {(1 / nd.od).mean():.1%} · μεση αποδοση {z.od.mean():.2f}')
    b = np.polyfit(z0.edge, z0.pnl, 1)
    P(f'    κλιση ROI πανω στο edge: {b[0]:+.2f} (1 = ο δηλωμενος edge «βγαινει» ολοκληρος· 0 = ανεξαρτητο απο το edge)')
P(''); P('=== 2. ΠΟΝΤΑΡΙΣΜΑ (ιδια picks, χρονολογικα· καθε τροπος κανονικοποιημενος σε μεσο ποντο 1 μοναδα) ===')
def kelly(z): return np.clip(z.edge / (z.od - 1), 0, None)
for mk in ('χαντικαπ', 'συνολα', 'ΟΛΑ'):
    z = Z if mk == 'ΟΛΑ' else Z[Z.mkt == mk]
    P(f'  {mk} ({len(z)} picks):')
    for nm, w in (('σταθερο 1 μον.', np.ones(len(z))), ('αναλογο του edge', z.edge.values), ('¼ Kelly', kelly(z).values)):
        w = w / w.mean(); pnl = w * z.pnl.values; cum = np.cumsum(pnl); dd = np.max(np.maximum.accumulate(cum) - cum)
        per = ' '.join(f'{s[-2:]}:{pnl[z.sea.values == s].sum() / w[z.sea.values == s].sum() * 100:+.1f}' for s in SE5)
        sh = pnl.mean() / pnl.std() * np.sqrt(len(pnl))
        P(f'    {nm:18s} ROI {pnl.sum() / w.sum() * 100:+5.1f}% · μοναδες {pnl.sum():+6.1f} · χειροτερη βυθιση {dd:5.1f} μον. · t {sh:+.1f} · [{per}]')
open('el_edge_calib_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
