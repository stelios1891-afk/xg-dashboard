# -*- coding: utf-8 -*-
"""ec_totals_venue_test.py — EuroCup ΣΥΝΟΛΑ: ΕΔΡΑ «ΨΗΛΩΝ/ΧΑΜΗΛΩΝ ΣΥΝΟΛΩΝ» ως ΣΚΙΑ (5/10/2026, Στελιος «τρεξε το τεστ»).
Επιδραση εδρας γηπεδουχου v = Σ(πραγματικο − μοντελο live) στα ΕΝΤΟΣ ΕΔΡΑΣ ματς του στις ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον / (n + 15).
1. Λιστα: μεγαλυτερες/μικροτερες v (ολες οι σεζον ως U2025) — ποιες ομαδες παιζουν φετος (U2026).
2. ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): picks του live κανονα (αγων 1-6 μιξη, 7+ μοντελο μονο, ≥6%, ανοιγμα Crown U2020-25) χωρισμενα σε
   «η εδρα ΣΥΜΦΩΝΕΙ» (v ≥ +1 για over / v ≤ −1 για under) · «ΔΙΑΦΩΝΕΙ» · «ουδετερη» → η σκια αξιζει αν ΣΥΜΦΩΝΕΙ − ΔΙΑΦΩΝΕΙ > 0 σε ≥4/6 σεζον.
3. ΠΡΟ-ΔΗΛΩΜΕΝΟ: κανονας ΜΟΝΟ εδρας (χωρις μοντελο): over αν v ≥ +X, under αν v ≤ −X (X {1, 1.5, 2, 3}), ανοιγμα → θετικο σε ≥4/6 σεζον.
Εξοδος: ec_totals_venue_out.txt"""
import sys, json, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
NS = {'__name__': 'v'}
exec(open('ec_totals_deep_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_totals_deep_out.txt', 'w', encoding='utf-8')", "open('_unused_deep.txt', 'w', encoding='utf-8')"), NS)
D, FIN, TOT, GN, MKT, cov, EVM = (NS[k] for k in ('D', 'FIN', 'TOT', 'GN', 'MKT', 'cov', 'EVM'))
seasn = np.asarray(NS['seasn'])
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
R = TOT - FIN; SY = np.array([int(s[1:]) for s in seasn]); HOME = D.home.values
def veff(code, Y):
    m = (HOME == code) & (SY < Y) & np.isfinite(R); n = m.sum()
    return (R[m].sum() / (n + 15), int(n)) if n else (0.0, 0)
V = np.array([veff(HOME[i], SY[i])[0] for i in range(len(D))])
# ---- 1. λιστα ----
names = {}
for i in range(len(D)): names[HOME[i]] = D.hname.values[i]
cur = set()
try:
    S = json.load(open('ec_sched.json', encoding='utf-8'))
    for x in S.get('U2026', []): cur.add(x['hcode']); names[x['hcode']] = x['home']
except Exception: pass
allv = {c: veff(c, 2026) for c in set(HOME) | cur}
P('################ 1. ΕΠΙΔΡΑΣΗ ΕΔΡΑΣ (ολες οι σεζον ως 2025-26) ################')
rows = sorted([(v, n, c) for c, (v, n) in allv.items() if n >= 8], reverse=True)
P('  ΨΗΛΑ συνολα στην εδρα τους:')
for v, n, c in rows[:10]: P(f'    {names.get(c, c)[:30]:30s} {v:+.1f} π. ({n} εντος) {"← ΦΕΤΟΣ" if c in cur else ""}')
P('  ΧΑΜΗΛΑ συνολα στην εδρα τους:')
for v, n, c in rows[-10:][::-1]: P(f'    {names.get(c, c)[:30]:30s} {v:+.1f} π. ({n} εντος) {"← ΦΕΤΟΣ" if c in cur else ""}')
P('  ΦΕΤΙΝΕΣ ομαδες (U2026): ' + ' · '.join(f'{names.get(c, c)[:18]} {allv[c][0]:+.1f} ({allv[c][1]})' for c in sorted(cur, key=lambda c: -allv[c][0]) if allv[c][1] > 0)
  + f' · χωρις ιστορικο εντος: {sum(1 for c in cur if allv[c][1] == 0)}/{len(cur)}')
# ---- 2. live picks × εδρα ----
P(''); P('################ 2. LIVE PICKS: ΣΥΜΦΩΝΕΙ / ΔΙΑΦΩΝΕΙ Η ΕΔΡΑ ################')
def live_pick(i):
    T, mk, oo, ou = MKT[i]['o']; w = .5 if GN[i] <= 5 else 1.0
    po, pq, pu = cov(mk + w * (FIN[i] - mk), T, 16.7); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
    if max(eo, eu) < .06: return None
    ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
    return (od - 1) if q > 0 else (0 if q == 0 else -1), ov
G = collections.defaultdict(list)
for i in MKT:
    if seasn[i] not in EVM or not np.isfinite(FIN[i]): continue
    p = live_pick(i)
    if not p: continue
    u, ov = p; v = V[i]
    grp = 'ΣΥΜΦΩΝΕΙ' if (ov and v >= 1) or (not ov and v <= -1) else ('ΔΙΑΦΩΝΕΙ' if (ov and v <= -1) or (not ov and v >= 1) else 'ουδετερη')
    G[grp].append((u, seasn[i]))
per = {}
for g, L in G.items():
    a = np.array([x[0] for x in L]); per[g] = {Y: np.mean([x[0] for x in L if x[1] == Y]) for Y in EVM if any(x[1] == Y for x in L)}
    P(f'  {g:9s} n {len(a):4d} · ROI {a.mean()*100:+.1f}% · {a.sum():+.1f}u · ανα σεζον ' + ' '.join(f'{Y[-2:]}:{v*100:+.0f}' for Y, v in per[g].items()))
both = [Y for Y in EVM if Y in per.get('ΣΥΜΦΩΝΕΙ', {}) and Y in per.get('ΔΙΑΦΩΝΕΙ', {})]
nb = sum(per['ΣΥΜΦΩΝΕΙ'][Y] > per['ΔΙΑΦΩΝΕΙ'][Y] for Y in both)
P(f'  → ΠΡΟ-ΔΗΛΩΜΕΝΟ: ΣΥΜΦΩΝΕΙ > ΔΙΑΦΩΝΕΙ σε {nb}/{len(both)} σεζον → ' + ('η σκια ΑΞΙΖΕΙ' if nb >= 4 else 'η σκια ΔΕΝ αποδεικνυεται'))
# ---- 3. κανονας μονο εδρας ----
P(''); P('################ 3. ΚΑΝΟΝΑΣ ΜΟΝΟ ΕΔΡΑΣ (χωρις μοντελο, ανοιγμα) ################')
for X in (1, 1.5, 2, 3):
    L = []
    for i in MKT:
        if seasn[i] not in EVM or abs(V[i]) < X: continue
        T, mk, oo, ou = MKT[i]['o']; ov = V[i] > 0; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
        L.append(((od - 1) if q > 0 else (0 if q == 0 else -1), seasn[i], ov))
    if not L: continue
    a = np.array([x[0] for x in L]); ps = {Y: np.mean([x[0] for x in L if x[1] == Y]) for Y in EVM if any(x[1] == Y for x in L)}
    no = sum(1 for x in L if x[2]); pos = sum(v > 0 for v in ps.values())
    P(f'  |v| ≥ {X}: n {len(a):4d} (over {no}/under {len(a) - no}) · ROI {a.mean()*100:+.1f}% · {a.sum():+.1f}u · θετ. {pos}/{len(ps)} · ' + ' '.join(f'{Y[-2:]}:{v*100:+.0f}' for Y, v in ps.items())
      + ('  ✓' if pos >= 4 else '  ✗'))
open('ec_totals_venue_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
