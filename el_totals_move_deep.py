# -*- coding: utf-8 -*-
"""el_totals_move_deep.py — ΣΥΝΟΛΑ Ευρωλιγκας: picks που γεννιουνται ΜΕΤΑ απο κοντρα κινηση ≥1.5 π. — ΒΑΘΥΤΕΡΑ (7/10/2026, Στελιος
«το Paris–ASVEL εφαγε μικρη κοντρα πολυ νωρις, με μικρα ορια — ενα μικρο μπετ στο under μπορει να το κουνησε· αξιζει να το ψαξουμε»).
Ιδια προσομοιωση με el_alert_types_totals (Crown καθε αλλαγη τιμης, live μοντελο, alert = πρωτη τιμη με edge ≥8%), E2021-25.
Ομαδα «κοντρα»: alerts ΟΧΙ στο ανοιγμα με κινηση αγορας ανοιγμα→alert ≥1.5 π. κοντρα (= σημερινος κανονας «move15» → καταγραφη).
ΕΡΩΤΗΣΕΙΣ (ολα γνωστα ΤΗ ΣΤΙΓΜΗ του alert, εκτος του Δ):
  Α. ΠΟΤΕ εγινε η κοντρα κινηση (ωρες πριν το τζαμπολ οταν ξεπερασε το 1.5): ≥24ω · 12-24ω · 6-12ω · <6ω (νωρις = μικρα ορια)
  Β. ΤΟ ΑΛΛΟ ΒΙΒΛΙΟ (Bet365): κινηθηκε κι αυτο κοντρα ≥1 π. απο το δικο του ανοιγμα ως το alert; (ναι = πληροφορια σε ολη την αγορα · οχι = ισως «μικρο μπετ»)
  Γ. ΜΕΓΕΘΟΣ: 1.5-2 / 2-3 / ≥3 π. · ΜΙΑ απότομη αλλαγη ≥1.5 vs σταδιακα · edge στο ανοιγμα (ηταν σχεδον pick;) ≥4% / <4%
  Δ. ΜΕΤΑ (μονο περιγραφη): συνεχισε κοντρα ≥0.5 ως το κλεισιμο / γυρισε προς εμας ≥0.5 / εμεινε
  Ε. OVER / UNDER σε καθε ομαδα
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): μια υποομαδα που ΦΑΙΝΕΤΑΙ τη στιγμη του alert (Α, Β, Γ) «ξαναμπαινει στο παιχνιδι» μονο αν ROI > 0 σε ≥4/5 σεζον,
  n ≥ 30, και το υπολοιπο της ομαδας «κοντρα» μενει αρνητικο.
Εξοδος: el_totals_move_deep_out.txt"""
import sys, json, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, pick, settle, at, D, SE5, LT = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'at', 'D', 'SE5', 'LT'))
ST, SHIFT, N = LT['ST'], LT['SHIFT'], NormalDist()
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
# ---- Bet365 (cid 8) σειρες συνολου, ιδια αντιστοιχιση ----
B8 = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r.get('ot') == 6 and r.get('cid') == 8 and r.get('t') == 23: B8[r['ngid']] = r['rows']
pos2ng = {D.index.get_loc(i): ng for ng, (i, sw) in LT['mapping'].items()}
def b365(pos, tip):
    rows = sorted([x for x in B8.get(pos2ng.get(pos), []) if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    s = []
    for x in rows:
        ut = x[0] + SHIFT
        if ut > tip + 600: break
        o1, o2 = 1 + x[2], 1 + x[3]; ph = (1 / o1) / (1 / o1 + 1 / o2)
        s.append((ut, x[1] + ST * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))))
    return s
rows = []
for p, r in REC[23].items():
    m = PR.get(key(p), {}).get('t_new')
    if m is None or not np.isfinite(m): continue
    ser, tip = r['ser'], r['tip']; o = ser[0]
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(23, m, row)
        if e < 0.08: continue
        mv = -(row[1] - o[1]) * side
        # ποτε ξεπερασε τα 1.5 κοντρα
        t15 = next((x[0] for x in ser[:k_ + 1] if -(x[1] - o[1]) * side >= 1.5), None)
        jumps = [-(ser[j][1] - ser[j - 1][1]) * side for j in range(1, k_ + 1)]
        bs = b365(p, tip); b_at = [x for x in bs if x[0] <= row[0]]
        b_mv = (-(b_at[-1][1] - bs[0][1]) * side) if (bs and b_at) else None
        c = ser[-1]; oc = c[3] if side == 1 else c[4]
        e_open = pick(23, m, o); e_open = e_open[1] if e_open[0] == side else -e_open[1]
        rows.append(dict(sea=D.season.values[p], at_open=(k_ == 0), side='over' if side == 1 else 'under', mv=mv,
                         h15=(tip - t15) / 3600 if t15 else None, hrs=(tip - row[0]) / 3600, bmv=b_mv, maxjump=max(jumps) if jumps else 0.0,
                         e_open=e_open, after=-(c[1] - row[1]) * side, pnl=settle(23, p, side, row, od), pnl_c=settle(23, p, side, c, oc)))
        break
Z = pd.DataFrame(rows)
def L(lab, z, w=44):
    if len(z) == 0: P(f'    {lab:{w}s} —'); return None
    pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0); ny = sum(1 for s in SE5 if (z.sea == s).any())
    per = ' '.join(f'{s[-2:]}:{z[z.sea == s].pnl.mean()*100:+.0f}' if (z.sea == s).any() else f'{s[-2:]}:—' for s in SE5)
    P(f'    {lab:{w}s} n {len(z):4d} · ROI {z.pnl.mean()*100:+6.1f}% ({pos}/{ny}) · {z.pnl.sum():+5.1f}u · στο κλεισιμο {z.pnl_c.mean()*100:+6.1f}% · [{per}]')
    return pos
K = Z[(~Z.at_open) & (Z.mv >= 1.5)]
P(f'ΣΥΝΟΛΑ Ευρωλιγκας E2021-25 · alerts {len(Z)} · στο ανοιγμα {Z.at_open.sum()} · «κοντρα ≥1.5» {len(K)} · με Bet365 σειρα {K.bmv.notna().sum()}')
L('αναφορα: στο ΑΝΟΙΓΜΑ', Z[Z.at_open]); L('αναφορα: μετα το ανοιγμα, κοντρα <1.5', Z[(~Z.at_open) & (Z.mv < 1.5)]); L('ΟΜΑΔΑ «κοντρα ≥1.5» (σημερα καταγραφη)', K)
cands = []
P(''); P('  Α. ΠΟΤΕ ξεπερασε τα 1.5 π. κοντρα (ωρες πριν το τζαμπολ):')
for lo, hi, lab in ((24, 999, '≥24ω (πολυ νωρις, μικρα ορια)'), (12, 24, '12-24ω'), (6, 12, '6-12ω'), (0, 6, '<6ω')):
    z = K[(K.h15 >= lo) & (K.h15 < hi)]; ps = L(lab, z); cands.append(('Α ' + lab, z, ps))
P(''); P('  Β. Bet365 (το αλλο βιβλιο) απο το δικο του ανοιγμα ως το alert:')
for lab, f in (('Bet365 κινηθηκε κι αυτο κοντρα ≥1 π.', K.bmv >= 1), ('Bet365 0.5-1 κοντρα', (K.bmv >= .5) & (K.bmv < 1)), ('Bet365 ΔΕΝ κινηθηκε (<0.5) ή αντιθετα', K.bmv < .5)):
    z = K[f]; ps = L(lab, z); cands.append(('Β ' + lab, z, ps))
P(''); P('  Γ. ΜΕΓΕΘΟΣ / ΤΡΟΠΟΣ / ποσο κοντα ηταν στο pick στο ανοιγμα:')
for lab, f in (('κοντρα 1.5-2', K.mv < 2), ('κοντρα 2-3', (K.mv >= 2) & (K.mv < 3)), ('κοντρα ≥3', K.mv >= 3),
               ('μια απότομη αλλαγη ≥1.5', K.maxjump >= 1.5), ('σταδιακα (καθε αλλαγη <1.5)', K.maxjump < 1.5),
               ('edge στο ανοιγμα ≥4% (σχεδον pick)', K.e_open >= .04), ('edge στο ανοιγμα <4%', K.e_open < .04)):
    z = K[f]; ps = L(lab, z); cands.append(('Γ ' + lab, z, ps))
P(''); P('  Δ. ΜΕΤΑ το alert ως το κλεισιμο (περιγραφη — δεν φαινεται τη στιγμη του pick):')
for lab, f in (('συνεχισε κοντρα ≥0.5', K.after <= -.5), ('εμεινε (±0.5)', K.after.abs() < .5), ('γυρισε προς εμας ≥0.5', K.after >= .5)):
    L(lab, K[f])
P(''); P('  Ε. OVER / UNDER:')
for sd in ('over', 'under'):
    L(f'{sd.upper()} — ολη η ομαδα «κοντρα»', K[K.side == sd])
    for lo, hi, lab in ((24, 999, '≥24ω'), (12, 24, '12-24ω'), (0, 12, '<12ω')):
        L(f'   {sd} · κοντρα εγινε {lab}', K[(K.side == sd) & (K.h15 >= lo) & (K.h15 < hi)])
    L(f'   {sd} · Bet365 ΔΕΝ κινηθηκε', K[(K.side == sd) & (K.bmv < .5)])
P(''); P('################ ΚΡΙΣΗ (προ-δηλωμενη): υποομαδα με ROI > 0 σε ≥4/5 σεζον, n ≥ 30, και το υπολοιπο αρνητικο ################')
any_ = False
for lab, z, ps in cands:
    if ps is None or len(z) < 30 or ps < 4 or z.pnl.mean() <= 0: continue
    rest = K.drop(z.index)
    if len(rest) and rest.pnl.mean() < 0:
        P(f'  ✓ {lab}: n {len(z)} · ROI {z.pnl.mean()*100:+.1f}% ({ps}/5) · υπολοιπο {rest.pnl.mean()*100:+.1f}% (n {len(rest)})'); any_ = True
if not any_: P('  ✗ καμια υποομαδα δεν περνα — ο κανονας «move15» μενει ως εχει')
open('el_totals_move_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
