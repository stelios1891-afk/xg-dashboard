# -*- coding: utf-8 -*-
"""ucl_window_compare.py — 19/10/2026 (Στελιος: «κατι παει λαθος, δεν τρεξαμε loso σε ολα τα κατωφλια; πως βγαινουν διαφορετικα;»).
Ιδια μηχανη με ucl_rule_band_test· ΜΟΝΗ διαφορα = ΠΑΡΑΘΥΡΟ ΕΙΣΟΔΟΥ: ≤72ω (οπως τα τεστ 10/10-16/10) vs ≤168ω (live απο 16/10).
OVER: νεα μορφη 2024-26 (ετσι κρινονται τα συνολα) · ΦΑΒΟΡΙ & DNB: 4 σεζον + νεα μορφη. Ζωνες edge πρωτης εμφανισης."""
import sys
_s = open('ucl_rule_band_test.py', encoding='utf-8').read()
exec(_s[:_s.index("for role, nm, live in")])
FULL = HS
for role in ('over', 'fav', 'dnb'):
    print(f'\n{"=" * 110}\n{role.upper()}')
    for wlab, hs in (('≤72ω', tuple(h for h in FULL if h <= 72)), ('≤168ω', FULL)):
        globals()['HS'] = hs
        D = over_rows() if role == 'over' else ah_rows(role)
        b = D[D.th == .04]
        for per, ss in (('νεα μορφη', NEW), ('4 σεζον', SE)):
            if role == 'over' and per == '4 σεζον': continue
            parts = []
            for lab, lo, hi in (('4-10%', .04, .10), ('≥10%', .10, 9), ('ΟΛΑ ≥4%', .04, 9)):
                y = b[(b.e >= lo) & (b.e < hi) & b.sea.isin(ss)]; u, r, n = units(y); s = y.groupby('sea').pnl.mean()
                parts.append(f'{lab} {n:3.0f} {100 * r:+6.1f}% ({" ".join(f"{100 * v:+.0f}" for v in s.values)})')
            print(f'   είσοδος {wlab:6s} {per:10s} │ ' + ' │ '.join(parts))
    globals()['HS'] = FULL
