# -*- coding: utf-8 -*-
"""t100_open_report_coverage.py — ΤΙ ΗΞΕΡΑΜΕ ΓΙΑ ΤΙΣ ΑΠΟΥΣΙΕΣ ΣΤΟ ΑΝΟΙΓΜΑ (25/10/2026, Στελιος: «παιζουμε στο ανοιγμα και ισως δεν
εχουμε τις αναφορες»). Περιγραφικο: για καθε ματς (Crown, 5 σεζον) συγκρινει την ΕΠΙΣΗΜΗ αναφορα που υπηρχε στο ανοιγμα (ιδια λογικη με
t22/t35/t97) με αυτη στο Τ−30′: ωρα ανοιγματος (Ελλαδα), ηλικια αναφορας, ποσο απο το τελικο «κοστος Out» ηταν ηδη γνωστο, αιφνιδια Out.
Εξοδος: t100_open_report_coverage_out.txt"""
import os, sys, io, contextlib, datetime as dt
from zoneinfo import ZoneInfo
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']; SER, SHIFT, G, dD, SEAS_G = g['SER'], g['SHIFT'], g['G'], g['dD'], g['SEAS_G']
REP_BY, abs_cost, W_A, status_at, REP_SEASONS = g['REP_BY'], g['abs_cost'], g['W_A'], g['status_at'], g['REP_SEASONS']
ATH = ZoneInfo('Europe/Athens'); rec = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in REP_SEASONS: continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    t0 = rows[0][0]; t1 = tip - 1800; h, a, d = G.home.values[i], G.away.values[i], dD[i]
    if t0 >= t1: continue
    for t in (h, a):
        same = [ep for ep, _, _ in REP_BY.get((t, d), ()) if ep <= t0]
        c0, d0 = abs_cost(t, d, s, t0, W_A); c1, d1 = abs_cost(t, d, s, t1, W_A)
        k0 = {k for k, _, _ in d0}; new = [x for x in d1 if x[0] not in k0]; gone = [x for x in d0 if x[0] not in {k for k, _, _ in d1}]
        rec.append(dict(sea=s, hr=dt.datetime.fromtimestamp(t0, ATH).hour, hrs=(tip - t0) / 3600, has=bool(same), age=(t0 - max(same)) / 3600 if same else np.nan,
                        c0=c0, c1=c1, nnew=len(new), cnew=sum(x[2] for x in new), ngone=len(gone), big=any(x[2] >= 1.5 for x in new)))
D = pd.DataFrame(rec); out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'ομαδες-ματς {len(D)} (2 ανα ματς) · σεζον {sorted(D.sea.unique())}')
P(f'ωρα ανοιγματος Crown (Ελλαδα): ' + ' · '.join(f'{k:02d}:00 {v:.0%}' for k, v in D.hr.value_counts(normalize=True).sort_index().items() if v >= .03))
P(f'ανοιγμα κατα μεσο ορο {D.hrs.mean():.1f}ω πριν το τζαμπολ (διαμεσος {D.hrs.median():.1f}ω)')
P(f'υπηρχε ΗΔΗ επισημη αναφορα για ΑΥΤΟ το ματς στο ανοιγμα: {D.has.mean():.0%} · ηλικια της (διαμεσος) {D.age.median():.1f}ω')
for s, x in D.groupby('sea'): P(f'   {s}: αναφορα στο ανοιγμα {x.has.mean():.0%} · ηλικια {x.age.median():.1f}ω · ανοιγμα {x.hrs.median():.1f}ω πριν')
P(f'\nΚΟΣΤΟΣ OUT (ποντοι χαντικαπ, μονο ≥20′): μεσο στο ανοιγμα {D.c0.mean():.2f} · στο Τ−30′ {D.c1.mean():.2f} → γνωστο στο ανοιγμα {D.c0.sum() / D.c1.sum():.0%}')
P(f'ομαδες-ματς με ΝΕΟ Out (≥20′) μετα το ανοιγμα: {(D.nnew > 0).mean():.1%} · μεσο κοστος τους {D[D.nnew > 0].cnew.mean():.2f}π · «μεγαλο» (≥1.5π) {D.big.mean():.1%}')
P(f'ομαδες-ματς οπου Out του ανοιγματος τελικα ΔΕΝ ηταν Out: {(D.ngone > 0).mean():.1%}')
for hs, x in D.groupby(D.has): P(f'   {"με αναφορα" if hs else "ΧΩΡΙΣ αναφορα"} στο ανοιγμα ({len(x)}): γνωστο {x.c0.sum() / max(x.c1.sum(), 1e-9):.0%} · νεο Out {(x.nnew > 0).mean():.1%} · μεγαλο {x.big.mean():.1%}')
open(os.path.join(SC, 't100_open_report_coverage_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
