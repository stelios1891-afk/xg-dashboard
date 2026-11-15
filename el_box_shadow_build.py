# -*- coding: utf-8 -*-
"""el_box_shadow_build.py — ΠΑΡΑΜΕΤΡΟΙ για τη ΣΚΙΑ «δικο box score» στο χαντικαπ Ευρωλιγκας (23/10/2026, Στελιος «ναι» στο σχεδιο σκιας).
Ιδιος υπολογισμος με el_value_system_page_test.py (υποψηφιος 4 «δικο box», ρεαλιστικη γνωση, K = 500):
  βαρη box (15 στατιστικα → επιθεση O / αμυνα D, ποντοι/100 κατοχες) C_E2026 = εκπαιδευση ΜΟΝΟ σε παραθυρα RAPM ως E2025
  (el_index_build_test.train_box + παραθυρο E2023-E2025) · περσινες τιμες = box ολης της E2025 με C_E2025 ·
  μιξη ζωντανα (n·φετος + 500·περσι)/(n + 500), n = φετινες κατοχες στο γηπεδο · κοστος = (β0 + β1·καθαρο/sd)·λεπτα/40·g(k)·βαρος σελιδας,
  β0/β1/sd = ridge 1 σε ΟΛΕΣ τις 5 σεζον (2021-22…2025-26) με τη σελιδα lineups ξαναχτισμενη στο ανοιγμα (N-Gpage).
Εξοδος: el_box_shadow_params.json (το διαβαζει το el_box_shadow.py). ΤΡΕΧΕΙ ΤΟΠΙΚΑ μια φορα τη σεζον (θελει el_pbp_stints.pkl)."""
import os, sys, io, json, contextlib, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T0 = time.time()
NS = {'__name__': 'p'}
with contextlib.redirect_stdout(_B()): exec(open('el_value_system_page_test.py', encoding='utf-8').read(), NS)
sys.stdout.reconfigure(encoding='utf-8')
V = NS['V']; BI = V['BI']; IX = BI['IX']
SEAS, BYS, agg, boxval, rapm, train_box, WIN, COEF, PIDS, KBOX = (IX[k] for k in ('SEAS', 'BYS', 'agg', 'boxval', 'rapm', 'train_box', 'WIN', 'COEF', 'PIDS', 'KBOX'))
CUR, PREV = 'E2026', 'E2025'
assert CUR not in COEF and PREV in COEF
# ---- παραθυρο E2023-E2025 → C_E2026 ----
i = SEAS.index(PREV); ss = SEAS[max(0, i - 2): i + 1]
gw = [(k, 1.0) for x in ss for k in BYS[x]]
R, h = rapm(gw, 8000); WIN[PREV] = (R, agg(gw))
cf = train_box(CUR)
print(f'C_{CUR}: παραθυρο {ss[0]}–{PREV} · παικτες {len(R)} · δειγμα {cf["n"]} · R² O {cf["r2O"]:.2f} D {cf["r2D"]:.2f}')
# ---- περσινες τιμες (E2025, C_E2025) ----
A_ = agg([(k, 1.0) for k in BYS[PREV]])
prev = {PIDS[p].strip(): [round(float(x), 4) for x in boxval(v, COEF[PREV])] for p, v in A_.items() if v[15] > 0}
# ---- sd + β (ρεαλιστικη γνωση, K 500, ολες οι σεζον) ----
X = NS['feat']('box', 500, 'net'); Yh = V['Yh']
b = np.linalg.solve(X.T @ X + np.eye(2), X.T @ Yh)
vals = [BI['blend']('box', sea, ts, p['pid'], 500) for a, (sea, hc, ac, ts) in zip(NS['AB'], V['hkeys']) for side in a for p, w in side]
sd = float(np.std([float(v[0] - v[1]) for v in vals if v is not None]))
print(f'β0 {b[0]:+.3f} · β1 {b[1]:+.3f} ανα 1 τυπ.απ. (sd καθαρου {sd:.3f} ποντοι/100 κατοχες) · περσινοι παικτες {len(prev)}')
out = dict(built='2026-10-23', season=CUR, prev_season=PREV, K=500, KBOX=KBOX, sd=sd, b0=float(b[0]), b1=float(b[1]),
           coef=dict(bO=[float(x) for x in cf['bO']], bD=[float(x) for x in cf['bD']], lg=[float(x) for x in cf['lg']]), prev=prev,
           note='σκια «δικο box» χαντικαπ EL — el_box_shadow_build.py / el_value_system_page_test.py')
json.dump(out, open('el_box_shadow_params.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'el_box_shadow_params.json γραφτηκε ({time.time() - T0:.0f} δευτ.)')
