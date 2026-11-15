"""ucl_totals_threshold_loso_fix.py — 16/10/2026 (Στελιος «τρεξτο»): ΕΠΑΝΑΛΗΨΗ του ucl_totals_threshold_loso (10/10, βαση του live κανονα
UCL over ≥4% / under ≥10%) ΧΩΡΙΣ τον κανονα «φρεσκια τιμη ≤24ω» στο snap_ou: το Nowgoal γραφει μονο ΑΛΛΑΓΕΣ γραμμης, αρα η τελευταια γνωστη
τιμη ισχυε ακομα — ο κανονας εκοβε ματς/ωρες χωρις αλλαγη και μετατοπιζε την «πρωτη εμφανιση» αργοτερα. Ιδια ροη πρωτης εμφανισης ≤72ω,
ιδια μηχανη, ιδιο LOSO. + πινακας ανα σταθερο κατωφλι (νεα μορφη / 4 σεζον, ανα βιβλιο & σεζον)."""
import sys
src = open('ucl_totals_threshold_loso.py', encoding='utf-8').read()
old = "    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None"
assert src.count(old) == 1
src = src.replace(old, "    if not prev: return None", 1)
exec(compile(src, 'ucl_totals_threshold_loso.py', 'exec'))
print('\n=== ΣΤΑΘΕΡΟ ΚΑΤΩΦΛΙ (ροη πρωτης εμφανισης ≤72ω) — picks ανα βιβλιο · ROI (Crown / SBOBET) · ανα σεζον')
for side in ('over', 'under'):
    for lab, pool in (('νεα μορφη', ('2425', '2526')), ('4 σεζον', SEAS)):
        print(f'   {side.upper()} {lab}:')
        for th in TH:
            f = stream(side, th, pool)
            if not len(f): continue
            bk = f.groupby('bk').pnl.mean(); ps = f.groupby('sea').pnl.mean()
            print(f'      ≥{int(th * 100):2d}%  {len(f) / 2:4.0f} picks  {100 * roi(f):+6.1f}%  (C {100 * bk.get("Crown", np.nan):+.0f} / S {100 * bk.get("SBOBET", np.nan):+.0f})  ' +
                  ' '.join(f'{s[2:]}:{100 * v:+.0f}' for s, v in ps.items()))
