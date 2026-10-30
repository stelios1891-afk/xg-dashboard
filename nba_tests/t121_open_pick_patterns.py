# -*- coding: utf-8 -*-
"""t121_open_pick_patterns.py — NBA: ΤΙ ΔΕΝ ΠΑΕΙ ΚΑΛΑ ΣΤΑ PICKS ΑΝΟΙΓΜΑΤΟΣ (χαντικαπ) — patterns απουσιων (30/10/2026, Στελιος «ναι»·
αφορμη Pacers +7.5 χωρις Haliburton/Zubac → 8.5).
ΔΕΙΓΜΑ: picks ανοιγματος του t120 (live μηχανη + live αξια αποντα, επισημη αναφορα ως το ανοιγμα −15′, Crown, edge ≥ 8% / Ιαν-Φεβ 12%, αγων ≤75).
ΜΕΤΡΗΣΗ ανα pattern: ROI, μοναδες, CLV (π., κινηση δικαιης γραμμης ως το κλεισιμο προς το pick), θετικες σεζον, συνολο αν τα αφαιρεσουμε.
PATTERNS (ορισμενα ΠΡΙΝ το τρεξιμο), για ΔΙΚΗ ΜΑΣ πλευρα (Ε) και ΑΝΤΙΠΑΛΟ (Α):
  1 λειπει ο ΚΑΛΥΤΕΡΟΣ (μεγαλυτερη αξια μεταξυ παικτων ρολου ≥20′ της ομαδας) — Out στο ανοιγμα
  2 λειπουν ≥2 ΒΑΣΙΚΟΙ (5 με τα περισσοτερα μεσα λεπτα) — Out
  3 κοστος απουσιων ≥2 / ≥3 / ≥4 π.
  4 λειπουν ≥3 παικτες ρολου (Out)
  5 το pick το ΕΦΤΙΑΞΕ η διορθωση απουσιων (χωρις απουσιες δεν θα ηταν pick) · το pick ΕΠΙΒΙΩΝΕΙ παρα κοστος ≥1 π. στη δικη μας πλευρα
  6 πολλοι αμφιβολοι στη δικη μας πλευρα (Σ πιθανοτητων Questionable/Doubtful ≥1)
  7 ΜΑΚΡΟΧΡΟΝΙΑ απουσια (Out που εχει χασει ≥5 συνεχομενα ματς της ομαδας) vs ΦΡΕΣΚΙΑ (0-2) — κοστος ≥1 π. απο αυτους
  8 ΑΟΥΤΣΑΙΝΤΕΡ με απουσιες (κοστος ≥2 στη δικη μας πλευρα) vs ΦΑΒΟΡΙ με απουσιες
ΚΡΙΤΗΡΙΑ «κανονα αποφυγης» (ΠΡΙΝ το τρεξιμο): n ≥ 100 · ROI ≤ −5% ΚΑΙ CLV < 0 · αρνητικο ≥4/5 σεζον · συνολικες μοναδες ΑΝΕΒΑΙΝΟΥΝ χωρις αυτα.
Εξοδος: t121_open_pick_patterns_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't120_abs_engine_el_style.py'), encoding='utf-8').read().split("T1, T2, DIE, BETS = [], [], []")[0]
NS = {'__file__': os.path.join(SC, 't120_abs_engine_el_style.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, NS)
sys.stdout.reconfigure(encoding='utf-8')
g = NS['g']
np, pd, G, SEAS_G, dD, EV, ACT, VNO, SER, SHIFT = (g[k] for k in ('np', 'pd', 'G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT'))
K2P, mins, REP_BY, line_at, REP_SEASONS, cover_, SIG_ = (g[k] for k in ('K2P', 'mins', 'REP_BY', 'line_at', 'REP_SEASONS', 'cover_', 'SIG_'))
team_cost, prob, value_live, GN, thr, edges, settle, LAG = (NS[k] for k in ('team_cost', 'prob', 'value_live', 'GN', 'thr', 'edges', 'settle', 'LAG'))
A2 = g['A2']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(SC, 't121_open_pick_patterns_out.txt'), 'w', encoding='utf-8').write(chr(10).join(out))
# ---- ρόστερ & ματς ομαδας ----
P2K = {(pid, t, s): k for (k, t, s), pid in K2P.items()}
TEAMP = collections.defaultdict(set)
for (k, t, s), pid in K2P.items(): TEAMP[(t, s)].add(pid)
PLAYD = collections.defaultdict(set)
for r in A2.itertuples(index=False):
    if r.MIN > 0: PLAYD[(r.pid, r.team, int(r.s))].add(r.dd)
TGAMES = collections.defaultdict(list)
for i in range(len(G)):
    s = int(SEAS_G[i]); TGAMES[(G.home.values[i], s)].append(dD[i]); TGAMES[(G.away.values[i], s)].append(dD[i])
for k in TGAMES: TGAMES[k].sort()
def streak(pid, t, s, d):
    """συνεχομενα ματς της ομαδας (πριν το d) που ο παικτης ΔΕΝ επαιξε"""
    n = 0; pl = PLAYD.get((pid, t, s), set())
    for dd in reversed([x for x in TGAMES[(t, s)] if x < d]):
        if dd in pl: break
        n += 1
    return n
def status_at(t, d, tau):
    st = {}
    for back in (3, 2, 1, 0):
        for ep, k, stt in REP_BY.get((t, d - np.timedelta64(back, 'D')), ()):
            if ep <= tau: st[k] = stt
    return st
def feats(t, d, s, tau):
    st = status_at(t, d, tau)
    roster = []
    for pid in TEAMP[(t, s)]:
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        roster.append((pid, m, value_live(pid, s, d)))
    if not roster: return None
    best = max(roster, key=lambda x: x[2])[0]; starters = {x[0] for x in sorted(roster, key=lambda x: -x[1])[:5]}
    cost, _ = team_cost(t, d, s, tau)
    outs = [x for x in roster if st.get(P2K.get((x[0], t, s))) == 'Out']
    q = sum(prob(st.get(P2K.get((x[0], t, s))), x[1]) for x in roster if st.get(P2K.get((x[0], t, s))) in ('Questionable', 'Doubtful'))
    lt = ft = 0.0
    for pid, m, v in outs:
        c = 0.75 * (v + 2.0) * m / 48; sk = streak(pid, t, s, d)
        if sk >= 5: lt += c
        elif sk <= 2: ft += c
    return dict(best=best in {x[0] for x in outs}, nst=len(starters & {x[0] for x in outs}), cost=cost, nout=len(outs), q=q, lt=lt, ft=ft)

R = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]) or GN[i] > 75: continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900 and x[1] is not None and x[2] and x[3]]
    if len(rows) < 1: continue
    close = line_at(rows, tip, sw)
    if not close: continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]; TH = thr(i)
    L0, oh0, oa0, f0, _ = line_at(rows, t0, sw)
    ch0, _ = team_cost(h, d, s, t0 - LAG); ca0, _ = team_cost(a, d, s, t0 - LAG)
    e1, e2 = edges(VNO[i] - ch0 + ca0, L0, oh0, oa0); sd, e, od = (1, e1, oh0) if e1 >= e2 else (-1, e2, oa0)
    if e < TH: continue
    n1, n2 = edges(VNO[i], L0, oh0, oa0); en = n1 if sd == 1 else n2
    us, them = (h, a) if sd == 1 else (a, h)
    fu, ft_ = feats(us, d, s, t0 - LAG), feats(them, d, s, t0 - LAG)
    if fu is None or ft_ is None: continue
    R.append(dict(sea=s, res=settle(i, L0, sd, od), clv=sd * (close[3] - f0), dog=(L0 * sd > 0), made=(en < TH),
                  **{f'u_{k}': v for k, v in fu.items()}, **{f'o_{k}': v for k, v in ft_.items()}, game=f'{str(d)[:10]} {h}-{a}', side=us, line=L0 * sd))
X = pd.DataFrame(R); SEA = sorted(X.sea.unique())
X.to_pickle(os.path.join(ROOT, 'nba_injrep', 't121_open_picks.pkl'))
def cell(Z):
    if not len(Z): return '    —'
    ps = Z.groupby('sea').res.sum()
    return f'{len(Z):5d} · ROI {100 * Z.res.mean():+6.1f}% · {Z.res.sum():+7.1f}μ · θετ {int((ps > 0).sum())}/{Z.sea.nunique()} · CLV {Z.clv.mean():+.2f}π'
P(f'NBA picks ανοιγματος (χαντικαπ, live μηχανη+αξια): {cell(X)}')
P('pattern | picks μεσα · ROI · μοναδες · θετικες σεζον · CLV || χωρις αυτα: μοναδες || ΚΡΙΤΗΡΙΟ (n≥100 · ROI≤−5% · CLV<0 · αρνητικο ≥4/5 · μοναδες ↑)')
PAT = []
for pre, nm in (('u', 'Ε (δικη μας)'), ('o', 'Α (αντιπαλος)')):
    PAT += [(f'1 {nm}: λειπει ο καλυτερος', X[f'{pre}_best']),
            (f'2 {nm}: ≥2 βασικοι Out', X[f'{pre}_nst'] >= 2),
            (f'3 {nm}: κοστος ≥2', X[f'{pre}_cost'] >= 2), (f'3 {nm}: κοστος ≥3', X[f'{pre}_cost'] >= 3), (f'3 {nm}: κοστος ≥4', X[f'{pre}_cost'] >= 4),
            (f'4 {nm}: ≥3 Out ρολου', X[f'{pre}_nout'] >= 3),
            (f'6 {nm}: αμφιβολοι Σ ≥1', X[f'{pre}_q'] >= 1),
            (f'7 {nm}: μακροχρονια ≥1 π.', X[f'{pre}_lt'] >= 1), (f'7 {nm}: φρεσκια ≥1 π.', X[f'{pre}_ft'] >= 1)]
PAT += [('5 το pick το ΕΦΤΙΑΞΑΝ οι απουσιες', X.made), ('5 επιβιωνει παρα κοστος ≥1 στη δικη μας', (~X.made) & (X.u_cost >= 1)),
        ('8 ΑΟΥΤΣΑΙΝΤΕΡ με κοστος ≥2 (δικη μας)', X.dog & (X.u_cost >= 2)), ('8 ΦΑΒΟΡΙ με κοστος ≥2 (δικη μας)', (~X.dog) & (X.u_cost >= 2))]
tot = X.res.sum()
for nm, m in PAT:
    Z = X[m]; rest = tot - Z.res.sum()
    ps = Z.groupby('sea').res.sum(); neg = int((ps < 0).sum())
    ok = len(Z) >= 100 and Z.res.mean() <= -.05 and Z.clv.mean() < 0 and neg >= 4 and rest > tot
    P(f'{nm:42s} | {cell(Z)} || χωρις: {rest:+7.1f}μ || {"✓ ΥΠΟΨΗΦΙΟΣ" if ok else "✗"}')
    if 'ΑΟΥΤΣΑΙΝΤΕΡ' in nm or 'καλυτερος' in nm: P(f'{"":42s}   ανα σεζον: ' + ' · '.join(f'{s_ % 100:02d}: {Z[Z.sea == s_].res.sum():+.1f}μ ({(Z.sea == s_).sum()})' for s_ in SEA))
save()
