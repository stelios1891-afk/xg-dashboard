"""uecl_b_shrink_test.py — 12/10/2026. Ευρημα uecl_nonfm_fix2_test: στη Β του Conference το μοντελο ΦΟΥΣΚΩΝΕΙ τη διαφορα και προς τις 2 μεριες
(ομαδα FotMob φαβορι: μοντ +1.10 / αγορα +0.98 / πραγμ +0.75 · ομαδα ΧΩΡΙΣ FotMob φαβορι: μοντ −0.50 / αγορα −0.10 / πραγμ −0.07).
ΜΙΑ παραμετρος: διαφορα του ζευγους χαντικαπ × s (συνολο ιδιο), μονο κατηγορια Β, s απο τις αλλες 3 σεζον (LOSO, Poisson log-lik).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ιδια με ucl_nonfm_fix2_test): Κ1 log-lik καλυτερο ≥3/4 · Κ2 λαθος διαφορας (απολυτο, ανα ρολο φαβ FotMob / φαβ χωρις) μικραινει ·
picks (εκτος δειγματος, κανονες UECL φαβ ≥10 / dog ≥10): μοναδες χαντικαπ συνολικα ≥ σημερα.
"""
import sys
src = open('uecl_nonfm_fix2_test.py', encoding='utf-8').read().split('exec(src)')[0]
exec(src)
src = src.split("# ================= Α. ΣΗΜΕΡΑ =================")[0]
exec(src)
import contextlib, io
def ll_pair(a, b, idx):
    k = np.array([LGF[i] for i in idx])
    return (GH[idx] * np.log(a) - a + GA[idx] * np.log(b) - b - k).sum()
def ah_s(s_, idx):
    T = LH_N[idx] + LA_N[idx]; m = (LH_N[idx] - LA_N[idx]) * s_
    return np.maximum((T + m) / 2, .05), np.maximum((T - m) / 2, .05)
GS = np.round(np.arange(0.30, 1.21, 0.05), 2)
base_ah = {i: (LH_N[i], LA_N[i]) for i in U}; base_ou = {i: (OH[i], OA[i]) for i in U}
with contextlib.redirect_stdout(io.StringIO()): P0 = make_picks(base_ah, base_ou)
k1, Pf, RR = [], [], []
print('ΣΥΜΠΙΕΣΗ ΔΙΑΦΟΡΑΣ s στη Β του Conference (LOSO)')
for hold in SEAS:
    tr = U[SEA[U] != hold]; te = U[SEA[U] == hold]
    s_ = GS[np.argmax([ll_pair(*ah_s(g, tr), tr) for g in GS])]
    k1.append(ll_pair(*ah_s(s_, te), te) - ll_pair(*ah_s(1.0, te), te))
    a, b = ah_s(s_, te)
    with contextlib.redirect_stdout(io.StringIO()):
        Pf.append(make_picks({i: (a[j], b[j]) for j, i in enumerate(te)}, {i: (OH[i], OA[i]) for i in te}))
    for j, i in enumerate(te):
        fmfav = (LH_N[i] > LA_N[i]) == FMH[i]; sg = 1 if FMH[i] else -1
        RR.append(dict(fmfav=fmfav, e0=sg * ((GH[i] - GA[i]) - (LH_N[i] - LA_N[i])), e1=sg * ((GH[i] - GA[i]) - (a[j] - b[j]))))
    print(f'   κρυμμενη {hold}: s = {s_:.2f} · Δlog-lik {k1[-1]:+.2f} ({len(te)} ματς)')
sa = GS[np.argmax([ll_pair(*ah_s(g, U), U) for g in GS])]
print(f'   s με ολες τις σεζον: {sa:.2f}  (1.00 = σημερα · 0.80 = η διαφορα μικραινει 20%)')
R_ = pd.DataFrame(RR); P1 = pd.concat(Pf)
ok1 = sum(x > 0 for x in k1) >= 3
print(f'Κ1 ακριβεια {sum(x > 0 for x in k1)}/4 {"✓" if ok1 else "✗"}')
ok2 = True
for lab, m in (('ομαδα FotMob φαβορι', R_.fmfav), ('ομαδα ΧΩΡΙΣ FotMob φαβορι', ~R_.fmfav)):
    a0, a1 = R_[m].e0.mean(), R_[m].e1.mean(); ok2 &= abs(a1) <= abs(a0)
    print(f'   λαθος διαφορας (σκοπια FotMob), {lab}: {a0:+.2f} → {a1:+.2f} (n{m.sum()})')
print(f'Κ2 λαθος μικραινει και στους 2 ρολους: {"✓" if ok2 else "✗"}')
print('PICKS σημερα → με s (εκτος δειγματος)')
for lab, k in (('ΦΑΒ μεγαλης (FotMob)', 'fav_big'), ('ΦΑΒ μικρης (χωρις)', 'fav_small'), ('DOG μεγαλης', 'dog_big'), ('DOG μικρης (χωρις)', 'dog_small')):
    print(f'   {lab:22s} σημερα {cc(P0[P0.side == k])}')
    print(f'   {"":22s} με s   {cc(P1[P1.side == k])}')
u0 = units(P0[P0.mkt == 'AH']); u1 = units(P1[P1.mkt == 'AH'])
print(f'Κ3 μοναδες χαντικαπ: σημερα {u0:+.1f} → με s {u1:+.1f} {"✓" if u1 >= u0 else "✗"}')
# ιδιο φαινομενο στην Α; (ελεγχος οτι ειναι θεμα Β)
IA = np.array([i for i in np.where(COMP == 'ConferenceLeague')[0] if SRCC[i] == 'FF' and LH_N[i] > 0])
LGF.update({i: lgamma(GH[i] + 1) + lgamma(GA[i] + 1) for i in IA})
print(f'(για συγκριση) s που ταιριαζει στην κατηγορια Α του Conference: {GS[np.argmax([ll_pair(*ah_s(g, IA), IA) for g in GS])]:.2f}')
