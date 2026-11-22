# -*- coding: utf-8 -*-
"""t105_janfeb_why.py — ΓΙΑΤΙ ΚΑΙ ΤΑ ΧΑΝΤΙΚΑΠ ΚΑΙ ΤΑ ΣΥΝΟΛΑ ΠΕΦΤΟΥΝ ΤΟΝ ΙΑΝ-ΦΕΒ; (25/10/2026, Στελιος «ναι ελεγξε τα»). ΠΕΡΙΓΡΑΦΙΚΟ.
3 υποθεσεις, ανα ΜΗΝΑ, και στις 2 αγορες:
 Υ1 «η αγορα ειναι πιο σωστη»: λαθος κλεισιματος (ποσο τυχαια ειναι τα ματς) · χασμα μοντελο−κλεισιμο · CLV picks · % picks οπου η αγορα ηρθε προς εμας
 Υ2 «το σκορ πεφτει μεσα στη σεζον»: μεσο συνολο ανα μηνα − μεσο σεζον, ΚΑΘΕ σεζον · πραγμ.−μοντελο & πραγμ.−ανοιγμα ανα μηνα & σεζον
 Υ3 «η διορθωση απουσιων υπερβαλλει»: κλιση (πραγμ. − μοντελο χωρις απουσιες) πανω στη διορθωση απουσιων, ανα μηνα (1.00 = σωστο)
ΧΑΝΤΙΚΑΠ: live μοντελο του t19 (t15 + B2B + απουσιες −2 + μεταγραφες), ανοιγμα Crown, ≥8%, χωρις Απριλιο (οπως t19).
ΣΥΝΟΛΑ: LIVE μηχανη απο _t104_totals_live.csv (τρεξε πρωτα t104_totals_by_period.py), ανοιγμα Crown, ≥8%.
Εξοδος: nba_tests/t105_janfeb_why_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't19_janfeb_diag.py'), encoding='utf-8').read().split("PERS = ('Οκτ'")[0]
g = {'__file__': os.path.join(SC, 't19_janfeb_diag.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, H = g['np'], g['pd'], g['X']
ACT, V, ABS, MON = g['ACT'], g['V'], g['ABS'], g['MON']
H['mon'] = MON[H.i.values]
T = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
MN = ((10, 'Οκτ'), (11, 'Νοε'), (12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ'), (3, 'Μαρ'), (4, 'Απρ'))
rm = lambda v: float(np.sqrt(np.mean(np.asarray(v) ** 2)))
def roi(d):
    if not len(d): return '   —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+5.1f}% ({len(d):3d}, {int((ps > 0).sum())}/{d.sea.nunique()})'
P('t105 · ΓΙΑΤΙ ΙΑΝ-ΦΕΒ · 5 σεζον 2021-22 … 2025-26 · ανοιγμα Crown · picks edge ≥8%')
P('\n=== Υ1 · ΠΟΣΟ ΣΩΣΤΗ ΕΙΝΑΙ Η ΑΓΟΡΑ ΑΝΑ ΜΗΝΑ ===')
P('  ΧΑΝΤΙΚΑΠ (ποντοι διαφορας) · μηνας: ματς · λαθος κλεισιματος · λαθος μοντελου · χασμα (μοντ.−κλεισ., + = χανουμε) · picks ROI · CLV picks · αγορα προς εμας / κοντρα')
for m, nm in MN:
    d = H[H.mon == m]
    if not len(d): continue
    k = d[d.pick]
    P(f'    {nm}: {len(d):4d} · {np.sqrt(d.ec.mean()):5.2f} · {np.sqrt(d.em.mean()):5.2f} · {np.sqrt(d.em.mean()) - np.sqrt(d.ec.mean()):+.2f} · {roi(k)} · {k.clv.mean():+.2f}π · {100 * (k.clv > 0.25).mean():.0f}% / {100 * (k.clv < -0.25).mean():.0f}%')
P('  ΣΥΝΟΛΑ (ποντοι συνολου) · ιδιες στηλες')
for m, nm in MN:
    d = T[T.mon == m]; k = d[d.pick]
    P(f'    {nm}: {len(d):4d} · {rm(d.tot - d.cfair):5.2f} · {rm(d.tot - d.mu):5.2f} · {rm(d.tot - d.mu) - rm(d.tot - d.cfair):+.2f} · {roi(k)} · {k.clv.mean():+.2f}π · {100 * (k.clv > 0.25).mean():.0f}% / {100 * (k.clv < -0.25).mean():.0f}%')
P('  ΙΑΝ-ΦΕΒ ανα σεζον (ROI picks): ' + ' · '.join(
    f"{s - 1}-{s % 100:02d} χαντ {100 * H[(H.sea == s) & H.mon.isin([1, 2]) & H.pick].res.mean():+.1f}% / συν {100 * T[(T.sea == s) & T.mon.isin([1, 2]) & T.pick].res.mean():+.1f}%" for s in sorted(T.sea.unique())))
P('\n=== Υ2 · ΣΚΟΡ ΑΝΑ ΜΗΝΑ (ολα τα ματς) ===')
P('  μεσο συνολο του μηνα − μεσο συνολο της σεζον (ποντοι), καθε σεζον:')
for s in sorted(T.sea.unique()):
    d = T[T.sea == s]; mu = d.tot.mean()
    P(f'    {s - 1}-{s % 100:02d} (μεσο {mu:.1f}): ' + ' · '.join(f"{nm} {d[d.mon == m].tot.mean() - mu:+5.1f}" for m, nm in MN if (d.mon == m).any()))
P('  πραγματικο − μοντελο (+ = το μοντελο ηταν χαμηλα), καθε σεζον:')
for s in sorted(T.sea.unique()):
    d = T[T.sea == s]
    P(f'    {s - 1}-{s % 100:02d}: ' + ' · '.join(f"{nm} {(d[d.mon == m].tot - d[d.mon == m].mu).mean():+5.1f}" for m, nm in MN if (d.mon == m).any()))
P('  πραγματικο − ανοιγμα (+ = η αγορα ηταν χαμηλα), καθε σεζον:')
for s in sorted(T.sea.unique()):
    d = T[T.sea == s]
    P(f'    {s - 1}-{s % 100:02d}: ' + ' · '.join(f"{nm} {(d[d.mon == m].tot - d[d.mon == m].fair).mean():+5.1f}" for m, nm in MN if (d.mon == m).any()))
P('  ΟΛΕΣ μαζι (± τυπικο σφαλμα): ' + ' · '.join(
    f"{nm} μοντ {(T[T.mon == m].tot - T[T.mon == m].mu).mean():+.2f}±{(T[T.mon == m].tot - T[T.mon == m].mu).std() / np.sqrt((T.mon == m).sum()):.2f}" for m, nm in MN))
P('  Ιανουαριος − Δεκεμβριος (μεσο συνολο, ποντοι) ανα σεζον: ' + ' · '.join(
    f"{s - 1}-{s % 100:02d} {T[(T.sea == s) & (T.mon == 1)].tot.mean() - T[(T.sea == s) & (T.mon == 12)].tot.mean():+.1f}" for s in sorted(T.sea.unique())))
P('\n=== Υ3 · ΑΚΡΙΒΕΙΑ ΔΙΟΡΘΩΣΗΣ ΑΠΟΥΣΙΩΝ ΑΝΑ ΜΗΝΑ (κλιση· 1.00 = σωστο, <1 = υπερβαλλουμε) ===')
for m, nm in MN:
    d = H[H.mon == m]
    if len(d):
        ii = d.i.values; y = ACT[ii] - (V[ii] - ABS[ii]); x = ABS[ii]; mm = np.abs(x) > 0
        kh, se_h = (np.polyfit(x[mm], y[mm], 1)[0], np.std(y[mm]) / np.sqrt((x[mm] ** 2).sum() - mm.sum() * x[mm].mean() ** 2)) if mm.sum() > 50 else (np.nan, np.nan)
        hh = f'χαντικαπ {kh:.2f}±{se_h:.2f} (μεση |διορθ.| {np.abs(x).mean():.2f}π)'
    else: hh = 'χαντικαπ —'
    d = T[T.mon == m]; x = (d.mu - d.eng).values; y = (d.tot - d.eng).values; mm = np.abs(x) > 1e-9
    kt = np.polyfit(x[mm], y[mm], 1)[0] if mm.sum() > 50 else np.nan
    se_t = np.std(y[mm]) / np.sqrt(((x[mm] - x[mm].mean()) ** 2).sum()) if mm.sum() > 50 else np.nan
    P(f'  {nm}: {hh} · συνολα {kt:.2f}±{se_t:.2f} (μεση |διορθ.| {np.abs(x).mean():.2f}π)')
open(os.path.join(SC, 't105_janfeb_why_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
