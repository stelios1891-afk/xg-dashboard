# -*- coding: utf-8 -*-
"""t17_trade_minutes.py — ΜΕΤΑΓΡΑΦΕΣ: ΤΑ ΛΕΠΤΑ ΣΤΗ ΝΕΑ ΟΜΑΔΑ (20/10/2026, Στελιος: «ερευνησε αυτο» — υποθεση: η φορμουλα θεωρει οτι ο
παικτης παιζει στη νεα ομαδα οσα στην παλια· για σταρ ισχυει, για ρολιστες οχι → γι αυτο οι μεσαιες αλλαγες χανουν).
Βαση: t15 (γεγονοτα μετακινησης, βαση live, διορθωση = 0.75·0.75·(αξια+2)·λεπτα/48 ±, χωρις σβησιμο).
1) ΠΕΡΙΓΡΑΦΙΚΟ: λεπτα/ματς στα 10 πρωτα με τη ΝΕΑ ομαδα vs 10 τελευταια με την παλια, ανα ρολο (λεπτα) και αξια.
2) ΜΕ ΤΑ ΠΡΑΓΜΑΤΙΚΑ νεα λεπτα (εκ των υστερων = ταβανι): αλλαζουν τα picks στις μεσαιες αλλαγες;
3) ΕΚΤΙΜΗΣΗ νεων λεπτων ΧΩΡΙΣ ματια στο μελλον: απο παλια λεπτα + θεση αξιας στη ροταρισμα της νεας ομαδας (γραμμικη, LOSO ανα σεζον).
Ιδια ομαδοποιηση picks με t15 (Η): κομμενα / νεα ανα μεγεθος μετακινησης. Εξοδος: t17_trade_minutes_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE = ns['BASE']
EVTS, TG, A2, value, MKH, rm, roi_od, ALL, FA, PLAYED = (ns[k] for k in ('EVTS', 'TG', 'A2', 'value', 'MKH', 'rm', 'roi_od', 'ALL', 'FA', 'PLAYED'))
inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---------- λεπτα πριν/μετα για καθε εισερχομενο ----------
PG = collections.defaultdict(list)                       # (pid, s) → [(d, team, min)]
for r in A2.itertuples(index=False): PG[(r.pid, int(r.s))].append((np.datetime64(r.d, 'D'), r.team, r.MIN))
for k in PG: PG[k].sort()
TEAMG = collections.defaultdict(list)                    # (s, team) → [(d, {pid: min})]
for (t, s_, d), x in A2.groupby(['team', 's', 'd']): TEAMG[(int(s_), t)].append((np.datetime64(d, 'D'), dict(zip(x.pid, x.MIN))))
for k in TEAMG: TEAMG[k].sort(key=lambda z: z[0])
INC = []                                                 # εισερχομενοι: dict
for s_, t, tau, p, sgn, mm in EVTS:
    if sgn < 0: continue
    games = PG.get((p, s_), [])
    new = [m for d, tt, m in games if tt == t and d >= tau][:10]
    # θεση αξιας στη ροταρισμα της νεας ομαδας (10 τελευταια ματς πριν το τ)
    prev = [z for z in TEAMG.get((s_, t), []) if z[0] < tau][-10:]
    rot = collections.Counter()
    for _, dct in prev:
        for q, m in dct.items(): rot[q] += m / max(len(prev), 1)
    rot = {q: m for q, m in rot.items() if m >= 10}
    v = value(p, s_ - 1); rank = 1 + sum(1 for q in rot if value(q, s_ - 1) > v)
    INC.append(dict(s=s_, t=t, tau=tau, p=p, old=mm, new=float(np.mean(new)) if len(new) >= 3 else np.nan, v=v, rank=rank, nrot=len(rot)))
import pandas as pd
D = pd.DataFrame(INC)
P(f'NBA · ΜΕΤΑΓΡΑΦΕΣ: ΛΕΠΤΑ ΣΤΗ ΝΕΑ ΟΜΑΔΑ · {len(D)} εισερχομενοι παικτες (με ≥3 ματς στη νεα ομαδα: {D.new.notna().sum()})')
P(''); P('=== 1. ΛΕΠΤΑ/ΜΑΤΣ: 10 τελευταια με την παλια → 10 πρωτα με τη νεα ===')
Dn = D[D.new.notna()]
for lab, m in (('σταρ (παλια ≥30′)', Dn.old >= 30), ('βασικοι 24-30′', (Dn.old >= 24) & (Dn.old < 30)), ('ρολιστες 15-24′', (Dn.old >= 15) & (Dn.old < 24)),
               ('παγκος <15′', Dn.old < 15)):
    d = Dn[m]
    if not len(d): continue
    err = (d.new - d.old)
    P(f'  {lab:22s} n {len(d):3d} · παλια {d.old.mean():5.1f}′ → νεα {d.new.mean():5.1f}′ · μεση αλλαγη {err.mean():+5.1f}′ · '
      f'τυπικη αποκλιση {err.std():4.1f}′ · |λαθος| {err.abs().mean():4.1f}′')
P('  ανα θεση αξιας στη νεα ομαδα (1 = ο καλυτερος της ροταρισμα):')
for lo, hi, lab in ((1, 2, '1ος-2ος'), (3, 5, '3ος-5ος'), (6, 8, '6ος-8ος'), (9, 99, '9ος+')):
    d = Dn[(Dn['rank'] >= lo) & (Dn['rank'] <= hi)]
    if len(d): P(f'    {lab:8s} n {len(d):3d} · παλια {d.old.mean():5.1f}′ → νεα {d.new.mean():5.1f}′ ({(d.new - d.old).mean():+5.1f}′)')
# ---------- 3) εκτιμηση νεων λεπτων: new ≈ a + b·old + c·rank (LOSO) ----------
D['hat'] = np.nan
for Y in EV:
    tr = Dn[Dn.s != Y]
    X = np.c_[np.ones(len(tr)), tr.old, np.minimum(tr['rank'], 12)]; c, *_ = np.linalg.lstsq(X, tr.new.values, rcond=None)
    m = D.s == Y; D.loc[m, 'hat'] = np.clip(c[0] + c[1] * D.loc[m, 'old'] + c[2] * np.minimum(D.loc[m, 'rank'], 12), 0, 38)
X = np.c_[np.ones(len(Dn)), Dn.old, np.minimum(Dn['rank'], 12)]; cAll, *_ = np.linalg.lstsq(X, Dn.new.values, rcond=None)
P(f'  εκτιμηση (ολα): νεα λεπτα ≈ {cAll[0]:.1f} + {cAll[1]:.2f}·παλια {cAll[2]:+.2f}·θεση · |λαθος| εκτιμησης {np.nanmean(np.abs(D.hat - D.new)):.1f}′ (vs «ιδια με πριν» {np.nanmean(np.abs(D.old - D.new)):.1f}′)')
MAP = {(r.s, r.t, r.tau, r.p): r for r in D.itertuples(index=False)}
# ---------- διορθωση με διαφορετικα λεπτα ----------
GLIST = collections.defaultdict(list)                    # i → [(side, sgn, v, (old, new, hat), n)]
for e in EVTS:
    s_, t, tau, p, sgn, mm = e; n = 0
    r = MAP.get((s_, t, tau, p)) if sgn > 0 else None
    for i in TG.get((s_, t), []):
        if dD[i] < tau: continue
        n += 1; side = 1 if G.home.values[i] == t else -1
        if sgn > 0 and (p, t, dD[i]) not in PLAYED: continue      # 20/10: ιδιο με το διορθωμενο t15 (εισερχομενος μονο οταν παιζει)
        GLIST[i].append((side, sgn, value(p, s_ - 1), mm, (r.new if (r is not None and r.new == r.new) else mm), (r.hat if (r is not None and r.hat == r.hat) else mm)))
def adj(kind):
    X = np.zeros(len(G))
    for i, lst in GLIST.items():
        for side, sgn, v, mo, mn, mh in lst:
            m = {'old': mo, 'new': mn, 'hat': mh}[kind]
            X[i] += side * sgn * 0.75 * 0.75 * (v + 2.0) * m / 48
    return X
def pick(v, i):
    L, mk, o1, o2 = MKH[i]['o']; pw, pp, pl = cover_(v[i], L, SIG_)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    x = (ACT[i] + L) * s_; return s_, ((od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0))
M = np.zeros(len(G), bool); M[list(GLIST)] = True; M &= np.isin(SEAS_G, EV)
P(''); P('=== 2-3. ΔΙΟΡΘΩΣΗ με «ιδια λεπτα με πριν» (t15) / ΠΡΑΓΜΑΤΙΚΑ νεα λεπτα (εκ των υστερων) / ΕΚΤΙΜΗΣΗ (χωρις ματια στο μελλον) ===')
P('  μονο ματς μετα απο μεταγραφη · λαθος = RMSE · καθαρα = μοναδες νεων picks − μοναδες κομμενων, ανα μεγεθος μετακινησης')
for kind, lab in (('old', 'ιδια λεπτα (t15)'), ('new', 'ΠΡΑΓΜΑΤΙΚΑ νεα λεπτα'), ('hat', 'ΕΚΤΙΜΗΣΗ νεων λεπτων')):
    Xk = adj(kind); V1 = BASE + Xk
    bet = sum(rm(V1, [Y], M) < rm(BASE, [Y], M) - 1e-6 for Y in EV)
    line = f'  {lab:22s} λαθος {rm(BASE, EV, M):.3f} → {rm(V1, EV, M):.3f} ({bet}/5) ·'
    tot = 0.0
    for lo, hi, bl in ((0, .5, '<0.5'), (.5, 1.5, '0.5-1.5'), (1.5, 99, '≥1.5')):
        cut = add = 0.0; nc = na = 0
        for i in np.where(M)[0]:
            if i not in MKH or not np.isfinite(BASE[i]) or not (lo <= abs(Xk[i]) < hi): continue
            a, b = pick(BASE, i), pick(V1, i)
            if a and not b: cut += a[1]; nc += 1
            elif b and not a: add += b[1]; na += 1
            elif a and b and a[0] != b[0]: cut += a[1]; add += b[1]; nc += 1; na += 1
        tot += add - cut
        line += f' {bl}: {add - cut:+5.1f}μ (−{nc}/+{na})'
    n2, r2, u2, _, _ = roi_od(V1, msk=M); n0, r0, u0, _, _ = roi_od(BASE, msk=M)
    P(line + f' · ΣΥΝΟΛΟ {tot:+.1f}μ · picks σε αυτα τα ματς {r0:+.1f}% → {r2:+.1f}%')
open(os.path.join(SC, 't17_trade_minutes_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
