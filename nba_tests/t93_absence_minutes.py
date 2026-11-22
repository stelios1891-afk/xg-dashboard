# -*- coding: utf-8 -*-
"""t93_absence_minutes.py — ΛΕΠΤΑ ΑΠΟΝΤΩΝ ΣΤΗΝ ΑΡΧΗ ΤΗΣ ΣΕΖΟΝ (25/10/2026, Στελιος «οκ φτιαξε το τεστ»).
Αφορμη: Duren 28′ + 10′ (τραυματισμος μεσα στο ματς) → μεσος 19′ < 20′ → το μοντελο τον αγνοει (περσι 28.3′).
ΠΛΑΙΣΙΟ: t22/t84 (αντιγραφο live χαντικαπ, τιμη Crown + επισημη αναφορα ιδια στιγμη, πιθανοτητες καταστασης οπως το live), ΑΝΟΙΓΜΑ.
ΕΚΔΟΧΕΣ λεπτων καθε αποντα (αφορα ΚΑΙ το οριο ≥20′ ΚΑΙ το κοστος 0.75·(αξια+2)·λεπτα/48):
  Α  live: μεσος ορος των (εως 10) φετινων ματς με την ομαδα
  Β/Γ/Δ μιξη: (n·φετινος + K·περσινος)/(n + K), K = 3 / 5 / 10 (περσινος = λεπτα/ματς πρσι, οποια ομαδα· αν δεν υπαρχει → φετινος)
  Ε  διαμεσος των φετινων (ενα κομμενο ματς δεν ριχνει τον αριθμο)
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): LOSO-επιλογη (σφαλμα) → σφαλμα καλυτερο απο Α σε ≥4/5 ΚΑΙ μοναδες & CLV οχι χειροτερα ΚΑΙ walk-forward οχι χειροτερο
  ΚΑΙ placebo < 5% · + ζευγαρωτη t, bootstrap, Οκτ-Δεκ, παραδειγματα.
Εξοδος: nba_tests/t93_absence_minutes_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't84_b2b_rest_expected.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα', None)")[0]
g = {'__file__': os.path.join(SC, 't84_b2b_rest_expected.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']
SER, SHIFT, SEAS_G, EV, REPS, VNO, G, dD, ACT = (g[x] for x in ('SER', 'SHIFT', 'SEAS_G', 'EV', 'REP_SEASONS', 'VNO', 'G', 'dD', 'ACT'))
status_at, K2P, HM, value, W_B, line_at, cover_, SIG_, A = (g[x] for x in ('status_at', 'K2P', 'HM', 'value', 'W_B', 'line_at', 'cover_', 'SIG_', 'g'))
A = A['A']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# περσινα λεπτα/ματς ανα παικτη (οποια ομαδα)
A2 = A[A.MIN > 0]; PREV = A2.groupby(['pid', 's']).MIN.mean().to_dict()
def mins_v(pid, t, s, d, ver):
    allg = [m for dd_, m in HM.get((pid, t, s), []) if dd_ < d]; h = allg[-10:]
    if not h: return None
    n = len(allg); cur = float(np.mean(h))                    # n = ΟΛΑ τα φετινα ματς (η μιξη σβηνει με τη σεζον) — διορθωση πριν την αναφορα
    if ver == 'Α': return cur
    if ver == 'Ε': return float(np.median(h))
    K = {'Β': 3, 'Γ': 5, 'Δ': 10}[ver]; pv = PREV.get((pid, s - 1))
    return cur if pv is None else (n * cur + K * float(pv)) / (n + K)
def cost(t, d, s, tau, ver, det=None):
    c = 0.0
    for k, (stt, rs) in status_at(t, d, tau).items():
        w = W_B.get(stt)
        if not w: continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins_v(pid, t, s, d, ver)
        if m is None or m < 20: continue
        cc = w * 0.75 * (value(pid, s - 1) + 2.0) * m / 48; c += cc
        if det is not None: det.append((k, stt, round(m, 1), round(cc, 2)))
    return c
VERS = ['Α', 'Β', 'Γ', 'Δ', 'Ε']
rows = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REPS or not np.isfinite(VNO[i]): continue
    rr = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rr = [x for x in rr if x[0] <= tip + 900]
    if not rr: continue
    tau = rr[0][0]; ln = line_at(rr, tau, sw); cl = line_at(rr, tip, sw)
    if not ln or not cl: continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    rec = dict(i=i, sea=s, date=str(d)[:10], mon=int(G.date.dt.month.values[i]), L=ln[0], oh=ln[1], oa=ln[2], fair=ln[3], cfair=cl[3], act=float(ACT[i]))
    for v in VERS: rec[v] = VNO[i] - cost(h, d, s, tau, v) + cost(a, d, s, tau, v)
    rows.append(rec)
X = pd.DataFrame(rows); ys = X.sea.values; SE = sorted(set(ys)); Y = X.act.values
day = pd.to_datetime(X.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
def picks(mu):
    u, c = np.zeros(len(X)), np.full(len(X), np.nan)
    for j, r in enumerate(X.itertuples(index=False)):
        pw, pp, pl = cover_(mu[j], r.L, SIG_); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; u[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c[j] = sd * (r.cfair - r.fair)
    return u, c
MU = {v: X[v].values for v in VERS}; U, CL = {}, {}
for v in VERS: U[v], CL[v] = picks(MU[v])
rm = lambda v, m: float(np.sqrt(np.mean((Y[m] - MU[v][m]) ** 2)))
od = X.mon.isin([10, 11, 12]).values
nm = {'Α': 'Α live (μεσος φετος)', 'Β': 'Β μιξη περσι K3', 'Γ': 'Γ μιξη περσι K5', 'Δ': 'Δ μιξη περσι K10', 'Ε': 'Ε διαμεσος φετος'}
P(f'ματς {len(X)} (ανοιγμα Crown, 5 σεζον) · διαφορετικη προβλεψη απο το live: ' + ' · '.join(f'{v} {int((np.abs(MU[v] - MU["Α"]) > 1e-6).sum())}' for v in VERS[1:]))
for v in VERS:
    P(f"  {nm[v]:22s} σφαλμα {rm(v, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(v, ys == s):.3f}' for s in SE) + f") · μοναδες {U[v].sum():+6.1f} (Οκτ-Δεκ {U[v][od].sum():+.1f}) · picks {int((U[v] != 0).sum())} · CLV {np.nanmean(CL[v]):+.2f}")
rng = np.random.default_rng(13)
P('\n=== vs live ===')
for v in VERS[1:]:
    bet = sum(rm(v, ys == s) < rm('Α', ys == s) for s in SE)
    dd = pd.Series((Y - MU['Α']) ** 2 - (Y - MU[v]) ** 2).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
    dw = pd.Series(U[v] - U['Α']).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(3000)])
    P(f'  {nm[v]:22s} καλυτερο {bet}/5 · ζευγαρωτη t {t:+.2f} · Δμοναδες {dw.sum():+.1f} (P {100 * (bs > 0).mean():.0f}%)')
sel = {s: min(VERS, key=lambda v: rm(v, ys != s)) for s in SE}
LM = np.zeros(len(X)); LU = np.zeros(len(X)); LC = np.full(len(X), np.nan)
for s in SE: m = ys == s; LM[m] = MU[sel[s]][m]; LU[m] = U[sel[s]][m]; LC[m] = CL[sel[s]][m]
bet = sum(np.sqrt(np.mean((Y - LM)[ys == s] ** 2)) < rm('Α', ys == s) for s in SE)
P(f"\nLOSO επιλογες: {' · '.join(f'{s % 100}:{sel[s]}' for s in SE)} · σφαλμα καλυτερο {bet}/5 · μοναδες {LU.sum():+.1f} vs {U['Α'].sum():+.1f} · CLV {np.nanmean(LC):+.2f} vs {np.nanmean(CL['Α']):+.2f}")
wf = [0.0, 0.0]; ch = []
for s in SE[2:]:
    prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = min(VERS, key=lambda v: rm(v, prev))
    wf[0] += U[b][cur].sum(); wf[1] += U['Α'][cur].sum(); ch.append(f'{s % 100}:{b}')
P(f"WALK-FORWARD: {' · '.join(ch)} → μοναδες {wf[0]:+.1f} vs live {wf[1]:+.1f}")
dlt = LM - MU['Α']; real = LU.sum() - U['Α'].sum(); res = []
for _ in range(300):
    perm = dlt.copy()
    for s in SE:
        m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
    res.append(picks(MU['Α'] + perm)[0].sum() - U['Α'].sum())
pl = 100 * (np.array(res) >= real).mean()
P(f'PLACEBO: πραγματικο {real:+.1f}μ · ≥ πραγματικο {pl:.1f}%')
ok = bet >= 4 and LU.sum() >= U['Α'].sum() and np.nanmean(LC) >= np.nanmean(CL['Α']) and wf[0] >= wf[1] and pl < 5
P(f'ΚΡΙΤΗΡΙΑ → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
# ---- παραδειγματα: απουσιες που το live αγνοει (<20′) αλλα η μιξη K5 μετραει ----
P('\n=== ΠΑΡΑΔΕΙΓΜΑΤΑ (2025-26, αρχη σεζον): live αγνοει, μιξη K5 μετραει ===')
shown = 0
for r in X[(X.sea == 2026) & (X.mon.isin([10, 11]))].itertuples(index=False):
    if shown >= 4: break
    i = r.i; s = 2026; d = dD[i]; tau = [[x[0] + SHIFT] for x in SER[i][2]][0][0]
    for t in (G.home.values[i], G.away.values[i]):
        da, dg = [], []; cost(t, d, s, tau, 'Α', da); cost(t, d, s, tau, 'Γ', dg)
        new = [x for x in dg if x[0] not in {y[0] for y in da}]
        if new:
            P(f"  {r.date} {G.away.values[i]}@{G.home.values[i]} · {t}: " + ' · '.join(f'{k} {st} λεπτα(μιξη) {m}′ κοστος {c} π.' for k, st, m, c in new)); shown += 1; break
open(os.path.join(SC, 't93_absence_minutes_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
