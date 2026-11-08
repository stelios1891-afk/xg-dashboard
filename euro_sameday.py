# -*- coding: utf-8 -*-
"""euro_sameday.py — 5/11/2026 (Στελιος: «προεκυψαν πολλα μπετς μεσα στην ιδια μερα στο conference, ολα δεχτηκαν κοντρα· πως απεδωσαν στο παρελθον η κινηση της αγορας και τα μπετ που γεννηθηκαν την ιδια μερα;»).
Ολοι οι live κανονες UECL, καθαρη μηχανη, 90′, μεσος Crown/SBOBET. ΓΕΝΝΗΘΗΚΕ ΙΔΙΑ ΜΕΡΑ = το edge περασε το κατωφλι ≤18ω πριν τη σεντρα, ενω υπηρχε τιμη νωριτερα χωρις edge. ΚΟΝΤΡΑ = η αγορα πηγε ≥0.10 γκολ κατα της πλευρας μας απο την πρωτη τιμη ≤72ω ως τη στιγμη του pick (χαντικαπ: δικαιη υπεροχη· συνολα: δικαιο συνολο).
Και ανα ΜΕΡΑ: πως πηγαν οι μερες με πολλα τετοια μπετ μαζι. Τιποτα live."""
import sys, datetime as dt
_src = open('euro_clean_rules.py', encoding='utf-8').read()
exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
side_nf = lambda i: (1 if FMA[i] else -1)
def start(i, bk, tot):
    for h in H_72:
        s = snap_ou(MIDS[i], bk, h) if tot else snap(MIDS[i], bk, h)
        if s: return h, (mtot(*s) if tot else fair(*s))
    return None, None
def classify(z, tot, lab):
    mv = []; lat = []
    for r in z.itertuples():
        h0, f0 = start(r.i, r.bk, tot); s = snap_ou(MIDS[r.i], r.bk, r.h) if tot else snap(MIDS[r.i], r.bk, r.h)
        f1 = mtot(*s) if tot else fair(*s)
        mv.append(r.side * (f1 - f0) if f0 is not None else np.nan); lat.append(h0 - r.h if h0 is not None else np.nan)
    return z.assign(mv=mv, lat=lat, rule=lab)
def day(i):
    return (dt.datetime.fromtimestamp(KO[MIDS[i]], dt.timezone.utc) + dt.timedelta(hours=2)).strftime('%Y-%m-%d')
def sh(z):
    if not len(z): return '   0 picks'
    return f"{len(z) / 2:5.1f}p {100 * z.pnl.mean():+6.1f}% {units(z):+6.1f}μ ±{100 * z.groupby('i').pnl.mean().std() / np.sqrt(max(z.i.nunique(), 1)):4.1f} │ " + ' '.join(f"{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}" for s in SEAS if (z.sea == s).any()) + f" │ C{100 * z[z.bk == 'Crown'].pnl.mean():+.0f} S{100 * z[z.bk == 'SBOBET'].pnl.mean():+.0f} │ CLV μετα {z.clv.mean():+.3f} (t {tval(z.clv):+.1f})"
def table(z):
    print(f'   ολα                                  {sh(z)}')
    print(f'   βγηκε στην πρωτη τιμη                {sh(z[z.lat == 0])}')
    print(f'   γεννηθηκε αργοτερα, >18ω πριν        {sh(z[(z.lat > 0) & (z.h > 18)])}')
    sd = z[(z.lat > 0) & (z.h <= 18)]
    print(f'   ΓΕΝΝΗΘΗΚΕ ΙΔΙΑ ΜΕΡΑ (≤18ω)           {sh(sd)}')
    print(f'      με ΚΟΝΤΡΑ κινηση ≥0.10            {sh(sd[sd.mv <= -.10])}')
    print(f'      με ΚΟΝΤΡΑ κινηση ≥0.25            {sh(sd[sd.mv <= -.25])}')
    print(f'      χωρις κοντρα                      {sh(sd[sd.mv > -.10])}')
    print(f'      πολυ αργα (≤8ω) & κοντρα ≥0.10    {sh(sd[(sd.h <= 8) & (sd.mv <= -.10)])}')
    print(f'   ΚΟΝΤΡΑ ≥0.10, οποτεδηποτε            {sh(z[z.mv <= -.10])}')
    print(f'   χωρις κοντρα, οποτεδηποτε            {sh(z[z.mv > -.10])}')
RULES = [('Β αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, ECB, 'dog', H_72, sidefn=side_nf), .10, False),
         ('Β under ≥14%', seq_ou(OH_N, OA_N, TOT90, ECB, False, H_72), .14, True),
         ('Α over ≥−2%', seq_ou(OH_N, OA_N, TOT90, ECA, True, H_72), -.02, True),
         ('Α φαβορι ≥4%', seq_ah(P6['INS'], GD, ECA, 'fav', H_72), .04, False),
         ('Α αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, ECA, 'dog', H_72), .10, False)]
ALL = []
for lab, p, t, tot in RULES:
    z = classify(at(p, t), tot, lab); ALL.append(z); print(f'\n=== UECL {lab}'); table(z)
A = pd.concat(ALL, ignore_index=True); A['day'] = [day(i) for i in A.i]
print('\n=== ΟΛΟΙ ΟΙ LIVE ΚΑΝΟΝΕΣ UECL ΜΑΖΙ'); table(A)
print('\n=== ΜΟΝΟ ΚΑΤΗΓΟΡΙΑ Β (dog + under)'); table(A[A.rule.str.startswith('Β')])
print('\n=== ΜΟΝΟ ΚΑΤΗΓΟΡΙΑ Α'); table(A[A.rule.str.startswith('Α')])
sd = A[(A.lat > 0) & (A.h <= 18)]; sa = sd[sd.mv <= -.10]
print('\n=== ΑΝΑ ΜΕΡΑ: ποσα μπετ γεννηθηκαν ιδια μερα με κοντρα κινηση, και πως πηγαν ΑΥΤΑ (μονο ημερες με ≥1)')
rows = []
for d, g in sa.groupby('day'):
    rows.append(dict(day=d, sea=g.sea.iloc[0], picks=len(g) / 2, μ=units(g), roi=100 * g.pnl.mean(), ολα_μερας=len(A[A.day == d]) / 2, μ_ολα=units(A[A.day == d])))
D = pd.DataFrame(rows).sort_values('day')
print(D.round(1).to_string(index=False))
for lo, hi, n in ((0, 1.5, '≤1.5 τετοια μπετ'), (2, 3.5, '2-3.5'), (4, 99, '≥4')):
    q = D[(D.picks >= lo) & (D.picks <= hi)]; pk = q.picks.sum()
    print(f'{n:18s}: {len(q):2d} μερες · {pk:5.1f} μπετ · {q.μ.sum():+6.1f}μ · ROI {100 * q.μ.sum() / max(pk, 1):+6.1f}% · θετικες μερες {(q.μ > 0).sum()}/{len(q)}')
print(f'ανα μερα (συστ. σφαλμα μεταξυ ημερων): μεσο κερδος {D.μ.mean():+.2f}μ ανα μερα, ±{D.μ.std() / np.sqrt(len(D)):.2f}, {len(D)} μερες')
# ---- ελεγχος: αλλες διοργανωσεις, ιδιος ορισμος
print('\n=== ΣΥΓΚΡΙΣΗ: ΙΔΙΟΣ ΟΡΙΣΜΟΣ ΣΕ ΑΛΛΟΥΣ ΚΑΝΟΝΕΣ (72ω-κλεισιμο, 4 σεζον)')
for lab, p, t, tot in (('UCL αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, UCLA, 'dog', H_72), .10, False), ('UCL φαβορι ≥4%', seq_ah(P6['INS'], GD, UCLA, 'fav', H_72), .04, False), ('UCL over Α ≥4%', seq_ou(OH_N, OA_N, TOT90, UCLA, True, H_72), .04, True), ('UEL αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, UELA, 'dog', H_72), .10, False), ('UEL under Α ≥10%', seq_ou(OH_N, OA_N, TOT90, UELA, False, H_72), .10, True)):
    z = classify(at(p, t), tot, lab); s = z[(z.lat > 0) & (z.h <= 18)]
    print(f'{lab}\n   ολα                     {sh(z)}\n   ιδια μερα               {sh(s)}\n   ιδια μερα & κοντρα      {sh(s[s.mv <= -.10])}')
# ---- ελεγχος με το χερι: οι μερες με ≥3 τετοια μπετ + ποσα γεννηθηκαν ιδια μερα ανα μερα (με ή χωρις κοντρα)
NM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        NM[str(k)] = (m['home'].get('name'), m['away'].get('name'))
print('\n=== ΕΛΕΓΧΟΣ: οι μερες με ≥3 μπετ ιδιας μερας & κοντρα')
for d in D[D.picks >= 3].day:
    print(d)
    for r in sa[sa.day == d].sort_values(['i', 'bk']).itertuples():
        s = snap_ou(MIDS[r.i], r.bk, r.h) if r.rule[2:] in ('under ≥14%', 'over ≥−2%') else snap(MIDS[r.i], r.bk, r.h)
        print(f"   {NM[MIDS[r.i]][0]} - {NM[MIDS[r.i]][1]} [{R90[MIDS[r.i]][0]}-{R90[MIDS[r.i]][1]}] {r.rule} {r.bk} {r.h}ω γραμμη/τιμες {s} edge {100 * r.e:.1f}% κινηση {r.mv:+.2f} αποτ. {r.pnl:+.2f}")
C = sd.groupby('day').agg(picks=('pnl', lambda x: len(x) / 2), μ=('pnl', lambda x: x.sum() / 2))
print('\n=== ΑΝΑ ΜΕΡΑ: ΟΛΑ τα μπετ που γεννηθηκαν ιδια μερα (με ή χωρις κοντρα)')
for lo, hi, n in ((0, 1.5, '≤1.5'), (2, 3.5, '2-3.5'), (4, 5.5, '4-5.5'), (6, 99, '≥6')):
    q = C[(C.picks >= lo) & (C.picks <= hi)]
    print(f'{n:6s}: {len(q):2d} μερες · {q.picks.sum():5.1f} μπετ · {q.μ.sum():+6.1f}μ · ROI {100 * q.μ.sum() / max(q.picks.sum(), 1):+6.1f}% · θετικες {(q.μ > 0).sum()}/{len(q)} · {[(d, round(float(r.μ), 1)) for d, r in q.iterrows()] if lo >= 4 else ""}')
# ---- ελεγχος: η εισοδος στο «0ω» ειναι η τιμη κλεισιματος, δυσκολα παιζεται· τα σημερινα γεννηθηκαν 5-19ω πριν. Και: ιδιο ματς και απο τις 2 πλευρες (φαβ + αουτσαιντερ).
print('\n=== ΙΔΙΑ ΜΕΡΑ ΑΝΑ ΩΡΑ ΕΙΣΟΔΟΥ (ολοι οι κανονες UECL)')
for lab, zz in (('ολοι', A), ('Β', A[A.rule.str.startswith('Β')]), ('Α', A[A.rule.str.startswith('Α')])):
    s = zz[(zz.lat > 0) & (zz.h <= 18)]
    print(lab)
    for a, b in ((12, 18), (6, 8), (4, 4), (2, 2), (1, 1), (0, 0)):
        print(f'   εισοδος {a}-{b}ω   {sh(s[(s.h >= a) & (s.h <= b)])}')
    print(f'   χωρις τα 0ω      {sh(s[s.h > 0])}')
    print(f'   μονο 4-18ω       {sh(s[s.h >= 4])}')
    print(f'   4-18ω & κοντρα   {sh(s[(s.h >= 4) & (s.mv <= -.10)])}')
    print(f'   4-18ω χωρις      {sh(s[(s.h >= 4) & (s.mv > -.10)])}')
s = A[(A.lat > 0) & (A.h >= 4) & (A.h <= 18)]
for lab, _ in RULES and [(r[0], 0) for r in RULES]:
    q = s[s.rule == lab]; print(f'4-18ω {lab:22s} {sh(q)}\n      & κοντρα                 {sh(q[q.mv <= -.10])}')
ah = A[A.rule.str.contains('αουτσαιντερ|φαβορι')]; both = ah.groupby(['i', 'bk']).side.nunique(); both = both[both > 1]
bm = {i for i, _ in both.index}
print(f'\nΙΔΙΟ ΜΑΤΣ ΚΑΙ ΑΠΟ ΤΙΣ 2 ΠΛΕΥΡΕΣ (χαντικαπ): {len(bm)} ματς απο {ah.i.nunique()} · μπετ {len(ah[ah.i.isin(bm)]) / 2:.1f} · ROI {100 * ah[ah.i.isin(bm)].pnl.mean():+.1f}%')
print(f'ΟΛΑ χωρις αυτα τα ματς (μονο χαντικαπ): {sh(ah[~ah.i.isin(bm)])}')
