# -*- coding: utf-8 -*-
"""t59_inseason_value.py — ΑΞΙΑ ΑΠΟΝΤΑ: ΣΤΑΔΙΑΚΗ ΜΙΞΗ ΦΕΤΙΝΗΣ (BOX) ΜΕ ΠΕΡΣΙΝΗ (22/10/2026).
Ερωτημα: στο live NBA η αξια ενος αποντα (για το κοστος απουσιας) ειναι ΜΟΝΟ η περσινη value(pid, s−1) (DARKO/LEBRON/BPM μαζεμενα· αγνωστος −1).
  Εκδοχη: v = (MIN_φετος·v_φετος + M·v_περσι)/(MIN_φετος + M) · MIN_φετος = λεπτα του παικτη φετος (ολες οι ομαδες) σε ματς ΠΡΙΝ την ημερα του ματς.
  Πλεγμα M ∈ {∞ (= live), 4000, 2000, 1000, 500} λεπτα. Αν δεν υπαρχει περσινη αξια → v_περσι = −1 (οπως το live).
ΦΕΤΙΝΗ ΑΞΙΑ (χωρις διαρροη): μηχανισμος nba_oracle_test.py — ρυθμοι ανα λεπτο 14 χαρακτηριστικων (2Π/3Π/βολες ευστ.-αστ., ΕΡ, ΑΡ, ΑΣ,
  ΚΛ, ΚΟ, ΛΑ, ΦΑ, +/-) ΜΟΝΟ απο ΦΕΤΙΝΑ box scores με ημερομηνια < ημερα ματς, φθορα 180 μερες, μαζεμα 300′ προς τον μεσο της λιγκας.
  Κλιμακα value(): v_φετος = a + w·(ρυθμοι − μεσος) · (a, w) με σταθμισμενα ελαχιστα τετραγωνα (βαρος = λεπτα σεζον) πανω σε ζευγαρια
  [ρυθμοι ΤΕΛΟΥΣ σεζον s′ → value(pid, s′)] για ΟΛΕΣ τις s′ < s (ποτε η s). Μεσος λιγκας επισης μονο απο s′ < s.
ΜΗΧΑΝΗ: ιδια με t56/t58 (exec t22 ως TAUS, _t29_games ανοιγμα, αντιστοιχιση (ημερομηνια, γηπεδουχος), |ACT−act| ≤ 0.5, opening_ts του t56,
  κοστος = p_out(κατασταση, ρολος)·0.75·(v+2)·λεπτα/48, λεπτα = live (μ.ο. ≤10 φετινων με την ομαδα), μονο ≥20′). Αλλαζει ΜΟΝΟ το v.
  Picks χαντικαπ στο ανοιγμα, edge ≥8%, σ 13.5. Ελεγχος: M=∞ πρεπει να δινει ROI +5.2%, 3103 picks, +159.8 μοναδες (t58 K=0).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο):
  LOSO 5 σεζον (2022-2026): M επιλεγεται στις 4 σεζον με RMSE (act − μοντελο), εφαρμοζεται στην 5η. ΠΕΡΝΑ αν:
  RMSE καλυτερο απο M=∞ σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ M=∞ ΚΑΙ θετικες σεζον ≥4/5
  ΚΑΙ λογικη (επιλεγμενο M σταθερο: ολα τα LOSO M μεσα σε ±1 βημα πλεγματος).
  Περιγραφικα: Οκτ-Δεκ vs Ιαν-Απρ, μοναδες ανα σεζον, ποιοτητα αντιστοιχισης (εκτος δειγματος: corr box τελους s με value(s) vs corr value(s−1) με value(s)).
ΕΛΕΓΧΟΣ: 3 πραγματικα παραδειγματα αποντων (βελτιωθηκε, επεσε, rookie) με περσινη, φετινη box, λεπτα ως τη μερα, μικτη M=1000, κοστος live vs νεο,
  + τελευταια ημερομηνια box που χρησιμοποιηθηκε (πρεπει < ημερα ματς).
Εξοδος: t59_inseason_value_out.txt"""
import os, sys, io, contextlib, collections, pickle, bisect
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
CACHE = os.environ.get('T59_CACHE')                         # προαιρετικο pickle (scratchpad) για ξανατρεξιμο χωρις τη βαρια φορτωση
class _B(io.StringIO):
    def reconfigure(self, **k): pass
import numpy as np, pandas as pd
if CACHE and os.path.exists(CACHE):
    C = pickle.load(open(CACHE, 'rb'))
else:
    src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(src, g)
    G, SEAS_G, dD, SER, SHIFT, A2, mins, value, status_at, ACT, K2P = g['G'], g['SEAS_G'], g['dD'], g['SER'], g['SHIFT'], g['A2'], g['mins'], g['value'], g['status_at'], g['ACT'], g['K2P']
    VM = value.__globals__['M']
    PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
            'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}
    def p_out(stt, m): return PROB['star' if m >= 30 else ('starter' if m >= 20 else 'role')].get(stt, 0.0)
    def opening_ts(i):
        sw, tip, r21, _ = SER[i]; rr = sorted(x[0] + SHIFT for x in r21); rr = [x for x in rr if x <= tip + 900]
        return rr[0] if rr else None
    GI = {(str(dD[j])[:10], G.home.values[j]): j for j in range(len(G))}
    X = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
    rows = []; ABS = []; miss = 0; notau = 0
    for r in X.itertuples(index=False):
        i = GI.get((str(r.date)[:10], r.home))
        if i is None or i not in SER: miss += 1; continue
        if abs(ACT[i] - r.act) > 0.5: miss += 1; continue
        tau = opening_ts(i)
        if tau is None: notau += 1; continue
        d = dD[i]; s = int(r.sea); q = len(rows)
        for t, sg in ((r.home, -1.0), (r.away, +1.0)):            # m = m0 − κοστος γηπ + κοστος φιλ
            for k, stt in status_at(t, d, tau).items():
                pid = K2P.get((k, t, s))
                if pid is None: continue
                m = mins(pid, t, s, d)
                if m is None or m < 20: continue
                w = p_out(stt, m)
                if w == 0: continue
                known = any((pid, s - 1) in Dm for Dm in VM.values())
                ABS.append(dict(q=q, sg=sg, pid=pid, team=t, stt=stt, m=m, w=w, vprev=value(pid, s - 1), known=known, s=s, d=str(d)[:10]))
        rows.append(dict(sea=s, L=r.L, oh=r.oh, oa=r.oa, fair=r.fair, act=r.act, date=str(d)[:10], home=r.home, away=r.away, m0=r.m0))
    # value(pid, s′) για εκπαιδευση αντιστοιχισης (ολοι οι παικτες-σεζον στα box)
    VAL = {}
    for p, s_ in A2[['pid', 's']].drop_duplicates().itertuples(index=False):
        s_ = int(s_)
        if any((p, s_) in Dm for Dm in VM.values()): VAL[(p, s_)] = value(p, s_)
    C = dict(rows=rows, ABS=ABS, miss=miss, notau=notau, VAL=VAL, NM=dict(zip(A2.pid, A2.PLAYER_NAME)))
    if CACHE: pickle.dump(C, open(CACHE, 'wb'))
sys.stdout.reconfigure(encoding='utf-8')
from statistics import NormalDist
N_ = NormalDist()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pd.DataFrame(C['rows']); AB_ = pd.DataFrame(C['ABS']); VAL = C['VAL']; NM = C['NM']
P(f"ματς {len(D)} (χωρις αντιστοιχιση/ACT {C['miss']}, χωρις χρονο ανοιγματος {C['notau']}) · εγγραφες αποντων με βαρος>0 και λεπτα ≥20: {len(AB_)} "
  f"(χωρις περσινη αξια: {int((~AB_.known).sum())})")
# ---------------- box scores (μηχανισμος nba_oracle_test) ----------------
BX = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'))
BX = BX[BX.stype == 'RS'].copy()
BX['MIN'] = pd.to_numeric(BX.MIN, errors='coerce').fillna(0); BX = BX[BX.MIN > 0].copy()
BX['pid'] = BX.PLAYER_ID.astype(str); BX['s'] = BX.season.str[:4].astype(int) + 1
BX['dd'] = pd.to_datetime(BX.GAME_DATE).values.astype('datetime64[D]').astype(np.int64)
BX['p2m'] = BX.FGM - BX.FG3M; BX['p2x'] = (BX.FGA - BX.FG3A) - (BX.FGM - BX.FG3M); BX['p3m'] = BX.FG3M; BX['p3x'] = BX.FG3A - BX.FG3M
BX['ftm'] = BX.FTM; BX['ftx'] = BX.FTA - BX.FTM
F = ['p2m', 'p2x', 'p3m', 'p3x', 'ftm', 'ftx', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']
for f in F: BX[f] = pd.to_numeric(BX[f], errors='coerce').fillna(0.0)
BX = BX.sort_values(['dd', 'GAME_ID']).reset_index(drop=True)
HLD, M0 = 180.0, 300.0
SEAS_BX = sorted(BX.s.unique())
P(f'box σεζον: {SEAS_BX} · γραμμες {len(BX)}')
MU_BY = {s: (BX[BX.s < s][F].sum() / BX[BX.s < s].MIN.sum()).values for s in SEAS_BX if (BX.s < s).any()}   # μεσος λιγκας μονο απο προηγουμενες σεζον
ST = {}                                                      # (pid, s) → (ημερες, t0, cum decayed stats, cum decayed min, cum raw min)
for (p, s), gg in BX.groupby(['pid', 's'], sort=False):
    dd = gg.dd.values; t0 = int(dd[0]); f = 2.0 ** ((dd - t0) / HLD)
    ST[(p, int(s))] = (dd, t0, np.cumsum(gg[F].values * f[:, None], axis=0), np.cumsum(gg.MIN.values * f), np.cumsum(gg.MIN.values))
def feats(p, s, d, mu):
    """ρυθμοι πανω απο τον μεσο ΜΟΝΟ απο ματς με ημερομηνια < d (int ημερες) · (feat, λεπτα, ματς, τελευταια ημερα)"""
    st = ST.get((p, s))
    if st is None: return np.zeros(len(F)), 0.0, 0, None
    dd, t0, cs, cm, cr = st; j = bisect.bisect_left(dd, d)
    if j == 0: return np.zeros(len(F)), 0.0, 0, None
    fac = 2.0 ** (-(d - t0) / HLD); ss = cs[j - 1] * fac; ms = cm[j - 1] * fac
    return (ss + M0 * mu) / (ms + M0) - mu, float(cr[j - 1]), j, int(dd[j - 1])
END = {k: int(v[0][-1]) + 1 for k, v in ST.items()}
FIT = {}; DIAG = []
for s in sorted(D.sea.unique()):
    mu = MU_BY[s]; Xs, ys_, ws = [], [], []
    for (p, s_), dEnd in END.items():
        if s_ >= s or (p, s_) not in VAL: continue
        ft, mn, _, _ = feats(p, s_, dEnd, mu)
        Xs.append(ft); ys_.append(VAL[(p, s_)]); ws.append(mn)
    Xs, ys_, ws = np.array(Xs), np.array(ys_), np.array(ws)
    Z = np.c_[np.ones(len(Xs)), Xs]; sw = np.sqrt(ws)
    coef = np.linalg.lstsq(Z * sw[:, None], ys_ * sw, rcond=None)[0]; FIT[s] = coef
    pr = Z @ coef; r2 = 1 - np.sum(ws * (ys_ - pr) ** 2) / np.sum(ws * (ys_ - np.average(ys_, weights=ws)) ** 2)
    # εκτος δειγματος (περιγραφικο, ΔΕΝ χρησιμοποιειται): box τελους s → value(s) vs value(s−1) → value(s)
    a1, a2, b1, wq = [], [], [], []
    for (p, s_), dEnd in END.items():
        if s_ != s or (p, s) not in VAL or (p, s - 1) not in VAL: continue
        ft, mn, _, _ = feats(p, s, dEnd, mu)
        if mn < 500: continue
        a1.append(coef[0] + ft @ coef[1:]); a2.append(VAL[(p, s - 1)]); b1.append(VAL[(p, s)]); wq.append(mn)
    DIAG.append((s, len(Xs), r2, len(a1), np.corrcoef(a1, b1)[0, 1], np.corrcoef(a2, b1)[0, 1], np.corrcoef(0.5 * np.array(a1) + 0.5 * np.array(a2), b1)[0, 1]))
P(''); P('ΑΝΤΙΣΤΟΙΧΙΣΗ box → κλιμακα value() (εκπαιδευση μονο σε s′ < s):')
for s, n, r2, n2, c1, c2, c3 in DIAG:
    P(f'  σεζον-τεστ {s}: ζευγαρια εκπαιδευσης {n:4d} · R² εντος δειγματος (σταθμ. λεπτα) {r2:.3f} · εκτος δειγματος (παικτες ≥500′ στη σεζον {s}, n {n2}): '
      f'corr(box τελους {s}, value {s}) {c1:.3f} · corr(value {s - 1}, value {s}) {c2:.3f} · corr(50/50, value {s}) {c3:.3f}')
# ---------------- φετινη αξια ανα αποντα ----------------
dint = pd.to_datetime(AB_.d).values.astype('datetime64[D]').astype(np.int64)
VN, MN, NG, LAST = [], [], [], []
for r, d in zip(AB_.itertuples(index=False), dint):
    coef = FIT[r.s]; ft, mn, ng, last = feats(r.pid, r.s, int(d), MU_BY[r.s])
    VN.append(coef[0] + ft @ coef[1:] if ng else np.nan); MN.append(mn); NG.append(ng); LAST.append(last)
AB_['vnow'] = VN; AB_['minnow'] = MN; AB_['ng'] = NG; AB_['last'] = LAST; AB_['dint'] = dint
leak = int(sum(1 for l, d in zip(LAST, dint) if l is not None and l >= d))
P(f'ελεγχος διαρροης: εγγραφες με τελευταιο box ≥ ημερα ματς: {leak} (πρεπει 0) · εγγραφες χωρις φετινο box πριν το ματς: {int((AB_.ng == 0).sum())}')
INF = float('inf'); MS = (INF, 4000, 2000, 1000, 500)
def vmix(M):
    if M == INF: return AB_.vprev.values
    vn = np.where(AB_.ng.values > 0, AB_.vnow.values, AB_.vprev.values); mn = AB_.minnow.values
    return (mn * vn + M * AB_.vprev.values) / (mn + M)
def lab(M): return '∞' if M == INF else str(int(M))
for M in MS:
    v = vmix(M); cost = AB_.w.values * 0.75 * (v + 2.0) * AB_.m.values / 48
    AB_[f'c{lab(M)}'] = cost; adj = np.zeros(len(D)); np.add.at(adj, AB_.q.values, AB_.sg.values * cost)
    D[f'm{lab(M)}'] = D.m0.values + adj
# ---- ελεγχος παραδειγματων ----
P(''); P('ΠΑΡΑΔΕΙΓΜΑΤΑ (απων Out/Doubtful, ≥300′ φετος πριν το ματς):')
c = AB_[(AB_.stt.isin(['Out', 'Doubtful'])) & (AB_.minnow >= 300)].copy(); c['dv'] = c.vnow - c.vprev
ex = [('βελτιωθηκε', c[c.known].sort_values('dv', ascending=False).iloc[0]), ('επεσε', c[c.known].sort_values('dv').iloc[0]),
      ('rookie/χωρις περσινη', c[~c.known].sort_values('minnow', ascending=False).iloc[0])]
def show(tag, r):
    rr = D.iloc[int(r.q)]; vm = (r.minnow * r.vnow + 1000 * r.vprev) / (r.minnow + 1000)
    P(f'  [{tag}] {r.d} {rr.away}@{rr.home} (σεζον {r.s}) · {r.team} {NM.get(r.pid)} [pid {r.pid}] · {r.stt} · λεπτα live {r.m:.1f}′ · '
      f'περσινη αξια {r.vprev:+.2f}{"" if r.known else " (αγνωστος → −1)"} · φετινη box (κλιμακα value) {r.vnow:+.2f} · φετινα λεπτα ως τη μερα {r.minnow:.0f}′ σε {r.ng} ματς '
      f'(τελευταιο box {str(np.datetime64(int(r["last"]), "D"))}) · μικτη M=1000 {vm:+.2f} · κοστος live {r["c∞"]:.2f} π. vs M=1000 {r["c1000"]:.2f} π.')
for t, r in ex: show(t, r)
P('  πιο «φημισμενα» αλλαγης (μεγαλυτερη |Δκοστος| με M=1000, διαφορετικοι παικτες):')
c['dc'] = (c['c1000'] - c['c∞']).abs(); seen = set(); k = 0
for _, r in c.sort_values('dc', ascending=False).iterrows():
    if r.pid in seen: continue
    seen.add(r.pid); show('μεγαλη αλλαγη', r); k += 1
    if k == 3: break
P('  κατανομη Δαξιας (M=1000 − live) στις εγγραφες: ' + ' · '.join(f'{qq}%: {np.percentile(vmix(1000) - AB_.vprev.values, qq):+.2f}' for qq in (5, 25, 50, 75, 95)))
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
SE = sorted(D.sea.unique()); ys = D.sea.values
def rm(pred, mk): return float(np.sqrt(np.mean((D.act.values[mk] - pred[mk]) ** 2)))
def cell(U):
    u = [x for v in U.values() for x in v]
    if not u: return 'κανενα pick'
    return (f"ROI {100 * np.mean(u):+5.1f}% · n {len(u)} · μοναδες {sum(u):+6.1f} · θετικες σεζον {sum(1 for s in SE if U[s] and sum(U[s]) > 0)}/5 · ανα σεζον "
            + ' '.join(f'{s % 100}:{sum(U[s]):+.1f}' for s in SE))
MON = pd.to_datetime(D.date).dt.month.values; OD = np.isin(MON, [10, 11, 12]); JA = np.isin(MON, [1, 2, 3, 4])
ALLM = np.ones(len(D), bool)
P(''); P(f'ΑΝΑ M (ματς Οκτ-Δεκ {int(OD.sum())} · Ιαν-Απρ {int(JA.sum())}):')
for M in MS:
    pr = D[f'm{lab(M)}'].values
    P(f'  M={lab(M):>4s} · RMSE ολα {rm(pr, ALLM):.4f} · Οκτ-Δεκ {rm(pr, OD):.4f} · Ιαν-Απρ {rm(pr, JA):.4f} · ανα σεζον ' + ' '.join(f'{s % 100}:{rm(pr, ys == s):.4f}' for s in SE))
    P(f'          picks ολα    : {cell(picks(pr))}')
    P(f'          picks Οκτ-Δεκ: {cell(picks(pr, OD))}')
    P(f'          picks Ιαν-Απρ: {cell(picks(pr, JA))}')
# ---- LOSO ----
P(''); P('LOSO (M απο τις 4 σεζον με RMSE, εφαρμογη στην 5η):')
held = np.zeros(len(D)); chosen = []
for s in SE:
    tr = ys != s
    best = min(MS, key=lambda M: np.mean((D.act.values[tr] - D[f'm{lab(M)}'].values[tr]) ** 2)); chosen.append(best)
    held[ys == s] = D[f'm{lab(best)}'].values[ys == s]
base = D['m∞'].values
U0, U1 = picks(base), picks(held)
d_rm = [rm(held, ys == s) - rm(base, ys == s) for s in SE]
u1, u0 = sum(x for v in U1.values() for x in v), sum(x for v in U0.values() for x in v)
pos = sum(1 for s in SE if U1[s] and sum(U1[s]) > 0); idx = [MS.index(k) for k in chosen]
c1, c2, c3, c4 = sum(x < 0 for x in d_rm) >= 4, u1 >= u0, pos >= 4, (max(idx) - min(idx) <= 1)
P('  επιλεγμενο M ανα LOSO σεζον: ' + ' '.join(f'{s % 100}:M={lab(k)}' for s, k in zip(SE, chosen)))
P('  ΔRMSE (LOSO − M=∞) ανα σεζον: ' + ' '.join(f'{s % 100}:{x:+.4f}' for s, x in zip(SE, d_rm)) + f' · καλυτερο σε {sum(x < 0 for x in d_rm)}/5')
P(f'  LOSO picks : {cell(U1)}')
P(f'  M=∞ picks  : {cell(U0)}')
for nm_, mk in (('Οκτ-Δεκ', OD), ('Ιαν-Απρ', JA)):
    P(f'  LOSO picks {nm_}: {cell(picks(held, mk))}')
    P(f'  M=∞  picks {nm_}: {cell(picks(base, mk))}')
    P(f'  ΔRMSE LOSO − M=∞ {nm_}: {rm(held, mk) - rm(base, mk):+.4f}')
P(f'  κριτηρια: RMSE ≥4/5 {"✓" if c1 else "✗"} · μοναδες ≥ M=∞ ({u1:+.1f} vs {u0:+.1f}) {"✓" if c2 else "✗"} · θετικες ≥4/5 ({pos}/5) {"✓" if c3 else "✗"} · λογικη/σταθερο {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if (c1 and c2 and c3 and c4) else "ΔΕΝ περνα"}')
e0 = (D.act.values - base) ** 2; e1_ = (D.act.values - held) ** 2; dd_ = e1_ - e0
P(f'  ΔMSE ανα ματς (LOSO − M=∞): {dd_.mean():+.4f} ± {dd_.std(ddof=1) / np.sqrt(len(dd_)):.4f} (τυπικο σφαλμα) · t {dd_.mean() / (dd_.std(ddof=1) / np.sqrt(len(dd_))):+.2f}')
def per_game(pred):
    res = np.zeros(len(D))
    for q, (r, mp) in enumerate(zip(D.itertuples(index=False), pred)):
        pw, pp, pl = cover(mp, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; res[q] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    return res
g0, g1 = per_game(base), per_game(held); dg = g1 - g0
P(f'  Δμοναδες (LOSO − M=∞): {dg.sum():+.1f} ± {dg.std(ddof=1) * np.sqrt(len(dg)):.1f} (τυπικο σφαλμα, ανα ματς ζευγαρωτα) · ματς με διαφορετικο pick/αποτελεσμα {int((dg != 0).sum())}')
P(f'  ROI M=∞ ± ΤΣ: {100 * g0[g0 != 0].mean() if False else 100 * u0 / sum(len(v) for v in U0.values()):+.1f}% ± {100 * np.std([x for v in U0.values() for x in v], ddof=1) / np.sqrt(sum(len(v) for v in U0.values())):.1f}% · ROI LOSO ± ΤΣ: {100 * u1 / sum(len(v) for v in U1.values()):+.1f}% ± {100 * np.std([x for v in U1.values() for x in v], ddof=1) / np.sqrt(sum(len(v) for v in U1.values())):.1f}%')
u0n = sum(len(v) for v in U0.values())
P(f'  ελεγχος αναπαραγωγης live (M=∞): ROI {100 * u0 / u0n:+.1f}% · n {u0n} · μοναδες {u0:+.1f} (στοχος +5.2% · 3103 · +159.8)')
open(os.path.join(SC, 't59_inseason_value_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
