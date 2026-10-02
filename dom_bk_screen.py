# -*- coding: utf-8 -*-
"""dom_bk_screen.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: «αξιζει να κατεβασουμε αποδοσεις;» ΧΩΡΙΣ αποδοσεις (2/10/2026, Στελιος: «για να μην κατεβαζουμε τσαμπα»).
6 μεγαλα: Ισπανια ACB · Ιταλια LBA · Ελλαδα GBL · Τουρκια TBL · Γαλλια LNB · Γερμανια BBL · σεζον 2020-21…2025-26 (Flashscore: fs_bk_games + fs_bk_stats).
ΜΗΧΑΝΗ (ιδια λογικη με Ευρωλιγκα): κατοχες × ποντοι/100 κατοχες, ridge επιθεση/αμυνα + εδρα (ελευθερη, προς περσινη) + ρυθμος,
  αφετηρια 0.7 × περσινο τελος, λ 8, walk-forward ανα μερα (μονο ματς ΠΡΙΝ τη μερα), «τυχη»: 3P%/FT% μισο-δρομο προς τον μεσο λιγκας.
  Ιδια μηχανη ΜΟΝΟ με σκορ και για Ευρωλιγκα/EuroCup (ιδια πηγη) → συγκριση «μηλα με μηλα».
ΜΕΤΡΟ 1 — προβλεψιμοτητα: λαθος (RMSE) διαφορας, % που εξηγει, ανα φαση σεζον (αγων 1-5 / 6-15 / 16+), ευρος δυναμης, εδρα, ποσο βοηθα η «τυχη».
ΜΕΤΡΟ 2 — επιδρασεις που το μοντελο δεν βλεπει (υπολοιπο = πραγματικη διαφορα − προβλεψη, γηπεδουχος):
  ευρωπαϊκο ματς (EL/EuroCup/BCL/FIBA EC) ≤3 μερες ΠΡΙΝ · ≤3 μερες ΜΕΤΑ (ξεκουραση αστερων) · διαφορα ξεκουρασης · εντος ή εκτος το ευρωπαϊκο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): μια επιδραση «αξιζει αποδοσεις» αν |μεσο υπολοιπο| ≥ 1.0 ποντο ΚΑΙ t ≥ 2 ΚΑΙ ιδιο προσημο σε ≥4/6 σεζον.
Εξοδος: dom_bk_screen_out.txt"""
import sys, json, math, datetime as dt, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
L6 = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']; EU = ['EL', 'EC', 'BCL', 'FEC']; YRS = range(2020, 2026)
NAME = dict(ACB='Ισπανια', LBA='Ιταλια', GBL='Ελλαδα', TBL='Τουρκια', LNB='Γαλλια', BBL='Γερμανια', EL='Ευρωλιγκα', EC='EuroCup')
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
FST = {}
for ln in open('fs_bk_stats.jsonl', encoding='utf-8'):
    r = json.loads(ln); FST[r['id']] = r['stats']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def fnum(x):
    try: return float(str(x).replace('%', ''))
    except Exception: return None
def box(st, i):
    if not st: return None
    g = lambda k: fnum((st.get(k) or (None, None))[i])
    b = dict(fg3=g('3-point field goals made'), fg3a=g('3-point field goals attempts'), ft=g('Free throws made'), fta=g('Free throws attempts'),
             fga=g('Field goals attempts'), orb=g('Offensive rebounds'), tov=g('Turnovers'))
    return b if all(v is not None for v in b.values()) else None
rows = []
for key, L in FG.items():
    lg, y = key.split('_'); y = int(y)
    if y not in YRS or lg not in L6 + EU: continue
    for e in L:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        if not (e.get('hid') and e.get('aid') and e.get('ts')): continue
        st = FST.get(e['id'])
        rows.append(dict(lg=lg, y=y, id=e['id'], t=pd.Timestamp(e['ts'], unit='s'), hid=e['hid'], aid=e['aid'], home=e['home'], away=e['away'],
                         hs=hs, as_=as_, hb=box(st, 0), ab=box(st, 1), stage=e.get('stage', '')))
G = pd.DataFrame(rows).sort_values('t').reset_index(drop=True)
G['d'] = (G.t.dt.normalize() - G.t.min().normalize()).dt.days
poss = lambda b: b['fga'] + 0.44 * b['fta'] - b['orb'] + b['tov']
G['ok'] = [h is not None and a is not None and (poss(h) + poss(a)) / 2 >= 50 for h, a in zip(G.hb, G.ab)]
P('=== ΔΕΔΟΜΕΝΑ ===')
for lg in L6 + ['EL', 'EC']:
    s = G[G.lg == lg]; P(f'  {NAME.get(lg, lg):10s} ματς {len(s):5d} · με box {s.ok.mean():.0%} · σεζον {sorted(s.y.unique())}')
# ---- αποδοτικοτητα (τυχη w) ----
def effs(w):
    EH, EA, PC = np.zeros(len(G)), np.zeros(len(G)), np.zeros(len(G))
    for (lg, y), g in G.groupby(['lg', 'y']):
        bx = g[g.ok]
        if len(bx):
            p3 = (sum(b['fg3'] for b in bx.hb) + sum(b['fg3'] for b in bx.ab)) / max(1, sum(b['fg3a'] for b in bx.hb) + sum(b['fg3a'] for b in bx.ab))
            ftp = (sum(b['ft'] for b in bx.hb) + sum(b['ft'] for b in bx.ab)) / max(1, sum(b['fta'] for b in bx.hb) + sum(b['fta'] for b in bx.ab))
            pace = float(np.mean([(poss(h) + poss(a)) / 2 for h, a in zip(bx.hb, bx.ab)]))
        else:
            p3 = ftp = None; pace = 72.0
        for i, r in g.iterrows():
            if r.ok and w is not None:
                ps = (poss(r.hb) + poss(r.ab)) / 2
                def adj(pts, b):
                    p3g = b['fg3'] / b['fg3a'] if b['fg3a'] else p3; ftg = b['ft'] / b['fta'] if b['fta'] else ftp
                    return pts - 3 * b['fg3'] + 3 * b['fg3a'] * (w * p3g + (1 - w) * p3) - b['ft'] + b['fta'] * (w * ftg + (1 - w) * ftp)
                EH[i], EA[i], PC[i] = 100 * adj(r.hs, r.hb) / ps, 100 * adj(r.as_, r.ab) / ps, ps
            else:
                ps = (poss(r.hb) + poss(r.ab)) / 2 if r.ok else pace
                EH[i], EA[i], PC[i] = 100 * r.hs / ps, 100 * r.as_ / ps, ps
    return EH, EA, PC
LAM, CARRY, HW = 8.0, 0.7, 50.0
def fit(hi, ai, eh, ea, n, o0, d0, h0, mu0):
    m = len(hi); A = np.zeros((2 * m + 2 * n + 2, 2 + 2 * n)); y = np.zeros(2 * m + 2 * n + 2); r0 = np.arange(m)
    A[r0, 0] = 1; A[r0, 1] = .5; A[r0, 2 + hi] = 1; A[r0, 2 + n + ai] = 1; y[r0] = eh
    A[m + r0, 0] = 1; A[m + r0, 1] = -.5; A[m + r0, 2 + ai] = 1; A[m + r0, 2 + n + hi] = 1; y[m + r0] = ea
    sl = math.sqrt(LAM); k = np.arange(n)
    A[2 * m + k, 2 + k] = sl; y[2 * m + k] = sl * o0; A[2 * m + n + k, 2 + n + k] = sl; y[2 * m + n + k] = sl * d0
    A[-2, 1] = math.sqrt(HW); y[-2] = math.sqrt(HW) * h0; A[-1, 0] = math.sqrt(5); y[-1] = math.sqrt(5) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1], x[2:2 + n], x[2 + n:]
def run(lg, EH, EA, PC):
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]])); info = {}
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        o0 = np.array([CARRY * prior.get(t, (0, 0))[0] for t in teams]); d0 = np.array([CARRY * prior.get(t, (0, 0))[1] for t in teams])
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                mu, h, O, D = fit(hi[past], ai[past], eh[past], ea[past], n, o0, d0, h0, mu0); pace = float(np.mean(pc[past][-200:]))
            else:
                mu, h, O, D, pace = mu0, h0, o0, d0, float(np.mean(PC[idx_all]))
            for j in cur:
                pred[sidx[j]] = pace * ((h + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D = fit(hi, ai, eh, ea, n, o0, d0, h0, mu0)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        net = (O - D) * float(np.mean(pc)) / 100
        info[y] = dict(h=h * float(np.mean(pc)) / 100, sd=float(np.std(net)), n=n)
    return pred, gn, info
act = (G.hs - G.as_).values.astype(float)
P(''); P('=== ΜΕΤΡΟ 1: ΠΡΟΒΛΕΨΙΜΟΤΗΤΑ (walk-forward, σεζον 2021-22…2025-26· η 2020-21 = ζεσταμα) ===')
P('  λαθος σε ποντους διαφορας (μικροτερο = καλυτερο) · % = ποσο απο τη διαφορα εξηγει το μοντελο')
P('  πρωταθλημα | ματς | λαθος ΜΕ box (τυχη) | μονο σκορ | % εξηγει | αγων 1-5 / 6-15 / 16+ | ευρος δυναμης (τ.α. ομαδων) | εδρα')
E_box, E_raw = effs(.5), effs(None)
PRED = {}
for lg in L6 + ['EL', 'EC']:
    pb, gn, info = run(lg, *E_box); pr, _, _ = run(lg, *E_raw)
    m = (G.lg.values == lg) & (G.y.values >= 2021) & np.isfinite(pb)
    rm = lambda v, mm: float(np.sqrt(np.mean((act - v)[mm] ** 2)))
    r2 = 1 - np.mean((act - pb)[m] ** 2) / np.var(act[m])
    ph = ' / '.join(f'{rm(pb, m & msk):.2f}' for msk in (gn <= 5, (gn >= 6) & (gn <= 15), gn >= 16))
    sd = np.mean([v['sd'] for y, v in info.items() if y >= 2021]); hh = np.mean([v['h'] for y, v in info.items() if y >= 2021])
    P(f'  {NAME[lg]:10s} | {m.sum():5d} | {rm(pb, m):6.2f} | {rm(pr, m):6.2f} | {r2*100:4.0f}% | {ph} | {sd:4.1f} | {hh:+.1f}')
    PRED[lg] = (pb, gn)
P('  (αναφορα αγορας απο τα τεστ μας: Ευρωλιγκα κλεισιμο ~11.4 · EuroCup κλεισιμο ~12.3 — εκει η μηχανη με box+ειδικους εβγαζε 11.7 / 12.4)')
# ---- ΜΕΤΡΟ 2: προγραμμα ----
P(''); P('=== ΜΕΤΡΟ 2: ΥΠΟΛΟΙΠΟ (πραγματικο − προβλεψη, ποντοι, απο πλευρα γηπεδουχου) ανα κατασταση · σεζον 2021-26 ===')
P('  ΠΡΟ-ΔΗΛΩΜΕΝΟ: αξιζει αποδοσεις αν |μεσο| ≥ 1.0 ΚΑΙ t ≥ 2 ΚΑΙ ιδιο προσημο σε ≥4/6 σεζον (εδω 5 σεζον αξιολογησης → ≥4/5)')
games = collections.defaultdict(list)                    # ομαδα → [(t, comp, εντος;)]
for r in G.itertuples():
    games[r.hid].append((r.t, r.lg, True)); games[r.aid].append((r.t, r.lg, False))
for v in games.values(): v.sort()
def ctx(team, t):
    v = games[team]; i = next((k for k, x in enumerate(v) if x[0] >= t), len(v))
    prev = v[i - 1] if i > 0 else None; nxt = next((x for x in v[i:] if x[0] > t + pd.Timedelta(hours=6)), None)
    rest = (t - prev[0]).total_seconds() / 86400 if prev else 9
    return dict(rest=min(rest, 9), prev_eu=bool(prev and prev[1] in EU and rest <= 3.5), prev_eu_away=bool(prev and prev[1] in EU and rest <= 3.5 and not prev[2]),
                next_eu=bool(nxt and nxt[1] in EU and (nxt[0] - t).total_seconds() / 86400 <= 3.5))
R = []
for lg in L6:
    pb, gn = PRED[lg]
    for i in np.where((G.lg.values == lg) & (G.y.values >= 2021) & np.isfinite(pb))[0]:
        r = G.iloc[i]; ch, ca = ctx(r.hid, r.t), ctx(r.aid, r.t)
        R.append(dict(lg=lg, y=r.y, res=act[i] - pb[i], **{f'h_{k}': v for k, v in ch.items()}, **{f'a_{k}': v for k, v in ca.items()}))
R = pd.DataFrame(R)
def show(lab, m, sign=1):
    s = R[m]; x = sign * s.res.values
    if len(x) < 30: P(f'  {lab:58s} n {len(x)} (λιγα)'); return
    mu, se = x.mean(), x.std(ddof=1) / math.sqrt(len(x)); per = [sign * R[m & (R.y == y)].res.mean() for y in range(2021, 2026) if (m & (R.y == y)).sum() >= 10]
    ok = abs(mu) >= 1.0 and abs(mu / se) >= 2 and sum(np.sign(p) == np.sign(mu) for p in per) >= 4
    P(f'  {lab:58s} n {len(x):5d} · {mu:+.2f} π. (t {mu/se:+.1f}) · σεζον ' + ' '.join(f'{p:+.1f}' for p in per) + ('  ← ΑΞΙΖΕΙ' if ok else ''))
show('γηπεδουχος με ευρωπαϊκο ≤3 μερες ΠΡΙΝ (φιλοξ. οχι)', R.h_prev_eu & ~R.a_prev_eu)
show('φιλοξενουμενος με ευρωπαϊκο ≤3 μερες ΠΡΙΝ (γηπ. οχι) [πλευρα φιλοξ.]', ~R.h_prev_eu & R.a_prev_eu, -1)
show('  … και το ευρωπαϊκο ηταν ΕΚΤΟΣ (ταξιδι) [πλευρα φιλοξ.]', ~R.h_prev_eu & R.a_prev_eu_away, -1)
show('  γηπεδουχος, ευρωπαϊκο ΕΚΤΟΣ', R.h_prev_eu_away & ~R.a_prev_eu)
show('και οι δυο με ευρωπαϊκο πριν', R.h_prev_eu & R.a_prev_eu)
show('γηπεδουχος με ευρωπαϊκο ≤3 μερες ΜΕΤΑ (ξεκουραζει;)', R.h_next_eu & ~R.a_next_eu)
show('φιλοξενουμενος με ευρωπαϊκο ≤3 μερες ΜΕΤΑ [πλευρα φιλοξ.]', ~R.h_next_eu & R.a_next_eu, -1)
P('  διαφορα ξεκουρασης (γηπ − φιλοξ, μερες):')
dr = (R.h_rest - R.a_rest)
for lo, hi, lab in ((-9, -2, '≤ −2'), (-2, -0.5, '−1'), (-0.5, 0.5, '0'), (0.5, 2, '+1'), (2, 9, '≥ +2')):
    show(f'    {lab}', (dr > lo) & (dr <= hi) if lo > -9 else (dr <= hi))
P(''); P('=== ανα πρωταθλημα: ευρωπαϊκο ΠΡΙΝ (οποια πλευρα, απο την πλευρα της κουρασμενης ομαδας) ===')
for lg in L6:
    mh = (R.lg == lg) & R.h_prev_eu & ~R.a_prev_eu; ma = (R.lg == lg) & ~R.h_prev_eu & R.a_prev_eu
    x = np.r_[R[mh].res.values, -R[ma].res.values]
    if len(x) >= 20: P(f'  {NAME[lg]:10s} n {len(x):4d} · {x.mean():+.2f} π. (t {x.mean() / (x.std(ddof=1) / math.sqrt(len(x))):+.1f})')
open('dom_bk_screen_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
# ---- ΕΛΕΓΧΟΣ ΜΠΕΡΔΕΜΑΤΟΣ (γραφτηκε ΜΕΤΑ το πρωτο αποτελεσμα): ειναι κουραση ή απλως «ομαδες Ευρωπης = υποτιμημενες»; ----
EUT = {(r.hid, r.y) for r in G[G.lg.isin(EU)].itertuples()} | {(r.aid, r.y) for r in G[G.lg.isin(EU)].itertuples()}
R2 = []
for lg in L6:
    pb, gn = PRED[lg]
    for i in np.where((G.lg.values == lg) & (G.y.values >= 2021) & np.isfinite(pb))[0]:
        r = G.iloc[i]; ch, ca = ctx(r.hid, r.t), ctx(r.aid, r.t)
        R2.append(dict(lg=lg, y=r.y, res=act[i] - pb[i], gn=gn[i], h_eut=(r.hid, r.y) in EUT, a_eut=(r.aid, r.y) in EUT, h_pe=ch['prev_eu'], a_pe=ca['prev_eu']))
R2 = pd.DataFrame(R2)
P(''); P('=== ΕΛΕΓΧΟΣ: ομαδες που παιζουν Ευρωπη ΦΕΤΟΣ, απεναντι σε ομαδα που ΔΕΝ παιζει (απο την πλευρα της «ευρωπαϊκης») ===')
def side(m_h, m_a, lab):
    x = np.r_[R2[m_h].res.values, -R2[m_a].res.values]
    yy = np.r_[R2[m_h].y.values, R2[m_a].y.values]
    per = [x[yy == y].mean() for y in range(2021, 2026)]
    P(f'  {lab:52s} n {len(x):5d} · {x.mean():+.2f} π. (t {x.mean() / (x.std(ddof=1) / math.sqrt(len(x))):+.1f}) · σεζον ' + ' '.join(f'{p:+.1f}' for p in per))
eh_, ea_ = R2.h_eut & ~R2.a_eut, ~R2.h_eut & R2.a_eut
side(eh_ & R2.h_pe, ea_ & R2.a_pe, 'ΜΕ ευρωπαϊκο ματς ≤3 μερες πριν')
side(eh_ & ~R2.h_pe, ea_ & ~R2.a_pe, 'ΧΩΡΙΣ ευρωπαϊκο εκεινη την εβδομαδα')
side(eh_ & (R2.gn <= 10), ea_ & (R2.gn <= 10), '  (μονο αγων 1-10)')
side(eh_ & (R2.gn > 10), ea_ & (R2.gn > 10), '  (μονο αγων 11+)')
P('  → αν ΚΑΙ τα δυο ~+2: δεν ειναι κουραση, ειναι γενικη υποτιμηση των ομαδων Ευρωπης απο το μοντελο (ή αληθινη: η Ευρωπη «διδασκει»)')
open('dom_bk_screen_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
