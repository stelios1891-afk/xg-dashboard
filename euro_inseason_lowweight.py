"""euro_inseason_lowweight.py — 9/10/2026 (Στελιος: «αν τα φετινα ευρωπαικα μετρουσαν λιγοτερο;»).
Σταθερα βαρη w_in ∈ {0.1, 0.25, 0.5, 1} (καθε φετινο ευρωπαικο = w εγχωρια ματς), διορθωση V0 (26/9) και B1. Περιγραφικο.
RPS επηρεαζομενων vs ΧΩΡΙΣ φετινα (×10⁻³) ανα σεζον/φαση + ROI σημερινη τιμολογηση (μεσος Crown/Pinnacle)."""
import sys, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'lw'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
run, rps_arr, dse, AFF, SEA, PH, SEAS, R_BASE, gen, roi, FLT, CROWN, PIN, BASE = (g[k] for k in (
    'run', 'rps_arr', 'dse', 'AFF', 'SEA', 'PH', 'SEAS', 'R_BASE', 'gen', 'roi', 'FLT', 'CROWN', 'PIN', 'BASE'))
def roi_line(L):
    G = [gen(L, OD) for OD in (CROWN, PIN)]; out = []
    for lab, flt in FLT:
        v = [roi([r for r in GG.values() if flt(r)]) for GG in G]
        out.append(f'{lab} {(v[0][0] + v[1][0]) / 2:.0f} {100 * np.nanmean([v[0][1], v[1][1]]):+.1f}%')
    return ' · '.join(out)
print('ΧΩΡΙΣ φετινα: ' + roi_line(BASE))
for fam, eq in (('V0', g['EQ0']), ('B1', g['eq_B1'])):
    for w in (0.1, 0.25, 0.5, 1.0):
        L, _ = run(eq, w); R = rps_arr(*L)
        cs = [dse(R[AFF & (SEA == s)] - R_BASE[AFF & (SEA == s)])[0] for s in SEAS]
        a, sa = dse(R[AFF] - R_BASE[AFF])
        ph = ' '.join(f'{p}: {1000 * dse(R[AFF & (PH == p)] - R_BASE[AFF & (PH == p)])[0]:+.2f}' for p in ('LP md1-2', 'LP md3-8', 'KO'))
        print(f'\n{fam} w={w}: RPS ΟΛΑ {1000 * a:+.2f}±{1000 * sa:.2f} · σεζον ' + ' '.join(f'{s}:{1000 * c:+.2f}' for s, c in zip(SEAS, cs))
              + f' ({sum(c < 0 for c in cs)}/4 καλυτερα) · {ph}')
        print('   ROI ' + roi_line(L))
