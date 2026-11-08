"""euro_m8_fit.py — 9/10/2026: συντελεστες Μ8 («τι xG να περιμενω») για το LIVE ευρωπαικο rating, απο ΟΛΕΣ τις 4 σεζον (2223-2526).
Ιδιο μοντελο με το euro_adj_methods (Poisson): log E[xG_blend] = a + b1·log λ_ομαδας + b2·log λ_αντιπαλου + b3·χασμα λιγκας + b4·εδρα
(λ = καθαρη V4 προβλεψη με εδρα, χωρις γ/κ· xG_blend = 60% xG + 40% γκολ). Επιθεση & αμυνα στοιβαγμενες (συμμετρικο).
Εξοδος: euro_m8_coef.json (το διαβαζει το euro_live_projections)."""
import sys, os, io, json, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
# 9/10/2026: python euro_m8_fit.py 0.8 → συντελεστες για τη μηχανη 80% (κανονας UEL φαβ εντος)· αποθηκευονται στο coef_by_blend
BL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
import picks
picks.BLEND = BL; picks._BLEND_D = (picks.BLEND_EARLY - BL) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
src = open('euro_adj_methods.py', encoding='utf-8').read().split('# ---------------- LOSO συντελεστες')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'mf'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
F, pois = g['F'], g['pois']
Xa = np.c_[np.ones(len(F)), np.log(F.l0F), np.log(F.l0A), F.Dt, F.home]
Xd = np.c_[np.ones(len(F)), np.log(F.l0A), np.log(F.l0F), -F.Dt, -F.home]
b = pois(np.r_[Xa, Xd], np.r_[F.ya.values, F.yd.values])
per = {}
for fold in sorted(F.fold.unique()):
    tr = F[F.fold != fold]
    Xa_ = np.c_[np.ones(len(tr)), np.log(tr.l0F), np.log(tr.l0A), tr.Dt, tr.home]; Xd_ = np.c_[np.ones(len(tr)), np.log(tr.l0A), np.log(tr.l0F), -tr.Dt, -tr.home]
    per[fold] = [round(float(x), 4) for x in pois(np.r_[Xa_, Xd_], np.r_[tr.ya.values, tr.yd.values])]
out = dict(fitted='2026-10-09', seasons=sorted(F.fold.unique().tolist()), n_obs=int(len(F)), blend_xg=float(g['b_bl']),
           names=['a', 'log_lam_team', 'log_lam_opp', 'league_gap', 'home'], coef=[round(float(x), 5) for x in b],
           loso=per, w_in=0.5, note='Μ8 · euro_adj_methods 9/10/2026 · βαρος 0.5 · απο το 1ο ευρωπαικο')
prev = json.load(open('euro_m8_coef.json', encoding='utf-8')) if os.path.exists('euro_m8_coef.json') else {}
cbb = prev.get('coef_by_blend', {}); cbb[f'{BL:.1f}'] = out['coef']
if abs(BL - 0.6) > 1e-9 and prev.get('coef'):
    out = {**prev}                               # η κυρια εγγραφη (60%) μενει ιδια
out['coef_by_blend'] = cbb
json.dump(out, open('euro_m8_coef.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
