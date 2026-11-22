"""euro_xi_abs_build.py — 14/10/2026. Βοηθητικο: ΑΠΟΛΥΤΗ αξια βασικης ενδεκαδας (αθροισμα αξιων των 11 στην ημερομηνια του ματς, οπως
uel_lineup_rule3) γηπεδουχου & φιλοξενουμενου σε ΟΛΑ τα ευρωπαικα ματς (UCL/UEL/UECL) → euro_xi_abs.pkl {mid: (vh, va)}
"""
import pickle
src = open('uel_lineup_rule3.py', encoding='utf-8').read().split('import collections\ncov = collections.Counter()')[0]
exec(src)
OUT = {}
for mid, v in SQ.items():
    j = VI.get(str(mid))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j])
    vh = xi_value((v.get('h') or {}), ko); va = xi_value((v.get('a') or {}), ko)
    if vh and va: OUT[str(mid)] = (vh, va)
pickle.dump(OUT, open('euro_xi_abs.pkl', 'wb'))
print(len(OUT), 'ευρωπαικα ματς με αξια και των 2 ενδεκαδων')
