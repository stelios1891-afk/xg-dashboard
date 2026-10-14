"""euro_team_value_build.py — 15/10/2026. Βοηθητικο: «ΣΥΝΗΘΙΣΜΕΝΗ» αξια ενδεκαδας καθε ομαδας ΠΡΙΝ το ευρωπαικο ματς (γνωστη απο πριν, οχι η ενδεκαδα
της ημερας) = διαμεσος των 5 τελευταιων εγχωριων βασικων ενδεκαδων (αξιες παικτων στην ημερομηνια, οπως uel_lineup_rule3) ως 60 μερες πριν (≥3),
αλλιως ως 150 μερες (≥2). → euro_team_value.pkl {mid: (vh, va)}
"""
import pickle
src = open('uel_lineup_rule3.py', encoding='utf-8').read().split('import collections\ncov = collections.Counter()')[0]
exec(src)
def usual(tid, ko):
    L = DOMV.get(int(tid), [])
    for days, need in ((60, 3), (150, 2)):
        prev = [z[1] for z in L if ko - pd.Timedelta(days=days) <= z[0] < ko - pd.Timedelta(hours=12)][-5:]
        if len(prev) >= need: return float(np.median(prev))
    return None
OUT = {}
for mid, v in SQ.items():
    j = VI.get(str(mid))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j]); th = (v.get('h') or {}).get('t'); ta = (v.get('a') or {}).get('t')
    if not th or not ta: continue
    a, b = usual(th, ko), usual(ta, ko)
    if a and b: OUT[str(mid)] = (a, b)
pickle.dump(OUT, open('euro_team_value.pkl', 'wb'))
print(len(OUT), 'ευρωπαικα ματς με συνηθισμενη αξια και των 2')
