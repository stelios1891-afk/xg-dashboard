# -*- coding: utf-8 -*-
"""nba_raptor_oracle_test.py — NBA «ΤΕΛΕΙΑ ΠΛΗΡΟΦΟΡΙΑ» με επαγγελματικη αξια παικτη (RAPTOR/PREDATOR του FiveThirtyEight) (28/9/2026).
Ερωτημα: αν η δικη μας αξια παικτη ηταν επιπεδου FiveThirtyEight, θα φτανε την αγορα ξεροντας ποιος παιζει;
Αξια παικτη = PREDATOR total (προβλεπτικη εκδοχη RAPTOR, π./100 κατοχες) της ΠΡΟΗΓΟΥΜΕΝΗΣ σεζον (γνωστη πριν ξεκινησει),
  μαζεμα με λεπτα: v = predator × mp/(mp + 500)· χωρις RAPTOR (ροκι κτλ) → ξεχωριστη μεταβλητη «λεπτα αγνωστων».
Λεπτα: οπως Τ2 (ποιοι επαιξαν ΓΝΩΣΤΟ, λεπτα = προσφατος μεσος ορος). Σεζον-τεστ: 2021-22, 2022-23, 2023-24 (RAPTOR ως 2022-23).
Παραλλαγες (βαρη LOSO στις 3 σεζον): R1 μονο RAPTOR · R2 RAPTOR + μοντελο ομαδων · R3 RAPTOR + δικη μας αξια (Τ2) + ομαδα.
Συγκριση στις ΙΔΙΕΣ σεζον: αγορα · μοντελο ομαδων · δικη μας Τ2 + ομαδα. Εξοδος: nba_raptor_oracle_test_out.txt"""
import sys, re, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_oracle_test.py', encoding='utf-8').read().split("RESULTS = {}")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
R = pd.concat([pd.read_csv('nba_raptor/modern_RAPTOR_by_player.csv'), pd.read_csv('nba_raptor/latest_2023.csv')], ignore_index=True)
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
R['k'] = R.player_name.map(nk)
R = R.sort_values('mp', ascending=False).drop_duplicates(['k', 'season'])
RV = {(k, s): (p, m) for k, s, p, m in zip(R.k, R.season, R.predator_total, R.mp)}
A['k'] = A.PLAYER_NAME.map(nk)
A['season_end'] = A.season.str[:4].astype(int) + 1
vals = [RV.get((k, s - 1)) for k, s in zip(A.k, A.season_end)]
A['rv'] = [p * m / (m + 500) if v is not None and not pd.isna(v[0]) else np.nan for v in vals for p, m in [v if v is not None else (np.nan, np.nan)]]
TS = [2022, 2023, 2024]
cov = A[A.season_end.isin(TS)]
P(f'καλυψη λεπτων με RAPTOR περσινης σεζον: ' + ' · '.join(f'{s}: {np.average(cov[cov.season_end == s].rv.notna(), weights=cov[cov.season_end == s].MIN):.0%}' for s in TS))
known = A.rv.notna().values
ZR = np.zeros(len(G)); ZU = np.zeros(len(G))
np.add.at(ZR, A.gi.values, sign * A.s2.values * np.nan_to_num(A.rv.values))
np.add.at(ZU, A.gi.values, sign * A.s2.values * (~known))
Y = (G.hs - G.as_).values.astype(float)
def loso(cols):
    Xm = np.column_stack([HOMEI] + cols); pred = np.full(len(G), np.nan)
    for s in TS:
        tr = np.isin(SEAS_G, [t for t in TS if t != s]); te = SEAS_G == s
        c = np.linalg.lstsq(Xm[tr], Y[tr], rcond=None)[0]; pred[te] = (Xm @ c)[te]
    return pred
pl_ours = (np.column_stack([HOMEI, Z2]) @ np.linalg.lstsq(np.column_stack([HOMEI, Z2])[np.isin(SEAS_G, [2021, 2025, 2026])], Y100[np.isin(SEAS_G, [2021, 2025, 2026])], rcond=None)[0]) * PACE / 100
V = {'μοντελο ομαδων': loso([team_base]),
     'δικη μας αξια (Τ2) + ομαδα': loso([team_base, pl_ours]),
     'R1 μονο RAPTOR': loso([ZR * PACE / 100, ZU]),
     'R2 RAPTOR + ομαδα': loso([team_base, ZR * PACE / 100, ZU]),
     'R3 RAPTOR + δικη μας + ομαδα': loso([team_base, ZR * PACE / 100, ZU, pl_ours])}
EV3 = [s for s in TS if s in EVAL]
mm = np.isin(SE, EV3)
P(f'σεζον-τεστ {EV3} · ματς με closing {mm.sum()} · αγορα Crown RMSE {np.sqrt(np.mean((ACT - MM)[mm] ** 2)):.2f}')
P('')
for nm, m in V.items():
    e = ACT - m[IDX]; b = np.polyfit((m[IDX] - MM)[mm], (ACT - MM)[mm], 1)[0]
    cells = []
    for thr in (0.05, 0.08, 0.10):
        Rr = roi(m, thr, EV3); pos = sum(1 for s in EV3 if len(Rr[Rr.season == s]) and Rr[Rr.season == s].p.mean() > 0)
        cells.append(f'≥{thr*100:.0f}%: {Rr.p.mean()*100:+.1f}% ({len(Rr)}) {pos}/{len(EV3)}')
    per = ' '.join(f'{s}:{np.sqrt(np.mean(e[SE == s] ** 2)):.2f}' for s in EV3)
    P(f'  {nm:32s} RMSE {np.sqrt(np.mean(e[mm] ** 2)):.2f} ({per}) · b {b:+.3f} | ' + ' | '.join(cells))
open('nba_raptor_oracle_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
