# -*- coding: utf-8 -*-
"""t58_minutes_blend.py — ΛΕΠΤΑ ΠΑΙΚΤΗ: ΣΤΑΔΙΑΚΗ ΜΙΞΗ ΦΕΤΙΝΩΝ ΜΕ ΠΕΡΣΙΝΑ (22/10/2026).
Ερωτημα: το live μετραει τα λεπτα ενος παικτη (για το κοστος απουσιας ΚΑΙ το οριο ρολου ≥20′) ως μ.ο. των φετινων ματς του με την ομαδα
  (τα τελευταια ≤10). Στην αρχη της σεζον = 1-3 ματς (θορυβος). Εκδοχη:
  λεπτα = (n·μ.ο._φετος + K·μ.ο._περσι)/(n+K) · n = φετινα ματς με την ομαδα (τα τελευταια ≤10) · μ.ο._περσι = μ.ο. λεπτων την προηγουμενη
  σεζον σε οποια ομαδα (μονο MIN>0) · αν δεν επαιξε περσι → μονο τα φετινα (live) · παικτης χωρις ΚΑΝΕΝΑ φετινο ματς με την ομαδα → δεν μετραει (live κανονας).
  Πλεγμα K ∈ {0 (=live), 2, 4, 8, 16}. Ολα τα αλλα οπως το live (abs_P του t56): w = p_out(κατασταση, ρολος), κοστος = w·0.75·(αξια+2)·λεπτα/48, μονο λεπτα ≥20.
ΒΑΣΗ: _t29_games.csv tau=ανοιγμα (m0, γραμμη Crown ανοιγματος), αντιστοιχιση με G μεσω (ημερομηνια, γηπεδουχος), ελεγχος ACT ≈ act (±0.5).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο):
  LOSO 5 σεζον (2022-2026): K επιλεγεται στις 4 σεζον με RMSE (act − μοντελο), εφαρμοζεται στην 5η. ΠΕΡΝΑ αν:
  RMSE καλυτερο απο K=0 σε ≥4/5 σεζον ΚΑΙ μοναδες picks (χαντικαπ ανοιγμα, edge ≥8%, σ=13.5) ≥ K=0 ΚΑΙ θετικες σεζον ≥4/5
  ΚΑΙ λογικη (επιλεγμενο K ≥0 και σταθερο: ολα τα LOSO K μεσα σε ±1 βημα πλεγματος).
  Περιγραφικα: τα ιδια ΜΟΝΟ για ματς οπου μια απο τις δυο ομαδες εχει παιξει <10 ματς φετος, και ανα σεζον μοναδες.
ΕΛΕΓΧΟΣ: 3 πραγματικα παραδειγματα (πρωτες 2 εβδομαδες, απων παικτης ρολου).
Εξοδος: t58_minutes_blend_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas')
G, SEAS_G, dD, SER, SHIFT, A2, HM, value, status_at, ACT, K2P = g['G'], g['SEAS_G'], g['dD'], g['SER'], g['SHIFT'], g['A2'], g['HM'], g['value'], g['status_at'], g['ACT'], g['K2P']
mins_live = g['mins']
from statistics import NormalDist
N_ = NormalDist()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
        'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}
def p_out(stt, m): return PROB['star' if m >= 30 else ('starter' if m >= 20 else 'role')].get(stt, 0.0)
KS = (0, 2, 4, 8, 16)
# ---- περσινος μ.ο. λεπτων (οποια ομαδα, MIN>0) ----
PREV = A2.groupby(['pid', 's']).MIN.agg(['mean', 'size'])
PREVM = {(int(p), int(s)): (float(m), int(n)) for (p, s), m, n in zip(PREV.index, PREV['mean'].values, PREV['size'].values)}
PTEAMS = A2.groupby(['pid', 's']).team.agg(lambda v: '/'.join(sorted(set(v))))
PTEAMS = {(int(p), int(s)): v for (p, s), v in PTEAMS.items()}
NM = dict(zip(A2.pid, A2.PLAYER_NAME))
NMS = {(int(p), int(s)): n for p, s, n in A2[['pid', 's', 'PLAYER_NAME']].drop_duplicates(['pid', 's']).itertuples(index=False)}
P(f'σεζον στα box: {sorted(int(x) for x in A2.s.unique())} · παικτες-σεζον με περσινο μ.ο.: {len(PREVM)}')
def mins_K(pid, t, s, d, K):
    h = [m for dd_, m in HM.get((pid, t, s), []) if dd_ < d][-10:]
    if not h: return None, 0, None, None
    mf = float(np.mean(h)); n = len(h); pv = PREVM.get((int(pid), int(s) - 1))
    if K == 0 or pv is None: return mf, n, mf, (pv[0] if pv else None)
    return (n * mf + K * pv[0]) / (n + K), n, mf, pv[0]
def abs_K(t, d, s, tau):
    c = np.zeros(len(KS)); det = []
    for k, stt in status_at(t, d, tau).items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        if p_out(stt, 0) == 0 and p_out(stt, 30) == 0: continue
        row = []
        for j, K in enumerate(KS):
            m, n, mf, pv = mins_K(pid, t, s, d, K)
            if m is None: row = None; break
            cc = p_out(stt, m) * 0.75 * (value(pid, s - 1) + 2.0) * m / 48 if m >= 20 else 0.0
            c[j] += cc; row.append((m, cc))
        if row is None: continue
        det.append((t, pid, stt, n, mf, pv, row))
    return c, det
def opening_ts(i):
    sw, tip, r21, _ = SER[i]; rr = sorted(x[0] + SHIFT for x in r21); rr = [x for x in rr if x <= tip + 900]
    return rr[0] if rr else None
TG = collections.defaultdict(list)
for i in range(len(G)):
    s = int(SEAS_G[i]); TG[(G.home.values[i], s)].append(dD[i]); TG[(G.away.values[i], s)].append(dD[i])
for k in TG: TG[k] = sorted(set(TG[k]))
FIRST = {k: v[0] for k, v in TG.items()}
GI = {(str(dD[j])[:10], G.home.values[j]): j for j in range(len(G))}
X = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
rows = []; miss = 0; notau = 0; DET = []
for r in X.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home))
    if i is None or i not in SER: miss += 1; continue
    if abs(ACT[i] - r.act) > 0.5: miss += 1; continue
    tau = opening_ts(i)
    if tau is None: notau += 1; continue
    d = dD[i]; s = int(r.sea)
    ch, dh = abs_K(r.home, d, s, tau); ca, da = abs_K(r.away, d, s, tau)
    gp = min(sum(1 for x in TG[(r.home, s)] if x < d), sum(1 for x in TG[(r.away, s)] if x < d))
    day = min(int((d - FIRST[(r.home, s)]) / np.timedelta64(1, 'D')), int((d - FIRST[(r.away, s)]) / np.timedelta64(1, 'D')))
    rec = dict(sea=s, L=r.L, oh=r.oh, oa=r.oa, fair=r.fair, act=r.act, gp=gp, day=day, date=str(d)[:10], home=r.home, away=r.away, raw=r.m0)
    for j, K in enumerate(KS): rec[f'm{K}'] = r.m0 - ch[j] + ca[j]
    rows.append(rec)
    for x in dh + da: DET.append((str(d)[:10], r.away + '@' + r.home, s, day) + x)
D = pd.DataFrame(rows); SE = sorted(D.sea.unique()); ys = D.sea.values
P(f'ματς {len(D)} (χωρις αντιστοιχιση/ACT {miss}, χωρις χρονο ανοιγματος {notau}) · ματς με ομαδα <10 φετινα ματς: {int((D.gp < 10).sum())}')
# ελεγχος: K=0 πρεπει να ταυτιζεται με το live mins
chk = 0; bad = 0
for (dt_, mt, s, day, t, pid, stt, n, mf, pv, row) in DET[:3000]:
    ml = mins_live(pid, t, s, np.datetime64(dt_, 'D')); chk += 1
    if ml is None or abs(ml - row[0][0]) > 1e-6: bad += 1
P(f'ελεγχος K=0 = live λεπτα: {chk - bad}/{chk} ιδια')
# ---- ελεγχος παραδειγματων ----
P(''); P('ΠΑΡΑΔΕΙΓΜΑΤΑ (πρωτες 2 εβδομαδες, απων/αμφιβολος παικτης ρολου, με περσινα λεπτα):')
cand = [x for x in DET if x[3] <= 14 and x[9] is not None and x[6] in ('Out', 'Doubtful') and max(x[10][0][0], x[10][2][0]) >= 20]
cand.sort(key=lambda x: -abs(x[10][2][1] - x[10][0][1]))
seen = set(); uniq = []
for c in cand:
    if c[5] not in seen: seen.add(c[5]); uniq.append(c)
pick = uniq[:2] + ([c for c in uniq if abs(c[10][2][1] - c[10][0][1]) < 0.3][:1])   # 2 με τη μεγαλυτερη αλλαγη + 1 με μικρη, διαφορετικοι παικτες
for (dt_, mt, s, day, t, pid, stt, n, mf, pv, row) in pick:
    P(f'  {dt_} {mt} (σεζον {s}, μερα {day} της σεζον) · {t} {NM.get(pid)} [pid {pid}] · {stt} · φετος {mf:.1f}′ σε {n} ματς · περσι {pv:.1f}′ '
      f'σε {PREVM[(int(pid), s - 1)][1]} ματς ({PTEAMS.get((int(pid), s - 1))}, ονομα περσι: {NMS.get((int(pid), s - 1))}) · λεπτα K=4 {row[2][0]:.1f}′ · '
      f'κοστος live {row[0][1]:.2f} π. vs K=4 {row[2][1]:.2f} π. · αξια περσι {value(pid, s - 1):+.2f}')
P(f'  (υποψηφια {len(cand)} · ποσοι απουσιες πρωτων 2 εβδ. αλλαζουν κοστος >0.3 π. με K=4: {sum(1 for c in cand if abs(c[10][2][1] - c[10][0][1]) > 0.3)})')
# ---- picks / RMSE ----
SIG = 13.5
def cover(m, L):
    if abs(L - round(L)) < 1e-9: pw = 1 - N_.cdf((-L + .5 - m) / SIG); pl = N_.cdf((-L - .5 - m) / SIG); return pw, 1 - pw - pl, pl
    pw = 1 - N_.cdf((-L - m) / SIG); return pw, 0.0, 1 - pw
def picks(pred, mask=None):
    U = collections.defaultdict(list)
    for q, (r, mp) in enumerate(zip(D.itertuples(index=False), pred)):
        if mask is not None and not mask[q]: continue
        pw, pp, pl = cover(mp, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; U[r.sea].append((od - 1) if x > 0 else (0.0 if x == 0 else -1.0))
    return U
def rm(pred, mk): return float(np.sqrt(np.mean((D.act.values[mk] - pred[mk]) ** 2)))
def cell(U):
    u = [x for v in U.values() for x in v]
    if not u: return 'κανενα pick'
    return (f"ROI {100 * np.mean(u):+5.1f}% · n {len(u)} · μοναδες {sum(u):+6.1f} · θετικες σεζον {sum(1 for s in SE if U[s] and sum(U[s]) > 0)}/5 · ανα σεζον "
            + ' '.join(f'{s % 100}:{sum(U[s]):+.1f}' for s in SE))
EARLY = D.gp.values < 10
P(''); P('ΑΝΑ K (ολα τα ματς / ματς με ομαδα <10 φετινα):')
for K in KS:
    pr = D[f'm{K}'].values
    P(f'  K={K:2d} · RMSE ολα {rm(pr, np.ones(len(D), bool)):.4f} · RMSE <10 {rm(pr, EARLY):.4f} · RMSE ανα σεζον ' + ' '.join(f'{s % 100}:{rm(pr, ys == s):.4f}' for s in SE))
    P(f'         picks ολα: {cell(picks(pr))}')
    P(f'         picks <10: {cell(picks(pr, EARLY))}')
P(''); P('ΔRMSE vs K=0 ανα φετινα ματς ομαδας (min των δυο): ')
for lab, mk in (('0-2', D.gp < 3), ('3-5', (D.gp >= 3) & (D.gp < 6)), ('6-9', (D.gp >= 6) & (D.gp < 10)), ('10+', D.gp >= 10)):
    mk = mk.values; base = rm(D['m0'].values, mk)
    P(f'  {lab:4s} n {int(mk.sum()):5d} · RMSE K=0 {base:.4f} · ' + ' · '.join(f'K={K}: {rm(D["m" + str(K)].values, mk) - base:+.4f}' for K in KS[1:]))
# ---- LOSO ----
P(''); P('LOSO (K απο τις 4 σεζον με RMSE, εφαρμογη στην 5η):')
held = np.zeros(len(D)); chosen = []
for s in SE:
    tr = ys != s
    best = min(KS, key=lambda K: np.mean((D.act.values[tr] - D[f'm{K}'].values[tr]) ** 2)); chosen.append(best)
    held[ys == s] = D[f'm{best}'].values[ys == s]
U0, U1 = picks(D.m0.values), picks(held)
d_rm = [rm(held, ys == s) - rm(D.m0.values, ys == s) for s in SE]
u1, u0 = sum(x for v in U1.values() for x in v), sum(x for v in U0.values() for x in v)
pos = sum(1 for s in SE if U1[s] and sum(U1[s]) > 0); idx = [KS.index(k) for k in chosen]
c1, c2, c3, c4 = sum(x < 0 for x in d_rm) >= 4, u1 >= u0, pos >= 4, (min(chosen) >= 0 and max(idx) - min(idx) <= 1)
P(f'  επιλεγμενο K ανα LOSO σεζον: ' + ' '.join(f'{s % 100}:K={k}' for s, k in zip(SE, chosen)))
P(f'  ΔRMSE (LOSO − K=0) ανα σεζον: ' + ' '.join(f'{s % 100}:{x:+.4f}' for s, x in zip(SE, d_rm)) + f' · καλυτερο σε {sum(x < 0 for x in d_rm)}/5')
P(f'  LOSO picks: {cell(U1)}')
P(f'  K=0 picks : {cell(U0)}')
EU0, EU1 = picks(D.m0.values, EARLY), picks(held, EARLY)
P(f'  LOSO picks <10: {cell(EU1)}')
P(f'  K=0 picks <10 : {cell(EU0)}')
P(f'  κριτηρια: RMSE ≥4/5 {"✓" if c1 else "✗"} · μοναδες ≥ K=0 ({u1:+.1f} vs {u0:+.1f}) {"✓" if c2 else "✗"} · θετικες ≥4/5 ({pos}/5) {"✓" if c3 else "✗"} · λογικη/σταθερο {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if (c1 and c2 and c3 and c4) else "ΔΕΝ περνα"}')
D['early'] = EARLY
pt = D.groupby('sea').early.mean()
P('  μεριδιο ματς <10 ανα σεζον: ' + ' '.join(f'{s % 100}:{100 * v:.0f}%' for s, v in pt.items()))
open(os.path.join(SC, 't58_minutes_blend_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
