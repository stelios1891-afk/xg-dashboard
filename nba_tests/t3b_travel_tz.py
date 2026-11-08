# -*- coding: utf-8 -*-
"""t3b_travel_tz.py — (20/10) Στελιος: «γιατι μονο ανατολη; προς τη δυση κερδιζεις ωρες;» → ΤΑΞΙΔΙ / ΖΩΝΗ ΩΡΑΣ ΚΑΙ ΣΤΙΣ ΔΥΟ ΚΑΤΕΥΘΥΝΣΕΙΣ.
ΒΑΣΗ = production CFG_H με ΑΦΕΤΗΡΙΑ ΑΝΑ ΟΜΑΔΑ (F.CARRY_MAP = 1.0·share^0.5 απο nba_carry_share.json, Test 4 / live)
       + 0.75·LOSS[2] (γνωστες απουσιες) + 3.0·(B2A − B2H).   (ιδια με t3 + carry)
ΟΡΙΣΜΟΙ (ανα ομαδα, γηπ ΚΑΙ φιλ): tz_change = ζωνη(γηπεδο τωρα) − ζωνη(γηπεδο προηγ. αγωνα της ομαδας), ιδια ημερομηνια για DST
  (ανατολη +, δυση −)· ξεκουραση = μερες αναμεσα − 1 (B2B = 0)· km = αποσταση γηπεδων. Ουδετερα γηπεδα/1ος αγωνας → 0.
  Ορος στο περιθωριο (γηπ − φιλ) = f(γηπ) − f(φιλ).
ΕΚΔΟΧΕΣ (συντελεστες OLS στο υπολοιπο ACT − ΒΑΣΗ, με σταθερα που ΔΕΝ εφαρμοζεται, LOSO = fit στις αλλες 4):
 (α) t3: γηπεδουχος που γυριζει ΑΝΑΤΟΛΙΚΑ με ≤1 μερα ξεκ. — k·(−1.29 για 1ω / −4.53 για ≥2ω) (τιμες t3, DST οπως t3)
 (β) ΚΑΘΕ ομαδα: k_E·(ωρες ανατολικα) + k_W·(ωρες δυτικα), ανεξαρτητα απο ξεκουραση
 (γ) οπως β αλλα μονο οταν ξεκουραση ≤1 μερα
 (δβ)/(δγ) οπως β/γ με ΕΝΑ συμμετρικο συντελεστη στο |ωρες|
 (εβ)/(εγ) ελεγχος: χιλιομετρα (/1000) αντι για ωρες, ολα / ≤1 μερα
ΕΠΙΛΟΓΗ ΜΙΑΣ ΕΚΔΟΧΗΣ με LOSO: για καθε σεζον-στοχο, εσωτερικο LOSO στις αλλες 4 (fit σε 3, μετρα στην 4η) → ελαχιστο RMSE.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ «ΠΕΡΝΑΕΙ» (γραφτηκε ΠΡΙΝ το τρεξιμο, ιδιο με t3): η LOSO-επιλεγμενη εκδοχη εχει RMSE (ολα τα ματς)
καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος edge ≥8% Οκτ-Δεκ οχι χειροτερο (διαφορα > −1.5pp).
Αναφερεται επισης ROI ολης της σεζον και units (μονο πληροφορια, οχι κριτηριο)."""
import os, sys, io, json, math, collections
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split('ev_m = np.isin(SEAS_G, EV)')[0]
exec(src)
sys.stdout.reconfigure(encoding='utf-8')
L2 = LOSS[2][0]
MG0 = MG.copy()
# ---------- ΑΦΕΤΗΡΙΑ ΑΝΑ ΟΜΑΔΑ (live) ----------
CJ = json.load(open('nba_carry_share.json', encoding='utf-8'))
F.CARRY_MAP = {k: CJ['c0'] * v ** CJ['pow'] for k, v in CJ['share'].items()}
_, MGc, _, _ = F.run_all((0.8, 8, 60, .75, 5.0, 1.0, .75, .25)); MGc = np.asarray(MGc, float)
F.CARRY_MAP = None
nmatch = sum(f'{s}|{t}' in CJ['share'] for s in EV for t in set(G.home))
print(f'carry map: κλειδια που ταιριαζουν στις EVAL σεζον {nmatch}/{len(EV) * 30}')

# ---------- B2B, ζωνες, ταξιδι ----------
TZ = {**{t: -5 for t in 'ATL BOS BRK CHO CLE DET IND MIA NYK ORL PHI TOR WAS'.split()},
      **{t: -6 for t in 'CHI DAL HOU MEM MIL MIN NOP OKC SAS'.split()},
      **{t: -7 for t in 'DEN UTA PHO'.split()}, **{t: -8 for t in 'GSW LAC LAL POR SAC'.split()}}
LL = dict(ATL=(33.757, -84.396), BOS=(42.366, -71.062), BRK=(40.683, -73.975), CHO=(35.225, -80.839), CHI=(41.881, -87.674),
          CLE=(41.496, -81.688), DAL=(32.790, -96.810), DEN=(39.749, -105.008), DET=(42.341, -83.055), GSW=(37.768, -122.388),
          HOU=(29.751, -95.362), IND=(39.764, -86.156), LAC=(34.043, -118.267), LAL=(34.043, -118.267), MEM=(35.138, -90.051),
          MIA=(25.781, -80.188), MIL=(43.045, -87.917), MIN=(44.979, -93.276), NOP=(29.949, -90.082), NYK=(40.751, -73.993),
          OKC=(35.463, -97.515), ORL=(28.539, -81.384), PHI=(39.901, -75.172), PHO=(33.446, -112.071), POR=(45.532, -122.667),
          SAC=(38.580, -121.500), SAS=(29.427, -98.438), TOR=(43.643, -79.379), UTA=(40.768, -111.901), WAS=(38.898, -77.021))
def km(a, b):
    (la1, lo1), (la2, lo2) = LL[a], LL[b]; p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def tz(t, d):
    ts = pd.Timestamp(d); y = ts.year
    dst0 = pd.Timestamp(y, 3, 8) + pd.Timedelta(days=(6 - pd.Timestamp(y, 3, 8).weekday()) % 7)
    dst1 = pd.Timestamp(y, 11, 1) + pd.Timedelta(days=(6 - pd.Timestamp(y, 11, 1).weekday()) % 7)
    return TZ[t] + (1 if (dst0 <= ts < dst1) and t != 'PHO' else 0)
N = len(G); NEU = G.neutral.values
B2H = np.zeros(N); B2A = np.zeros(N); EAST_T3 = np.zeros(N)
TZC = np.zeros((N, 2)); KM = np.zeros((N, 2)); GAP = np.full((N, 2), 99)      # [:,0] γηπ, [:,1] φιλ
last = {}; lastloc = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    if not NEU[i] and (s, h_) in last:                                   # ακριβως η t3 εκδοχη
        gap = int((d - last[(s, h_)]).astype(int)); loc = lastloc[(s, h_)]
        if gap <= 2 and loc is not None and loc != h_: EAST_T3[i] = max(0, tz(h_, d) - tz(loc, last[(s, h_)]))
    for j, t in enumerate((h_, a_)):
        if (s, t) in last:
            GAP[i, j] = int((d - last[(s, t)]).astype(int)); loc = lastloc[(s, t)]
            if not NEU[i] and loc is not None:
                TZC[i, j] = tz(h_, d) - tz(loc, d); KM[i, j] = km(loc, h_)
    loc_i = None if NEU[i] else h_
    last[(s, h_)] = d; last[(s, a_)] = d; lastloc[(s, h_)] = loc_i; lastloc[(s, a_)] = loc_i
CORE = MGc + 0.75 * L2
BASE = CORE + 3.0 * (B2A - B2H)
BASE_NOC = MG0 + 0.75 * L2 + 3.0 * (B2A - B2H)
ev_m = np.isin(SEAS_G, EV)
RES = ACT - BASE
E_ = np.clip(TZC, 0, None); W_ = np.clip(-TZC, 0, None); R1 = (GAP <= 2).astype(float)
dif = lambda M: M[:, 0] - M[:, 1]
ELIT = -1.29 * (EAST_T3 == 1) - 4.53 * (EAST_T3 >= 2)
VERS = collections.OrderedDict([
    ('α  t3 ανατ. γηπ ≤1μ', np.c_[ELIT]),
    ('β  E/W ολα', np.c_[dif(E_), dif(W_)]),
    ('γ  E/W ≤1μ', np.c_[dif(E_ * R1), dif(W_ * R1)]),
    ('δβ |ωρες| ολα', np.c_[dif(E_ + W_)]),
    ('δγ |ωρες| ≤1μ', np.c_[dif((E_ + W_) * R1)]),
    ('εβ km ολα', np.c_[dif(KM / 1000)]),
    ('εγ km ≤1μ', np.c_[dif(KM / 1000 * R1)]),
])
OK = np.isfinite(BASE)
def fit(X, ys):
    m = np.isin(SEAS_G, ys) & OK; A_ = np.c_[np.ones(m.sum()), X[m]]
    c, *_ = np.linalg.lstsq(A_, RES[m], rcond=None); return c[1:]
def sse(v, ys):
    m = np.isin(SEAS_G, ys) & OK; return float(((ACT - v)[m] ** 2).sum()), int(m.sum())
def loso(X):
    v = BASE.copy(); cf = {}
    for Y in EV:
        c = fit(X, [x for x in EV if x != Y]); cf[Y] = c; mm = SEAS_G == Y; v[mm] = BASE[mm] + (X @ c)[mm]
    return v, cf
def inner_rmse(X, outer):
    oth = [x for x in EV if x != outer]; S = n = 0
    for Z in oth:
        c = fit(X, [x for x in oth if x != Z]); a, b = sse(BASE + X @ c, [Z]); S += a; n += b
    return math.sqrt(S / n)

print(f'\nEVAL {ev_m.sum()} αγωνες · ομαδο-αγωνες με ταξιδι ανατ. {int((E_[ev_m] > 0).sum())} / δυτ. {int((W_[ev_m] > 0).sum())} · '
      f'εκ των οποιων ≤1μ ξεκ.: ανατ. {int(((E_ > 0) & (R1 > 0))[ev_m].sum())} / δυτ. {int(((W_ > 0) & (R1 > 0))[ev_m].sum())}')
print(f'ΒΑΣΗ χωρις carry RMSE {rm(BASE_NOC, EV):.4f} · ΒΑΣΗ με carry (live) RMSE {rm(BASE, EV):.4f}')

# ---------- ΠΕΡΙΓΡΑΦΙΚΟ ----------
print('\n=== ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο (ACT − ΒΑΣΗ) υπερ της ομαδας, ανα κατευθυνση × ξεκουραση × γηπ/φιλ (μεσος ± SE, n) ===')
cells = collections.defaultdict(list)
for i in np.where(ev_m & OK & ~NEU)[0]:
    for j in (0, 1):
        if GAP[i, j] == 99: continue
        dr = 'ανατ' if TZC[i, j] > 0 else ('δυτ' if TZC[i, j] < 0 else '0ω')
        rs = 'B2B' if GAP[i, j] == 1 else ('1μ' if GAP[i, j] == 2 else '2+μ')
        cells[(dr, rs, 'γηπ' if j == 0 else 'φιλ')].append(RES[i] * (1 if j == 0 else -1))
print(f'   {"":10s}' + ''.join(f'| {r + " " + ha:>20s} ' for ha in ('γηπ', 'φιλ') for r in ('B2B', '1μ', '2+μ')))
for dr in ('ανατ', '0ω', 'δυτ'):
    row = f'   {dr:10s}'
    for ha in ('γηπ', 'φιλ'):
        for r in ('B2B', '1μ', '2+μ'):
            x = np.array(cells[(dr, r, ha)])
            row += f'| {x.mean():+5.2f}±{x.std(ddof=1) / np.sqrt(len(x)):4.2f} (n{len(x):4d}) ' if len(x) > 1 else f'| {"—":>20s} '
    print(row)
print('   ανα ωρες (ολες οι ξεκουρασεις, γηπ+φιλ μαζι, υπερ ομαδας):')
th = collections.defaultdict(list)
for i in np.where(ev_m & OK & ~NEU)[0]:
    for j in (0, 1):
        if GAP[i, j] != 99: th[int(TZC[i, j])].append(RES[i] * (1 if j == 0 else -1))
print('     ' + ' · '.join(f'{h:+d}ω {np.mean(th[h]):+5.2f}±{np.std(th[h], ddof=1) / np.sqrt(len(th[h])):.2f} (n{len(th[h])})' for h in sorted(th)))

# ---------- ΕΚΔΟΧΕΣ ----------
base_s = {Y: rm(BASE, [Y]) for Y in EV}
nb, rb, ub, psb, _ = roi_od(BASE); nfb, rfb, ufb, psfb, _ = roi_od(BASE, msk=ALL)
HDR = f'{"εκδοχη":22s} | RMSE ολα | καλ. | ROI Οκτ-Δεκ ≥8%  (n)    units θετ | ROI ολη ≥8%  (n)    units'
def line(lab, v):
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-5 for Y in EV)
    print(f'{lab:22s} | {rm(v, EV):8.4f} | {bet}/5  | {r1:+6.1f}% ({n1:4d}) {u1:+7.1f}u {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {u2:+7.1f}u', flush=True)
    return bet, r1
print(f'\n=== ΕΚΔΟΧΕΣ (LOSO συντελεστες) ===\n{HDR}')
line('ΒΑΣΗ (carry)', BASE)
LV = {}
for nm, X in VERS.items():
    v, cf = loso(X); LV[nm] = (v, cf); line(nm, v)
print('\nΣυντελεστες ανα fold (π. περιθωριου ανα ωρα / ανα 1000km· αρνητικο = χανει η ομαδα που ταξιδευει) — σεζον-στοχος 2022…2026:')
for nm, (v, cf) in LV.items():
    print(f'   {nm:22s} ' + ' · '.join('/'.join(f'{x:+.2f}' for x in cf[Y]) for Y in EV))
full = {nm: fit(X, EV) for nm, X in VERS.items()}
print('   ολα τα δεδομενα (5σ): ' + ' · '.join(f'{nm.split()[0]} ' + '/'.join(f'{x:+.2f}' for x in c) for nm, c in full.items()))

# ---------- ΕΠΙΛΟΓΗ ΜΙΑΣ ΕΚΔΟΧΗΣ ----------
print('\n=== ΕΠΙΛΟΓΗ ΕΚΔΟΧΗΣ με εσωτερικο LOSO (RMSE ×1e4 πανω απο 13) ===')
pick = {}
for Y in EV:
    ir = {nm: inner_rmse(X, Y) for nm, X in VERS.items()}; pick[Y] = min(ir, key=ir.get)
    print(f'   στοχος {Y}: ' + ' '.join(f'{nm.split()[0]} {(x - 13) * 1e4:5.0f}' for nm, x in ir.items()) + f'  (βαση {(math.sqrt(sse(BASE, [x for x in EV if x != Y])[0] / sse(BASE, [x for x in EV if x != Y])[1]) - 13) * 1e4:5.0f}) → {pick[Y].split()[0]}')
vS = BASE.copy()
for Y in EV: mm = SEAS_G == Y; vS[mm] = LV[pick[Y]][0][mm]
print(HDR); bet, r1 = line('LOSO-επιλεγμενη', vS)
print(f'\nΚΡΙΤΗΡΙΟ: RMSE καλυτερο {bet}/5 (απαιτ. ≥4) · ROI Οκτ-Δεκ {r1:+.1f}% vs ΒΑΣΗ {rb:+.1f}% (Δ {r1 - rb:+.1f}pp, απαιτ. > −1.5) → '
      f'{"ΠΕΡΝΑΕΙ" if bet >= 4 and r1 - rb > -1.5 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
print('\nΑΝΑ ΣΕΖΟΝ RMSE (ΒΑΣΗ / επιλεγμ. / α / β / γ) · units Οκτ-Δεκ (ΒΑΣΗ / επιλεγμ.):')
ps_s = roi_od(vS)[3]
for Y in EV:
    print(f'   {Y}: {base_s[Y]:.4f} / {rm(vS, [Y]):.4f} / ' + ' / '.join(f'{rm(LV[k][0], [Y]):.4f}' for k in list(VERS)[:3]) + f' · {psb[Y]:+.1f} / {ps_s[Y]:+.1f}')
