"""uel_totals_over_xg100.py — 15/10/2026 (Στελιος: «το 112 picks +12.5% ειναι καλο, στειλε μου και το over»). OVER Europa Α: σημερινο (60% xG) vs xG 100%,
σε κατωφλια 0-10%, παραθυρα ≤12ω (προταση σκιας) και ≤72ω · ανα βιβλιο, ανα σεζον, κοινα / μονο-xG100 / μονο-σημερινο."""
import sys
_s = open('uel_totals_under_check.py', encoding='utf-8').read(); exec(_s[:_s.index("print('UNDER")])
X1 = rp(P('bl1.0'), P('bl0.6'))
def bb(Pk): return ' · '.join(f'{b[0]} {100 * Pk[Pk.bk == b].pnl.mean():+.0f}%' for b in ('Crown', 'SBOBET')) if len(Pk) else ''
for win in (12, 72):
    print(f'{NL}OVER ≤{win}ω — picks/βιβλιο · ROI · μοναδες │ ανα σεζον 22/23/24/25 │ ανα βιβλιο')
    for th in (.10, .08, .06, .04, .02, 0.0):
        a = picks_th(OH0, OA0, .85, 'over', th, win); b = picks_th(*X1, .85, 'over', th, win)
        print(f'   ≥{int(th * 100):2d}%  σημερινο {cell(a)} │ {bb(a)}')
        print(f'        xG 100% {cell(b)} │ {bb(b)}')
    a = picks_th(OH0, OA0, .85, 'over', .08, win); b = picks_th(*X1, .85, 'over', .08, win)
    ka = set(zip(a.k, a.bk)); kb = set(zip(b.k, b.bk))
    print(f'   στο ≥8%: κοινα {cell(a[[t in kb for t in zip(a.k, a.bk)]])}')
    print(f'            μονο σημερινο (κοβει το xG100) {cell(a[[t not in kb for t in zip(a.k, a.bk)]])}')
    print(f'            μονο xG100 (προσθετει) {cell(b[[t not in ka for t in zip(b.k, b.bk)]])}')
