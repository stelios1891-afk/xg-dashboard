"""uel_fix_clv_windows.py — 15/10/2026 (Στελιος: «αφου 24ω ειναι καλυτερο απο 48 ή 72, σημαινει οτι δεν ερχεται κοντα μας η αγορα;»).
Europa κατηγορια Α, σημερινο (Μ) vs διορθωμενο (ΒΕ, ιδιες LOSO παραμετροι με euro_fix_threshold_timing), κατωφλι ≥4%:
 (1) για picks που βγαινουν σε καθε στιγμη: ποσο κινειται η αγορα ΠΡΟΣ το pick μετα (ως 24ω, ως κλεισιμο)
 (2) ΙΔΙΑ picks (οσα βγαινουν ηδη 72ω πριν): ROI αν τα επαιζες 72ω / 48ω / 24ω / 12ω / κλεισιμο — το καθαρο αποτελεσμα του χρονισμου
"""
import sys
exec(open('euro_fix_threshold_timing.py', encoding='utf-8').read().split("for cm in COMP_ONLY:")[0])
cm = 'EuropaLeague'
x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
LV = {}
for ver in ('M', 'BE'):
    lh = np.zeros(len(x)); la = np.zeros(len(x))
    for s in seas:
        te = (x.sea == s).values; p = fitV(x[~te], ver) if ver != 'M' else (0, 0, 0, 0, 0, 0)
        a, b = lamV(x[te], p); lh[te] = a; la[te] = b
    LV[ver] = (lh, la)
xa_ = x[x.cat == 'A']
W2 = [72, 48, 24, 12, 6, 1, 0]
for ver in ('M', 'BE'):
    print(f'\n===== {"ΣΗΜΕΡΙΝΟ" if ver == "M" else "ΔΙΟΡΘΩΜΕΝΟ (τεντωμα)"} · κατωφλι ≥4%')
    R = []
    for k_ in xa_.index:
        r = x.loc[k_]; i = int(r.i); mid = str(MIDS[i]); D_ = sdist(LV[ver][0][k_], LV[ver][1][k_])
        for bk in ('Crown', 'SBOBET'):
            S = {w: snapT(mid, bk, w) for w in W2}
            M_ = {w: implied_margin(i, *S[w]) if S[w] else np.nan for w in W2}
            for w in W2:
                s = S[w]
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if not (1.70 <= o <= 2.10): continue
                    for kn, cond, how in KINDS:
                        if not cond(ln): continue
                        f = cover_q if how == 'q' else picks.p_cover
                        if edge(*f(D_, side, ln), o) < .04: continue
                        later = {}
                        for w2 in W2:
                            s2 = S[w2]
                            if s2 and W2.index(w2) >= W2.index(w):
                                L2, a2, b2 = s2; o2 = a2 if side == 1 else b2
                                later[w2] = picks.settle(GD[i], side, L2 if side == 1 else -L2, o2)
                        R.append(dict(w=w, kind=kn, bk=bk, sea=r.sea, pnl=picks.settle(GD[i], side, ln, o),
                                      mv24=side * (M_[24] - M_[w]) if w in (72, 48) and np.isfinite(M_[24]) else np.nan,
                                      mvc=side * (M_[0] - M_[w]) if np.isfinite(M_[0]) and w != 0 else np.nan, later=later))
    R = pd.DataFrame(R)
    for kn, *_ in KINDS:
        print(f'   {kn}')
        for w in W2[:-1]:
            y = R[(R.w == w) & (R.kind == kn)]
            if len(y) < 10: continue
            print(f'      μπαινεις {WLAB[w]:9s} n{len(y) / 2:4.0f} · ROI {100 * y.pnl.mean():+6.1f}% · η αγορα μετα: ως 24ω {y.mv24.mean():+.3f} · ως κλεισιμο {y.mvc.mean():+.3f} γκολ (+ = προς εμας)')
        y = R[(R.w == 72) & (R.kind == kn)]
        if len(y) >= 10:
            line = '      ΙΔΙΑ picks (οσα βγαινουν 72ω): ROI αν τα επαιζες '
            for w2 in (72, 48, 24, 12, 0):
                v = [d.get(w2) for d in y.later if d.get(w2) is not None]
                if v: line += f'{WLAB[w2]} {100 * np.mean(v):+.1f}% · '
            print(line)
