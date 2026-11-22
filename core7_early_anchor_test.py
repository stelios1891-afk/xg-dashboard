"""
core7_early_anchor_test.py — ΤΕΣΤ 28/9/2026 (Στελιος: «βελτιωση μεχρι την 14η»). ΑΓΚΥΡΑ ΜΟΝΟ ΣΤΙΣ md7-14.
Διορθωσεις ομαδων μαθαινονται απο ΟΛΑ τα ματς (closing AH) και ΜΕΤΑΦΕΡΟΝΤΑΙ στη νεα σεζον (c=1)· εφαρμοζονται ΜΟΝΟ στις md≤14·
md15+ = live αμεταβλητο (η τσεπη δεν αγγιζεται).
ΠΡΟ-ΔΗΛΩΣΗ: λ ∈ {0.3, 0.5, 0.7}, επιλογη LOSO (fold = σεζον) στο RPS των md7-14. ΠΕΡΝΑ αν (1) RPS md7-14 < live ΚΑΙ ≥3/4 σεζον,
(2) picks md7-14 (κανονες live, closing) ROI > live ΚΑΙ μοναδες ≥ live. Πληροφοριακα: κλιση b στις md7-14, ανα λιγκα.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
g = {'__name__': 'early'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
D, run, probs, rps, bets, picks = g['D'], g['run'], g['probs'], g['rps'], g['bets'], g['picks']
SEAS = sorted(D.season.unique()); E = (D.win == 'md7-14').values; y = D.y.values
s0 = (D.xh - D.xa).values
def early(lam):
    sa = run(lam, 1); s = s0.copy(); s[D.md.values <= 14] = sa[D.md.values <= 14]; return s
V = {'live': s0}
for lam in (0.3, 0.5, 0.7): V[f'λ={lam}'] = early(lam)
res = {}
for k, s in V.items():
    pm = probs(s); row = {}
    for s_ in SEAS:
        m = E & (D.season == s_).values; row[s_] = rps(pm[m], y[m])
    row['md7-14'] = rps(pm[E], y[E])
    mk = E & D.s_mkt.notna().values
    A = np.column_stack([np.ones(mk.sum()), D.s_mkt[mk], s[mk] - D.s_mkt[mk]]); row['b'] = np.linalg.lstsq(A, D.gd[mk].astype(float), rcond=None)[0][2]
    bb = bets(s, E); pn = np.array([x[0] for x in bb]); row['n'] = len(pn); row['ROI'] = 100 * pn.mean(); row['u'] = pn.sum()
    row['σεζον+'] = sum(np.mean([x[0] for x in bb if x[1] == s_]) > 0 for s_ in SEAS if any(x[1] == s_ for x in bb))
    for s_ in SEAS: row[f'ROI_{s_}'] = 100 * np.mean([x[0] for x in bb if x[1] == s_]) if any(x[1] == s_ for x in bb) else np.nan
    res[k] = row
T = pd.DataFrame(res).T; pd.set_option('display.width', 250)
print('md7-14 ΜΟΝΟ (md15+ αμεταβλητο):'); print(T.round(4).to_string())
sel = []
for s_ in SEAS:
    oth = [x for x in SEAS if x != s_]; best = min([k for k in V if k != 'live'], key=lambda k: np.mean([res[k][x] for x in oth]))
    sel.append((s_, best, res[best][s_], res['live'][s_]))
print('LOSO: ' + ' · '.join(f'{s_}: {b} {a:.5f} vs live {l:.5f}' for s_, b, a, l in sel))
wins = sum(a < l for _, _, a, l in sel); c1 = np.mean([a for *_, a, _ in sel]) < np.mean([l for *_, l in sel]) and wins >= 3
best = max([k for k in V if k != 'live'], key=lambda k: -np.mean([res[k][x] for x in SEAS])); b = res[best]; L = res['live']
c2 = b['ROI'] > L['ROI'] and b['u'] >= L['u']
print(f"ΚΡΙΣΗ: (1) RPS md7-14 LOSO {np.mean([a for *_, a, _ in sel]):.5f} vs {np.mean([l for *_, l in sel]):.5f} ({wins}/4) {'✓' if c1 else '✗'} · "
      f"(2) {best}: picks {b['ROI']:+.1f}% / {b['u']:+.1f}u (n{int(b['n'])}) vs live {L['ROI']:+.1f}% / {L['u']:+.1f}u (n{int(L['n'])}) {'✓' if c2 else '✗'} → {'ΠΕΡΝΑ' if c1 and c2 else 'ΔΕΝ ΠΕΡΝΑ'}")
