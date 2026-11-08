"""euro_motivation_check.py — ευαισθησια των ευρηματων του euro_motivation (θελει γκολ / νεκρη) ανα σεζον, μορφη, οριο."""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
R = pd.read_pickle('euro_motivation_rows.pkl')
def roi(x):
    v = x[['ah_Crown', 'ah_SBOBET']]; n = v.notna().any(axis=1).sum()
    if n == 0: return 'n   0'
    ps = x.assign(p=v.mean(axis=1)).groupby('sea').p.mean()
    return f'n{n:4d} ROI {100 * v.stack().mean():+6.1f}% (C {100 * v.ah_Crown.mean():+.0f}/S {100 * v.ah_SBOBET.mean():+.0f}) σεζ {int((ps > 0).sum())}/{ps.size}'
print('ΘΕΛΕΙ ΓΚΟΛ — τυφλο χαντικαπ υπερ της ομαδας, ανα οριο αναγκης:')
for t in (0.05, 0.10, 0.15, 0.20, 0.30):
    print(f'   αναγκη ≥ {t:.2f}: {roi(R[R.gn >= t])}')
x = R[R.gn >= .10]
print('   ανα σεζον: ' + ' · '.join(f'{s}: {roi(x[x.sea == s])}' for s in sorted(x.sea.unique())))
print('   ανα μορφη: ' + ' · '.join(f'{"νεα" if n else "ομιλοι"}: {roi(x[x.new == n])}' for n in (True, False)))
print('   ανα διοργανωση: ' + ' · '.join(f'{c[:4]}: {roi(x[x.comp == c])}' for c in sorted(x.comp.unique())))
print('   ανα ρολο: ' + ' · '.join(f'{l}: {roi(x[m])}' for l, m in (('φαβ ≤−0.5', x.ahL_Crown <= -.5), ('κοντα', x.ahL_Crown.abs() < .5), ('αουτ ≥+0.5', x.ahL_Crown >= .5))))
print('   αντιπαλος: ' + ' · '.join(f'{l}: {roi(x[x.opp_status == l])}' for l in ('νεκρη', 'χαμηλο', 'υψηλο')))
print(f'   μεσο κινητρο νικης αυτων {x.ws.mean():.2f} · ματς ανα σεζον ~{len(x) / 4:.0f}')
print('\nΥΨΗΛΟ ΚΙΝΗΤΡΟ ΧΩΡΙΣ αναγκη γκολ (ελεγχος: μηπως ειναι απλως «κινητρο»):', roi(R[(R.status == 'υψηλο') & (R.gn < .10)]))
print('ΚΙΝΗΤΡΟ ΝΙΚΗΣ ανα επιπεδο (τυφλο χαντικαπ υπερ):')
for lo, hi in ((0, .05), (.05, .2), (.2, .5), (.5, .8), (.8, 1.01)):
    print(f'   {lo:.2f}-{hi:.2f}: {roi(R[(R.ws >= lo) & (R.ws < hi)])}')
print('\nΝΕΚΡΗ — τυφλο χαντικαπ υπερ, ανα σεζον: ' + ' · '.join(f'{s}: {roi(R[(R.status == "νεκρη") & (R.sea == s)])}' for s in sorted(R.sea.unique())))
