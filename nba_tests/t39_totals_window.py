# -*- coding: utf-8 -*-
"""t39_totals_window.py — ΣΥΝΟΛΑ NBA · Μ2δ (Μ2 + Απριλιος χωριστα): WALK-FORWARD + ΠΑΡΑΘΥΡΟ ΣΕΖΟΝ + ΣΤΙΓΜΕΣ (21/10/2026).
ΠΡΟ-ΔΗΛΩΜΕΝΑ: (Α) walk-forward Μ2δ ≥6% (2024←22-23, 2025←22-24, 2026←22-25): ΠΕΡΝΑ αν ROI>0 σε ≥2/3 & συνολο>0 & CLV>0.
 (Β) ΠΑΡΑΘΥΡΟ: picks μονο απο μηνα m0 ∈ {Οκτ (ολη), Δεκ, Φεβ, Μαρ} — LOSO m0 με μοναδες· το παραθυρο ΠΕΡΝΑ αν LOSO μοναδες > «ολη» ΚΑΙ οχι χειροτερο σε ≥4/5.
 (Γ) ΚΑΤΩΦΛΙ {4,6,8,10}% LOSO · (Δ) ιδια μηχανη στα Τ−2ω / Τ−30′ (περιγραφικο). Εξοδος: t39_totals_window_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
exec(src)
out2 = []
def P2(s=''): print(s, flush=True); out2.append(str(s))
def fx(D): return np.c_[feats(D), (D.mon == 4).astype(float)]
def fitp(D, Xf, y, tr, te):
    A = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y[tr])
    return D.fair.values[te] + np.c_[np.ones(te.sum()), Xf[te]] @ b
MSTART = {'ολη': (10, 11, 12, 1, 2, 3, 4), 'απο Δεκ': (12, 1, 2, 3, 4), 'απο Φεβ': (2, 3, 4), 'απο Μαρ': (3, 4)}
for tau in ('ανοιγμα', 'Τ−2ω', 'Τ−30′'):
    D = X[X.tau == tau].reset_index(drop=True); ys = D.sea.values; y = (D.tot - D.fair).values; Xf = fx(D)
    lo = np.zeros(len(D)); wf = np.full(len(D), np.nan)
    for s in SE: lo[ys == s] = fitp(D, Xf, y, ys != s, ys == s)
    for s in (2024, 2025, 2026): wf[ys == s] = fitp(D, Xf, y, ys < s, ys == s)
    D['lo'] = lo; D['wf'] = wf
    P2(f'=== {tau} ===')
    w = picks(D[D.sea >= 2024], col='wf', thr=.06)
    P2(f'  (Α) walk-forward ≥6%: {cell(w)} · ανα σεζον ' + ' · '.join(f'{s}: {100 * w[w.sea == s].res.mean():+.1f}% ({len(w[w.sea == s])})' for s in (2024, 2025, 2026)))
    U = {}
    for th in (4, 6, 8, 10):
        p = picks(D, col='lo', thr=th / 100)
        for nm, ms in MSTART.items(): U[(th, nm)] = p[p.mon.isin(ms)]
    UU = {k: v.groupby('sea').res.sum().reindex(SE, fill_value=0) for k, v in U.items()}
    for nm in MSTART: P2(f'  (Β) {nm:8s} ' + ' · '.join(f'{th}%: {cell(U[(th, nm)])}' for th in (6, 8)))
    for keys, lab in ((list(UU), 'κατωφλι+παραθυρο'), ([k for k in UU if k[1] == 'ολη'], 'μονο κατωφλι (ολη)')):
        ch, diff, held = [], [], []
        for s in SE:
            best = max(keys, key=lambda k: UU[k].drop(s).sum()); ch.append(best); held.append(U[best][U[best].sea == s])
            diff.append(UU[best][s] - UU[(6, 'ολη')][s])
        H = __import__('pandas').concat(held)
        P2(f'  LOSO {lab}: {ch} → {cell(H)} · − (6%, ολη): {sum(diff):+.1f}μ (οχι χειροτερο {sum(x >= 0 for x in diff)}/5)')
open(os.path.join(SC, 't39_totals_window_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
