"""uel_value_blend_picks.py — 15/10/2026 (Στελιος: «το βασικο ερωτημα: κοβει κακα αουτσαιντερ και φερνει καλυτερα φαβορι, ναι ή οχι;»).
Ο μηχανισμος αξιας ως ΠΡΟΒΛΕΨΗ (μιξη μοντελου με «τι λεει η αξια ενδεκαδας», βαρος απο τις αλλες 3 σεζον — euro_value_blend_quality) και τα picks
που βγαζει vs το σημερινο: ΚΟΠΗΚΑΝ / ΚΡΑΤΗΘΗΚΑΝ / ΠΡΟΣΤΕΘΗΚΑΝ ανα αγορα (φαβορι εντος/εκτος, αουτσαιντερ), κατηγορια Α & Β,
κανονες καθε διοργανωσης (UEL/UECL φαβ ≥4% dog ≥10% · UCL φαβ ≥10% dog ≥4%), πρωτη εμφανιση ≤72ω, Crown & SBOBET (μεσος ορος βιβλιων), ανα σεζον.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
NL = chr(10)
WG = np.round(np.arange(0.0, 1.01, 0.05), 2)
def blend_comp(cm):
    x = A[(A.comp == cm) & A.hasv].copy(); seas = sorted(x.sea.unique())
    x['vm'] = [VF[s][0] * lv + VF[s][1] for s, lv in zip(x.sea, x.lv_)]
    def lamW(y, w):
        T = y.lh.values + y.la.values; m = (1 - w) * (y.lh.values - y.la.values) + w * y.vm.values
        return np.maximum((T + m) / 2, .05), np.maximum((T - m) / 2, .05)
    lh1 = x.lh.values.copy(); la1 = x.la.values.copy()
    for s in seas:
        tr = x[x.sea != s]; w = WG[int(np.argmax([ll(tr, *lamW(tr, w)) for w in WG]))]
        te = (x.sea == s).values; a, b = lamW(x[te], w); lh1[te] = a; la1[te] = b
    return x.index, lh1, la1
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    P0 = picks_comp(cm)
    idx, lh1, la1 = blend_comp(cm)
    A_save = A[['lh', 'la']].copy()
    A.loc[idx, 'lh'] = lh1; A.loc[idx, 'la'] = la1
    P1 = picks_comp(cm)
    A[['lh', 'la']] = A_save
    ok = set(A.loc[idx, 'i'].astype(int))
    P0 = P0[P0.i.isin(ok)]; P1 = P1[P1.i.isin(ok)]
    k0 = set(zip(P0.i, P0.side, P0.bk)); k1 = set(zip(P1.i, P1.side, P1.bk))
    P0['st'] = ['κρατηθηκε' if k in k1 else 'ΚΟΠΗΚΕ' for k in zip(P0.i, P0.side, P0.bk)]
    P1['st'] = ['κρατηθηκε' if k in k0 else 'ΠΡΟΣΤΕΘΗΚΕ' for k in zip(P1.i, P1.side, P1.bk)]
    print(f'{NL}{"=" * 118}{NL}{lab} — σημερινο → με μηχανισμο αξιας · κελι = picks (ανα βιβλιο) · ROI · μοναδες')
    print(f'   {"κατηγορια / αγορα":20s} │ {"ΣΗΜΕΡΙΝΟ ολα":>22s} │ {"κοπηκαν":>22s} │ {"προστεθηκαν":>22s} │ {"ΜΕ ΑΞΙΑ ολα":>22s} │ σεζον σημερινο → με αξια')
    for c_ in ('A', 'B'):
        for nm, f in (('φαβορι εντος', lambda y: (y.kind == 'φαβ') & (y.ven == 'εντος')), ('φαβορι εκτος', lambda y: (y.kind == 'φαβ') & (y.ven == 'εκτος')),
                      ('αουτσαιντερ', lambda y: y.kind == 'dog')):
            a = P0[(P0.cat == c_) & f(P0)]; b = P1[(P1.cat == c_) & f(P1)]
            se = ' '.join(f'{s[2:]}:{100 * a[a.sea == s].pnl.mean():+.0f}→{100 * b[b.sea == s].pnl.mean():+.0f}' for s in sorted(set(a.sea) | set(b.sea)))
            print(f'   {c_} {nm:18s} │ {cell(a):>22s} │ {cell(a[a.st == "ΚΟΠΗΚΕ"]):>22s} │ {cell(b[b.st == "ΠΡΟΣΤΕΘΗΚΕ"]):>22s} │ {cell(b):>22s} │ {se}')
