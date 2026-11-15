"""travel_patterns.py — 17/10/2026 (Στελιος: «συνοψη για να μη μπερδευομαστε: μετα απο 1 ευρωπαικο, ΜΟΝΟΤΙΒΟ 1: πρωταθλημα χωρις ευρωπαικο την
επομενη μεσοβδομαδα · ΜΟΤΙΒΟ 2: Ευρωπη → πρωταθλημα → Ευρωπη. Ξεχωριστα εντος / εκτος. Επηρεαζεται η ομαδα; αξιζει η κοντρα της ή το under;»).
Πανω στο travel_fatigue_B.pkl (travel_fatigue_full: ομαδες Δυτ./Κεντρ. Ευρωπης, ευρωπαικα 2122-2526 + προκριματικα, ΜΟΝΟ πρωταθλημα (οχι κυπελλα),
1.5-6 μερες μετα το ευρωπαικο, αγορα κλεισιματος). ΜΟΤΙΒΟ 1 = επομενο ευρωπαικο >7 μερες μετα (ή κανενα) · ΜΟΤΙΒΟ 2 = ≤5 μερες μετα.
Στηλες: συνολο γκολ − αγορα (ολα τα ματς) · τυφλο UNDER κλεισ. · διαφορα − αγορα · τυφλο χαντικαπ ΚΟΝΤΡΑ (μονο οπου υπαρχουν γραμμες AH/OU)."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
B = pd.read_pickle('travel_fatigue_B.pkl')
B = B[(B.kind == 'dom') & B.rc.notna()].copy()
B['pat'] = np.where(B.eu_after <= 5, 'Ε→Π→Ε', np.where((B.eu_after > 7) | B.eu_after.isna(), 'Ε→Π', 'αλλο'))
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '   —'
def pc(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{100 * v.mean():+6.1f}% ({len(v):3d})' if len(v) >= 5 else f'   —   ({len(v):3d})'
TR = (('ευρωπαικο ΕΝΤΟΣ [ελεγχος]', lambda y: y.prev_home), ('εκτος <1.500 χλμ', lambda y: ~y.prev_home & (y.trip < 1500)),
      ('εκτος 1.500-2.500', lambda y: ~y.prev_home & (y.trip >= 1500) & (y.trip < 2500)), ('εκτος ≥2.500', lambda y: ~y.prev_home & (y.trip >= 2500)))
for pat, lab in (('Ε→Π', 'ΜΟΤΙΒΟ 1: Ευρωπη → Πρωταθλημα (χωρις ευρωπαικο την επομενη μεσοβδομαδα)'), ('Ε→Π→Ε', 'ΜΟΤΙΒΟ 2: Ευρωπη → Πρωταθλημα → Ευρωπη (ξανα ευρωπαικο ≤5 μερες μετα)')):
    print(f'\n{"=" * 130}\n{lab}')
    for where, m in (('ΠΡΩΤΑΘΛΗΜΑ ΕΝΤΟΣ', True), ('ΠΡΩΤΑΘΛΗΜΑ ΕΚΤΟΣ', False)):
        y0 = B[(B.pat == pat) & (B.nhome == m)]
        print(f'  — {where} —')
        print(f'   {"το ευρωπαικο πριν":28s} {"n":>5s} │ {"συνολο−αγ":>11s} {"UNDER (n)":>15s} │ {"διαφορα−αγ":>11s} {"βαζει−αγ":>10s} {"τρωει−αγ":>10s} {"ΚΟΝΤΡΑ AH (n)":>15s}')
        for tl, f in TR:
            y = y0[f(y0)]
            print(f'   {tl:28s} {len(y):5d} │ {ms(y.rt):>11s} {pc(y.und):>15s} │ {ms(y.rc):>11s} {ms(y.sf):>10s} {ms(y.sa):>10s} {pc(y.roi_opp):>15s}')
print(f'\n(μοτιβο «αλλο» = επομενο ευρωπαικο 5-7 μερες μετα: {int((B.pat == "αλλο").sum())} ματς — εκτος πινακων)')
