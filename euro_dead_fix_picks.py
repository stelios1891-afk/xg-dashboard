"""euro_dead_fix_picks.py — 10/10/2026 (Στελιος: «μας νοιαζει αν το μοντελο εβρισκε αξια και ηταν ψευτικη»).
Τελευταιες 2 αγωνιστικες: τα ΔΙΚΑ ΜΑΣ picks (σημερινοι κανονες, κλεισιμο, μεσος Crown/Pinnacle) σε ματς με «νεκρη» ομαδα,
ανα ειδος νεκρης (νεα με κινητρο θεσης / νεα εντελως νεκρη / ομιλοι κλειδωμενοι), και τι κανει η διορθωση
(λ επιθεσης νεκρης ×e^a, λ αμυνας ×e^d, με τις LOSO τιμες της αντιστοιχης σεζον απο euro_motivation): ποια picks φευγουν/μπαινουν/μενουν."""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'df'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
R = pd.read_pickle('euro_motivation_seed_rows.pkl')
LOSO = {'2223': (-0.20, 0.05), '2324': (-0.25, 0.05), '2425': (-0.20, 0.10), '2526': (-0.15, 0.05)}   # euro_motivation_out (a, d)
def kind(r):
    if r.status != 'νεκρη': return None
    if not r.new: return 'ομιλοι κλειδωμενοι'
    return 'νεα + κινητρο θεσης' if r.ws_seed >= 0.05 else 'νεα εντελως νεκρη'
R['kind'] = [kind(r) for r in R.itertuples()]
G = g['g']; MIDS = G['MIDS']; IDX = {m: i for i, m in enumerate(MIDS)}
LH, LA = g['BASE'][0].copy(), g['BASE'][1].copy()
for r in R[R.kind.notna()].itertuples():
    i = IDX.get(r.mid)
    if i is None: continue
    a, d = LOSO[r.sea]
    if r.side == 1: LH[i] *= np.exp(a); LA[i] *= np.exp(d)
    else: LA[i] *= np.exp(a); LH[i] *= np.exp(d)
DEADM = {}
for r in R[R.kind.notna()].itertuples(): DEADM.setdefault(r.mid, []).append((r.side, r.kind))
LATE = set(R.mid)
def picks(L):
    out = []
    for bk, OD in (('Crown', g['CROWN']), ('Pin', g['PIN'])):
        for (mid, side), rr in g['gen'](L, OD).items():
            if mid not in LATE: continue
            dm = DEADM.get(mid, [])
            on = [k for s, k in dm if s == side]; ag = [k for s, k in dm if s == -side]
            out.append(dict(bk=bk, mid=mid, side=side, role=rr['role'], sea=rr['sea'], pnl=rr['pnl'],
                            wh=('σε νεκρη' if on else ('κατα νεκρης' if ag else 'χωρις νεκρη')), kind=(on or ag or [None])[0]))
    return pd.DataFrame(out)
P0, P1 = picks(g['BASE']), picks((LH, LA))
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():.0f} picks {100 * m["mean"].mean():+.1f}% ({m["size"].mean() * m["mean"].mean():+.1f}u)'
print('1. ΤΑ PICKS ΜΑΣ ΣΗΜΕΡΑ στις τελευταιες 2 αγωνιστικες')
print(f'   ολα: {c(P0)}')
for w in ('σε νεκρη', 'κατα νεκρης', 'χωρις νεκρη'):
    x = P0[P0.wh == w]
    print(f'   pick {w:12s}: {c(x)}' + ('' if w == 'χωρις νεκρη' else '   [' + ' · '.join(f'{k}: {c(x[x.kind == k])}' for k in ('νεα + κινητρο θεσης', 'νεα εντελως νεκρη', 'ομιλοι κλειδωμενοι')) + ']'))
    if w != 'χωρις νεκρη':
        print(f'      ως φαβορι {c(x[x.role == "fav"])} · ως αουτσαιντερ {c(x[x.role == "dog"])}')
print('\n2. ΜΕ ΤΗ ΔΙΟΡΘΩΣΗ (λ νεκρης επιθ ×e^a / αμυνα ×e^d, LOSO ανα σεζον)')
print(f'   ολα: {c(P1)}  (σημερα {c(P0)})')
k0 = set(zip(P0.bk, P0.mid, P0.side)); k1 = set(zip(P1.bk, P1.mid, P1.side))
gone = P0[[k not in k1 for k in zip(P0.bk, P0.mid, P0.side)]]; new = P1[[k not in k0 for k in zip(P1.bk, P1.mid, P1.side)]]
stay = P1[[k in k0 for k in zip(P1.bk, P1.mid, P1.side)]]
print(f'   φευγουν : {c(gone)}  [σε νεκρη {c(gone[gone.wh == "σε νεκρη"])} · κατα νεκρης {c(gone[gone.wh == "κατα νεκρης"])}]')
print(f'   μπαινουν: {c(new)}  [σε νεκρη {c(new[new.wh == "σε νεκρη"])} · κατα νεκρης {c(new[new.wh == "κατα νεκρης"])}]')
print(f'   μενουν  : {c(stay)}')
print('   ανα σεζον (σημερα → με διορθωση): ' + ' · '.join(f'{s}: {100 * P0[P0.sea == s].pnl.mean():+.0f}% → {100 * P1[P1.sea == s].pnl.mean():+.0f}%' for s in sorted(P0.sea.unique())))
