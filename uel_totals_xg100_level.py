"""uel_totals_xg100_level.py — 15/10/2026: το xG 100% κατεβαζει το μεσο συνολο του μοντελου (2.93→2.78) → μηπως το under κερδιζει απλως επειδη
βγαζει περισσοτερα under; ΕΛΕΓΧΟΣ: xG 100% με το ΙΔΙΟ μεσο συνολο με το σημερινο (ολα τα λ ×c, c ωστε μεσος ορος ιδιος) → μενει μονο η
διαφορετικη ΚΑΤΑΤΑΞΗ ματς. Over ≤12ω/≤72ω ≥8% και under ≤72ω/≤12ω ≥10%."""
import sys
_s = open('uel_totals_under_check.py', encoding='utf-8').read(); exec(_s[:_s.index("print('UNDER")])
X1 = rp(P('bl1.0'), P('bl0.6'))
c = (OH0 + OA0).mean() / (X1[0] + X1[1]).mean()
XL = (X1[0] * c, X1[1] * c)
print(f'μεσο συνολο: σημερινο {(OH0 + OA0).mean():.2f} · xG100 {(X1[0] + X1[1]).mean():.2f} · xG100 ιδιο επιπεδο (×{c:.3f}) {(XL[0] + XL[1]).mean():.2f}')
def bb(Pk): return ' · '.join(f'{b[0]} {100 * Pk[Pk.bk == b].pnl.mean():+.0f}%' for b in ('Crown', 'SBOBET')) if len(Pk) else ''
for nm, side, th, win in (('OVER ≥8% ≤12ω', 'over', .08, 12), ('OVER ≥8% ≤72ω', 'over', .08, 72), ('UNDER ≥10% ≤72ω', 'under', .10, 72), ('UNDER ≥10% ≤12ω', 'under', .10, 12)):
    print(f'{NL}{nm}  — picks/βιβλιο · ROI · μοναδες │ ανα σεζον 22/23/24/25 │ ανα βιβλιο')
    for lab, (oh, oa) in (('σημερινο 60%', (OH0, OA0)), ('xG 100%', X1), ('xG 100% ιδιο επιπεδο', XL)):
        Pk = picks_th(oh, oa, .85, side, th, win); print(f'   {lab:22s} {cell(Pk)} │ {bb(Pk)}')
