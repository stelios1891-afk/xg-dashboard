# -*- coding: utf-8 -*-
"""t15_trades.py — ΜΕΤΑΓΡΑΦΕΣ ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ (20/10/2026, Στελιος: «οι μεταγραφες προφανως πρεπει να λογιζονται — αν παιρνουν τη δυναμικη
απο την προηγουμενη ομαδα κτλπ — ειναι παρα πολυ σημαντικο»).
ΣΗΜΕΡΑ (live & ολα τα τεστ): καμια προσαρμογη — η ομαδα αλλαζει μονο σιγα σιγα μεσα απο τα αποτελεσματα· ο παικτης που φευγει απλως
βγαινει απο τις απουσιες, ο καινουργιος δεν προσθετει τιποτα.
ΓΕΓΟΝΟΣ = παικτης που παιζει για ≥2 ομαδες στην ιδια σεζον (box score). Ημερα γνωσης τ = πρωτο ματς με τη νεα ομαδα − 2 μερες
(οχι πριν απο την επομενη του τελευταιου ματς με την παλια). Απο τ και μετα, σε ΚΑΘΕ ομαδα:
  ΔΙΟΡΘΩΣΗ = α · Σ ±0.75·(αξια − ΑΝΤΙΚ)·λεπτα/48   (+ για οσους ηρθαν, − για οσους εφυγαν)
  λεπτα = μ.ο. 10 τελευταιων με την παλια ομαδα φετος (≥5 ματς), αλλιως περσινα/ματς, αλλιως 15 · αξια = περσινη (οπως οι απουσιες).
  ΣΒΗΣΙΜΟ: η μηχανη μαθαινει απο τα αποτελεσματα μετα τη μεταγραφη → βαρος k/(k+n), n = ματς της ομαδας απο τ (k = ∞ / 32 / 16 / 8).
Πλεγμα: α {0.5, 0.75, 1.0} × ΑΝΤΙΚ {−2, −1, 0} × k {∞, 32, 16, 8}. ΒΑΣΗ = live (production + B2B 3 + απουσιες αντικ. −2, K=2).
(Α) ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο της ΒΑΣΗΣ και της αγορας ανοιγματος απο την πλευρα της ομαδας που ΕΝΙΣΧΥΘΗΚΕ, ανα ματς μετα τη μεταγραφη.
(Β) ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο, ιδιο με t11 + Φεβ-Απρ): LOSO επιλογη με RMSE στις αλλες 4 → περνα αν RMSE καλυτερο απο τη
  ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος ≥8% ολης οχι χειροτερο (> −1.5pp) ΚΑΙ Φεβ-Απρ οχι χειροτερο (> −1.5pp). Εξοδος: t15_trades_out.txt"""
import os, sys, io, contextlib, collections, itertools
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'absence_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; MG = ns['MG']; A = ns['A']; ACT = ns['ACT']
rm, roi_od, ALL, value, MKH = ns['rm'], ns['roi_od'], ns['ALL'], ns['value'], ns['MKH']
MPT, GPT = None, None
# ---------- βαση live (αντικ. −2) ----------
ns['REP'] = -2.0
LH = np.zeros(len(G)); LA = np.zeros(len(G))
for i in range(len(G)):
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    LH[i], _ = ns['team_loss'](h, d, 2); LA[i], _ = ns['team_loss'](a, d, 2)
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
BASE = MG + 3.0 * (B2A - B2H) + 0.75 * (LH - LA)
MON = G.date.dt.month.values; FA = np.isin(MON, [2, 3, 4])
# ---------- γεγονοτα μεταγραφης ----------
A2 = A[A.MIN > 0][['pid', 'team', 's', 'd', 'MIN']].sort_values('d')
prev_mpg = {}
for (p, s), g in A2.groupby(['pid', 's']): prev_mpg[(p, int(s))] = float(g.MIN.mean())
EVTS = []                                                   # (s, team, tau, pid, sign, minutes)
for (p, s), g in A2.groupby(['pid', 's']):
    s = int(s); teams = g.team.values; ds = g.d.values; mins = g.MIN.values
    for j in range(1, len(g)):
        if teams[j] == teams[j - 1]: continue
        t0, t1 = teams[j - 1], teams[j]
        old = [(dd, mm) for dd, mm, tt in zip(ds[:j], mins[:j], teams[:j]) if tt == t0]
        mm = float(np.mean([x[1] for x in old[-10:]])) if len(old) >= 5 else (prev_mpg.get((p, s - 1)) or 15.0)
        tau = max(np.datetime64(ds[j], 'D') - np.timedelta64(2, 'D'), np.datetime64(ds[j - 1], 'D') + np.timedelta64(1, 'D'))
        EVTS.append((s, t0, tau, p, -1, min(mm, 36.0))); EVTS.append((s, t1, tau, p, +1, min(mm, 36.0)))
EVTS = [e for e in EVTS if e[0] in EV]
# αριθμος ματς της ομαδας απο τ
TG = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'):
    TG[(SEAS_G[i], G.home.values[i])].append(i); TG[(SEAS_G[i], G.away.values[i])].append(i)
GIDX = collections.defaultdict(list)                        # i → [(sg, evt, n)]
for e in EVTS:
    s, t, tau, p, sgn, mm = e; n = 0
    for i in TG.get((s, t), []):
        if dD[i] < tau: continue
        n += 1; side = 1 if G.home.values[i] == t else -1
        GIDX[i].append((side, sgn, value(p, s - 1), mm, n))
def adj(alpha, rep, k):
    X = np.zeros(len(G))
    for i, lst in GIDX.items():
        for side, sgn, v, mm, n in lst:
            w = 1.0 if k is None else k / (k + n - 1)
            X[i] += side * sgn * alpha * 0.75 * (v - rep) * mm / 48 * w
    return X
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
nev = len({(e[0], e[3], e[2]) for e in EVTS})
P(f'NBA · ΜΕΤΑΓΡΑΦΕΣ ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ · 5 σεζον · {nev} μετακινησεις παικτων · ματς που επηρεαζονται {len(GIDX)}')
# ---------- (Α) περιγραφικο ----------
MKO = np.full(len(G), np.nan)
for i, dct in MKH.items(): MKO[i] = dct['o'][1]
X0 = adj(1.0, -2.0, None)
P(''); P('=== (Α) ΠΕΡΙΓΡΑΦΙΚΟ: απο την πλευρα της ομαδας που ΕΝΙΣΧΥΘΗΚΕ καθαρα (+ = επαιξε καλυτερα απο την προβλεψη) ===')
P('    «αλλαγη» = καθαρη ενισχυση σε δικους μας ποντους (α 1, αντικ. −2, χωρις σβησιμο)')
rows = collections.defaultdict(list)
for i, lst in GIDX.items():
    if not np.isfinite(BASE[i]) or SEAS_G[i] not in EV: continue
    n = min(x[4] for x in lst); x = X0[i]
    if abs(x) < 0.5: continue
    sg = np.sign(x); bk = '1-5' if n <= 5 else ('6-15' if n <= 15 else ('16-30' if n <= 30 else '31+'))
    rows[bk].append((abs(x), sg * (ACT[i] - BASE[i]), sg * (ACT[i] - MKO[i]) if np.isfinite(MKO[i]) else np.nan, sg * (MKO[i] - BASE[i]) if np.isfinite(MKO[i]) else np.nan))
P(f'  {"ματς μετα":10s} {"n":>5s} {"αλλαγη":>7s} | {"μοντελο":>12s} | {"αγορα ανοιγ.":>12s} | {"αγορα − μοντελο":>15s}')
for bk in ('1-5', '6-15', '16-30', '31+'):
    R = np.array(rows[bk])
    if not len(R): continue
    cs = []
    for c in (1, 2, 3):
        x = R[:, c]; x = x[np.isfinite(x)]; cs.append(f'{x.mean():+5.2f}±{x.std() / np.sqrt(len(x)):.2f}')
    P(f'  {bk:10s} {len(R):5d} {R[:, 0].mean():7.2f} | {cs[0]:>12s} | {cs[1]:>12s} | {cs[2]:>15s}')
P('  (αγορα − μοντελο = ποσους ποντους ΠΕΡΙΣΣΟΤΕΡΟ απο εμας δινει η αγορα στην ομαδα που ενισχυθηκε)')
# ---------- (Β) πλεγμα ----------
base_s = {Y: rm(BASE, [Y]) for Y in EV}
_, rb_all, _, _, _ = roi_od(BASE, msk=ALL); _, rb_fa, _, _, _ = roi_od(BASE, msk=FA); n_od, rb_od, _, _, _ = roi_od(BASE)
AFF = np.zeros(len(G), bool); AFF[list(GIDX)] = True
P(''); P('=== (Β) ΔΙΟΡΘΩΣΗ ΜΕΤΑΓΡΑΦΗΣ — πλεγμα ===')
P(f'{"εκδοχη":26s} | RMSE ολα | καλ. | RMSE επηρ. (n) | ROI ολη ≥8%             | ROI Φεβ-Απρ ≥8%          | ROI Οκτ-Δεκ')
def line(lab, v):
    n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); n3, r3, u3, ps3, _ = roi_od(v, msk=FA); n1, r1, u1, _, _ = roi_od(v)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-6 for Y in EV)
    P(f'{lab:26s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, AFF):6.3f} ({int((AFF & np.isin(SEAS_G, EV)).sum())}) | {r2:+6.1f}% ({n2:4d}) {sum(ps2[Y] > 0 for Y in EV)}/5 | '
      f'{r3:+6.1f}% ({n3:4d}) {sum(ps3[Y] > 0 for Y in EV)}/5 | {r1:+6.1f}%')
    return r2, r3
line('ΒΑΣΗ (live, καμια)', BASE)
GRID = list(itertools.product((0.5, 0.75, 1.0), (-2.0, -1.0, 0.0), (None, 32, 16, 8)))
VV = {}
for a, r, k in GRID:
    VV[(a, r, k)] = BASE + adj(a, r, k)
    line(f'α {a:<4g} αντ {r:+g} k {k if k else "∞"}', VV[(a, r, k)])
pk = {Y: min(GRID, key=lambda g: rm(VV[g], [x for x in EV if x != Y])) for Y in EV}
vL = BASE.copy()
for Y in EV: m = SEAS_G == Y; vL[m] = VV[pk[Y]][m]
P(f'LOSO επιλογες: {pk}')
r2, r3 = line('LOSO', vL)
c1 = sum(rm(vL, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = r2 - rb_all > -1.5; c3 = r3 - rb_fa > -1.5
P(f'ΚΡΙΤΗΡΙΑ: (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) ολη {r2 - rb_all:+.1f}pp {"✓" if c2 else "✗"} · (3) Φεβ-Απρ {r3 - rb_fa:+.1f}pp {"✓" if c3 else "✗"} '
  f'→ {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('  ανα σεζον RMSE ΒΑΣΗ/LOSO: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(vL, [Y]):.4f}' for Y in EV))
# ---------- (Γ) αγορα: παιζοντας ΤΥΦΛΑ την ομαδα που ενισχυθηκε στο ανοιγμα (περιγραφικο) ----------
P(''); P('=== (Γ) ΠΑΙΖΟΝΤΑΣ ΤΗΝ ΟΜΑΔΑ ΠΟΥ ΕΝΙΣΧΥΘΗΚΕ στο ανοιγμα (τυφλα, χωρις μοντελο) — καλυψη / ROI (θετικες σεζον) ===')
for lab, lo, hi, thr in (('ματς 1-5, ενισχυση ≥0.5', 1, 5, .5), ('ματς 1-15, ενισχυση ≥0.5', 1, 15, .5), ('ματς 1-15, ενισχυση ≥1.5', 1, 15, 1.5),
                         ('ματς 16-30, ενισχυση ≥0.5', 16, 30, .5)):
    res = []; sea = []
    for i, lst in GIDX.items():
        if SEAS_G[i] not in EV or i not in MKH: continue
        n = min(x[4] for x in lst); x = X0[i]
        if not (lo <= n <= hi) or abs(x) < thr: continue
        L, mk, o1, o2 = MKH[i]['o']; sg = 1 if x > 0 else -1; od_ = o1 if sg == 1 else o2
        v = (ACT[i] + L) * sg; res.append((od_ - 1) if v > 0 else (0.0 if v == 0 else -1.0)); sea.append(SEAS_G[i])
    res = np.array(res); sea = np.array(sea)
    if not len(res): continue
    pos = sum(1 for Y in set(sea) if res[sea == Y].sum() > 0)
    P(f'  {lab:30s} n {len(res):4d} · καλυψη {100 * (res > 0).sum() / max((res != 0).sum(), 1):4.1f}% · ROI {100 * res.mean():+5.1f}% ({pos}/{len(set(sea))})')
# ---------- (Δ) 20/10 Στελιος: «να ξαναμετραμε τη δυναμη οπως στην αφετηρια: φετινα δεδομενα + οποιος ηρθε − οποιος εφυγε» ----------
# Αξια ροστερ (ιδια με nba_live_roster): Σ 5·λεπτα_i/Σλεπτα · αξια_i. Πριν = οσοι επαιξαν στα 10 τελευταια ματς της ομαδας πριν το τ (φετινα λεπτα,
# αξια περσινη, αγνωστοι −1)· Μετα = Πριν − οσοι εφυγαν + οσοι ηρθαν (με τα λεπτα της παλιας τους ομαδας). Δ = Μετα − Πριν → στη δυναμη απο το τ.
TEAMG = collections.defaultdict(list)                       # (s, team) → [(d, {pid: min})]
for (t, s_, d), x in A2.groupby(['team', 's', 'd']): TEAMG[(int(s_), t)].append((np.datetime64(d, 'D'), dict(zip(x.pid, x.MIN))))
for k in TEAMG: TEAMG[k].sort(key=lambda z: z[0])
EVB = collections.defaultdict(lambda: {'in': {}, 'out': set()})   # (s, team, tau) → παικτες
for s_, t, tau, p, sgn, mm in EVTS:
    if sgn > 0: EVB[(s_, t, tau)]['in'][p] = mm
    else: EVB[(s_, t, tau)]['out'].add(p)
def tvw(d):
    if not d: return 0.0
    tot = sum(d.values()); return sum(5 * m / tot * value(p, SS) for p, m in d.items())
DELTA = []                                                  # (s, team, tau, Δ)
for (s_, t, tau), e in EVB.items():
    prev = [z for z in TEAMG.get((s_, t), []) if z[0] < tau][-10:]
    if not prev: continue
    mins = collections.defaultdict(list)
    for _, dct in prev:
        for p, m in dct.items(): mins[p].append(m)
    before = {p: float(np.sum(v)) / len(prev) for p, v in mins.items()}       # μεσα λεπτα/ματς στα 10 (0 οταν δεν επαιξε)
    after = {p: m for p, m in before.items() if p not in e['out']}
    for p, m in e['in'].items(): after[p] = m
    SS = s_
    DELTA.append((s_, t, tau, tvw(after) - tvw(before)))
GI2 = collections.defaultdict(list)
for s_, t, tau, dlt in DELTA:
    n = 0
    for i in TG.get((s_, t), []):
        if dD[i] < tau: continue
        n += 1; GI2[i].append((1 if G.home.values[i] == t else -1, dlt, n))
def adj2(alpha, k):
    X = np.zeros(len(G))
    for i, lst in GI2.items():
        for side, dlt, n in lst:
            X[i] += side * alpha * dlt * (1.0 if k is None else k / (k + n - 1))
    return X
dl = np.array([abs(x[3]) for x in DELTA])
P(''); P(f'=== (Δ) ΞΑΝΑΜΕΤΡΗΜΑ ΡΟΣΤΕΡ στη μεταγραφη (οπως η αφετηρια) · {len(DELTA)} αλλαγες ομαδας · μεσο |Δ| {dl.mean():.2f} π. (90%: {np.percentile(dl, 90):.2f}) ===')
P(f'{"εκδοχη":26s} | RMSE ολα | καλ. | RMSE επηρ. (n) | ROI ολη ≥8%             | ROI Φεβ-Απρ ≥8%          | ROI Οκτ-Δεκ')
line('ΒΑΣΗ (live, καμια)', BASE)
GRID2 = list(itertools.product((0.5, 1.0, 1.5), (None, 32, 16)))
VV2 = {}
for a, k in GRID2:
    VV2[(a, k)] = BASE + adj2(a, k); line(f'ροστερ β {a:<4g} k {k if k else "∞"}', VV2[(a, k)])
pk2 = {Y: min(GRID2, key=lambda g: rm(VV2[g], [x for x in EV if x != Y])) for Y in EV}
vL2 = BASE.copy()
for Y in EV: m = SEAS_G == Y; vL2[m] = VV2[pk2[Y]][m]
P(f'LOSO επιλογες: {pk2}')
r2b, r3b = line('LOSO ροστερ', vL2)
c1 = sum(rm(vL2, [Y]) < base_s[Y] - 1e-6 for Y in EV) >= 4; c2 = r2b - rb_all > -1.5; c3 = r3b - rb_fa > -1.5
P(f'ΚΡΙΤΗΡΙΑ (ιδια): (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) ολη {r2b - rb_all:+.1f}pp {"✓" if c2 else "✗"} · (3) Φεβ-Απρ {r3b - rb_fa:+.1f}pp {"✓" if c3 else "✗"} '
  f'→ {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P('  ανα σεζον RMSE ΒΑΣΗ/LOSO ροστερ: ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(vL2, [Y]):.4f}' for Y in EV))
# ---------- (Ε) 20/10 Στελιος: «δειξε μονο απο οταν μετρανε οι αλλαγες και μετα» — ΜΟΝΟ ματς μετα απο μεταγραφη ----------
X1 = adj(0.75, -2.0, None); X2 = adj2(0.5, 16)
M_ANY = np.zeros(len(G), bool); M_ANY[list(GIDX)] = True
P(''); P('=== (Ε) ΜΟΝΟ ΤΑ ΜΑΤΣ ΜΕΤΑ ΑΠΟ ΜΕΤΑΓΡΑΦΗ (απο τη μερα που μετραει η αλλαγη) ===')
for lab, M in (('ολα τα επηρεασμενα ματς', M_ANY), ('αλλαγη ≥0.5 π. (φορμουλα)', M_ANY & (np.abs(X1) >= .5)), ('αλλαγη ≥1.5 π. (φορμουλα)', M_ANY & (np.abs(X1) >= 1.5)),
               ('ματς 1-15 μετα, αλλαγη ≥0.5', M_ANY & (np.abs(X1) >= .5) & np.array([bool(GIDX.get(i)) and min(x[4] for x in GIDX[i]) <= 15 for i in range(len(G))]))):
    ne = int((M & np.isin(SEAS_G, EV)).sum())
    P(f'  -- {lab} ({ne} ματς) --')
    for vl, v in (('σημερα (καμια διορθωση)', BASE), ('φορμουλα απουσιας ×0.75', BASE + X1), ('ξαναμετρημα ροστερ ×0.5', BASE + X2)):
        n_, r_, u_, ps_, _ = roi_od(v, msk=M)
        bet = sum(rm(v, [Y], M) < rm(BASE, [Y], M) - 1e-6 for Y in EV)
        P(f'     {vl:26s} λαθος {rm(v, EV, M):6.3f} (καλυτερο σε {bet}/5 σεζον) · picks ≥8% {r_:+6.1f}% ({n_:4d}, {u_:+6.1f}μ, {sum(ps_[Y] > 0 for Y in EV)}/5)')
open(os.path.join(SC, 't15_trades_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
