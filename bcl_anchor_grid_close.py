# -*- coding: utf-8 -*-
"""bcl_anchor_grid_close.py — ιδιο πλεγμα με bcl_anchor_grid αλλα στο ΚΛΕΙΣΙΜΟ: αγκυρα = δικαιο κλεισιματος, picks στις τιμες κλεισιματος (21/10/2026)."""
src = open('bcl_anchor_test.py', encoding='utf-8').read().split("# ---------- μηχανες ----------")[0].replace("open('bcl_anchor_test_out.txt'", "open('NUL'")
exec(src)
FC = np.array([r['fc'] for r in rows])
P('  RMSE κλεισιμο: ' + ' · '.join(f'{s}: {rm(FC, Y == s):.2f}' for s in SE))
WS = (.1, .2, .3, .4, .5, .7, 1.0); THR = (.04, .08, .12)
P('  w \ κατωφλι | ' + ' | '.join(f'{int(t * 100)}%'.center(30) for t in THR))
best = None
for w in WS:
    pr = FC + w * (FIN - FC); sg = float(np.std(ACT - pr)); cs = []
    for th in THR:
        R = evaluate(pr, sg, th, when='c'); a = np.array([x[1] for x in R]) if R else np.array([0.0])
        ps = units_by(R); cs.append(f'{100 * a.mean():+5.1f}% ({len(R):4d}, {a.sum():+6.1f}μ, {sum(1 for v in ps.values() if v > 0)}/6)')
    P(f'  w {w:<4} | ' + ' | '.join(c.center(30) for c in cs))
P(f'  LIVE στο κλεισιμο (σ 12, ≥8%): {cell(evaluate(FIN, 12.0, .08, when="c"))}')
