"""uecl_b_dog_path.py — 13/10/2026 (Στελιος: «στα αουτσαιντερ της Β, πως κινειται η αγορα;»). Ιδια αναλυση με uecl_under_path για τα
αουτσαιντερ ΧΩΡΙΣ FotMob της κατηγοριας Β (uecl_b_dog_test, edge ≥10%): για καθε pick, κινηση της αγορας (διαφορα γκολ που δικαιολογει
η τιμη, + = προς το αουτσαιντερ μας) απο την εισοδο ως το κλεισιμο σε καθε στιγμη + ROI αν επαιζα το ιδιο pick τοτε. Συγκριση με τα under Β.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
F = pd.read_csv('uecl_b_dog_picks.csv')
P = []
for r in F.itertuples():
    pth = {}
    for h in HS:
        if h > r.h: continue
        s = snap_ah(MIDS[r.i], r.bk, h)
        if not s: continue
        L, oh, oa = s; ln = L if r.side == 1 else -L; o = oh if r.side == 1 else oa
        pth[h] = (r.side * implied_margin(r.i, L, oh, oa), picks.settle(GD[r.i], r.side, ln, o))
    if r.h not in pth: continue
    m0 = pth[r.h][0]
    for h, (m, pnl) in pth.items(): P.append(dict(i=r.i, bk=r.bk, h0=r.h, h=h, mv=m - m0, pnl=pnl))
P = pd.DataFrame(P)
print('ΑΟΥΤΣΑΙΝΤΕΡ ΧΩΡΙΣ FotMob (Β) — πορεια της αγορας μετα την εισοδο (+ = προς εμας, γκολ διαφορας)')
for coh, m_ in (('picks που βγηκαν ≥36ω πριν', P.h0 >= 36), ('picks που βγηκαν 24-12ω πριν', P.h0.between(12, 24)), ('picks που βγηκαν ≤8ω πριν', P.h0 <= 8)):
    x = P[m_]
    if len(x) == 0: continue
    n0 = x[x.h == x.h0].groupby('bk').size().mean()
    cells = [f'{"κλεισ" if h == 0 else f"{h}ω"}: {y.mv.mean():+.2f} / ROI {100 * y.groupby("bk").pnl.mean().mean():+.0f}%' for h in HS for y in [x[x.h == h]] if len(y) >= 4]
    print(f'   {coh} ({n0:.0f} picks):'); print('      ' + ' · '.join(cells))
cl = P[P.h == 0]
print(f'   ΣΥΝΟΛΟ ως το κλεισιμο: κινηση {cl.mv.mean():+.3f} · προς εμας {100 * (cl.mv > .005).mean():.0f}% · κοντρα {100 * (cl.mv < -.005).mean():.0f}% · ιδια {100 * (cl.mv.abs() <= .005).mean():.0f}%')
