"""
intl_xg_team_windows.py — xG επιθεσης/αμυνας ομαδων με ΔΙΑΦΟΡΕΤΙΚΟ πληθος ματς N (26/9/2026, Στελιος: «να δουμε αν 8 ή 20 ματς δουλευουν καλυτερα, οχι μονο ROI
αλλα και προβλεψη»). Ιδια μεθοδος με intl_xg_totals (μονο αγωνιστικα ματς με xG· διορθωση αντιπαλου· shrink K=8 προς τον μεσο· εδρα 1.15).
Εξοδος: intl_xg_teamN{N}.csv (mid, xgsum = λ_h+λ_a, n = λιγοτερα ματς ιστορικου απο τις 2 ομαδες) για N ∈ {6, 8, 12, 16, 20}.
"""
import sys, collections, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
MU = float(pd.concat([M[M.has_xg].xg_h, M[M.has_xg].xg_a]).mean()); K = 8; HF = 1.15
for N in (6, 8, 12, 16, 20):
    hist = collections.defaultdict(list); rows = []
    def rating(t):
        h = hist[t][-N:]; n = len(h)
        if n == 0: return MU, MU, 0
        w = n / (n + K); return w * np.mean([x[0] for x in h]) + (1 - w) * MU, w * np.mean([x[1] for x in h]) + (1 - w) * MU, n
    for r in M.itertuples():
        ah, dh, nh = rating(r.hid); aa, da, na = rating(r.aid); hf = 1.0 if r.neutral else HF
        lh = MU * (ah / MU) * (da / MU) * hf; la = MU * (aa / MU) * (dh / MU) / hf
        rows.append((r.mid, lh + la, min(nh, na)))
        if r.has_xg and pd.notna(r.xg_h):
            hist[r.hid].append((float(r.xg_h) / (da / MU), float(r.xg_a) / (aa / MU))); hist[r.aid].append((float(r.xg_a) / (dh / MU), float(r.xg_h) / (ah / MU)))
    pd.DataFrame(rows, columns=['mid', 'xgsum', 'n']).to_csv(f'intl_xg_teamN{N}.csv', index=False)
    print(f'N={N}: {len(rows)} ματς')
