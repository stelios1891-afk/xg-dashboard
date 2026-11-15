# -*- coding: utf-8 -*-
"""psg_deep_build.py — 19/10/2026 (Στελιος: «γιατι το ευρωπαικο μοντελο υποτιμα την Παρι στην Ευρωπη;»).
Χτιζει ΕΝΑ πινακα ομαδα-ανα-ματς (ευρωπαικα 2022-26, σημερινη αλυσιδα — ιδιο harness με psg_europe_residual / team_euro_decomp):
  γκολ, μοντελο (LH_N/LA_N), πραγματικα xG FotMob, λιγκα ομαδας/αντιπαλου (euro_v6_preds), φαση, ημερομηνια,
  αγορα κλεισιματος (διαφορα που δικαιολογει το χαντικαπ, μεσος Crown/SBOBET) + αποτελεσμα ποντας στο χαντικαπ της ομαδας (κλεισιμο, μεσος 2 βιβλιων).
Αποθηκευει psg_deep_rows.pkl για τα psg_deep_*.py. Κανενα live αρχειο δεν αλλαζει."""
import sys, os, json, glob, pickle
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
NM = {}; DT = {}; XG90 = {}; ET = set()
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        NM[str(mid)] = (m['home']['name'], m['away']['name']); DT[str(mid)] = m.get('date')
        sh = [s for s in (m.get('shots') or []) if s.get('xg') is not None]; hid = int(m['home']['id'])
        if sh:   # ΜΟΝΟ κανονικη διαρκεια (min ≤ 90 — οι καθυστερησεις ειναι 90 στο FotMob· >90 = παραταση/πεναλτι διαδικασιας)
            if max(s['min'] for s in sh) > 90: ET.add(str(mid))
            XG90[str(mid)] = (sum(s['xg'] for s in sh if s['min'] <= 90 and int(s['tid']) == hid), sum(s['xg'] for s in sh if s['min'] <= 90 and int(s['tid']) != hid))
V6 = pickle.load(open('euro_v6_preds.pkl', 'rb')); VI = {str(m): j for j, m in enumerate(V6['mids'])}
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -6.0, 6.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
R = []
for i, mid in enumerate(MIDS):
    mid = str(mid); h, a = NM.get(mid, (None, None))
    if h is None: continue
    j = VI.get(mid); lgh = V6['lg_h'][j] if j is not None else None; lga = V6['lg_a'][j] if j is not None else None
    ph = V6['phase'][j] if j is not None else None
    xg = XG90.get(mid)
    mk = []; pnl_h = []; pnl_a = []; lines = []
    for bk in ('Crown', 'SBOBET'):
        s = snap_ah(mid, bk, 0)
        if not s: continue
        L, oh, oa = s
        mk.append(implied_margin(i, L, oh, oa)); lines.append(L)
        pnl_h.append(picks.settle(GD[i], 1, L, oh)); pnl_a.append(picks.settle(GD[i], -1, -L, oa))
    kg = np.mean(mk) if mk else np.nan
    for side, tm, op in ((1, h, a), (-1, a, h)):
        H = side == 1
        R.append(dict(mid=mid, i=i, team=tm, opp=op, comp=COMP[i], sea=SEA[i], home=H, phase=ph, date=DT.get(mid),
                      lg=lgh if H else lga, olg=lga if H else lgh,
                      gf=GH[i] if H else GA[i], ga=GA[i] if H else GH[i],
                      mf=LH_N[i] if H else LA_N[i], ma=LA_N[i] if H else LH_N[i],
                      xf=(xg[0] if H else xg[1]) if xg else np.nan, xa=(xg[1] if H else xg[0]) if xg else np.nan,
                      kgd=side * kg, line=(np.mean(lines) * side) if lines else np.nan,
                      pnl=np.mean(pnl_h if H else pnl_a) if mk else np.nan, nbk=len(mk), et=mid in ET,
                      xf_old=(XG[mid][0] if H else XG[mid][1]) if mid in XG else np.nan))
D = pd.DataFrame(R)
D['gd'] = D.gf - D.ga; D['mgd'] = D.mf - D.ma; D['rd'] = D.gd - D.mgd
D.to_pickle('psg_deep_rows.pkl')
print(f'{len(D)} γραμμες ομαδα-ματς · {D.mid.nunique()} ματς · με xG {D.xf.notna().mean():.0%} · με αγορα {D.kgd.notna().mean():.0%}')
print(D.phase.value_counts().to_string()); print(f'ματς με παραταση/πεναλτι: {len(ET)} (το παλιο XG του uel_full_review μετρουσε και αυτα τα σουτ)')
print(D[D.team == 'Paris Saint-Germain'][['sea', 'comp', 'opp', 'home', 'phase', 'gf', 'ga', 'mf', 'ma', 'xf', 'xa', 'kgd', 'line', 'pnl']].round(2).to_string())
