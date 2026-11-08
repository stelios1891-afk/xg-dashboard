"""
southam_mech1.py — 5/10/2026 ΦΑΣΗ 4α: ΕΙΔΙΚΟΙ ΜΗΧΑΝΙΣΜΟΙ vs ΤΕΛΙΚΗ ΑΓΟΡΑ (Pinnacle 1Χ2, football-data 2012-2025).
Για καθε ματς: «υπολοιπο» = πραγματικη υπεροχη γηπεδουχου − αναμενομενη της αγορας (λ απο 1Χ2, Dixon-Coles).
Θετικο = ο γηπεδουχος τα πηγε ΚΑΛΥΤΕΡΑ απ' οσο ελεγε η αγορα. Αν ενας μηχανισμος δινει υπολοιπο ≠ 0 σταθερα → η αγορα τον υποτιμα.
Επισης τυφλο ROI στο τελικο 1Χ2 Pinnacle (γηπεδουχος / φιλοξενουμενος) σε καθε κελι.
Μηχανισμοι: αποσταση ταξιδιου φιλοξενουμενου · ζωνες ωρας · υψομετρο (MLS Κολοραντο/RSL, Βραζ. οροπεδιο) · συνθετικο χορτο
· ξεκουραση/κουραση (ημερες απο το προηγουμενο ματς ΟΛΩΝ των διοργανωσεων, 2021+) · ηπειρωτικο/κυπελλο αμεσως πριν/μετα
· φαση σεζον (αγωνιστικη) · τελευταιες αγωνιστικες · MLS διακοπη Leagues Cup / παραθυρα FIFA.
Περιγραφικο — ΚΑΜΙΑ αποφαση. Οι μηχανισμοι με |t|≥2 ΚΑΙ σταθεροτητα ανα σεζον περνανε στη Φαση 4β (με χαντικαπ Nowgoal & μοντελο).
"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import southam_common as C
from southam_geo import GEO

F = pd.concat([C.fd_load('BRA', 'Brazil'), C.fd_load('USA', 'MLS')], ignore_index=True)
F = F[(F.Season <= 2025) & F.PSCH.notna() & F.PSCD.notna() & F.PSCA.notna()].copy()
inv = 1 / F[['PSCH', 'PSCD', 'PSCA']].values; q = inv / inv.sum(1, keepdims=True)
F['mH'], F['mD'], F['mA'] = q[:, 0], q[:, 1], q[:, 2]
L = C.market_lambdas(F.mH.values, F.mD.values, F.mA.values); F['msup'] = L[:, 0] - L[:, 1]; F['mtot'] = L[:, 0] + L[:, 1]
F['gd'] = F.HG - F.AG; F['res'] = F.gd - F.msup
F['pnl_h'] = np.where(F.gd > 0, F.PSCH - 1, -1.0); F['pnl_a'] = np.where(F.gd < 0, F.PSCA - 1, -1.0)
F['geo'] = F.kh.isin(GEO) & F.ka.isin(GEO)
def hav(a, b):
    la1, lo1 = math.radians(a[0]), math.radians(a[1]); la2, lo2 = math.radians(b[0]), math.radians(b[1])
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
F['km'] = [hav(GEO[h], GEO[a]) if g else np.nan for h, a, g in zip(F.kh, F.ka, F.geo)]
F['tz'] = [abs(GEO[h][2] - GEO[a][2]) if g else np.nan for h, a, g in zip(F.kh, F.ka, F.geo)]
F['alt_h'] = [GEO[h][3] if g else np.nan for h, a, g in zip(F.kh, F.ka, F.geo)]
F['alt_gap'] = [GEO[h][3] - GEO[a][3] if g else np.nan for h, a, g in zip(F.kh, F.ka, F.geo)]
F['turf_h'] = [GEO[h][4] if g else np.nan for h, g in zip(F.kh, F.geo)]
F['turf_a'] = [GEO[a][4] if g else np.nan for a, g in zip(F.ka, F.geo)]
# αγωνιστικη (σειρα ματς της ομαδας στη σεζον) & τελευταιες
F = F.sort_values(['league', 'Season', 'date']).reset_index(drop=True)
for side in ('h', 'a'):
    F[f'n_{side}'] = 0
cnt = {}
for i, r in F.iterrows():
    for side, k in (('h', r.kh), ('a', r.ka)):
        c = cnt.get((r.league, r.Season, k), 0); F.at[i, f'n_{side}'] = c + 1; cnt[(r.league, r.Season, k)] = c + 1
tot = F.groupby(['league', 'Season']).apply(lambda g: max(g.n_h.max(), g.n_a.max()), include_groups=False).to_dict()
F['md'] = np.maximum(F.n_h, F.n_a); F['left'] = [tot[(l, s)] - m for l, s, m in zip(F.league, F.Season, F.md)]
# ξεκουραση ΟΛΩΝ των διοργανωσεων (2021+): λιγκα + κυπελλα FotMob
cups = pd.DataFrame(json.load(open('southam_cups.json', encoding='utf-8')))
cups['date'] = pd.to_datetime(cups.utc, utc=True).dt.tz_localize(None).dt.normalize()
games = {}
for r in cups.itertuples():
    for nm, opp in ((r.home, r.away), (r.away, r.home)):
        games.setdefault(C.key(nm), []).append((r.date, r.comp))
for r in F.itertuples():
    for nm in (r.kh, r.ka):
        games.setdefault(nm, []).append((r.date.normalize(), 'league'))
for k in games: games[k] = sorted(set(games[k]))
def rest(k, d):
    g = games.get(k, []); prev = [x for x in g if x[0] < d]; nxt = [x for x in g if x[0] > d]
    pr = (d - prev[-1][0]).days if prev else np.nan; pc = prev[-1][1] if prev else None
    nx = (nxt[0][0] - d).days if nxt else np.nan; nc = nxt[0][1] if nxt else None
    return pr, pc, nx, nc
R = [rest(h, d.normalize()) + rest(a, d.normalize()) for h, a, d in zip(F.kh, F.ka, F.date)]
F[['rest_h', 'prevc_h', 'next_h', 'nextc_h', 'rest_a', 'prevc_a', 'next_a', 'nextc_a']] = pd.DataFrame(R, index=F.index)
F.loc[F.Season < 2021, ['rest_h', 'rest_a', 'next_h', 'next_a']] = np.nan
CONT = {'Libertadores', 'Sudamericana', 'ConcacafCC', 'LeaguesCup', 'ClubWorldCup'}
F.to_csv('southam_mech1_rows.csv', index=False)

def cell(d, lab):
    if len(d) < 25: return f'  {lab:46s} n{len(d):5d}'
    se = d.res.std() / np.sqrt(len(d)); ps = d.groupby('Season').res.mean()
    rh = d.pnl_h.mean(); ra = d.pnl_a.mean()
    return (f'  {lab:46s} n{len(d):5d}  υπολοιπο {d.res.mean():+.3f} ±{se:.3f} (t {d.res.mean()/se:+.1f}) · σεζον υπερ γηπ {int((ps > 0).sum())}/{len(ps)}'
            f' · ROI γηπ {100*rh:+5.1f}% · φιλοξ {100*ra:+5.1f}%')
for lg in ('Brazil', 'MLS'):
    D = F[F.league == lg]
    print(f'\n======================== {lg} — n {len(D)} (2012-2025) · μεσο υπολοιπο ολων {D.res.mean():+.3f} ±{D.res.std()/np.sqrt(len(D)):.3f} ========================')
    print(' ΤΑΞΙΔΙ φιλοξενουμενου (km):')
    for lo, hi in ((0, 500), (500, 1500), (1500, 2500), (2500, 9999)):
        print(cell(D[(D.km >= lo) & (D.km < hi)], f'{lo}-{hi} km'))
    if lg == 'MLS':
        print(' ΖΩΝΕΣ ΩΡΑΣ διαφορα:')
        for z in (0, 1, 2, 3):
            print(cell(D[D.tz == z], f'{z} ωρες'))
    print(' ΥΨΟΜΕΤΡΟ (γηπεδο − εδρα φιλοξενουμενου):')
    for lo, hi in ((-9999, -500), (-500, 500), (500, 1000), (1000, 9999)):
        print(cell(D[(D.alt_gap >= lo) & (D.alt_gap < hi)], f'{lo}..{hi} m'))
    if lg == 'MLS':
        print(cell(D[D.kh.isin(['colorado', 'rsl'])], 'εδρα Κολοραντο/RSL (ολα)'))
        print(cell(D[D.kh.isin(['colorado', 'rsl']) & (D.alt_gap > 1000)], 'Κολοραντο/RSL vs ομαδα χαμηλου'))
    print(' ΣΥΝΘΕΤΙΚΟ ΧΟΡΤΟ:')
    print(cell(D[(D.turf_h == 1) & (D.turf_a == 0)], 'γηπ σε συνθετικο, φιλοξ απο φυσικο'))
    print(cell(D[(D.turf_h == 0)], 'φυσικο χορτο'))
    print(' ΞΕΚΟΥΡΑΣΗ (ολες οι διοργανωσεις, 2021+) — διαφορα ημερων γηπ−φιλοξ:')
    E = D[D.rest_h.notna() & D.rest_a.notna()]
    dr = (E.rest_h.clip(upper=10) - E.rest_a.clip(upper=10))
    for lo, hi in ((-99, -3), (-3, -1), (-1, 2), (2, 4), (4, 99)):
        print(cell(E[(dr >= lo) & (dr < hi)], f'διαφορα {lo}..{hi}'))
    print(cell(E[E.rest_a <= 3], 'φιλοξ με ≤3 μερες ξεκουραση'))
    print(cell(E[E.rest_h <= 3], 'γηπ με ≤3 μερες ξεκουραση'))
    print(' ΗΠΕΙΡΩΤΙΚΟ/ΚΥΠΕΛΛΟ γυρω απο το ματς (2021+):')
    print(cell(E[E.prevc_h.isin(CONT) & (E.rest_h <= 4)], 'γηπ επαιξε ηπειρωτικο ≤4 μερες πριν'))
    print(cell(E[E.prevc_a.isin(CONT) & (E.rest_a <= 4)], 'φιλοξ επαιξε ηπειρωτικο ≤4 μερες πριν'))
    print(cell(E[E.nextc_h.isin(CONT) & (E.next_h <= 4)], 'γηπ εχει ηπειρωτικο σε ≤4 μερες (rotation;)'))
    print(cell(E[E.nextc_a.isin(CONT) & (E.next_a <= 4)], 'φιλοξ εχει ηπειρωτικο σε ≤4 μερες (rotation;)'))
    print(cell(E[(E.nextc_h == 'CopaDoBrasil') & (E.next_h <= 4)] if lg == 'Brazil' else E[(E.nextc_h == 'USOpenCup') & (E.next_h <= 4)], 'γηπ εχει εγχωριο κυπελλο σε ≤4 μερες'))
    print(cell(E[(E.nextc_a == 'CopaDoBrasil') & (E.next_a <= 4)] if lg == 'Brazil' else E[(E.nextc_a == 'USOpenCup') & (E.next_a <= 4)], 'φιλοξ εχει εγχωριο κυπελλο σε ≤4 μερες'))
    print(' ΦΑΣΗ ΣΕΖΟΝ:')
    for lo, hi in ((1, 7), (7, 15), (15, 25), (25, 99)):
        print(cell(D[(D.md >= lo) & (D.md < hi)], f'αγωνιστικη {lo}-{hi - 1}'))
    for k in (1, 2, 3):
        print(cell(D[D.left == k - 1], f'{k}η απο το τελος'))
    print(' ΑΝΑ ΣΕΖΟΝ (εδρα: μεσο υπολοιπο — θετικο = η αγορα υποτιμησε τον γηπεδουχο):')
    print('   ' + ' '.join(f'{s}:{g.res.mean():+.2f}' for s, g in D.groupby('Season')))
