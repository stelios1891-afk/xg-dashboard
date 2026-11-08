"""uecl_over_by_gap.py — 13/10/2026 (Στελιος: «στα συνολα βοηθαει η διορθωση;»). Η συμπιεση δεν αγγιζει το συνολο (σταθερο εκ κατασκευης).
Ομως το ιδιο φαινομενο (τα ευρωπαικα ματς ειναι πιο «ισορροπημενα») μπορει να φαινεται στα γκολ: uecl_mechanism → η ΔΗΜΙΟΥΡΓΙΑ (xG − μοντελο)
ειναι +0.21/πλευρα στα ισορροπημενα ματς, −0.08 στα ανισα. Εδω: Conference κατηγορια Α, ανα διαφορα του μοντελου (|λ_γηπ − λ_φιλ|):
γκολ / xG / μοντελο συνολων / αγορα + OVER picks (live κανονας ≥ −2%, 1.70-2.10, πρωτη εμφανιση ≤72ω) και UNDER @10.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
IA = [i for i in UI if cat(i) == 'A' and LH_N[i] > 0]
GAP = {i: abs(LH_N[i] - LA_N[i]) for i in IA}
BINS = ((0, .4, 'ισορροπημενα (<0.4)'), (.4, .9, 'μετρια (0.4-0.9)'), (.9, 9, 'ανισα (>0.9)'))
print('CONFERENCE, ΚΑΤΗΓΟΡΙΑ Α — ανα διαφορα δυναμης που βλεπει το μοντελο')
for lo, hi, lab in BINS:
    ii = [i for i in IA if lo <= GAP[i] < hi]
    tg = np.mean([GH[i] + GA[i] for i in ii]); mo = np.mean([OH[i] + OA[i] for i in ii])
    xg = np.nanmean([sum(XG[i]) if XG.get(i) else np.nan for i in ii])
    mk = []
    for i in ii:
        so = snap_ou(MIDS[i], 'Crown', 0) or snap_ou(MIDS[i], 'SBOBET', 0)
        if so: mk.append(mtot(*so))
    print(f'   {lab:22s} n{len(ii):3d} · γκολ {tg:.2f} · xG {xg:.2f} · μοντελο {mo:.2f} · αγορα {np.mean(mk):.2f} · πραγμ − μοντ {tg - mo:+.2f} · πραγμ − αγορα {tg - np.mean(mk):+.2f}')
for kind, th in (('over', -.02), ('under', .10)):
    X = R[R.kind == kind]; F = X[X.e >= th].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
    print(f'   {kind.upper()} @{100 * th:+.0f}% ανα διαφορα:')
    for lo, hi, lab in BINS:
        y = F[F.i.map(lambda i: lo <= GAP.get(i, -1) < hi)]
        print(f'      {lab:22s} {cc(y)}')
