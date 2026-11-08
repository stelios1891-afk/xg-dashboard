"""core7_totals_honest_split.py — 15/10/2026 (Στελιος: «τα overs/συνολα νωρις, 5 μερες πριν, ειχαν κερδος, μετα βρεθηκε λαθος — να επιστρεψουμε; τα ορια
5 μερες πριν στα top-5 ηταν θετικα»). Πανω στα rows του core7_totals_anchor_md1_test (εκδοχη Γ1 = ΤΙΜΙΟΣ ΧΡΟΝΟΣ, αγκυρα απο 7η): χωρισμα
top-5 vs Πορτογαλια/Ολλανδια × παραθυρο αγωνιστικης × ωρες πριν (≥120ω = 5+ μερες) × πλευρα, ανα σεζον. + συγκριση με την παλια (λαθος) εκδοχη Α."""
import sys
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
R = pd.read_csv('core7_totals_anchor_md1_rows.csv', dtype={'season': str})
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
R['grp'] = np.where(R.league.isin(TOP5), 'top-5', 'PT/NL')
SEAS = sorted(R.season.unique())
def fm(y):
    if len(y) == 0: return '      —'
    s = y.groupby('season').pnl.mean()
    return f'n{len(y):4d} {100 * y.pnl.mean():+6.1f}% {y.pnl.sum():+6.1f}μ {int((s > 0).sum())}/{len(s)} │ ' + ' '.join(f'{100 * s.get(q, np.nan):+4.0f}' for q in SEAS)
for var in ('Γ1. αγκυρα απο 7η, τιμιος χρονος', 'Α. οπως ηταν (αγκυρα απο 7η, ανοιγμα)'):
    x = R[R['var'] == var]
    print(f'\n{"=" * 110}\n{var}  · edge ≥10%, 1.70-2.10 · ανα σεζον 22/23/24/25 (%)')
    for bk in ('Crown', 'Bet365'):
        y0 = x[x.book == bk]
        print(f' {bk}')
        for wl, m in (('7-14', y0.md.between(6, 13)), ('15+', y0.md >= 14), ('ολα 7+', y0.md >= 6)):
            for g in ('top-5', 'PT/NL', 'ολα'):
                y = y0[m] if g == 'ολα' else y0[m & (y0.grp == g)]
                print(f'   {wl:7s} {g:6s} ολα: {fm(y)}')
                if g == 'top-5':
                    for hl, hm in (('≥120ω (5+ μερες)', y.hrs >= 120), ('<120ω', y.hrs < 120)):
                        print(f'   {"":7s} {"":6s} {hl:16s} {fm(y[hm])}')
                    for sd in ('OVER', 'UNDER'):
                        print(f'   {"":7s} {"":6s} {sd:16s} {fm(y[y.side == sd])}')
    if var.startswith('Γ1'):
        y = x[(x.book == 'Crown') & (x.md >= 6)]
        print(f'\n ΠΟΤΕ ΒΓΑΙΝΕΙ Η «ΤΙΜΙΑ» ΤΙΜΗ (Crown, 7+): ωρες πριν διαμεσος {y.hrs.median():.0f} · ≥120ω {100 * (y.hrs >= 120).mean():.0f}% των picks')
        print(' ανα λιγκα (Crown, 7+): ' + ' · '.join(f'{lg} {fm(y[y.league == lg]).split("│")[0].strip()}' for lg in sorted(y.league.unique())))
