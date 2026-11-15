"""
core7_early_anchor_all.py — 28/9/2026 (Στελιος: «τρεξε και τις πρωτες 6 αγωνιστικες»). Ιδια αγκυρα με core7_early_anchor_test.py
αλλα με ΟΛΕΣ τις αγωνιστικες (europe_test_preds_all.csv, md = ματς που εχουν παιξει και οι δυο: md 0-5 = αγωνιστικες 1-6, md 6-13 = 7-14).
Οι διορθωσεις μαθαινονται απο ΟΛΑ τα ματς (και 1-6), μεταφερονται στη νεα σεζον (c=1), εφαρμοζονται ΜΟΝΟ στις αγωνιστικες 1-14.
ΠΡΟ-ΔΗΛΩΣΗ (ανα παραθυρο 1-6 και 7-14 χωριστα): λ LOSO στο RPS· ΠΕΡΝΑ αν RPS < live σε ≥3/4 σεζον ΚΑΙ picks (κανονες live, closing)
ROI > live ΚΑΙ μοναδες ≥ live. (Η 1η σεζον 2223 ξεκινα με διορθωσεις 0 — δεν εχουμε 2122.)
"""
import sys, io, os, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
os.environ['CORE7_PREDS'] = 'europe_test_preds_all.csv'
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
g = {'__name__': 'early_all'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
D, run, probs, rps, bets = g['D'], g['run'], g['probs'], g['rps'], g['bets']
SEAS = sorted(D.season.unique()); y = D.y.values; md = D.md.values
print(f'ματς {len(D)} · με closing AH {D.s_mkt.notna().sum()} · αγωνιστικες 1-6: {(md < 6).sum()} · 7-14: {((md >= 6) & (md <= 13)).sum()}')
W = {'αγωνιστικες 1-6': md < 6, 'αγωνιστικες 7-14': (md >= 6) & (md <= 13)}
s0 = (D.xh - D.xa).values
V = {'live': s0}
for lam in (0.3, 0.5, 0.7):
    sa = run(lam, 1); s = s0.copy(); s[md <= 13] = sa[md <= 13]; V[f'λ={lam}'] = s
PM = {k: probs(s) for k, s in V.items()}
for wn, E in W.items():
    rows = {}
    for k, s in V.items():
        pm = PM[k]; row = {s_: rps(pm[E & (D.season == s_).values], y[E & (D.season == s_).values]) for s_ in SEAS}
        row['ΟΛΑ'] = rps(pm[E], y[E])
        bb = bets(s, E); pn = np.array([x[0] for x in bb]); row['n'] = len(pn); row['ROI'] = 100 * pn.mean() if len(pn) else np.nan; row['u'] = pn.sum()
        for s_ in SEAS:
            q = [x[0] for x in bb if x[1] == s_]; row[f'ROI_{s_}'] = 100 * np.mean(q) if q else np.nan
        rows[k] = row
    T = pd.DataFrame(rows).T; pd.set_option('display.width', 250)
    print(f'\n=== {wn} ==='); print(T.round(4).to_string())
    sel = []
    for s_ in SEAS:
        oth = [x for x in SEAS if x != s_]; best = min([k for k in V if k != 'live'], key=lambda k: np.mean([rows[k][x] for x in oth]))
        sel.append((best, rows[best][s_], rows['live'][s_]))
    wins = sum(a < l for _, a, l in sel)
    best = min([k for k in V if k != 'live'], key=lambda k: rows[k]['ΟΛΑ']); b = rows[best]; L = rows['live']
    c1 = np.mean([a for _, a, _ in sel]) < np.mean([l for *_, l in sel]) and wins >= 3
    c2 = b['ROI'] > L['ROI'] and b['u'] >= L['u']
    print(f"  LOSO επιλογες: {[x[0] for x in sel]} · RPS {np.mean([a for _, a, _ in sel]):.5f} vs live {np.mean([l for *_, l in sel]):.5f} ({wins}/4) {'✓' if c1 else '✗'} · "
          f"{best}: picks {b['ROI']:+.1f}% / {b['u']:+.1f}u (n{int(b['n'])}) vs live {L['ROI']:+.1f}% / {L['u']:+.1f}u (n{int(L['n'])}) {'✓' if c2 else '✗'} → {'ΠΕΡΝΑ' if c1 and c2 else 'ΔΕΝ ΠΕΡΝΑ'}")
