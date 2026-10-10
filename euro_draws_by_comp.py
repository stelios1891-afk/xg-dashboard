"""euro_draws_by_comp.py — 10/10/2026 (Στελιος: «ποσες ισοπαλιες προβλεπουμε, τι δινει η αγορα, τι η πραγματικοτητα — ανα διοργανωση»).
2223-2526, FotMob+FotMob και ολα τα ματς. Μοντελο = σημερινο χαντικαπ/1Χ2 Ευρωπης (Poisson ×1.13 στα ισοπαλα, μετα ×0.85 στη μαζα ισοπαλιας).
Αγορα = Pinnacle 1Χ2 κλεισιμο (toa_pin_hist) χωρις γκανιοτα. + ποια κλιμακα ισοπαλιας θα εφερνε το μοντελο στην πραγματικοτητα ανα διοργανωση."""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
MIDS, COMP, FM, SEA, LH, LA, GD, picks = u['MIDS'], np.asarray(u['COMP']), np.asarray(u['FM']), np.asarray(u['SEA']), u['LH_N'], u['LA_N'], np.asarray(u['GD']), u['picks']
KO = u['KO']
PIN = {}
for line in open('toa_pin_hist.jsonl', encoding='utf-8'):
    r = json.loads(line)
    if r.get('h') and r.get('d') and r.get('a'): PIN[str(r['mid'])] = (r['h'], r['d'], r['a'])   # τελευταια εγγραφη = κλεισιμο
rows = []
for i, mid in enumerate(MIDS):
    d1 = picks.gd_dist(max(LH[i], .05), max(LA[i], .05)); px = d1.get(0, 0.0)
    p = PIN.get(mid); mk = np.nan
    if p:
        inv = [1 / x for x in p]; mk = inv[1] / sum(inv)
    rows.append(dict(comp=COMP[i], sea=SEA[i], fm=bool(FM[i]), raw113=px, model=0.85 * px, mk=mk, act=float(GD[i] == 0)))
D = pd.DataFrame(rows)
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
print('ΙΣΟΠΑΛΙΕΣ (%): πραγματικο · μοντελο σημερα (×1.13 → ×0.85) · αγορα Pinnacle · χωρις το ×0.85 (×1.13 μονο)')
print('  → «σωστη κλιμακα» = ποσο θα επρεπε να πολλαπλασιασουμε τη μαζα ισοπαλιας του ×1.13 για να πεσει πανω στο πραγματικο')
for scope, m in (('ολα τα ματς', np.ones(len(D), bool)), ('FotMob+FotMob', D.fm.values)):
    print(f'\n== {scope} ==')
    for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
        x = D[m & (D.comp == cm).values]; y = x.dropna(subset=['mk'])
        print(f'   {CL[cm]:5s} n{len(x):4d} · πραγμ {100 * x.act.mean():.1f} · μοντελο {100 * x.model.mean():.1f} · αγορα {100 * y.mk.mean():.1f} (n{len(y)}) · ×1.13 μονο {100 * x.raw113.mean():.1f} · σωστη κλιμακα {x.act.mean() / x.raw113.mean():.2f}')
        print('         ανα σεζον πραγμ/μοντελο/αγορα: ' + ' · '.join(f'{s}: {100 * z.act.mean():.0f}/{100 * z.model.mean():.0f}/{100 * z.dropna(subset=["mk"]).mk.mean():.0f}' for s, z in x.groupby('sea')))
