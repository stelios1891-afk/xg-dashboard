"""euro_variant_build.py — 15/10/2026 (Στελιος: «παρε ολους τους μηχανισμους και τεσταρε — ποσο μετραει η περσινη σεζον, η φετινη, τα περσινα
ευρωπαικα, τα φετινα, αξια, αγκυρα, τα παντα»).
Ξαναχτιζει τα ευρωπαικα λ (euro_v6w2_test — ιδια αλυσιδα με το live, κοκκινες emps) με ΑΛΛΗ ρυθμιση ΕΝΟΣ μηχανισμου, και μετα τρεχει τη σημερινη
ευρωπαικη αλυσιδα (uel_battery harness: γ, κ UCL, ισοπαλιες) → euro_blend_dump_<tag>.pkl (ιδια μορφη με τα dumps του τεστ μιξης xG).
Χρηση: python euro_variant_build.py <tag> [K=8] [W=2.0] [BLEND=0.6]
   K     = βαρος της περσινης σεζον στη μιξη με τη φετινη (n/(n+K)· μεγαλο K = μετραει περισσοτερο το περσινο)
   W     = βαρος των ΠΕΡΣΙΝΩΝ ευρωπαικων ματς στη «βαση» καθε ομαδας (0 = καθολου)
   BLEND = μεριδιο xG στη δυναμη ομαδας
"""
import sys, os, io, pickle, contextlib, runpy
tag = sys.argv[1]
kv = dict(a.split('=') for a in sys.argv[2:])
K = int(kv.get('K', 8)); W = float(kv.get('W', 2.0)); B = float(kv.get('BLEND', 0.6))
import picks
picks.BLEND = B; picks._BLEND_D = (picks.BLEND_EARLY - B) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
src = open('euro_v6w2_test.py', encoding='utf-8').read()
src = src.replace('K = 8\n', f'K = {K}\n', 1).replace('W_GRID = [2.0]', f'W_GRID = [{W}]', 1).replace('LH2, LA2 = PRED[2.0]', f'LH2, LA2 = PRED[{W}]', 1)
out_pkl = f'euro_v6w2_preds_{tag}.pkl'
os.environ['RED_MODE'] = 'emps'; os.environ['NO_SANITY'] = '1'; os.environ['W2_OUT'] = out_pkl
g = {'__name__': '__main__'}
try:
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, 'euro_v6w2_test.py', 'exec'), g)
except SystemExit as e:   # το euro_v6w2_test τελειωνει με sys.exit(0)
    if e.code: raise
# αλυσιδα live (γ, κ, ισοπαλιες) πανω στα νεα λ
os.environ['W2_IN'] = out_pkl
src2 = open('uel_battery.py', encoding='utf-8').read(); src2 = src2[:src2.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g2 = {'__name__': 'bd'}
with contextlib.redirect_stdout(io.StringIO()): exec(src2, g2)
import numpy as np
pickle.dump(dict(LH=np.asarray(g2['LH_N']), LA=np.asarray(g2['LA_N']), GH=np.asarray(g2['GH']), GA=np.asarray(g2['GA']), GD=np.asarray(g2['GD']),
                 SEA=np.asarray(g2['SEA']), COMP=np.asarray(g2['COMP']), MIDS=list(g2['MIDS']), FM=np.asarray(g2['FM'])),
            open(f'euro_blend_dump_{tag}.pkl', 'wb'))
print('OK', tag, f'K={K} W={W} BLEND={B}')
