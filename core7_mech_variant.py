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
if V.startswith('cur_'):                # 1/10: «σωστο SoS» cur_<ST>_<GLO>_<GHI> (SOS_MODE=current)
    _, st_, lo_, hi_ = V.split('_')
    assert 'ST = 1.5; GLO, GHI = 6, 13' in pre
    pre = pre.replace('ST = 1.5; GLO, GHI = 6, 13', f'ST = {float(st_)}; GLO, GHI = {int(lo_)}, {int(hi_)}')
    os.environ['SOS_MODE'] = 'current'
if V.startswith('sos_'):                # 1/10: sos_<ST>_<GLO>_<GHI> π.χ. sos_1.5_6_19 (παραθυρο σε ματς που εχουν παιχτει)
    _, st_, lo_, hi_ = V.split('_')
    assert 'ST = 1.5; GLO, GHI = 6, 13' in pre
    pre = pre.replace('ST = 1.5; GLO, GHI = 6, 13', f'ST = {float(st_)}; GLO, GHI = {int(lo_)}, {int(hi_)}')
if V.startswith('c2_'):                 # 1/10: c2_<ST2>_<GHI> = σωστο SoS 0.75 στις 7-14 (6-13 αντιπαλοι) ΚΑΙ βαρος ST2 απο 14 ως GHI αντιπαλους
    _, st2_, hi_ = V.split('_')
    assert 'ST = 1.5; GLO, GHI = 6, 13' in pre
    pre = pre.replace('ST = 1.5; GLO, GHI = 6, 13', f'ST = 0.75; ST2 = {float(st2_)}; GLO, GHI = 6, {int(hi_)}')
    old_ret = ("            return (r[0] * (lxx / max(mD, 1e-9)) ** ST, r[1] * (lxx / max(mA, 1e-9)) ** ST," + chr(10) +
               "                    r[2] * (lsx / max(mSA, 1e-9)) ** ST, r[3] * (lsx / max(mSF, 1e-9)) ** ST)")
    assert old_ret in pre, 'sosadj μορφη αλλαξε'
    pre = pre.replace(old_ret, old_ret.replace('** ST', '** _st').replace(
        '            return (', "            _st = ST if len(t['opp']) <= 13 else ST2" + chr(10) + '            return (', 1))
    os.environ['SOS_MODE'] = 'current'
if V == 'nosos':                       # 1/10: χωρις διορθωση προγραμματος (SoS) στις αγων. 7-14
    assert 'ST = 1.5;' in pre
    pre = pre.replace('ST = 1.5;', 'ST = 0.0;')
g = {'__name__': 'mech'}
exec(pre, g)
g['P'].to_csv(f'core7_mech_preds_{V}.csv', index=False)
print(V, 'OK', len(g['P']))
