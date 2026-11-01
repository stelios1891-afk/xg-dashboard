"""euro_dead_newformat.py — 10/10/2026 (Στελιος: «ασε τις παλιες σεζον — μονο νεο φορματ»).
ΜΟΝΟ 2425/2526 (36 ομαδες, ενιαια βαθμολογια): ειδη «νεκρης» → πραγματικο vs μοντελο / αγορα, τυφλο χαντικαπ, ΤΑ ΔΙΚΑ ΜΑΣ picks,
και διορθωση λ νεκρης με 2-fold (τιμη απο την αλλη σεζον) → ποια picks φευγουν/μπαινουν."""
import sys, io, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'nf'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
R = pd.read_pickle('euro_motivation_seed_rows.pkl'); R = R[R.new].copy()
def typ(r):
    if r.status != 'νεκρη': return 'ζωντανη (κινητρο ≥0.05)'
    p8, p24 = r.probs['8αδα'], r.probs['24αδα']
    if p24['W'] < .05: return 'ΗΔΗ ΑΠΟΚΛΕΙΣΜΕΝΗ'
    if p8['L'] > .95: return 'ΣΙΓΟΥΡΗ ΣΤΗΝ 8ΑΔΑ'
    if p24['L'] > .95 and p8['W'] < .05: return 'ΚΛΕΙΔΩΜΕΝΗ 9-24 (playoff)'
    return 'πρακτικα κλειδωμενη'
R['typ'] = [typ(r) for r in R.itertuples()]
G = g['g']; MIDS = G['MIDS']; IDX = {m: i for i, m in enumerate(MIDS)}
TYP = {(r.mid, r.side): r.typ for r in R.itertuples()}
LATE = set(R.mid)
def picks(L):
    out = []
    for bk, OD in (('Crown', g['CROWN']), ('Pin', g['PIN'])):
        for (mid, side), rr in g['gen'](L, OD).items():
            if mid in LATE:
                out.append(dict(bk=bk, mid=mid, side=side, role=rr['role'], sea=rr['sea'], pnl=rr['pnl'], typ=TYP.get((mid, side)), opp=TYP.get((mid, -side))))
    return pd.DataFrame(out)
P0 = picks(g['BASE'])
def se(x): x = x.dropna(); return x.std() / math.sqrt(len(x)) if len(x) > 1 else np.nan
def pk(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); return f'{m["size"].mean():.0f} picks {100 * m["mean"].mean():+.0f}%'
ORDER = ['ΗΔΗ ΑΠΟΚΛΕΙΣΜΕΝΗ', 'ΚΛΕΙΔΩΜΕΝΗ 9-24 (playoff)', 'ΣΙΓΟΥΡΗ ΣΤΗΝ 8ΑΔΑ', 'πρακτικα κλειδωμενη', 'ζωντανη (κινητρο ≥0.05)']
print('ΝΕΟ ΦΟΡΜΑΤ (2024-25, 2025-26) — τελευταιες 2 αγωνιστικες League Phase (UCL/UEL 7-8, UECL 5-6)')
print(f'{"ειδος":28s} {"n":>4s} | {"xG−μοντ":>9s} {"γκολ−μοντ":>10s} | {"διαφ−μοντ":>10s} {"διαφ−αγορα":>11s} | {"τυφλο υπερ":>10s} | picks μας ΣΕ αυτη · ΚΑΤΑ αυτης')
for t in ORDER:
    x = R[R.typ == t]
    if len(x) == 0: continue
    dm = (x.gf - x.ga) - (x.lf - x.la); dk = (x.gf - x.ga) - x.mkt; v = x[['ah_Crown', 'ah_SBOBET']].stack()
    print(f'{t:28s} {len(x):4d} | {(x.xf - x.lf).mean():+5.2f}±{se(x.xf - x.lf):.2f} {(x.gf - x.lf).mean():+6.2f}±{se(x.gf - x.lf):.2f} | {dm.mean():+6.2f}±{se(dm):.2f} {dk.mean():+7.2f}±{se(dk):.2f} | '
          f'{100 * v.mean():+8.1f}% | {pk(P0[P0.typ == t])} · {pk(P0[P0.opp == t])}')
D = R[R.status == 'νεκρη']
dm = (D.gf - D.ga) - (D.lf - D.la); dk = (D.gf - D.ga) - D.mkt
print(f'{"ΟΛΕΣ ΟΙ ΝΕΚΡΕΣ":28s} {len(D):4d} | {(D.xf - D.lf).mean():+5.2f}±{se(D.xf - D.lf):.2f} {(D.gf - D.lf).mean():+6.2f}±{se(D.gf - D.lf):.2f} | {dm.mean():+6.2f}±{se(dm):.2f} {dk.mean():+7.2f}±{se(dk):.2f} | '
      f'{100 * D[["ah_Crown", "ah_SBOBET"]].stack().mean():+8.1f}% | {pk(P0[P0.typ.notna() & (P0.typ != ORDER[-1])])}')
print(f'   ανα σεζον (xG−μοντελο νεκρων): ' + ' · '.join(f'{s}: {(D[D.sea == s].xf - D[D.sea == s].lf).mean():+.2f} (n{(D.sea == s).sum()})' for s in ('2425', '2526')))
# ---- διορθωση 2-fold ----
X = R.dropna(subset=['lf'])
def ll(x, a, d):
    dead = (x.status == 'νεκρη').values
    lf = x.lf.values * np.exp(np.where(dead, a, 0)); la = x.la.values * np.exp(np.where(dead, d, 0))
    return float(np.sum(x.gf.values * np.log(lf) - lf + x.ga.values * np.log(la) - la))
GR = np.round(np.arange(-0.5, 0.31, 0.05), 2); FIT = {}
print('\nΔΙΟΡΘΩΣΗ 2-fold (τιμη απο την ΑΛΛΗ σεζον του νεου φορματ):')
for te, tr in (('2425', '2526'), ('2526', '2425')):
    A = X[X.sea == tr]; a = max(GR, key=lambda v: ll(A, v, 0)); d = max(GR, key=lambda v: ll(A, a, v)); FIT[te] = (a, d)
    T = X[X.sea == te]
    print(f'   {te}: a {a:+.2f} (επιθεση ×{math.exp(a):.2f}) · d {d:+.2f} → Δπιθανοφανεια {ll(T, a, d) - ll(T, 0, 0):+.2f}')
LH, LA = g['BASE'][0].copy(), g['BASE'][1].copy()
for r in D.itertuples():
    i = IDX.get(r.mid)
    if i is None: continue
    a, d = FIT[r.sea]
    if r.side == 1: LH[i] *= math.exp(a); LA[i] *= math.exp(d)
    else: LA[i] *= math.exp(a); LH[i] *= math.exp(d)
P1 = picks((LH, LA))
k0 = set(zip(P0.bk, P0.mid, P0.side)); k1 = set(zip(P1.bk, P1.mid, P1.side))
print(f'   picks σημερα: {pk(P0)} → με διορθωση: {pk(P1)}')
print(f'   φευγουν {pk(P0[[k not in k1 for k in zip(P0.bk, P0.mid, P0.side)]])} · μπαινουν {pk(P1[[k not in k0 for k in zip(P1.bk, P1.mid, P1.side)]])}')
print('   ανα σεζον: ' + ' · '.join(f'{s}: {pk(P0[P0.sea == s])} → {pk(P1[P1.sea == s])}' for s in ('2425', '2526')))
