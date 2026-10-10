"""euro_prev_venue_test.py — 10/10/2026 (Στελιος: «δεν εχουμε δει καθολου κουραση, ειναι το ιδιο να ερχεσαι απο ματς πρωταθληματος εκτος με το να ερχεσαι
εντος? ειναι το ιδιο το εκτος πρωταθλημα → εκτος τσαμπιονς λιγκ με το εντος → εντος?»).
Για καθε ευρωπαικο ματς (UCL/UEL/UECL 2223-2526) και καθε ομαδα: το ΤΕΛΕΥΤΑΙΟ εγχωριο ματς πριν (εντος/εκτος, μερες ξεκουρασης).
Αποτελεσμα: λαθος διαφορας γκολ (πραγματικη − μοντελο live χαντικαπ / − αγορα κλεισιματος), σκοπια ομαδας.
(Η ερευνα 28/8 εβλεπε το ΕΓΧΩΡΙΟ ματς πριν/μετα την Ευρωπη — εδω το ΙΔΙΟ το ευρωπαικο.)
ΠΡΟ-ΔΗΛΩΜΕΝΟ: μια κατασταση «μετραει» μονο αν το λαθος vs ΑΓΟΡΑ διαφερει απο το υπολοιπο δειγμα με |t| ≥2 ΚΑΙ ιδιο προσημο σε ≥3/4 σεζον
(αλλιως: η αγορα το ξερει ή ειναι θορυβος). Περιγραφικο — κανενας κανονας χωρις ξεχωριστο τεστ picks.
"""
import sys, os, glob, json, pickle, datetime as dt, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_team_hfa_rows.pkl'); X = X[np.isfinite(X.kgd)].copy()
V = pickle.load(open('euro_v6_preds.pkl', 'rb')); KO = {str(m): d for m, d in zip(V['mids'], V['date'])}
X['ko'] = X.mid.astype(str).map(KO)
SKIP = ('Europe', 'Friendlies', 'Nations', 'WC', 'EURO', 'AFCON', 'Copa', 'AsianCup', 'GoldCup', 'WorldCup', 'Brazil', 'MLS')
DOM = {}
for f in glob.glob('data_*.json'):
    key = os.path.basename(f)[5:-5]
    if key.startswith(SKIP): continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for m in d.values():
        try: ts = pd.Timestamp(dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC'))
        except Exception: continue
        DOM.setdefault(int(m['home']['id']), []).append((ts, 1)); DOM.setdefault(int(m['away']['id']), []).append((ts, 0))
for k in DOM: DOM[k].sort()
def prev(tid, ko):
    xs = [x for x in DOM.get(tid, []) if x[0] < ko - pd.Timedelta(hours=12)]
    if not xs: return None, None
    t, h = xs[-1]; days = (ko - t).total_seconds() / 86400
    return (h if days <= 8 else None), days
rows = []
for r in X.itertuples():
    if pd.isna(r.ko): continue
    for tid, is_home, sg in ((r.hid, True, 1), (r.aid, False, -1)):
        pv, days = prev(tid, r.ko)
        if pv is None: continue
        rows.append(dict(sea=r.sea, comp=r.comp, team=r.home if is_home else r.away, eu_home=is_home, prev_home=bool(pv), days=days,
                         res=sg * r.res, resk=sg * r.res_k))
T = pd.DataFrame(rows)
print(f'ομαδο-ματς με εγχωριο ματς ≤8 μερες πριν: {len(T)} · μερες ξεκουρασης: διαμεσος {T.days.median():.1f}')
def line(x, lab, rest=None):
    se = x.resk.std() / np.sqrt(len(x))
    tt = ''
    if rest is not None and len(rest) and len(x):
        d = x.resk.mean() - rest.resk.mean(); s2 = np.sqrt(x.resk.var() / len(x) + rest.resk.var() / len(rest)); tt = f' · vs υπολοιπα αγορα {d:+.2f} (t {d / s2:+.1f})'
    ps = x.groupby('sea').resk.mean()
    print(f'   {lab:44s} n{len(x):5d} · λαθος μοντελου {x.res.mean():+.2f} · λαθος ΑΓΟΡΑΣ {x.resk.mean():+.2f}±{se:.2f}{tt} · ανα σεζον αγορα ' +
          ' '.join(f'{s[2:]}:{v:+.2f}' for s, v in ps.items()))
print('\nΑ. ΠΡΟΗΓΟΥΜΕΝΟ ΕΓΧΩΡΙΟ ΕΝΤΟΣ vs ΕΚΤΟΣ (ολες οι διοργανωσεις)')
for lab, m in (('ηρθε απο ΕΝΤΟΣ εγχωριο', T.prev_home), ('ηρθε απο ΕΚΤΟΣ εγχωριο', ~T.prev_home)):
    line(T[m], lab, T[~m])
print('\nΒ. ΣΥΝΔΥΑΣΜΟΙ (προηγουμενο εγχωριο → ευρωπαικο)')
for a in (True, False):
    for b in (True, False):
        m = (T.prev_home == a) & (T.eu_home == b)
        line(T[m], f'{"εντος" if a else "εκτος"} πρωταθλημα → {"ΕΝΤΟΣ" if b else "ΕΚΤΟΣ"} Ευρωπη', T[(T.eu_home == b) & ~m])
print('   (συγκριση: καθε συνδυασμος vs ΤΟ ΙΔΙΟ γηπεδο στην Ευρωπη με το αλλο προηγουμενο)')
print('\nΓ. ΑΝΑ ΔΙΟΡΓΑΝΩΣΗ: «εκτος → εκτος» vs «εντος → εκτος» και «εκτος → εντος» vs «εντος → εντος»')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    t = T[T.comp == cm]
    for b in (False, True):
        a1 = t[(~t.prev_home) & (t.eu_home == b)]; a0 = t[(t.prev_home) & (t.eu_home == b)]
        line(a1, f'{cm[:8]} εκτος → {"ΕΝΤΟΣ" if b else "ΕΚΤΟΣ"}', a0)
print('\nΔ. ΜΕΡΕΣ ΞΕΚΟΥΡΑΣΗΣ (απο το εγχωριο ως το ευρωπαικο)')
for lo, hi in ((0, 3.0), (3.0, 3.6), (3.6, 4.6), (4.6, 8.1)):
    m = (T.days >= lo) & (T.days < hi)
    if m.sum() == 0: continue
    line(T[m], f'{lo:.1f}-{hi:.1f} μερες', T[~m])
