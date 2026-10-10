"""ucl_gap_totals_test.py — 10/10/2026 (Στελιος: «η πετυχαινουμε τη διορθωση και κραταμε over & under, η αν δεν πετυχει κραταμε μονο τα over»).
Διαγνωση (ucl_gap_totals_diag): στο UCL το λαθος ΣΥΝΟΛΟΥ μεγαλωνει με τη διαφορα δυναμης λιγκας |D| (+0.89/μοναδα |D|, και σε FF +0.64)·
σε UEL ανιθετα (−0.77), UECL ≈0 → κοινη παραμετρος ≈0. ΑΡΑ: ΜΙΑ παραμετρος ΜΟΝΟ UCL, ΜΟΝΟ στο ζευγος συνολων (το χαντικαπ ανεγγιχτο):
    λ_ou της ομαδας απο τη ΔΥΝΑΤΟΤΕΡΗ λιγκα × exp(τ·|D|)   (τα επιπλεον γκολ τα βαζει ο «μεγαλος» — ucl_totals_sources_diag)
τ: μεγιστη Poisson πιθανοφανεια γκολ (και των 2 πλευρων) στις ΑΛΛΕΣ 3 σεζον UCL (LOSO), grid 0..1.5.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ολα εκτος δειγματος, κρυμμενη σεζον):
  Κ1 ακριβεια: Poisson log-lik γκολ UCL καλυτερη σε ≥3/4 σεζον.
  Κ2 βαθμονομηση: |μεσο λαθος συνολου| των μη-FotMob ματς ΜΙΚΡΑΙΝΕΙ, και των FF ΔΕΝ μεγαλωνει (συνολο 4 σεζον).
  Κ3 picks (over ≥4% / under ≥10%, ενα ανα ματς, πρωτη εμφανιση ≤72ω, μεσος Crown/SBOBET): (α) συνολικες μοναδες UCL (FF+μη-FM) ≥ σημερινες,
     (β) τα under μη-FotMob ΔΕΝ ειναι αρνητικα (ROI ≥0 ή εξαφανιζονται), (γ) νεα μορφη FF μοναδες οχι χειροτερες απο σημερα σε καμια απο τις 2 σεζον.
  Περνα ολα → over ΚΑΙ under στα μη-FotMob (με τη διορθωση, που μπαινει και στα FF UCL συνολα). Αλλιως → μονο over μη-FotMob, χωρις διορθωση.
"""
import sys, io, os, json, glob, contextlib
DRAW_SCALE = 0.85
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
picks, KO = u['picks'], u['KO']
MIDS, COMP, FM, SEA = u['MIDS'], np.asarray(u['COMP']), u['FM'], np.asarray(u['SEA'])
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA = np.asarray(w['GH']), np.asarray(w['GA'])
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
import euro_shadow_scan as ES
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
TOU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        if bk is None: continue
        seq = sorted((int(mt), pl(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or []) if mt and pl(gg) is not None)
        if seq: TOU[(str(r['mid']), bk)] = seq
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
def mtot(L, o, un):
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def _cat(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return '?'
    a, b = sorted((_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')))
    return a + b
SRCC = [_cat(i) for i in range(len(MIDS))]

Dg = np.asarray(w['g']['D'], float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
U = np.where(ucl)[0]
strong_h = Dg > 0                                   # D>0: η λιγκα του γηπεδουχου δυνατοτερη
def pair(tau, idx):
    f = np.exp(tau * np.abs(Dg[idx]))
    lh = np.where(strong_h[idx], OH[idx] * f, OH[idx]); la = np.where(strong_h[idx], OA[idx], OA[idx] * f)
    return lh, la
from math import lgamma
_LGH = np.array([lgamma(g + 1) for g in GH]); _LGA = np.array([lgamma(g + 1) for g in GA])
def ll(tau, idx):
    lh, la = pair(tau, idx)
    return (GH[idx] * np.log(lh) - lh - _LGH[idx] + GA[idx] * np.log(la) - la - _LGA[idx]).sum()
GRID = np.round(np.arange(0, 1.51, 0.05), 2)
# ---- snapshots αγορας (ανεξαρτητα απο τ) ----
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
SN = []
for i in U:
    mid = MIDS[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            sn = snap_ou(mid, bk, h)
            if sn: SN.append((i, bk, h) + tuple(sn))
print(f'UCL ματς {len(U)} · snapshots {len(SN)}')
def picks_for(lam):                                  # lam: dict i -> (lh, la)
    TD = {i: ES.tot_dist(lam[i][0], lam[i][1], DRAW_SCALE) for i in lam}
    rows = []
    for (i, bk, h, L, o, un) in SN:
        if i not in TD: continue
        po, pu = ES.p_over(TD[i], L); tot = GH[i] + GA[i]
        for side, od, pw, pl in (('over', o, po, pu), ('under', un, pu, po)):
            if not (1.70 <= od <= 2.10): continue
            e = pw * (od - 1) * (1 - picks.MARGIN) - pl
            if e >= (.04 if side == 'over' else .10):
                rows.append(dict(i=i, bk=bk, h=h, side=side, sea=SEA[i], src=SRCC[i], e=e, od=od, pnl=settle(tot, L, od, side == 'over')))
    P = pd.DataFrame(rows).sort_values('h', ascending=False)
    P = P.groupby(['i', 'bk', 'side']).head(1).sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
    P['nf'] = P.src != 'FF'
    return P
def units(x):
    return x.groupby('bk').pnl.sum().mean() if len(x) else 0.0
def roi(x):
    return 100 * x.groupby('bk').pnl.mean().mean() if len(x) else float('nan')
def npk(x):
    return x.groupby('bk').size().mean() if len(x) else 0
base_lam = {i: (OH[i], OA[i]) for i in U}
P0 = picks_for(base_lam)
k1 = []; res0 = []; res1 = []; Pfold = []; taus = {}
for hold in SEAS:
    tr = U[np.isin(SEA[U], [s for s in SEAS if s != hold])]; te = U[SEA[U] == hold]
    tau = GRID[np.argmax([ll(t, tr) for t in GRID])]; taus[hold] = tau
    d = ll(tau, te) - ll(0.0, te); k1.append(d)
    lh, la = pair(tau, te)
    for j, i in enumerate(te):
        res0.append((SRCC[i] != 'FF', GH[i] + GA[i] - OH[i] - OA[i])); res1.append((SRCC[i] != 'FF', GH[i] + GA[i] - lh[j] - la[j]))
    lam = {i: (lh[j], la[j]) for j, i in enumerate(te)}
    Pfold.append(picks_for(lam))
    print(f'κρυμμενη {hold}: τ = {tau:.2f} (train) · Δlog-lik στην {hold} {d:+.2f} ({len(te)} ματς)')
P1 = pd.concat(Pfold)
fullt = GRID[np.argmax([ll(t, U) for t in GRID])]
print(f'τ σε ολες τις 4 σεζον: {fullt:.2f}  (exp(τ·0.5) = ×{np.exp(fullt * .5):.2f} στον «μεγαλο» σε |D|=0.5)')
ok1 = sum(1 for d in k1 if d > 0) >= 3
print(f'\nΚ1 ακριβεια: θετικο σε {sum(1 for d in k1 if d > 0)}/4 σεζον → {"✓" if ok1 else "✗"}')
r0 = pd.DataFrame(res0, columns=['nf', 'r']); r1 = pd.DataFrame(res1, columns=['nf', 'r'])
nf0, nf1 = r0[r0.nf].r.mean(), r1[r1.nf].r.mean(); ff0, ff1 = r0[~r0.nf].r.mean(), r1[~r1.nf].r.mean()
ok2 = abs(nf1) < abs(nf0) and abs(ff1) <= abs(ff0) + 1e-9
print(f'Κ2 βαθμονομηση: μη-FotMob λαθος συνολου {nf0:+.2f} → {nf1:+.2f} · FF {ff0:+.2f} → {ff1:+.2f} → {"✓" if ok2 else "✗"}')
print('\nΚ3 PICKS (εκτος δειγματος) — σημερα → με διορθωση')
for lab, m0, m1 in (('ΟΛΑ UCL', P0.i >= 0, P1.i >= 0),
                    ('FF over', (~P0.nf) & (P0.side == 'over'), (~P1.nf) & (P1.side == 'over')),
                    ('FF under', (~P0.nf) & (P0.side == 'under'), (~P1.nf) & (P1.side == 'under')),
                    ('μη-FM over', P0.nf & (P0.side == 'over'), P1.nf & (P1.side == 'over')),
                    ('μη-FM under', P0.nf & (P0.side == 'under'), P1.nf & (P1.side == 'under'))):
    a, b = P0[m0], P1[m1]
    print(f'   {lab:12s} {npk(a):4.0f} picks {roi(a):+6.1f}% {units(a):+6.1f}μ  →  {npk(b):4.0f} picks {roi(b):+6.1f}% {units(b):+6.1f}μ   · ανα σεζον μοναδες: ' +
          ' '.join(f'{s[2:]} {units(a[a.sea == s]):+.1f}→{units(b[b.sea == s]):+.1f}' for s in SEAS))
ok3a = units(P1) >= units(P0)
u = P1[P1.nf & (P1.side == 'under')]; ok3b = len(u) == 0 or roi(u) >= 0
ok3c = all(units(P1[(~P1.nf) & (P1.sea == s)]) >= units(P0[(~P0.nf) & (P0.sea == s)]) - 1e-9 for s in NEW)
print(f'Κ3α συνολικες μοναδες ≥ σημερα: {"✓" if ok3a else "✗"} · Κ3β under μη-FM οχι αρνητικα: {"✓" if ok3b else "✗"} · Κ3γ FF νεα μορφη οχι χειροτερα και στις 2: {"✓" if ok3c else "✗"}')
print(f'\nΑΠΟΤΕΛΕΣΜΑ: {"ΠΕΡΝΑ — over & under μη-FotMob με τη διορθωση" if (ok1 and ok2 and ok3a and ok3b and ok3c) else "ΔΕΝ ΠΕΡΝΑ — μονο over μη-FotMob, χωρις διορθωση"}')
