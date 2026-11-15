"""
intl_deepfav_config.py — ΣΥΝΤΕΛΕΣΤΕΣ ΥΠΕΡΟΧΗΣ ΓΙΑ ΤΑ ΒΑΘΙΑ ΦΑΒΟΡΙ (25/9/2026, αποφαση Στελιου «βαλε και τα 2 στο live»).
Το live βγαζει υπεροχη = a·diff με a μετρημενο ΧΩΡΙΣ αξια ροστερ (Μ1 0.491, Α/AV ~0.50), ενω στα Μ1/Μ3 το diff περιεχει και την αξια →
υπερεκτιμηση νικης φαβορι με 3+ (47% vs 37% στα μεγαλα φαβορι). Τεστ intl_window_test.py GD_FIX=deepfav: σωστη κλιση ΜΟΝΟ για pick φαβορι −2 και βαθυτερα
→ βαθια φαβορι +6.1→+15.6%, συνολο συναινεσης +10.5→+11.3% (ΠΕΡΝΑ, και στα 2 βιβλια).
Εδω: κλιση gd ~ diff (χωρις σταθερα) ανα μοντελο σε ΟΛΑ τα αγωνιστικα του backtest (intl_model_choice_v3) → intl_deepfav_config.json.
"""
import sys, json, numpy as np
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'cfg'}
exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D = G['D']; C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]
a = {m: float(np.sum(C[f'd_{m}'] * C.gd) / np.sum(C[f'd_{m}'] ** 2)) for m in ('M1', 'M2', 'M3')}
cfg = dict(a_deep={'H': a['M1'], 'A': a['M2'], 'AV': a['M3']}, line_max=-2.0, n=int(len(C)),
           note='υπεροχη βαθιων φαβορι = a_deep·diff (ιδιο T)· εφαρμοζεται ΜΟΝΟ οταν η πλευρα-φαβορι εχει handicap ≤ −2')
json.dump(cfg, open('intl_deepfav_config.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('intl_deepfav_config.json:', {k: round(v * 100, 3) for k, v in cfg['a_deep'].items()}, 'γκολ/100 Elo · n', len(C))
