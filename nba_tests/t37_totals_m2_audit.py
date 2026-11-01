# -*- coding: utf-8 -*-
"""t37_totals_m2_audit.py — ΕΛΕΓΧΟΣ της μηχανης Μ2 (t36) πριν την αναφορα: συντελεστες (ολα τα δεδομενα + ανα LOSO), picks LOSO ανα σεζον/over-under/
περιοδο/ζωνη, και 3 πραγματικα παραδειγματα. (21/10/2026)"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
exec(src)
def P2(s=''): print(s, flush=True); out2.append(s)
out2 = []
NAMES = ['μ − αγορα', 'LO (επιθεση εκτος)', 'LD (αμυνα εκτος)', 'LOp − LO (αμφιβολοι επιθ.)', 'LDp − LD (αμφιβολοι αμυν.)', 'Οκτ-Δεκ', 'Μαρ-Απρ', 'γραμμη − 225', 'αγωνας ≤10']
G0 = None
for tau in ('ανοιγμα', 'Τ−30′'):
    D = X[X.tau == tau].reset_index(drop=True); ys = D.sea.values; y = (D.tot - D.fair).values; Xf = feats(D)
    A = np.c_[np.ones(len(D)), Xf]; b = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y)
    P2(f'=== {tau}: συντελεστες Μ2 (ολα) · σταθερα {b[0]:+.2f} · ' + ' · '.join(f'{n} {v:+.2f}' for n, v in zip(NAMES, b[1:])))
    m2 = np.zeros(len(D))
    for s in SE:
        tr = ys != s; At = np.c_[np.ones(tr.sum()), Xf[tr]]; bb = np.linalg.solve(At.T @ At + 50 * np.eye(At.shape[1]), At.T @ y[tr])
        m2[ys == s] = D.fair.values[ys == s] + np.c_[np.ones((ys == s).sum()), Xf[ys == s]] @ bb
        P2(f'   χωρις {s}: ' + ' · '.join(f'{v:+.2f}' for v in bb))
    D['m2'] = m2
    pk = picks(D, col='m2', thr=.06); pk = pk.merge(D[['i', 'home', 'away', 'date', 'T', 'fair', 'm2', 'mu', 'tot', 'lo', 'ld']].rename(columns={'T': 'TT'}), on='i')
    P2(f'   picks ≥6%: {cell(pk)} | over {cell(pk[pk.sd == 1])} | under {cell(pk[pk.sd == -1])}')
    for per in ('Οκτ-Δεκ', 'Ιαν-Φεβ', 'Μαρ-Απρ'): P2(f'      {per}: {cell(pk[pk.per == per])}')
    P2('      ανα σεζον: ' + ' · '.join(f'{s}: {100 * pk[pk.sea == s].res.mean():+.1f}% ({len(pk[pk.sea == s])})' for s in SE))
    if tau == 'ανοιγμα': G0 = pk
P2(''); P2('=== ΠΑΡΑΔΕΙΓΜΑΤΑ (ανοιγμα, ≥6%) ===')
for r in G0.sample(4, random_state=7).itertuples():
    P2(f'  {r.date} {r.home}-{r.away}: γραμμη {r.TT} · αγορα δικαιο {r.fair:.1f} · live μοντελο {r.mu:.1f} · Μ2 {r.m2:.1f} · απουσιες LO {r.lo:.2f} LD {r.ld:.2f} · '
       f'{"OVER" if r.sd == 1 else "UNDER"} · πραγματικο {r.tot:.0f} → {r.res:+.2f}μ')
open(os.path.join(SC, 't37_totals_m2_audit_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
