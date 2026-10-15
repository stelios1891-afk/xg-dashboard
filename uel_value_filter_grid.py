"""uel_value_filter_grid.py — 15/10/2026 (Στελιος: «πως ακριβως το χρησιμοποιεις τωρα — τρεξε τεστ, ισως υπαρχει καλυτερος τροπος, πχ πιο επιθετικος»).
ΦΙΛΤΡΟ ΑΞΙΑΣ: διαφωνια = (τι λεει η αξια − τι λεει το μοντελο) για την ομαδα του pick, σε γκολ. «Τι λεει η αξια» = k·ln(συνηθισμενη αξια ενδεκαδας γηπ/φιλ)
+ εδρα, ευθεια απο τις αλλες 3 σεζον ολων των ευρωπαικων. ΠΑΙΖΕΤΑΙ το pick μονο αν διαφωνια > τ.
  τ = −1.0 / −0.75 / −0.5 (σημερινη προταση) / −0.25 / 0 / +0.25  — οσο πιο ψηλα το τ, τοσο πιο ΕΠΙΘΕΤΙΚΟ (κοβει περισσοτερα· στο τ ≥ 0 παιζεις
  μονο οταν η αξια ΣΥΜΦΩΝΕΙ με το μοντελο οτι η ομαδα αξιζει τουλαχιστον οσο λεει το μοντελο)
ανα αγορα & κατηγορια, Europa + επαναληψη Conference/Champions · + τ επιλεγμενο ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ (απο τις αλλες 3 σεζον, μεγιστες μοναδες) για καθε αγορα.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
NL = chr(10)
TS = (-9, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25)
TL = {-9: 'χωρις φιλτρο'}
def cell(y):
    if len(y) == 0: return '      —'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean()
    return f'{n:3.0f} {100 * m.mean():+5.0f}% {m.mean() * n:+5.1f}μ'
GR = (('Α φαβορι εντος', lambda P: (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εντος')),
      ('Α φαβορι εκτος', lambda P: (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εκτος')),
      ('Α αουτσαιντερ', lambda P: (P.cat == 'A') & (P.kind == 'dog')),
      ('Β φαβορι', lambda P: (P.cat == 'B') & (P.kind == 'φαβ')),
      ('Β αουτσαιντερ', lambda P: (P.cat == 'B') & (P.kind == 'dog')))
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    P = picks_comp(cm); P = P[P.dis.notna()]
    print(f'{NL}{"=" * 130}{NL}{lab} — παιζεται μονο αν διαφωνια > τ · κελι = picks ανα βιβλιο · ROI · μοναδες')
    print(f'   {"αγορα":16s} │' + '│'.join(f'{(TL.get(t) or f"τ {t:+.2f}"):>19s}' for t in TS) + '│ τ εκτος δειγματος → αποτελεσμα')
    for nm, f in GR:
        y = P[f(P)]
        cells = [cell(y[y.dis > t]) for t in TS]
        # LOSO: τ απο τις αλλες σεζον (μεγιστες μοναδες), εφαρμογη στην κρατημενη
        outs = []; chosen = []
        for s in sorted(y.sea.unique()):
            tr = y[y.sea != s]
            sc = {t: tr[tr.dis > t].groupby('bk').pnl.sum().mean() if len(tr[tr.dis > t]) else 0 for t in TS}
            t = max(sc, key=lambda k: sc[k]); chosen.append(t); outs.append(y[(y.sea == s) & (y.dis > t)])
        Z = pd.concat(outs) if outs else y.iloc[:0]
        print(f'   {nm:16s} │' + '│'.join(f'{c:>19s}' for c in cells) + f'│ ' + ','.join('—' if t == -9 else f'{t:+.2f}' for t in chosen) + f' → {cell(Z)}')
