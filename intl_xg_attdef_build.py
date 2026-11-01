"""
intl_xg_attdef_build.py — xG ΕΠΙΘΕΣΗΣ/ΑΜΥΝΑΣ ανα εθνικη (τρεχουσα κατασταση) για το ΝΕΟ T των over (26/9/2026, αποφαση Στελιου).
Ιδια μεθοδος με το τεστ (intl_xg_totals / intl_xg_team_windows N=12): μονο αγωνιστικα ματς με xG (τα φιλικα δεν εχουν xG), 12 τελευταια,
διορθωση αντιπαλου, shrink K=8 προς τον μεσο, εδρα 1.15. Τρεχει σε καθε intl_refresh.
Εξοδος: intl_xg_attdef.json {tid: {att, dfn, n}, "_meta": {mu, N, K, hf, asof}}
"""
import sys, json, collections, datetime as dt, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
N, K, HF = 12, 8, 1.15
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
import intl_dedupe
M = intl_dedupe.dedupe(M, where='xg_attdef').sort_values('date').reset_index(drop=True)
MU = float(pd.concat([M[M.has_xg].xg_h, M[M.has_xg].xg_a]).mean())
hist = collections.defaultdict(list)
def rating(t):
    h = hist[t][-N:]; n = len(h)
    if n == 0: return MU, MU, 0
    w = n / (n + K); return w * np.mean([x[0] for x in h]) + (1 - w) * MU, w * np.mean([x[1] for x in h]) + (1 - w) * MU, n
for r in M[M.has_xg].itertuples():
    if pd.isna(r.xg_h): continue
    ah, dh, _ = rating(r.hid); aa, da, _ = rating(r.aid)
    hist[r.hid].append((float(r.xg_h) / (da / MU), float(r.xg_a) / (aa / MU))); hist[r.aid].append((float(r.xg_a) / (dh / MU), float(r.xg_h) / (ah / MU)))
out = {str(t): dict(zip(('att', 'dfn', 'n'), rating(t))) for t in hist}
out['_meta'] = dict(mu=MU, N=N, K=K, hf=HF, asof=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M'), last_match=str(M[M.has_xg].date.max())[:10])
json.dump(out, open('intl_xg_attdef.json', 'w', encoding='utf-8'))
print(f'intl_xg_attdef.json: {len(out) - 1} ομαδες · μ {MU:.3f} · τελευταιο ματς με xG {out["_meta"]["last_match"]}')
