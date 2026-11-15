"""uecl_nonfm_fav_check.py — 12/10/2026 (Στελιος: «απεναντι σε ποιες ομαδες ειναι φαβορι οι ομαδες χωρις FotMob — Α, Β ή Γ; πως γινεται να
υπερτιμαμε και την ομαδα FotMob και την ομαδα χωρις FotMob;»). Conference 4 σεζον.
  1) ποτε η ομαδα ΧΩΡΙΣ FotMob ειναι φαβορι (μοντελου / αγορας): απεναντι σε ομαδα FotMob (ματς Β) ή σε αλλη χωρις (Γ) · λιγκα του FotMob αντιπαλου
  2) η ιδια ομαδα χωρις FotMob κατα ΔΥΝΑΜΗ (κλιμακες της διαφορας που της δινει το μοντελο): πραγμ / xG / μοντελο / αγορα — ειναι το rating της
     πολυ «ακραιο»; (δυνατες → λιγοτερο δυνατες απ οσο λεμε, αδυναμες → λιγοτερο αδυναμες) + κλιση
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
X = S[(S.comp == 'UECL') & (S.src != 'FotMob')].copy()
O = S.loc[[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')] for r in X.itertuples()]].reset_index(drop=True)
X = X.reset_index(drop=True)
X['olam'], X['og'], X['oxg'], X['ok_'], X['osrc'] = O.lam.values, O.g.values, O.xg.values, O.k.values, O.src.values
X['olg'] = [V6['lg_h' if v == 'εκτος' else 'lg_a'][VI[str(MIDS[i])]] for i, v in zip(X.i, X.venue)]
X['m'] = X.lam - X.olam; X['km'] = X.k - X.ok_; X['y'] = X.g - X.og; X['yx'] = X.xg - X.oxg
X['opp'] = np.where(X.osrc == 'FotMob', 'Β (αντιπαλος ΜΕ FotMob)', 'Γ (αντιπαλος ΧΩΡΙΣ)')
print('1. ΟΜΑΔΕΣ ΧΩΡΙΣ FotMob — ποσο συχνα ειναι φαβορι και απεναντι σε ποιον (Conference, 4 σεζον)')
for lab, fav in (('φαβορι ΜΟΝΤΕΛΟΥ', X.m > 0), ('φαβορι ΑΓΟΡΑΣ', X.km > 0)):
    t = X[fav]; print(f'   {lab}: {len(t)} απο {len(X)} εμφανισεις ({100 * len(t) / len(X):.0f}%) → ' +
                       ' · '.join(f'{k}: {v} ({100 * v / len(t):.0f}%)' for k, v in t.opp.value_counts().items()))
t = X[(X.m > 0) & (X.osrc == 'FotMob')]
print(f'   οταν ειναι φαβορι μοντελου απεναντι σε ομαδα ΜΕ FotMob ({len(t)}), ο αντιπαλος ειναι απο: ' +
      ' · '.join(f'{k} {v}' for k, v in t.olg.value_counts().head(10).items()) + f' · top-5: {t.olg.isin(TOP5).sum()}')
for k, x in X.groupby('opp'):
    print(f'   {k:26s} εμφανισεις {len(x):3d} · φαβορι μοντελου {100 * (x.m > 0).mean():.0f}% · φαβορι αγορας {100 * (x.km > 0).mean():.0f}%')
print('\n2. Η ΟΜΑΔΑ ΧΩΡΙΣ FotMob ανα ΔΥΝΑΜΗ που της δινει το μοντελο (διαφορα απο τη δικη της σκοπια) — μονο ματς Β')
B = X[X.osrc == 'FotMob'].copy()
B['bin'] = pd.cut(B.m, [-9, -1.2, -0.6, -0.2, 0.2, 9], labels=['πολυ αδυναμη (<−1.2)', 'αδυναμη (−1.2…−0.6)', 'λιγο αδυναμη (−0.6…−0.2)', 'ισοδυναμη (±0.2)', 'ΦΑΒΟΡΙ (>+0.2)'])
for k, x in B.groupby('bin', observed=True):
    print(f'   {k:26s} n{len(x):3d} · διαφορα: μοντελο {x.m.mean():+.2f} · αγορα {x.km.mean():+.2f} · xG {x.yx.mean():+.2f} · ΠΡΑΓΜ {x.y.mean():+.2f} · '
          f'λαθος μοντελου {(x.y - x.m).mean():+.2f} (xG {(x.yx - x.m).mean():+.2f})')
b = np.polyfit(B.m, B.y - B.m, 1)[0]; bx = np.polyfit(B.m, B.yx - B.m, 1)[0]; bk = np.polyfit(B.km, B.y - B.km, 1)[0]
print(f'   ΚΛΙΣΗ λαθους ως προς τη διαφορα του μοντελου: γκολ {b:+.2f} · xG {bx:+.2f} (αρνητικη = η διαφορα ειναι φουσκωμενη· −0.30 ≈ s 0.70) · '
      f'ιδια κλιση για την ΑΓΟΡΑ {bk:+.2f}')
A_ = S[(S.comp == 'UECL') & (S['cat'] == 'Α')].copy()
OA_ = S.loc[[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')] for r in A_.itertuples()]]
ma = A_.lam.values - OA_.lam.values; ya = A_.g.values - OA_.g.values; yxa = A_.xg.values - OA_.xg.values
print(f'   (συγκριση, ματς Α: κλιση γκολ {np.polyfit(ma, ya - ma, 1)[0]:+.2f} · xG {np.polyfit(ma, yxa - ma, 1)[0]:+.2f})')
