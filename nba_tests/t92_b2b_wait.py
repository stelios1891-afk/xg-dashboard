# -*- coding: utf-8 -*-
"""t92_b2b_wait.py — ΟΤΑΝ Η ΔΙΚΗ ΜΑΣ ΟΜΑΔΑ ΠΑΙΖΕΙ 2ο ΜΑΤΣ B2B: ΝΑ ΠΕΡΙΜΕΝΟΥΜΕ; (25/10/2026, Στελιος «ισως σε αυτα υπαρχει αξια να περιμενουμε»).
ΠΕΡΙΓΡΑΦΙΚΟ. Πλαισιο t22/t84 (αντιγραφο live: τιμη Crown + τελευταια επισημη αναφορα ιδια στιγμη, πιθανοτητες καταστασης οπως το live).
Picks edge ≥8% σε 4 στιγμες: ανοιγμα · Τ−6ω · Τ−2ω · Τ−30′. Χωριζονται απο την πλευρα του pick: ΕΜΕΙΣ σε 2ο B2B / ΑΝΤΙΠΑΛΟΣ / ΚΑΙ ΟΙ ΔΥΟ / ΚΑΝΕΙΣ,
και (για τις ομαδες σε B2B) αν η ομαδα ΜΑΣ ειχε ηδη δηλωσει στην αναφορα τη στιγμη του pick.
Μετρα: ROI στην τιμη της στιγμης, μοναδες, CLV (κινηση ως το κλεισιμο), θετικες σεζον. Εξοδος: nba_tests/t92_b2b_wait_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't84_b2b_rest_expected.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα', None)")[0]
g = {'__file__': os.path.join(SC, 't84_b2b_rest_expected.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']
SER, SHIFT, SEAS_G, EV, REP_SEASONS, VNO, G, dD, ACT = (g[x] for x in ('SER', 'SHIFT', 'SEAS_G', 'EV', 'REP_SEASONS', 'VNO', 'G', 'dD', 'ACT'))
cost, b2b, submitted, line_at, cover_, SIG_ = g['cost'], g['b2b'], g['submitted'], g['line_at'], g['cover_'], g['SIG_']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
TAUS = (('ανοιγμα', None), ('Τ−6ω', 6), ('Τ−2ω', 2), ('Τ−30′', 0.5))
R = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    close = line_at(rows, tip, sw)
    for lab, hrs in TAUS:
        tau = rows[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rows[0][0]: continue
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        m = VNO[i] - cost(h, d, s, tau, 'Α') + cost(a, d, s, tau, 'Α')
        pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
        sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
        if e < .08: continue
        me, op = (h, a) if sd == 1 else (a, h)
        bm, bo = b2b(me, d), b2b(op, d)
        cat = 'ΕΜΕΙΣ σε B2B' if bm and not bo else ('ΑΝΤΙΠΑΛΟΣ σε B2B' if bo and not bm else ('ΚΑΙ ΟΙ ΔΥΟ' if bm and bo else 'ΚΑΝΕΙΣ'))
        x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        R.append(dict(sea=s, tau=lab, cat=cat, res=res, clv=sd * (close[3] - fair), subm=submitted(me, d, tau), mon=int(G.date.dt.month.values[i])))
X = pd.DataFrame(R)
def cell(d):
    if len(d) < 5: return f'— ({len(d)})'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π'
for per, M in (('ΟΛΗ Η ΣΕΖΟΝ', X.mon > 0), ('ΟΚΤ-ΔΕΚ', X.mon.isin([10, 11, 12]))):
    P(f'\n=== {per} · picks edge ≥8% στην τιμη της στιγμης ===')
    P(f'{"κατηγορια":18s} | ' + ' | '.join(f'{t:44s}' for t, _ in TAUS))
    for c in ('ΚΑΝΕΙΣ', 'ΕΜΕΙΣ σε B2B', 'ΑΝΤΙΠΑΛΟΣ σε B2B', 'ΚΑΙ ΟΙ ΔΥΟ'):
        P(f'{c:18s} | ' + ' | '.join(f'{cell(X[M & (X.cat == c) & (X.tau == t)]):44s}' for t, _ in TAUS))
    P('  -- ΕΜΕΙΣ σε B2B (μονοι ή και οι δυο), χωρισμενα: η ομαδα μας ΕΙΧΕ δηλωσει τη στιγμη του pick / ΔΕΝ ειχε --')
    mm = M & X.cat.isin(['ΕΜΕΙΣ σε B2B', 'ΚΑΙ ΟΙ ΔΥΟ'])
    for t, _ in TAUS:
        P(f'     {t:8s} ειχε δηλωσει: {cell(X[mm & (X.tau == t) & X.subm]):44s} · δεν ειχε: {cell(X[mm & (X.tau == t) & ~X.subm])}')
open(os.path.join(SC, 't92_b2b_wait_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
