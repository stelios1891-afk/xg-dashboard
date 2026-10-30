# -*- coding: utf-8 -*-
"""t120_abs_engine_el_style.py — NBA ΜΗΧΑΝΗ ΑΠΟΥΣΙΩΝ ΜΕ ΤΑ ΤΕΣΤ ΤΗΣ ΕΥΡΩΛΙΓΚΑΣ (30/10/2026, Στελιος «ναι»: πηγη = ΕΠΙΣΗΜΗ αναφορα).
ΧΑΝΤΙΚΑΠ (τα συνολα σε δευτερο βημα). 5 σεζον με επισημες αναφορες · κανονικη περιοδος · αγωνας ≤75 (live LATE_GP).
ΜΗΧΑΝΗ = αντιγραφο live (t22: VNO = production + carry + B2B + ζωνη ωρας + μεταγραφες, χωρις απουσιες)
  + απουσιες απο την ΕΠΙΣΗΜΗ αναφορα με ΠΙΘΑΝΟΤΗΤΕΣ ΑΝΑ ΡΟΛΟ (live nba_injrep_live.PROB) · κοστος 0.75·(αξια+2)·λεπτα/48 · μονο ρολου ≥20′.
  ΡΕΑΛΙΣΤΙΚΗ ΓΝΩΣΗ: στη στιγμη τ η μηχανη ξερει την αναφορα ως τ−15′ (καθυστερηση live).
ΤΙΜΕΣ: Crown, καθε αλλαγη γραμμης (news_test SER, +8 διορθωση) ως το τζαμπολ. PICK = edge ≥ κατωφλι live (8% · Ιαν-Φεβ 12%).
ΣΤΙΓΜΕΣ σαρωσης: καθε αλλαγη τιμης + καθε αλλαγη αναφορας (+15′) των 2 ομαδων.
ΤΕΣΤ:
  Τ1 ΑΝΟΙΓΜΑ: μηχανη με απουσιες (αναφορα ως το ανοιγμα) vs ιδια ΧΩΡΙΣ απουσιες → picks που ΚΟΒΕΙ / ΠΡΟΣΘΕΤΕΙ / ΚΟΙΝΑ (ROI ανοιγματος, CLV).
  Τ2 ΜΕΤΑ ΤΟ ΑΝΟΙΓΜΑ: picks που ΓΕΝΝΑ ΜΟΝΟ η ειδηση (η διορθωση αλλαξε και με την παλια διορθωση στην ιδια τιμη ΔΕΝ θα ηταν pick)
     ανα ωρες πριν, πλευρα (απων στον αντιπαλο / σε εμας), ειδος (καινουργιος στην αναφορα · αλλαγη καταστασης · επιστροφη).
     + picks ανοιγματος που «ΔΕΝ ΙΣΧΥΟΥΝ ΠΙΑ» λογω ειδησης (στην ιδια γραμμη edge < 0): ROI αν τα κρατουσαμε.
  Τ3 «ΟΠΩΣ ΠΑΙΖΟΥΜΕ»: Β = ανοιγμα + alerts απουσιων · Α = scanner live (πρωτη φορα edge ≥ κατωφλι, κανονας πρωτης γραμμης:
     και στη γραμμη ανοιγματος με την ΤΩΡΙΝΗ μηχανη ≥ κατωφλι). Ενα bet ανα ματς/πλευρα.
  Τ4 ΖΩΝΤΑΝΗ vs ΠΑΓΩΜΕΝΗ: ιδιος scanner Α με απουσιες παγωμενες στο ανοιγμα → η διαφορα = αξια των ειδησεων μεσα στη μερα.
ΚΡΙΤΗΡΙΑ (οπως Ευρωλιγκα): ROI > 0 · θετικο ≥4/5 σεζον · CLV > 0. CLV = κινηση δικαιης γραμμης ως το κλεισιμο προς το pick (π.).
ΟΧΙ στο τεστ: φιλτρο κινητρου 71-75, steam, Doubtful-φιλτρο. Εξοδος: t120_abs_engine_el_style_out.txt"""
import os, sys, io, contextlib, collections, bisect
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, G, SEAS_G, dD, EV, ACT, VNO, SER, SHIFT = (g[k] for k in ('np', 'pd', 'G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT'))
cover_, SIG_, value, K2P, mins, REP_BY, line_at, REP_SEASONS = (g[k] for k in ('cover_', 'SIG_', 'value', 'K2P', 'mins', 'REP_BY', 'line_at', 'REP_SEASONS'))
PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04},
        'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
        'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}
def prob(st, m):
    return PROB['star' if m >= 30 else ('starter' if m >= 20 else 'role')].get(st, 0.0)
LAG = 900
# 30/10 (Στελιος «ναι»): ΑΞΙΑ ΑΠΟΝΤΑ ΟΠΩΣ ΤΟ LIVE (T120_VALUE=live, προεπιλογη): περσινο DARKO+LEBRON (χωρις BPM) × λεπτα/(λεπτα+500)
# (αν δεν επαιξε περσι → προπερσι) ανακατεμενο με φετινο «Β» (δικο μας box, t65 εβδομαδιαιο walk-forward, κλιμακα a+c·B απο σεζον < S):
# v = (φετινα λεπτα·v_B + 250·v_περσι)/(φετινα λεπτα + 250). 2021-22: χωρις «Β» (δεν υπαρχουν περσινα pbp) → μονο περσινο.
# T120_VALUE=old → η παλια αξια του t22 (DARKO/LEBRON/BPM περσι) για συγκριση.
VMODE = os.environ.get('T120_VALUE', 'live')
if VMODE == 'live':
    t65s = open(os.path.join(SC, 't65_bet.py'), encoding='utf-8').read()
    t65s = t65s.split("INF = float('inf')")[0].replace("OUTF = os.path.join(SC, 't65_own_index_out.txt')", "OUTF = os.devnull")
    g65 = {'__file__': os.path.join(SC, 't65_bet.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(t65s, g65)
    cwd_ = os.getcwd(); os.chdir(ROOT)
    rs_ = open(os.path.join(ROOT, 'nba_roster_adj.py'), encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
    R_ = {}
    with contextlib.redirect_stdout(_B()): exec(rs_, R_)
    os.chdir(cwd_); sys.stdout.reconfigure(encoding='utf-8')
    VM_, MPT_ = R_['M'], R_['MPT']; own_at = g65['own_at']; MAPN = g65['mapping'](MPT_, 0); TEST65 = set(g65['TEST'])
    def base4(p, y):
        vs = [VM_[k][(p, y)] for k in ('DARKO', 'LEBRON') if (p, y) in VM_[k]]
        if not vs: return None
        mp = MPT_.get((p, y), 0.0); return float(np.mean(vs)) * mp / (mp + 500)
    A3 = g['A2'].copy(); A3 = A3.sort_values('dd')
    CUMM = {}
    for (pid_, s_), gg in A3.groupby(['pid', 's']): CUMM[(pid_, int(s_))] = (gg.dd.values, np.cumsum(gg.MIN.values))
    VCACHE_ = {}; STATB = collections.Counter()
    def value_live(pid, s, d):
        key = (pid, s, d)
        if key in VCACHE_: return VCACHE_[key]
        v0 = base4(pid, s - 1)
        if v0 is None: v0 = base4(pid, s - 2)
        if v0 is None: v0 = -1.0
        v = v0
        if s in TEST65:
            c = CUMM.get((pid, s)); mn = 0.0
            if c is not None:
                j = np.searchsorted(c[0], d, side='left'); mn = float(c[1][j - 1]) if j > 0 else 0.0
            o = own_at(str(pid), s, str(d)[:10], 'prior') if mn > 0 else None
            if o is not None:
                a_, c_ = MAPN[s][0]; vb = a_ + c_ * o[0]; v = (mn * vb + 250 * v0) / (mn + 250)
        STATB[('B' if v != v0 else ('περσι' if v0 != -1.0 else 'αγνωστος'), s)] += 1
        VCACHE_[key] = v; return v
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(SC, 't120_abs_engine_el_style_out.txt' if os.environ.get('T120_VALUE', 'live') == 'live' else 't120_abs_engine_el_style_OLDVALUE_out.txt'), 'w', encoding='utf-8').write(chr(10).join(out))

# ---- αριθμος αγωνα (μικροτερος των 2 + 1, οπως live) ----
order = np.argsort(G.date.values, kind='stable'); cnt = collections.Counter(); GN = np.zeros(len(G), int)
for i in order:
    s = int(SEAS_G[i]); h, a = G.home.values[i], G.away.values[i]
    GN[i] = min(cnt[(s, h)], cnt[(s, a)]) + 1; cnt[(s, h)] += 1; cnt[(s, a)] += 1

def team_cost(t, d, s, tau):
    """κοστος απουσιων ομαδας (π.) με την αναφορα γνωστη ως τ · + λεξικο {key: (κατασταση, κοστος)}"""
    st = {}
    for back in (3, 2, 1, 0):
        for ep, k, stt in REP_BY.get((t, d - np.timedelta64(back, 'D')), ()):
            if ep <= tau: st[k] = stt
    c = 0.0; det = {}
    for k, stt in st.items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        w = prob(stt, m)
        if w <= 0: continue
        vv = value_live(pid, s, d) if VMODE == 'live' else value(pid, s - 1)
        cc = w * 0.75 * (vv + 2.0) * m / 48; c += cc; det[k] = (stt, cc)
    return c, det
def rep_times(t, d, lo, hi):
    ts = set()
    for back in (3, 2, 1, 0):
        for ep, k, stt in REP_BY.get((t, d - np.timedelta64(back, 'D')), ()):
            if lo < ep + LAG < hi: ts.add(ep + LAG)
    return ts
def thr(i): return 0.12 if int(G.date.dt.month.values[i]) in (1, 2) else 0.08
def edges(m, L, oh, oa):
    pw, pp, pl = cover_(m, L, SIG_); return pw * oh + pp - 1, pl * oa + pp - 1
def settle(i, L, sd, od):
    x = (ACT[i] + L) * sd; return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)

T1, T2, DIE, BETS = [], [], [], {'A': {}, 'B': {}, 'F': {}}
PLAYED = collections.defaultdict(float)
for r in g['A2'].itertuples(index=False): PLAYED[(r.pid, r.dd)] += float(r.MIN)
n_games = 0
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]) or GN[i] > 75: continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900 and x[1] is not None and x[2] and x[3]]
    if len(rows) < 1: continue
    close = line_at(rows, tip, sw)
    if not close: continue
    n_games += 1
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]; TH = thr(i)
    events = sorted(set(x[0] for x in rows if x[0] < tip) | rep_times(h, d, t0, tip) | rep_times(a, d, t0, tip))
    # γραμμη ανοιγματος
    L0, oh0, oa0, f0, _ = line_at(rows, t0, sw)
    ch0, dh0 = team_cost(h, d, s, t0 - LAG); ca0, da0 = team_cost(a, d, s, t0 - LAG)
    m_open = VNO[i] - ch0 + ca0; m_none = VNO[i]
    # ---- Τ1: ανοιγμα με / χωρις απουσιες ----
    rec = {}
    for nm, m in (('abs', m_open), ('none', m_none)):
        e1, e2 = edges(m, L0, oh0, oa0); sd, e, od = (1, e1, oh0) if e1 >= e2 else (-1, e2, oa0)
        rec[nm] = (sd, od) if e >= TH else None
    for sd in (1, -1):
        ina = rec['abs'] is not None and rec['abs'][0] == sd; inn = rec['none'] is not None and rec['none'][0] == sd
        if not (ina or inn): continue
        od = oh0 if sd == 1 else oa0; adj = (ca0 - ch0) * sd                   # + = οι απουσιες ευνοουν την πλευρα
        T1.append(dict(sea=s, grp='ΚΟΙΝΟ' if (ina and inn) else ('ΚΟΒΕΤΑΙ' if inn else 'ΠΡΟΣΤΙΘΕΤΑΙ'), res=settle(i, L0, sd, od),
                       clv=sd * (close[3] - f0), adj=adj))
    open_pick = rec['abs']
    if open_pick: BETS['B'][(i, open_pick[0])] = dict(sea=s, res=settle(i, L0, open_pick[0], open_pick[1]), clv=open_pick[0] * (close[3] - f0), kind='ανοιγμα', hrs=(tip - t0) / 3600)
    # ---- σαρωση ----
    prev_adj = ca0 - ch0; prev_det = (dh0, da0); died = set()
    for tau in events:
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        ch, dh = team_cost(h, d, s, tau - LAG); ca, da = team_cost(a, d, s, tau - LAG)
        adj = ca - ch; m = VNO[i] + adj; mF = m_open
        e1, e2 = edges(m, L, oh, oa)
        for sd, e, od in ((1, e1, oh), (-1, e2, oa)):
            # Α scanner live: πρωτη φορα ≥ κατωφλι + κανονας πρωτης γραμμης (τωρινη μηχανη στη γραμμη ανοιγματος)
            if e >= TH and (i, sd) not in BETS['A']:
                q1, q2 = edges(m, L0, oh0, oa0); e0 = q1 if sd == 1 else q2
                if e0 >= TH:
                    BETS['A'][(i, sd)] = dict(sea=s, res=settle(i, L, sd, od), clv=sd * (close[3] - fair), kind='σαρωση', hrs=(tip - tau) / 3600, at_open=(tau == t0))
            # Τ2: γεννηθηκε απο την ειδηση (μετα το ανοιγμα)
            if tau > t0 and e >= TH and abs(adj - prev_adj) > 1e-9:
                p1, p2 = edges(VNO[i] + prev_adj, L, oh, oa); eprev = p1 if sd == 1 else p2
                if eprev < TH and (i, sd) not in BETS['B']:
                    # ειδος ειδησης: ποιοι παικτες αλλαξαν
                    side_team, (dprev, dnow) = (a, (prev_det[1], da)) if sd == 1 else (h, (prev_det[0], dh))   # απων στον ΑΝΤΙΠΑΛΟ βοηθα
                    own_team, (oprev, onow) = (h, (prev_det[0], dh)) if sd == 1 else (a, (prev_det[1], da))
                    ch_opp = {k: v for k, v in dnow.items() if dprev.get(k) != v}; ch_own = {k: v for k, v in oprev.items() if onow.get(k) != v}
                    gone_opp = {k for k in dprev if k not in dnow}
                    who = 'ΑΝΤΙΠΑΛΟΣ χανει' if ch_opp else ('ΕΠΙΣΤΡΟΦΗ σε εμας' if ch_own else 'αλλο')
                    if ch_opp:
                        newk = [k for k in ch_opp if k not in dprev]
                        kind = 'καινουργιος στην αναφορα' if newk else 'αλλαγη καταστασης'
                    elif ch_own: kind = 'επιστροφη/αναβαθμιση δικου μας'
                    elif gone_opp: kind = 'αλλο'
                    else: kind = 'αλλο'
                    # 30/10 (Στελιος «ποιες ειναι οι επιστροφες;»): λεπτομερειες δικων μας αλλαγων — καταστασ. πριν → τωρα, κοστος πριν, ΕΠΑΙΞΕ τελικα (λεπτα)
                    ret_ = [(k, oprev[k][0], onow[k][0] if k in onow else 'εκτος αναφορας', round(oprev[k][1], 2),
                             PLAYED.get((K2P.get((k, own_team, s)), d), 0.0)) for k in ch_own]
                    opp_ = [(k, dprev[k][0] if k in dprev else 'καθολου', v[0], round(v[1], 2), PLAYED.get((K2P.get((k, side_team, s)), d), 0.0)) for k, v in ch_opp.items()]
                    r_ = dict(sea=s, res=settle(i, L, sd, od), clv=sd * (close[3] - fair), kind='ειδηση', hrs=(tip - tau) / 3600, who=who, nk=kind,
                              dpts=(adj - prev_adj) * sd, dog=(L * sd > 0), ret=ret_, opp=opp_, game=f'{str(d)[:10]} {h}-{a}', side=(h if sd == 1 else a), L=L * sd, od=od,
                              mv_open=sd * (fair - f0))
                    T2.append(r_); BETS['B'][(i, sd)] = r_
            # «δεν ισχυει πια»: pick ανοιγματος, η ειδηση το κανει edge < 0 στην ΙΔΙΑ γραμμη ανοιγματος
            if open_pick and open_pick[0] == sd and sd not in died and abs(adj - prev_adj) > 1e-9:
                q1, q2 = edges(m, L0, oh0, oa0); en = q1 if sd == 1 else q2
                if en < 0:
                    died.add(sd); DIE.append(dict(sea=s, res=settle(i, L0, sd, open_pick[1]), hrs=(tip - tau) / 3600,
                                                  res_now=settle(i, L, -sd, oa if sd == 1 else oh)))
        # Τ4: παγωμενη μηχανη
        f1, f2 = edges(mF, L, oh, oa)
        for sd, e, od in ((1, f1, oh), (-1, f2, oa)):
            if e >= TH and (i, sd) not in BETS['F']:
                q1, q2 = edges(mF, L0, oh0, oa0); e0 = q1 if sd == 1 else q2
                if e0 >= TH: BETS['F'][(i, sd)] = dict(sea=s, res=settle(i, L, sd, od), clv=sd * (close[3] - fair), kind='σαρωση', hrs=(tip - tau) / 3600, at_open=(tau == t0))
        prev_adj = adj; prev_det = (dh, da)

SEA = sorted({int(SEAS_G[i]) for i in SER if int(SEAS_G[i]) in EV and int(SEAS_G[i]) in REP_SEASONS})
def cell(X):
    if not len(X): return '        —'
    X = pd.DataFrame(X) if not isinstance(X, pd.DataFrame) else X
    ps = X.groupby('sea').res.sum()
    return f'{len(X):5d} bets · ROI {100 * X.res.mean():+6.1f}% · {X.res.sum():+7.1f}μ · θετ {int((ps > 0).sum())}/{X.sea.nunique()} · CLV {X.clv.mean():+.2f}π' if 'clv' in X else \
           f'{len(X):5d} bets · ROI {100 * X.res.mean():+6.1f}% · {X.res.sum():+7.1f}μ · θετ {int((ps > 0).sum())}/{X.sea.nunique()}'
def per_sea(X):
    X = pd.DataFrame(X); return ' · '.join(f'{s % 100:02d}: {X[X.sea == s].res.sum():+.1f}μ ({(X.sea == s).sum()})' for s in SEA)
P(f'NBA ΧΑΝΤΙΚΑΠ · αξια αποντα: {VMODE} · μηχανη απουσιων με τα τεστ της Ευρωλιγκας · σεζον {SEA} · ματς {n_games} · πηγη: ΕΠΙΣΗΜΗ αναφορα (+15′) · Crown')
X1 = pd.DataFrame(T1)
if VMODE == 'live': P('ελεγχος αξιας (μοναδικοι παικτης·μερα): ' + ' · '.join(f'{s_}: ' + '/'.join(f'{k} {STATB[(k, s_)]}' for k in ('B', 'περσι', 'αγνωστος')) for s_ in SEA))
P('\n=== Τ1 ΑΝΟΙΓΜΑ: με απουσιες vs χωρις (ROI στην τιμη ανοιγματος) ===')
for gname in ('ΚΟΙΝΟ', 'ΚΟΒΕΤΑΙ', 'ΠΡΟΣΤΙΘΕΤΑΙ'):
    P(f'  {gname:12s}: {cell(X1[X1.grp == gname])}')
    P(f'                ανα σεζον: {per_sea(X1[X1.grp == gname])}')
P(f'  ολα με απουσιες (κοινα+προστιθεται): {cell(X1[X1.grp != "ΚΟΒΕΤΑΙ"])}')
P(f'  ολα χωρις απουσιες (κοινα+κοβεται):  {cell(X1[X1.grp != "ΠΡΟΣΤΙΘΕΤΑΙ"])}')
save()
X2 = pd.DataFrame(T2)
P('\n=== Τ2 ΜΕΤΑ ΤΟ ΑΝΟΙΓΜΑ: picks που γεννα ΜΟΝΟ η ειδηση (τιμη της στιγμης) ===')
P(f'  ΟΛΑ: {cell(X2)}'); P(f'        ανα σεζον: {per_sea(X2)}')
if len(X2):
    for lab, m_ in (('<1ω', X2.hrs < 1), ('1-3ω', (X2.hrs >= 1) & (X2.hrs < 3)), ('3-6ω', (X2.hrs >= 3) & (X2.hrs < 6)), ('6-12ω', (X2.hrs >= 6) & (X2.hrs < 12)), ('≥12ω', X2.hrs >= 12)):
        P(f'  {lab:6s} πριν: {cell(X2[m_])}')
    for w_ in X2.who.unique(): P(f'  {w_:22s}: {cell(X2[X2.who == w_])}')
    for k_ in X2.nk.unique(): P(f'  {k_:32s}: {cell(X2[X2.nk == k_])}')
    P(f'  αουτσαιντερ {cell(X2[X2.dog])} · φαβορι {cell(X2[~X2.dog])}')
    P(f'  αλλαγη διορθωσης <1 π. {cell(X2[X2.dpts < 1])} · 1-2 π. {cell(X2[(X2.dpts >= 1) & (X2.dpts < 2)])} · ≥2 π. {cell(X2[X2.dpts >= 2])}')
if len(X2):
    X2.to_pickle(os.path.join(ROOT, 'nba_injrep', 't120_news_picks.pkl'))
    R2 = X2[X2.who == 'ΕΠΙΣΤΡΟΦΗ σε εμας']
    P(f'\n=== ΕΠΙΣΤΡΟΦΕΣ (picks υπερ ομαδας που ξαναπαιρνει παικτη): {cell(R2)} ===')
    rows_ = [(r.sea, r.res, st0, st1, c0, mn) for r in R2.itertuples() for (k, st0, st1, c0, mn) in r.ret]
    if rows_:
        RR = pd.DataFrame(rows_, columns=['sea', 'res', 'st0', 'st1', 'c0', 'mn'])
        for (a0, a1), x in RR.groupby(['st0', 'st1']): P(f'  {a0:12s} → {a1:16s}: {len(x):3d} περιπτωσεις · ROI picks {100 * x.res.mean():+6.1f}% · επαιξε τελικα {100 * (x.mn > 0).mean():.0f}% (μ.ο. {x.mn[x.mn > 0].mean() if (x.mn > 0).any() else 0:.0f}′) · κοστος που αφαιρεθηκε {x.c0.mean():.2f} π.')
        P(f'  επαιξε τελικα: {cell(RR[RR.mn > 0])} · ΔΕΝ επαιξε: {cell(RR[RR.mn == 0])}')
    for r in R2.itertuples():
        P(f'   {r.game} · pick {r.side} {r.L:+g} @{r.od:.2f} · {r.hrs:.1f}ω πριν · ' + ', '.join(f'{k} {a0}→{a1} (κοστος {c0}, επαιξε {mn:.0f}′)' for k, a0, a1, c0, mn in r.ret) + f' · {r.res:+.2f}')
XD = pd.DataFrame(DIE)
P('\n=== «ΔΕΝ ΙΣΧΥΕΙ ΠΙΑ»: pick ανοιγματος που η ειδηση κανει edge < 0 (στη γραμμη ανοιγματος) ===')
if len(XD):
    ps = XD.groupby('sea').res.sum()
    P(f'  {len(XD)} picks · αν τα ΚΡΑΤΟΥΣΑΜΕ (τιμη ανοιγματος): ROI {100 * XD.res.mean():+.1f}% ({XD.res.sum():+.1f}μ, θετ {int((ps > 0).sum())}/{XD.sea.nunique()}) · '
      f'αν παιζαμε την ΑΝΤΙΘΕΤΗ πλευρα τη στιγμη της ειδησης: ROI {100 * XD.res_now.mean():+.1f}% ({XD.res_now.sum():+.1f}μ)')
save()
P('\n=== Τ3 «ΟΠΩΣ ΠΑΙΖΟΥΜΕ» · Τ4 ΖΩΝΤΑΝΗ vs ΠΑΓΩΜΕΝΗ ===')
XA, XB, XF = (pd.DataFrame(list(BETS[k].values())) for k in ('A', 'B', 'F'))
P(f'  Β ανοιγμα + alerts απουσιων: {cell(XB)}'); P(f'        ανα σεζον: {per_sea(XB)}')
P(f'     απο αυτα: ανοιγμα {cell(XB[XB.kind == "ανοιγμα"])} · alerts {cell(XB[XB.kind == "ειδηση"])}')
P(f'  Α scanner live (ζωντανη μηχανη): {cell(XA)}'); P(f'        ανα σεζον: {per_sea(XA)}')
P(f'     απο αυτα: στο ανοιγμα {cell(XA[XA.at_open])} · αργοτερα {cell(XA[~XA.at_open])}')
P(f'  Τ4 scanner με ΠΑΓΩΜΕΝΕΣ απουσιες: {cell(XF)}'); P(f'        ανα σεζον: {per_sea(XF)}')
P(f'     απο αυτα: στο ανοιγμα {cell(XF[XF.at_open])} · αργοτερα {cell(XF[~XF.at_open])}')
kA, kF = set(BETS['A']), set(BETS['F'])
oa_ = [BETS['A'][k] for k in kA - kF]; of_ = [BETS['F'][k] for k in kF - kA]
P(f'  ΜΟΝΟ στη ζωντανη: {cell(oa_)} · ΜΟΝΟ στην παγωμενη: {cell(of_)}')
P(f'  ζωντανη − παγωμενη = {XA.res.sum() - XF.res.sum():+.1f}μ · ανα σεζον ' + ' · '.join(f'{s % 100:02d}: {XA[XA.sea == s].res.sum() - XF[XF.sea == s].res.sum():+.1f}' for s in SEA))
save()
