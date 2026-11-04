# -*- coding: utf-8 -*-
"""uel_homefav_decomp.py — 4/11/2026 (Στελιος: «η διαφορα ειναι οτι μετραμε τα ευρωπαικα; και ριχνει τοσο το roi;»). Αποσυνθεση +16.8% → +9.8% του κανονα UEL φαβορι εντος:
ιδιο παραθυρο (36/24/18/12ω, πρωτη φορα), ιδια κριτηρια, ΤΡΕΙΣ εκδοχες μηχανης: Α dump 0.8 (euro_blend_dump, 9/10) · Β harness χωρις φετινα (BASE) · Γ harness + Μ8 0.5 (INS).
Β→Γ = η ΚΑΘΑΡΗ επιδραση των φετινων ευρωπαικων · Α→Β = διαφορα των δυο κατασκευων (χωρις καμια σχεση με τα ευρωπαικα). Για καθε βημα: κοινα / φευγουν / μπαινουν."""
import sys, io, contextlib
import numpy as np, pandas as pd
src = open('uel_homefav_inseason.py', encoding='utf-8').read()
pre = src[:src.index('rows = []\nfor i, mid in enumerate(MIDS):')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
io.StringIO = _Q
g = {'__name__': 'ud'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8')
import picks
MIDS, SEA, GD, U, D8, INS, BASE, snap, sdist, cover_q, edge = (g[k] for k in ('MIDS', 'SEA', 'GD', 'U', 'D8', 'INS', 'BASE', 'snap', 'sdist', 'cover_q', 'edge'))
ENG = {'Α dump 0.8': (D8['LH'], D8['LA']), 'Β χωρις φετινα': BASE, 'Γ με Μ8': INS}
def rule(LL, hours=(36, 24, 18, 12)):
    rows = []
    for i, mid in enumerate(MIDS):
        if not U[i] or not D8['FM'][i]: continue
        D = sdist(LL[0][i], LL[1][i])
        for bk in ('Crown', 'SBOBET'):
            for h in hours:
                s = snap(mid, bk, h)
                if not s: continue
                L, oh, oa = s
                if not (1.70 <= oh <= 2.10) or L > -0.5: continue
                pw, pp = cover_q(D, 1, L); e = edge(pw, pp, oh)
                if e >= .04:
                    rows.append(dict(i=i, mid=str(mid), bk=bk, h=h, sea=SEA[i], e=e, ln=L, od=oh, pnl=picks.settle(float(GD[i]), 1, L, oh))); break
    return pd.DataFrame(rows)
def cell(z):
    if not len(z): return '  0'
    n = len(z) / 2
    return f"{n:5.1f} picks {100 * z.pnl.mean():+6.1f}% {z.pnl.sum() / 2:+6.1f}μ"
def seas(z):
    return ' '.join(f"{s[2:]}:{100 * g_.pnl.mean():+.0f}" for s, g_ in z.groupby('sea'))
R = {k: rule(v) for k, v in ENG.items()}
print('ΠΑΡΑΘΥΡΟ 12-36ω (οπως το live) · ιδια κριτηρια · μεσος Crown/SBOBET')
for k, z in R.items():
    print(f'   {k:16s} {cell(z)} │ σεζον {seas(z)} │ θετικες {sum(g_.pnl.mean() > 0 for _, g_ in z.groupby("sea"))}/4')
Uu = np.asarray(U) & np.asarray(D8['FM'])
for a, b in (('Α dump 0.8', 'Β χωρις φετινα'), ('Β χωρις φετινα', 'Γ με Μ8')):
    ka = set(zip(R[a].i, R[a].bk)); kb = set(zip(R[b].i, R[b].bk))
    za = R[a]; zb = R[b]
    both = za[[x in kb for x in zip(za.i, za.bk)]]; out = za[[x not in kb for x in zip(za.i, za.bk)]]; inn = zb[[x not in ka for x in zip(zb.i, zb.bk)]]
    both_b = zb[[x in ka for x in zip(zb.i, zb.bk)]]
    dlh = np.abs(np.asarray(ENG[a][0])[Uu] - np.asarray(ENG[b][0])[Uu]); dla = np.abs(np.asarray(ENG[a][1])[Uu] - np.asarray(ENG[b][1])[Uu])
    ds = (np.asarray(ENG[b][0]) - np.asarray(ENG[b][1]))[Uu] - (np.asarray(ENG[a][0]) - np.asarray(ENG[a][1]))[Uu]
    print(f"\n{a} → {b}: |Δ αναμενομενα γκολ| γηπ {dlh.mean():.3f} / φιλ {dla.mean():.3f} · Δ υπεροχης γηπ. μεσο {ds.mean():+.3f} (sd {ds.std():.3f})")
    print(f"   κοινα   {cell(both)} (με τη 2η μηχανη {cell(both_b)})  │ {seas(both)}")
    print(f"   φευγουν {cell(out)} │ {seas(out)}")
    print(f"   μπαινουν {cell(inn)} │ {seas(inn)}")
print('\nΑΚΡΙΒΩΣ 24ω (το παλιο τεστ), για ελεγχο αναπαραγωγης:')
for k, v in ENG.items():
    z = rule(v, (24,)); print(f'   {k:16s} {cell(z)} │ σεζον {seas(z)}')
print('\nΠΟΣΟ ΕΥΑΙΣΘΗΤΟ: Γ με Μ8, ανα παραθυρο')
for hs in ((36,), (36, 24), (36, 24, 18, 12), (24, 18, 12), (24,), (18,), (12,)):
    z = rule(INS, hs); print(f'   ωρες {str(hs):22s} {cell(z)} │ σεζον {seas(z)}')
