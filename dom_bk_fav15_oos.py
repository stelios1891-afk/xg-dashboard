# -*- coding: utf-8 -*-
"""dom_bk_fav15_oos.py — ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ ελεγχος του ευρηματος «Ισπανια: φαβορι ≥15 ποντων υποτιμημενα» (dom_bk_t1_bigclubs: +2.37 π.
vs κλεισιμο, t 2.2, 5/6, ROI +11%) στις 4 λιγκες που ΔΕΝ ειχαμε δει (Ελλαδα, Τουρκια, Γαλλια, Γερμανια) — 6/10/2026.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (απο 5/10, πριν κατεβουν τα δεδομενα): το ευρημα «γενικευεται» αν, στις 4 λιγκες μαζι, υπολοιπο φαβορι ≥15 στο κλεισιμο ≥ +1.0
  με t ≥ 2 ΚΑΙ ιδιο προσημο σε ≥3/4 λιγκες. Αναφορα: ROI τυφλο φαβορι ≥15 (κλεισιμο/ανοιγμα) ανα λιγκα και σεζον. Ιδια μεθοδος με το t1.
Εξοδος: dom_bk_fav15_oos_out.txt"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
src = open('dom_bk_t1_bigclubs.py', encoding='utf-8').read()
src = src.replace("LGS = ['ACB', 'LBA']", "LGS = ['GBL', 'TBL', 'LNB', 'BBL']").replace("NAME = dict(ACB='Ισπανια', LBA='Ιταλια')", "NAME = dict(GBL='Ελλαδα', TBL='Τουρκια', LNB='Γαλλια', BBL='Γερμανια')")
src = src.split("for lg in LGS:\n    GG = [g for g in G if g['lg'] == lg]")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
NS = {'__name__': 'f'}
exec(src, NS)
G, side_items, report, SEAS, P, out = (NS[k] for k in ('G', 'side_items', 'report', 'SEAS', 'P', 'out'))
out.clear()
allr = []; signs = []
for lg in ['GBL', 'TBL', 'LNB', 'BBL']:
    GG = [g for g in G if g['lg'] == lg]
    it = [side_items(g, g['cl'][0] < 0) for g in GG if abs(g['cl'][0]) >= 15]
    P(f'=== {NS["NAME"][lg]} · {len(GG)} ματς με αγορα ===')
    if it:
        report('    φαβορι ≥15 (κλεισιμο)', it)
        r = np.array([a - mc for _, a, mc, *_ in it]); allr += list(r); signs.append(np.sign(r.mean()) if len(r) else 0)
    for lo, hi in ((10, 14.5),):
        it2 = [side_items(g, g['cl'][0] < 0) for g in GG if lo <= abs(g['cl'][0]) <= hi]
        if it2: report(f'    φαβορι {lo}-{hi} (αναφορα)', it2)
a = np.array(allr)
m, se = a.mean(), a.std(ddof=1) / np.sqrt(len(a))
ok = m >= 1.0 and m / se >= 2 and sum(s > 0 for s in signs) >= 3
P(''); P(f'ΣΥΝΟΛΟ 4 λιγκες: φαβορι ≥15 n {len(a)} · υπολοιπο vs κλεισιμο {m:+.2f} (t {m/se:+.1f}) · θετικο σε {sum(s > 0 for s in signs)}/4 λιγκες → '
  + ('ΓΕΝΙΚΕΥΕΤΑΙ' if ok else 'ΔΕΝ ΓΕΝΙΚΕΥΕΤΑΙ (Ισπανια: +2.37, t 2.2)'))
open('dom_bk_fav15_oos_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
