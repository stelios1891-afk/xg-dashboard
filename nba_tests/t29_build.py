# -*- coding: utf-8 -*-
"""t29_build.py — ΒΑΣΗ ΓΙΑ ΙΑΝΟΥΑΡΙΟ-ΦΕΒΡΟΥΑΡΙΟ (21/10/2026): ΟΛΑ τα ματς κανονικης περιοδου (5 σεζον με επισημες αναφορες) σε 2 στιγμες
(ανοιγμα · Τ−30′): προβλεψη αντιγραφου live (t22: χωρις «εχασε 2», απουσιες απο την τελευταια αναφορα ≤ τ, μονο Out) + τιμη Crown + κλεισιμο.
Εξοδος: nba_tests/_t29_games.csv"""
import os, sys, io, contextlib, pickle
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g22 = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g22)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g22['np'], __import__('pandas')
G, SEAS_G, dD, EV, ACT, VNO, SER, SHIFT = (g22[k] for k in ('G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT'))
W_A, abs_cost, line_at, REP_SEASONS = g22['W_A'], g22['abs_cost'], g22['line_at'], g22['REP_SEASONS']
GN = np.asarray(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['GN'])
rows = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rr = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rr = [x for x in rr if x[0] <= tip + 900]
    if not rr: continue
    close = line_at(rr, tip, sw); h, a, d = G.home.values[i], G.away.values[i], dD[i]
    for lab, tau in (('ανοιγμα', rr[0][0]), ('Τ−30′', max(tip - 1800, rr[0][0]))):
        ln = line_at(rr, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        ch, _ = abs_cost(h, d, s, tau, W_A); ca, _ = abs_cost(a, d, s, tau, W_A)
        rows.append(dict(i=i, sea=s, date=str(d), mon=int(G.date.dt.month.values[i]), gn=int(GN[i]), tau=lab, home=h, away=a,
                         m=VNO[i] - ch + ca, m0=VNO[i], abs_h=ch, abs_a=ca, L=L, oh=oh, oa=oa, fair=fair, cfair=close[3], act=ACT[i]))
pd.DataFrame(rows).to_csv(os.path.join(SC, '_t29_games.csv'), index=False)
print('γραμμες', len(rows))
