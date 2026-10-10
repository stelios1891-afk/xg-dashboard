"""euro_team_hfa_eu_test.py — 10/10/2026 (Στελιος: «μηπως θα δουλευε καλυτερα ενα ιστορικο hfa?» — Bodø).
Συνεχεια του euro_team_hfa_test (εκει: η ΕΓΧΩΡΙΑ ιστορικη εδρα ΔΕΝ προβλεπει τιποτα, β ≈ 0· η Bodø δεν εχει εξτρα εδρα στη Νορβηγια).
ΕΔΩ: ιστορικο απο τα ΙΔΙΑ τα ευρωπαικα ματς της ομαδας, ΜΟΝΟ προηγουμενες σεζον (2122 απο τα δεδομενα ματς για το ιστορικο οπου υπαρχει).
Για καθε ομαδα πριν απο τη σεζον s: λαθος μοντελου (πραγματικη − μοντελο διαφορα, σκοπια ομαδας) εντος r_H, εκτος r_A
   «εξτρα εδρα» h = (r_H − r_A)/2 · «γενικη υποτιμηση» g = (r_H + r_A)/2 · συρρικνωση n/(n+6) (n = λιγοτερα απο εντος/εκτος).
Προβλεπτες για το ματς: x_h = h_γηπ + h_φιλ (η φιλοξενουμενη με μεγαλη εδρα ειναι χειροτερη εκτος) · x_g = g_γηπ − g_φιλ.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ιδια με euro_team_hfa_test): Κ1 β>0, t≥2, LOSO β>0 σε ≥3/4 · Κ2 MAE εκτος δειγματος καλυτερο σε ≥3/4 σεζον ·
   Κ3 η αγορα δεν το εχει (β αγορας >0, t≥1.5).
"""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_team_hfa_rows.pkl')
X = X[np.isfinite(X.kgd)].copy()
SEAS = ('2223', '2324', '2425', '2526')
K = 6.0
def hist(team, sea):
    p = X[X.sea < sea]
    rh = p[p.hid == team].res; ra = -p[p.aid == team].res
    n = min(len(rh), len(ra))
    if n == 0: return 0.0, 0.0, 0
    s = n / (n + K)
    return s * (rh.mean() - ra.mean()) / 2, s * (rh.mean() + ra.mean()) / 2, n
H = {}
for r in X.itertuples():
    for t in (r.hid, r.aid):
        if (t, r.sea) not in H: H[(t, r.sea)] = hist(t, r.sea)
X['xh'] = [H[(r.hid, r.sea)][0] + H[(r.aid, r.sea)][0] for r in X.itertuples()]
X['xg'] = [H[(r.hid, r.sea)][1] - H[(r.aid, r.sea)][1] for r in X.itertuples()]
X['n_min'] = [min(H[(r.hid, r.sea)][2], H[(r.aid, r.sea)][2]) for r in X.itertuples()]
Y = X[X.sea != '2223'].copy()          # 2223 δεν εχει προηγουμενες σεζον στο δειγμα
Y = Y[(Y.xh != 0) | (Y.xg != 0)]
print(f'ματς με ευρωπαικο ιστορικο (2324-2526): {len(Y)} · x_εδρας sd {Y.xh.std():.2f} · x_υποτιμησης sd {Y.xg.std():.2f}')
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
for lab, col in (('«ΕΞΤΡΑ ΕΔΡΑ» (x_h)', 'xh'), ('«ΓΕΝΙΚΗ ΥΠΟΤΙΜΗΣΗ» (x_g)', 'xg')):
    print(f'\n== {lab}')
    for tgt, nm in (('res', 'λαθος ΜΟΝΤΕΛΟΥ'), ('res_k', 'λαθος ΑΓΟΡΑΣ')):
        b, se = ols(Y[col].values, Y[tgt].values)
        fold = []
        for s in ('2324', '2425', '2526'):
            tr = Y[Y.sea != s]; te = Y[Y.sea == s]
            bb, _ = ols(tr[col].values, tr[tgt].values)
            fold.append((s, bb, np.abs(te[tgt] - bb * te[col]).mean() - np.abs(te[tgt]).mean()))
        print(f'   {nm}: β = {b:+.2f} ± {se:.2f} (t {b / se:+.1f}) · LOSO β ' + ' '.join(f'{s}:{bb:+.2f}' for s, bb, _ in fold) +
              ' · ΔMAE εκτος δειγματος ' + ' '.join(f'{s}:{d:+.3f}' for s, _, d in fold) + '  (αρνητικο = καλυτερα)')
    Y['q'] = pd.qcut(Y[col].rank(method='first'), 5, labels=False)
    for q, y in Y.groupby('q'):
        print(f'      x {y[col].min():+.2f}…{y[col].max():+.2f} n{len(y):4d} · λαθος μοντελου {y.res.mean():+.2f} · λαθος αγορας {y.res_k.mean():+.2f}')
b = Y[Y.home.str.contains('Bod')]
print(f'\nBodø εντος (2324-2526): n{len(b)} · x_εδρας {b.xh.mean():+.2f} · x_υποτιμησης {b.xg.mean():+.2f} · λαθος μοντελου {b.res.mean():+.2f} · αγορας {b.res_k.mean():+.2f}')
top = Y.groupby('home').agg(n=('res', 'size'), xh=('xh', 'mean'), res=('res', 'mean'), resk=('res_k', 'mean')).query('n >= 6').sort_values('xh', ascending=False)
print('ομαδες με τη μεγαλυτερη ιστορικη «εξτρα εδρα» (≥6 ματς εντος 2324-2526): ομαδα · x_h · λαθος μοντελου / αγορας εντος')
for t, r in top.head(8).iterrows():
    print(f'   {t[:22]:22s} n{r.n:2.0f} · x_h {r.xh:+.2f} · {r.res:+.2f} / {r.resk:+.2f}')
