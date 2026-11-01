# -*- coding: utf-8 -*-
"""t33_dynamic_start.py — ΔΥΝΑΜΙΚΗ ΑΦΕΤΗΡΙΑ (21/10/2026, Στελιος: «αν η αφετηρια ξεκιναει με μια απουσια 1-2 ματς … δεν θα εμφανιζεται
η ομαδα πιο αδυναμη απ οτι ειναι οταν γυρισει ο παικτης;»).
ΣΗΜΕΡΑ (live «W1»): η αφετηρια της σεζον = αξια των παικτων που επαιξαν στο 1ο ματς (βαρη = περσινα λεπτα/ματς, αγνωστοι −1/15′)· οποιος
ελειψε απο το 1ο ματς μενει ΕΚΤΟΣ αφετηριας ολη τη σεζον (βαρος αφετηριας ≈ 8/(8+ματς)).
ΔΥΝΑΜΙΚΗ: παικτης που ΔΕΝ επαιξε στο 1ο ματς της ομαδας, εχει αξια (περσι/προπερσι) και δεν ηρθε με μεταγραφη μεσα στη σεζον (δεν επαιξε για
αλλη ομαδα φετος πριν), απο το 1ο ματς που παιζει και μετα: διαφορα = [αξια(ρόστερ 1ου ματς + αυτος) − αξια(ρόστερ 1ου ματς)] × 8/(8 + ματς ομαδας πριν).
ΕΚΔΟΧΕΣ (γραφτηκαν πριν το τρεξιμο): Α = ολοι οι παραπανω · Β = μονο οσοι γυρισαν μεσα στα ματς 2-20 της ομαδας (μικρες απουσιες) ·
  Γ = οπως Α χωρις το σβησιμο 8/(8+n) (ανω οριο: πληρες βαρος, ελεγχος λογικης).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: LOSO (επιλογη με RMSE στις αλλες 4 απο {σημερα, Α, Β}) · ΠΕΡΝΑ αν RMSE καλυτερο σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% ολης οχι χειροτερο
  (> −1.5pp) ΚΑΙ Οκτ-Δεκ οχι χειροτερο (> −1.5pp). Περιγραφικο: λαθος (πραγματικο − προβλεψη) απο την πλευρα της ομαδας που «γυρισε» παικτη.
Εξοδος: t33_dynamic_start_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE0 = ns['BASE']
TG, value, rm, roi_od, ALL, MKH, A = ns['TG'], ns['value'], ns['rm'], ns['roi_od'], ns['ALL'], ns['MKH'], ns['A']
NSR = ns['ns']['NS']; MPT, GPT = NSR['MPT'], NSR['GPT']
BASE = BASE0 + ns['adj'](1.0, -2.0, None)                                    # live: + μεταγραφες
A2 = A[A.MIN > 0][['pid', 'team', 's', 'd', 'MIN']].copy(); A2['dd'] = A2.d.values.astype('datetime64[D]'); A2['s'] = A2.s.astype(int)
first_team = {}                                                               # (pid, s) → πρωτη ομαδα φετος
for r in A2.sort_values('dd').itertuples(index=False):
    first_team.setdefault((r.pid, r.s), r.team)
def wv(p, s):
    w = MPT[(p, s - 1)] / GPT[(p, s - 1)] if (p, s - 1) in MPT and GPT.get((p, s - 1)) else 15.0
    return w, value(p, s - 1)
def tv(lst):
    if not lst: return 0.0
    tot = sum(w for w, _ in lst); return sum(5 * w / tot * v for w, v in lst)
RET = collections.defaultdict(list)                                           # i → [(side, Δ, n_before)]
nret = collections.Counter()
for (t, s), g in A2.groupby(['team', 's']):
    if s not in EV: continue
    idx = TG.get((s, t), [])
    if not idx: continue
    d1 = dD[idx[0]]
    g1 = set(g[g.dd == d1].pid)
    if not g1: continue
    base_lst = [wv(p, s) for p in g1]; v0 = tv(base_lst)
    firstplay = g.groupby('pid').dd.min()
    for p, fd in firstplay.items():
        if p in g1 or first_team.get((p, s)) != t: continue                  # επαιξε στο 1ο · ή ηρθε απο αλλη ομαδα (μεταγραφη)
        if value(p, s - 1) == -1.0 and (p, s - 1) not in MPT: continue         # χωρις αξια (rookie/αγνωστος)
        dlt = tv(base_lst + [wv(p, s)]) - v0
        n_ret = sum(1 for i in idx if dD[i] < fd)                              # ματς της ομαδας πριν γυρισει
        nret['≤20' if n_ret <= 19 else '>20'] += 1
        for k, i in enumerate(idx):
            if dD[i] < fd: continue
            side = 1 if G.home.values[i] == t else -1
            RET[i].append((side, dlt, k, n_ret))                              # k = ματς ομαδας πριν απο αυτο
def mk(var):
    X = np.zeros(len(G))
    for i, lst in RET.items():
        for side, dlt, k, n_ret in lst:
            if var == 'Β' and n_ret > 19: continue
            w = 1.0 if var == 'Γ' else 8.0 / (8.0 + k)
            X[i] += side * dlt * w
    return X
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'NBA · ΔΥΝΑΜΙΚΗ ΑΦΕΤΗΡΙΑ · βαση = live (W1 + μεταγραφες) · επιστροφες παικτων που ελειψαν απο το 1ο ματς: {dict(nret)} · ματς που επηρεαζονται {len(RET)}')
base_s = {Y: rm(BASE, [Y]) for Y in EV}
_, rb_all, _, _, _ = roi_od(BASE, msk=ALL); _, rb_od, _, _, _ = roi_od(BASE)
AFF = np.zeros(len(G), bool); AFF[list(RET)] = True
VV = {'σημερα': BASE}
for v in ('Α', 'Β', 'Γ'): VV[v] = BASE + mk(v)
P(f'{"εκδοχη":10s} | RMSE ολα | καλ. | RMSE επηρ. | ROI ολη ≥8%           | ROI Οκτ-Δεκ ≥8%')
def line(lab, v):
    n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); n1, r1, u1, ps1, _ = roi_od(v)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    P(f'{lab:10s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, AFF):9.4f} | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5 | {r1:+6.1f}% ({n1:4d}) {sum(ps1[Y] > 0 for Y in EV)}/5')
    return r2, r1
for k, v in VV.items(): line(k, v)
pk = {Y: min(('σημερα', 'Α', 'Β'), key=lambda k: rm(VV[k], [x for x in EV if x != Y])) for Y in EV}
vL = BASE.copy()
for Y in EV: m = SEAS_G == Y; vL[m] = VV[pk[Y]][m]
P(''); P(f'LOSO επιλογες: {pk}')
r2, r1 = line('LOSO', vL)
c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = r2 - rb_all > -1.5; c3 = r1 - rb_od > -1.5
P(f'ΚΡΙΤΗΡΙΑ: RMSE ≥4/5 {"✓" if c1 else "✗"} · ολη {r2 - rb_all:+.1f}pp {"✓" if c2 else "✗"} · Οκτ-Δεκ {r1 - rb_od:+.1f}pp {"✓" if c3 else "✗"} → {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('  ανα σεζον RMSE σημερα/Α/Β: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(VV["Α"], [Y]):.4f}/{rm(VV["Β"], [Y]):.4f}' for Y in EV))
# περιγραφικο: απο την πλευρα της ομαδας που γυρισε παικτη (μονο ματς με |Δ| ≥ 0.3)
P(''); P('=== ΠΕΡΙΓΡΑΦΙΚΟ: ομαδα που «γυρισε» παικτη (Δ ≥ 0.3 π.) — λαθος (πραγματικο − προβλεψη) ===')
XA = mk('Α')
for lab, lo, hi in (('ματς 2-10', 1, 9), ('ματς 11-30', 10, 29), ('ματς 31+', 30, 99)):
    eb, ea = [], []
    for i, lst in RET.items():
        if SEAS_G[i] not in EV or not np.isfinite(BASE[i]): continue
        k = min(x[2] for x in lst); x = XA[i]
        if abs(x) < 0.3 or not (lo <= k <= hi): continue
        sg = np.sign(x); eb.append(sg * (ACT[i] - BASE[i])); ea.append(sg * (ACT[i] - VV['Α'][i]))
    if eb: P(f'  {lab:10s} n {len(eb):4d} · σημερα {np.mean(eb):+5.2f}±{np.std(eb) / np.sqrt(len(eb)):.2f} · δυναμικη Α {np.mean(ea):+5.2f}')
# ελεγχος παραδειγματος: μεγαλυτερες επιστροφες
P(''); P('=== ΕΛΕΓΧΟΣ: οι 5 μεγαλυτερες επιστροφες (Δ) ===')
names = dict(zip(A.pid, A.PLAYER_NAME)) if 'PLAYER_NAME' in A else {}
big = []
for (t, s), g in A2.groupby(['team', 's']):
    pass
rows = []
for i, lst in RET.items():
    for side, dlt, k, n_ret in lst:
        if k == n_ret: rows.append((dlt, SEAS_G[i], G.home.values[i] if side == 1 else G.away.values[i], str(dD[i]), n_ret))
for dlt, s, t, d, n_ret in sorted(rows, reverse=True)[:5]:
    P(f'  {s} {t} · γυρισε {d} μετα απο {n_ret} ματς · Δ αφετηριας {dlt:+.2f} π. (× 8/(8+{n_ret}) = {dlt * 8 / (8 + n_ret):+.2f})')
open(os.path.join(SC, 't33_dynamic_start_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
