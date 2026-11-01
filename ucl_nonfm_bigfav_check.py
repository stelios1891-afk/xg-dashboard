"""ucl_nonfm_bigfav_check.py — 16/10/2026 (Στελιος: «αν υποεκτιμαμε τα γκολ των μεγαλων, τα χαντικαπ τους ειναι ακομα καλυτερα picks απ οσο δειχνει
το μοντελο»). Champions League κατηγορια Β (μια ομαδα χωρις FotMob): (1) ΤΥΦΛΑ η μεγαλη (FotMob) στο χαντικαπ κλεισιματος οταν ειναι φαβορι
της αγορας · (2) κατανομη: πραγματικη διαφορα − γραμμη (μεσος, διαμεσος, % καλυψης, «συντριβες») · (3) μοντελο vs αγορα στα ιδια ματς ·
(4) τα picks του μοντελου (φαβ μεγαλης ≥10%): ποσο πανω απο την αγορα ηταν το μοντελο, ποσο βγηκε η πραγματικοτητα."""
import sys, os
_s = open('ucl_nonfm_fix_test.py', encoding='utf-8').read(); _s = _s[:_s.index('# ================= Β. ΔΙΟΡΘΩΣΗ')]
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
rows = []
for (i, bk, h, L, oh, oa) in SA:
    if h != 0: continue
    big = 1 if FMH[i] else -1; ln = big * L; o = oh if big == 1 else oa
    if ln > -0.5: continue                                         # μεγαλη φαβορι της αγορας
    marg = big * GD[i]; lm = big * (LH_N[i] - LA_N[i])
    rows.append(dict(i=i, bk=bk, sea=SEA[i], ln=ln, o=o, pnl=picks.settle(GD[i], big, ln, o), marg=marg, mod=lm, mkt=-ln))
R = pd.DataFrame(rows); C = R[R.bk == 'Crown']
print(f'Β κατηγορια, η μεγαλη φαβορι αγορας (γραμμη ≤ −0.5) στο κλεισιμο: {len(C)} ματς')
print(f'(1) ΤΥΦΛΑ μεγαλη στο χαντικαπ κλεισιματος: ' + ' · '.join(f'{b} {100 * R[R.bk == b].pnl.mean():+.1f}% ({(R.bk == b).sum()})' for b in ('Crown', 'SBOBET')) +
      ' · ανα σεζον ' + ' '.join(f'{s[2:]}:{100 * R[R.sea == s].pnl.mean():+.0f}' for s in SEAS))
e = C.marg - C.mkt
print(f'(2) πραγματικη διαφορα − γραμμη αγορας: μεσος {e.mean():+.2f} · διαμεσος {e.median():+.2f} · καλυψη (> γραμμη) {100 * (C.marg > C.mkt).mean():.0f}% · '
      f'ισοπαλια/χασμα (≤0 διαφορα) {100 * (C.marg <= 0).mean():.0f}% · συντριβες (νικη ≥4) {100 * (C.marg >= 4).mean():.0f}%')
print(f'    μεση πραγματικη διαφορα {C.marg.mean():+.2f} · μοντελο {C["mod"].mean():+.2f} · αγορα {C.mkt.mean():+.2f}')
for lo, hi in ((0.5, 1.25), (1.5, 2.0), (2.25, 9)):
    z = C[(C.mkt >= lo) & (C.mkt <= hi)]
    if len(z): print(f'    γραμμη {lo}-{hi if hi < 9 else "+"}: n{len(z):3d} · πραγμ {z.marg.mean():+.2f} · μοντ {z["mod"].mean():+.2f} · αγορα {z.mkt.mean():+.2f} · τυφλα {100 * z.pnl.mean():+.1f}%')
F = P0[P0.side == 'fav_big']
if len(F):
    fi = F.drop_duplicates('i').i.values
    print(f'(4) picks μοντελου φαβ μεγαλης ≥10% ({len(fi)} ματς): μοντελο {np.mean([FH[list(U).index(i)] and (LH_N[i] - LA_N[i]) or (LA_N[i] - LH_N[i]) for i in fi]):+.2f} · '
          f'αγορα κλεισ {np.nanmean([CLINE.get(i, np.nan) for i in fi]):+.2f} · πραγματικα {np.mean([(GD[i] if FMH[i] else -GD[i]) for i in fi]):+.2f}')
