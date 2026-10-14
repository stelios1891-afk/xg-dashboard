"""euro_transfer_mechanism.py — 14/10/2026 (Στελιος: «η δυναμη ομαδας ειναι αυτη που ειναι — πως μετραμε ΛΟΓΙΚΑ ποσο μεταφερεται; στη διαφορα
επιπεδου ισως κατι πιο ΑΤΟΜΙΚΟ ανα ομαδα αντι για το συνολο πρωταθληματος — π.χ. η καλυτερη της Ελλαδας/Σερβιας/Ουγγαριας vs 6η-7η Ισπανιας/Ιταλιας»).
Κατηγορια Α, 4 σεζον, Poisson με OFFSET = log live λ (0 = η live προβλεψη σωστη), στοχος xG (και γκολ):
 1) ΤΟ ΣΕΝΑΡΙΟ: ΚΟΡΥΦΑΙΑ μη-top5 (δυναμη στο πανω 25% των ευρωπαιων μη-top5) vs ΜΕΤΡΙΑ top-5 (δυναμη ≤ διαμεσου των top-5) — μοντελο vs xG vs γκολ
 2) ΑΤΟΜΙΚΟ ΜΕΤΡΟ ανα ομαδα: ln(αξια ενδεκαδας γηπ / φιλ) — εξηγει κατι που το μοντελο δεν εχει; και «απορροφα» το τεντωμα;
 3) τεντωμα δυναμης ομαδας ανα ΕΠΙΠΕΔΟ (κορυφαια της λιγκας της vs μεσαια) — ειναι το τεντωμα μονο στις κορυφαιες μικρων λιγκων;
"""
import sys, os, glob, json, pickle
_TOUT = sys.stdout
exec(open('euro_stretch_home_source.py', encoding='utf-8').read().split("print('ΚΑΤΗΓΟΡΙΑ Α — ποσο ΑΚΟΜΑ")[0])
sys.stdout = _TOUT
XA = pickle.load(open('euro_xi_abs.pkl', 'rb'))
A['V'] = [np.log(XA[m][0] / XA[m][1]) if m in XA else np.nan for m in A.mid]
A['top5h'] = A.lgh.isin(TOP5); A['top5a'] = A.lga.isin(TOP5)
def design5(df, target, extra=()):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        yh, ya = (r.gh, r.ga) if target == 'γκολ' else (r.xh, r.xa)
        for y, lam, sgn in ((yh, r.lh, 1), (ya, r.la, -1)):
            x = {'t': sgn * (r.th - r.ta) / 2, 'D': sgn * r.D, 'home': sgn / 2}
            for e in extra: x[e] = sgn * getattr(r, e) / 2
            rows.append(x); ys.append(y); offs.append(np.log(lam))
    return pd.DataFrame(rows), np.array(ys, float), np.array(offs)
fmt = lambda r, k: f'{r[k][0]:+.2f}±{r[k][1]:.2f}'
NL = chr(10)
# ---- 1 σεναριο
nt = pd.concat([A.loc[~A.top5h, 'th'], A.loc[~A.top5a, 'ta']]); tt = pd.concat([A.loc[A.top5h, 'th'], A.loc[A.top5a, 'ta']])
q75, q50 = nt.quantile(.75), tt.median()
SCN = []
print(f'1) ΣΕΝΑΡΙΟ: κορυφαια μη-top5 (δυναμη ≥{q75:.2f} στη λιγκα της) vs μετρια top-5 (δυναμη ≤{q50:.2f}) — απο τη σκοπια της μη-top5')
for cm, lab in ((('EuropaLeague', 'ConferenceLeague'), 'EUROPA + CONFERENCE'), (('ChampionsLeague',), 'CHAMPIONS')):
    S = []
    for r in A[A.comp.isin(cm)].itertuples():
        for sg, tn, lgn, to, lgo in ((1, r.th, r.lgh, r.ta, r.lga), (-1, r.ta, r.lga, r.th, r.lgh)):
            if lgn not in TOP5 and tn >= q75 and lgo in TOP5 and to <= q50:
                SCN.append((r.mid, sg)); S.append(dict(home=sg == 1, mdl=sg * (r.lh - r.la), xg=sg * (r.xh - r.xa), gd=sg * (r.gh - r.ga), t=sg * (r.th - r.ta) / 2 * 2, D=sg * r.D))
    S = pd.DataFrame(S)
    if len(S) < 5: print(f'   {lab}: n{len(S)} (λιγα)'); continue
    print(f'   {lab}: n{len(S)} (εντος {S.home.sum()}) · μοντελο {S.mdl.mean():+.2f} · xG {S.xg.mean():+.2f} · γκολ {S.gd.mean():+.2f} → μοντελο − xG {(S.mdl - S.xg).mean():+.2f} ±{(S.mdl - S.xg).std() / np.sqrt(len(S)):.2f}'
          f' · (δυναμη ομαδας {S.t.mean():+.2f} · διαφορα λιγκας {S.D.mean():+.2f})')
pickle.dump(SCN, open('euro_scenario_mids.pkl', 'wb'))
# ---- 2 ατομικο μετρο
print(NL + '2) ΑΤΟΜΙΚΟ ΜΕΤΡΟ: αξια ενδεκαδας (ln λογος) μεσα στο ιδιο μοντελο — συντελεστης >0 = πληροφορια που το μοντελο ΔΕΝ εχει')
for cm, lab in ((('EuropaLeague',), 'EUROPA'), (('ConferenceLeague',), 'CONFERENCE'), (('ChampionsLeague',), 'CHAMPIONS')):
    x = A[A.comp.isin(cm) & A.V.notna()]
    for tg in ('xG', 'γκολ'):
        r0 = poisson(*design5(x, tg)); r1 = poisson(*design5(x, tg, ('V',)))
        print(f'   {lab:10s} n{len(x):4d} {tg:4s} · ΧΩΡΙΣ αξια: ομαδα {fmt(r0, "t")} λιγκα {fmt(r0, "D")} │ ΜΕ αξια: ομαδα {fmt(r1, "t")} λιγκα {fmt(r1, "D")} · ΑΞΙΑ ΕΝΔΕΚΑΔΑΣ {fmt(r1, "V")}')
# ---- 3 τεντωμα ανα επιπεδο ομαδας
print(NL + '3) ΤΕΝΤΩΜΑ «δυναμης ομαδας» ανα ΤΥΠΟ ΖΕΥΓΑΡΙΟΥ (xG · Europa + Conference) — 0 = σωστο')
U = A[A.comp.isin(['EuropaLeague', 'ConferenceLeague'])]
kinds = np.where(U.top5h & U.top5a, 'top5 vs top5', np.where(~U.top5h & ~U.top5a, 'μη-top5 vs μη-top5', 'top5 vs μη-top5'))
for k in ('top5 vs top5', 'top5 vs μη-top5', 'μη-top5 vs μη-top5'):
    x = U[kinds == k]
    if len(x) < 40: print(f'   {k:20s} n{len(x)} (λιγα)'); continue
    r = poisson(*design5(x, 'xG'))
    print(f'   {k:20s} n{len(x):4d} · δυναμη ομαδας {fmt(r, "t")} · διαφορα λιγκας {fmt(r, "D")}')
hi = (U.th + U.ta) / 2
for lab, m_ in (('και οι 2 ομαδες ΚΟΡΥΦΑΙΕΣ των λιγκων τους (μεσος ≥ διαμεσου)', hi >= hi.median()), ('πιο μεσαιες ομαδες', hi < hi.median())):
    r = poisson(*design5(U[m_], 'xG'))
    print(f'   {lab:62s} n{m_.sum():4d} · δυναμη ομαδας {fmt(r, "t")} · διαφορα λιγκας {fmt(r, "D")}')
