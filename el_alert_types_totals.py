# -*- coding: utf-8 -*-
"""el_alert_types_totals.py — ΣΥΝΟΛΑ: βαθυτερα οι τυποι alerts (1/10/2026, Στελιος «παμε στα συνολα»).
Ιδια προσομοιωση με el_alert_types.py (Crown, καθε αλλαγη τιμης, alert = πρωτη τιμη με edge ≥8%, live & παλιο μοντελο).
1. Πως γεννηθηκαν τα picks μετα το ανοιγμα: μονο αποδοση / γραμμη +0.5 / +1 / +1.5 / ≥2 (κοντρα σε εμας).
2. Κινηση αγορας ανοιγμα→alert σε λεπτα διαστηματα (αναμενομενο συνολο, με τις αποδοσεις) + ανα σεζον.
3. Ωρα × κινηση · ξαφνικη/σταδιακη · over/under.
4. Κανονας «οχι picks με κοντρα ≥Χ π.» (Χ = 1, 1.5, 2): ROI ολων πριν/μετα, ανα σεζον, αγων 1-10 / 11+.
Εξοδος: el_alert_types_totals_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, pick, settle, at, D, SE5 = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'at', 'D', 'SE5'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
def sim(which):
    rows = []
    for p, r in REC[23].items():
        m = PR.get(key(p), {}).get('t_' + which)
        if m is None or not np.isfinite(m): continue
        ser, tip = r['ser'], r['tip']; o = ser[0]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(23, m, row)
            if e < 0.08: continue
            prev1 = at(ser, row[0] - 3600) or o
            od_o = o[3] if side == 1 else o[4]
            c = ser[-1]; oc = c[3] if side == 1 else c[4]
            rows.append(dict(sea=D.season.values[p], hrs=(tip - row[0]) / 3600, at_open=(k_ == 0), side='over' if side == 1 else 'under',
                             mv=-(row[1] - o[1]) * side, mv1=-(row[1] - prev1[1]) * side, dline=-(row[2] - o[2]) * side, dodds=od - od_o,
                             e_open=pick(23, m, o)[1] * (1 if pick(23, m, o)[0] == side else -1), e=e,
                             pnl=settle(23, p, side, row, od), pnl_c=settle(23, p, side, c, oc),
                             gn=PR[key(p)].get('gn', PR[key(p)].get('rnd', 99))))
            break
    return pd.DataFrame(rows)
def L(lab, z, w=36):
    if len(z) == 0: P(f'    {lab:{w}s} —'); return
    pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0)
    per = ' '.join(f'{s[-2:]}:{z[z.sea == s].pnl.mean()*100:+.0f}' if (z.sea == s).any() else f'{s[-2:]}:—' for s in SE5)
    P(f'    {lab:{w}s} n {len(z):4d} · ROI {z.pnl.mean()*100:+6.1f}% ({pos}/5) · στο κλεισιμο {z.pnl_c.mean()*100:+6.1f}% · [{per}]')
for which in ('new', 'old'):
    Z = sim(which); nz = Z[~Z.at_open]
    P(''); P(f'======== ΣΥΝΟΛΑ — μοντελο {which.upper()} · {len(Z)} alerts ({len(nz)} μετα το ανοιγμα) ========')
    P('  1. ΠΩΣ γεννηθηκαν (μετα το ανοιγμα): αλλαγη ΓΡΑΜΜΗΣ κοντρα σε εμας')
    P(f'    edge στο ανοιγμα (ιδια πλευρα): διαμεσος {nz.e_open.median()*100:.1f}%')
    for lo, hi, lab in ((-0.01, 0.01, 'μονο αποδοση (ιδια γραμμη)'), (0.49, 0.51, 'γραμμη +0.5'), (0.99, 1.01, 'γραμμη +1'), (1.49, 1.51, 'γραμμη +1.5'), (1.99, 99, 'γραμμη ≥+2')):
        z = nz[(nz.dline > lo) & (nz.dline < hi)]
        if len(z): P(f'    {lab:26s} {len(z)/len(nz):4.0%} · αλλαγη αποδοσης {z.dodds.mean():+.3f} · edge ανοιγμα {z.e_open.median()*100:+.1f}%'); L('', z, 2)
    z = nz[nz.dline < -0.01]
    if len(z): P(f'    γραμμη ΠΡΟΣ εμας (αποδοση κοντρα) {len(z)/len(nz):.0%}'); L('', z, 2)
    P('  2. ΚΙΝΗΣΗ αγορας ανοιγμα→alert (αναμενομενο συνολο, + = κοντρα):')
    L('στο ΑΝΟΙΓΜΑ', Z[Z.at_open])
    for lo, hi in ((-9, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 99)):
        L(f'{lo:+.1f} … {hi:+.1f} π.' if hi < 99 else f'≥{lo:.1f} π.', nz[(nz.mv >= lo) & (nz.mv < hi)])
    P('  3. ΩΡΑ × κινηση · ξαφνικη/σταδιακη · over/under:')
    for lo, hi, lab in ((12, 99, '≥12ω'), (6, 12, '6-12ω'), (2, 6, '2-6ω'), (0, 2, '<2ω')):
        z = nz[(nz.hrs >= lo) & (nz.hrs < hi)]
        L(f'{lab} · κοντρα <1.5π', z[z.mv < 1.5]); L(f'{lab} · κοντρα ≥1.5π', z[z.mv >= 1.5])
    big = nz[nz.mv >= 1.5]
    L('κοντρα ≥1.5 · ΞΑΦΝΙΚΗ (≥1π στην 1ω)', big[big.mv1 >= 1]); L('κοντρα ≥1.5 · ΣΤΑΔΙΑΚΗ', big[big.mv1 < 1])
    L('κοντρα ≥1.5 · OVER', big[big.side == 'over']); L('κοντρα ≥1.5 · UNDER', big[big.side == 'under'])
    sm_ = nz[nz.mv < 1.5]
    L('κοντρα <1.5 · OVER', sm_[sm_.side == 'over']); L('κοντρα <1.5 · UNDER', sm_[sm_.side == 'under'])
    P('  4. ΚΑΝΟΝΑΣ «οχι picks με κοντρα ≥Χ π. απο το ανοιγμα»:')
    L('ΟΛΑ τα alerts (σημερα)', Z)
    for X in (1.0, 1.5, 2.0):
        keep = Z[Z.at_open | (Z.mv < X)]
        L(f'χωρις κοντρα ≥{X:g} π. (κοβει {len(Z) - len(keep)})', keep)
    keep = Z[Z.at_open | (Z.mv < 1.5)]
    L('  ↳ αγων 1-10', keep[keep.gn <= 10]); L('  ↳ αγων 11+', keep[keep.gn > 10])
    L('  (ολα αγων 1-10)', Z[Z.gn <= 10]); L('  (ολα αγων 11+)', Z[Z.gn > 10])
open('el_alert_types_totals_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
