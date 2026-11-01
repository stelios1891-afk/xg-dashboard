# -*- coding: utf-8 -*-
"""el_onoff_mix_test.py — EUROLEAGUE ΣΥΝΟΛΑ: on/off απουσιων ως ΜΙΞΗ περσινου + φετινου (23/10/2026, Στελιος «μιξη οπως στο NBA»).
Βαση: el_absence_onoff_test.py εκδοχη W4 (μονο [δικα×z(onO), αντιπ.×z(onD)], ridge 1, LOSO E2021-25, picks συνολων ≥8% στο ανοιγμα).
ΙΔΙΑ με W4: ορισμος απουσιας (≥3/10 φετινα, λεπτα ≥10′, k 1-3 πληρες / 4-10 μισο), w, τυπος W4, picks. Αλλαζουν ΜΟΝΟ τα (onO, onD).
ON/OFF ΑΠΟ ΠΕΝΤΑΔΕΣ (el_pbp_stints.pkl, μονο Ευρωλιγκα): για παικτη p σε ομαδα t, σεζον S: μεσα = κομματια με p στο γηπεδο,
  εξω = ολα τα υπολοιπα κομματια της ομαδας t στη σεζον S (ως την ημερομηνια οπου ισχυει· οπως 3StepsBasket = συνολο ομαδας − μεσα).
  onO = 100·ΠΥ/κατ(μεσα) − 100·ΠΥ/κατ(εξω) · onD = 100·ΠΚ/κατ.αντ(μεσα) − (εξω).
  «Κομματι» (segment) = (σεζον, ομαδα)· δεκτο αν κατοχες μεσα ≥10 ΚΑΙ εξω ≥10 (μετα το βαρος ρ).
  Συνδυασμος segments: n_s = ρ_s / (1/κατ.μεσα + 1/κατ.εξω) (κατοχες επιθεσης, οπως το live) · τιμη = Σ n_s·diff_s / Σ n_s ·
  μαζεμα × N/(N+1500), N = Σ n_s.   (ρ_s = ρ για περσινη σεζον, 1 για φετινη.)
  Φετινα = μονο ματς με ημερομηνια < ματς-τεστ − 1ω (el_players.json utc).
ΕΚΔΟΧΕΣ: A0 = live (3StepsBasket περσινο, ακριβως W4 — ΠΡΕΠΕΙ 511 picks / +59.0μ, αλλιως STOP)
         A1 = δικο μας περσινο μονο (ολη η περσινη σεζον EL) · A2(ρ) ρ ∈ {0.25, 0.5, 1.0} · A3 = μονο φετινο ως το ματς.
         Νεος παικτης χωρις περσινα → μονο φετινα (αρχη 0).  Κλιμακα z: SD της εκδοχης στους απουσες με τιμη ≠ 0 (οπως W4: με προφιλ).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ το τρεξιμο):
  LOSO E2021-25: στο A2 το ρ επιλεγεται ΣΤΙΣ 4 σεζον εκπαιδευσης (ελαχιστο RMSE συνολου εντος δειγματος με τους bO/bD των 4)
    → εκδοχη «A2*» (το ρ μπορει να αλλαζει ανα σεζον). Τα A2(ρ) σταθερα = πληροφοριακα.
  Μια εκδοχη (A1, A2*, A3) ΑΝΤΙΚΑΘΙΣΤΑ το A0 αν: RMSE συνολου καλυτερο απο A0 σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ A0
    ΚΑΙ θετικες σεζον (ROI picks > 0) ≥4/5.
  Πινακες: RMSE/ΔRMSE vs A0 ανα σεζον · bO/bD (ολα & ανα σεζον, προσημα) · picks n/μ/ROI/ανα σεζον/θετικες · over/under · αγων. 1-10 vs 11+
    (11+ = RS 11+ και playoffs/PI/FF) · καλυψη (απουσες με τιμη ≠0) · A1↔A0 συσχετιση · 3 παραδειγματα.
Εξοδος: el_onoff_mix_test_out.txt · el_onoff_variants_alpha.pkl (dict εκδοχη → DataFrame ανα ματς)."""
import sys, io, contextlib, json, pickle, collections, math
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
G = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_onoff_test.py', encoding='utf-8').read().split("# ---- Ευρωλιγκα 2021-25 με live μοντελο")[0], G)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D, REC, NP, PL, TG, PH, NAME, profile, Phi = G['D'], G['REC'], G['NP'], G['PL'], G['TG'], G['PH'], G['NAME'], G['profile'], G['Phi']
SE = G['SE']; K_SHR = 1500.0
# ---- απουσες: ΑΚΡΙΒΩΣ ο κωδικας του W4, + pid/ομαδα ----
def absents(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v > 0); res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, 0) > 0: continue
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, 0) > 0: break
            k += 1
        h = [mn for t, mn in PH[pid] if t < ts - 3600][-10:]
        if not h or np.mean(h) < 10: continue
        w = np.mean(h) / 40 * (1.0 if k + 1 <= 3 else (.5 if k + 1 <= 10 else 0.0))
        if w <= 0: continue
        pr = profile(NAME[pid], int(sea[1:]))
        res.append(dict(pid=pid, team=team, sea=sea, ts=ts, w=w, A0=(pr['onO'], pr['onD']) if pr else (0.0, 0.0), A0has=pr is not None))
    return res
# ---- κωδικος ματς / φαση ----
CODE = {}
for k, g in PL.items():
    if not k.startswith('E'): continue
    CODE[(g['season'], g['hcode'], g['acode'], pd.Timestamp(g['utc']).strftime('%Y-%m-%d'))] = (g['code'], g['phase'], g['rnd'])
rows = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('t_new') is None or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); ah, aa = absents(sea, hc, ts), absents(sea, ac, ts)
    if ah is None or aa is None: continue
    cd = CODE.get((sea, hc, ac, t.strftime('%Y-%m-%d')))
    if cd is None: cd = next((v for (s_, h_, a_, dd), v in CODE.items() if s_ == sea and h_ == hc and a_ == ac
                              and abs((pd.Timestamp(dd) - t.normalize()).days) <= 1), (None, None, None))
    rows.append(dict(y=sea, hc=hc, ac=ac, t=t, code=cd[0], phase=cd[1], rnd=cd[2], hs=float(D.hs.values[pos]), as_=float(D.as_.values[pos]),
                     T=float(NP[key]['t_new']), M=float(NP[key]['h_new']), ah=ah, aa=aa, op=d_['open'], cl=d_[0]))
P(f'Ευρωλιγκα 2021-25: ματς {len(rows)} (χωρις κωδικο ματς: {sum(r["code"] is None for r in rows)})')
# ---- ΠΕΝΤΑΔΕΣ → ανα (σεζον, ομαδα): λιστα ματς (ts, συνολο ομαδας, μεσα ανα παικτη) ----
C = pickle.load(open('el_pbp_stints.pkl', 'rb'))
TEAMG = collections.defaultdict(list); PTEAMS = collections.defaultdict(set); badteam = 0
for k, g in C.items():
    pg = PL.get(k)
    if pg is None: continue
    ts = pd.Timestamp(pg['utc']).timestamp(); s = g['season']
    for side, code_ in ((0, pg['hcode']), (1, pg['acode'])):
        tot = np.zeros(4); on = collections.defaultdict(lambda: np.zeros(4))   # [ΠΥ, κατ. υπερ, ΠΚ, κατ. κατα]
        for st in g['stints']:
            five = st[side]; pf, pa = st[2 + side], st[3 - side]; qf, qa = st[4 + side], st[5 - side]
            v = np.array([pf, qf, pa, qa], float); tot += v
            for pid in five: on[pid] += v
        if tot[1] <= 0: badteam += 1; continue
        TEAMG[(s, code_)].append((ts, tot, dict(on)))
        for pid in on: PTEAMS[(pid, s)].add(code_)
for v in TEAMG.values(): v.sort(key=lambda x: x[0])
P(f'πενταδες: ομαδες-σεζον {len(TEAMG)} · ματς-ομαδες χωρις κατοχες {badteam}')
def seg(pid, s, team, cut):
    """(diff_O, diff_D, n) για ενα segment· cut = None → ολη η σεζον."""
    tot = np.zeros(4); on = np.zeros(4); seen = False
    for ts, tt, o in TEAMG.get((s, team), []):
        if cut is not None and ts >= cut: break
        tot += tt
        if pid in o: on += o[pid]; seen = True
    if not seen: return None
    off = tot - on
    if on[1] < 10 or off[1] < 10 or on[3] < 10 or off[3] < 10: return None
    dO = 100 * on[0] / on[1] - 100 * off[0] / off[1]; dD = 100 * on[2] / on[3] - 100 * off[2] / off[3]
    return dO, dD, 1 / (1 / on[1] + 1 / off[1])
SEGC = {}
def segs(pid, s, cut):
    kk = (pid, s, cut)
    if kk not in SEGC: SEGC[kk] = [x for tm in sorted(PTEAMS.get((pid, s), ())) for x in [seg(pid, s, tm, cut)] if x is not None]
    return SEGC[kk]
def prevs(s): return f'E{int(s[1:]) - 1}'
def value(pid, s, ts, rho_prev, use_cur):
    L = [(a, b, rho_prev * n) for a, b, n in segs(pid, prevs(s), None)] if rho_prev > 0 else []
    if use_cur: L += segs(pid, s, ts - 3600)
    N = sum(x[2] for x in L)
    if N <= 0: return (0.0, 0.0), False
    sh = N / (N + K_SHR)
    return (sh * sum(a * n for a, _, n in L) / N, sh * sum(b * n for _, b, n in L) / N), True
VARS = {'A0': None, 'A1': (1.0, False), 'A2 ρ0.25': (0.25, True), 'A2 ρ0.5': (0.5, True), 'A2 ρ1.0': (1.0, True), 'A3': (0.0, True)}
RHOS = {'A2 ρ0.25': .25, 'A2 ρ0.5': .5, 'A2 ρ1.0': 1.0}
for r in rows:
    for p in r['ah'] + r['aa']:
        p['V'] = {'A0': (p['A0'], p['A0has'])}
        for nm, par in VARS.items():
            if par is not None: p['V'][nm] = value(p['pid'], p['sea'], p['ts'], *par)
allp = [p for r in rows for p in r['ah'] + r['aa']]
SD = {}
for nm in VARS:
    has = [p['V'][nm][0] for p in allp if p['V'][nm][1] and (p['V'][nm][0] != (0.0, 0.0))]
    SD[nm] = (np.std([x[0] for x in has]), np.std([x[1] for x in has]))
P(''); P('## ΚΑΛΥΨΗ & ΚΛΙΜΑΚΑ (απουσες E2021-25, ' + f'{len(allp)} απουσιες-ματς)')
P('  εκδοχη     | απουσες με τιμη ≠0 | SD onO (ποντ./100 κατ., μετα μαζεμα) | SD onD')
for nm in VARS:
    c = sum(1 for p in allp if p['V'][nm][1] and p['V'][nm][0] != (0.0, 0.0))
    P(f'  {nm:10s} | {c:5d} ({c / len(allp):4.0%})       | {SD[nm][0]:.2f} | {SD[nm][1]:.2f}')
# ---- A1 ↔ A0 (ιδια περσινη σεζον, κοινοι παικτες· μοναδικοι παικτης-σεζον) ----
U = {}
for p in allp:
    if p['V']['A0'][1] and p['V']['A1'][1]: U[(p['pid'], p['sea'])] = (p['V']['A0'][0], p['V']['A1'][0])
a0 = np.array([v[0] for v in U.values()]); a1 = np.array([v[1] for v in U.values()])
P(''); P(f'## A1 (δικο μας, μονο EL) ↔ A0 (3StepsBasket, EL+EuroCup): κοινοι παικτες-σεζον {len(U)}')
P(f'  συσχετιση onO {np.corrcoef(a0[:, 0], a1[:, 0])[0, 1]:+.2f} · onD {np.corrcoef(a0[:, 1], a1[:, 1])[0, 1]:+.2f} · '
  f'κλιση A1 πανω στο A0: onO {np.polyfit(a0[:, 0], a1[:, 0], 1)[0]:.2f} · onD {np.polyfit(a0[:, 1], a1[:, 1], 1)[0]:.2f} · '
  f'SD A0 {a0[:, 0].std():.2f}/{a0[:, 1].std():.2f} · SD A1 {a1[:, 0].std():.2f}/{a1[:, 1].std():.2f}')
# ---- χαρακτηριστικα W4 ανα εκδοχη ----
YH = np.array([r['hs'] - (r['T'] + r['M']) / 2 for r in rows]); YA = np.array([r['as_'] - (r['T'] - r['M']) / 2 for r in rows]); YT = YH + YA
ys = np.array([r['y'] for r in rows]); ALL = np.ones(len(rows), bool)
def feats(nm):
    sO, sD = SD[nm]
    f = lambda own, opp: [sum(p['w'] * p['V'][nm][0][0] / sO for p in own), sum(p['w'] * p['V'][nm][0][1] / sD for p in opp)]
    return np.array([f(r['ah'], r['aa']) for r in rows]), np.array([f(r['aa'], r['ah']) for r in rows])
X = {nm: feats(nm) for nm in VARS}
def fit(nm, tr):
    XH, XA = X[nm]; Xm = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(Xm.T @ Xm + 1.0 * np.eye(2), Xm.T @ y)
def adj(nm, b, m): XH, XA = X[nm]; return XH[m] @ b + XA[m] @ b
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
HELD, COEF, RHO_SEL = {}, {}, {}
for nm in VARS:
    h = np.zeros(len(rows))
    for Yr in SE: m = ys == Yr; h[m] = adj(nm, fit(nm, ~m), m)
    HELD[nm] = h; COEF[nm] = (fit(nm, ALL), {s: fit(nm, ys == s) for s in SE})
h = np.zeros(len(rows))
for Yr in SE:
    m = ys == Yr; tr = ~m; best = None
    for nm in RHOS:
        b = fit(nm, tr); e = float(np.sqrt(np.mean((YT[tr] - adj(nm, b, tr)) ** 2)))
        if best is None or e < best[0]: best = (e, nm, b)
    RHO_SEL[Yr] = RHOS[best[1]]; h[m] = adj(best[1], best[2], m)
HELD['A2*'] = h
ORDER = ['A0', 'A1', 'A2*', 'A3', 'A2 ρ0.25', 'A2 ρ0.5', 'A2 ρ1.0']
P(''); P('## ρ που επιλεγει το LOSO για το A2* (στις 4 σεζον εκπαιδευσης): ' + ' · '.join(f'{s}: ρ {RHO_SEL[s]}' for s in SE))
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ bO (δικα×z(onO)) / bD (αντιπ.×z(onD)) — ποντοι ομαδας ανα 40′ απουσιας ανα 1 SD· αναμενομενο < 0')
for nm in VARS:
    b, per = COEF[nm]
    P(f'  {nm:10s} bO {b[0]:+.2f} [' + ' '.join(f'{s[-2:]}:{per[s][0]:+.2f}' for s in SE) + f'] <0 σε {sum(per[s][0] < 0 for s in SE)}/5 · '
      f'bD {b[1]:+.2f} [' + ' '.join(f'{s[-2:]}:{per[s][1]:+.2f}' for s in SE) + f'] <0 σε {sum(per[s][1] < 0 for s in SE)}/5')
P(''); P(f'## LOSO RMSE συνολου (ποντοι· χωρις διορθωση {rmse(YT, ALL):.3f}) και ΔRMSE vs A0 ανα σεζον (− = καλυτερο απο A0)')
P('  εκδοχη     | RMSE ολα | ' + ' | '.join(f'{s} RMSE (Δ)' for s in SE) + ' | καλυτερο απο A0')
BETTER = {}
for nm in ORDER:
    hh = HELD[nm]; d = [rmse(YT - hh, ys == s) - rmse(YT - HELD['A0'], ys == s) for s in SE]; BETTER[nm] = sum(x < 0 for x in d)
    P(f'  {nm:10s} | {rmse(YT - hh, ALL):.3f}   | ' + ' | '.join(f'{rmse(YT - hh, ys == s):.3f} ({x:+.3f})' for s, x in zip(SE, d)) + f' | {BETTER[nm]}/5')
# ---- picks (ιδιος κωδικας με W4 tpicks) + γραμμες ανα ματς ----
def tp(t, T_):
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7); return po, 1 - po - pu, pu
    po = 1 - Phi((T_ - t) / 16.7); return po, 0.0, 1 - po
def picks_df(a):
    R = []
    for r, x_ in zip(rows, a):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + x_, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        pk = e >= .08; x = (r['hs'] + r['as_'] - T_) * sd
        R.append(dict(season=r['y'], code=r['code'], home=r['hc'], away=r['ac'], t=r['t'], phase=r['phase'], rnd=r['rnd'],
                      pred_total=r['T'] + x_, base_total=r['T'], adj=x_, actual=r['hs'] + r['as_'], line=T_, odds_over=oo, odds_under=ou,
                      edge=e, pick=('over' if sd == 1 else 'under') if pk else None, pick_odds=od if pk else None,
                      units=(((od - 1) if x > 0 else (0 if x == 0 else -1)) if pk else 0.0),
                      clv_mv=((r['cl'][1] - o[1]) * sd) if pk else np.nan))
    return pd.DataFrame(R)
DF = {nm: picks_df(HELD[nm]) for nm in ORDER}
def summ(df):
    q = df[df.pick.notna()]; U_ = {s: q[q.season == s].units for s in SE}
    return len(q), q.units.sum(), (q.units.mean() * 100 if len(q) else np.nan), sum(1 for s in SE if len(U_[s]) and U_[s].mean() > 0), U_
P(''); P('## PICKS ΣΥΝΟΛΩΝ ≥8% στο ανοιγμα (μοναδες 1/pick, Crown)')
P('  εκδοχη     | picks | μοναδες | ROI    | θετ. σεζον | ' + ' | '.join(f'{s} n/μ' for s in SE) + ' | CLV (ποντοι γραμμης προς εμας)')
RES = {}
for nm in ORDER:
    n, u, roi, pos, U_ = summ(DF[nm]); RES[nm] = (n, u, roi, pos)
    P(f'  {nm:10s} | {n:5d} | {u:+7.1f} | {roi:+5.1f}% | {pos}/5        | ' + ' | '.join(f'{len(U_[s])}/{U_[s].sum():+.1f}' for s in SE)
      + f' | {DF[nm].clv_mv.mean():+.2f}')
n0, u0, _, _ = RES['A0']
if not (n0 == 511 and abs(u0 - 59.0) < 0.05):
    P(f'!!! A0 ΔΕΝ αναπαραγει το W4 (511 / +59.0): {n0} / {u0:+.1f} — STOP'); open('el_onoff_mix_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out)); sys.exit(1)
P('  (A0 αναπαραγει το W4: 511 picks / +59.0μ ✓)')
P(''); P('## OVER / UNDER χωριστα (picks · μοναδες · ROI)')
for nm in ORDER:
    q = DF[nm][DF[nm].pick.notna()]
    P(f'  {nm:10s} ' + ' · '.join(f'{sd_}: {len(q[q.pick == sd_]):3d} · {q[q.pick == sd_].units.sum():+6.1f}μ · {q[q.pick == sd_].units.mean() * 100:+5.1f}%' for sd_ in ('over', 'under')))
P(''); P('## ΑΓΩΝΙΣΤΙΚΕΣ 1-10 vs 11+ (11+ = κανονικη 11+ και playoffs/PI/FF) — picks · μοναδες · ROI')
for nm in ORDER:
    q = DF[nm][DF[nm].pick.notna()]; e = (q.phase == 'RS') & (q.rnd <= 10)
    P(f'  {nm:10s} 1-10: {e.sum():3d} · {q[e].units.sum():+6.1f}μ · {q[e].units.mean() * 100:+5.1f}%  |  11+: {(~e).sum():3d} · {q[~e].units.sum():+6.1f}μ · {q[~e].units.mean() * 100:+5.1f}%')
P(''); P('## ΚΡΙΤΗΡΙΑ (προ-δηλωμενα): RMSE καλυτερο απο A0 ≥4/5 · μοναδες ≥ A0 · θετικες σεζον ≥4/5')
for nm in ('A1', 'A2*', 'A3'):
    n, u, roi, pos = RES[nm]; c1, c2, c3 = BETTER[nm] >= 4, u >= u0, pos >= 4
    P(f'  {nm:5s} RMSE {BETTER[nm]}/5 {"✓" if c1 else "✗"} · μοναδες {u:+.1f} vs {u0:+.1f} {"✓" if c2 else "✗"} · θετικες {pos}/5 {"✓" if c3 else "✗"} → '
      + ('ΑΝΤΙΚΑΘΙΣΤΑ ΤΟ A0' if c1 and c2 and c3 else 'ΔΕΝ αντικαθιστα'))
# ---- ΠΑΡΑΔΕΙΓΜΑΤΑ ----
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ (onO/onD ποντοι ανα 100 κατοχες μετα το μαζεμα· επιδραση = ποντοι στο συνολο του ματς, συντελεστες ολων των σεζον)')
def effect(p, nm):
    b = COEF[nm][0]; v = p['V'][nm][0]; return p['w'] * (b[0] * v[0] / SD[nm][0] + b[1] * v[1] / SD[nm][1])
cand = []
for r in rows:
    for p in r['ah'] + r['aa']:
        if r['y'] not in ('E2024', 'E2025') or p['w'] < .5: continue
        pt = PTEAMS.get((p['pid'], prevs(p['sea'])), set())
        typ = 'νεος (χωρις περσινα EL)' if not pt and not p['A0has'] else ('αλλαξε ομαδα' if pt and p['team'] not in pt else ('σταθερος' if p['team'] in pt else None))
        if typ: cand.append((typ, p, r))
def pick_ex(typ, keyf):
    L = [c for c in cand if c[0] == typ]
    return max(L, key=keyf) if L else None
EX = [pick_ex('νεος (χωρις περσινα EL)', lambda c: (c[2]['rnd'] or 0) * (c[2]['phase'] == 'RS') + c[1]['w']),
      pick_ex('αλλαξε ομαδα', lambda c: c[1]['A0has'] * 100 + (c[2]['rnd'] or 0) * (c[2]['phase'] == 'RS')),
      pick_ex('σταθερος', lambda c: c[1]['w'] * 10 + abs(c[1]['V']['A1'][0][0]) + abs(c[1]['V']['A1'][0][1]))]
for c in EX:
    if c is None: continue
    typ, p, r = c
    P(f'  [{typ}] {NAME.get(p["pid"], p["pid"])} ({p["team"]}) · ματς {r["y"]} #{r["code"]} {r["hc"]}-{r["ac"]} {r["t"]:%Y-%m-%d} (αγων. {r["phase"]} {r["rnd"]}) · w {p["w"]:.2f}'
      f' · περσι ομαδες EL {sorted(PTEAMS.get((p["pid"], prevs(p["sea"])), set()))} · 3StepsBasket προφιλ: {"ναι" if p["A0has"] else "οχι"}')
    for nm in ['A0', 'A1', 'A2 ρ0.25', 'A2 ρ0.5', 'A2 ρ1.0', 'A3']:
        v = p['V'][nm][0]
        P(f'      {nm:9s} onO {v[0]:+6.2f} · onD {v[1]:+6.2f} · επιδραση στο συνολο {effect(p, nm):+5.2f} ποντοι')
    cs = segs(p['pid'], p['sea'], p['ts'] - 3600); ps = segs(p['pid'], prevs(p['sea']), None)
    P('      segments περσι: ' + '; '.join(f'diffO {a:+.1f} diffD {b:+.1f} n {n:.0f}' for a, b, n in ps) +
      ' · φετος ως το ματς: ' + '; '.join(f'diffO {a:+.1f} diffD {b:+.1f} n {n:.0f}' for a, b, n in cs))
P(''); P('## ΖΕΥΓΑΡΩΤΗ ΔΙΑΦΟΡΑ vs A0 (ανα ματς, 1563): μοναδες (± τυπ. σφαλμα) · ΔMSE συνολου (± τυπ. σφαλμα, ποντοι²)')
e0 = (YT - HELD['A0']) ** 2
for nm in ORDER[1:]:
    du = DF[nm].units.values - DF['A0'].units.values; de = (YT - HELD[nm]) ** 2 - e0
    P(f'  {nm:10s} Δμοναδες {du.sum():+6.1f} ± {du.std(ddof=1) * math.sqrt(len(du)):.1f} · ΔMSE {de.mean():+.3f} ± {de.std(ddof=1) / math.sqrt(len(de)):.3f}'
      f' · ματς με διαφορετικο pick {int((DF[nm].pick.fillna("-") != DF["A0"].pick.fillna("-")).sum())}')
pickle.dump({nm: DF[nm] for nm in ORDER}, open('el_onoff_variants_alpha.pkl', 'wb'))
P(''); P('pickle: el_onoff_variants_alpha.pkl · εκδοχες ' + ', '.join(ORDER))
open('el_onoff_mix_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
