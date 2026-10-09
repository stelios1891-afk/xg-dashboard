"""euro_dead_picks.py — 10/10/2026: τα picks μας (σημερινοι κανονες, κλεισιμο) ΠΑΝΩ σε «νεκρες» ομαδες στις τελευταιες 2 αγωνιστικες — τι ηταν."""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'dp'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
R = pd.read_pickle('euro_motivation_rows.pkl')
ST = {(r.mid, r.side): (r.status, r.opp_status, r.team, r.sea, r.comp) for r in R.itertuples()}
ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
INFO = {str(m['mid']): (m['hname'], m['aname'], m['score'], m['round']) for v in ef.values() for m in v}
G = g['g']; MIDS = G['MIDS']; IDX = {m: i for i, m in enumerate(MIDS)}
rows = []
for bk, OD in (('Crown', g['CROWN']), ('Pin', g['PIN'])):
    for (mid, side), rr in g['gen'](g['BASE'], OD).items():
        s = ST.get((mid, side))
        if not s: continue
        lf, oh, oa = OD[mid]; ln, o = (lf, oh) if side == 1 else (-lf, oa)
        rows.append(dict(bk=bk, mid=mid, side=side, status=s[0], opp=s[1], team=s[2], sea=s[3], comp=s[4], role=rr['role'], line=ln, odds=o,
                         home=side == 1, pnl=rr['pnl'], match=f'{INFO[mid][0]} – {INFO[mid][1]}', score=INFO[mid][2], rnd=INFO[mid][3]))
P = pd.DataFrame(rows)
D = P[P.status == 'νεκρη']
def c(x):
    m = x.groupby('bk').pnl.agg(['mean', 'size'])
    return f'{m["size"].mean():.0f} picks {100 * m["mean"].mean():+.1f}%' if len(m) else '—'
print(f'ΣΥΝΟΛΟ picks σε νεκρη ομαδα: {c(D)}')
for lab, f in (('ως ΦΑΒΟΡΙ', D.role == 'fav'), ('ως ΑΟΥΤΣΑΙΝΤΕΡ', D.role == 'dog'), ('εντος', D.home), ('εκτος', ~D.home),
               ('αντιπαλος με κινητρο (υψηλο)', D.opp == 'υψηλο'), ('αντιπαλος επισης νεκρη', D.opp == 'νεκρη')):
    print(f'   {lab:30s} {c(D[f])}')
print('   ανα διοργανωση: ' + ' · '.join(f'{k[:4]} {c(D[D.comp == k])}' for k in sorted(D.comp.unique())))
print('\nΛΙΣΤΑ (μοναδικα picks· τιμη/γραμμη Crown αν υπαρχει):')
U = D.sort_values('bk').drop_duplicates(['mid', 'side'])
for r in U.sort_values(['sea', 'comp']).itertuples():
    print(f'   {r.sea} {r.comp[:4]} αγ.{r.rnd} {r.match[:38]:38s} {r.score:6s} | pick {r.team[:18]:18s} {"εντος" if r.home else "εκτος"} {r.role:3s} {r.line:+.2f} @{r.odds:.2f} '
          f'→ {r.pnl:+.2f} | αντιπ. {r.opp}')
