"""uel_xi_ratios_build.py — 14/10/2026. Βοηθητικο: ποσοστο ενδεκαδας (αξια βασικων στην ημερομηνια του ματς / διαμεσος 5 εγχωριων, οπως
uel_lineup_rule3) για γηπεδουχο & φιλοξενουμενο σε ΟΛΑ τα ματς UEL/UECL + φαβορι αγορας (χαντικαπ 1ω, Crown αλλιως SBOBET) → uel_xi_ratios.pkl
"""
import sys, pickle
src = open('uel_lineup_rule3.py', encoding='utf-8').read().split('import collections\ncov = collections.Counter()')[0]
exec(src)
OUT = {}
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague'): continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j])
    rh, _ = ratio2(MIDS[i], 'h', ko); ra, _ = ratio2(MIDS[i], 'a', ko)
    s = snap_ah(MIDS[i], 'Crown', 1) or snap_ah(MIDS[i], 'SBOBET', 1)
    fav = (1 if s[0] < 0 else (-1 if s[0] > 0 else 0)) if s else 0
    OUT[str(MIDS[i])] = (rh, ra, fav)
pickle.dump(OUT, open('uel_xi_ratios.pkl', 'wb'))
print(len(OUT), 'ματς ·', sum(1 for v in OUT.values() if np.isfinite(v[0]) and np.isfinite(v[1])), 'με γνωστες και τις 2 ενδεκαδες')
