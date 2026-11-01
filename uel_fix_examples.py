"""uel_fix_examples.py — 15/10/2026 (Στελιος: «θελω τα ματς αναλυτικα: αποδοσεις πριν, αποδοσεις μετα και αγορα — 10 που κοπηκαν και 10 που
προστεθηκαν · μονο στην Α μπηκε η διορθωση του τεντωματος; οχι στη Β; εκει ειναι πολλες ομαδες που κυριαρχουν εγχωρια»).
Ιδιο περιβαλλον με uel_fix_cut_picks (Europa 2223-2526, ΒΕ με LOSO παραμετρους — εκτιμημενες σε ΟΛΕΣ τις κατηγοριες), κανονες picks UEL.
Για καθε pick: γραμμη, ΑΠΟΔΟΣΗ ΑΓΟΡΑΣ, ΔΙΚΑΙΗ ΑΠΟΔΟΣΗ σημερινου μοντελου (πριν) και διορθωμενου (μετα) στην ιδια γραμμη, edge πριν/μετα, αποτελεσμα.
Κατηγορια Α (FotMob και οι 2) και Β (η μια χωρις FotMob).
"""
import sys
exec(open('uel_fix_cut_picks.py', encoding='utf-8').read().split("xa_ = x[x.cat == 'A']")[0])
def fair_e(lh, la, side, ln, o):
    D_ = sdist(lh, la); f = cover_q if ln <= -0.5 else picks.p_cover
    pw, pp = f(D_, side, ln); return (1 - pp) / max(pw, 1e-9), edge(pw, pp, o)
for CAT, lab in (('A', 'ΚΑΤΗΓΟΡΙΑ Α (FotMob και οι 2)'), ('B', 'ΚΑΤΗΓΟΡΙΑ Β (η μια ομαδα χωρις FotMob)')):
    xc = x[x.cat == CAT]
    REC = []
    for r in xc.itertuples():
        i = int(r.i)
        _, p0 = first_pick(i, r.lh, r.la); _, p1 = first_pick(i, r.lh3, r.la3)
        hn, an = NM.get(i, ('?', '?'))
        for side in set(p0) | set(p1):
            a, b = p0.get(side), p1.get(side)
            st = 'κρατηθηκε' if a and b else ('ΚΟΠΗΚΕ' if a else 'ΠΡΟΣΤΕΘΗΚΕ')
            pk = a or b
            f0, e0 = fair_e(r.lh, r.la, side, pk['ln'], pk['o']); f1, e1 = fair_e(r.lh3, r.la3, side, pk['ln'], pk['o'])
            REC.append(dict(st=st, sea=r.sea, match=f'{hn} - {an}', team=hn if side == 1 else an, kind=pk['kind'], ven='εντος' if side == 1 else 'εκτος',
                            ln=pk['ln'], o=pk['o'], f0=f0, f1=f1, e0=e0, e1=e1, gd=GD[i] * side, score=f'{int(GH[i])}-{int(GA[i])}', pnl=pk['pnl']))
    R = pd.DataFrame(REC)
    print(f'\n{"=" * 120}\n{lab} — {len(xc)} ματς')
    for st in ('ΚΟΠΗΚΕ', 'κρατηθηκε', 'ΠΡΟΣΤΕΘΗΚΕ'):
        y = R[R.st == st]
        print(f'   {st:11s} {len(y):3d} picks · ROI {100 * y.pnl.mean():+6.1f}% · μοναδες {y.pnl.sum():+5.1f}')
    y0 = R[R.st != 'ΠΡΟΣΤΕΘΗΚΕ']; y1 = R[R.st != 'ΚΟΠΗΚΕ']
    print(f'   ΣΗΜΕΡΙΝΟ ολα {len(y0)} picks · ROI {100 * y0.pnl.mean():+6.1f}% · μοναδες {y0.pnl.sum():+5.1f}  →  ΔΙΟΡΘΩΜΕΝΟ ολα {len(y1)} picks · ROI {100 * y1.pnl.mean():+6.1f}% · μοναδες {y1.pnl.sum():+5.1f}')
    for st, key, asc in (('ΚΟΠΗΚΕ', 'drop', False), ('ΠΡΟΣΤΕΘΗΚΕ', 'gain', False)):
        y = R[R.st == st].copy()
        y['d'] = (y.e0 - y.e1) if st == 'ΚΟΠΗΚΕ' else (y.e1 - y.e0)
        y = y.sort_values('d', ascending=False).drop_duplicates('match').head(10)
        print(f'\n   10 ΠΟΥ {"ΚΟΠΗΚΑΝ" if st == "ΚΟΠΗΚΕ" else "ΠΡΟΣΤΕΘΗΚΑΝ"} (με τη μεγαλυτερη αλλαγη)')
        print(f'   {"σεζ":4s} {"ματς":40s} {"pick":28s} {"αγορα":>6s} │ {"δικαιη ΠΡΙΝ":>11s} {"edge":>6s} │ {"δικαιη ΜΕΤΑ":>11s} {"edge":>6s} │ σκορ  αποτ.')
        for r in y.itertuples():
            pk = f'{r.team[:16]} {r.ln:+.2f} ({r.kind} {r.ven})'
            print(f'   {r.sea:4s} {r.match[:40]:40s} {pk[:28]:28s} {r.o:6.2f} │ {r.f0:11.2f} {100 * r.e0:+5.0f}% │ {r.f1:11.2f} {100 * r.e1:+5.0f}% │ {r.score:5s} {r.pnl:+.2f}')
