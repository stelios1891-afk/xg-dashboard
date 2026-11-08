"""euro_dead_types.py — 10/10/2026 (Στελιος: «με το νεκρη ποιες ομαδες μετρας; μονο τις αποκλεισμενες;»). Ειδη «νεκρης» + τα picks μας σε καθε ειδος."""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
R = pd.read_pickle('euro_motivation_seed_rows.pkl')
def typ(r):
    if r.status != 'νεκρη': return None
    p = r.probs
    if r.new:
        p8, p24 = p['8αδα'], p['24αδα']
        if p24['W'] < .05: return 'νεα: ΗΔΗ ΑΠΟΚΛΕΙΣΜΕΝΗ'
        if p8['L'] > .95: return 'νεα: ΣΙΓΟΥΡΗ ΣΤΗΝ 8ΑΔΑ'
        if p24['L'] > .95 and p8['W'] < .05: return 'νεα: ΚΛΕΙΔΩΜΕΝΗ 9-24 (playoff)'
        return 'νεα: πρακτικα κλειδωμενη (<5% αλλαγη)'
    p1, p2, p3 = p['1η'], p['2αδα'], p['3αδα']
    if p1['L'] > .95: return 'ομιλοι: ΣΙΓΟΥΡΗ 1η'
    if p2['L'] > .95 and p1['W'] < .05: return 'ομιλοι: ΚΛΕΙΔΩΜΕΝΗ 2η'
    if p3['W'] < .05: return 'ομιλοι: ΚΛΕΙΔΩΜΕΝΗ 4η (εκτος)'
    if p3['L'] > .95 and p2['W'] < .05: return 'ομιλοι: ΚΛΕΙΔΩΜΕΝΗ 3η (πεφτει διοργανωση)'
    return 'ομιλοι: πρακτικα κλειδωμενη (<5% αλλαγη)'
R['typ'] = [typ(r) for r in R.itertuples()]
D = R[R.typ.notna()]
print(f'«ΝΕΚΡΕΣ» συνολο {len(D)}:')
for t, x in D.groupby('typ'):
    print(f'   {t:44s} {len(x):3d} · xG υπερ−μοντελο {(x.xf - x.lf).mean():+.2f} · γκολ υπερ−μοντελο {(x.gf - x.lf).mean():+.2f}  π.χ. ' + ', '.join(x.team.head(3)))
