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
import os, sys, io, contextlib, collections, itertools, json
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'absence_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    _src = open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0]
    # 21/10 (Στελιος «γιατι οχι ιδια με το live;»): ΑΝΤΙΓΡΑΦΟ LIVE — αφετηρια ανα ομαδα 1.0·√(μεριδιο λεπτων) (nba_carry_share.json)
    REPLICA = os.environ.get('NBA_REPLICA', '1') == '1'
    if REPLICA:
        _cs = json.load(open(os.path.join(os.path.dirname(SC), 'nba_carry_share.json'), encoding='utf-8'))
        ns['_CMAP'] = {k: _cs['c0'] * v ** _cs['pow'] for k, v in _cs['share'].items()}
        _old = '_, MG, _, _ = F.run_all((0.8, 8, 60, .75, 5.0, 1.0, .75, .25))'
        assert _src.count(_old) == 1
        _src = _src.replace(_old, 'F.CARRY_MAP = _CMAP; ' + _old + '; F.CARRY_MAP = None')
    exec(_src, ns)
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
# 21/10 ΑΝΤΙΓΡΑΦΟ LIVE: αλλαγη ζωνης ωρας −0.68 π./ωρα αν το προηγουμενο ματς της ομαδας ηταν ≤2 μερες πριν (ιδιο με nba_odds_scan.tz_feat)
_TZ = {**{t: -5 for t in 'ATL BOS BRK CHO CLE DET IND MIA NYK ORL PHI TOR WAS'.split()}, **{t: -6 for t in 'CHI DAL HOU MEM MIL MIN NOP OKC SAS'.split()},
       **{t: -7 for t in 'DEN UTA PHO'.split()}, **{t: -8 for t in 'GSW LAC LAL POR SAC'.split()}}
import datetime as _dt
def _tzone(t, d):
    dd = _dt.date.fromisoformat(str(d)[:10]); y = dd.year
    m8 = _dt.date(y, 3, 8); a0 = m8 + _dt.timedelta(days=(6 - m8.weekday()) % 7); n1 = _dt.date(y, 11, 1); a1 = n1 + _dt.timedelta(days=(6 - n1.weekday()) % 7)
    return _TZ[t] + (1 if (a0 <= dd < a1) and t != 'PHO' else 0)
TZH = np.zeros(len(G)); TZA = np.zeros(len(G)); lastv = {}
if REPLICA:
    for i in np.argsort(dD, kind='stable'):
        s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
        for t, arr in ((h_, TZH), (a_, TZA)):
            pv = lastv.get((s, t))
            if pv and int((d - pv[0]).astype(int)) <= 2 and h_ in _TZ and pv[1] in _TZ:
                arr[i] = abs(_tzone(h_, d) - _tzone(pv[1], d))
        lastv[(s, h_)] = (d, h_); lastv[(s, a_)] = (d, h_)
BASE = MG + 3.0 * (B2A - B2H) + 0.75 * (LH - LA) - 0.68 * (TZH - TZA)
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
        d_new = np.datetime64(ds[j], 'D')
        # 20/10 ΔΙΟΡΘΩΣΗ (ελεγχος Dončić/Butler): οπως το live → ο παικτης που ΦΕΥΓΕΙ αφαιρειται απο το ντεμπουτο του στη νεα ομαδα
        # (ως τοτε, αν λειπει, τον καλυπτει ηδη το συστημα απουσιων)· ο παικτης που ΕΡΧΕΤΑΙ πιστωνεται ΜΟΝΟ στα ματς που παιζει με τη νεα ομαδα
        # (τραυματιας = «Out» στη λιστα, δεν μετρα). Πριν: και τα δυο απο τ = ντεμπουτο − 2 μερες → πιστωση τραυματιων/πριν το ντεμπουτο.
        EVTS.append((s, t0, d_new, p, -1, min(mm, 36.0))); EVTS.append((s, t1, d_new, p, +1, min(mm, 36.0)))
EVTS = [e for e in EVTS if e[0] in EV]
# αριθμος ματς της ομαδας απο τ
TG = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'):
    TG[(SEAS_G[i], G.home.values[i])].append(i); TG[(SEAS_G[i], G.away.values[i])].append(i)
PLAYED = set(zip(A2.pid, A2.team, A2.d.values.astype('datetime64[D]')))
GIDX = collections.defaultdict(list)                        # i → [(sg, evt, n)]
for e in EVTS:
    s, t, tau, p, sgn, mm = e; n = 0
    for i in TG.get((s, t), []):
        if dD[i] < tau: continue
        n += 1
        if sgn > 0 and (p, t, dD[i]) not in PLAYED: continue      # εισερχομενος που δεν επαιξε (τραυματιας/πριν ερθει) → καμια πιστωση
        side = 1 if G.home.values[i] == t else -1
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
# ---------- (Ζ) 20/10 Στελιος: «την αλλαγη ΟΛΩΝ των picks, απο ποια αγωνιστικη ως ποια, ποσο βελτιωθηκαν» ----------
cover_, SIG_ = ns['cover'], ns['SIG']
GNUM = {}                                                   # (i, team) → αριθμος αγωνα της ομαδας
for (s_, t), lst in TG.items():
    for k_, i in enumerate(lst): GNUM[(i, t)] = k_ + 1
def pick(v, i):
    L, mk, o1, o2 = MKH[i]['o']; pw, pp, pl = cover_(v[i], L, SIG_)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    x = (ACT[i] + L) * s_; return s_, ((od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0))
V1 = BASE + X1
first_g = []
for e in EVTS:
    s_, t, tau, p, sgn, mm = e
    gs = [GNUM[(i, t)] for i in TG.get((s_, t), []) if dD[i] >= tau]
    if gs: first_g.append(gs[0])
fg = np.array(first_g)
P(''); P('=== (Ζ) ΟΛΑ ΤΑ PICKS ΣΤΑ ΜΑΤΣ ΜΕΤΑ ΑΠΟ ΜΕΤΑΓΡΑΦΗ: σημερα vs με διορθωση (φορμουλα ×0.75, χωρις σβησιμο) ===')
P(f'  η διορθωση αρχιζει στον αγωνα της ομαδας: διαμεσος {np.median(fg):.0f}ος (10%: {np.percentile(fg, 10):.0f}ος · 90%: {np.percentile(fg, 90):.0f}ος) και μενει ως το τελος της κανονικης περιοδου (82ος)')
grp = collections.defaultdict(list)
for i in GIDX:
    if SEAS_G[i] not in EV or i not in MKH or not np.isfinite(BASE[i]): continue
    a, b = pick(BASE, i), pick(V1, i)
    if a is None and b is None: continue
    big = abs(X1[i]) >= 1.5
    if a and b and a[0] == b[0]: g = 'ιδιο pick (μενει)'
    elif a and b: g = 'ΑΝΤΙΘΕΤΗ πλευρα'
    elif a: g = 'ΚΟΒΕΤΑΙ (υπηρχε, φευγει)'
    else: g = 'ΠΡΟΣΤΙΘΕΤΑΙ (νεο)'
    grp[g].append((SEAS_G[i], a[1] if a else None, b[1] if b else None, big))
def roi(v):
    v = [x for x in v if x is not None]; return (100 * np.mean(v), len(v), sum(v)) if v else (0, 0, 0)
P(f'  {"ομαδα":28s} {"picks":>5s} | {"με τη σημερινη πλευρα":>26s} | {"με τη διορθωμενη πλευρα":>26s}')
for g in ('ιδιο pick (μενει)', 'ΚΟΒΕΤΑΙ (υπηρχε, φευγει)', 'ΠΡΟΣΤΙΘΕΤΑΙ (νεο)', 'ΑΝΤΙΘΕΤΗ πλευρα'):
    L_ = grp.get(g, [])
    if not L_: continue
    ra = roi([x[1] for x in L_]); rb = roi([x[2] for x in L_])
    P(f'  {g:28s} {len(L_):5d} | ' + (f'{ra[0]:+6.1f}% ({ra[2]:+6.1f}μ)' if ra[1] else '        —       ').rjust(26) + ' | ' + (f'{rb[0]:+6.1f}% ({rb[2]:+6.1f}μ)' if rb[1] else '        —       ').rjust(26))
allA = [x[1] for L_ in grp.values() for x in L_]; allB = [x[2] for L_ in grp.values() for x in L_]
ra, rb = roi(allA), roi(allB)
P(f'  ΣΥΝΟΛΟ σε αυτα τα ματς: σημερα {ra[0]:+.1f}% ({ra[1]} picks, {ra[2]:+.1f}μ) → με διορθωση {rb[0]:+.1f}% ({rb[1]} picks, {rb[2]:+.1f}μ) · διαφορα {rb[2] - ra[2]:+.1f} μοναδες')
for Y in EV:
    a_ = roi([x[1] for L_ in grp.values() for x in L_ if x[0] == Y]); b_ = roi([x[2] for L_ in grp.values() for x in L_ if x[0] == Y])
    P(f'    {Y}: {a_[2]:+6.1f}μ ({a_[1]}) → {b_[2]:+6.1f}μ ({b_[1]})')
# ---------- (Η) 20/10 Στελιος: «αυτα που κοπηκαν γιατι κοπηκαν;» ----------
def pick_e(v, i):
    L, mk, o1, o2 = MKH[i]['o']; pw, pp, pl = cover_(v[i], L, SIG_)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
MKC = {i: d['c'][1] for i, d in MKH.items()}
recs = []
for i in GIDX:
    if SEAS_G[i] not in EV or i not in MKH or not np.isfinite(BASE[i]): continue
    a, b = pick(BASE, i), pick(V1, i)
    if (a is None) == (b is None): continue
    kind = 'ΚΟΒΕΤΑΙ' if a else 'ΠΡΟΣΤΙΘΕΤΑΙ'
    sd = a[0] if a else b[0]; res = a[1] if a else b[1]
    e0 = pick_e(BASE, i)[1]; e1 = pick_e(V1, i)[1]
    eff = sd * X1[i]                                        # + = η διορθωση ΒΟΗΘΑ την πλευρα του pick, − = την ΑΔΥΝΑΤΙΖΕΙ
    t_pick = G.home.values[i] if sd == 1 else G.away.values[i]
    who = set()
    for side, sgn, v, mm, n in GIDX[i]:
        team_side = side * sd                               # +1 = ομαδα του pick
        who.add(('η ΔΙΚΗ ΜΑΣ ομαδα ' if team_side > 0 else 'ο ΑΝΤΙΠΑΛΟΣ ') + ('ΠΗΡΕ παικτη' if sgn > 0 else 'ΕΔΩΣΕ παικτη'))
    mv = sd * (MKC[i] - MKH[i]['o'][1])                     # + = η αγορα πηγε ΠΡΟΣ το pick ως το κλεισιμο
    recs.append(dict(kind=kind, res=res, eff=eff, e0=e0, e1=e1, mon=int(MON[i]), who=' & '.join(sorted(who)), mv=mv, sea=SEAS_G[i]))
import pandas as pd
R = pd.DataFrame(recs)
def cl(d):
    return f'{len(d):4d} picks · ROI {100 * d.res.mean():+6.1f}% ({d.res.sum():+6.1f}μ, {sum(d.groupby("sea").res.sum() > 0)}/{d.sea.nunique()}) · αγορα μετα {d.mv.mean():+5.2f}π'
P(''); P('=== (Η) ΓΙΑΤΙ ΚΟΒΟΝΤΑΙ / ΠΡΟΣΤΙΘΕΝΤΑΙ picks με τη διορθωση μεταγραφων ===')
for kind in ('ΚΟΒΕΤΑΙ', 'ΠΡΟΣΤΙΘΕΤΑΙ'):
    D_ = R[R.kind == kind]
    P(f'  ---- {kind}: {cl(D_)} · edge σημερα {100 * D_.e0.mean():.1f}% → με διορθωση {100 * D_.e1.mean():.1f}% · μεση μετακινηση μοντελου {D_.eff.mean():+.2f}π ----')
    P('   ποιος αλλαξε ρόστερ (σε σχεση με το pick):')
    for w, d in sorted(D_.groupby('who'), key=lambda kv: -len(kv[1])):
        if len(d) >= 8: P(f'     {w:62s} {cl(d)}')
    P('   ποσο μετακινηθηκε το μοντελο:')
    for lo, hi, lab in ((0, .5, '<0.5 π.'), (.5, 1.5, '0.5-1.5 π.'), (1.5, 99, '≥1.5 π.')):
        d = D_[(D_.eff.abs() >= lo) & (D_.eff.abs() < hi)]
        if len(d): P(f'     {lab:12s} {cl(d)}')
    P('   ποιον μηνα:')
    for m in (11, 12, 1, 2, 3, 4):
        d = D_[D_.mon == m]
        if len(d): P(f'     μηνας {m:2d}    {cl(d)}')
open(os.path.join(SC, 't15_trades_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
