# -*- coding: utf-8 -*-
"""t109_clean_late_moves.py — ΑΡΓΑ PICKS ΧΑΝΤΙΚΑΠ ΧΩΡΙΣ ΑΠΟΥΣΙΑ: ΟΡΙΑΚΑ ΜΕ ΜΙΚΡΗ ΚΙΝΗΣΗ vs ΚΟΝΤΡΑ ΣΕ ΜΕΓΑΛΗ ΚΙΝΗΣΗ (26/10/2026, Στελιος
«στα οριακα edges ισως μπαινουν μεσα και πικς απο το 2ο γκρουπ και χαλανε τα νουμερα» · ορισμος εγκριθηκε «ναι»). ΠΕΡΙΓΡΑΦΙΚΟ.
Πλαισιο t108 (live αντιγραφο + επισημη αναφορα της στιγμης, Crown, 5 σεζον, 16 στιγμες Τ−36…−0.5ω, κατωφλι 8% · Ιαν-Φεβ 12%).
ΒΗΜΑ 1 — ΕΚΤΟΣ («με απουσια») αν απο το ανοιγμα ως τη στιγμη του pick: η επισημη αναφορα αλλαξε την προβλεψη ≥0.3π, Ή υπαρχει ειδηση NBC
  «εκτος»/«παιζει» για παικτη ρολου (≥20′) οποιασδηποτε ομαδας (ορισμοι t50, ωρα tweet). Τα υπολοιπα = «ΚΑΘΑΡΗ ΚΙΝΗΣΗ ΑΓΟΡΑΣ».
ΒΗΜΑ 2 — καθαρα ανα ΚΙΝΗΣΗ = ποσους ποντους πηγε η δικαιη γραμμη της αγορας απο το ανοιγμα ως τη στιγμη, ΚΟΝΤΡΑ στην πλευρα μας:
  <1π (Σεναριο 3 αν edge ανοιγματος 7-8% / 6-7%) · 1-2π (ενδιαμεσο) · ≥2π (Σεναριο 2 «κοντρα στα λεφτα»). Σεναριο 1 = picks ανοιγματος (μετρο).
  Πινακας edge ανοιγματος (κατωφλι−1…0 · −2…−1 · −4…−2 · <−4) × κινηση.
ΚΡΙΤΗΡΙΟ (t101/t107): σεναριο «σαν τα picks ανοιγματος» μονο αν ROI > 0, ≥4/5 σεζον, CLV > 0, n ≥ 80.
Εξοδος: t109_clean_late_moves_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't108_late_picks_hours_news.py'), encoding='utf-8').read().split('recs = []; n_open = 0')[0]
gg = {'__file__': os.path.join(SC, 't108_late_picks_hours_news.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, gg)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = gg['np'], gg['pd']
SER, SHIFT, G, dD, SEAS_G, EV, VNO, ACT = (gg[k] for k in ('SER', 'SHIFT', 'G', 'dD', 'SEAS_G', 'EV', 'VNO', 'ACT'))
abs_cost, W, line_at, edges, REP_SEASONS, NBYG, HS, block = (gg[k] for k in ('abs_cost', 'W', 'line_at', 'edges', 'REP_SEASONS', 'NBYG', 'HS', 'block'))
def news_between(i, ta, tb):
    d = NBYG.get(i)
    if d is None: return []
    return [r for r in d.itertuples(index=False) if ta < r.t0 <= tb]
recs = []; opn = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    mon = int(G.date.dt.month.values[i]); thr = .12 if mon in (1, 2) else .08
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]
    close = line_at(rows, tip, sw); ln0 = line_at(rows, t0, sw)
    ab0 = -abs_cost(h, d, s, t0, W)[0] + abs_cost(a, d, s, t0, W)[0]
    E0 = edges(VNO[i] + ab0, ln0)
    for sd in (1, -1):
        if E0[sd] >= thr:
            od = ln0[1] if sd == 1 else ln0[2]; x = (ACT[i] + ln0[0]) * sd
            opn.append(dict(sea=s, res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0), clv=sd * (close[3] - ln0[3])))
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
            nw = news_between(i, t0, tau); rep = abs(abt - ab0) >= 0.3
            recs.append(dict(i=i, sea=s, mon=mon, hrs=hrs, bl=block(hrs), thr=thr, e=E[sd], e0=E0[sd], er=ER[sd], rule_cut=ER[sd] < thr,
                             rep=rep, news=len(nw) > 0, clean=not rep and not nw, move=sd * (ln0[3] - ln[3]), dline=sd * (ln0[0] - ln[0]),
                             res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0), clv=sd * (close[3] - ln[3])))
X = pd.DataFrame(recs); O = pd.DataFrame(opn); X['g0'] = X.e0 - X.thr
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum()); ok = d.res.mean() > 0 and pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}, CLV {d.clv.mean():+.2f}π)' + (' ✓' if ok else '')
C = X[X.clean]
P('t109 · ΑΡΓΑ PICKS ΧΑΝΤΙΚΑΠ NBA ΧΩΡΙΣ ΑΠΟΥΣΙΑ · Crown · 5 σεζον · κελι = ROI στην τιμη της στιγμης (picks, μοναδες, θετικες σεζον, CLV ποντοι) · ✓ = κριτηριο')
P(f'\nΣΕΝΑΡΙΟ 1 · picks ανοιγματος: {cell(O)}')
P(f'\nΒΗΜΑ 1 · αργα picks {len(X)}: με αλλαγη αναφορας {int(X.rep.sum())} · με ειδηση NBC (χωρις αλλαγη αναφορας) {int((X.news & ~X.rep).sum())} · ΚΑΘΑΡΑ {len(C)} ({100 * len(C) / len(X):.0f}%)')
P(f'  ολα αργα {cell(X)}')
P(f'  με απουσια (αναφορα ή ειδηση) {cell(X[~X.clean])}')
P(f'  ΚΑΘΑΡΑ {cell(C)}')
MV = (('<1π', -99, 1), ('1-2π', 1, 2), ('≥2π', 2, 99))
P('\nΒΗΜΑ 2 · ΚΑΘΑΡΑ ανα κινηση της αγορας κοντρα μας (δικαιη γραμμη, ποντοι, ανοιγμα → στιγμη του pick):')
for nm, lo, hi in MV:
    d = C[(C.move >= lo) & (C.move < hi)]
    P(f'  κινηση {nm:5s} {cell(d)} · μεση κινηση {d.move.mean():+.2f}π · αλλαγη γραμμης {d.dline.mean():+.2f}π')
P('\n  ΣΕΝΑΡΙΟ 3 (οριακα, κινηση <1π):')
for nm, lo, hi in (('edge ανοιγματος κατωφλι−1…0 (7-8%)', -.01, 0), ('κατωφλι−2…−1 (6-7%)', -.02, -.01), ('7-8% ΚΑΙ 6-7% μαζι', -.02, 0)):
    P(f'    {nm:36s} {cell(C[(C.move < 1) & (C.g0 >= lo) & (C.g0 < hi)])}')
P(f'  ΣΕΝΑΡΙΟ 2 (κοντρα στα λεφτα, κινηση ≥2π): {cell(C[C.move >= 2])}')
P('\nΠΙΝΑΚΑΣ · ΚΑΘΑΡΑ · edge ανοιγματος × κινηση:')
EB = (('7-8%', -.01, 0), ('6-7%', -.02, -.01), ('4-6%', -.04, -.02), ('<4%', -9, -.04))
for en, elo, ehi in EB:
    P(f'  edge ανοιγ. {en:5s}: ' + ' · '.join(f'{mn} {cell(C[(C.g0 >= elo) & (C.g0 < ehi) & (C.move >= mlo) & (C.move < mhi)])}' for mn, mlo, mhi in MV))
P('\nΚΑΘΑΡΑ ανα μπλοκ ωρων × κινηση (<1π / ≥1π):')
for b in ('>12ω', '12-6ω', '6-3ω', '3-1ω', 'τελ. ωρα'):
    d = C[C.bl == b]; P(f'  {b:9s} <1π {cell(d[d.move < 1])} · ≥1π {cell(d[d.move >= 1])}')
P('\nΚΑΘΑΡΑ σεναριο 3 (<1π, 6-8%) ανα σεζον: ' + ' · '.join(f'{s}: {d.res.sum():+.1f}μ ({len(d)})' for s, d in C[(C.move < 1) & (C.g0 >= -.02)].groupby('sea')))
P('\nελεγχος (2 παραδειγματα σεναριου 3 και 2):')
for lab, d in (('Σ3', C[(C.move < 1) & (C.g0 >= -.01)]), ('Σ2', C[C.move >= 2])):
    for _, r in d.head(2).iterrows():
        j = int(r.i); P(f'   {lab}: {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · Τ−{r.hrs}ω · edge ανοιγ. {100 * r.e0:.1f}% → {100 * r.e:.1f}% · κινηση {r.move:+.2f}π (γραμμη {r.dline:+.1f}) · αποτ {r.res:+.2f}')
X.to_csv(os.path.join(SC, '_t109_picks.csv'), index=False)
open(os.path.join(SC, 't109_clean_late_moves_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
