"""euro_spread_check.py — 15/10/2026 (Στελιος: «βλεπεις στις ομαδες εκτος top-5 οτι εχουμε μεγαλες διαφορες στο μηχανισμο που υπολογιζουμε τη
διαφορα δυναμικοτητας;»). Πανω στις πλευρες του euro_league_team_history (ολα τα ευρωπαικα 2223-2526, live λ).
 1) ΠΟΣΟ «ΚΥΡΙΑΡΧΕΣ» φαινονται εγχωρια οι ομαδες που παιζουν Ευρωπη (δυναμη t πανω απο τον μεσο της λιγκας τους), ανα ομαδα λιγκων
 2) ΜΑΤΣ ανα ζευγαρι λιγκων: ποσο ΑΠΛΩΜΕΝΕΣ ειναι οι διαφορες του μοντελου vs της αγορας (τυπικη αποκλιση) και ποσο «αξιζει» 1 γκολ διαφορας
    του μοντελου στην αγορα / στα γκολ / στο xG ισοπαλιας (κλιση· 1 = ιδια κλιμακα, 0.5 = το μοντελο διπλασιαζει τις διαφορες)
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_league_team_history_rows.pkl')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
MIDT = {'PrimeiraLiga', 'Eredivisie', 'Belgium'}
grp = lambda lg: 'top-5' if lg in TOP5 else ('Πορτογ/Ολλ/Βελγ' if lg in MIDT else 'υπολοιπες')
X['g'] = X.lg.map(grp); X['og'] = X.opp_lg.map(grp)
print('1) ΕΓΧΩΡΙΑ ΚΥΡΙΑΡΧΙΑ των ομαδων που παιζουν Ευρωπη (t = ποσο πανω απο τον μεσο ορο της λιγκας τους · log-κλιμακα)')
for g in ('top-5', 'Πορτογ/Ολλ/Βελγ', 'υπολοιπες'):
    x = X[X.g == g].drop_duplicates(['lg', 'sea', 't'])
    print(f'   {g:16s} ομαδα-σεζον {len(x):4d} · μεση t {x.t.mean():+.2f} · εδρος (τυπ. αποκλιση) {x.t.std():.2f} · κορυφαιο 10% ≥ {x.t.quantile(.9):+.2f}')
H = X.drop_duplicates('mid')        # μια γραμμη ανα ματς (σκοπια γηπεδουχου)
def pair(r):
    a, b = sorted([r.g, r.og]); return f'{a} vs {b}'
H = H.assign(pair=H.apply(pair, axis=1))
def sl(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 20: return np.nan, np.nan
    b = np.polyfit(x[ok], y[ok], 1); e = y[ok] - np.polyval(b, x[ok])
    return b[0], np.sqrt((e ** 2).sum() / (ok.sum() - 2) / ((x[ok] - x[ok].mean()) ** 2).sum())
print('\n2) ΑΝΑ ΖΕΥΓΑΡΙ ΛΙΓΚΩΝ — τυπ. αποκλιση της διαφορας (μοντελο / αγορα) · «ποσο αξιζει 1 γκολ διαφορας του μοντελου»: στην αγορα / στα γκολ / στο xG ισοπαλιας')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague', None):
    print(f'   {cm or "ΟΛΕΣ"}')
    for p in ('top-5 vs top-5', 'top-5 vs υπολοιπες', 'Πορτογ/Ολλ/Βελγ vs υπολοιπες', 'υπολοιπες vs υπολοιπες'):
        x = H[(H.pair == p) & ((H.comp == cm) if cm else True)]
        if len(x) < 25: continue
        x = x[np.isfinite(x.mk)]
        bk, sk = sl(x.mdl.values, x.mk.values); bg, sg = sl(x.mdl.values, x.gd.values.astype(float)); bl, sl_ = sl(x.mdl.values, x.lvl.values)
        print(f'      {p:30s} n{len(x):4d} · απλωμα μοντελο {x.mdl.std():.2f} / αγορα {x.mk.std():.2f} · 1 γκολ μοντελου = αγορα {bk:.2f}±{sk:.2f} · '
              f'γκολ {bg:.2f}±{sg:.2f} · xG-ισοπ./90 {bl:.2f}±{sl_:.2f}')
