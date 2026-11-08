"""euro_league_diff_by_comp.py — 14/10/2026 (Στελιος: «μηπως η διαφορα λιγκας δεν ειναι σωστη για το Europa ή δεν εφαρμοζεται σωστα; γιατι στο
Champions League η αντιστοιχη ομαδα απο Ελλαδα/Κροατια/Τσεχια μεταφραζεται πιο σωστα;»).
Πανω στις πλευρες του euro_league_team_history (ολα τα ευρωπαικα 2223-2526, live λ). Λαθος = πραγματικο − μοντελο (γκολ) απο τη σκοπια της ομαδας.
 1) ομαδες εκτος top-5 ανα ΔΙΟΡΓΑΝΩΣΗ: μεσο λαθος, χωρισμενο σε αντιπαλο top-5 (εκει μετραει πολυ η διαφορα λιγκας) / αντιπαλο εκτος top-5
 2) ΑΠΟΣΥΝΘΕΣΗ ανα διοργανωση: λαθος = a + bD·(διαφορα λιγκας) + bt·(δυναμη ομαδας) + bo·(δυναμη αντιπαλου)
    bD < 0 → το μοντελο δινει ΠΑΡΑΠΑΝΩ πλεονεκτημα λιγκας απ' οσο αξιζει · bt < 0 → η εγχωρια δυναμη μεταφερεται λιγοτερο
 3) οι «βαριες» λιγκες (Ελλαδα, Κροατια, Τσεχια, Σερβια, Τουρκια, Ουκρανια, Σκωτια, Αυστρια) ανα διοργανωση: ποιος αντιπαλος, ποσο λαθος
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_league_team_history_rows.pkl')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
HEAVY = {'GreeceSL', 'CroatiaHNL', 'CzechFirstLeague', 'SerbiaSuperLiga', 'TurkishSuperLig', 'UkrainePremierLeague', 'ScottishPrem', 'AustrianBundesliga'}
X['top5'] = X.lg.isin(TOP5); X['opp5'] = X.opp_lg.isin(TOP5)
se = lambda v: v.dropna().std() / np.sqrt(max(v.notna().sum(), 1))
CM = (('ChampionsLeague', 'CHAMPIONS'), ('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'))
def cell(x):
    if len(x) < 15: return f'n{len(x):4d} (λιγα)'
    return (f'n{len(x):4d} · μοντελο {x.mdl.mean():+.2f} → λαθος γκολ {x.r.mean():+.2f}±{se(x.r):.2f} · xG-ισοπ. {x.rl.mean():+.2f}±{se(x.rl):.2f} · '
            f'ΑΓΟΡΑ {x.rk.mean():+.2f}±{se(x.rk):.2f}')
print('1) ΟΜΑΔΕΣ ΕΚΤΟΣ TOP-5 — μεσο λαθος (+ = τις υποτιμαμε · − = τις υπερτιμαμε)')
for cm, lab in CM:
    x = X[(X.comp == cm) & ~X.top5]
    print(f'   {lab}')
    print(f'      vs αντιπαλο TOP-5       {cell(x[x.opp5])}')
    print(f'      vs αντιπαλο εκτος top-5 {cell(x[~x.opp5])}')
def ols(x, cols):
    y = x.dropna(subset=['r'] + cols)
    A = np.c_[np.ones(len(y))] if not cols else np.c_[np.ones(len(y)), y[cols].values]
    b, *_ = np.linalg.lstsq(A, y.r.values, rcond=None); e = y.r.values - A @ b
    sev = np.sqrt(np.diag(np.linalg.inv(A.T @ A) * (e @ e) / (len(y) - A.shape[1]))); return b, sev, len(y)
print('\n2) ΑΠΟΣΥΝΘΕΣΗ ΛΑΘΟΥΣ (γκολ) ανα διοργανωση — ολες οι πλευρες: λαθος = a + bD·D + bt·t_ομαδας + bo·t_αντιπαλου')
print('   (D = διαφορα επιπεδου λιγκας υπερ της ομαδας · t = δυναμη μεσα στη λιγκα της) · bD<0: υπερβολικο πλεονεκτημα λιγκας · bt<0: υπερβολικη μεταφορα εγχωριας δυναμης')
for cm, lab in CM + (('ALL', 'ΟΛΕΣ'),):
    x = X if cm == 'ALL' else X[X.comp == cm]
    b, s, n = ols(x, ['D', 't', 't_opp'])
    print(f'   {lab:10s} n{n:5d} · bD {b[1]:+.2f}±{s[1]:.2f} · bt {b[2]:+.2f}±{s[2]:.2f} · bo {b[3]:+.2f}±{s[3]:.2f}')
    xx = x[~x.top5]
    b, s, n = ols(xx, ['D', 't', 't_opp'])
    print(f'   {"":10s} μονο ομαδες εκτος top-5 n{n:5d} · bD {b[1]:+.2f}±{s[1]:.2f} · bt {b[2]:+.2f}±{s[2]:.2f} · bo {b[3]:+.2f}±{s[3]:.2f}')
print('\n3) «ΒΑΡΙΕΣ» ΛΙΓΚΕΣ (Ελλαδα, Κροατια, Τσεχια, Σερβια, Τουρκια, Ουκρανια, Σκωτια, Αυστρια) ανα διοργανωση')
for cm, lab in CM:
    x = X[(X.comp == cm) & X.lg.isin(HEAVY)]
    if len(x) == 0: continue
    print(f'   {lab:10s} {cell(x)} · δυναμη ομαδας {x.t.mean():+.2f} · αντιπαλος top-5 {100 * x.opp5.mean():.0f}% · διαφορα λιγκας {x.D.mean():+.2f}')
    for opp, m_ in (('vs top-5', x.opp5), ('vs εκτος top-5', ~x.opp5)):
        y = x[m_]
        if len(y) >= 15: print(f'      {opp:16s} {cell(y)} · δυναμη ομαδας {y.t.mean():+.2f} · αντιπαλου {y.t_opp.mean():+.2f} · διαφορα λιγκας {y.D.mean():+.2f}')
