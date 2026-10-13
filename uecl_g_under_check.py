"""uecl_g_under_check.py — 13/10/2026 (Στελιος: «γιατι τοσο λιγα picks στη Γ; με χαμηλοτερο κατωφλι θα εβγαιναν περισσοτερα; πως κινειται η αγορα
απο το ανοιγμα ως το κλεισιμο σε σχεση με εμας;»). Conference κατηγορια Γ (καμια ομαδα με FotMob), UNDER (ζευγος W2, ισοπαλιες ×0.85),
1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET μεσος. (1) κατωφλια 0-14% (2) πορεια αγορας μετα την εισοδο + εισοδος vs κλεισιμο (3) τυφλα.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_D = open(os.devnull, 'w', encoding='utf-8'); _R = sys.stdout; sys.stdout = _D
exec(_src)
sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
X = R[R.kind == 'under Γ']
nG = len({i for i in UI if cat(i) == 'G'})
print(f'CONFERENCE ΚΑΤΗΓΟΡΙΑ Γ: {nG} ματς σε 4 σεζον · με τιμη under 1.70-2.10 καποια στιγμη ≤72ω: {X.i.nunique()}')
def first_(th): return X[X.e >= th].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
print('1. UNDER ανα κατωφλι (πρωτη εμφανιση με edge ≥ κατωφλι):')
for th in (-0.04, 0, .02, .04, .06, .08, .10, .12, .14):
    F = first_(th); print(f'   ≥{100 * th:+3.0f}%  {cc(F)}')
B0 = X.sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
print(f'   ΤΥΦΛΑ under Γ (πρωτη τιμη ≤72ω): {cc(B0)} · στο κλεισιμο: {cc(X[X.h == 0])}')
print('   ποσο edge δινει το μοντελο στα ματς Γ (πρωτη τιμη, Crown): ' +
      ' · '.join(f'{lab} {100 * (B0[B0.bk == "Crown"].e >= lo).mean():.0f}%' for lab, lo in (('≥0%', 0), ('≥4%', .04), ('≥8%', .08), ('≥14%', .14))))
print('2. ΠΟΡΕΙΑ ΑΓΟΡΑΣ μετα την εισοδο (γκολ που δικαιολογει η τιμη · + = η αγορα κατεβαζει γκολ = προς το under μας):')
for th in (.04, .14):
    F = first_(th); P = []
    for r in F.itertuples():
        pth = {}
        for h in HS:
            if h > r.h: continue
            s = snap_ou(MIDS[r.i], r.bk, h)
            if s: pth[h] = (-mtot(*s), settle(GH[r.i] + GA[r.i], s[0], s[2], False))
        if r.h in pth:
            for h, (m, pnl) in pth.items(): P.append(dict(h0=r.h, h=h, mv=m - pth[r.h][0], pnl=pnl, bk=r.bk))
    P = pd.DataFrame(P); cl = P[P.h == 0]
    cells = [f'{"κλεισ" if h == 0 else f"{h}ω"}: {y.mv.mean():+.2f}' for h in HS for y in [P[(P.h == h) & (P.h0 >= 24)]] if len(y) >= 4]
    print(f'   @{100 * th:.0f}% ({len(F) / 2:.0f} picks) · picks που βγηκαν ≥24ω πριν: ' + ' · '.join(cells))
    print(f'      ΣΥΝΟΛΟ ως το κλεισιμο: κινηση {cl.mv.mean():+.3f} · προς εμας {100 * (cl.mv > .005).mean():.0f}% / κοντρα {100 * (cl.mv < -.005).mean():.0f}% · '
          f'ROI στην εισοδο {100 * F.groupby("bk").pnl.mean().mean():+.1f}% vs στο κλεισιμο {100 * cl.groupby("bk").pnl.mean().mean():+.1f}%')
