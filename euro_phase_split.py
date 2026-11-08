"""euro_phase_split.py — 9/10/2026 (Στελιος: «τα αποτελεσματα ανα διοργανωση ειναι μαζι με τα νοκ αουτ;»).
Χωρισμα League Phase/ομιλοι (αγωνιστικες 1-8) vs ΝΟΚ-ΑΟΥΤ (playoff, 1/8 ... τελικος), 2223-2526:
(Α) σημερινοι κανονες ευρωπαικων picks (κλεισιμο, μεσος Crown/Pinnacle) · (Β) κανονας UEL φαβ εντος (dump 0.8, 24ω @4%, Crown/SBOBET)."""
import sys, io, json, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
RND = {str(m['mid']): str(m['round']) for v in ef.values() for m in v}
PH = lambda mid: 'League Phase' if RND.get(str(mid), '?').isdigit() else 'νοκ-αουτ'
src = open('euro_dominance_cost.py', encoding='utf-8').read().split("SEL = [")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'ps'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
C = g['P']['Γ σημερα γ+κ']; C['ph'] = C.mid.map(PH)
def cell(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():.0f} picks {100 * m["mean"].mean():+.1f}% ({int((ps > 0).sum())}/{ps.size} σεζ)'
print('(Α) ΣΗΜΕΡΙΝΟΙ ΚΑΝΟΝΕΣ — κλεισιμο, μεσος Crown/Pinnacle')
for lab, f in (('ΟΛΑ', lambda d: d), ('UCL', lambda d: d[d.comp == 'ChampionsLeague']), ('UEL', lambda d: d[d.comp == 'EuropaLeague']),
               ('UECL', lambda d: d[d.comp == 'ConferenceLeague']), ('φαβορι', lambda d: d[d.role == 'fav']), ('αουτσαιντερ', lambda d: d[d.role == 'dog'])):
    x = f(C)
    print(f'   {lab:12s} ΟΛΑ {cell(x):28s} | League Phase {cell(x[x.ph == "League Phase"]):28s} | νοκ-αουτ {cell(x[x.ph == "νοκ-αουτ"])}')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
D = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb')); rows = []
for i, mid in enumerate(D['MIDS']):
    if D['COMP'][i] != 'EuropaLeague' or not D['FM'][i]: continue
    dist = u['sdist'](D['LH'][i], D['LA'][i])
    for bk in ('Crown', 'SBOBET'):
        s = u['snap'](mid, bk, 24)
        if not s: continue
        L, oh, oa = s
        if L > -0.5 or not (1.70 <= oh <= 2.10): continue
        pw, pp = u['cover_q'](dist, 1, L)
        if u['edge'](pw, pp, oh) >= .04:
            rows.append(dict(bk=bk, sea=D['SEA'][i], ph=PH(mid), pnl=u['picks'].settle(D['GD'][i], 1, L, oh)))
R = pd.DataFrame(rows)
print(f'\n(Β) UEL ΦΑΒΟΡΙ ΕΝΤΟΣ (24ω, edge ≥4%, Crown/SBOBET): ΟΛΑ {cell(R)} | League Phase {cell(R[R.ph == "League Phase"])} | νοκ-αουτ {cell(R[R.ph == "νοκ-αουτ"])}')
