"""uel_value_tau025_all.py — 15/10/2026 (Στελιος: «το −0.25 δεν δουλευει στις υπολοιπες αγορες;»). Europa, φιλτρο αξιας τ = −0.25 σε ΚΑΘΕ αγορα:
χωρις φιλτρο vs με φιλτρο — ανα βιβλιο, ανα σεζον, κριτηρια (θετικο 2 βιβλια + ≥3/4 σεζον + οι 2 νεας μορφης), κινηση αγορας. + ο LIVE κανονας φαβ εντος.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
P = picks_comp('EuropaLeague'); P = P[P.dis.notna()]
def line(y):
    mb = y.groupby('bk').pnl.mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]; n = y.groupby('bk').size().mean()
    k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
    return (f"{n:3.0f} picks {100 * mb.mean():+6.1f}% ({mb.mean() * n:+5.1f}μ) · σεζον " + ' '.join(f"{s[2:]}:{100 * v:+.0f}%" for s, v in ps.items()) +
            f" · κινηση {y.clv.mean():+.3f} │ {'✓' if k2 else '✗'}")
for nm, f in (('Α φαβορι εντος', (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εντος')), ('Α φαβορι εκτος', (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εκτος')),
              ('Α αουτσαιντερ', (P.cat == 'A') & (P.kind == 'dog')), ('Β φαβορι', (P.cat == 'B') & (P.kind == 'φαβ')), ('Β αουτσαιντερ', (P.cat == 'B') & (P.kind == 'dog'))):
    y = P[f]
    print(f'{nm}'); print(f'   χωρις φιλτρο  {line(y)}'); print(f'   τ −0.25       {line(y[y.dis > -.25])}')
