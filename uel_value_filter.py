"""uel_value_filter.py — 15/10/2026 (Στελιος: «Europa κραταμε μονο τα φαβορι εντος · δοκιμασε την αξια παικτων (Transfermarkt) / αξια ενδεκαδας σαν
ΦΙΛΤΡΟ — μηπως λογω μεγαλης διαφορας αξιας κοβει κακα picks απο ομαδες που υπερτιμαμε»).
Europa League 2223-2526, σημερινο μοντελο, κανονες picks UEL (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 · 1.70-2.10 · πρωτη εμφανιση ≤72ω),
κατηγορια Α και Β. ΑΞΙΑ = «συνηθισμενη» αξια βασικης ενδεκαδας (διαμεσος 5 τελευταιων εγχωριων, γνωστη ΠΡΙΝ το ματς — euro_team_value.pkl).
 1) ROI ανα ΛΟΓΟ ΑΞΙΑΣ (ομαδα του pick / αντιπαλος), ανα αγορα
 2) ΦΙΛΤΡΟ Φ1 (απλο, προ-δηλωμενο): κοβεται το pick αν η ομαδα του pick ειναι ≤ 0.5× της αξιας του αντιπαλου
 3) ΦΙΛΤΡΟ Φ2 (διαφωνια): «τι λεει η αξια» = διαφορα γκολ απο ln(λογος αξιας) + εδρα (ευθεια απο τις ΑΛΛΕΣ 3 σεζον, ολα τα ευρωπαικα).
    κοβεται το pick αν η αξια βλεπει την ομαδα του pick ≥0.5 γκολ χειροτερη απ οσο το μοντελο
 Για καθε φιλτρο: ROI αυτων που κοβει / κραταει, ανα αγορα, ανα σεζον.
"""
import sys
exec(open('uel_targeted_fix.py', encoding='utf-8').read().split("for CAT, lab in (('A', 'ΚΑΤΗΓΟΡΙΑ Α")[0])
NL = chr(10)
# ευθεια «τι λεει η αξια» απο ΟΛΑ τα ευρωπαικα (A: ολες οι διοργανωσεις), LOSO ανα σεζον
ALLV = A[A.mid_.notna()] if 'mid_' in A.columns else None
A['lnv'] = A.lv_ * 2 if 'lv_' in A.columns else np.nan     # lv_ = ln(αξια γηπ/φιλ) (0 οπου λειπει)
A['hasv'] = [str(MIDS[int(i)]) in TV for i in A.i]
VF = {}
for s in sorted(A.sea.unique()):
    tr = A[(A.sea != s) & A.hasv]
    b = np.polyfit(tr.lv_.values, tr.gd.values.astype(float), 1); VF[s] = b          # gd ≈ b0·ln(V) + b1 (εδρα)
print('«ΤΙ ΛΕΕΙ Η ΑΞΙΑ» (απο τις αλλες 3 σεζον, ολα τα ευρωπαικα): διαφορα γκολ γηπ ≈ k·ln(αξια γηπ/φιλ) + εδρα · ' +
      ' · '.join(f'{s}: k {VF[s][0]:.2f} εδρα {VF[s][1]:+.2f}' for s in VF))
REC = []
for r in x[x.cat.isin(['A', 'B'])].itertuples():
    i = int(r.i); mid = str(MIDS[i])
    if mid not in TV: continue
    vh, va = TV[mid]; p0 = first_pick(i, r.lh, r.la); hn, an = NM.get(i, ('?', '?'))
    vm = VF[r.sea][0] * np.log(vh / va) + VF[r.sea][1]
    for side, pk in p0.items():
        REC.append(dict(cat=r.cat, sea=r.sea, match=f'{hn} - {an}', team=hn if side == 1 else an, kind=pk['kind'], ven='εντος' if side == 1 else 'εκτος',
                        ln=pk['ln'], o=pk['o'], pnl=pk['pnl'], vr=(vh / va) if side == 1 else (va / vh),
                        dis=side * (vm - (r.lh - r.la)), mdl=side * (r.lh - r.la), vmm=side * vm,
                        lg_t=r.lgh if side == 1 else r.lga, lg_o=r.lga if side == 1 else r.lgh))
R = pd.DataFrame(REC)
def cell(y):
    return f'{len(y):3d} picks {100 * y.pnl.mean():+6.1f}% ({y.pnl.sum():+5.1f}μ)' if len(y) else '  —'
MK = (('φαβορι εντος', lambda y: (y.kind == 'φαβ') & (y.ven == 'εντος')), ('φαβορι εκτος', lambda y: (y.kind == 'φαβ') & (y.ven == 'εκτος')),
      ('αουτσαιντερ', lambda y: y.kind == 'dog'), ('ΟΛΑ', lambda y: y.kind.notna()))
for c_ in ('A', 'B'):
    y = R[R.cat == c_]
    print(f'{NL}{"=" * 110}{NL}ΚΑΤΗΓΟΡΙΑ {c_}: {len(y)} picks με αξια')
    print('  1) ROI ανα ΛΟΓΟ ΑΞΙΑΣ (ομαδα pick / αντιπαλος)')
    print(f'     {"αγορα":14s} │ {"≤0.5 (πολυ φθηνοτερη)":>24s} │ {"0.5-1":>24s} │ {"1-2":>24s} │ {">2 (πολυ ακριβοτερη)":>24s}')
    for nm, f in MK:
        z = y[f(y)]
        print(f'     {nm:14s} │ ' + ' │ '.join(f'{cell(z[(z.vr > lo) & (z.vr <= hi)]):>24s}' for lo, hi in ((0, .5), (.5, 1), (1, 2), (2, 1e9))))
    for fl, cond in (('Φ1: κοβεται αν η ομαδα pick ≤0.5× αξια αντιπαλου', y.vr <= .5), ('Φ2: κοβεται αν η αξια τη βλεπει ≥0.5 γκολ χειροτερη απο το μοντελο', y.dis <= -.5)):
        print(f'  {fl}')
        for nm, f in MK:
            z = y[f(y)]; cut = z[cond[f(y)]]; keep = z[~cond[f(y)]]
            print(f'     {nm:14s} ολα {cell(z)} │ ΚΟΒΟΝΤΑΙ {cell(cut)} │ ΜΕΝΟΥΝ {cell(keep)}')
        cut = y[cond]
        if len(cut):
            ps = cut.groupby('sea').pnl.mean()
            print('     κομμενα ανα σεζον: ' + ' '.join(f'{s[2:]}:{100 * v:+.0f}%({(cut.sea == s).sum()})' for s, v in ps.items()))
    cut = y[y.dis <= -.5].sort_values('dis').head(15)
    if len(cut):
        print(f'  ΠΑΡΑΔΕΙΓΜΑΤΑ που κοβει το Φ2 (τα 15 με τη μεγαλυτερη διαφωνια): μοντελο vs «τι λεει η αξια» (διαφορα γκολ υπερ της ομαδας του pick)')
        for r in cut.itertuples():
            print(f'     {r.sea} {r.match[:38]:38s} {r.team[:16]:16s} {r.ln:+.2f} {r.kind} {r.ven:5s} │ μοντελο {r.mdl:+.2f} · αξια {r.vmm:+.2f} · λογος αξιας {r.vr:.2f} │ {r.pnl:+.2f} │ {r.lg_t[:12]} vs {r.lg_o[:12]}')
