"""uecl_timing_close.py — 12/10/2026 (Στελιος: «ο χρονισμος θα πρεπει να συγκρινει καθε πικ την ωρα που βγηκε με το κλεισιμο — βγηκε 72ω → κλεισιμο,
βγηκε 26ω → κλεισιμο κτλ»). Ροες του uecl_battery (Conference League 4 σεζον, Crown & SBOBET μεσος). Για καθε ωρα πρωτης εμφανισης:
ROI ΣΤΗΝ ΕΙΣΟΔΟ vs ROI των ΙΔΙΩΝ picks στην τιμη ΚΛΕΙΣΙΜΑΤΟΣ (ιδια πλευρα, γραμμη/τιμη κλεισιματος) + κινηση αγορας ως το κλεισιμο
(γκολ που δικαιολογει η τιμη· + = η αγορα ηρθε ΠΡΟΣ το pick).
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 2 =================')[0]
_DEV = open(os.devnull, "w", encoding="utf-8"); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
W = [(72, 72, '72ω'), (60, 60, '60ω'), (48, 48, '48ω'), (36, 36, '36ω'), (24, 24, '24ω'), (18, 18, '18ω'), (12, 12, '12ω'), (8, 8, '8ω'),
     (6, 4, '6-4ω'), (2, 1, '2-1ω'), (0, 0, 'μονο στο κλεισιμο')]
def close_pnl(r):                       # ιδια πλευρα στην τιμη κλεισιματος, ΧΩΡΙΣ φιλτρο τιμης
    i = r.i
    if r.grp == 'AH':
        s = snap_ah(MIDS[i], r.bk, 0)
        if not s: return np.nan
        L, oh, oa = s; ln = L if r.side == 1 else -L; o = oh if r.side == 1 else oa
        return picks.settle(GD[i], r.side, ln, o)
    s = snap_ou(MIDS[i], r.bk, 0)
    if not s: return np.nan
    L, o, un = s; return settle(GH[i] + GA[i], L, o if r.side == 'over' else un, r.side == 'over')
for k in list(SF):
    SF[k] = SF[k].assign(pc=[close_pnl(r) for r in SF[k].itertuples()])
for lab in ('ΦΑΒ Α @10 (προταση)', 'OVER Α @8 (προταση)', 'UNDER Β @14 (σκια)', 'DOG Α @10 (σημερα)', 'ΦΑΒ Α @4 (σημερα)', 'OVER Α @4 (σημερα)'):
    F = SF[lab]
    print(f'\n{lab} — {len(F) / 2:.0f} picks')
    print(f'   {"βγηκε":18s} {"picks":>5s} {"ROI στην εισοδο":>16s} {"ROI στο κλεισιμο":>17s} {"διαφορα":>8s}   κινηση αγορας ως το κλεισιμο')
    for hi, lo, wl in W:
        y = F[(F.h <= hi) & (F.h >= lo)]
        if len(y) == 0: continue
        z = y.dropna(subset=['pc']); e = z.groupby('bk').pnl.mean().mean(); c = z.groupby('bk').pc.mean().mean(); cv = y.clv.dropna()
        print(f'   {wl:18s} {len(y) / 2:5.1f} {100 * e:+15.0f}% {100 * c:+16.0f}% {100 * (e - c):+7.0f}   '
              f'{cv.mean():+.2f} γκολ (προς εμας {100 * (cv > 0).mean():.0f}% · κοντρα {100 * (cv < 0).mean():.0f}%)')
    z = F.dropna(subset=['pc']); e = z.groupby('bk').pnl.mean().mean(); c = z.groupby('bk').pc.mean().mean()
    print(f'   {"ΟΛΑ":18s} {len(F) / 2:5.1f} {100 * e:+15.0f}% {100 * c:+16.0f}% {100 * (e - c):+7.0f}   {F.clv.mean():+.2f} γκολ')
