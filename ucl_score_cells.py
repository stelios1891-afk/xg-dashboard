"""ucl_score_cells.py — 10/10/2026 (Στελιος: «δες το 0-0 και για το Champions League»). Πραγματικο vs μοντελο ανα σκορ/συνολο, UCL FotMob+FotMob,
παλια (2223-24) και νεα μορφη (2425-26). Μοντελο = μηχανη συνολων (W2 + κ): σημερα ×1.13 και «ιδιο με χαντικαπ»."""
import sys, io, contextlib
import numpy as np
import euro_shadow_scan  # προφορτωση εκτος redirect
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_totals_draw_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src[:src.index("VAR = {")]
g = {'__name__': 'sc'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
OH, OA, GH, GA, FM, ucl, newf, matrix = (g[k] for k in ('OH', 'OA', 'GH', 'GA', 'FM', 'ucl', 'newf', 'matrix'))
CELLS = (('0-0', lambda h, a: h == 0 and a == 0), ('1-0/0-1', lambda h, a: h + a == 1), ('1-1', lambda h, a: h == 1 and a == 1), ('2-2', lambda h, a: h == 2 and a == 2),
         ('ισοπαλια', lambda h, a: h == a), ('συνολο 0-1', lambda h, a: h + a <= 1), ('συνολο 2', lambda h, a: h + a == 2), ('συνολο 3', lambda h, a: h + a == 3),
         ('συνολο 4+', lambda h, a: h + a >= 4))
def modp(M, f): return sum(M[i, j] for i in range(13) for j in range(13) if f(i, j))
for lab, m in (('UCL ΝΕΑ μορφη 2425-26', newf), ('UCL παλια μορφη 2223-24', ~newf)):
    ii = [i for i in range(len(OH)) if FM[i] and ucl[i] and m[i]]
    MA = [matrix(max(OH[i], .05), max(OA[i], .05), 1.13) for i in ii]; MB = [matrix(max(OH[i], .05), max(OA[i], .05), 1.13, True) for i in ii]
    print(f'\n{lab} (n{len(ii)}) — % : πραγματικο · μοντελο σημερα ×1.13 · «ιδιο με χαντικαπ»')
    for name, f in CELLS:
        act = np.mean([f(GH[i], GA[i]) for i in ii]); a = np.mean([modp(M, f) for M in MA]); bb = np.mean([modp(M, f) for M in MB])
        print(f'   {name:11s} {100 * act:5.1f} · {100 * a:5.1f} · {100 * bb:5.1f}   (πραγμ/μοντελο Β = {act / bb:.2f})')
