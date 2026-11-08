"""euro_rotation_predict_test.py — 10/10/2026 (Στελιος: «δες πρωτα αν η προβλεψη ροτεισον εξηγει τα λαθη»).
ΠΡΟΒΛΕΨΗ ROTATION (μονο πληροφορια ΠΡΙΝ το ματς), νεα μορφη 2425-2526:
  prior λιγκας×διοργανωσης = μεσο ln(αξια ενδεκαδας) της λιγκας σε αυτη τη διοργανωση στην ΑΛΛΗ σεζον (LOSO)
  συνηθεια ομαδας = μεσο ln(αξια ενδεκαδας) στα ΠΡΟΗΓΟΥΜΕΝΑ ευρωπαικα της ιδιας σεζον
  προβλεψη = (n_προηγ · συνηθεια + 2 · prior) / (n_προηγ + 2)          (ln αξιας: 0 = πληρης, −0.2 ≈ 82% αξια)
x = προβλεψη γηπεδουχου − προβλεψη φιλοξενουμενου (σκοπια γηπεδουχου). Αποτελεσμα: λαθος διαφορας (πραγματικη − μοντελο / − αγορα κλεισιματος).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (UEL + UECL, νεα μορφη): (α) κλιση λαθους ΜΟΝΤΕΛΟΥ ~ x >0 με t ≥2 ΚΑΙ ιδιο προσημο στις 2 σεζον ·
  (β) κλιση λαθους ΑΓΟΡΑΣ ~ x >0 με t ≥1.5 (η αγορα δεν το εχει → εκμεταλλευσιμο). + περιγραφικα: picks χαντικαπ ανα προβλεψη, UCL για συγκριση.
Πηγες: euro_rotation_rows.pkl (euro_rotation_teams), uel_vs_ucl_diag_rows.pkl (uel_vs_ucl_diag: μοντελο/αγορα, FotMob+FotMob).
"""
import sys, pickle, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NEW = ('2425', '2526')
T = pd.read_pickle('euro_rotation_rows.pkl').sort_values('ko').copy()
T['lr'] = np.log(T.ratio.clip(lower=0.3, upper=2.0))
# prior λιγκας×διοργανωσης απο την ΑΛΛΗ σεζον
PRI = {}
for sea in NEW:
    other = T[T.sea != sea]
    g = other.groupby(['lg', 'comp']).lr.agg(['mean', 'size'])
    comp_mean = other.groupby('comp').lr.mean()
    for (lg, cm), r in g.iterrows():
        PRI[(sea, lg, cm)] = (r['mean'] * r['size'] + comp_mean[cm] * 5) / (r['size'] + 5)    # λιγκες με λιγα ματς → προς τον μεσο της διοργανωσης
    for cm, v in comp_mean.items():
        PRI[(sea, '*', cm)] = v
pred = []
for (tm, sea), t in T.groupby(['team', 'sea']):
    t = t.sort_values('ko'); hist = []
    for r in t.itertuples():
        pr = PRI.get((sea, r.lg, r.comp), PRI.get((sea, '*', r.comp), 0.0))
        n = len(hist); hab = np.mean(hist) if hist else 0.0
        pred.append((r.Index, (n * hab + 2 * pr) / (n + 2), n))
        hist.append(r.lr)
P = pd.DataFrame(pred, columns=['idx', 'pred', 'nprev']).set_index('idx')
T = T.join(P)
print(f'ομαδο-ματς με προβλεψη: {len(T)} · συσχετιση προβλεψης ↔ πραγματικης αξιας ενδεκαδας (ln): ' +
      ' · '.join(f'{c[:6]} {np.corrcoef(t.pred, t.lr)[0, 1]:+.2f}' for c, t in T.groupby('comp')))
# ---- ενωση με μοντελο/αγορα ----
X = pd.read_pickle('uel_vs_ucl_diag_rows.pkl')
V6 = pickle.load(open('euro_v6_preds.pkl', 'rb'))
X['mid'] = [str(V6['mids'][i]) for i in X.i]; X['ko'] = [pd.Timestamp(V6['date'][i]) for i in X.i]
X = X[X.sea.isin(NEW)]
key = {(r.team, r.ko): r.pred for r in T.itertuples()}
X['ph'] = [key.get((r.home, r.ko), np.nan) for r in X.itertuples()]
X['pa'] = [key.get((r.away, r.ko), np.nan) for r in X.itertuples()]
X = X.dropna(subset=['ph', 'pa']).copy()
X['x'] = X.ph - X.pa
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
print('\nΛΑΘΟΣ ΔΙΑΦΟΡΑΣ ~ x (x>0: ο γηπεδουχος αναμενεται να κανει ΛΙΓΟΤΕΡΟ rotation απο τον φιλοξενουμενο) — κλιση σε γκολ ανα μοναδα ln αξιας')
res = {}
for lab, m in (('UEL+UECL', X.comp != 'ChampionsLeague'), ('UEL', X.comp == 'EuropaLeague'), ('UECL', X.comp == 'ConferenceLeague'), ('UCL', X.comp == 'ChampionsLeague')):
    x = X[m]
    bm, sm = ols(x.x.values, x.rm.values); bk, sk = ols(x.x.values, x.rk.values)
    seas = ' · '.join(f'{s[2:]}: μοντ {ols(y.x.values, y.rm.values)[0]:+.2f} αγορ {ols(y.x.values, y.rk.values)[0]:+.2f}' for s, y in x.groupby('sea'))
    res[lab] = (bm, sm, bk, sk, [ols(y.x.values, y.rm.values)[0] for s, y in x.groupby('sea')])
    print(f'   {lab:9s} n{len(x):4d} · sd x {x.x.std():.2f} · ΜΟΝΤΕΛΟ {bm:+.2f}±{sm:.2f} (t {bm / sm:+.1f}) · ΑΓΟΡΑ {bk:+.2f}±{sk:.2f} (t {bk / sk:+.1f}) · ανα σεζον: {seas}')
bm, sm, bk, sk, ps = res['UEL+UECL']
ka = bm > 0 and bm / sm >= 2 and all(v > 0 for v in ps); kb = bk > 0 and bk / sk >= 1.5
print(f'\n(α) εξηγει το λαθος του μοντελου: {"✓" if ka else "✗"} · (β) η αγορα δεν το εχει: {"✓" if kb else "✗"}')
print('\nΣΕ ΓΚΟΛ: x ανα κλιμακα (UEL+UECL) — λαθος μοντελου / αγορας (σκοπια γηπεδουχου)')
x = X[X.comp != 'ChampionsLeague']
for lo, hi, lb in ((-9, -0.08, 'ο γηπεδουχος πιο πιθανο rotation'), (-0.08, 0.08, 'ιδιο'), (0.08, 9, 'ο φιλοξενουμενος πιο πιθανο rotation')):
    y = x[(x.x >= lo) & (x.x < hi)]
    print(f'   {lb:38s} n{len(y):4d} · μοντελο {y.rm.mean():+.2f} · αγορα {y.rk.mean():+.2f}')
X.to_pickle('euro_rotation_pred_rows.pkl')
