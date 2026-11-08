# -*- coding: utf-8 -*-
"""el_fav_dog_timing.py — ΕΥΡΩΛΙΓΚΑ ΧΑΝΤΙΚΑΠ: ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΪΝΤΕΡ — ΠΟΤΕ ΠΑΙΖΟΥΜΕ (12/10/2026, Στελιος: «να συγκρινουμε την ΑΡΧΙΚΗ
τιμη απο οταν βγηκε το pick με την τιμη ΚΛΕΙΣΙΜΑΤΟΣ του ΙΔΙΟΥ pick»). ΠΕΡΙΓΡΑΦΙΚΟ.
Live μηχανη (h_new), Crown, κανονικη περιοδος E2021-25. Για καθε ματς: η ΠΡΩΤΗ τιμη με edge ≥8% (alert· οχι τα πρωτοεμφανιζομενα στο τελευταιο
2ωρο = καταγραφη στο live) → ΙΔΙΑ πλευρα: (α) στην τιμη/γραμμη του alert · (β) στην τιμη/γραμμη ΚΛΕΙΣΙΜΑΤΟΣ (ακομα κι αν εκει δεν ηταν πια pick).
Φαβορι = το pick δινει ποντους (γραμμη < 0) στο alert. Ανα ωρα alert, ανα μπλοκ αγωνιστικων.
Εξοδος: el_fav_dog_timing_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
sys.stdout.reconfigure(encoding='utf-8')
REC, PR, key, pick, settle, D, SE5 = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'D', 'SE5'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows = []
for p, r in REC[21].items():
    q = PR.get(key(p), {}); m = q.get('h_new')
    if m is None or not np.isfinite(m): continue
    ser, tip = r['ser'], r['tip']; c = ser[-1]
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(21, m, row)
        if e < .08: continue
        if k_ > 0 and (tip - row[0]) / 3600 < 2: break                     # live: πρωτη εμφανιση στο τελευταιο 2ωρο = καταγραφη
        hc = row[2] * side                                                  # γραμμη της πλευρας μας
        oc = c[3] if side == 1 else c[4]
        rows.append(dict(sea=D.season.values[p], gn=q.get('gn', 99), role='ΦΑΒΟΡΙ' if hc < 0 else ('ΑΟΥΤΣΑΪΝΤΕΡ' if hc > 0 else 'PICK 0'),
                         hrs=(tip - row[0]) / 3600, at_open=(k_ == 0), pa=settle(21, p, side, row, od), pc=settle(21, p, side, c, oc),
                         oa=od, oc=oc, la=hc, lc=c[2] * side))
        break
X = pd.DataFrame(rows)
def cell(d, col):
    if not len(d): return '—'
    ps = d.groupby('sea')[col].mean()
    return f'{100*d[col].mean():+6.1f}% ({len(d)}, {d[col].sum():+6.1f}μ, {int((ps > 0).sum())}/5)'
P(f'picks χαντικαπ (πρωτο alert ≥8%): {len(X)} · φαβορι {np.mean(X.role == "ΦΑΒΟΡΙ"):.0%} · αουτσαιντερ {np.mean(X.role == "ΑΟΥΤΣΑΪΝΤΕΡ"):.0%} · pick 0 {np.mean(X.role == "PICK 0"):.0%}')
P(''); P('=== ΙΔΙΟ PICK: τιμη ALERT vs τιμη ΚΛΕΙΣΙΜΑΤΟΣ ===')
P('  ρολος          · στο ALERT                          · στο ΚΛΕΙΣΙΜΟ                       · διαφορα · μεση αποδοση alert→κλεισ. · γραμμη ιδια/καλυτερη/χειροτερη')
for role in ('ΦΑΒΟΡΙ', 'ΑΟΥΤΣΑΪΝΤΕΡ', 'PICK 0', 'ΟΛΑ'):
    d = X if role == 'ΟΛΑ' else X[X.role == role]
    if not len(d): continue
    same = np.mean(d.lc == d.la); better = np.mean(d.lc > d.la); worse = np.mean(d.lc < d.la)
    P(f'  {role:14s} · {cell(d, "pa"):35s} · {cell(d, "pc"):35s} · {100*(d.pc.mean()-d.pa.mean()):+5.1f} μ. · {d.oa.mean():.3f}→{d.oc.mean():.3f} · {same:.0%}/{better:.0%}/{worse:.0%}')
P(''); P('=== ΑΝΑ ΩΡΑ ΤΟΥ ALERT (πριν το τζαμπολ) — alert | κλεισιμο ===')
for lo, hi, lab in ((24, 999, '≥24ω (συνηθως στο ανοιγμα)'), (12, 24, '12-24ω'), (6, 12, '6-12ω'), (2, 6, '2-6ω')):
    cells = []
    for role in ('ΦΑΒΟΡΙ', 'ΑΟΥΤΣΑΪΝΤΕΡ'):
        d = X[(X.role == role) & (X.hrs >= lo) & (X.hrs < hi)]
        cells.append(f'{role[:4]}: {cell(d, "pa")} | {cell(d, "pc")}')
    P(f'  {lab:26s} ' + '   ·   '.join(cells))
P(''); P('=== ΑΝΑ ΜΠΛΟΚ ΑΓΩΝΙΣΤΙΚΩΝ — alert | κλεισιμο ===')
for a, b in ((1, 3), (4, 6), (7, 10), (11, 20), (21, 34)):
    cells = []
    for role in ('ΦΑΒΟΡΙ', 'ΑΟΥΤΣΑΪΝΤΕΡ'):
        d = X[(X.role == role) & (X.gn >= a) & (X.gn <= b)]
        cells.append(f'{role[:4]}: {cell(d, "pa")} | {cell(d, "pc")}')
    P(f'  αγων {a:2d}-{b:2d}  ' + '   ·   '.join(cells))
open('el_fav_dog_timing_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
