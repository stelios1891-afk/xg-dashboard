# -*- coding: utf-8 -*-
"""travel_opponent.py — 25/10/2026 (Στελιος: «τρεξε το 4» = η ΚΑΤΑΣΤΑΣΗ ΤΟΥ ΑΝΤΙΠΑΛΟΥ στα σεναρια κουρασης). Δεδομενα: travel_scenarios.pkl
(επομενο ματς πρωταθληματος 1.5-6 μερες μετα απο ευρωπαικο, 2021-26), ΜΟΝΟ ματς με πραγματικη γραμμη AH/OU (CORE7, Crown/Bet365).
ΚΑΤΗΓΟΡΙΕΣ (ΠΡΟ-ΔΗΛΩΜΕΝΕΣ), ανα ματς:
  Α  μονο η μια ομαδα ειχε Ευρωπη ≤6μ — ο αντιπαλος ΞΕΚΟΥΡΑΣΤΟΣ (≥5 μερες)  · Α0 Ευρωπη ΕΝΤΟΣ (ελεγχος) · Α1 Ευρωπη ΕΚΤΟΣ <1.500 · Α2 ΕΚΤΟΣ ≥1.500
  Β  μονο η μια ομαδα ειχε Ευρωπη — ο αντιπαλος επαιξε κι αυτος <5 μερες πριν (πρωταθλημα/κυπελλο μεσοβδομαδα)
  Γ  ΚΑΙ ΟΙ ΔΥΟ ειχαν Ευρωπη ≤6μ · Γ1 και οι δυο ΕΚΤΟΣ στην Ευρωπη («ταξιδεψαν και οι δυο») · Γ2 τουλαχιστον ενας ΕΝΤΟΣ
  + ΞΕΚΟΥΡΑΣΗ ΣΕ ΩΡΕΣ της ομαδας της Ευρωπης (Α/Β): <66ω (π.χ. Πεμ βραδυ → Κυρ απογευμα) · 66-80ω · >80ω · και ΔΙΑΦΟΡΑ με τον αντιπαλο (ωρες).
ΜΕΤΡΗΣΕΙΣ: γκολ − αγορα κλεισιματος (συνολο) · under κλεισ. · (μονο Α/Β) διαφορα της ομαδας της Ευρωπης − αγορα · χαντικαπ ΚΟΝΤΡΑ της.
ΤΑ ΜΑΤΣ Γ ΜΕΤΡΙΟΥΝΤΑΙ ΜΙΑ ΦΟΡΑ. ΚΡΙΤΗΡΙΟ (ιδιο με travel_scenarios): ≥40 bets, ιδια φορα ≥3/4 σεζον, |t|≥2, under >0 ΚΑΙ > ελεγχου Α0."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
D = pd.read_pickle('travel_scenarios.pkl')
D = D[D.src == 'AH/OU'].copy()
D.loc[D.orest > 14, 'orest'] = np.nan                      # αντιπαλος χωρις προηγουμενο ματς στα δεδομενα (π.χ. νεοφωτιστος) → αγνωστο
D['rest_h'] = D.rest * 24; D['diff_h'] = (D.rest - D.orest) * 24
SEAS = ['2223', '2324', '2425', '2526']
eu_away = D.fam.str[:2] != 'Σ0'


def cat(r):
    if r['opp_eu']:
        return 'Γ1 και οι δυο ΕΚΤΟΣ στην Ευρωπη' if (r['opp_eu_away'] and r['fam'][:2] != 'Σ0') else 'Γ2 και οι δυο Ευρωπη (τουλ. ενας εντος)'
    if not np.isfinite(r['orest']):
        return None
    if r['orest'] >= 5:
        if r['fam'][:2] == 'Σ0': return 'Α0 μονο η μια · Ευρωπη ΕΝΤΟΣ · αντιπ. ξεκουραστος (ελεγχος)'
        return 'Α1 μονο η μια · Ευρωπη ΕΚΤΟΣ <1.500 · αντιπ. ξεκουραστος' if r['trip'] < 1500 else 'Α2 μονο η μια · Ευρωπη ΕΚΤΟΣ ≥1.500 · αντιπ. ξεκουραστος'
    return 'Β μονο η μια · αντιπαλος επαιξε κι αυτος <5μ'


D['cat'] = [cat(r) for r in D.to_dict('records')]


def stat(z, lab, base=None, team=True):
    rt = z.rt.dropna(); u = z.und.dropna()
    if len(rt) < 5:
        return f'   {lab:62s} n {len(rt)}'
    se = rt.std(ddof=1) / np.sqrt(len(rt)); t = rt.mean() / se if se > 0 else np.nan
    sg = [np.sign(g.rt.mean()) for _, g in z[z.sea.isin(SEAS)].groupby('sea') if len(g) >= 3]
    neg, pos = sum(1 for s in sg if s < 0), sum(1 for s in sg if s > 0)
    same, dirn = (neg, '−') if neg >= pos else (pos, '+')
    useas = ' '.join(f"{s[2:]}:{100 * g.und.mean():+.0f}" for s, g in z[z.und.notna()].groupby('sea'))
    ok = len(u) >= 40 and same >= 3 and abs(t) >= 2 and u.mean() > 0 and (base is None or u.mean() > base)
    tm = (f" │ διαφορα ομαδας Ευρωπης−αγορα {z.rc.mean():+.2f} │ χαντ. κοντρα {100 * z.roi_opp.mean():+5.1f}%") if team else ''
    return (f"   {lab:62s} n {len(rt):4d} │ γκολ−αγορα {rt.mean():+.2f}±{se:.2f} (t {t:+.1f}) {dirn} {same}/{len(sg)} │ under κλεισ. "
            f"{100 * u.mean():+6.1f}% ({len(u):3d}) [{useas}]" + tm + ('  ✓ ΣΗΜΑ' if ok else ''))


NL = chr(10)
print('Η ΚΑΤΑΣΤΑΣΗ ΤΟΥ ΑΝΤΙΠΑΛΟΥ — επομενο ματς πρωταθληματος μετα απο ευρωπαικο, CORE7 με γραμμη AH/OU, 2022-26 (κλεισιμο Crown/Bet365)')
print('γκολ−αγορα: − = μπηκαν λιγοτερα απο τη γραμμη συνολων · under κλεισ. = ROI under στο κλεισιμο · διαφορα: + = η ομαδα της Ευρωπης πηγε καλυτερα απο την αγορα')
for venue, vlab in ((None, 'ΟΛΑ'), (True, 'η ομαδα της Ευρωπης ΕΝΤΟΣ στο πρωταθλημα'), (False, 'η ομαδα της Ευρωπης ΕΚΤΟΣ στο πρωταθλημα')):
    print(f"{NL}{'=' * 160}{NL}### {vlab}")
    Z = D if venue is None else D[D.nhome == venue]
    base = Z[Z.cat.fillna('').str.startswith('Α0')].und.mean()
    for c in sorted(Z.cat.dropna().unique()):
        z = Z[Z.cat == c]
        if c.startswith('Γ'):
            z = z.drop_duplicates('mid')                    # το ματς μετραει μια φορα
        print(stat(z, c, None if c.startswith('Α0') else base, team=not c.startswith('Γ')))
    if venue is None:
        G1 = Z[Z.cat.fillna('').str.startswith('Γ1')].drop_duplicates('mid')
        for lab, m in (('   └ Γ1 και οι δυο ταξιδι <1.500', (G1.trip < 1500) & (G1.opp_trip < 1500)),
                       ('   └ Γ1 τουλαχιστον ενας ≥1.500', (G1.trip >= 1500) | (G1.opp_trip >= 1500)),
                       ('   └ Γ1 και οι δυο ≥1.500', (G1.trip >= 1500) & (G1.opp_trip >= 1500))):
            print(stat(G1[m], lab, base, team=False))
print(f"{NL}{'=' * 160}{NL}### ΞΕΚΟΥΡΑΣΗ ΣΕ ΩΡΕΣ — ομαδα της Ευρωπης, Ευρωπη ΕΚΤΟΣ, αντιπαλος ΧΩΡΙΣ Ευρωπη (Α1+Α2+Β)")
Z = D[D.cat.fillna('').str.match('Α1|Α2|Β')]
base = D[D.cat.fillna('').str.startswith('Α0')].und.mean()
for lab, m in (('ξεκουραση <66 ωρες', Z.rest_h < 66), ('66-80 ωρες', (Z.rest_h >= 66) & (Z.rest_h < 80)), ('>80 ωρες', Z.rest_h >= 80)):
    print(stat(Z[m], lab, base))
print('   — διαφορα ξεκουρασης με τον αντιπαλο —')
for lab, m in (('≥48 ωρες ΛΙΓΟΤΕΡΗ απο τον αντιπαλο', Z.diff_h <= -48), ('24-48 ωρες λιγοτερη', (Z.diff_h > -48) & (Z.diff_h <= -24)),
               ('<24 ωρες διαφορα ή περισσοτερη', Z.diff_h > -24)):
    print(stat(Z[m], lab, base))
print(f"{NL}(ελεγχος Α0 — Ευρωπη ΕΝΤΟΣ, αντιπαλος ξεκουραστος — ανα ωρες ξεκουρασης, για συγκριση)")
Z0 = D[D.cat.fillna('').str.startswith('Α0')]
for lab, m in (('ξεκουραση <66 ωρες', Z0.rest_h < 66), ('66-80 ωρες', (Z0.rest_h >= 66) & (Z0.rest_h < 80)), ('>80 ωρες', Z0.rest_h >= 80)):
    print(stat(Z0[m], lab))
