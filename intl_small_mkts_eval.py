"""
intl_small_mkts_eval.py — ΤΕΣΤ 2/10/2026 (Στελιος): εθνικες — ΝΙΚΗ 1Χ2 (καθε τιμη ≥1.70, ζωνες) vs DNB (γραμμη 0) vs −0.25 φαβορι.
Πηγη: intl_window_test ... SMALL_MKTS=1 (live ρυθμισεις, 72ω πρωτη εμφανιση, edge ≥10%, Crown & SBOBET, 5 σεζον).
Συναινεση ≥2/3 μοντελα (ιδια αγορα & πλευρα) — τιμη της πιο αργης εμφανισης (οπως intl_model_choice_final).
ΠΡΟ-ΔΗΛΩΣΗ: αγορα/ζωνη ΥΠΟΨΗΦΙΑ αν ROI > 0 ΚΑΙ στα 2 βιβλια, θετικη ≥3/5 σεζον (Crown), n ≥ 20 (Crown).
Επιπλεον: ιδια ματς οπου βγαινουν ΚΑΙ νικη ΚΑΙ DNB/−0.25 → ποια απεδωσε καλυτερα. Δεν αλλαζει τιποτα live.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
S = pd.read_csv('intl_window_test_proper_ahdogold_TmixN12_gddeepfav_small_bets.csv', dtype={'mid': str, 'season': str})
S = S[S.model.isin(['M1', 'M2', 'M3'])]
def band(r):
    if r.rule != 'WIN': return r.rule
    o = r.odds
    return 'WIN 1.70-2.10' if o < 2.10 else ('WIN 2.10-2.60' if o < 2.60 else ('WIN 2.60-3.50' if o < 3.50 else 'WIN >3.50'))
def cons(df):
    rows = []
    for _, g in df.groupby(['mid', 'book', 'rule', 'side']):
        if g.model.nunique() >= 2: rows.append(g.sort_values('hours').iloc[0])
    R = pd.DataFrame(rows); R['band'] = R.apply(band, axis=1); return R
def fm(x):
    if len(x) < 3: return f'n{len(x):4d}        —        '
    ps = x.groupby('season').pnl.mean()
    return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}u {int((ps > 0).sum())}/{len(ps)}'
ORDER = ['WIN 1.70-2.10', 'WIN 2.10-2.60', 'WIN 2.60-3.50', 'WIN >3.50', 'DNB', 'Q25']
LAB = {'Q25': '−0.25 φαβορι', 'DNB': 'DNB (γραμμη 0)'}
passed = []
for wlab in ('72ω', 'closing'):
    W = S[S.win == wlab]; C = cons(W)
    print(f'\n=== {wlab} — ΣΥΝΑΙΝΕΣΗ ≥2/3 — Crown | SBOBET (n · ROI · μοναδες · σεζον θετικες) ===')
    for b in ORDER:
        x = C[C.band == b]; c, s_ = x[x.book == 'Crown'], x[x.book == 'SBOBET']
        tag = ''
        if wlab == '72ω' and len(c) >= 20 and c.pnl.mean() > 0 and len(s_) and s_.pnl.mean() > 0 and int((c.groupby('season').pnl.mean() > 0).sum()) >= 3:
            tag = '  ← ΥΠΟΨΗΦΙΑ'; passed.append(b)
        print(f'  {LAB.get(b, b):16s} {fm(c)} | {fm(s_)}{tag}')
    if wlab == '72ω':
        print('\n  ΑΝΑ ΜΟΝΤΕΛΟ (72ω, Crown): ' )
        for b in ORDER:
            print(f'    {LAB.get(b, b):16s} ' + ' · '.join(f'{m}: {fm(W[(W.model == m) & (W.book == "Crown") & (W.apply(band, axis=1) == b)])}' for m in ('M1', 'M2', 'M3')))
        # ιδια ματς: νικη + DNB / νικη + −0.25 (ιδια πλευρα)
        print('\n  ΙΔΙΑ ΜΑΤΣ (ιδια πλευρα, συναινεση και στα δυο) — Crown | SBOBET')
        for other in ('DNB', 'Q25'):
            for bk in ('Crown', 'SBOBET'):
                w = C[(C.rule == 'WIN') & (C.book == bk)].set_index(['mid', 'side']); o = C[(C.rule == other) & (C.book == bk)].set_index(['mid', 'side'])
                k = w.index.intersection(o.index)
                if len(k) == 0: print(f'    νικη vs {LAB[other]} ({bk}): κανενα κοινο ματς'); continue
                wp, op_ = w.loc[k], o.loc[k]
                print(f'    νικη vs {LAB[other]} ({bk}): {len(k)} κοινα ματς · ΝΙΚΗ {100*wp.pnl.mean():+.1f}% ({wp.pnl.sum():+.1f}u, μεση τιμη {wp.odds.mean():.2f}) · '
                      f'{LAB[other]} {100*op_.pnl.mean():+.1f}% ({op_.pnl.sum():+.1f}u, μεση τιμη {op_.odds.mean():.2f})')
        # μονο νικες οπου δεν υπαρχει χαντικαπ ≥0.5 (δηλ. γραμμη −0.25/0/+0.25) — ο νεος κανονας
        print('\n  ΖΩΝΕΣ ΝΙΚΗΣ ανα αποδοση (Crown): εδω φαινεται αν τα «@7» διαφερουν απο τις λογικες νικες')
        x = C[(C.rule == 'WIN') & (C.book == 'Crown')]
        for lo, hi in ((1.7, 2.1), (2.1, 2.6), (2.6, 3.5), (3.5, 5), (5, 99)):
            y = x[(x.odds >= lo) & (x.odds < hi)]
            print(f'    @{lo:.2f}-{hi if hi < 99 else "∞"}: {fm(y)} · ποσοστο νικων {100*(y.pnl > 0).mean() if len(y) else 0:.0f}% (χρειαζεται ~{100/((lo+min(hi,9))/2):.0f}%)')
print(f'\nΚΡΙΣΗ (72ω, προ-δηλωμενη): υποψηφιες = {passed or "ΚΑΜΙΑ"}')
