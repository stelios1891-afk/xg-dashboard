"""
discipline_test.py — 5/10/2026 (Στελιος «τρεξε το 8»): ΠΕΙΘΑΡΧΙΑ — παιζουν χειροτερα απ' οσο λεει η αγορα οι ομαδες με κοκκινες;
Αφορμη: η παλια (λαθος) φορμουλα κοκκινων «τιμωρουσε» την ομαδα που αποβαλλοταν· μηπως επιανε κατι αληθινο;
CORE7, 2223-2526 (ιστορικο και απο 2122), τελικη γραμμη Pinnacle (core7_sos15_final: s_mkt = υπεροχη αγορας).
Υπολοιπο ομαδας = (διαφορα γκολ υπερ της) − (υπεροχη που της εδινε η αγορα). Αρνητικο = τα πηγε χειροτερα απο την αγορα.
Μετρα (μονο ΠΡΙΝ το ματς — καμια ματια στο μελλον):
  (1) κοκκινη στο ΑΜΕΣΩΣ προηγουμενο ματς της (πιθανη τιμωρια παικτη)  ·  (1β) ο ΑΝΤΙΠΑΛΟΣ ειχε κοκκινη στο προηγουμενο του
  (2) κοκκινες στα τελευταια 10 ματς (0 / 1 / 2 / 3+)  ·  (3) «επιρρεπεις» ομαδες: κοκκινες/ματς σεζον ως τωρα (με περσινο), κορυφαιο 20%
  + τυφλο ROI κοντρα (ή υπερ) στην ομαδα, Pinnacle κλεισιμο, ανα σεζον.
"""
import sys, io, contextlib, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read()
pre = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'disc'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, picks = g['D'], g['picks']
# ---- ιστορικο κοκκινων ανα ομαδα (ολα τα ματς λιγκας, χρονολογικα) ----
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
hist = {}; MREDS = {}
for lg in LG:
    for sea in ('2122', '2223', '2324', '2425', '2526'):
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for mid, m in d.items():
            if m.get('hs') is None: continue
            rh = sum(1 for r in (m.get('reds') or []) if r.get('home')); ra = sum(1 for r in (m.get('reds') or []) if not r.get('home'))
            MREDS[str(mid)] = (rh, ra)
            dt = pd.Timestamp(m['date'].replace(' UTC', ''))
            for nm, k in ((m['home']['name'], rh), (m['away']['name'], ra)):
                hist.setdefault((lg, nm), []).append((dt, sea, str(mid), k))
for k in hist: hist[k].sort()
def feats(lg, nm, mid):
    h = hist.get((lg, nm), [])
    idx = next((i for i, x in enumerate(h) if x[2] == mid), None)
    if idx is None or idx == 0: return None
    prev = h[idx - 1]; last10 = [x[3] for x in h[max(0, idx - 10):idx]]
    sea = h[idx][1]; cur = [x[3] for x in h[:idx] if x[1] == sea]; prv = [x[3] for x in h[:idx] if x[1] != sea][-34:]
    rate = (sum(cur) + sum(prv) * 0.5) / max(len(cur) + len(prv) * 0.5, 1)
    days = (h[idx][0] - prev[0]).days
    return dict(red_prev=int(prev[3] > 0), prev_recent=days <= 10, red10=sum(last10), rate=rate, n_cur=len(cur))
rows = []
for r in D[D.md >= 1].itertuples():
    if r.s_mkt != r.s_mkt: continue
    for side, nm, onm in ((1, r.h, r.a), (-1, r.a, r.h)):
        f = feats(r.league, nm, r.mid); fo = feats(r.league, onm, r.mid)
        if f is None or fo is None: continue
        L = r.L if side == 1 else -r.L; o = r.ah if side == 1 else r.aa
        rows.append(dict(season=r.season, league=r.league, home=side == 1, res=side * (r.gd - r.s_mkt),
                         pnl=picks.settle(r.gd, side, L, o) if (L == L and o == o) else np.nan,
                         **{k: v for k, v in f.items()}, opp_red_prev=fo['red_prev'], opp_rate=fo['rate']))
X = pd.DataFrame(rows)
thr = X.rate.quantile(0.8)
def st(d, lab):
    if len(d) < 40: return f'  {lab:46s} n{len(d):5d}'
    se = d.res.std() / np.sqrt(len(d)); ps = d.groupby('season').res.mean(); pr = d.groupby('season').pnl.mean()
    return (f'  {lab:46s} n{len(d):5d} · υπολοιπο {d.res.mean():+.3f} ±{se:.3f} (t {d.res.mean()/se:+.1f}) · σεζον αρνητικες {int((ps < 0).sum())}/{len(ps)}'
            f' · ROI ΥΠΕΡ της ομαδας {100*d.pnl.mean():+5.1f}% ({int((pr > 0).sum())}/{len(pr)})')
print(f'CORE7 2223-2526 · {len(X)} ομαδες-ματς (καθε ματς 2 φορες) · υπολοιπο σε γκολ (ομαδα − αγορα)')
print(st(X, 'ΟΛΑ (ελεγχος ≈ 0)'))
print('\n(1) ΚΟΚΚΙΝΗ ΣΤΟ ΠΡΟΗΓΟΥΜΕΝΟ ΜΑΤΣ (πιθανη τιμωρια)')
print(st(X[X.red_prev == 1], 'η ομαδα ειχε κοκκινη στο προηγουμενο'))
print(st(X[(X.red_prev == 1) & X.prev_recent], '   … και το προηγουμενο ηταν ≤10 μερες πριν'))
print(st(X[X.red_prev == 0], 'η ομαδα ΔΕΝ ειχε'))
print(st(X[X.opp_red_prev == 1], '(1β) ο ΑΝΤΙΠΑΛΟΣ ειχε κοκκινη στο προηγουμενο'))
print(st(X[(X.red_prev == 1) & X.home], '   ομαδα με κοκκινη, εντος'))
print(st(X[(X.red_prev == 1) & ~X.home], '   ομαδα με κοκκινη, εκτος'))
print('\n(2) ΚΟΚΚΙΝΕΣ ΣΤΑ ΤΕΛΕΥΤΑΙΑ 10 ΜΑΤΣ')
for lo, hi, lab in ((0, 1, '0'), (1, 2, '1'), (2, 3, '2'), (3, 99, '3+')):
    print(st(X[(X.red10 >= lo) & (X.red10 < hi)], f'{lab} κοκκινες'))
print(f'\n(3) «ΕΠΙΡΡΕΠΕΙΣ» ΟΜΑΔΕΣ (κοκκινες/ματς ≥ {thr:.3f}, κορυφαιο 20%)')
print(st(X[X.rate >= thr], 'επιρρεπεις'))
print(st(X[X.rate < thr], 'οι υπολοιπες'))
print(st(X[(X.rate >= thr) & (X.opp_rate < X.opp_rate.quantile(0.5))], 'επιρρεπεις vs «ησυχος» αντιπαλος'))
print('\nανα λιγκα (1) κοκκινη στο προηγουμενο: ' + ' · '.join(f'{lg}: {d.res.mean():+.2f} (n{len(d)})' for lg, d in X[X.red_prev == 1].groupby('league')))
print('ανα σεζον (1): ' + ' · '.join(f'{s}: {d.res.mean():+.3f} (n{len(d)})' for s, d in X[X.red_prev == 1].groupby('season')))
# παλινδρομηση: υπολοιπο ~ red_prev + red10 + rate
A = np.c_[np.ones(len(X)), X.red_prev, X.red10.clip(upper=4), X.rate]
b, *_ = np.linalg.lstsq(A, X.res.values, rcond=None); e = X.res.values - A @ b
se = np.sqrt(np.diag(np.linalg.inv(A.T @ A)) * (e @ e) / (len(X) - 4))
print('\nΠΑΛΙΝΔΡΟΜΗΣΗ υπολοιπο ~ κοκκινη_προηγ + κοκκινες_10 + ρυθμος: ' + ' · '.join(f'{n} {b[i]:+.3f} (t {b[i]/se[i]:+.1f})' for i, n in enumerate(['σταθερα', 'κοκκινη_προηγ', 'κοκκινες_10', 'ρυθμος'])))
