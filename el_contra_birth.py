# -*- coding: utf-8 -*-
"""el_contra_birth.py — ΕΥΡΩΛΙΓΚΑ: ΤΙ «ΓΕΝΝΑΕΙ» ΕΝΑ PICK ΜΕΤΑ ΤΟ ΑΝΟΙΓΜΑ & ΠΟΣΟ ΚΟΝΤΡΑ (17/10/2026, Στελιος: «τι προκαλει τα αουτσαιντερ
2-6ω; κοντρα οπως ο κανονας Γ ή μια αποδοση 1.85→1.90 που πιανει το κατωφλι; αναλυση κοντρας 1.5, 2.5 ποντων… σε συνολα και χαντικαπ»).
Ιδια προσομοιωση με el_alert_types / el_over_late_test: live μηχανη (h_new / t_new), Crown καθε αλλαγη τιμης, E2021-25, ALERT = πρωτη τιμη με edge ≥8%.
ΚΟΝΤΡΑ = ποσο απομακρυνθηκε η ΔΙΚΑΙΗ αγορα (αναμενομενη διαφορα / συνολο, με τις αποδοσεις) απο την πλευρα μας, απο την πρωτη τιμη ως το alert.
ΑΙΤΙΑ του alert (συγκριση με την ΑΜΕΣΩΣ προηγουμενη τιμη): «αλλαξε η γραμμη» ή «μονο η αποδοση».
Live κανονες στη σημανση: χαντικαπ <2ω = καταγραφη (late2h) · συνολα: κοντρα ≥1.5 που ξεπεραστηκε ≥6ω πριν = καταγραφη (Γ / move15).
ΠΕΡΙΓΡΑΦΙΚΟ (χωρις κριση). Εξοδος: el_contra_birth_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {'__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
sys.stdout.reconfigure(encoding='utf-8')
REC, PR, key, pick, settle, D, at = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'D', 'at'))
rows = []
for t, fld in ((21, 'h_new'), (23, 't_new')):
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(fld)
        if m is None or not np.isfinite(m): continue
        ser, tip = r['ser'], r['tip']; o = ser[0]; c = ser[-1]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(t, m, row)
            if e < .08: continue
            hrs = (tip - row[0]) / 3600
            mv = -(row[1] - o[1]) * side if t == 21 else -(row[1] - o[1]) * side   # + = ΚΟΝΤΡΑ (η αγορα εφυγε απο την πλευρα μας)
            prev = ser[k_ - 1] if k_ > 0 else None
            prev1 = at(ser, row[0] - 3600) or o
            cause = None if prev is None else ('αλλαξε η γραμμη' if abs(row[2] - prev[2]) > 1e-9 else 'μονο η αποδοση')
            hx = None                                                   # ποτε ξεπεραστηκε το 1.5 κοντρα (για τον κανονα Γ)
            if mv >= 1.5:
                hx = next(((tip - x[0]) / 3600 for x in ser[:k_ + 1] if -(x[1] - o[1]) * side >= 1.5), None)
            if t == 21:
                hc = row[2] * side
                role = 'ΦΑΒΟΡΙ' if hc < 0 else ('ΑΟΥΤΣΑΪΝΤΕΡ' if hc > 0 else 'PK')
                paper = 'τελ.2ωρο' if (k_ > 0 and hrs < 2) else None
            else:
                role = 'OVER' if side == 1 else 'UNDER'
                paper = 'Γ (κοντρα≥1.5, ≥6ω)' if (hx is not None and hx >= 6) else None
            oc = c[3] if side == 1 else c[4]
            rows.append(dict(t=t, sea=D.season.values[p], role=role, hrs=hrs, at_open=(k_ == 0), mv=mv, mv1h=-(row[1] - prev1[1]) * side,
                             cause=cause, paper=paper, after=(c[1] - row[1]) * side, pa=settle(t, p, side, row, od), pc=settle(t, p, side, c, oc)))
            break
X = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d, col='pa'):
    if not len(d): return '      —                   '
    ps = d.groupby('sea')[col].mean()
    return f'{100*d[col].mean():+6.1f}% ({len(d):3d}, {d[col].sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
def ln(lab, d):
    if not len(d): P(f'    {lab:34s} —'); return
    P(f'    {lab:34s} {cell(d)} · κλεισ. {cell(d, "pc")} · αγορα μετα {d.after.mean():+.2f}π')
P('ΕΥΡΩΛΙΓΚΑ · τι γεννα τα picks μετα το ανοιγμα · live μηχανη, Crown, E2021-25 · κελι = ROI (picks, μοναδες, θετικες σεζον)')
P('κοντρα = ποντοι που η δικαιη αγορα εφυγε απο την πλευρα μας (ανοιγμα → pick) · «αγορα μετα» + = ηρθε προς εμας ως το κλεισιμο')
# ---------- 1. Αουτσαιντερ 2-6ω ----------
d26 = X[(X.t == 21) & (X.role == 'ΑΟΥΤΣΑΪΝΤΕΡ') & ~X.at_open & (X.hrs >= 2) & (X.hrs < 6)]
P(''); P(f'=== 1. ΑΟΥΤΣΑΪΝΤΕΡ που πρωτοβγαινουν 2-6ω πριν ({len(d26)}) — ΤΙ ΤΑ ΓΕΝΝΗΣΕ ===')
P('  ποσο κοντρα ειχε φαει η αγορα απο το ανοιγμα:')
for lo, hi, lab in ((-99, 0.5, 'καθολου / προς εμας (<0.5)'), (0.5, 1.5, '0.5-1.5'), (1.5, 2.5, '1.5-2.5'), (2.5, 99, '≥2.5')):
    ln(lab, d26[(d26.mv >= lo) & (d26.mv < hi)])
P('  τι αλλαξε τη στιγμη του pick:')
for cz in ('αλλαξε η γραμμη', 'μονο η αποδοση'):
    ln(cz, d26[d26.cause == cz])
ln('ξαφνικη: ≥1π κοντρα την τελευταια 1ω', d26[d26.mv1h >= 1])
ln('σταδιακη (<1π την τελευταια 1ω)', d26[d26.mv1h < 1])
P(f'  μεση κοντρα απο ανοιγμα {d26.mv.mean():+.2f}π (6-12ω αουτσ.: {X[(X.t == 21) & (X.role == "ΑΟΥΤΣΑΪΝΤΕΡ") & ~X.at_open & (X.hrs >= 6) & (X.hrs < 12)].mv.mean():+.2f}π)')
# ---------- 2. Κοντρα ανα μεγεθος ----------
B = ((-99, 0.5, '<0.5 (σχεδον καμια)'), (0.5, 1.5, '0.5-1.5'), (1.5, 2.5, '1.5-2.5'), (2.5, 4.0, '2.5-4'), (4.0, 99, '≥4'))
for t, roles, nm in ((21, ('ΦΑΒΟΡΙ', 'ΑΟΥΤΣΑΪΝΤΕΡ'), 'ΧΑΝΤΙΚΑΠ'), (23, ('OVER', 'UNDER'), 'ΣΥΝΟΛΑ')):
    Z = X[(X.t == t) & ~X.at_open]
    P(''); P(f'=== 2. {nm}: picks ΜΕΤΑ το ανοιγμα ανα ΚΟΝΤΡΑ (ολα, και αυτα που σημερα γινονται καταγραφη) ===')
    P(f'  (στο ανοιγμα, για συγκριση: {cell(X[(X.t == t) & X.at_open])})')
    for role in roles + ('ΟΛΑ',):
        P(f'  {role}:')
        R = Z if role == 'ΟΛΑ' else Z[Z.role == role]
        for lo, hi, lab in B:
            ln(lab, R[(R.mv >= lo) & (R.mv < hi)])
    P(f'  ανα ωρα γεννησης × κοντρα (ΟΛΑ {nm}):')
    for hlo, hhi, hl in ((6, 99, '≥6ω'), (2, 6, '2-6ω'), (0, 2, '<2ω')):
        for lo, hi, lab in ((-99, 1.5, 'κοντρα <1.5'), (1.5, 2.5, 'κοντρα 1.5-2.5'), (2.5, 99, 'κοντρα ≥2.5')):
            ln(f'{hl} · {lab}', Z[(Z.hrs >= hlo) & (Z.hrs < hhi) & (Z.mv >= lo) & (Z.mv < hi)])
    P(f'  αιτια (ΟΛΑ {nm}): ')
    for cz in ('αλλαξε η γραμμη', 'μονο η αποδοση'):
        ln(cz, Z[Z.cause == cz])
    P(f'  σημερινη μεταχειριση: κανονικα {cell(Z[Z.paper.isna()])} · καταγραφη {cell(Z[Z.paper.notna()])}')
open('el_contra_birth_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
