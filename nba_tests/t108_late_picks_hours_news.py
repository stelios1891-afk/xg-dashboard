# -*- coding: utf-8 -*-
"""t108_late_picks_hours_news.py — ΑΡΓΑ PICKS ΧΑΝΤΙΚΑΠ ΑΝΑ ΜΠΛΟΚ ΩΡΩΝ + ΕΛΕΓΧΟΣ «ΤΟ ΜΟΝΤΕΛΟ ΗΞΕΡΕ ΤΗΝ ΕΙΔΗΣΗ;» (26/10/2026, Στελιος:
«μετρα και την ωρα τους, μπετς που δεν προεκυψαν στο ανοιγμα αλλα μετα, σε μπλοκ ωρων» · «θα καταλαβει το μοντελο οτι 5 ωρες πριν βγηκε
μια απουσια και κουνησε τη γραμμη;»). ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει τιποτα.
Πλαισιο t101/t22: live αντιγραφο + απουσιες απο την ΕΠΙΣΗΜΗ αναφορα NBA με ωρα ≤ τ (11 στιγμιοτυπα/μερα: 8π,11π,1μ,3μ,5μ-11μ ωρα ΗΠΑ ET)
· γραμμη Crown που ισχυε στο τ · κατωφλι 8% (Ιαν-Φεβ 12%) · 5 σεζον.
ΣΤΙΓΜΕΣ τ: Τ−36,−30,−24,−20,−16,−12,−10,−8,−6,−5,−4,−3,−2,−1.5,−1,−0.5 ωρες (μονο μετα το ανοιγμα). ΑΡΓΟ pick = πρωτη στιγμη που μια πλευρα
φτανει το κατωφλι ενω ΔΕΝ ηταν pick στο ανοιγμα. Ομαδες t101: Α (τα αφηνει ο κανονας 1ης γραμμης) · Β1 (κοβει, μονο τιμη) · Β2 (κοβει, τιμη+απουσιες αναφορας).
ΜΠΛΟΚ: >12ω · 12-6ω · 6-3ω · 3-1ω · τελευταια ωρα.
ΕΙΔΗΣΗ ΠΟΥ Η ΑΝΑΦΟΡΑ ΔΕΝ ΕΙΧΕ ΑΚΟΜΑ (NBC 5 σεζον, ορισμοι t50: «εκτος»/«παιζει», ωρα tweet αν υπαρχει, παικτης ρολου ≥20′): υπαρχει ειδηση για
το ματς με ωρα ≤ τ, και η επισημη αναφορα του τ ΔΕΝ την εχει ακομα (εκτος → οχι Out · παιζει → ακομα Out/Doubtful/Questionable).
  «κοντρα» = η ειδηση ευνοει την ΑΛΛΗ πλευρα (= η αγορα κινηθηκε, το μοντελο δεν το ξερει → ψευτικο edge).
Εξοδος: t108_late_picks_hours_news_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't50_news_5s.py'), encoding='utf-8').read().split('D = pd.DataFrame(N)')[0]
src = src.replace('N.append(dict(i=i, S=S,', 'N.append(dict(k=k, i=i, S=S,')
assert 'N.append(dict(k=k,' in src
g5 = {'__file__': os.path.join(SC, 't50_news_5s.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g5)
sys.stdout.reconfigure(encoding='utf-8')
g = g5['g']['g']; np, pd = g5['np'], g5['pd']
SER, SHIFT, G, dD, SEAS_G, EV, VNO, ACT = (g[k] for k in ('SER', 'SHIFT', 'G', 'dD', 'SEAS_G', 'EV', 'VNO', 'ACT'))
abs_cost, W, line_at, cover_, SIG_, REP_SEASONS, status_at = g['abs_cost'], g['W_B'], g['line_at'], g['cover_'], g['SIG_'], g['REP_SEASONS'], g['status_at']
NW = pd.DataFrame(g5['N']); NBYG = {i: d for i, d in NW.groupby('i')}
def edges(m, ln):
    pw, pp, pl = cover_(m, ln[0], SIG_); return {1: pw * ln[1] + pp - 1, -1: pl * ln[2] + pp - 1}
HS = (36, 30, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1.5, 1, 0.5)
def block(h): return '>12ω' if h > 12 else ('12-6ω' if h > 6 else ('6-3ω' if h > 3 else ('3-1ω' if h > 1 else 'τελ. ωρα')))
BL = ('>12ω', '12-6ω', '6-3ω', '3-1ω', 'τελ. ωρα')
def unknown_news(i, tau, sd):
    """(υπαρχει αγνωστη στην αναφορα ειδηση ≤τ, υπαρχει ΚΟΝΤΡΑ στο pick)"""
    d = NBYG.get(i)
    if d is None: return False, False
    any_, contra = False, False
    for r in d.itertuples(index=False):
        if r.t0 > tau: continue
        st = status_at(r.team, dD[i], tau).get(r.k)
        if (r.kind == 'out' and st == 'Out') or (r.kind == 'in' and st not in ('Out', 'Doubtful', 'Questionable')): continue
        any_ = True
        fav_home = (-r.hc) if r.home else r.hc                 # hc>0 = κακο για την ομαδα της ειδησης
        if sd * fav_home < 0: contra = True
    return any_, contra
recs = []; n_open = 0
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    mon = int(G.date.dt.month.values[i]); thr = .12 if mon in (1, 2) else .08
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]
    close = line_at(rows, tip, sw); ln0 = line_at(rows, t0, sw)
    ab0 = -abs_cost(h, d, s, t0, W)[0] + abs_cost(a, d, s, t0, W)[0]
    E0 = edges(VNO[i] + ab0, ln0); n_open += sum(E0[k] >= thr for k in E0)
    seen = set()
    for hrs in HS:
        tau = tip - hrs * 3600
        if tau <= t0: continue
        ln = line_at(rows, tau, sw)
        abt = -abs_cost(h, d, s, tau, W)[0] + abs_cost(a, d, s, tau, W)[0]; m = VNO[i] + abt
        E = edges(m, ln); ER = edges(m, ln0)
        for sd in (1, -1):
            if E[sd] < thr or E0[sd] >= thr or sd in seen: continue
            seen.add(sd)
            od = ln[1] if sd == 1 else ln[2]; x = (ACT[i] + ln[0]) * sd
            grp = 'Α' if ER[sd] >= thr else ('Β2' if abs(abt - ab0) >= 0.3 else 'Β1')
            un, co = unknown_news(i, tau, sd)
            recs.append(dict(i=i, sea=s, mon=mon, hrs=hrs, bl=block(hrs), grp=grp, news=un, contra=co,
                             res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0), clv=sd * (close[3] - ln[3]), e=E[sd], er=ER[sd], thr=thr))
X = pd.DataFrame(recs); out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum())
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}, CLV {d.clv.mean():+.2f}π)'
P(f't108 · ΑΡΓΑ PICKS ΧΑΝΤΙΚΑΠ NBA · Crown · 5 σεζον · picks ανοιγματος (για μετρο) {n_open} · αργα {len(X)}')
P('κελι = ROI στην τιμη της στιγμης (picks, μοναδες, θετικες σεζον, CLV = κινηση γραμμης ως το κλεισιμο προς εμας σε ποντους)')
P('\n(1) ΑΝΑ ΜΠΛΟΚ ΩΡΩΝ ΠΡΙΝ ΤΟ ΤΖΑΜΠΟΛ (πρωτη στιγμη που εγινε pick):')
for b in BL:
    d = X[X.bl == b]; P(f'  {b:9s} ολα {cell(d)}')
    P(f'  {"":9s}   Α (τα αφηνει ο κανονας) {cell(d[d.grp == "Α"])}')
    P(f'  {"":9s}   Β1 μονο τιμη {cell(d[d.grp == "Β1"])} · Β2 τιμη+αναφορα {cell(d[d.grp == "Β2"])}')
P(f'  ΟΛΑ      ολα {cell(X)} · Α {cell(X[X.grp == "Α"])} · Β1 {cell(X[X.grp == "Β1"])} · Β2 {cell(X[X.grp == "Β2"])}')
P('\n(2) ΗΞΕΡΕ ΤΟ ΜΟΝΤΕΛΟ ΤΗΝ ΕΙΔΗΣΗ; (ειδηση NBC ≤ τ που η επισημη αναφορα του τ δεν εχει ακομα)')
for k in ('Α', 'Β1', 'Β2'):
    d = X[X.grp == k]
    P(f'  {k:2s}: με αγνωστη ειδηση {100 * d.news.mean():4.1f}% (κοντρα στο pick {100 * d.contra.mean():4.1f}%)')
    P(f'      χωρις αγνωστη ειδηση («καθαρα») {cell(d[~d.news])}')
    P(f'      με αγνωστη ειδηση ΚΟΝΤΡΑ στο pick {cell(d[d.contra])}')
    P(f'      με αγνωστη ειδηση υπερ / ουδετερη {cell(d[d.news & ~d.contra])}')
P('\n(3) ΚΑΘΑΡΑ (χωρις αγνωστη ειδηση) ΑΝΑ ΜΠΛΟΚ:')
C = X[~X.news]
for b in BL:
    d = C[C.bl == b]; P(f'  {b:9s} Α {cell(d[d.grp == "Α"])} · Β (κοβει) {cell(d[d.grp != "Α"])}')
P('\n(4) ΣΧΕΔΟΝ PICKS (τωρινο μοντελο στην 1η γραμμη κατωφλι−1…0%, οπως Μπακς), Β, ανα μπλοκ — ολα / καθαρα:')
NM = X[(X.grp != 'Α') & (X.er - X.thr >= -.01)]
for b in BL: P(f'  {b:9s} ολα {cell(NM[NM.bl == b])} · καθαρα {cell(NM[(NM.bl == b) & ~NM.news])}')
P(f'  ΟΛΑ      ολα {cell(NM)} · καθαρα {cell(NM[~NM.news])}')
P('\nελεγχος: 2 αργα picks με ειδηση κοντρα:')
for _, r in X[X.contra].head(2).iterrows():
    j = int(r.i)
    P(f'   {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · Τ−{r.hrs}ω · {r.grp} · edge {100 * r.e:.1f}% · ειδησεις ματς: '
      + ' | '.join(f'{x.k} {x.kind} ({x.team}, Τ−{x.hrs:.1f}ω, αξια {x.hc:+.1f})' for x in NBYG[j].itertuples()) + f' · αποτ {r.res:+.2f}')
X.to_csv(os.path.join(SC, '_t108_picks.csv'), index=False)
open(os.path.join(SC, 't108_late_picks_hours_news_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
