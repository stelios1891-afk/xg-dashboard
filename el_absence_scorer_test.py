# -*- coding: utf-8 -*-
"""el_absence_scorer_test.py — EUROLEAGUE: ΜΕΤΡΑΕΙ Η «ΑΞΙΑ» ΤΟΥ ΑΠΟΝΤΑ ΠΕΡΑ ΑΠΟ ΤΑ ΛΕΠΤΑ; (9/10/2026, Στελιος: «πως ξερουμε οτι η υποτιμηση των
σκορερ, π.χ. Nunn, ειναι σωστη; — τρεξε και αυτο το τεστ»).
Βαση = μοντελο + κοστος «μονο λεπτα» (γ .5, el_player_absence_value, LOSO). Υπολοιπο r = πραγμ − (μοντελο + κοστος λεπτων).
Χαρακτηριστικα απόντα (απο ματς ΠΡΙΝ, τυποποιημενα): ποντοι/40 · «υπολοιπα» = (PIR − ποντοι)/40 · +/-/40. Χ = Σ λεπτα/40 × g(k) × z (φιλ − γηπ).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): χαρακτηριστικο ΜΕΤΡΑΕΙ αν (α) LOSO: η προσθηκη του στη βαση βελτιωνει RMSE σε ≥4/5 σεζον ΚΑΙ (β) εκτιμημενο
  ΧΩΡΙΣΤΑ σε καθε σεζον εχει το ιδιο προσημο σε ≥4/5. Αναφορα: ομαδες απουσιων «καθαρος σκορερ» (ποντοι/40 πανω απο 75%, υπολοιπα κατω απο 50%)
  vs «παικτης για ολα» (υπολοιπα πανω απο 75%) — μεσο υπολοιπο r απο τη μερια της ομαδας που λειπει (− = εχασε ΠΕΡΙΣΣΟΤΕΡΑ απο οσα λενε τα λεπτα).
Εξοδος: el_absence_scorer_out.txt"""
import sys, io, contextlib
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
G_ = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_player_absence_value.py', encoding='utf-8').read().split("P(''); P('## ΟΛΑ ΤΑ ΔΕΔΟΜΕΝΑ")[0], G_)
sys.stdout.reconfigure(encoding='utf-8')
rows, SE, Y, ys, feats, fit, rmse = (G_[k] for k in ('rows', 'SE', 'Y', 'ys', 'feats', 'fit', 'rmse'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
GAM = .5
# ---- βαση: μονο λεπτα (LOSO) ----
use0 = np.array([1, 0, 0, 0]); base = np.zeros(len(Y))
for Yr in SE:
    b, X = fit(GAM, use0, [s for s in SE if s != Yr]); m = ys == Yr; base[m] = (X @ b)[m]
r = Y - base
P(f'βαση «μονο λεπτα» LOSO: RMSE {rmse(Y, np.ones(len(Y), bool)):.3f} → {rmse(r, np.ones(len(Y), bool)):.3f}')
# ---- χαρακτηριστικα ----
allp = [p for q in rows for p in q['ah'] + q['aa']]
for p in allp: p['oth'] = p['pir'] - p['pts']
MU = {f: np.mean([p[f] for p in allp]) for f in ('pts', 'oth', 'pm')}; SD = {f: np.std([p[f] for p in allp]) for f in ('pts', 'oth', 'pm')}
def xf(q, f):
    x = 0.0
    for lst, s in ((q['aa'], 1), (q['ah'], -1)):
        for p in lst:
            g = 1.0 if p['k'] <= 3 else (GAM if p['k'] <= 10 else 0.0)
            x += s * p['min'] / 40 * g * (p[f] - MU[f]) / SD[f]
    return x
NM = {'pts': 'ποντοι/40', 'oth': 'υπολοιπα (PIR − ποντοι)/40', 'pm': '+/-/40'}
P(''); P('## ΚΑΘΕ ΧΑΡΑΚΤΗΡΙΣΤΙΚΟ ΧΩΡΙΣΤΑ ΠΑΝΩ ΣΤΗ ΒΑΣΗ (συντελεστης = ποντοι ανα 40′ απουσιας ανα 1 τυπ. αποκλιση· + = ο απων με περισσοτερο απο αυτο ΚΟΣΤΙΖΕΙ ΠΕΡΙΣΣΟΤΕΡΟ)')
for f in ('pts', 'oth', 'pm'):
    x = np.array([xf(q, f) for q in rows])
    per = {s: float(np.polyfit(x[ys == s], r[ys == s], 1)[0]) for s in SE}
    allb = float(np.polyfit(x, r, 1)[0])
    held = np.zeros(len(Y))
    for Yr in SE:
        tr = ys != Yr; bb = np.polyfit(x[tr], r[tr], 1); held[ys == Yr] = np.polyval(bb, x[ys == Yr])
    d = [rmse(r - held, ys == s) - rmse(r, ys == s) for s in SE]
    same = sum(1 for v in per.values() if np.sign(v) == np.sign(allb))
    ok = sum(v < 0 for v in d) >= 4 and same >= 4
    P(f'  {NM[f]:28s} συντελεστης ολα {allb:+.2f} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{v:+.2f}' for s, v in per.items()) + f' (ιδιο προσημο {same}/5)'
      + f' · LOSO ' + ' '.join(f'{v:+.3f}' for v in d) + f' → {sum(v < 0 for v in d)}/5' + ('  <- ΜΕΤΡΑΕΙ' if ok else '  ✗'))
# ---- τυποι παικτων ----
P(''); P('## ΤΥΠΟΙ ΑΠΟΝΤΩΝ (ματς οπου απο τη μια πλευρα λειπει ακριβως ενας τετοιος ≥20′ και απο την αλλη τιποτα): μεσο υπολοιπο απο τη μερια της ομαδας που λειπει')
q75 = {f: np.percentile([p[f] for p in allp], 75) for f in ('pts', 'oth')}; q50 = {f: np.percentile([p[f] for p in allp], 50) for f in ('pts', 'oth')}
def typ(p):
    if p['pts'] >= q75['pts'] and p['oth'] < q50['oth']: return 'καθαρος σκορερ'
    if p['oth'] >= q75['oth']: return 'παικτης για ολα'
    return 'αλλος'
G = {'καθαρος σκορερ': [], 'παικτης για ολα': [], 'αλλος': []}
for q, rr, y in zip(rows, r, ys):
    for lst, other, s in ((q['ah'], q['aa'], 1), (q['aa'], q['ah'], -1)):
        big = [p for p in lst if p['min'] >= 20]
        if len(big) == 1 and not other and big[0]['k'] <= 3: G[typ(big[0])].append((rr * s, y))
for t, L in G.items():
    if not L: continue
    a = np.array([v for v, _ in L]); t_ = a.mean() / (a.std() / np.sqrt(len(a))) if len(a) > 2 else 0
    P(f'  {t:16s} n {len(a):4d} · υπολοιπο {a.mean():+.2f} π. (t {t_:+.1f}) · ανα σεζον ' + ' '.join(f'{s[-2:]}:{np.mean([v for v, y in L if y == s]):+.1f}' for s in SE if any(y == s for _, y in L)))
P('  (+ = η ομαδα που ελειπε ο παικτης πηγε ΚΑΛΥΤΕΡΑ απο οσα λενε τα λεπτα → αξιζε λιγοτερο· − = ΧΕΙΡΟΤΕΡΑ → αξιζε περισσοτερο)')
open('el_absence_scorer_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
