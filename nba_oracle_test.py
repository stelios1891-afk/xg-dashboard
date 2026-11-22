# -*- coding: utf-8 -*-
"""nba_oracle_test.py — NBA ΤΕΣΤ «ΤΕΛΕΙΑΣ ΠΛΗΡΟΦΟΡΙΑΣ» (28/9/2026): αν ξεραμε ποιος παιζει, φτανουμε την αγορα;
Αξια παικτη (ΠΡΙΝ απο καθε ματς): ρυθμοι ανα λεπτο απο ολα τα προηγουμενα ματς του με φθορα (μιση αξια σε 180 μερες), μαζεμα
  300′ προς τον μεσο της λιγκας· χαρακτηριστικα: 2Π ευστ./αστ., 3Π ευστ./αστ., βολες ευστ./αστ., ΕΡ, ΑΡ, ΑΣ, ΚΛ, ΚΟ, ΛΑ, ΦΑ, +/-.
Ομαδα σε καθε ματς: Σ μεριδιο λεπτων × χαρακτηριστικα (γηπ − φιλ).
  Τ1 «πληρης γνωση»: πραγματικα λεπτα καθε παικτη.
  Τ2 «γνωση απουσιων»: ποιοι επαιξαν ΓΝΩΣΤΟ, λεπτα = προσφατος μεσος ορος τους (αναλογα σε 240′).
Βαρη χαρακτηριστικων & συνδυασμος με το μοντελο ομαδων: μετρημενα ΜΟΝΟ στις αλλες σεζον (LOSO).
Κριση: RMSE vs Crown closing · κλιση b · ROI χαντικαπ ≥5/8/10% (ιδια συναρτηση με nba_model_test). Εξοδος: nba_oracle_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_model_test.py', encoding='utf-8').read().split("P('')\nP('=== ΒΑΣΙΚΟ ΜΟΝΤΕΛΟ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()

A = pd.read_csv('nba_player_games.csv')
A = A[A.stype == 'RS'].copy()
A['date'] = pd.to_datetime(A.GAME_DATE)
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
A['team'] = A.TEAM_ABBREVIATION.replace(AB)
A['opp'] = A.MATCHUP.str.split(' ').str[-1].replace(AB)
A['home'] = A.MATCHUP.str.contains(' vs. ')
A['MIN'] = pd.to_numeric(A.MIN, errors='coerce').fillna(0)
A = A[A.MIN > 0]
A['p2m'] = A.FGM - A.FG3M; A['p2x'] = (A.FGA - A.FG3A) - (A.FGM - A.FG3M); A['p3m'] = A.FG3M; A['p3x'] = A.FG3A - A.FG3M
A['ftm'] = A.FTM; A['ftx'] = A.FTA - A.FTM
F = ['p2m', 'p2x', 'p3m', 'p3x', 'ftm', 'ftx', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']
A = A.sort_values(['date', 'GAME_ID']).reset_index(drop=True)
# αντιστοιχιση με τα ματς του G (ημερομηνια + γηπεδουχος)
gk = {(d, h): i for i, (d, h) in enumerate(zip(G.date, G.home))}
A['gi'] = [gk.get((d, t if hm else o)) for d, t, o, hm in zip(A.date, A.team, A.opp, A.home)]
A = A[A.gi.notna()].copy(); A['gi'] = A.gi.astype(int)
P(f'γραμμες παικτη-ματς (κανονικη περιοδος, αντιστοιχισμενες): {len(A)} · ματς {A.gi.nunique()}')

# ---- ρυθμοι ΠΡΙΝ απο καθε ματς (φθορα 180 μερες, μαζεμα 300′) ----
HLD, M0 = 180.0, 300.0
MU = A[F].sum() / A.MIN.sum()
state = {}                                          # pid -> [t_last, min_sum, stat_sums(np), gm_count, min_recent]
pre = np.zeros((len(A), len(F))); premin = np.zeros(len(A))
for d, blk in A.groupby('date', sort=True):
    for k, r in blk.iterrows():
        s = state.get(r.PLAYER_ID)
        if s is None:
            pre[k] = MU.values; premin[k] = np.nan
        else:
            fac = 0.5 ** ((d - s[0]).days / HLD)
            ms = s[1] * fac; ss = s[2] * fac
            pre[k] = (ss + M0 * MU.values) / (ms + M0); premin[k] = s[4]
    for k, r in blk.iterrows():
        s = state.get(r.PLAYER_ID); v = r[F].values.astype(float)
        if s is None:
            state[r.PLAYER_ID] = [d, r.MIN, v.copy(), 1, r.MIN]
        else:
            fac = 0.5 ** ((d - s[0]).days / HLD)
            state[r.PLAYER_ID] = [d, s[1] * fac + r.MIN, s[2] * fac + v, s[3] + 1, 0.8 * s[4] + 0.2 * r.MIN]
X = pre - MU.values                                  # πανω απο τον μεσο παικτη
A['premin'] = premin
# Τ1: πραγματικα λεπτα · Τ2: προσφατος μεσος ορος λεπτων (οσων επαιξαν), αναλογα σε 240′
tm_min = A.groupby(['gi', 'team']).MIN.transform('sum')
A['s1'] = A.MIN / (tm_min / 5)
pm_ = A.premin.fillna(A.groupby(['gi', 'team']).premin.transform('median')).fillna(15.0)
A['s2'] = pm_ / (pm_.groupby([A.gi, A.team]).transform('sum') / 5)
sign = np.where(A.home, 1.0, -1.0)
def game_feats(scol):
    Z = np.zeros((len(G), len(F)))
    np.add.at(Z, A.gi.values, (sign * A[scol].values)[:, None] * X)
    return Z
Z1, Z2 = game_feats('s1'), game_feats('s2')
Y100 = 100 * (G.hs - G.as_).values / G.poss.values; HOMEI = (~G.neutral.values).astype(float)
SEAS_G = G.season.values
team_base = run(h=2.0, lam=8, HL=60, carry=0.7)[0]     # το καλυτερο μοντελο ομαδων (LOSO χαντικαπ)
PACE = np.nanmean(G.pace.values)
RESULTS = {}
for nm, Z in (('Τ1 πληρης γνωση (πραγματικα λεπτα)', Z1), ('Τ2 γνωση απουσιων (μεσα λεπτα)', Z2)):
    pl_only = np.full(len(G), np.nan); combo = np.full(len(G), np.nan); betas = []
    for Y in SEAS[1:]:
        tr = (SEAS_G != Y) & (SEAS_G != SEAS[0]); te = SEAS_G == Y
        Axx = np.column_stack([HOMEI, Z]); Axx_tr = np.vstack([Axx[tr], np.column_stack([np.zeros(len(F)), np.eye(len(F))])])
        yy = np.concatenate([Y100[tr], np.zeros(len(F))])
        c = np.linalg.lstsq(Axx_tr, yy, rcond=None)[0]; betas.append(c)
        pl = (Axx @ c) * PACE / 100                                     # ποντοι
        pl_only[te] = pl[te]
        B = np.column_stack([np.ones(len(G)), team_base, pl])
        cc = np.linalg.lstsq(B[tr], (G.hs - G.as_).values[tr], rcond=None)[0]
        combo[te] = (B @ cc)[te]
    RESULTS[nm] = (pl_only, combo, np.mean(betas, axis=0))
P('')
P('=== ΑΠΟΤΕΛΕΣΜΑΤΑ (σεζον-τεστ 2021-22 … 2025-26, LOSO) ===')
def rep(lab, m):
    mm = np.isin(SE, EVAL); e = ACT - m[IDX]
    b = np.polyfit((m[IDX] - MM)[mm], (ACT - MM)[mm], 1)[0]
    cells = []
    for thr in (0.05, 0.08, 0.10):
        R = roi(m, thr, EVAL); pos = sum(1 for s in EVAL if len(R[R.season == s]) and R[R.season == s].p.mean() > 0)
        cells.append(f'≥{thr*100:.0f}%: {R.p.mean()*100:+.1f}% ({len(R)}) {pos}/{len(EVAL)}')
    P(f'  {lab:46s} RMSE {np.sqrt(np.mean(e[mm] ** 2)):.2f} · b {b:+.3f} | ' + ' | '.join(cells))
P(f'  (αγορα Crown closing: RMSE {np.sqrt(np.mean((ACT - MM)[np.isin(SE, EVAL)] ** 2)):.2f})')
rep('μοντελο ομαδων (χωρις παικτες)', team_base)
for nm, (pl, cb, bt) in RESULTS.items():
    rep(nm + ' — μονο παικτες', pl)
    rep(nm + ' — παικτες + ομαδα', cb)
P('')
P('βαρη χαρακτηριστικων (Τ1, μεσος ορος LOSO, π./100 ανα +1 ανα λεπτο πανω απο μεσο — ×48 για «ανα αγωνα»):')
P('  ' + ' · '.join(f'{f} {b * 48:+.1f}' for f, b in zip(F, RESULTS['Τ1 πληρης γνωση (πραγματικα λεπτα)'][2][1:])))
open('nba_oracle_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
