"""uecl_mechanism.py — 12/10/2026 (Στελιος: «γιατι υποτιμαμε τα γκολ στην Α; ποιος μηχανισμος; ειδαμε κατι παρομοιο στο UCL; πως γινεται οι ομαδες FotMob
να βαζουν περισσοτερα στην Α και λιγοτερα στη Β — αντιφατικο; εχει να κανει με rotation;»).
Χωριζω το λαθος καθε πλευρας σε δυο κομματια: ΔΗΜΙΟΥΡΓΙΑ = xG − μοντελο (φτιαχνει περισσοτερες φασεις απ οσες λεμε;) και
ΦΙΝΙΡΙΣΜΑ = γκολ − xG (τις βαζει;). Μοντελο = ζευγος συνολων (W2, οπως στα over/under). 4 σεζον, κλεισιμο Crown/SBOBET για την αγορα.
  1) ανα διοργανωση (UCL / UEL / UECL) × κατηγορια: πλευρα ΜΕ FotMob και πλευρα ΧΩΡΙΣ
  2) UECL Α: που ειναι το εξτρα γκολ (διαφορα δυναμης, φαση, σεζον, εντος/εκτος, top-5)
  3) ROTATION (νεα μορφη, ενδεκαδες FotMob): οταν η ομαδα ΜΕ FotMob κανει rotation (αξια ενδεκαδας ≤85% της εγχωριας) vs πληρης ενδεκαδα
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
NL = chr(10)
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
S['day'] = [pd.Timestamp(KO.get(MIDS[i], 0), unit='s').strftime('%Y-%m-%d') for i in S.i]
S['lg'] = [V6['lg_h' if v == 'εντος' else 'lg_a'][VI[str(MIDS[i])]] for i, v in zip(S.i, S.venue)]
S['cr'] = S.xg - S.lou; S['fn'] = S.g - S.xg; S['tot_err'] = S.g - S.lou
def line(x, lab, w=34):
    if len(x) < 15: return f'   {lab:{w}s} n{len(x):4d} (λιγα)'
    return (f'   {lab:{w}s} n{len(x):4d} · γκολ {x.g.mean():.2f} · xG {x.xg.mean():.2f} · μοντελο {x.lou.mean():.2f} · αγορα {x.k.mean():.2f} · '
            f'ΔΗΜΙΟΥΡΓΙΑ {x.cr.mean():+.2f}±{se(x.cr):.2f} · ΦΙΝΙΡΙΣΜΑ {x.fn.mean():+.2f}±{se(x.fn):.2f}')
print('1. ΑΝΑ ΔΙΟΡΓΑΝΩΣΗ — ΔΗΜΙΟΥΡΓΙΑ (xG − μοντελο) και ΦΙΝΙΡΙΣΜΑ (γκολ − xG), γκολ που ΒΑΖΕΙ καθε πλευρα')
for cm in ('UCL', 'UEL', 'UECL'):
    x = S[S.comp == cm]
    print(f'   --- {cm} ---')
    print(line(x[x['cat'] == 'Α'], 'Α · ομαδες FotMob (και οι 2)'))
    print(line(x[(x['cat'] == 'Β') & (x.src == 'FotMob')], 'Β · η ομαδα ΜΕ FotMob'))
    print(line(x[(x['cat'] == 'Β') & (x.src != 'FotMob')], 'Β · η ομαδα ΧΩΡΙΣ FotMob'))
    print(line(x[x['cat'] == 'Γ'], 'Γ · ομαδες χωρις FotMob'))
# ===== 2 =====
print(NL + '2. CONFERENCE Α — που βρισκεται το εξτρα γκολ (ανα πλευρα)')
U = S[(S.comp == 'UECL') & (S['cat'] == 'Α')].copy()
mm = {i: abs(x[x.venue == 'εντος'].lou.iloc[0] - x[x.venue == 'εκτος'].lou.iloc[0]) for i, x in U.groupby('i')}
U['gap'] = U.i.map(mm); U['fav'] = [x.lou >= (U[(U.i == x.i) & (U.venue != x.venue)].lou.iloc[0]) for x in U.itertuples()]
for lab, m_ in (('φαβορι (μοντελου)', U.fav), ('αουτσαιντερ', ~U.fav), ('εντος', U.venue == 'εντος'), ('εκτος', U.venue == 'εκτος'),
                ('ισορροπημενα (διαφορα <0.4)', U.gap < .4), ('μετρια (0.4-0.9)', U.gap.between(.4, .9)), ('μεγαλη διαφορα (>0.9)', U.gap > .9),
                ('φαση λιγκας', U.ph == 'league'), ('νοκ-αουτ', U.ph == 'KO'), ('ομαδα top-5', U.lg.isin(TOP5)), ('ομαδα αλλης λιγκας', ~U.lg.isin(TOP5))):
    print(line(U[m_], lab))
for s_, x in U.groupby('sea'): print(line(x, f'σεζον {s_}'))
# ===== 3 =====
print(NL + '3. ROTATION (νεα μορφη 2425-2526) — η ομαδα ΜΕ FotMob με rotation (≤85%) ή πληρη ενδεκαδα')
RT = pd.read_pickle('euro_rotation_rows.pkl'); RT['day'] = pd.to_datetime(RT.ko).dt.strftime('%Y-%m-%d')
RT = RT.drop_duplicates(['team', 'day'])
X = S[S.sea.isin(['2425', '2526']) & (S.src == 'FotMob')].merge(RT[['team', 'day', 'ratio', 'rot']], on=['team', 'day'], how='left')
print(f'   ομαδες FotMob νεας μορφης: {len(X)} · με ενδεκαδα: {X.ratio.notna().sum()}')
for cm in ('UECL', 'UEL', 'UCL'):
    for c in ('Α', 'Β'):
        x = X[(X.comp == cm) & (X['cat'] == c) & X.ratio.notna()]
        if len(x) < 15: continue
        print(f'   {cm} κατηγορια {c}:')
        print(line(x[x.rot == True], '   rotation (≤85%)'))
        print(line(x[x.rot == False], '   πληρης ενδεκαδα'))
# και ο αντιπαλος: τα γκολ που ΤΡΩΕΙ η ομαδα FotMob οταν κανει rotation (αμυνα)
print('   ΑΜΥΝΑ — γκολ που τρωει η ομαδα ΜΕ FotMob (σκοπια αντιπαλου), Conference νεας μορφης:')
Y = X[(X.comp == 'UECL') & X.ratio.notna()].copy()
O = S.loc[[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')] for r in Y.itertuples()]].reset_index(drop=True)
O['rot'] = Y.rot.values; O['cat2'] = Y['cat'].values
for c in ('Α', 'Β'):
    for rv, rl in ((True, 'rotation'), (False, 'πληρης')):
        print(line(O[(O.cat2 == c) & (O.rot == rv)], f'   κατηγορια {c} · {rl}'))
