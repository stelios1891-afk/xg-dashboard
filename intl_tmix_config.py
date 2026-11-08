"""
intl_tmix_config.py — ΒΑΡΗ ΝΕΟΥ T ΓΙΑ ΤΑ OVER (26/9/2026, αποφαση Στελιου «βαλτο», μονο στα over).
T_over = b0 + b1·T_σημερα + b2·(λh_xG + λa_xG)· b = OLS στα πραγματικα γκολ ΟΛΩΝ των αγωνιστικων του backtest (intl_model_choice_v3 D),
ανα εκδοχη (H=Μ1, A=Μ2, AV=Μ3), xG ομαδων N=12 (intl_xg_teamN12.csv, n≥3). Τεστ: intl_tmix_eval / intl_tmix_n_eval
(over συναινεσης 72ω +13.2→+17.5%, ακριβεια γκολ MAE 1.383→1.344). Εξοδος: intl_tmix_config.json
"""
import sys, os, json, contextlib, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'cfg'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, T_of = G['D'], G['T_of']
X = pd.read_csv('intl_xg_teamN12.csv', dtype={'mid': str}); X = X[X.n >= 3]; XG = dict(zip(X.mid, X.xgsum))
C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]
cfg = {}
for v, m in (('H', 'M1'), ('A', 'M2'), ('AV', 'M3')):
    tr = [(T_of(getattr(r, f'd_{m}'), r), XG[str(r.mid)], r.tot) for r in C.itertuples() if str(r.mid) in XG]
    b = np.linalg.lstsq(np.array([[1, a, x] for a, x, _ in tr]), np.array([t for *_, t in tr]), rcond=None)[0]; cfg[v] = [float(x) for x in b]
cfg['_note'] = 'T_over = b0 + b1·T_σημερα + b2·xG ομαδων (N=12)· μονο για OVER· αν λειπει xG (n<3) → T σημερα'
json.dump(cfg, open('intl_tmix_config.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('intl_tmix_config.json:', {k: [round(x, 3) for x in v] for k, v in cfg.items() if not k.startswith('_')}, f'· n={len(tr)}')
