# -*- coding: utf-8 -*-
"""el_ht_pin_slots.py — τα ΦΕΤΙΝΑ (E2026) bets ημιχρονου ≥8% του el_live_pace_test → χρονικα παραθυρα ημιχρονου (για Pinnacle μεσω TOA historical).
Παραθυρο = απο την ΠΡΩΤΗ ως την ΤΕΛΕΥΤΑΙΑ in-play γραμμη Crown με σκορ = ακριβως το σκορ ημιχρονου (UTC, +8 διορθωση Nowgoal).
Εξοδος: el_ht_pin_slots.json (29/10/2026)"""
import sys, io, json, runpy, contextlib
class _B(io.StringIO):
    def reconfigure(self, **k): pass
sys.argv = ['el_live_pace_test.py', 'E2026']
with contextlib.redirect_stdout(_B()): NS = runpy.run_path('el_live_pace_test.py')
sys.stdout.reconfigure(encoding='utf-8')
ROWS, SHIFT = NS['NS']['ROWS'], NS['NS']['SHIFT']
out = []
for z in NS['L8']:
    g = z['g']; hs, as_ = g['sc2']
    ts = [x[0] + SHIFT for x in ROWS.get((g['ng'], 23), []) if len(x) >= 7 and x[4] == 3 and x[5] is not None and x[6] is not None
          and (int(x[5]), int(x[6])) in ((hs, as_), (as_, hs))]
    out.append(dict(ng=g['ng'], home=g['teams'][0], away=g['teams'][1], tip=g['tip'], close=g['L'], ht=[hs, as_], ht_pts=z['r']['pts'],
                    t_a=min(ts), t_b=max(ts), crown=dict(line=z['lv'][0], oo=z['lv'][1], ou=z['lv'][2]), ours=round(z['F'], 2), side=z['side'],
                    final=g['tot'], u_crown=z['u']))
json.dump(out, open('el_ht_pin_slots.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'bets · παραθυρο ημιχρονου (λεπτα): ' + ', '.join(f'{(o["t_b"] - o["t_a"]) / 60:.0f}' for o in out))
