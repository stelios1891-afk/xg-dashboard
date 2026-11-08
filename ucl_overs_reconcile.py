"""ucl_overs_reconcile.py — 10/10/2026 (Στελιος: «απο που προκυπτει οτι τα over δεν βγαζουν; ξεραμε οτι βγαζουν — ψαξτο»).
Συμφιλιωση: παλιο ucl_final_summary (11/9: overs@4 +11.9%, n=123) vs σημερινο euro_totals_test (−2.9%).
Διαφορες που ελεγχονται ΜΙΑ-ΜΙΑ: (α) σεζον: νεα μορφη 2425-2526 vs ολες · (β) βιβλιο: Crown vs SBOBET · (γ) ζευγος προβλεψης:
ΚΥΡΙΟ (το ιδιο με το χαντικαπ, πεναλτι 0.25, με γ+κ — αυτο ειχε το παλιο τεστ) vs ΜΗΧΑΝΗ ΓΚΟΛ W2 (πεναλτι 0.76 + κ, αυτο που τρεχει live)."""
import sys, io, contextlib
import euro_shadow_scan  # προφορτωση εκτος redirect (κανει reconfigure stdout)
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_totals_test.py', encoding='utf-8').read()
src = src[:src.index('HS = (72, 60')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'rc'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
u = g['u']; LHm, LAm = np.asarray(u['LH_N']), np.asarray(u['LA_N'])           # κυριο ζευγος (live χαντικαπ)
OH, OA, MIDS, FM, SEA, ucl, GH, GA, ES, snap_ou, settle, picks = (g[k] for k in ('OH', 'OA', 'MIDS', 'FM', 'SEA', 'ucl', 'GH', 'GA', 'ES', 'snap_ou', 'settle', 'picks'))
rows = []
for i, mid in enumerate(MIDS):
    if not FM[i] or not ucl[i]: continue
    for lab, (lh, la) in (('ΚΥΡΙΟ (παλιο τεστ)', (LHm[i], LAm[i])), ('W2 (live overs)', (OH[i], OA[i]))):
        td = ES.tot_dist(lh, la)
        for bk in ('Crown', 'SBOBET'):
            s = snap_ou(mid, bk, 0)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            e = po * (o - 1) * (1 - picks.MARGIN) - pu
            rows.append(dict(eng=lab, bk=bk, sea=SEA[i], e=e, inz=1.70 <= o <= 2.10, model=lh + la, L=L, pnl=settle(GH[i] + GA[i], L, o, True)))
R = pd.DataFrame(rows)
def c(x):
    if len(x) == 0: return '—'
    ps = x.groupby('sea').pnl.mean()
    return f'n{len(x):4d} {100 * x.pnl.mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size} σεζον: ' + ' '.join(f'{s} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print('OVER @4% ΣΤΟ ΚΛΕΙΣΙΜΟ, Champions League, ζωνη 1.70-2.10')
for eng in ('ΚΥΡΙΟ (παλιο τεστ)', 'W2 (live overs)'):
    print(f'\n== {eng} ==  (μεσο συνολο μοντελου {R[(R.eng == eng) & (R.bk == "Crown")].model.mean():.2f})')
    for bk in ('Crown', 'SBOBET'):
        for sl, ss in (('νεα μορφη 2425-26', ('2425', '2526')), ('παλια μορφη 2223-24', ('2223', '2324')), ('ολες', ('2223', '2324', '2425', '2526'))):
            x = R[(R.eng == eng) & (R.bk == bk) & R.sea.isin(ss) & R.inz & (R.e >= .04)]
            print(f'   {bk:7s} {sl:20s} {c(x)}')

# ---- ροη πρωτης εμφανισης (απο euro_totals_test) ανα μορφη ----
F = pd.read_pickle('euro_totals_first.pkl')
print(chr(10) + 'ΡΟΗ «πρωτη εμφανιση ≤72ω» @4% (μεσος Crown/SBOBET) ανα μορφη')
for side in ('over', 'under'):
    for fmt, ss in (('νεα μορφη 2425-26', ('2425', '2526')), ('παλια 2223-24', ('2223', '2324'))):
        x = F[(F.side == side) & F.sea.isin(ss)]; m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
        late = x[x.h <= 8]; early = x[x.h >= 48]
        print(f'   {side.upper():5s} {fmt:18s} n{m["size"].mean():.0f} {100 * m["mean"].mean():+.1f}% (' + ' '.join(f'{s_} {100 * v:+.0f}' for s_, v in ps.items()) +
              f') · βγηκαν 72-48ω {100 * early.pnl.mean():+.1f}% (n{len(early) / 2:.0f}) · βγηκαν ≤8ω {100 * late.pnl.mean():+.1f}% (n{len(late) / 2:.0f})')
