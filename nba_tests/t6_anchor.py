# -*- coding: utf-8 -*-
"""t6_anchor.py — ΤΕΣΤ 6 (Στελιος 20/10: «εχουμε δοκιμασει την αγκυρα αγορας ή οχι;») — ΝΕΟ: «αγκυρα ratings αγορας».
Ratings ομαδων που ΣΥΝΕΠΑΓΟΝΤΑΙ οι ΠΑΡΕΛΘΟΥΣΕΣ γραμμες κλεισιματος (Crown, δικαιη διαφορα χωρις γκανιοτα):
  κλεισιμο_j = h + r_γηπ − r_φιλ, ridge προς prior, φθινον βαρος. Walk-forward: για αγωνα της ημερας d χρησιμοποιουνται ΜΟΝΟ αγωνες με ημερα < d
  (καμια ματια στο μελλον· η γραμμη του ιδιου του αγωνα ΔΕΝ μπαινει). Prior σεζον Y = 0.8 × τελικα ratings αγορας της Y−1 (2020-21 φορτωνεται για το 2021-22).
  ΣΤΑΘΕΡΕΣ (οχι tuning): ημιζωη 60 μερες, ridge κ = 3 «αγωνες» προς το prior.
  Εκδοχη Α: ακατεργαστο κλεισιμο. Εκδοχη Β: κλεισιμο − (B2B 3.0 + 0.75·απουσιες K=2) των παλιων αγωνων (καθαρη δυναμη).
Αναμειξη: V_λ = (1−λ)·MG + λ·MR + 3·(B2A−B2H) + 0.75·LOSS2, λ ∈ {0, 0.25, 0.5, 0.75} (λ=0 = βαση: production + B2B + απουσιες). LOSO επιλογη λ με RMSE των αλλων 4.

ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο, ιδιο με NBA_TESTS_TODO): ΠΕΡΝΑ αν RMSE (LOSO) καλυτερο σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος edge ≥8% Οκτ-Δεκ
  οχι χειροτερο (Δ ≥ −1.5pp = θορυβος). Αναφερονται και RMSE αγων 1-15, ROI ολης σεζον, θετικες σεζον.
Εξοδος: t6_anchor_out.txt"""
import os, sys, json, collections
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
PROJ = os.path.dirname(SC); os.chdir(PROJ)
sys.stdout.reconfigure(encoding='utf-8')
from t_common import load, side_pick, settle, np
import pandas as pd
from statistics import NormalDist
nd = NormalDist()
D = load()
MG, OC, S, EV, ACT, SIG, G, GN = D['MG'], D['OC'], D['SEAS_G'], D['EV'], D['ACT'], D['SIG'], D['G'], D['GN']
ADJ = 3.0 * (D['B2A'] - D['B2H']) + 0.75 * D['LOSS2']
BASE = MG + ADJ
MON = G.date.dt.month.values; ODm = np.isin(MON, [10, 11, 12]); dD = G.date.values.astype('datetime64[D]')

# ---------- κλεισιμο 2020-21 (για prior του 2021-22): ιδια αντιστοιχιση με ablate/news_test ----------
CL = {i: d['c'][1] for i, d in OC.items()}
need = set()
S21 = json.load(open('nowgoal_nba/sched_20-21.json', encoding='utf-8')); need = {g['ngid'] for g in S21}
ODD = {}
for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ngid'] in need and r['t'] == 21:
        ODD[r['ngid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
keyd = collections.defaultdict(list)
for i in np.where(S == 2021)[0]: keyd[(int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
n21 = 0
for g in S21:
    if g['hs'] is None or not ODD.get(g['ngid']): continue
    ts = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
    us = ts.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize(); tip = ts.timestamp()
    cand = [i for i in keyd.get((g['hs'], g['as_']), []) if abs((G.date.values[i] - np.datetime64(us)) / np.timedelta64(1, 'D')) <= 1]; sw = False
    if not cand: cand = [i for i in keyd.get((g['as_'], g['hs']), []) if abs((G.date.values[i] - np.datetime64(us)) / np.timedelta64(1, 'D')) <= 1]; sw = True
    if len(cand) != 1: continue
    rows = [x for x in ODD[g['ngid']] if x[0] + 8 * 3600 <= tip + 900]
    if not rows: continue
    x = rows[-1]; L = -x[1] * (-1 if sw else 1); oh, oa = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])
    ph = (1 / oh) / (1 / oh + 1 / oa); CL[cand[0]] = -L + SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)); n21 += 1
print(f'κλεισιματα: {len(CL)} (εκ των οποιων 2020-21: {n21})')

HL, KAP = 60.0, 3.0
def fit(rows, prior, teams):
    """rows: (age_days, home, away, y). Ridge προς prior, ελευθερο h (μικρο ridge προς 2.0)."""
    T = {t: k for k, t in enumerate(teams)}; n = len(teams)
    A = np.zeros((n + 1, n + 1)); b = np.zeros(n + 1)
    for age, h, a, y in rows:
        w = 0.5 ** (age / HL); x = np.zeros(n + 1); x[T[h]] = 1; x[T[a]] = -1; x[n] = 1
        A += w * np.outer(x, x); b += w * x * y
    for t, k in T.items(): A[k, k] += KAP; b[k] += KAP * prior.get(t, 0.0)
    A[n, n] += 1.0; b[n] += 2.0
    sol = np.linalg.solve(A, b); r = {t: sol[k] for t, k in T.items()}; m = np.mean(list(r.values()))
    return {t: v - m for t, v in r.items()}, sol[n]

def market_ratings(clean):
    MR = np.full(len(G), np.nan); prior = {}
    for Y in sorted(set(S)):
        idx = np.where(S == Y)[0]; teams = sorted(set(G.home.values[idx]) | set(G.away.values[idx]))
        days = sorted(set(dD[idx])); hist = []
        bydays = collections.defaultdict(list)
        for i in idx: bydays[dD[i]].append(i)
        for d in days:
            rows = [((d - dd).astype(int), h, a, y) for dd, h, a, y in hist]
            r, h0 = fit(rows, prior, teams)
            for i in bydays[d]: MR[i] = h0 + r[G.home.values[i]] - r[G.away.values[i]]
            for i in bydays[d]:
                if i in CL: hist.append((d, G.home.values[i], G.away.values[i], CL[i] - (ADJ[i] if clean else 0.0)))
        last = days[-1] + np.timedelta64(1, 'D')
        rf, _ = fit([((last - dd).astype(int), h, a, y) for dd, h, a, y in hist], prior, teams)
        prior = {t: 0.8 * v for t, v in rf.items()}
    return MR

def rm(v, ys, msk=None):
    m = np.isin(S, ys) & np.isfinite(v) & (np.ones(len(G), bool) if msk is None else msk); return float(np.sqrt(np.mean((ACT - v)[m] ** 2)))
def roi(v, od=True):
    R = []
    for i, d in OC.items():
        if S[i] not in EV or (od and not ODm[i]) or not np.isfinite(v[i]): continue
        L, mk, o1, o2 = d['o']; s_, e, od_, p, pp = side_pick(v[i], L, o1, o2, SIG)
        if e >= .08: R.append((S[i], settle(ACT[i], L, s_, od_)[0]))
    u = np.array([x[1] for x in R]); ps = {Y: sum(x[1] for x in R if x[0] == Y) for Y in EV}
    return len(R), u.mean() * 100, u.sum(), ps
E15 = GN <= 15
OPN = np.full(len(G), np.nan)
for i, d in OC.items(): OPN[i] = d['o'][1]
print(f'αναφορα RMSE (5 σεζον): βαση {rm(BASE, EV):.3f} · αγων 1-15 {rm(BASE, EV, E15):.3f} · αγορα ανοιγματος {rm(OPN, EV):.3f} / 1-15 {rm(OPN, EV, E15):.3f}')

for clean, nm in ((False, 'Α ακατεργαστο κλεισιμο'), (True, 'Β κλεισιμο − B2B/απουσιες')):
    MR = market_ratings(clean)
    print(f'\n################ ΕΚΔΟΧΗ {nm} ################')
    print(f'  μονο ratings αγορας (+B2B/απουσιες): RMSE {rm(MR + ADJ, EV):.3f} · αγων 1-15 {rm(MR + ADJ, EV, E15):.3f}')
    print(f'  {"λ":>5s} | RMSE ολα | 1-15  | ανα σεζον {" ".join(str(Y) for Y in EV)}       | ROI Οκτ-Δεκ ≥8%         | ROI ολη ≥8%')
    VS = {}
    for lam in (0.0, 0.25, 0.5, 0.75):
        v = (1 - lam) * MG + lam * MR + ADJ; VS[lam] = v
        n1, r1, u1, p1 = roi(v); n2, r2, u2, p2 = roi(v, False)
        print(f'  {lam:5.2f} | {rm(v, EV):8.3f} | {rm(v, EV, E15):5.3f} | ' + ' '.join(f'{rm(v, [Y]):.3f}' for Y in EV)
              + f' | {n1:4d} {r1:+5.1f}% {sum(p1[Y] > 0 for Y in EV)}/5 | {n2:4d} {r2:+5.1f}% {sum(p2[Y] > 0 for Y in EV)}/5')
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        oth = [x for x in EV if x != Y]; lam = min(VS, key=lambda l: rm(VS[l], oth)); ch.append(lam)
        m = S == Y; held[m] = VS[lam][m]
    d = [rm(held, [Y]) - rm(BASE, [Y]) for Y in EV]; d15 = [rm(held, [Y], E15) - rm(BASE, [Y], E15) for Y in EV]
    n1, r1, u1, p1 = roi(held); n0, r0, u0, p0 = roi(BASE); n2, r2, u2, p2 = roi(held, False); n3, r3, u3, p3 = roi(BASE, False)
    ok = sum(x < 0 for x in d) >= 4 and (r1 - r0) >= -1.5
    print(f'  LOSO λ ανα σεζον {ch}')
    print(f'    RMSE {rm(BASE, EV):.3f} → {rm(held, EV):.3f} · ανα σεζον ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5')
    print(f'    RMSE αγων 1-15 {rm(BASE, EV, E15):.3f} → {rm(held, EV, E15):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d15) + f' → {sum(x < 0 for x in d15)}/5')
    print(f'    ROI Οκτ-Δεκ: βαση {n0} {r0:+.1f}% ({sum(p0[Y] > 0 for Y in EV)}/5) → {n1} {r1:+.1f}% ({sum(p1[Y] > 0 for Y in EV)}/5) · ανα σεζον ' + ' '.join(f'{p1[Y]:+.1f}' for Y in EV))
    print(f'    ROI ολη:     βαση {n3} {r3:+.1f}% ({sum(p3[Y] > 0 for Y in EV)}/5) → {n2} {r2:+.1f}% ({sum(p2[Y] > 0 for Y in EV)}/5)')
    print(f'    → ΚΡΙΤΗΡΙΟ: {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"} (ΔROI Οκτ-Δεκ {r1 - r0:+.2f}pp · μοναδες {u0:+.1f} → {u1:+.1f})')
