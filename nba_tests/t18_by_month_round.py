# -*- coding: utf-8 -*-
"""t18_by_month_round.py — ΑΠΟΔΟΣΗ ΤΟΥ LIVE ΜΟΝΤΕΛΟΥ ΑΝΑ ΜΗΝΑ ΚΑΙ ΑΝΑ ΑΓΩΝΙΣΤΙΚΗ (20/10/2026, Στελιος).
Μοντελο = οπως το live σημερα: production + B2B 3 + απουσιες (γνωστες, αντικ. −2) + μεταγραφες (α 1.0, αντικ. −2, χωρις σβησιμο).
(Η αλλαγη ζωνης ωρας και το carry ανα ομαδα δεν ειναι μεσα — μικρη επιδραση, βλ. t3b/t4.)
Picks = edge ≥8% στη γραμμη ΑΝΟΙΓΜΑΤΟΣ (Crown). Αγωνιστικη = αγωνας Ν της ομαδας με τα περισσοτερα ματς (οπως το live «gno»).
Ανα κελι: picks, ROI, μοναδες, θετικες σεζον · λαθος μοντελου vs λαθος κλεισιματος. Εξοδος: t18_by_month_round_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE = ns['BASE']; MKH = ns['MKH']
inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']
V = BASE + ns['adj'](1.0, -2.0, None)
MON = G.date.dt.month.values
GNO = np.zeros(len(G), int); cnt = collections.Counter()
for i in np.argsort(dD, kind='stable'):
    s, h, a = SEAS_G[i], G.home.values[i], G.away.values[i]
    GNO[i] = max(cnt[(s, h)], cnt[(s, a)]) + 1; cnt[(s, h)] += 1; cnt[(s, a)] += 1
P_ = []
for i, d in MKH.items():
    if SEAS_G[i] not in EV or not np.isfinite(V[i]): continue
    L, mk, o1, o2 = d['o']; pw, pp, pl = cover_(V[i], L, SIG_)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    cl = d['c'][1]
    rec = dict(i=i, sea=SEAS_G[i], mon=MON[i], gno=GNO[i], em=(ACT[i] - V[i]) ** 2, ec=(ACT[i] - cl) ** 2, pick=e >= .08)
    if e >= .08:
        x = (ACT[i] + L) * s_; rec['res'] = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        rec['fav'] = (L * s_) < 0
    P_.append(rec)
import pandas as pd
X = pd.DataFrame(P_)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def row(lab, d):
    pk = d[d.pick]
    ps = pk.groupby('sea').res.sum()
    fav = pk[pk.fav == True]; dog = pk[pk.fav == False]
    P(f'  {lab:14s} {len(d):5d} ματς · λαθος μοντελο {np.sqrt(d.em.mean()):5.2f} vs κλεισιμο {np.sqrt(d.ec.mean()):5.2f} · '
      f'picks {len(pk):4d} · ROI {100 * pk.res.mean() if len(pk) else 0:+6.1f}% ({pk.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{pk.sea.nunique()}) · '
      f'φαβ {100 * fav.res.mean() if len(fav) else 0:+5.1f}% ({len(fav)}) · αουτσ {100 * dog.res.mean() if len(dog) else 0:+5.1f}% ({len(dog)})')
P('NBA · ΑΠΟΔΟΣΗ LIVE ΜΟΝΤΕΛΟΥ ανα ΜΗΝΑ και ανα ΑΓΩΝΙΣΤΙΚΗ · 5 σεζον (2021-22…2025-26) · picks = edge ≥8% στο ανοιγμα (Crown)')
P(''); P('=== ΑΝΑ ΜΗΝΑ ===')
for m, lab in ((10, 'Οκτωβριος'), (11, 'Νοεμβριος'), (12, 'Δεκεμβριος'), (1, 'Ιανουαριος'), (2, 'Φεβρουαριος'), (3, 'Μαρτιος'), (4, 'Απριλιος')):
    d = X[X.mon == m]
    if len(d): row(lab, d)
P(''); P('=== ΑΝΑ ΑΓΩΝΙΣΤΙΚΗ (αγωνας της ομαδας) ===')
for lo, hi in ((1, 5), (6, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 82)):
    d = X[(X.gno >= lo) & (X.gno <= hi)]
    if len(d): row(f'{lo}-{hi}' + (' (εκτος live)' if lo == 71 else ''), d)
P(''); P('=== ΑΝΑ ΣΕΖΟΝ (ως τον 70ο αγωνα, οπως το live) ===')
for Y in EV:
    d = X[(X.sea == Y) & (X.gno <= 70)]; row(f'{Y - 1}-{str(Y)[2:]}', d)
row('ΣΥΝΟΛΟ ≤70', X[X.gno <= 70])
open(os.path.join(SC, 't18_by_month_round_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
