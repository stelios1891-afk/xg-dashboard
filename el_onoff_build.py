# -*- coding: utf-8 -*-
"""el_onoff_build.py — LIVE ΣΥΝΟΛΑ Ευρωλιγκας: απουσιες με ON/OFF (9/10/2026, Στελιος «ας περασουμε το αμυνα και επιθεση»).
Τεστ: el_absence_onoff_test.py, εκδοχη W4 «μονο on/off» (EL RMSE 3/5, picks συνολων +52.4 → +59.0μ· EuroCup επιβεβαιωση 4/5 & t −2.7/−2.6).
Βγαζει el_onoff_prev.json = {coef: {bO, bD}, sd: {onO, onD}, season_prev, players: [{sur, first, onO, onD}]}
  bO, bD = συντελεστες W4 σε ΟΛΑ τα δεδομενα E2021-25 · προφιλ = on/off της ΠΡΟΗΓΟΥΜΕΝΗΣ σεζον (EL + EuroCup, 3StepsBasket, μαζεμα 1500).
ΤΡΕΧΕΙ: μια φορα τη σεζον (μετα το bb3s_fetch.py της νεας χρονιας: αλλαξε SEASON_PREV). Χρονος ~5′."""
import sys, io, contextlib, json
import numpy as np
SEASON_PREV = 2025                       # 2025-26 (= competitionId euroleague-2026 / eurocup-2026) → προφιλ για τη σεζον 2026-27
class _B(io.StringIO):
    def reconfigure(self, **k): pass
G = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_onoff_test.py', encoding='utf-8').read().split("P(''); P('################ ΣΥΝΟΛΑ")[0], G)
sys.stdout.reconfigure(encoding='utf-8')
fit, PROF, SD = G['fit'], G['PROF'], G['SD']
ALL = np.ones(len(G['rows']), bool)
b = fit([2, 3], ALL)
pl = []
for (sur, first), d in PROF.items():
    v = d.get(SEASON_PREV)
    if v is None or v[2] <= 0: continue
    pl.append(dict(sur=list(sur), first=first, onO=round(float(v[0] / v[2]), 3), onD=round(float(v[1] / v[2]), 3)))
out = dict(built='2026-10-09', test='el_absence_onoff_test.py W4', coef=dict(bO=round(float(b[0]), 4), bD=round(float(b[1]), 4)),
           sd=dict(onO=round(float(SD['onO']), 4), onD=round(float(SD['onD']), 4)), season_prev=SEASON_PREV, players=pl)
json.dump(out, open('el_onoff_prev.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f"συντελεστες: δικα×onO {b[0]:+.3f} · αντιπ.×onD {b[1]:+.3f} · SD onO {SD['onO']:.3f} onD {SD['onD']:.3f} · παικτες με προφιλ {SEASON_PREV}: {len(pl)}")
