"""uel_bfav_value_criteria.py — 15/10/2026 (Στελιος: «μονο το Europa μας νοιαζει»). Europa, φαβορι κατηγοριας Β + φιλτρο αξιας (παιζεται μονο αν
διαφωνια αξια−μοντελο > τ), τ = −0.5 / −0.25 / 0: ΠΛΗΡΗ κριτηρια — ανα βιβλιο, ανα σεζον, νεα μορφη (2425+2526), εντος/εκτος, κινηση αγορας.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
P = picks_comp('EuropaLeague'); P = P[P.dis.notna() & (P.cat == 'B') & (P.kind == 'φαβ')]
for t in (-9, -0.5, -0.25, 0.0):
    for nm, m_ in (('ολα', P.ven.notna()), ('εντος', P.ven == 'εντος'), ('εκτος', P.ven == 'εκτος')):
        y = P[m_ & (P.dis > t)]
        if len(y) < 4: continue
        mb = y.groupby('bk').pnl.mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
        k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
        print(f"{'χωρις φιλτρο' if t == -9 else f'τ {t:+.2f}':12s} {nm:5s} {len(y) / 2:3.0f} picks · Crown {100 * mb.get('Crown', np.nan):+.0f}% SBOBET {100 * mb.get('SBOBET', np.nan):+.0f}% · "
              f"σεζον " + ' '.join(f"{s[2:]}:{100 * v:+.0f}%({(y.sea == s).sum() // 2})" for s, v in ps.items()) + f" · κινηση αγορας {y.clv.mean():+.3f} │ κριτηρια {'✓' if k2 else '✗'}")
