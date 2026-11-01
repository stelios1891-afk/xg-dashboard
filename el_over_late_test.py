# -*- coding: utf-8 -*-
"""el_over_late_test.py — ΕΥΡΩΛΙΓΚΑ: OVER ΠΟΥ ΠΡΩΤΟΒΓΑΙΝΟΥΝ ΑΡΓΑ = ΚΑΤΑΓΡΑΦΗ; (12/10/2026, Στελιος «κανε το τεστ στα over»).
Ευρημα (el_over_under_timing, ΔΙΕΡΕΥΝΗΤΙΚΟ): over στο alert ανα ωρα πρωτης εμφανισης 12-24ω +10.3% · 6-12ω +5.2% · 2-6ω −1.8% · <2ω −5.3%·
το ιδιο over στο κλεισιμο χανει −3.1 μ. (η αξια των over ειναι νωρις).
ΠΡΟΣΟΜΟΙΩΣΗ LIVE (Crown, καθε αλλαγη τιμης, live μηχανη t_new, κανονικη περιοδος E2021-25): πρωτη τιμη με edge ≥8% = alert·
  ΥΠΑΡΧΩΝ live κανονας συνολων (move15): αν η αγορα κινηθηκε ≥1.5 π. ΚΟΝΤΡΑ απο την πρωτη τιμη ΚΑΙ η κινηση ξεπερασε το 1.5 ≥6ω πριν
  → καταγραφη (οχι παιχνιδι)· <6ω → κανονικο. Ο νεος κανονας μετραει ΠΑΝΩ στα κανονικα picks που μενουν.
ΝΕΟΣ ΚΑΝΟΝΑΣ (ΠΡΟ-ΔΗΛΩΜΕΝΟΣ, ΠΡΙΝ την εκτελεση): OVER που πρωτοεμφανιζεται < Χ ωρες πριν το τζαμπολ (οχι στο ανοιγμα) = ΚΑΤΑΓΡΑΦΗ.
  ΚΥΡΙΟ Χ = 6. ΠΕΡΝΑ αν ΟΛΑ:
  (1) τα κομμενα over: ROI < 0 ΚΑΙ χειροτερα απο οσα μενουν, στην τιμη του alert ΚΑΙ στην τιμη κλεισιματος,
  (2) χειροτερα απο οσα μενουν σε ≥3/5 σεζον (σεζον με ≥3 κομμενα),
  (3) ιδια φορα με Χ = 4 και Χ = 8 (σταθεροτητα οριου),
  (4) οι μοναδες των over με τον κανονα ≥ χωρις.
  Under: καμια αλλαγη (αναφορα μονο). Εξοδος: el_over_late_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
sys.stdout.reconfigure(encoding='utf-8')
REC, PR, key, pick, settle, D = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'D'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows = []
for p, r in REC[23].items():
    q = PR.get(key(p), {}); m = q.get('t_new')
    if m is None or not np.isfinite(m): continue
    ser, tip = r['ser'], r['tip']; c = ser[-1]; o = ser[0]
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(23, m, row)
        if e < .08: continue
        d_open = (row[1] - o[1]) * side                                     # + = η αγορα ηρθε προς εμας απο την πρωτη τιμη
        move15 = False
        if d_open <= -1.5:
            hx = next(((tip - x[0]) / 3600 for x in ser[:k_ + 1] if (x[1] - o[1]) * side <= -1.5), None)
            move15 = hx is None or hx >= 6
        oc = c[3] if side == 1 else c[4]
        rows.append(dict(sea=D.season.values[p], side='OVER' if side == 1 else 'UNDER', hrs=(tip - row[0]) / 3600, at_open=(k_ == 0),
                         move15=move15, pa=settle(23, p, side, row, od), pc=settle(23, p, side, c, oc)))
        break
X = pd.DataFrame(rows)
SE = sorted(X.sea.unique())
def cell(d, col='pa'):
    if not len(d): return '—'
    ps = d.groupby('sea')[col].mean()
    return f'{100*d[col].mean():+6.1f}% ({len(d)}, {d[col].sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
live = X[~X.move15]
P(f'συνολα (πρωτο alert ≥8%): {len(X)} · με τον live κανονα move15 → καταγραφη {int(X.move15.sum())} · κανονικα {len(live)} '
  f'(over {int((live.side == "OVER").sum())} / under {int((live.side == "UNDER").sum())})')
P(f'  κανονικα σημερα: OVER alert {cell(live[live.side == "OVER"])} · κλεισιμο {cell(live[live.side == "OVER"], "pc")}')
P(f'                   UNDER alert {cell(live[live.side == "UNDER"])} · κλεισιμο {cell(live[live.side == "UNDER"], "pc")}')
ov = live[live.side == 'OVER']
P(''); P('=== OVER (κανονικα) ανα ωρα πρωτης εμφανισης — alert | κλεισιμο ===')
for lo, hi in ((12, 99), (8, 12), (6, 8), (4, 6), (2, 4), (0, 2)):
    d = ov[(ov.hrs >= lo) & (ov.hrs < hi)]
    P(f'  {lo:2d}-{hi if hi < 99 else "+"}ω: {cell(d)} | {cell(d, "pc")}' + (f' · στο ανοιγμα {int(d.at_open.sum())}' if len(d) else ''))
res = {}
P(''); P('=== ΚΑΝΟΝΑΣ: over με πρωτη εμφανιση < Χ ωρες (οχι στο ανοιγμα) → καταγραφη ===')
for Xh in (4, 6, 8):
    cut = ov[(ov.hrs < Xh) & ~ov.at_open]; keep = ov.drop(cut.index)
    ys = [s for s in SE if (cut.sea == s).sum() >= 3]
    worse = sum(1 for s in ys if cut[cut.sea == s].pa.mean() < keep[keep.sea == s].pa.mean())
    res[Xh] = dict(cut_a=cut.pa.mean(), cut_c=cut.pc.mean(), keep_a=keep.pa.mean(), keep_c=keep.pc.mean(), worse=worse, ny=len(ys),
                   u0=ov.pa.sum(), u1=keep.pa.sum())
    P(f'  Χ={Xh}: κοβει alert {cell(cut)} · κλεισ. {cell(cut, "pc")} | μενουν alert {cell(keep)} · κλεισ. {cell(keep, "pc")} | '
      f'κομμενα χειροτερα σε {worse}/{len(ys)} σεζον · μοναδες over {ov.pa.sum():+.1f} → {keep.pa.sum():+.1f}')
r6 = res[6]
c1 = r6['cut_a'] < 0 and r6['cut_c'] < 0 and r6['cut_a'] < r6['keep_a'] and r6['cut_c'] < r6['keep_c']
c2 = r6['worse'] >= 3
c3 = all(res[x]['cut_a'] < res[x]['keep_a'] for x in (4, 8))
c4 = r6['u1'] >= r6['u0']
P(''); P(f'ΚΡΙΣΗ (Χ=6): (1) κομμενα <0 & χειροτερα σε alert ΚΑΙ κλεισιμο {"✓" if c1 else "✗"} · (2) χειροτερα σε {r6["worse"]}/{r6["ny"]} σεζον {"✓" if c2 else "✗"} · '
  f'(3) ιδια φορα Χ=4 & 8 {"✓" if c3 else "✗"} · (4) μοναδες ≥ {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if c1 and c2 and c3 and c4 else "ΔΕΝ ΠΕΡΝΑ"}')
P(''); P('(αναφορα) UNDER κανονικα ανα ωρα: ' + ' · '.join(f'{lo}-{hi if hi < 99 else "+"}ω {cell(live[(live.side == "UNDER") & (live.hrs >= lo) & (live.hrs < hi)])}'
                                                       for lo, hi in ((12, 99), (6, 12), (2, 6), (0, 2))))
open('el_over_late_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
