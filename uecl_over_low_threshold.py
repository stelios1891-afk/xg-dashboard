"""uecl_over_low_threshold.py — 12/10/2026 (Στελιος: «για τα over, αφου υποτιμαμε τα γκολ, εχεις δοκιμασει χαμηλοτερο κατωφλι;»).
Conference, κατηγορια Α, OVER (ζευγος W2, ισοπαλιες ×0.85), 1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET μεσος.
Κατωφλια −10%…+8% · ΖΩΝΕΣ ανα 2-4 μοναδες (τι προσθετει καθε σκαλι) με τον κανονα του UCL αναποδα (για ΚΑΤΕΒΑΣΜΑ: ζωνη θετικη σε 2 βιβλια,
≥3/4 σεζον, και οι 2 νεας μορφης) · LOSO · ΤΥΦΛΑ over Α (χωρις μοντελο) στην πρωτη τιμη ≤72ω και στο κλεισιμο.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_D = open(os.devnull, 'w', encoding='utf-8'); _RL = sys.stdout; sys.stdout = _D
exec(_src)
sys.stdout = _RL; sys.stdout.reconfigure(encoding='utf-8')
X = R[R.kind == 'over']
def first_o(th): return X[X.e >= th].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
def units(x): return x.groupby('bk').pnl.sum().mean()
print('OVER κατηγοριας Α — κατωφλια (πρωτη εμφανιση με edge ≥ κατωφλι)')
for th in (-.10, -.06, -.04, -.02, 0, .02, .04, .06, .08):
    F = first_o(th); print(f'   ≥{100 * th:+4.0f}%  {cc(F)} · μοναδες {units(F):+5.1f}')
print('\nΖΩΝΕΣ — τι προσθετει καθε σκαλι (picks που μπαινουν με το χαμηλοτερο αλλα οχι με το ψηλοτερο κατωφλι)')
for lo, hi in ((-.10, -.04), (-.04, -.02), (-.02, 0), (-.04, 0), (0, .02), (.02, .04)):
    a = first_o(lo); b = first_o(hi); band = a.merge(b[['i', 'bk']], on=['i', 'bk'], how='left', indicator=True); band = band[band._merge == 'left_only']
    bk = band.groupby('bk').pnl.mean(); ps = band.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    ok = bool((bk > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
    print(f'   {100 * lo:+.0f}…{100 * hi:+.0f}%: {cc(band)} · κανονας (θετικη 2 βιβλια, ≥3/4, 2 νεας μορφης) {"✓" if ok else "✗"}')
outs, allx = loso(X, (-.06, -.04, -.02, 0, .02, .04, .06, .08), ('i', 'bk'))
print('\nLOSO (κατωφλια −6…+8%): ' + ' '.join(f'{h[2:]}:{100 * t:+.0f}' for h, t, _ in outs) + f' → εκτος δειγματος {cc(allx)}')
B0 = X.sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
C0 = X[X.h == 0]
print(f'\nΤΥΦΛΑ over Α (καθε ματς Α, χωρις μοντελο): πρωτη τιμη ≤72ω {cc(B0)} · στο κλεισιμο {cc(C0)}')
