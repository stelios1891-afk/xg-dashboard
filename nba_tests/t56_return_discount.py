# -*- coding: utf-8 -*-
"""t56_return_discount.py — ΕΚΠΤΩΣΗ ΕΠΙΣΤΡΟΦΗΣ ΣΤΟ ΜΟΝΤΕΛΟ (22/10/2026, Στελιος «τρεξε αυτο το τεστ για αρχη»).
Ερωτημα: οταν ενας παικτης ρολου επιστρεφει μετα απο απουσια, το live μοντελο τον μετραει με ΠΛΗΡΗ αξια — υπερεκτιμα την ομαδα του;
ΒΑΣΗ: _t29_games.csv (ανοιγμα Crown, live αντιγραφο t22: μηχανη + απουσιες απο την επισημη αναφορα ως το ανοιγμα, μονο Out) · 5 σεζον.
ΕΠΙΣΤΡΕΦΩΝ (ΜΟΝΟ με οσα ξερουμε στο ανοιγμα): παικτης ρολου (μ.ο. ≥20′ στα 10 τελευταια του ματς της σεζον για την ομαδα), ελειψε απο το
  αμεσως προηγουμενο ματς (ή ματς) της ομαδας, και στην αναφορα του ανοιγματος ΔΕΝ ειναι Out. Βαρος w = πιθανοτητα να παιξει
  (1 − πιθανοτητα απουσιας ανα κατασταση & ρολο, οπως το live: χωρις κατασταση/Available → 1).
  κοστος = 0.75·(αξια+2)·λεπτα/48 (live) · RET = Σ φιλοξ w·κοστος − Σ γηπ w·κοστος (+ = καλο για τη γηπεδουχο οταν «κοβουμε» τους επιστρεφοντες)
ΕΚΔΟΧΗ: προβλεψη = μοντελο + δ·RET, δ = ποσοστο της αξιας που ΔΕΝ αποδιδει στο 1ο ματς (δ ∈ {0, .25, .5, .75, 1}, και ελευθερο δ).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (γραφτηκαν πριν το τρεξιμο): ΠΕΡΝΑ αν, LOSO 5 σεζον (δ επιλεγεται απο τις 4 με RMSE):
  RMSE καλυτερο απο δ=0 σε ≥4/5 ΚΑΙ μοναδες picks χαντικαπ ≥8% στο ανοιγμα ≥ δ=0 ΚΑΙ θετικες σεζον ≥4/5 ΚΑΙ ΛΟΓΙΚΗ 0 ≤ δ ≤ 1 σε ολα τα LOSO.
  Περιγραφικα: συντελεστης (πραγμ − μοντελο) & (πραγμ − αγορα) πανω στο RET ανα σεζον · ανα διαρκεια απουσιας (1 / 2-4 / 5+ ματς).
Εξοδος: t56_return_discount_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas')
G, SEAS_G, dD, SER, SHIFT, A2, mins, value, status_at, REP_BY, ACT = g['G'], g['SEAS_G'], g['dD'], g['SER'], g['SHIFT'], g['A2'], g['mins'], g['value'], g['status_at'], g['REP_BY'], g['ACT']
K2P = g['K2P']
from statistics import NormalDist
N_ = NormalDist()
PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
        'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}
def p_out(stt, m): return PROB['star' if m >= 30 else ('starter' if m >= 20 else 'role')].get(stt, 0.0)
X = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
# ---- εμφανισεις παικτων & προγραμμα ομαδων ----
APP = collections.defaultdict(list); KEY = {}
for r in A2.itertuples(index=False): APP[(r.pid, r.team, int(r.s))].append(r.dd); KEY[r.pid] = r.k
for k in APP: APP[k] = sorted(set(APP[k]))
ROST = collections.defaultdict(set)
BYP = collections.defaultdict(list)
for (pid, t, s), v in APP.items(): BYP[(pid, s)].append((t, v))
OTHER = {(pid, t, s): sorted(x for t2, v2 in BYP[(pid, s)] if t2 != t for x in v2) for (pid, t, s) in APP}
for (pid, t, s) in APP: ROST[(t, s)].add(pid)
TG = collections.defaultdict(list)
for i in range(len(G)):
    s = int(SEAS_G[i]); TG[(G.home.values[i], s)].append(dD[i]); TG[(G.away.values[i], s)].append(dD[i])
for k in TG: TG[k] = sorted(set(TG[k]))
def opening_ts(i):
    sw, tip, r21, _ = SER[i]; rr = sorted(x[0] + SHIFT for x in r21); rr = [x for x in rr if x <= tip + 900]
    return rr[0] if rr else None
def returners(t, s, d, tau):
    games = [x for x in TG[(t, s)] if x < d]
    if not games: return 0.0, []
    prev = games[-1]; st = status_at(t, d, tau); tot = 0.0; det = []
    for pid in ROST[(t, s)]:
        ap = [x for x in APP[(pid, t, s)] if x < d]
        if not ap or ap[-1] >= prev: continue                      # επαιξε στο προηγουμενο ματς → οχι επιστροφη
        if any(ap[-1] < x < d for x in OTHER.get((pid, t, s), ())): continue   # επαιξε για ΑΛΛΗ ομαδα στο μεταξυ → μεταγραφη
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        k_missed = sum(1 for x in games if x > ap[-1])
        if k_missed >= 2 and not any(kk == KEY.get(pid) for x in games if x > ap[-1] for ep, kk, _ in REP_BY.get((t, x), ())): continue   # ελειπε χωρις να ειναι ποτε στην αναφορα → εκτος ρόστερ
        stt = st.get(KEY.get(pid))
        if stt == 'Out': continue                                  # το live τον εχει ηδη απωντα
        if CLEAN and stt is None and k_missed >= 2: continue      # 22/10 ελεγχος t57d: χωρις κατασταση + ελειψε ≥2 = εκτος ροτασιον/ροστερ (95% δεν παιζουν), οχι επιστροφη
        w = 1.0 - p_out(stt, m)
        if w <= 0: continue
        c = 0.75 * (value(pid, s - 1) + 2.0) * m / 48 * w; tot += c; det.append((k_missed, c, pid, stt, m))
    return tot, det
GI = {(str(dD[j])[:10], G.home.values[j]): j for j in range(len(G))}
def abs_P(t, d, s, tau):
    c = 0.0
    for k, stt in status_at(t, d, tau).items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        c += p_out(stt, m) * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
    return c
BASE = os.environ.get('T56_BASE', 'P'); CLEAN = os.environ.get('T56_CLEAN') == '1'
rows = []; miss = 0
for r in X.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home))
    if i is None or i not in SER: miss += 1; continue
    tau = opening_ts(i)
    if abs(ACT[i] - r.act) > 0.5: miss += 1; continue
    if tau is None: continue
    d = dD[i]; s = int(r.sea)
    ch, dh = returners(r.home, s, d, tau); ca, da = returners(r.away, s, d, tau)
    kk = [x[0] for x in dh + da]
    rows.append(dict(sea=s, m=(r.m0 - abs_P(r.home, d, s, tau) + abs_P(r.away, d, s, tau)) if BASE == 'P' else r.m, sts=sorted({(x[3] or '—') for x in dh + da}), L=r.L, oh=r.oh, oa=r.oa, fair=r.fair, act=r.act, RET=ca - ch, nret=len(kk), date=str(d), home=r.home, away=r.away, det=[(r.home,) + x for x in dh] + [(r.away,) + x for x in da], kmin=(min(kk) if kk else np.nan), kmax=(max(kk) if kk else np.nan)))
D = pd.DataFrame(rows); SE = sorted(D.sea.unique()); ys = D.sea.values
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'ΒΑΣΗ: {"σημερινο live (Out + Doubtful/Questionable/Probable με πιθανοτητα)" if BASE == "P" else "μονο Out (παλιο)"}')
P(f'ματς {len(D)} (χωρις αντιστοιχιση {miss}) · με τουλαχιστον 1 επιστρεφοντα {int((D.nret > 0).sum())} ({100 * (D.nret > 0).mean():.0f}%) · μεσο |RET| οπου υπαρχει {D.RET[D.nret > 0].abs().mean():.2f} π.')
NM = dict(zip(A2.pid, A2.PLAYER_NAME))
P('ελεγχος — 4 ματς με το μεγαλυτερο |RET|:')
for r in D.reindex(D.RET.abs().sort_values(ascending=False).index[:4]).itertuples(index=False):
    P(f'  {r.date} {r.away}@{r.home} · RET {r.RET:+.2f} · μοντελο {r.m:+.1f} · αγορα {r.fair:+.1f} · πραγμ {r.act:+.0f} · ' + '; '.join(f'{t} {NM.get(pid, pid)} (ελειψε {k}, {m:.0f}′, {stt or "—"}, {c:.2f})' for t, k, c, pid, stt, m in r.det))
# ---- περιγραφικα ----
def coef(x, y):
    A = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(A, y, rcond=None)[0]; r = y - A @ b
    se = np.sqrt(np.sum(r ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return b[1], se
M = D[D.nret > 0]
b, se = coef(M.RET.values, (M.act - M.m).values); bm, sem = coef(M.RET.values, (M.act - M.fair).values)
P(f'(πραγμ − μοντελο) πανω στο RET: {b:+.2f} ± {se:.2f}  (= δ που ταιριαζει· 0 = το μοντελο μετραει σωστα τους επιστρεφοντες, 1 = δεν αποδιδουν τιποτα)')
P(f'(πραγμ − αγορα)  πανω στο RET: {bm:+.2f} ± {sem:.2f}  (τι κανει η αγορα)')
P('  ανα σεζον (μοντελο): ' + ' · '.join(f'{s % 100}: {coef(M[M.sea == s].RET.values, (M[M.sea == s].act - M[M.sea == s].m).values)[0]:+.2f}' for s in SE))
for lab, mk in (('απουσια 1 ματς', M.kmax <= 1), ('2-4 ματς', (M.kmax >= 2) & (M.kmax <= 4)), ('5+ ματς', M.kmax >= 5)):
    x = M[mk]
    if len(x) > 30: c_, s_ = coef(x.RET.values, (x.act - x.m).values); P(f'  {lab:14s} n {len(x):4d} · δ {c_:+.2f} ± {s_:.2f}')
for lab in ('—', 'Probable', 'Questionable'):
    x = M[M.sts.map(lambda v: v == [lab])]
    if len(x) > 30: c_, s_ = coef(x.RET.values, (x.act - x.m).values); P(f'  μονο «{lab}» n {len(x):4d} · δ {c_:+.2f} ± {s_:.2f}')
# ---- LOSO ----
SIG = 13.5
def cover(m, L):
    if abs(L - round(L)) < 1e-9: pw = 1 - N_.cdf((-L + .5 - m) / SIG); pl = N_.cdf((-L - .5 - m) / SIG); return pw, 1 - pw - pl, pl
    pw = 1 - N_.cdf((-L - m) / SIG); return pw, 0.0, 1 - pw
def picks(pred):
    U = collections.defaultdict(list)
    for r, mp in zip(D.itertuples(index=False), pred):
        pw, pp, pl = cover(mp, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; U[r.sea].append((od - 1) if x > 0 else (0.0 if x == 0 else -1.0))
    return U
rm = lambda pred, s: float(np.sqrt(np.mean((D.act.values[ys == s] - pred[ys == s]) ** 2)))
GRID = (0.0, .25, .5, .75, 1.0)
held = np.zeros(len(D)); chosen = []; held_free = np.zeros(len(D)); free = []
for s in SE:
    tr = ys != s
    best = min(GRID, key=lambda dd: np.mean((D.act.values[tr] - (D.m.values[tr] + dd * D.RET.values[tr])) ** 2)); chosen.append(best)
    held[ys == s] = D.m.values[ys == s] + best * D.RET.values[ys == s]
    trm = tr & (D.nret.values > 0); fb = coef(D.RET.values[trm], (D.act.values[trm] - D.m.values[trm]))[0]; free.append(fb)
    held_free[ys == s] = D.m.values[ys == s] + fb * D.RET.values[ys == s]
U0, U1, U2 = picks(D.m.values), picks(held), picks(held_free)
def cell(U):
    u = [x for v in U.values() for x in v]; return f"{100 * np.mean(u):+5.1f}% ({len(u)}, {sum(u):+6.1f}μ, θετ {sum(1 for s in SE if U[s] and sum(U[s]) > 0)}/5) · " + ' '.join(f'{s % 100}:{sum(U[s]):+.1f}' for s in SE)
d0 = [rm(D.m.values, s) for s in SE]
for nm, h, U, par in (('δ πλεγμα (LOSO)', held, U1, chosen), ('δ ελευθερο (LOSO)', held_free, U2, [round(f, 2) for f in free])):
    dd = [rm(h, s) - a for s, a in zip(SE, d0)]
    u, u0 = sum(x for v in U.values() for x in v), sum(x for v in U0.values() for x in v)
    ok = sum(x < 0 for x in dd) >= 4 and u >= u0 and sum(1 for s in SE if U[s] and sum(U[s]) > 0) >= 4 and all(0 <= p <= 1 for p in par)
    P(f'{nm:20s} δ ανα LOSO {par} · RMSE vs δ=0 ' + ' '.join(f'{x:+.3f}' for x in dd) + f' ({sum(x < 0 for x in dd)}/5) | picks {cell(U)} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"}')
P(f'{"δ=0 (live σημερα)":20s} picks {cell(U0)}')
open(os.path.join(SC, f't56_return_discount_{BASE}{"_clean" if CLEAN else ""}_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
