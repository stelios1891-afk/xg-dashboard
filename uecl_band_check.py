"""uecl_band_check.py — 12/10/2026 (Στελιος: «γιατι να αλλαξουν τα κατωφλια; σε ποσες σεζον ειναι τα 46/58/35 picks;»).
Οι ΖΩΝΕΣ που κοβονται (φαβ 4-10%, over 4-8%) ανα βιβλιο/σεζον με τον ΚΑΝΟΝΑ του UCL (ucl_over_band_test): αλλαγη μονο αν η ζωνη ειναι
αρνητικη ΚΑΙ στα 2 βιβλια, ≥3/4 σεζον ΚΑΙ στις 2 σεζον νεας μορφης. + picks ανα σεζον για καθε ροη.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 2 =================')[0]
_D = open(os.devnull, 'w', encoding='utf-8'); _RL = sys.stdout; sys.stdout = _D
exec(_src)
sys.stdout = _RL; sys.stdout.reconfigure(encoding='utf-8')
def first(kind, th):
    X = R[R.kind == kind]; keys = ['i', 'bk', 'side'] if X.grp.iloc[0] == 'AH' else ['i', 'bk']
    return X[X.e >= th].sort_values('h', ascending=False).groupby(keys).head(1)
for lab, kind, lo, hi in (('ΦΑΒΟΡΙ Α', 'φαβορι', .04, .10), ('OVER Α', 'over', .04, .08)):
    a = first(kind, lo); b = first(kind, hi)
    k = ['i', 'bk', 'side'] if kind == 'φαβορι' else ['i', 'bk']
    band = a.merge(b[k], on=k, how='left', indicator=True); band = band[band._merge == 'left_only']
    bk = band.groupby('bk').pnl.mean(); ps = band.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    rule = bool((bk < 0).all()) and (ps < 0).sum() >= 3 and len(pn) == 2 and bool((pn < 0).all())
    print(f'{lab}: picks που ΚΟΒΟΝΤΑΙ (ζωνη {int(lo*100)}-{int(hi*100)}%): {cc(band)}')
    print(f'   κανονας UCL (αρνητικη σε 2 βιβλια, ≥3/4 σεζον, 2 νεας μορφης): {"✓ αλλαζει" if rule else "✗ ΔΕΝ περνα"}')
    print(f'   μοναδες: @{int(lo*100)}% {a.groupby("bk").pnl.sum().mean():+.1f} · @{int(hi*100)}% {b.groupby("bk").pnl.sum().mean():+.1f}')
for lab in ('ΦΑΒ Α @10 (προταση)', 'ΦΑΒ Α @4 (σημερα)', 'OVER Α @8 (προταση)', 'OVER Α @4 (σημερα)', 'DOG Α @10 (σημερα)'):
    F = SF[lab]; n = F.groupby(['sea', 'bk']).size().groupby('sea').mean()
    print(f'{lab:22s} picks ανα σεζον: ' + ' · '.join(f'{s}: {v:.0f}' for s, v in n.items()) + f' · συνολο {n.sum():.0f}')
