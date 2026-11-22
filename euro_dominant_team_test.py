"""euro_dominant_team_test.py — 10/10/2026 (Στελιος: «δες το ναι» — γιατι υποτιμαμε τη Bodø στην Ευρωπη).
euro_team_hfa_test/_eu_test: η Bodø υποτιμαται +0.96 γκολ διαφορα (42 ματς), η Νορβηγια χωρις Bodø +0.23±0.31 (θορυβος), Molde 0.00,
ημερολογιακες λιγκες συνολικα +0.11±0.12 → ΟΧΙ θεμα λιγκας/ημερολογιου. Υποθεση: ΚΥΡΙΑΡΧΕΣ ομαδες στο πρωταθλημα τους «συμπιεζονται»
απο το μοντελο (γνωστη συμπιεση υπεροχης) → υποτιμουνται στην Ευρωπη.
Προβλεπτης (γνωστος πριν τη σεζον): εγχωρια διαφορα γκολ ανα ματς της ομαδας, 12 μηνες πριν την 1η Αυγουστου της σεζον.
x = d_γηπ − d_φιλ · αποτελεσμα: λαθος διαφορας (πραγματικη − μοντελο / − αγορα) στο ευρωπαικο ματς.
ΠΡΟ-ΔΗΛΩΜΕΝΑ: Κ1 β>0, t≥2, LOSO β>0 σε ≥3/4 · Κ2 MAE εκτος δειγματος καλυτερο σε ≥3/4 · Κ3 αγορα δεν το εχει (β αγορας >0, t≥1.5).
"""
import sys, os, glob, json, datetime as dt, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_team_hfa_rows.pkl'); X = X[np.isfinite(X.kgd)].copy()
SKIP = ('Europe', 'Friendlies', 'Nations', 'WC', 'EURO', 'AFCON', 'Copa', 'AsianCup', 'GoldCup', 'WorldCup', 'Brazil', 'MLS')
DOM = {}
for f in glob.glob('data_*.json'):
    key = os.path.basename(f)[5:-5]
    if key.startswith(SKIP): continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for m in d.values():
        if m.get('hs') is None or m.get('as') is None: continue
        try: ts = dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC')
        except Exception: continue
        g = int(m['hs']) - int(m['as'])
        DOM.setdefault(int(m['home']['id']), []).append((ts, g, key))
        DOM.setdefault(int(m['away']['id']), []).append((ts, -g, key))
def dom(tid, sea):
    y = 2000 + int(sea[:2]); end = dt.datetime(y, 8, 1); start = end - dt.timedelta(days=365)
    g = [x[1] for x in DOM.get(tid, []) if start <= x[0] < end]
    return (np.mean(g) if len(g) >= 10 else np.nan), len(g)
DD = {}
for r in X.itertuples():
    for t in (r.hid, r.aid):
        if (t, r.sea) not in DD: DD[(t, r.sea)] = dom(t, r.sea)
X['dh'] = [DD[(r.hid, r.sea)][0] for r in X.itertuples()]; X['da'] = [DD[(r.aid, r.sea)][0] for r in X.itertuples()]
Y = X.dropna(subset=['dh', 'da']).copy(); Y['x'] = Y.dh - Y.da
print(f'ματς με εγχωρια δεδομενα και για τις 2 ομαδες: {len(Y)} · Bodø εγχωρια διαφορα/ματς: ' +
      ' '.join(f'{s}:{DD.get((t, s), (np.nan,))[0]:+.2f}' for s in ('2223', '2324', '2425', '2526') for t in {int(X[X.home.str.contains("Bod")].hid.iloc[0])}))
def ols(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x)
    return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
SEAS = ('2223', '2324', '2425', '2526')
for tgt, nm in (('res', 'λαθος ΜΟΝΤΕΛΟΥ'), ('res_k', 'λαθος ΑΓΟΡΑΣ')):
    b, se = ols(Y.x.values, Y[tgt].values); fold = []
    for s in SEAS:
        tr = Y[Y.sea != s]; te = Y[Y.sea == s]; bb, _ = ols(tr.x.values, tr[tgt].values)
        fold.append((s, bb, np.abs(te[tgt] - bb * te.x).mean() - np.abs(te[tgt]).mean()))
    print(f'{nm}: β = {b:+.3f} ± {se:.3f} (t {b / se:+.1f}) · LOSO β ' + ' '.join(f'{s}:{bb:+.3f}' for s, bb, _ in fold) +
          ' · ΔMAE εκτος δειγματος ' + ' '.join(f'{s}:{d:+.3f}' for s, _, d in fold))
# σκοπια ομαδας: ποσο κυριαρχη ηταν εγχωρια → λαθος στην Ευρωπη
rows = []
for r in Y.itertuples():
    rows.append(dict(team=r.home, d=r.dh, res=r.res, resk=r.res_k)); rows.append(dict(team=r.away, d=r.da, res=-r.res, resk=-r.res_k))
T = pd.DataFrame(rows)
print('\nΣΚΟΠΙΑ ΟΜΑΔΑΣ: εγχωρια διαφορα γκολ ανα ματς (περσι) → λαθος μοντελου / αγορας στην Ευρωπη')
for lo, hi in ((-9, 0), (0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 9)):
    t = T[(T.d >= lo) & (T.d < hi)]
    if len(t): print(f'   {lo:+.1f}…{hi:+.1f}: n{len(t):4d} · μοντελο {t.res.mean():+.2f}±{t.res.std() / np.sqrt(len(t)):.2f} · αγορα {t.resk.mean():+.2f}')
top = T[T.d >= 1.5].groupby('team').agg(n=('res', 'size'), d=('d', 'mean'), res=('res', 'mean'), resk=('resk', 'mean')).query('n >= 6').sort_values('res', ascending=False)
print('κυριαρχες ομαδες (εγχωρια ≥1.5/ματς, ≥6 ευρωπαικα): ομαδα · εγχωρια · λαθος μοντελου / αγορας')
for t, r in top.iterrows(): print(f'   {t[:22]:22s} n{r.n:3.0f} · {r.d:+.2f} · {r.res:+.2f} / {r.resk:+.2f}')
