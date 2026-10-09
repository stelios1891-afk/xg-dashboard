"""
core7_early_weakness.py — 9/10/2026 (Στελιος «τρεξτο»): ΠΟΥ ΑΔΥΝΑΤΕΙ ΤΟ ΜΟΝΤΕΛΟ ΝΩΡΙΣ; (CORE7, 2223-2526, live μηχανη:
σωστο SoS 0.75 @7-14, Dixon-Coles, κοκκινες emps, warm-start K=8). Αγωνιστικη = md+1 (md = ματς που εχουν παιχτει).
Μηχανες: LIVE (K=8) · ΜΟΝΟ ΠΕΡΣΙΝΟ (K=100000) · ΜΟΝΟ ΦΕΤΙΝΟ (K=0.01) — core7_mech_variant KWARM.
Αγορα: Pinnacle κλεισιμο (football-data, αγων 7+) · Crown & Bet365 κλεισιμο (Nowgoal, ολες).
Υπεροχη αγορας για αγων 1-6 (Crown): αντιστροφη p_cover με το συνολο του μοντελου.
Ενοτητες: Α χαρτης απωλειων · Β ποιος εχει δικιο / απο που ερχεται το λαθος · Γ καμπυλη μαθησης · Δ μεροληψια αγορας ανα αγωνιστικη ·
Ε ΦΙΛΤΡΟ ΣΤΑΘΕΡΟΤΗΤΑΣ (προ-δηλωμενο, LOSO).
ΠΡΟ-ΔΗΛΩΣΗ Ε: φιλτρο περνα αν (1) LOSO ROI (μεσος 3 βιβλιων) > 0 ΚΑΙ > σημερα σε ≥3/4 σεζον, (2) θετικο Pinnacle ΚΑΙ ≥1 αλλο βιβλιο,
(3) ≥60 picks συνολο (μεσος βιβλιων). Ορια επιλεγονται LOSO απο πλεγμα (μεγιστες μοναδες στις 3 σεζον εκπαιδευσης).
"""
import sys, io, json, contextlib, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
s = open('core7_sos15_final.py', encoding='utf-8').read(); s = s[:s.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'ew'}
with contextlib.redirect_stdout(_Q()): exec(s, g)
D, run_L, load, NG, picks, ev_ok = g['D'], g['run_L'], g['load'], g['NG'], g['picks'], g['ev_ok']
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEAS = ['2223', '2324', '2425', '2526']
V = 'cur_0.75_6_13~emps'
def preds(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str}); return P.set_index('mid')
P = preds(V); PP = preds(V + '@K100000'); PC = preds(V + '@K0.01')
M = P[P.season.isin(SEAS)].copy()
M['s_mod'] = M.xg_h - M.xg_a; M['T'] = M.xg_h + M.xg_a
M['s_pr'] = (PP.xg_h - PP.xg_a).reindex(M.index); M['s_cu'] = (PC.xg_h - PC.xg_a).reindex(M.index)
Dm = D.set_index('mid')
for c in ('L', 'ah', 'aa', 's_mkt'): M[f'pin_{c}'] = Dm[c].reindex(M.index)
# ---- αγκυρα live (15+ κοντες dogs, 0.7 φαβορι) απο run_L πανω στα D ----
xh, xa, _ = load(V); D['xh'] = xh; D['xa'] = xa
S0, SA = run_L(0, 0, 6), run_L(0.5, 0, 6)
M['s_anc'] = pd.Series(SA, index=D.mid.values).reindex(M.index); M['s_0'] = pd.Series(S0, index=D.mid.values).reindex(M.index)
# ---- Crown/Bet365 κλεισιμο + υπεροχη αγορας απο Crown ----
for bk, ab in (('Crown', 'cr'), ('Bet365', 'b3')):
    q = [NG.get((m, bk)) for m in M.index]
    M[f'{ab}_L'] = [x[1][0] if x else np.nan for x in q]; M[f'{ab}_oh'] = [x[1][1] if x else np.nan for x in q]; M[f'{ab}_oa'] = [x[1][2] if x else np.nan for x in q]
def mkt_sup(L, oh, oa, T):
    if not (L == L and oh == oh): return np.nan
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        sm = (lo + hi) / 2; d = picks.gd_dist_dom(max((T + sm) / 2, .05), max((T - sm) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = sm
        else: hi = sm
    return (lo + hi) / 2
M['s_cr'] = [mkt_sup(L, oh, oa, T) for L, oh, oa, T in zip(M.cr_L, M.cr_oh, M.cr_oa, M['T'])]
M['s_m'] = M.pin_s_mkt.where(M.pin_s_mkt.notna(), M.s_cr)          # αγορα: Pinnacle οπου υπαρχει, αλλιως Crown
M['wd'] = pd.cut(M.md, [-1, 4, 5, 13, 99], labels=['1-5', '6', '7-14', '15+'])
print(f'ματς {len(M)} · με αγορα {M.s_m.notna().sum()} · ανα παραθυρο ' + ' '.join(f'{k}:{v}' for k, v in M.groupby("wd", observed=True).size().items()))
# ---- PICKS (ιδιοι κανονες με live) ----
rows = []
for mid, r in M.iterrows():
    for bk, (L, oh, oa) in (('Pinnacle', (r.pin_L, r.pin_ah, r.pin_aa)), ('Crown', (r.cr_L, r.cr_oh, r.cr_oa)), ('Bet365', (r.b3_L, r.b3_oh, r.b3_oa))):
        if not (L == L and oh == oh): continue
        T = r['T']; sp = r.s_mod
        if r.md >= 14 and abs(L) in (0.5, 0.75) and r.s_anc == r.s_anc: sp = r.s_0 + (r.s_anc - r.s_0)          # αγκυρα κοντες (live 15+)
        for b in picks.evaluate_bet(max((T + sp) / 2, .05), max((T - sp) / 2, .05), L, oh, oa):
            rows.append(dict(mid=mid, book=bk, role='dog', side=b['side'], hcap=b['hcap'], odds=b['odds'], edge=b['edge'], pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
        if r.md >= 14 and abs(L) >= 0.5 and r.s_anc == r.s_anc:
            s7 = r.s_0 + 0.7 * (r.s_anc - r.s_0); side = 1 if L < 0 else -1; o = oh if side == 1 else oa
            if 1.70 <= o <= 2.10:
                e = picks.fav_edge_q((T + s7) / 2, (T - s7) / 2, side, -abs(L), o)
                if e >= 0.10: rows.append(dict(mid=mid, book=bk, role='fav', side=side, hcap=-abs(L), odds=o, edge=e, pnl=picks.settle(r.gd, side, -abs(L), o)))
        if 6 <= r.md <= 13 and abs(L) in (0.5, 0.75):
            side = 1 if L < 0 else -1; o = oh if side == 1 else oa
            if 1.70 <= o <= 2.10:
                e = picks.fav_edge_q(r.xg_h, r.xg_a, side, -abs(L), o)
                if e >= 0: rows.append(dict(mid=mid, book=bk, role='fav', side=side, hcap=-abs(L), odds=o, edge=e, pnl=picks.settle(r.gd, side, -abs(L), o)))
B = pd.DataFrame(rows).merge(M[['season', 'league', 'md', 'wd', 'gd', 's_mod', 's_m', 's_pr', 's_cu', 'home', 'away']], left_on='mid', right_index=True)
B['team'] = np.where(B.side == 1, B.home, B.away); B['opp'] = np.where(B.side == 1, B.away, B.home)
B['dep'] = pd.cut(B.hcap.abs(), [-.1, .75, 1.25, 9], labels=['κοντη ≤0.75', 'μεση 1-1.25', 'βαθια ≥1.5'])
BK = ('Pinnacle', 'Crown', 'Bet365')
def fm(d, short=False):
    """ενας αριθμος: ROI ολων των book-picks (μεσος), n = μεσος αριθμος picks ανα βιβλιο, σεζον θετικες, βιβλια θετικα."""
    if len(d) < 6: return f'n{len(d) / 3:5.0f}' + ' ' * 26
    ps = d.groupby('season').pnl.mean(); pb = d.groupby('book').pnl.mean()
    return f'n{len(d) / max(d.book.nunique(), 1):5.0f} {100 * d.pnl.mean():+6.1f}% {d.pnl.sum() / max(d.book.nunique(), 1):+6.1f}u σεζ {int((ps > 0).sum())}/{ps.size} βιβλ {int((pb > 0).sum())}/{pb.size}'
out = print
out('\n' + '=' * 110 + '\nΑ. ΧΑΡΤΗΣ ΑΠΩΛΕΙΩΝ — ολα τα picks των live κανονων (ROI μεσος βιβλιων· n = picks ανα βιβλιο· 1-6 μονο Crown/Bet365)\n' + '=' * 110)
for wd in ('1-5', '6', '7-14', '15+'):
    x = B[B.wd == wd]; out(f'\n [{wd}] ΟΛΑ: {fm(x)}')
    for role in ('dog', 'fav'):
        y = x[x.role == role]
        if len(y) < 6: continue
        out(f'   {role:4s} {fm(y)}')
        for dep, z in y.groupby('dep', observed=True): out(f'       {str(dep):13s} {fm(z)}')
        out(f'       εντος      {fm(y[y.side == 1])}'); out(f'       εκτος      {fm(y[y.side == -1])}')
x = B[B.md.between(5, 13) & (B.role == 'dog')]
out('\n [6-14 dogs] ανα edge:'); [out(f'       {str(k):12s} {fm(v)}') for k, v in x.groupby(pd.cut(x.edge, [0.099, .13, .18, .25, 9]), observed=True)]
out(' [6-14 dogs] ανα λιγκα:'); [out(f'       {k:13s} {fm(v)}') for k, v in x.groupby('league')]
out(' [6-14 dogs] ανα σεζον:'); [out(f'       {k:13s} {fm(v)}') for k, v in x.groupby('season')]
# ================= Β =================
out('\n' + '=' * 110 + '\nΒ. ΠΟΙΟΣ ΕΧΕΙ ΔΙΚΙΟ — ολα τα ματς (οχι μονο picks). Σφαλμα = πραγματικη διαφορα γκολ − υπεροχη (RMSE· μικροτερο = καλυτερο)\n' + '=' * 110)
A = M[M.s_m.notna() & M.s_pr.notna() & M.s_cu.notna()].copy()
A['wb'] = pd.cut(A.md, [-1, 2, 4, 5, 9, 13, 19, 99], labels=['1-3', '4-5', '6', '7-10', '11-14', '15-20', '21+'])
def ols(y, X):
    X = np.c_[np.ones(len(y)), X]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (e @ e) / (len(y) - X.shape[1])); return b, se
out(f'   {"αγων":6s} {"n":>5s} | RMSE αγορα  live  περσινο φετινο | κοινη: αγορα + β·(live−αγορα) | β περσινο−αγορα / φετινο−αγορα (μαζι)')
for wb, x in A.groupby('wb', observed=True):
    y = x.gd.values.astype(float); rm = lambda s_: np.sqrt(np.mean((y - s_) ** 2))
    b1, se1 = ols(y - x.s_m.values, (x.s_mod - x.s_m).values)
    b2, se2 = ols(y - x.s_m.values, np.c_[(x.s_pr - x.s_m).values, (x.s_cu - x.s_m).values])
    out(f'   {str(wb):6s} {len(x):5d} | {rm(x.s_m):.3f}  {rm(x.s_mod):.3f}  {rm(x.s_pr):.3f}  {rm(x.s_cu):.3f}  | β {b1[1]:+.2f} (t {b1[1] / se1[1]:+.1f})'
        f'                | {b2[1]:+.2f} (t {b2[1] / se2[1]:+.1f}) / {b2[2]:+.2f} (t {b2[2] / se2[2]:+.1f})')
out('\n   ΣΥΜΠΙΕΣΗ (σκοπια φαβορι αγορας): μεσος υπεροχης αγορα / live / περσινο / φετινο / ΠΡΑΓΜΑΤΙΚΟ')
for wb in ('1-5', '6', '7-14', '15+'):
    x = A[A.md.between(*{'1-5': (0, 4), '6': (5, 5), '7-14': (6, 13), '15+': (14, 99)}[wb])]
    sg = np.sign(x.s_m)
    for lab, c in (('ισορροπα <0.5', x.s_m.abs() < .5), ('μεσαια 0.5-1.2', x.s_m.abs().between(.5, 1.2)), ('ανισα ≥1.2', x.s_m.abs() > 1.2)):
        z = x[c]; sz = sg[c]
        out(f'   [{wb:4s}] {lab:15s} n{len(z):5d}: {(z.s_m * sz).mean():.2f} / {(z.s_mod * sz).mean():.2f} / {(z.s_pr * sz).mean():.2f} / {(z.s_cu * sz).mean():.2f} / {(z.gd * sz).mean():.2f}')
# ---- απο που ερχεται η διαφωνια στα picks 6-14 ----
out('\n   DOG PICKS 6-14: τι λενε τα κομματια για την ΙΔΙΑ πλευρα (θετικο = υπερ του pick, γκολ πανω απο την αγορα)')
x = B[B.md.between(5, 13) & (B.role == 'dog')].copy()
for c in ('s_mod', 's_pr', 's_cu'): x[c + '_v'] = (x[c] - x.s_m) * x.side
x['act'] = (x.gd - x.s_m) * x.side
out(f'     live {x.s_mod_v.mean():+.2f} · περσινο {x.s_pr_v.mean():+.2f} · φετινο {x.s_cu_v.mean():+.2f} · ΠΡΑΓΜΑΤΙΚΟ {x.act.mean():+.2f} (±{x.act.std() / np.sqrt(len(x)):.2f})')
x['src'] = np.select([(x.s_pr_v > .15) & (x.s_cu_v > .15), x.s_pr_v > .15, x.s_cu_v > .15], ['και τα δυο', 'κυριως περσινο', 'κυριως φετινο'], 'κανενα μονο του')
for k, v in x.groupby('src'): out(f'     πηγη διαφωνιας: {k:16s} {fm(v)} · πραγματικο−αγορα {v.act.mean():+.2f}')
# ================= Γ =================
out('\n' + '=' * 110 + '\nΓ. ΚΑΜΠΥΛΗ ΜΑΘΗΣΗΣ — ανα αγωνιστικη: RMSE live − RMSE αγορας (0 = ιδιο με αγορα) · |live − αγορα| · κλιση πραγματικου πανω στη διαφωνια\n' + '=' * 110)
for md, x in A.groupby(A.md.clip(upper=30)):
    if md not in (0, 2, 4, 5, 6, 7, 8, 9, 10, 12, 14, 17, 20, 25, 30): continue
    y = x.gd.values.astype(float); b1, se1 = ols(y - x.s_m.values, (x.s_mod - x.s_m).values)
    out(f'   αγων {md + 1:2d}{"+" if md == 30 else " "} n{len(x):4d} · ΔRMSE {np.sqrt(np.mean((y - x.s_mod) ** 2)) - np.sqrt(np.mean((y - x.s_m) ** 2)):+.3f} · |διαφωνια| {(x.s_mod - x.s_m).abs().mean():.2f} · β {b1[1]:+.2f} (t {b1[1] / se1[1]:+.1f})')
# ================= Δ =================
out('\n' + '=' * 110 + '\nΔ. ΜΕΡΟΛΗΨΙΑ ΑΓΟΡΑΣ ανα αγωνιστικη — πραγματικο − αγορα (σκοπια φαβορι· αρνητικο = η αγορα ΦΟΥΣΚΩΝΕΙ το φαβορι)\n' + '=' * 110)
for lab, c in (('φαβορι ≥1 (ολα)', A.s_m.abs() >= 1), ('  εντος', A.s_m >= 1), ('  εκτος', A.s_m <= -1), ('φαβορι 0.5-1', A.s_m.abs().between(.5, 1))):
    z = A[c]; sg = np.sign(z.s_m); r_ = (z.gd - z.s_m) * sg
    cells = []
    for wb, v in r_.groupby(z.wb, observed=True):
        cells.append(f'{wb}: {v.mean():+.2f}±{v.std() / np.sqrt(len(v)):.2f}')
    out(f'   {lab:18s} ' + ' · '.join(cells))
# ================= Ε =================
out('\n' + '=' * 110 + '\nΕ. ΣΤΑΘΕΡΟΤΗΤΑ ΟΜΑΔΩΝ\n' + '=' * 110)
SQ = json.load(open('squads_all.json', encoding='utf-8')); MG = json.load(open('managers_all.json', encoding='utf-8'))
ALLP = pd.concat([preds(V)[['league', 'season', 'home', 'away', 'md', 'date']]]); ALLP = ALLP.reset_index()
SEA_ALL = ['2122'] + SEAS
TEAMS = {}
for lg in LG:
    for sea in SEA_ALL:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        TEAMS[(lg, sea)] = {m['home']['id'] for m in d.values()} | {m['away']['id'] for m in d.values()}
        for mid, m in d.items():
            if mid not in ALLP.mid.values and m.get('hs') is not None:
                pass
# matches ανα ομαδα-σεζον με σειρα (απο data json για να εχουμε και 2122)
TG = {}
for lg in LG:
    for sea in SEA_ALL:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        ms = sorted(((pd.to_datetime(m['date'].replace(' UTC', ''), format='%a, %b %d, %Y, %H:%M'), mid, m) for mid, m in d.items() if m.get('hs') is not None))
        for dt, mid, m in ms:
            for side, t in (('h', m['home']['id']), ('a', m['away']['id'])): TG.setdefault((t, sea), []).append((dt, mid, side))
def prevsea(s): return f'{int(s[:2]) - 1:02d}{int(s[2:]) - 1:02d}'
ST = {}
for lg in LG:
    for sea in SEAS:
        for t in TEAMS.get((lg, sea), ()):
            cur = TG.get((t, sea), []); prv = TG.get((t, prevsea(sea)), [])
            promoted = t not in TEAMS.get((lg, prevsea(sea)), set())
            c_now = MG.get(cur[0][1], {}).get(cur[0][2], [None])[0] if cur else None
            c_prev = MG.get(prv[-1][1], {}).get(prv[-1][2], [None])[0] if prv else None
            mins_prev = {}
            for _, mid, sd in prv:
                for p, mn in (SQ.get(mid, {}).get(sd, {}).get('p') or {}).items(): mins_prev[p] = mins_prev.get(p, 0) + (mn or 0)
            tot = keep = 0
            for _, mid, sd in cur[:5]:
                for p, mn in (SQ.get(mid, {}).get(sd, {}).get('p') or {}).items():
                    tot += mn or 0; keep += (mn or 0) * (mins_prev.get(p, 0) >= 900)
            ST[(t, sea)] = dict(promoted=promoted, coach_same=(c_now is not None and c_now == c_prev), cont=keep / tot if tot else np.nan)
# G_prior: το περσινο μας vs αγορα στις αγων 1-4 (ανα ομαδα) — ΓΝΩΣΤΟ πριν την 6η
E = A[A.md <= 3]
gp = {}
for r in E.itertuples():
    d_ = r.s_pr - r.s_m
    gp.setdefault((r.home, r.season), []).append(d_); gp.setdefault((r.away, r.season), []).append(-d_)
for k, v in gp.items():
    if k in ST: ST[k]['gprior'] = float(np.mean(v)); ST[k]['n_g'] = len(v)
SD = pd.DataFrame([dict(team=k[0], season=k[1], **v) for k, v in ST.items()])
out(f'   ομαδες-σεζον {len(SD)} · νεοφωτιστες {int(SD.promoted.sum())} · ιδιος προπονητης {SD.coach_same.mean():.0%} · συνεχεια λεπτων μεσος {SD.cont.mean():.2f} · |G_prior| μεσος {SD.gprior.abs().mean():.2f}')
out(f'   συσχετισεις: |G_prior| με συνεχεια {SD.gprior.abs().corr(SD.cont):+.2f} · με ιδιο προπονητη {SD.gprior.abs().corr(SD.coach_same.astype(float)):+.2f}')
SI = SD.set_index(['team', 'season'])
for side in ('team', 'opp'):
    for c in ('promoted', 'coach_same', 'cont', 'gprior'):
        B[f'{side}_{c}'] = [SI[c].get((t, s_), np.nan) for t, s_ in zip(B[side], B.season)]
B['team_g'] = B.team_gprior * 1.0; B['opp_g'] = B.opp_gprior * 1.0
# ---- περιγραφικο: ROI dogs 6-14 & 15+ ανα σταθεροτητα ----
for wlab, wsel in (('6-14', B.md.between(5, 13)), ('15+', B.md >= 14)):
    x = B[wsel & (B.role == 'dog')]
    out(f'\n   DOGS {wlab}: ολα {fm(x)}')
    out(f'     ΔΙΚΗ ΜΑΣ ομαδα νεοφωτιστη {fm(x[x.team_promoted == True])} · οχι {fm(x[x.team_promoted == False])}')
    out(f'     ΑΝΤΙΠΑΛΟΣ νεοφωτιστος     {fm(x[x.opp_promoted == True])} · οχι {fm(x[x.opp_promoted == False])}')
    out(f'     δικη μας ιδιος προπονητης {fm(x[x.team_coach_same == True])} · αλλαξε {fm(x[x.team_coach_same == False])}')
    out(f'     αντιπαλος ιδιος προπονητης {fm(x[x.opp_coach_same == True])} · αλλαξε {fm(x[x.opp_coach_same == False])}')
    for lab, col in (('συνεχεια δικης μας', 'team_cont'), ('συνεχεια αντιπαλου', 'opp_cont')):
        q = pd.qcut(x[col], 3, labels=['χαμηλη', 'μεση', 'ψηλη'])
        out(f'     {lab:22s} ' + ' | '.join(f'{k}: {fm(v)}' for k, v in x.groupby(q, observed=True)))
    # G_prior προσανατολισμενο: θετικο = το περσινο μας ειναι ΠΙΟ αισιοδοξο απο την αγορα για τη δικη μας ομαδα στην αρχη
    for lab, col in (('G_prior δικης μας (περσινο − αγορα στην αρχη)', 'team_g'), ('G_prior αντιπαλου', 'opp_g')):
        q = pd.cut(x[col], [-9, -.25, -.08, .08, .25, 9], labels=['≤−.25', '−.25…−.08', '±.08', '.08….25', '≥.25'])
        out(f'     {lab}:'); [out(f'         {str(k):10s} {fm(v)}') for k, v in x.groupby(q, observed=True)]
# ---- ΦΙΛΤΡΟ (LOSO) ----
out('\n   ΦΙΛΤΡΟ ΣΤΑΘΕΡΟΤΗΤΑΣ (dogs 6-14) — LOSO: ορια απο τις 3 αλλες σεζον, κριση στην 4η')
X = B[B.md.between(5, 13) & (B.role == 'dog')].copy()
GRID = list(itertools.product([0.08, 0.15, 0.25, 0.4, 9], [0, 0.5, 0.6, 0.7], [False, True], ['both', 'team', 'opp']))
def keep_mask(d, gthr, cthr, coach, who):
    m = pd.Series(True, index=d.index)
    sides = ['team', 'opp'] if who == 'both' else [who]
    for sd in sides:
        m &= (d[f'{sd}_g'].abs() <= gthr) | (gthr >= 9)
        m &= (d[f'{sd}_cont'] >= cthr) | (cthr == 0)
        m &= (d[f'{sd}_promoted'] != True)
        if coach: m &= d[f'{sd}_coach_same'] == True
    return m
res = []
for test in SEAS:
    tr = X[X.season != test]; te = X[X.season == test]
    best = max(GRID, key=lambda p: tr[keep_mask(tr, *p)].pnl.sum())
    k_ = te[keep_mask(te, *best)]
    res.append(k_); out(f'     εκτος {test}: ορια |G|≤{best[0]} συνεχεια≥{best[1]} προπονητης={best[2]} ποιος={best[3]} → {fm(k_)} · σημερα {fm(te)}')
R = pd.concat(res)
out(f'     LOSO ΣΥΝΟΛΟ: φιλτρο {fm(R)} · σημερα {fm(X)}')
ps_f = R.groupby('season').pnl.mean(); ps_b = X.groupby('season').pnl.mean(); pb = R.groupby('book').pnl.mean()
c1 = int(((ps_f > 0) & (ps_f > ps_b.reindex(ps_f.index))).sum()) >= 3
c2 = pb.get('Pinnacle', -1) > 0 and ((pb.get('Crown', -1) > 0) or (pb.get('Bet365', -1) > 0)); c3 = len(R) / 3 >= 60
out(f'     ΚΡΙΣΗ: (1) {"✓" if c1 else "✗"} (2) {"✓" if c2 else "✗"} (3) {"✓" if c3 else "✗"} → {"ΠΕΡΝΑ" if (c1 and c2 and c3) else "ΔΕΝ ΠΕΡΝΑ"}')
out('\n   ΣΤΑΘΕΡΑ ορια (ενδεικτικα, ΟΧΙ LOSO): και οι δυο ομαδες |G_prior| ≤ 0.15, οχι νεοφωτιστες')
for wlab, wsel in (('6-14', B.md.between(5, 13)), ('15+', B.md >= 14)):
    x = B[wsel & (B.role == 'dog')]; m_ = keep_mask(x, 0.15, 0, False, 'both')
    out(f'     {wlab}: σταθερες {fm(x[m_])} · υπολοιπα {fm(x[~m_])}')
B.to_pickle('core7_early_weakness_picks.pkl'); SD.to_csv('core7_team_stability.csv', index=False)
