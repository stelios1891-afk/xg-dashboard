# -*- coding: utf-8 -*-
"""t110_totals_late_moves.py — ΣΥΝΟΛΑ: ΑΡΓΑ PICKS ΑΝΑ ΜΠΛΟΚ ΩΡΩΝ / ΑΠΟΥΣΙΑ / ΚΙΝΗΣΗ ΑΓΟΡΑΣ (26/10/2026, Στελιος «χαντικαπ μονο ανοιγμα
και τιποτα αλλο, παμε και στα συνολα»). Ιδιος ορισμος με t108 + t109 (χαντικαπ). ΠΕΡΙΓΡΑΦΙΚΟ.
ΜΟΝΤΕΛΟ στη στιγμη τ = LIVE μηχανη συνολων (eng απο _t104_totals_live.csv: νεα μηχανη + Φ3) − 0.5·LO(τ) + 1.0·LD(τ), LO/LD απο τους Out ρολου
  (≥20′) της ΕΠΙΣΗΜΗΣ αναφορας με ωρα ≤ τ (οπως live). Γραμμη = συνολο Crown που ισχυε στο τ (καθε αλλαγη με ωρα). σ 18 · κατωφλι 8% ολη τη σεζον.
ΣΤΙΓΜΕΣ τ: Τ−36…−0.5ω (16, οπως t108). ΑΡΓΟ pick = πρωτη στιγμη που μια πλευρα (Over/Under) φτανει 8% ενω ΔΕΝ ηταν pick στο ανοιγμα.
  Α = τα αφηνει ο κανονας 1ης γραμμης (τωρινο μοντελο στην 1η γραμμη ≥8%) · Β = τα κοβει.
ΑΠΟΥΣΙΑ (εκτος «καθαρων») αν απο το ανοιγμα ως το τ: αλλαξε η λιστα Out ρολου στην αναφορα (οποιαδηποτε ομαδα) Ή ειδηση NBC «εκτος»/«παιζει»
  για παικτη ρολου (t50). ΚΙΝΗΣΗ = ποσους ποντους πηγε το δικαιο συνολο της αγορας απο το ανοιγμα ως το τ ΚΟΝΤΡΑ στην πλευρα μας
  (Over: πτωση, Under: ανοδος): <1 · 1-2 · 2-3 · ≥3π. Σεναριο 3 = edge ανοιγματος 7-8% / 6-7% με κινηση <1π.
ΚΡΙΤΗΡΙΟ (t101/t107/t109): «σαν τα picks ανοιγματος» μονο αν ROI > 0, ≥4/5 σεζον, CLV > 0, n ≥ 80.
Εξοδος: t110_totals_late_moves_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# ειδησεις NBC (t50) + αναφορες (t22) — μεσα απο το t108
src = open(os.path.join(SC, 't108_late_picks_hours_news.py'), encoding='utf-8').read().split('recs = []; n_open = 0')[0]
gg = {'__file__': os.path.join(SC, 't108_late_picks_hours_news.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, gg)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = gg['np'], gg['pd']; NBYG, HS, block = gg['NBYG'], gg['HS'], gg['block']
g22 = gg['g']; status_at, K2P, mins, SER, SHIFT, G, dD = (g22[k] for k in ('status_at', 'K2P', 'mins', 'SER', 'SHIFT', 'G', 'dD'))
odval = gg['g5']['odval']
from statistics import NormalDist
ND = NormalDist(); SIG = 18.0; THR = .08
def cover(mu, T):
    if abs(T - round(T)) < 1e-9:
        po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
    po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
def fair(x):
    oo, ou = 1 + x[2], 1 + x[3]; po = (1 / oo) / (1 / oo + 1 / ou); return float(x[1]) + SIG * ND.inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
def at(rows, ts):
    pre = [x for x in rows if x[0] <= ts]; return pre[-1] if pre else None
def outs(t, d, s, tau):
    res = {}
    for k, stt in status_at(t, d, tau).items():
        if stt != 'Out': continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        o_, d_ = odval(pid, s - 1); res[k] = ((o_ + 0.5) * m / 48, (d_ + 0.5) * m / 48)
    return res
def mu_at(eng, h, a, d, s, tau):
    L = {**{('h', k): v for k, v in outs(h, d, s, tau).items()}, **{('a', k): v for k, v in outs(a, d, s, tau).items()}}
    return eng - 0.5 * sum(v[0] for v in L.values()) + 1.0 * sum(v[1] for v in L.values()), frozenset(L)
def edges(mu, x):
    po, pp, pu = cover(mu, float(x[1])); return {1: po * (1 + x[2]) + pp - 1, -1: pu * (1 + x[3]) + pp - 1}
T4 = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv'))
GI = {(str(dD[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
recs, opn, miss = [], [], 0
for r in T4.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home, r.away))
    if i is None or i not in SER: miss += 1; continue
    sw, tip, r21, r23 = SER[i]
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: miss += 1; continue
    s, d, h, a = int(r.sea), dD[i], r.home, r.away; t0 = rows[0][0]; x0 = rows[0]; xc = rows[-1]
    mu0, set0 = mu_at(r.eng, h, a, d, s, t0); E0 = edges(mu0, x0); f0, fc = fair(x0), fair(xc)
    for sd in (1, -1):
        if E0[sd] >= THR:
            od = 1 + (x0[2] if sd == 1 else x0[3]); y = (r.tot - float(x0[1])) * sd
            opn.append(dict(sea=s, sd=sd, res=(od - 1) if y > 0 else (0.0 if y == 0 else -1.0), clv=sd * (fc - f0)))
    seen = set()
    for hrs in HS:
        tau = tip - hrs * 3600
        if tau <= t0: continue
        x = at(rows, tau); mu, st = mu_at(r.eng, h, a, d, s, tau)
        E = edges(mu, x); ER = edges(mu, x0); ft = fair(x)
        for sd in (1, -1):
            if E[sd] < THR or E0[sd] >= THR or sd in seen: continue
            seen.add(sd)
            od = 1 + (x[2] if sd == 1 else x[3]); y = (r.tot - float(x[1])) * sd
            nw = [z for z in NBYG.get(i, pd.DataFrame()).itertuples(index=False) if t0 < z.t0 <= tau] if i in NBYG else []
            rep = st != set0
            recs.append(dict(i=i, sea=s, mon=int(r.mon), sd=sd, hrs=hrs, bl=block(hrs), e=E[sd], e0=E0[sd], er=ER[sd], cut=ER[sd] < THR,
                             rep=rep, news=len(nw) > 0, clean=(not rep) and not nw, move=sd * (f0 - ft), dmu=mu - mu0,
                             res=(od - 1) if y > 0 else (0.0 if y == 0 else -1.0), clv=sd * (fc - ft)))
X = pd.DataFrame(recs); O = pd.DataFrame(opn); X['g0'] = X.e0 - THR
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum()); ok = d.res.mean() > 0 and pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}, CLV {d.clv.mean():+.2f}π)' + (' ✓' if ok else '')
P(f't110 · ΣΥΝΟΛΑ NBA · αργα picks · Crown · 5 σεζον · ματς {len(T4) - miss} (χωρις αντιστοιχιση {miss}) · κελι = ROI (picks, μοναδες, θετ. σεζον, CLV ποντοι συνολου) · ✓ = κριτηριο')
P(f'\nΣΕΝΑΡΙΟ 1 · picks ανοιγματος: {cell(O)} · Over {cell(O[O.sd == 1])} · Under {cell(O[O.sd == -1])}   (ελεγχος t104: +5.7%, 2505)')
C = X[X.clean]
P(f'\nΟΛΑ αργα {cell(X)} · Α (τα αφηνει ο κανονας) {cell(X[~X.cut])} · Β (τα κοβει) {cell(X[X.cut])}')
P(f'  με απουσια (αναφορα {int(X.rep.sum())} / μονο ειδηση {int((X.news & ~X.rep).sum())}) {cell(X[~X.clean])}')
P(f'  ΚΑΘΑΡΑ ({len(C)}, {100 * len(C) / len(X):.0f}%) {cell(C)} · Over {cell(C[C.sd == 1])} · Under {cell(C[C.sd == -1])}')
P('\n(1) ΑΝΑ ΜΠΛΟΚ ΩΡΩΝ (ολα / καθαρα):')
for b in ('>12ω', '12-6ω', '6-3ω', '3-1ω', 'τελ. ωρα'):
    P(f'  {b:9s} ολα {cell(X[X.bl == b])} · καθαρα {cell(C[C.bl == b])}')
MV = (('<1π', -99, 1), ('1-2π', 1, 2), ('2-3π', 2, 3), ('≥3π', 3, 99))
P('\n(2) ΚΑΘΑΡΑ ανα κινηση αγορας κοντρα μας (δικαιο συνολο, ποντοι):')
for nm, lo, hi in MV:
    d = C[(C.move >= lo) & (C.move < hi)]; P(f'  κινηση {nm:5s} {cell(d)} · μεση κινηση {d.move.mean():+.2f}π')
P('\n  ΣΕΝΑΡΙΟ 3 (οριακα, κινηση <1π):')
for nm, lo, hi in (('edge ανοιγματος 7-8%', -.01, 0), ('6-7%', -.02, -.01), ('6-8% μαζι', -.02, 0)):
    P(f'    {nm:22s} {cell(C[(C.move < 1) & (C.g0 >= lo) & (C.g0 < hi)])}')
P(f'  ΣΕΝΑΡΙΟ 2 (κοντρα στα λεφτα ≥2π): {cell(C[C.move >= 2])}')
P('\nΠΙΝΑΚΑΣ · ΚΑΘΑΡΑ · edge ανοιγματος × κινηση:')
for en, elo, ehi in (('7-8%', -.01, 0), ('6-7%', -.02, -.01), ('4-6%', -.04, -.02), ('<4%', -9, -.04)):
    P(f'  edge ανοιγ. {en:5s}: ' + ' · '.join(f'{mn} {cell(C[(C.g0 >= elo) & (C.g0 < ehi) & (C.move >= mlo) & (C.move < mhi)])}' for mn, mlo, mhi in MV))
P('\nελεγχος (2 παραδειγματα: σεναριο 3 και μεγαλη κινηση):')
for lab, d in (('Σ3', C[(C.move < 1) & (C.g0 >= -.01)]), ('Σ2', C[C.move >= 2])):
    for _, q in d.head(2).iterrows():
        j = int(q.i); P(f'   {lab}: {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · {"Over" if q.sd == 1 else "Under"} · Τ−{q.hrs}ω · edge ανοιγ. {100 * q.e0:.1f}% → {100 * q.e:.1f}% · κινηση {q.move:+.2f}π · μοντελο Δ {q.dmu:+.2f}π · αποτ {q.res:+.2f}')
X.to_csv(os.path.join(SC, '_t110_picks.csv'), index=False)
open(os.path.join(SC, 't110_totals_late_moves_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
