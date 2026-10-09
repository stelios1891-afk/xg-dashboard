"""euro_blend_dump.py — βοηθητικο του τεστ μιξης: τρεχει τη σημερινη ευρωπαικη αλυσιδα (uel_battery harness) με W2_IN=<pkl> και σωζει λ/picks.
Χρηση: python euro_blend_dump.py euro_v6w2_preds_bl0.8.pkl 0.8"""
import sys, os, io, pickle, contextlib
import numpy as np
os.environ['W2_IN'] = sys.argv[1]; tag = sys.argv[2]
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'bd'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
P0 = g['make_picks'](g['LH_N'], g['LA_N'])
pickle.dump(dict(LH=np.asarray(g['LH_N']), LA=np.asarray(g['LA_N']), GH=np.asarray(g['GH']), GA=np.asarray(g['GA']), GD=np.asarray(g['GD']),
                 SEA=np.asarray(g['SEA']), COMP=np.asarray(g['COMP']), MIDS=list(g['MIDS']), FM=np.asarray(g['FM']), P0=P0),
            open(f'euro_blend_dump_{tag}.pkl', 'wb'))
print('OK', tag, len(P0))
