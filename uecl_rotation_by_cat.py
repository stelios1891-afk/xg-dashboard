"""uecl_rotation_by_cat.py — 12/10/2026 (Στελιος: «ποσο rotation κανουν οι ομαδες FotMob οταν παιζουν με ομαδα Β σε σχεση με οταν παιζουν με ομαδα Α;»).
Νεα μορφη 2425-2526 (ενδεκαδες FotMob, euro_rotation_rows: αξια βασικων / διαμεσος αξιας βασικων στα 5 τελευταια εγχωρια · rotation = ≤85% ·
αλλαγες = ποσοι απο τους 11 «βασικους» λειπουν). Ανα διοργανωση, κατηγορια, φαβορι/αουτσαιντερ, φαση· + ιδιες ομαδες και στις 2 κατηγοριες.
+ φινιρισμα (γκολ − xG) ανα ομαδα rotation/πληρης στη Β.
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
S['day'] = [pd.Timestamp(KO.get(MIDS[i], 0), unit='s').strftime('%Y-%m-%d') for i in S.i]
S['fav'] = [r.lam >= S.loc[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')], 'lam'] for r in S.itertuples()]
RT = pd.read_pickle('euro_rotation_rows.pkl'); RT['day'] = pd.to_datetime(RT.ko).dt.strftime('%Y-%m-%d'); RT = RT.drop_duplicates(['team', 'day'])
X = S[S.sea.isin(['2425', '2526']) & (S.src == 'FotMob') & S['cat'].isin(['Α', 'Β'])].merge(RT[['team', 'day', 'ratio', 'ch', 'rot']], on=['team', 'day'], how='inner')
def line(x, lab, w=36):
    if len(x) < 8: return f'   {lab:{w}s} n{len(x):3d} (λιγα)'
    return (f'   {lab:{w}s} n{len(x):3d} · rotation (≤85%) {100 * x.rot.mean():3.0f}% · αξια ενδεκαδας {100 * x.ratio.mean():3.0f}% της εγχωριας · '
            f'αλλαγες {x.ch.mean():.1f}/11 · φινιρισμα {(x.g - x.xg).mean():+.2f}')
for cm in ('UECL', 'UEL', 'UCL'):
    x = X[X.comp == cm]
    print(f'\n===== {cm} (νεα μορφη, ομαδες ΜΕ FotMob με γνωστη ενδεκαδα) =====')
    for c in ('Α', 'Β'):
        y = x[x['cat'] == c]
        print(line(y, f'απεναντι σε ομαδα {"Α (με FotMob)" if c == "Α" else "Β (χωρις FotMob)"}'))
        for fv, fl in ((True, '   ως φαβορι'), (False, '   ως αουτσαιντερ')): print(line(y[y.fav == fv], fl))
        for ph in ('league', 'KO'): print(line(y[y.ph == ph], f'   φαση {"λιγκας" if ph == "league" else "νοκ-αουτ"}'))
    both = set(x[x['cat'] == 'Α'].team) & set(x[x['cat'] == 'Β'].team)
    print(f'   ΙΔΙΕΣ ομαδες ({len(both)}) και στις δυο:')
    for c in ('Α', 'Β'): print(line(x[(x['cat'] == c) & x.team.isin(both)], f'   απεναντι σε {c}'))
