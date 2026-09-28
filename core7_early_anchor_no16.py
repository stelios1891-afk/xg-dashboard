"""
core7_early_anchor_no16.py — 28/9/2026 (Στελιος: «δεν παιζουμε τα πρωτα 6 — να μην τα μετρησουμε σαν αγκυρα»).
Ιδιο με core7_early_anchor_all.py αλλα οι διορθωσεις ΔΕΝ ενημερωνονται απο ματς των αγωνιστικων 1-6 (md 0-5)· μεταφορα σεζον c=1·
εφαρμογη & μετρηση ΜΟΝΟ στις αγωνιστικες 7-14 (md 6-13). Ιδιο κριτηριο: RPS < live σε ≥3/4 σεζον ΚΑΙ picks ROI > live ΚΑΙ μοναδες ≥ live.
Συγκριση και με την εκδοχη «με τα 1-6».
"""
import sys, io, os, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
os.environ['CORE7_PREDS'] = 'europe_test_preds_all.csv'
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
g = {'__name__': 'no16'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
D, probs, rps, bets = g['D'], g['probs'], g['rps'], g['bets']
SEAS = sorted(D.season.unique()); y = D.y.values; md = D.md.values; E = (md >= 6) & (md <= 13)

def run_mask(lam, upd_ok):
    s_adj = np.zeros(len(D))
    for lg, idx in D.groupby('league').groups.items():
        off = {}
        for i in idx:
            r = D.loc[i]
            s = (r.xh - r.xa) + off.get(r.h, 0.0) - off.get(r.a, 0.0); s_adj[i] = s
            if upd_ok[i] and r.s_mkt == r.s_mkt:
                e = r.s_mkt - s; off[r.h] = off.get(r.h, 0.0) + lam * e / 2; off[r.a] = off.get(r.a, 0.0) - lam * e / 2
    return s_adj
s0 = (D.xh - D.xa).values
V = {'live': s0}
for lam in (0.3, 0.5, 0.7):
    for lab, ok in (('χωρις 1-6', md >= 6), ('με 1-6', np.ones(len(D), bool))):
        sa = run_mask(lam, ok); s = s0.copy(); s[E] = sa[E]; V[f'λ={lam} {lab}'] = s
rows = {}
for k, s in V.items():
    pm = probs(s); row = {s_: rps(pm[E & (D.season == s_).values], y[E & (D.season == s_).values]) for s_ in SEAS}
    row['ΟΛΑ'] = rps(pm[E], y[E])
    bb = bets(s, E); pn = np.array([x[0] for x in bb]); row['n'] = len(pn); row['ROI'] = 100 * pn.mean(); row['u'] = pn.sum()
    for s_ in SEAS:
        q = [x[0] for x in bb if x[1] == s_]; row[f'ROI_{s_}'] = 100 * np.mean(q) if q else np.nan
    rows[k] = row
T = pd.DataFrame(rows).T; pd.set_option('display.width', 250)
print('ΑΓΩΝΙΣΤΙΚΕΣ 7-14 (md 6-13)'); print(T.round(4).to_string())
for lab in ('χωρις 1-6', 'με 1-6'):
    ks = [k for k in V if k.endswith(lab)]
    sel = []
    for s_ in SEAS:
        oth = [x for x in SEAS if x != s_]; b = min(ks, key=lambda k: np.mean([rows[k][x] for x in oth])); sel.append((b, rows[b][s_], rows['live'][s_]))
    wins = sum(a < l for _, a, l in sel); best = min(ks, key=lambda k: rows[k]['ΟΛΑ']); b = rows[best]; L = rows['live']
    c1 = np.mean([a for _, a, _ in sel]) < np.mean([l for *_, l in sel]) and wins >= 3; c2 = b['ROI'] > L['ROI'] and b['u'] >= L['u']
    print(f"ΚΡΙΣΗ [{lab}]: RPS LOSO {np.mean([a for _, a, _ in sel]):.5f} vs live {np.mean([l for *_, l in sel]):.5f} ({wins}/4) {'✓' if c1 else '✗'} · "
          f"{best}: picks {b['ROI']:+.1f}% / {b['u']:+.1f}u (n{int(b['n'])}) vs live {L['ROI']:+.1f}% / {L['u']:+.1f}u (n{int(L['n'])}) {'✓' if c2 else '✗'} → {'ΠΕΡΝΑ' if c1 and c2 else 'ΔΕΝ ΠΕΡΝΑ'}")
