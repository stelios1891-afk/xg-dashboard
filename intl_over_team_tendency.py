"""
intl_over_team_tendency.py — OVER ΣΕ ΟΜΑΔΕΣ «ΧΩΡΙΣ ΓΚΟΛ» (25/9/2026, ερωτημα Στελιου: χασαμε over σε Αρμενια−Λετονια και Γεωργια−Β.Ιρλανδια,
«κακα ματς» — ομαδες που δεν φημιζονται για γκολ· φαινεται στο ιστορικο;). Το live T ΔΕΝ εχει ορο ομαδας (μονο διαφορα/κοντινο/επιπεδο).

ΤΑΣΗ ΟΜΑΔΑΣ (walk-forward, μονο πριν το ματς): μεσος συνολικων γκολ (υπερ+κατα) στα 12 προηγουμενα ΑΓΩΝΙΣΤΙΚΑ της ματς (≥6)· ιδιο με xG (ματς με xG).
  ταση ματς = μεσος των δυο ομαδων. Επισης: «ελαχιστη» = η ομαδα με τα λιγοτερα.
ΔΕΙΓΜΑ: over bets του τεστ παραθυρου 72ω (σωστος τυπος, intl_window_test_proper_ahproper_bets.csv) — Μ1/Μ2/Μ3 και συναινεση ≥2/3· Crown/SBOBET.
ΠΡΟ-ΔΗΛΩΣΗ (πριν τρεξει, ΜΙΑ εκτελεση):
  Τριτα της τασης (γκολ) στο δειγμα των over· ROI ανα τριτο.
  ΦΙΛΤΡΟ «εξω το χαμηλο τριτο» ΠΕΡΝΑ αν: ROI των υπολοιπων > ROI ολων ΚΑΙ στα 2 βιβλια, ΚΑΙ ROI του χαμηλου τριτου < 0 σε ≥4/5 σεζον, για τη ΣΥΝΑΙΝΕΣΗ.
  Αναφορα: ιδιο με xG· ιδιο για «ελαχιστη ομαδα»· η γραμμη της αγορας στα χαμηλα ματς (τα ξερει ηδη;)· οι δυο περιπτωσεις της 25/9.
Εξοδος: intl_over_team_tendency_out.txt
"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

M = pd.read_csv('intl_matches.csv', dtype={'mid': str, 'season': str}, parse_dates=['date'])
import intl_dedupe
M = intl_dedupe.dedupe(M, where='over_tendency').sort_values('date').reset_index(drop=True)
M['tot'] = M.hs + M['as']; M['xtot'] = np.where(M.has_xg, M.xg_h + M.xg_a, np.nan)
COMP = M.ctype.isin(['nl', 'qual', 'tourn'])
hist = {}; hx = {}; TEN = {}
for r in M.itertuples():
    vals = {}
    for t in (int(r.hid), int(r.aid)):
        g = hist.get(t, [])[-12:]; x = [v for v in hx.get(t, [])[-12:] if not np.isnan(v)]
        vals[t] = (np.mean(g) if len(g) >= 6 else np.nan, np.mean(x) if len(x) >= 4 else np.nan)
    TEN[r.mid] = (vals[int(r.hid)], vals[int(r.aid)])
    if r.ctype in ('nl', 'qual', 'tourn'):
        for t in (int(r.hid), int(r.aid)):
            hist.setdefault(t, []).append(r.tot); hx.setdefault(t, []).append(r.xtot)
def ten(m, i, how):
    a, b = TEN.get(m, ((np.nan, np.nan), (np.nan, np.nan)))
    return (a[i] + b[i]) / 2 if how == 'mean' else min(a[i], b[i])

B = pd.read_csv('intl_window_test_proper_ahproper_bets.csv', dtype={'mid': str, 'season': str})
B = B[(B.win == '72ω') & (B.rule == 'OVER') & B.model.isin(['M1', 'M2', 'M3'])].copy()
rows = [g.sort_values('hours').iloc[0].to_dict() | dict(model='ΣΥΝΑΙΝΕΣΗ') for (bk, mid), g in B.groupby(['book', 'mid']) if g.model.nunique() >= 2]
B = pd.concat([B, pd.DataFrame(rows)], ignore_index=True)
B['tg'] = [ten(m, 0, 'mean') for m in B.mid]; B['tx'] = [ten(m, 1, 'mean') for m in B.mid]; B['tmin'] = [ten(m, 0, 'min') for m in B.mid]
B = B.merge(M[['mid', 'tot']], on='mid', how='left')
P_(f'over bets 72ω: {len(B)} (με ταση γκολ {int(B.tg.notna().sum())}, με ταση xG {int(B.tx.notna().sum())})')

def cell(x):
    if len(x) < 5: return '—'
    s = x.groupby('season').pnl.mean(); return f"n{len(x):3d} {x.pnl.mean() * 100:+6.1f}% {int((s > 0).sum())}/{s.size}"
def avg2(x):
    c, s = x[x.book == 'Crown'], x[x.book == 'SBOBET']
    return (c.pnl.mean() + s.pnl.mean()) / 2 * 100 if len(c) and len(s) else np.nan

verdict = {}
for col, lab in (('tg', 'ΤΑΣΗ ΓΚΟΛ (μεσος 2 ομαδων)'), ('tx', 'ΤΑΣΗ xG (μεσος 2 ομαδων)'), ('tmin', 'ΤΑΣΗ ΓΚΟΛ — η πιο «στεγνη» ομαδα')):
    D = B[B[col].notna()].copy()
    q1, q2 = D[D.model == 'ΣΥΝΑΙΝΕΣΗ'][col].quantile([1 / 3, 2 / 3])
    D['τριτο'] = np.where(D[col] <= q1, 'χαμηλο', np.where(D[col] <= q2, 'μεσαιο', 'ψηλο'))
    P_(f'\n=== {lab} · ορια τριτων {q1:.2f} / {q2:.2f} γκολ ανα ματς ===')
    for mdl in ('ΣΥΝΑΙΝΕΣΗ', 'M1', 'M2', 'M3'):
        x = D[D.model == mdl]
        parts = []
        for t in ('χαμηλο', 'μεσαιο', 'ψηλο'):
            y = x[x['τριτο'] == t]; parts.append(f"{t}: {avg2(y):+6.1f}% (Crown {cell(y[y.book == 'Crown'])} · SBOBET {cell(y[y.book == 'SBOBET'])})")
        P_(f'  {mdl:10s} ' + ' | '.join(parts))
    x = D[D.model == 'ΣΥΝΑΙΝΕΣΗ']
    ok = True; det = []
    for bk in ('Crown', 'SBOBET'):
        a_ = x[x.book == bk].pnl.mean(); b_ = x[(x.book == bk) & (x['τριτο'] != 'χαμηλο')].pnl.mean(); ok &= b_ > a_; det.append(f'{bk} ολα {a_ * 100:+.1f} → χωρις χαμηλο {b_ * 100:+.1f}')
    lo = x[x['τριτο'] == 'χαμηλο'].groupby('season').pnl.mean(); neg = int((lo < 0).sum()); ok &= neg >= 4
    verdict[lab] = ok
    P_(f'  ΦΙΛΤΡΟ «εξω το χαμηλο» (συναινεση): {" · ".join(det)} · χαμηλο αρνητικο σε {neg}/{lo.size} σεζον → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
    y = x.copy(); y['line'] = y.line.astype(float)
    P_('  γραμμη αγορας & πραγματικα γκολ ανα τριτο (συναινεση): ' + ' · '.join(f"{t}: γραμμη {y[y['τριτο'] == t].line.mean():.2f}, γκολ {y[y['τριτο'] == t].tot.mean():.2f}" for t in ('χαμηλο', 'μεσαιο', 'ψηλο')))
# οι δυο περιπτωσεις της 25/9
P_('\n=== ΟΙ ΔΥΟ ΠΕΡΙΠΤΩΣΕΙΣ 25/9 (ταση πριν το ματς) ===')
ID = {}
for r in M.itertuples(): ID[r.hn] = int(r.hid); ID[r.an] = int(r.aid)
def now_t(t):
    g = hist.get(t, [])[-12:]; x = [v for v in hx.get(t, [])[-12:] if not np.isnan(v)]
    return (np.mean(g) if g else np.nan), (np.mean(x) if x else np.nan)
for h, a in (('Armenia', 'Latvia'), ('Georgia', 'Northern Ireland')):
    (gh, xh), (ga, xa) = now_t(ID[h]), now_t(ID[a])
    P_(f'  {h} − {a}: {h} {gh:.2f} γκολ/ματς (xG {xh:.2f}) · {a} {ga:.2f} (xG {xa:.2f}) · μεσος {(gh + ga) / 2:.2f} (ταση πριν τη 25/9)')
open('intl_over_team_tendency_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
