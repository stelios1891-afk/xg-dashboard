"""uecl_under_path.py — 12/10/2026 (Στελιος: «στα under ποτε τα picks της εισοδου ξεκινανε να πεφτουν; ποτε χανεται η αξια, ποσες ωρες πριν;»).
UNDER Β @14 (σκια-προταση) + για συγκριση DOG Α @10, Conference League 4 σεζον, Crown & SBOBET μεσος. Για καθε pick: πορεια της αγορας απο την
ΕΙΣΟΔΟ ως το κλεισιμο σε καθε στιγμη (72/60/48/36/24/18/12/8/6/4/2/1ω/κλεισιμο):
  κινηση = ποσα γκολ εχει ριξει η αγορα το συνολο απο την εισοδο (+ = προς το under μας) · ROI αν επαιζα ΤΟ ΙΔΙΟ pick σε εκεινη τη στιγμη (χωρις φιλτρο τιμης).
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 2 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
def path(r):
    out = {}
    for h in HS:
        if h > r.h: continue
        if r.grp == 'OU':
            s = snap_ou(MIDS[r.i], r.bk, h)
            if not s: continue
            L, o, un = s; mt_ = mtot(L, o, un)
            out[h] = ((-1 if r.side == 'under' else 1) * mt_, settle(GH[r.i] + GA[r.i], L, un if r.side == 'under' else o, r.side == 'over'))
        else:
            s = snap_ah(MIDS[r.i], r.bk, h)
            if not s: continue
            L, oh, oa = s; ln = L if r.side == 1 else -L; o = oh if r.side == 1 else oa
            out[h] = (r.side * implied_margin(r.i, L, oh, oa), picks.settle(GD[r.i], r.side, ln, o))
    return out
for lab in ('UNDER Β @14 (σκια)', 'DOG Α @10 (σημερα)'):
    F = SF[lab]; P = []
    for r in F.itertuples():
        p = path(r)
        if r.h not in p: continue
        m0 = p[r.h][0]
        for h, (m, pnl) in p.items():
            P.append(dict(i=r.i, bk=r.bk, h0=r.h, h=h, mv=m - m0, pnl=pnl))
    P = pd.DataFrame(P)
    print(f'\n{lab} — πορεια της αγορας μετα την εισοδο (+ = προς εμας, σε γκολ)')
    for coh, m_ in (('ΟΛΑ τα picks', P.h0 >= 0), ('picks που βγηκαν ≥36ω πριν', P.h0 >= 36), ('picks που βγηκαν 24-12ω πριν', P.h0.between(12, 24)),
                    ('picks που βγηκαν ≤8ω πριν', P.h0 <= 8)):
        x = P[m_]
        if len(x) == 0: continue
        n0 = x[x.h == x.h0].groupby('bk').size().mean()
        print(f'   {coh} ({n0:.0f} picks):')
        cells = []
        for h in HS:
            y = x[x.h == h]
            if len(y) < 4: continue
            cells.append(f'{"κλεισ" if h == 0 else f"{h}ω"}: {y.mv.mean():+.2f} / ROI {100 * y.groupby("bk").pnl.mean().mean():+.0f}%')
        print('      ' + ' · '.join(cells))
