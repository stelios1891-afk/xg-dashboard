"""
core7_mech_variant.py — 28/9/2026 «ανατομια της συμπιεσης» (Στελιος): χτιζει προβλεψεις της live μηχανης (europe_test.py, ΟΛΕΣ οι αγωνιστικες)
με ΕΝΑΝ μηχανισμο αλλαγμενο. Χρηση: python core7_mech_variant.py <variant>
  base     = σημερινο (teamgame_inputs_5s_wf.csv)
  nocomp   = χωρις Caley συμπιεση μεγαλων ευκαιριων (np_raw αντι compressed+rescale)
  pen76    = πεναλτι 0.76 xG αντι 0.25
  both     = nocomp + pen76
  k4       = warm-start K=4 αντι 8 (ελαφρυτερη ελξη προς περσινο)
Εξοδος: core7_mech_preds_<variant>.csv. Δεν αγγιζει τιποτα live.
"""
import sys, os
import pandas as pd
V = sys.argv[1]
src_csv = 'teamgame_inputs_5s_wf.csv'
if V in ('nocomp', 'pen76', 'both'):
    T = pd.read_csv(src_csv)
    np_part = T['np_raw'] if V in ('nocomp', 'both') else T['comp_np_scaled']
    pen_w = 0.76 if V in ('pen76', 'both') else 0.25
    T['xg_model'] = np_part + pen_w * T['pen'] + T['red_xg']
    T['xgps'] = T['xg_model'] / T['ns_eff'].clip(lower=1)
    csv = f'tmp_mech_inputs_{V}.csv'; T.to_csv(csv, index=False)
else:
    csv = src_csv
import sos_test
_orig = sos_test.load_matches_5s
sos_test.load_matches_5s = lambda leagues, seasons, csv_=None, **k: _orig(leagues, seasons, csv=csv)
src = open('europe_test.py', encoding='utf-8').read()
pre = src[:src.index("P = P[P.md >= GLO].copy()")]
if V == 'k4':
    assert 'K = 8.0;' in pre
    pre = pre.replace('K = 8.0;', 'K = 4.0;')
g = {'__name__': 'mech'}
exec(pre, g)
g['P'].to_csv(f'core7_mech_preds_{V}.csv', index=False)
print(V, 'OK', len(g['P']))
