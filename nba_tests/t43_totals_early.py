# -*- coding: utf-8 -*-
"""t43_totals_early.py — ΣΥΝΟΛΑ NBA · Μ2δ · ΓΙΑΤΙ ΧΑΝΕΙ ΣΤΟΥΣ ΠΡΩΤΟΥΣ ΜΗΝΕΣ; (21/10/2026, Στελιος «κλιση, λαθος προβλεψης, κινηση αγορας, ατυχια; ομαδες που αλλαξαν πολυ;»)
Βαση _t35 (ανοιγμα) · Μ2δ με LOSO (5 σεζον) ΚΑΙ walk-forward (2024-26) · picks ≥6%. Περιοδοι: Οκτ-Νοε · Δεκ-Ιαν · Φεβ-Απρ.
ΕΛΕΓΧΟΙ (ΠΡΟ-ΔΗΛΩΜΕΝΕΣ ΕΡΜΗΝΕΙΕΣ, γραφτηκαν πριν το τρεξιμο):
 Κ1 ΤΥΧΗ: πραγματικες μοναδες − αναμενομενες απο το ΚΛΕΙΣΙΜΟ (evc). Αν |z| < 2 ΚΑΙ CLV Οκτ-Νοε > 0 → «συμβατο με ατυχια».
 Κ2 ΚΛΙΣΗ: (πραγμ − αγορα) πανω στο (Μ2δ − αγορα) ανα περιοδο (ολα τα ματς). 1 = σωστη ενταση· αν Οκτ-Νοε < 0.5 με 2·SE κατω απο 1 → «υπερβολικο νωρις».
 Κ3 ΛΑΘΟΣ ΠΡΟΒΛΕΨΗΣ: RMSE Μ2δ vs αγορα ανα περιοδο· μεση μεροληψια (πραγμ − Μ2δ) ανα σεζον/περιοδο (αλλαζει προσημο → θορυβος σταθερας Οκτ-Δεκ).
 Κ4 ΑΓΟΡΑ: κινηση ανοιγμα→κλεισιμο προς το pick (CLV σε π.) και (πραγμ − κλεισιμο) προς το pick ανα περιοδο.
 Κ5 ΑΛΛΑΓΗ ΡΟΣΤΕΡ: μεριδιο περσινων λεπτων στο ροστερ του 1ου ματς (t4). Ματς «αλλαγμενο» αν μια απο τις 2 ομαδες < 0.6.
    Εξηγει την απωλεια αν: Οκτ-Νοε αλλαγμενα ROI < −5% ΚΑΙ μη-αλλαγμενα > 0 (και ιδια φορα σε LOSO και walk-forward).
Εξοδος: t43_totals_early_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# --- μεριδιο επιστρεφοντων λεπτων (ιδιο με t4) ---
g4 = {'__file__': os.path.join(SC, 'absence_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0], g4)
A = g4['A']; SHARE = {}
for s in sorted(A.s.unique()):
    if s - 1 not in set(A.s): continue
    cur = A[A.s == s]; prev = A[A.s == s - 1]
    for t in sorted(cur.team.unique()):
        tg = cur[cur.team == t].sort_values(['date', 'GAME_ID']); g1 = tg.GAME_ID.iloc[0]
        ros = set(tg[tg.GAME_ID == g1].pid); pt = prev[prev.team == t].groupby('pid').MIN.sum()
        SHARE[(int(s), t)] = float(pt[pt.index.isin(ros)].sum() / pt.sum()) if pt.sum() > 0 else 1.0
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
with contextlib.redirect_stdout(_B()): exec(src)
sys.stdout.reconfigure(encoding='utf-8')
out2 = []
def P2(s=''): print(s, flush=True); out2.append(str(s))
D = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
D['P3'] = D.mon.map({10: 'Οκτ-Νοε', 11: 'Οκτ-Νοε', 12: 'Δεκ-Ιαν', 1: 'Δεκ-Ιαν', 2: 'Φεβ-Απρ', 3: 'Φεβ-Απρ', 4: 'Φεβ-Απρ'})
D['sh_h'] = [SHARE.get((int(s), h), np.nan) for s, h in zip(D.sea, D.home)]; D['sh_a'] = [SHARE.get((int(s), a), np.nan) for s, a in zip(D.sea, D.away)]
D['sh_min'] = D[['sh_h', 'sh_a']].min(axis=1)
P2(f'μεριδιο βρεθηκε: {D.sh_min.notna().mean() * 100:.0f}% των ματς · μεσο {np.nanmean(D.sh_min):.2f}')
ys = D.sea.values; y = (D.tot - D.fair).values; Xf = np.c_[feats(D), (D.mon == 4).astype(float)]
def fitp(tr, te):
    A_ = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A_.T @ A_ + 50 * np.eye(A_.shape[1]), A_.T @ y[tr])
    return D.fair.values[te] + np.c_[np.ones(te.sum()), Xf[te]] @ b
D['lo_'] = 0.0; D['wf'] = np.nan
for s in SE: D.loc[ys == s, 'lo_'] = fitp(ys != s, ys == s)
for s in (2024, 2025, 2026): D.loc[ys == s, 'wf'] = fitp(ys < s, ys == s)
PER = ('Οκτ-Νοε', 'Δεκ-Ιαν', 'Φεβ-Απρ')
def pk_of(col, d):
    p = picks(d, col=col, thr=.06)
    if not len(p): return p
    m = d.set_index('i'); p['P3'] = m.loc[p.i, 'P3'].values; p['sh'] = m.loc[p.i, 'sh_min'].values; p['clo'] = (p.sd * (m.loc[p.i, 'tot'].values - m.loc[p.i, 'cfair'].values))
    return p
SETS = {'LOSO 5σ': pk_of('lo_', D), 'walk-forward 24-26': pk_of('wf', D[D.sea >= 2024])}
for nm, pk in SETS.items():
    P2(''); P2(f'################ {nm} ################')
    P2('=== Κ1 ΤΥΧΗ: πραγματικο vs αναμενομενο απο το κλεισιμο ===')
    for per in PER:
        d = pk[pk.P3 == per]
        if not len(d): continue
        z = (d.res.sum() - d.evc.sum()) / np.sqrt(len(d) * 0.93)
        P2(f'  {per}: {cell(d)} · αναμενομενο (κλεισιμο) {100 * d.evc.mean():+.1f}% → πραγμ − αναμ. {d.res.sum() - d.evc.sum():+.1f}μ (z {z:+.2f}) · over {cell(d[d.sd == 1])} · under {cell(d[d.sd == -1])}')
    P2('  ανα σεζον Οκτ-Νοε / Δεκ-Ιαν: ' + ' · '.join(f"{s}: {100 * pk[(pk.sea == s) & (pk.P3 == 'Οκτ-Νοε')].res.mean():+.0f}% ({len(pk[(pk.sea == s) & (pk.P3 == 'Οκτ-Νοε')])}) / {100 * pk[(pk.sea == s) & (pk.P3 == 'Δεκ-Ιαν')].res.mean():+.0f}% ({len(pk[(pk.sea == s) & (pk.P3 == 'Δεκ-Ιαν')])})" for s in sorted(pk.sea.unique())))
    P2('=== Κ4 ΑΓΟΡΑ: κινηση ανοιγμα→κλεισιμο προς το pick · πραγμ − κλεισιμο προς το pick (π.) ===')
    for per in PER:
        d = pk[pk.P3 == per]
        if len(d): P2(f'  {per}: CLV {d.clv.mean():+.2f} π. (αγορα προς εμας {100 * (d.clv > 0).mean():.0f}% / κοντρα {100 * (d.clv < 0).mean():.0f}%) · μετα το κλεισιμο {d.clo.mean():+.2f} ± {d.clo.std() / np.sqrt(len(d)):.2f} π. · edge δηλωμενο {100 * d.e.mean():.1f}%')
    P2('=== Κ5 ΑΛΛΑΓΗ ΡΟΣΤΕΡ (μικροτερο μεριδιο επιστρεφοντων λεπτων των 2 ομαδων) ===')
    for per in PER:
        d = pk[pk.P3 == per]
        if not len(d): continue
        P2(f'  {per}: ' + ' · '.join(f'{lab} {cell(x)}' for lab, x in (('<0.45', d[d.sh < .45]), ('0.45-0.6', d[(d.sh >= .45) & (d.sh < .6)]), ('≥0.6', d[d.sh >= .6]))))
        P2(f'      over/under στα αλλαγμενα (<0.6): over {cell(d[(d.sh < .6) & (d.sd == 1)])} · under {cell(d[(d.sh < .6) & (d.sd == -1)])}')
P2(''); P2('################ ΟΛΑ ΤΑ ΜΑΤΣ (οχι μονο picks) ################')
P2('=== Κ2 ΚΛΙΣΗ: (πραγμ − αγορα) πανω στο (Μ2δ − αγορα) · Κ3 ΛΑΘΟΣ: RMSE Μ2δ / αγορα ===')
for col, lab in (('lo_', 'LOSO'), ('wf', 'walk-forward')):
    for per in PER:
        d = D[(D.P3 == per) & D[col].notna()]; x = (d[col] - d.fair).values; yy = (d.tot - d.fair).values
        b = np.polyfit(x, yy, 1)[0]; se = np.sqrt(np.sum((yy - np.polyval(np.polyfit(x, yy, 1), x)) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
        P2(f'  {lab:12s} {per}: κλιση {b:+.2f} ± {se:.2f} · sd(Μ2δ − αγορα) {x.std():.2f} · RMSE Μ2δ {np.sqrt(np.mean((d.tot - d[col]) ** 2)):.3f} / αγορα {np.sqrt(np.mean((d.tot - d.fair) ** 2)):.3f} · n {len(d)}')
P2('=== Κ3 ΜΕΡΟΛΗΨΙΑ ανα σεζον (πραγμ − αγορα ανοιγματος / πραγμ − Μ2δ LOSO) ===')
for per in PER:
    P2(f'  {per}: ' + ' · '.join(f'{s}: {(D[(D.sea == s) & (D.P3 == per)].tot - D[(D.sea == s) & (D.P3 == per)].fair).mean():+.1f} / {(D[(D.sea == s) & (D.P3 == per)].tot - D[(D.sea == s) & (D.P3 == per)].lo_).mean():+.1f}' for s in SE))
P2('=== Κ5 ΜΕΡΟΛΗΨΙΑ ΑΓΟΡΑΣ ανα αλλαγη ροστερ (ολα τα ματς Οκτ-Νοε): πραγμ − αγορα / πραγμ − Μ2δ ===')
d = D[D.P3 == 'Οκτ-Νοε']
for lab, m in (('<0.45', d.sh_min < .45), ('0.45-0.6', (d.sh_min >= .45) & (d.sh_min < .6)), ('≥0.6', d.sh_min >= .6)):
    x = d[m]; P2(f'  {lab:9s} n {len(x):4d} · πραγμ − αγορα {(x.tot - x.fair).mean():+.2f} ± {(x.tot - x.fair).std() / np.sqrt(len(x)):.2f} · πραγμ − Μ2δ {(x.tot - x.lo_).mean():+.2f} · RMSE Μ2δ {np.sqrt(np.mean((x.tot - x.lo_) ** 2)):.2f} / αγορα {np.sqrt(np.mean((x.tot - x.fair) ** 2)):.2f}')
open(os.path.join(SC, 't43_totals_early_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
