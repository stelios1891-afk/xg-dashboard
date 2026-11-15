"""euro_after_contra_test.py — 14/10/2026 (Στελιος: «2 μπετς στο LASK - Liverpool, και τα 2 μετα απο κοντρα (λειπουν Isak, Gakpo, Szoboszlai) —
ιστορικα πως αποδιδουν μπετς που παιρνουμε μετα απο κοντρα;»).
Ευρωπαικα 4 σεζον (UCL / UEL / UECL), κατηγορια Α, κανονες picks (UCL: φαβ ≥10% · dog ≥4% · over ≥4% — UEL/UECL: φαβ ≥4% · dog ≥10% · over ≥4%),
1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET. Για καθε pick: ΚΟΝΤΡΑ = ποσο κινηθηκε η αγορα ΕΝΑΝΤΙΑ στην πλευρα μας ΠΡΙΝ την εισοδο
(απο την πρωτη τιμη ≤72ω ως τη στιγμη που βγηκε το pick · γκολ διαφορας για χαντικαπ / γκολ συνολου για over).
Ομαδες: χωρις κινηση / μικρη κοντρα (0.10-0.25) / μεγαλη κοντρα (≥0.25) / κινηση ΥΠΕΡ μας. ROI στην εισοδο, ROI στο κλεισιμο, CLV μετα την εισοδο.
"""
import sys, os
NL = chr(10)
ALL = []
for CMPN, lab in (('ChampionsLeague', 'UCL'), ('EuropaLeague', 'UEL'), ('ConferenceLeague', 'UECL')):
    src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
    src = src.replace("open('uecl_full_review.py', encoding='utf-8').read()",
                      "open('uecl_full_review.py', encoding='utf-8').read().replace(\"CMP = 'ConferenceLeague'\", \"CMP = '" + CMPN + "'\")")
    _D = open(os.devnull, 'w', encoding='utf-8'); _R = sys.stdout; sys.stdout = _D
    g = {'__name__': 'x'}
    exec(src, g)
    sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
    R, MIDS, snap_ah, snap_ou, implied_margin, mtot = g['R'], g['MIDS'], g['snap_ah'], g['snap_ou'], g['implied_margin'], g['mtot']
    pd, np, picks, GD, GH, GA, settle = g['pd'], g['np'], g['picks'], g['GD'], g['GH'], g['GA'], g['settle']
    ucl = CMPN == 'ChampionsLeague'
    for kind, th in (('φαβορι', .10 if ucl else .04), ('αουτσαιντερ', .04 if ucl else .10), ('over', .04)):
        X = R[R.kind == kind]
        if len(X) == 0: continue
        keys = ['i', 'bk', 'side'] if kind != 'over' else ['i', 'bk']
        F = X[X.e >= th].sort_values('h', ascending=False).groupby(keys).head(1)
        first = X.sort_values('h', ascending=False).groupby(keys).head(1).set_index(keys).mk     # πρωτη τιμη ≤72ω
        for r in F.itertuples():
            k = (r.i, r.bk, r.side) if kind != 'over' else (r.i, r.bk)
            m0 = first.get(k)
            if m0 is None or not np.isfinite(m0): continue
            # κλεισιμο
            if kind == 'over':
                s = snap_ou(MIDS[r.i], r.bk, 0); mc = mtot(*s) if s else np.nan
                pc = settle(GH[r.i] + GA[r.i], s[0], s[1], True) if s else np.nan
            else:
                s = snap_ah(MIDS[r.i], r.bk, 0)
                mc = r.side * implied_margin(r.i, *s) if s else np.nan
                pc = picks.settle(GD[r.i], r.side, s[0] if r.side == 1 else -s[0], s[1] if r.side == 1 else s[2]) if s else np.nan
            ALL.append(dict(comp=lab, kind=kind, bk=r.bk, sea=r.sea, h=r.h, contra=r.mk - m0, clv=mc - r.mk, pnl=r.pnl, pc=pc, e=r.e))
A = pd.DataFrame(ALL)
def cc(x):
    if len(x) < 6: return f'n{len(x) / 2:4.0f} (λιγα)'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); c = x.groupby('bk').pc.mean()
    return (f'{n:4.0f} picks · ROI στην εισοδο {100 * m.mean():+6.1f}% · στο κλεισιμο {100 * c.mean():+6.1f}% · CLV μετα {x.clv.mean():+.2f} · '
            f'σεζον θετικες {(x.groupby("sea").pnl.mean() > 0).sum()}/{x.sea.nunique()}')
BINS = (('ΜΕΓΑΛΗ ΚΟΝΤΡΑ (αγορα −0.25 ή περισσοτερο)', A.contra <= -0.25), ('μικρη κοντρα (−0.10…−0.25)', (A.contra > -0.25) & (A.contra <= -0.10)),
        ('χωρις κινηση (±0.10)', A.contra.abs() < 0.10), ('κινηση ΥΠΕΡ μας (≥ +0.10)', A.contra >= 0.10))
print('PICKS ΜΕΤΑ ΑΠΟ ΚΟΝΤΡΑ — ευρωπαικα 4 σεζον, κατηγορια Α (κοντρα = κινηση αγορας εναντια στην πλευρα μας ΠΡΙΝ την εισοδο)')
for grp, m_ in (('ΟΛΑ', A.comp.notna()), ('UCL', A.comp == 'UCL'), ('UEL', A.comp == 'UEL'), ('UECL', A.comp == 'UECL')):
    print(f'{NL}=== {grp}')
    for lab, b in BINS: print(f'   {lab:42s} {cc(A[m_ & b])}')
print(f'{NL}=== ΑΝΑ ΑΓΟΡΑ (ολες οι διοργανωσεις)')
for kind in ('φαβορι', 'αουτσαιντερ', 'over'):
    print(f'   {kind}:')
    for lab, b in BINS: print(f'      {lab:42s} {cc(A[(A.kind == kind) & b])}')
print(f'{NL}=== ΜΕΓΑΛΗ ΚΟΝΤΡΑ ανα ωρα εισοδου (ολα)')
for lo, hi, l in ((24, 72, '24-72ω'), (8, 23, '8-23ω'), (0, 7, '≤7ω')):
    print(f'   {l:8s} {cc(A[(A.contra <= -0.25) & (A.h >= lo) & (A.h <= hi)])}')
A.to_pickle('euro_after_contra_rows.pkl')
