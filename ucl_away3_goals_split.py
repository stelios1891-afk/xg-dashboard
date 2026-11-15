"""ucl_away3_goals_split.py — 16/10/2026 (Στελιος: «η εξτρα κουραση του 3ου συνεχομενου εκτος πως επηρεαζει τα γκολ; τρωει πιο πολλα; βαζει
λιγοτερα; το over γινεται καλυτερο ή χειροτερο;»). Πανω στις γραμμες ομαδας-ματς του ucl_away_streak_deep (ιδιο ημερολογιο, Crown/SBOBET κλεισιμο):
γκολ που ΒΑΖΕΙ / ΤΡΩΕΙ η ομαδα − αναμενομενα της αγορας (απο υπεροχη & συνολο κλεισιματος) = (Σ−αγ ± διαφορα−αγ)/2, + ανα σεζον, + xG."""
import sys, os
_s = open('ucl_away_streak_deep.py', encoding='utf-8').read(); _s = _s[:_s.index("SEAS = ['2122'")]
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
SEAS = ['2122', '2223', '2324', '2425', '2526']
E['sf'] = (E.rt + E.rc) / 2; E['sa'] = (E.rt - E.rc) / 2
U = E[(E.comp == 'ChampionsLeague') & E.ok]
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '—'
print('CHAMPIONS LEAGUE 2122-2526 · ομαδα-ματς · + = περισσοτερα γκολ απ οσα περιμενε η αγορα στο κλεισιμο')
print(f'   {"ομαδα":34s} {"n":>4s} │ {"ΒΑΖΕΙ − αγορα":>13s} │ {"ΤΡΩΕΙ − αγορα":>13s} │ {"συνολο − αγορα":>14s} │ {"διαφορα − αγορα":>15s} │ ανα σεζον (βαζει / τρωει)')
for lab, m in (('εκτος, 1ο (προηγ. εντος) [βαση]', (U.s == -1) & (U.streak == 1)), ('εκτος, 2ο συνεχομενο', (U.s == -1) & (U.streak == 2)),
               ('ΕΚΤΟΣ 3ο+ συνεχομενο', (U.s == -1) & (U.streak >= 3)), ('   …και ξεκουραση ≤3.5 μερες', (U.s == -1) & (U.streak >= 3) & (U.rest <= 3.5)),
               ('ο ΓΗΠΕΔΟΥΧΟΣ απεναντι σε 3ο+ εκτος', (U.s == 1) & (U.o_streak >= 3))):
    y = U[m]
    print(f'   {lab:34s} {len(y):4d} │ {ms(y.sf):>13s} │ {ms(y.sa):>13s} │ {ms(y.rt):>14s} │ {ms(y.rc):>15s} │ ' +
          ' '.join(f'{s[2:]}: {y[y.sea == s].sf.mean():+.2f}/{y[y.sea == s].sa.mean():+.2f}' for s in SEAS if (y.sea == s).sum()))
y = U[(U.s == -1) & (U.streak >= 3)]
print(f'\n   3ο+ εκτος — xG διαφορα − μοντελο {ms(y.rx)} · xG διαφορα − αγορα {ms(y.rxm)} · (n με xG {y.rx.notna().sum()})')
