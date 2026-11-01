# -*- coding: utf-8 -*-
"""t111_totals_big_clv_middle.py — ΣΥΝΟΛΑ NBA: ΜΕΓΑΛΗ ΚΙΝΗΣΗ ΥΠΕΡ ΜΑΣ ΩΣ ΤΟ ΚΛΕΙΣΙΜΟ & «MIDDLE» ΣΤΟ ΚΛΕΙΣΙΜΟ (27/10/2026, Στελιος: αφορμη
MIA-DAL Over 233.5 → 240.5 και CHA-WAS Under 232.5 → 226.0 · «ποσα συνολα ειχαν κινηση 3π, 4π, 5π, 6π… τι ποσοστο, πως απεδωσαν· οταν
υπαρχει τοσο μεγαλο drop μηπως middle στο κλεισιμο ειναι πιο profitable — παιζουμε το αντιθετο στη γραμμη κλεισιματος»). ΠΕΡΙΓΡΑΦΙΚΟ.
Crown (Nowgoal, καθε αλλαγη με ωρα) · 5 σεζον 2021-22 … 2025-26 · LIVE μηχανη συνολων στο ανοιγμα (ιδια με t104/t110: 2505 picks ≥8%).
ΚΙΝΗΣΗ = γραμμη κλεισιματος − γραμμη ανοιγματος σε ΠΟΝΤΟΥΣ ΓΡΑΜΜΗΣ, προς ΤΗΝ ΠΛΕΥΡΑ ΜΑΣ (Over: ανεβηκε · Under: κατεβηκε).
Κατηγοριες: ≤0 · 0-1 · 1-2 · 2-3 · 3-4 · 4-5 · 5-6 · ≥6.
ΓΙΑ ΚΑΘΕ pick: Α = μονο το αρχικο (ανοιγμα) · Β = μονο το ΑΝΤΙΘΕΤΟ στη γραμμη & τιμη κλεισιματος · Α+Β = και τα δυο (2 μοναδες)
  · middle = κερδιζουν ΚΑΙ τα δυο (συνολο αναμεσα στις 2 γραμμες).
ΣΥΓΚΡΙΣΗ (ολα τα ματς, οχι μονο δικα μας): ποσοστο ματς με |κινηση| ≥3/4/5/6 · «κοντρα στην κινηση στο κλεισιμο» (παιζω την πλευρα
  που η αγορα εγκαταλειψε, στη γραμμη κλεισιματος) ανα κατηγορια.
Εξοδος: t111_totals_big_clv_middle_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't110_totals_late_moves.py'), encoding='utf-8').read().split('recs, opn, miss = [], [], 0')[0]
gg = {'__file__': os.path.join(SC, 't110_totals_late_moves.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, gg)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = gg['np'], gg['pd']; T4, GI, SER, SHIFT, dD, G = gg['T4'], gg['GI'], gg['SER'], gg['SHIFT'], gg['dD'], gg['G']
mu_at, edges, THR = gg['mu_at'], gg['edges'], gg['THR']
def res1(tot, T, sd, od):
    y = (tot - T) * sd; return (od - 1) if y > 0 else (0.0 if y == 0 else -1.0)
PK, AL = [], []
for r in T4.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home, r.away))
    if i is None or i not in SER: continue
    sw, tip, r21, r23 = SER[i]
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    x0, xc = rows[0], rows[-1]; T0, Tc = float(x0[1]), float(xc[1]); s = int(r.sea)
    mv = Tc - T0
    # ολα τα ματς: κοντρα στην κινηση στο κλεισιμο (αν κινηθηκε προς τα πανω → Under στο κλεισιμο)
    if mv != 0:
        sdf = -1 if mv > 0 else 1; odf = 1 + (xc[3] if sdf == -1 else xc[2])
        AL.append(dict(sea=s, am=abs(mv), res=res1(r.tot, Tc, sdf, odf)))
    else: AL.append(dict(sea=s, am=0.0, res=np.nan))
    mu0, _ = mu_at(r.eng, r.home, r.away, dD[i], s, x0[0]); E0 = edges(mu0, x0)
    for sd in (1, -1):
        if E0[sd] < THR: continue
        odA = 1 + (x0[2] if sd == 1 else x0[3]); odB = 1 + (xc[3] if sd == 1 else xc[2])
        a = res1(r.tot, T0, sd, odA); b = res1(r.tot, Tc, -sd, odB)
        PK.append(dict(i=i, sea=s, sd=sd, T0=T0, Tc=Tc, mv=sd * mv, tot=r.tot, a=a, b=b, ab=a + b, mid=(a > 0) and (b > 0), odA=odA, odB=odB))
X = pd.DataFrame(PK); A = pd.DataFrame(AL)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
CAT = (('≤0 (κοντρα ή ιδια)', -99, 0.001), ('0-1', 0.001, 1), ('1-2', 1, 2), ('2-3', 2, 3), ('3-4', 3, 4), ('4-5', 4, 5), ('5-6', 5, 6), ('≥6', 6, 99))
def roi(v, d, k=1):
    v = d[v]; ps = d.groupby('sea')[v.name].sum(); return f'{100 * v.mean() / k:+6.1f}% ({v.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()})'
P(f't111 · ΣΥΝΟΛΑ NBA · Crown · 5 σεζον · picks ανοιγματος ≥8%: {len(X)} · ολα τα ματς με γραμμη: {len(A)}')
P('ΚΙΝΗΣΗ = γραμμη κλεισιματος − ανοιγματος σε ποντους, προς την πλευρα μας (+ = η αγορα ηρθε προς εμας)')
P('\n(1) ΔΙΚΑ ΜΑΣ PICKS ανα κινηση:  picks (% των picks) · Α αρχικο · Β αντιθετο στο κλεισιμο · Α+Β (ROI ανα 2 μοναδες) · middle %')
for nm, lo, hi in CAT:
    d = X[(X.mv >= lo) & (X.mv < hi)]
    if not len(d): P(f'  {nm:20s} —'); continue
    P(f'  {nm:20s} {len(d):5d} ({100 * len(d) / len(X):4.1f}%) · Α {roi("a", d)} · Β {roi("b", d)} · Α+Β {roi("ab", d, 2)} · middle {100 * d.mid.mean():4.1f}%')
for nm, lo in (('≥3', 3), ('≥4', 4), ('≥5', 5), ('≥6', 6)):
    d = X[X.mv >= lo]
    P(f'  ΣΩΡΕΥΤΙΚΑ {nm:5s}      {len(d):5d} ({100 * len(d) / len(X):4.1f}%) · Α {roi("a", d)} · Β {roi("b", d)} · Α+Β {roi("ab", d, 2)} · middle {100 * d.mid.mean():4.1f}%')
P(f'  ΟΛΑ                 {len(X):5d}          · Α {roi("a", X)} · Β {roi("b", X)} · Α+Β {roi("ab", X, 2)} · middle {100 * X.mid.mean():4.1f}%')
P('\n  Στα ≥3: Α+Β ανα σεζον (μοναδες): ' + ' · '.join(f'{s}: Α {d.a.sum():+.1f} / Α+Β {d.ab.sum():+.1f} ({len(d)})' for s, d in X[X.mv >= 3].groupby('sea')))
P('\n(2) ΟΛΑ ΤΑ ΜΑΤΣ: ποσο συχνα κινειται τοσο η γραμμη (απολυτη κινηση ανοιγμα→κλεισιμο, οποια φορα) · «κοντρα στην κινηση στο κλεισιμο»')
for nm, lo, hi in (('0', -1, 0.001), ('0-1', 0.001, 1), ('1-2', 1, 2), ('2-3', 2, 3), ('3-4', 3, 4), ('4-5', 4, 5), ('5-6', 5, 6), ('≥6', 6, 99)):
    d = A[(A.am >= lo) & (A.am < hi)]; dd = d.dropna(subset=['res'])
    P(f'  {nm:5s} {len(d):5d} ματς ({100 * len(d) / len(A):4.1f}%)' + (f' · κοντρα στο κλεισιμο {roi("res", dd)}' if len(dd) else ''))
for nm, lo in (('≥3', 3), ('≥4', 4), ('≥5', 5), ('≥6', 6)):
    d = A[A.am >= lo].dropna(subset=['res']); P(f'  ΣΩΡΕΥΤΙΚΑ {nm:4s} {len(d):5d} ({100 * len(d) / len(A):4.1f}%) · κοντρα στο κλεισιμο {roi("res", d)}')
P('\nελεγχος (2 picks με κινηση ≥6):')
for _, q in X[X.mv >= 6].head(2).iterrows():
    j = int(q.i); P(f'   {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · {"Over" if q.sd == 1 else "Under"} {q.T0:g} @{q.odA:.2f} → κλεισιμο {q.Tc:g} · αντιθετο @{q.odB:.2f} · συνολο {q.tot:g} · Α {q.a:+.2f} Β {q.b:+.2f} middle {q.mid}')
X.to_csv(os.path.join(SC, '_t111_picks.csv'), index=False)
open(os.path.join(SC, 't111_totals_big_clv_middle_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
