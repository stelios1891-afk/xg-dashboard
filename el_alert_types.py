# -*- coding: utf-8 -*-
"""el_alert_types.py — ΤΥΠΟΙ ALERTS με το LIVE μοντελο (1/10/2026, αιτημα Στελιου: «να μην τα βαζουμε ολα στο ιδιο τσουβαλι —
μια κοντρα 1 ποντου 10 ωρες πριν δεν ειναι το ιδιο με μια ξαφνικη εντονη αλλαγη 1-2 ωρες πριν, που μπορει να ειναι απουσια»).
Μοντελο: el_newmodel_preds.pkl (χαντικαπ Β1+ειδικοι+προετοιμασια+εγχωρια 11+ · συνολο v2+Κ2+προετοιμασια)· και το ΠΑΛΙΟ για συγκριση.
Αγορα: Crown (Nowgoal), καθε αλλαγη τιμης (οχι ωριαια), σωστη ωρα (+8), κανονικη περιοδος E2021-E2025 (el_line_timing).
ALERT = η ΠΡΩΤΗ αλλαγη τιμης οπου edge ≥ 8%. Κατηγοριες:
  ΠΟΤΕ γεννηθηκε: στο ΑΝΟΙΓΜΑ (πρωτη τιμη) · ≥12ω · 6-12ω · 2-6ω · <2ω πριν το τζαμπολ
  ΤΙ προηγηθηκε (για οσα δεν ειναι στο ανοιγμα): κινηση της αγορας (αναμενομενη διαφορα/συνολο) ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ ως το alert,
     + = ΚΟΝΤΡΑ σε εμας (η αγορα απομακρυνθηκε απο την πλευρα μας): ~0 (<0.5π) · 0.5-1.5π · ≥1.5π
  ΞΑΦΝΙΚΗ: ≥1π κοντρα μεσα στην τελευταια 1 ωρα πριν το alert.
Για καθε ομαδα: ROI στην τιμη του alert (x/5 σεζον), ROI αν περιμεναμε το κλεισιμο (ιδια πλευρα, γραμμη/τιμη κλεισιματος),
  τι εκανε η αγορα ΜΕΤΑ (+ = γυρισε προς εμας), % που ηταν ακομα pick στο κλεισιμο.
Εξοδος: el_alert_types_out.txt"""
import sys, pickle
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
LT = {}
src = open('el_line_timing.py', encoding='utf-8').read().split('ATH = ')[0]
exec(src, LT)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, REC, ACT, TOT, SE5, SM, ST = (LT[k] for k in ('D', 'REC', 'ACT', 'TOT', 'SE5', 'SM', 'ST'))
PR = pickle.load(open('el_newmodel_preds.pkl', 'rb'))
def key(i): return (D.season.values[i], D.home.values[i], D.away.values[i], str(pd.Timestamp(D.t.values[i]))[:16])
def pick(t, mu_model, row):
    _, _, L, o1, o2 = row; sg = SM if t == 21 else ST
    thr = -L if t == 21 else L
    if abs(L - round(L)) < 1e-9:
        pw = 1 - NormalDist(mu_model, sg).cdf(thr + 0.5); pl = NormalDist(mu_model, sg).cdf(thr - 0.5)
    else:
        pw = 1 - NormalDist(mu_model, sg).cdf(thr); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
def settle(t, p, side, row, od):
    L = row[2]; v = ((ACT[p] + L) if t == 21 else (TOT[p] - L)) * side
    return (od - 1) if v > 0 else (0.0 if v == 0 else -1.0)
def at(ser, tau):
    k = None
    for r in ser:
        if r[0] <= tau: k = r
        else: break
    return k
def simulate(t, which):
    fld = ('h_' if t == 21 else 't_') + which; recs = []
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(fld)
        if m is None or not np.isfinite(m): continue
        ser, tip = r['ser'], r['tip']; o = ser[0]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(t, m, row)
            if e < 0.08: continue
            prev1 = at(ser, row[0] - 3600) or o
            c = ser[-1]; oc = c[3] if side == 1 else c[4]
            sc, ec, _ = pick(t, m, c)
            recs.append(dict(sea=D.season.values[p], hrs=(tip - row[0]) / 3600, at_open=(k_ == 0),
                             mv_open=-(row[1] - o[1]) * side,        # + = η αγορα φευγει απο την πλευρα μας (ανοιγμα → alert)
                             mv_1h=-(row[1] - prev1[1]) * side,      # + = κοντρα την τελευταια ωρα
                             after=(c[1] - row[1]) * side,           # + = μετα το alert η αγορα ηρθε προς εμας
                             edge=e, pnl=settle(t, p, side, row, od), pnl_close=settle(t, p, side, c, oc),
                             still=(sc == side and ec >= 0.08), gn=PR[key(p)].get('gn', PR[key(p)].get('rnd', 99))))
            break
    return pd.DataFrame(recs)
def line_(lab, z):
    if len(z) == 0: P(f'    {lab:34s} —'); return
    pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0)
    P(f'    {lab:34s} n {len(z):4d} · ROI στο alert {z.pnl.mean()*100:+6.1f}% ({pos}/5) · αν περιμεναμε κλεισιμο {z.pnl_close.mean()*100:+6.1f}% · '
      f'μετα το alert η αγορα {z.after.mean():+.2f}π. προς εμας · ακομα pick στο κλεισιμο {z.still.mean():.0%} · edge {z.edge.mean()*100:.0f}%')
def report(t, nm, which):
    Z = simulate(t, which)
    P(''); P(f'=== {nm} — μοντελο {which.upper()} · {len(Z)} alerts · διαμεσος γεννησης {Z.hrs.median():.1f}ω πριν ===')
    line_('ΟΛΑ', Z)
    P('  Α. ΠΟΤΕ γεννηθηκε:')
    line_('στο ΑΝΟΙΓΜΑ (πρωτη τιμη)', Z[Z.at_open])
    nz = Z[~Z.at_open]
    for lo, hi, lab in ((12, 99, 'αργοτερα, ≥12ω πριν'), (6, 12, '6-12ω πριν'), (2, 6, '2-6ω πριν'), (0, 2, 'τελευταιο 2ωρο')):
        line_(lab, nz[(nz.hrs >= lo) & (nz.hrs < hi)])
    P('  Β. ΤΙ προηγηθηκε (οχι στο ανοιγμα) — κινηση αγορας ανοιγμα→alert, + = κοντρα σε εμας:')
    for lo, hi, lab in ((-99, -0.5, 'αγορα ΠΡΟΣ εμας (≤ −0.5π)'), (-0.5, 0.5, 'σχεδον ακινητη (<0.5π)'), (0.5, 1.5, 'κοντρα 0.5-1.5π'), (1.5, 99, 'κοντρα ≥1.5π')):
        line_(lab, nz[(nz.mv_open >= lo) & (nz.mv_open < hi)])
    line_('ΞΑΦΝΙΚΗ: ≥1π κοντρα στην τελευταια 1ω', nz[nz.mv_1h >= 1])
    P('  Γ. ΣΥΝΔΥΑΣΜΟΣ (ωρα × κινηση ανοιγμα→alert):')
    for lo, hi, lab in ((6, 99, '≥6ω'), (2, 6, '2-6ω'), (0, 2, '<2ω')):
        z = nz[(nz.hrs >= lo) & (nz.hrs < hi)]
        line_(f'{lab} · ακινητη/προς εμας (<0.5π)', z[z.mv_open < 0.5])
        line_(f'{lab} · κοντρα ≥0.5π', z[z.mv_open >= 0.5])
    P('  Δ. αγων 1-10 vs 11+:')
    line_('αγων 1-10', Z[Z.gn <= 10]); line_('αγων 11+', Z[Z.gn > 10])
    return Z
ZZ = {}
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΟ ΠΟΝΤΩΝ')):
    for which in ('new', 'old'):
        ZZ[(t, which)] = report(t, nm, which)
pickle.dump(ZZ, open('el_alert_types.pkl', 'wb'))
open('el_alert_types_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
