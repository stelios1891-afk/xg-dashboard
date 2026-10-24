# -*- coding: utf-8 -*-
"""t69_return_game.py — ΤΟ ΜΑΤΣ ΤΗΣ ΕΠΙΣΤΡΟΦΗΣ, ΓΝΩΣΤΟ ΣΤΟ ΑΝΟΙΓΜΑ (24/10/2026, Στελιος «τρεξ'το»· αφορμη Knueppel/Charlotte).
Τα t5/t13 (20/10) εκριναν μπονους ΑΠΟ ΤΟ 2ο ματς μετα την επιστροφη (✗)· το ιδιο το ματς επιστροφης δεν ελεγχθηκε ρεαλιστικα
(το t13 «ματς 1» +3.9 ειχε το λαθος οτι η βαση εβγαζε ακομα τον παικτη ως απων).
ΠΛΑΙΣΙΟ = t22 (αντιγραφο live: production + carry + B2B + ζωνη + μεταγραφες, απουσιες απο την ΕΠΙΣΗΜΗ αναφορα με πιθανοτητες
  Out 1 / D .97 / Q .45 / P .07 οπως το live)· τιμη = γραμμη Crown στο ΑΝΟΙΓΜΑ· αναφορα = η τελευταια με ωρα ≤ ανοιγμα.
ΕΠΙΣΤΡΟΦΗ = παικτης που ΠΑΙΖΕΙ στο ματς, ελειψε τα ν ≥1 αμεσως προηγουμενα ματς της ομαδας του (οχι ανταλλαγη) και ειναι ρολου:
  mid   = μ.ο. ≥20′ στις 10 τελευταιες φετινες εμφανισεις του για την ομαδα πριν την απουσια
  start = πρωτη φετινη εμφανιση (για οποια ομαδα), η ομαδα εχει παιξει ≥1 ματς, περσινος μ.ο. (10 τελευταια) ≥20′
ΓΝΩΣΤΗ ΣΤΟ ΑΝΟΙΓΜΑ = η ομαδα εχει ηδη δηλωσει για ΑΥΤΟ το ματς (≥1 γραμμη με ωρα ≤ ανοιγμα) ΚΑΙ ο παικτης ΔΕΝ ειναι Out/Doubtful/
  Questionable στη δηλωση αυτου του ματς. Τοτε η ΒΑΣΗ (οπως το live) ΔΕΝ τον μετραει απωνα (ακομα κι αν ηταν Out στη χθεσινη αναφορα).
ΚΟΣΤΟΣ του = 0.75·(αξια+2)·λεπτα/48 (λεπτα: mid = μ.ο. πριν την απουσια · start = περσινος).
ΕΚΔΟΧΗ: + k · κοστος · f(ν) στο περιθωριο της ομαδας του, ΜΟΝΟ στο ματς επιστροφης· f: «σταθερο» = 1 · «με διαρκεια» = ν/(ν+5)
  (ποσο απο τη δυναμη χτιστηκε χωρις αυτον)· k ∈ {0.25 … 1.5}· LOSO (επιλογη k,f με RMSE στις αλλες σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (εγκριθηκε 24/10 πριν το τρεξιμο): RMSE καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος edge ≥8%
  Οκτ-Δεκ οχι χειροτερο απο −1.5pp. ROI ολης της σεζον = πληροφορια. «πρωτο ματς σεζον» χωριστα = μονο πληροφορια.
Εξοδος: nba_tests/t69_return_game_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
_src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα', None)")[0]
_G = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 't22'}
with contextlib.redirect_stdout(_B()): exec(_src, _G)
sys.stdout.reconfigure(encoding='utf-8')
globals().update({k: v for k, v in _G.items() if not k.startswith('__') and k not in ('out', 'P')})
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# ---------- εμφανισεις ----------
PLAY = collections.defaultdict(dict)                         # (ομαδα, ημερα) → {pid: λεπτα}
for r in A2.itertuples(index=False): PLAY[(r.team, r.dd)][r.pid] = r.MIN
TDAYS = collections.defaultdict(list)                        # (ομαδα, σεζον) → ημερες ματς
for r in A2.drop_duplicates(['team', 'dd']).itertuples(index=False): TDAYS[(r.team, int(r.s))].append(r.dd)
for k in TDAYS: TDAYS[k].sort()
APP = collections.defaultdict(list)                          # (pid, σεζον) → [(ημερα, ομαδα)]
for r in A2.itertuples(index=False): APP[(r.pid, int(r.s))].append((r.dd, r.team))
for k in APP: APP[k].sort()
P2K = {(r.pid, r.team, int(r.s)): r.k for r in A2.drop_duplicates(['pid', 'team', 's']).itertuples(index=False)}
def prev_avg(pid, s):
    h = [m for dd_, tt, m in sorted((x[0], x[1], PLAY[(x[1], x[0])][pid]) for x in APP.get((pid, s), []))][-10:]
    return float(np.mean(h)) if h else None

def returns(t, s, d):
    """[(pid, τυπος, ν χαμενα, λεπτα)] για την ομαδα t στο ματς της d."""
    days = [x for x in TDAYS.get((t, s), []) if x < d]
    if not days: return []
    res = []
    for pid, mn in PLAY.get((t, d), {}).items():
        if mn <= 0: continue
        apps = [x for x in APP[(pid, s)] if x[0] < d]
        mine = [x for x in apps if x[1] == t]
        if not apps:                                           # πρωτη φετινη εμφανιση
            pv = prev_avg(pid, s - 1)
            if pv is None or pv < 20: continue
            res.append((pid, 'start', len(days), pv)); continue
        if not mine: continue                                  # ηρθε με ανταλλαγη
        lastp = mine[-1][0]
        if any(x[0] > lastp and x[1] != t for x in apps): continue
        nm = sum(1 for x in days if x > lastp)
        if nm < 1: continue
        m = mins(pid, t, s, lastp + np.timedelta64(1, 'D'))
        if m is None or m < 20: continue
        res.append((pid, 'mid', nm, m))
    return res

def today(t, d, tau):
    st = {}; sub = False
    for ep, k, s_ in REP_BY.get((t, d), ()):
        if ep <= tau: st[k] = s_; sub = True
    return sub, st
def abs_cost_ex(t, d, s, tau, W, ex):
    c = 0.0
    for k, stt in status_at(t, d, tau).items():
        if k in ex: continue
        w = W.get(stt)
        if not w: continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        c += w * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
    return c

# ---------- ανα ματς: ΒΑΣΗ στο ανοιγμα + επιστροφες ----------
REC = []; EVT = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    tau = rows[0][0]; ln = line_at(rows, tau, sw)
    if not ln: continue
    L, oh, oa, fair, _ = ln; h, a, d = G.home.values[i], G.away.values[i], dD[i]
    bon = {}                                                   # sg → [(κοστος, ν, τυπος)]
    exs = {}
    for t, sg in ((h, 1), (a, -1)):
        sub, st = today(t, d, tau); ex = set()
        for pid, typ, nm, mn in returns(t, s, d):
            k = P2K.get((pid, t, s))
            known = sub and st.get(k) not in ('Out', 'Doubtful', 'Questionable')
            c = 0.75 * (value(pid, s - 1) + 2.0) * mn / 48
            EVT.append(dict(i=i, sea=s, sg=sg, typ=typ, nm=nm, c=c, known=known, mon=int(G.date.dt.month.values[i])))
            if known: ex.add(k); bon.setdefault(sg, []).append((c, nm, typ))
        exs[t] = ex
    m0 = VNO[i] - abs_cost_ex(h, d, s, tau, W_B, exs[h]) + abs_cost_ex(a, d, s, tau, W_B, exs[a])
    REC.append(dict(i=i, sea=s, m0=m0, act=ACT[i], L=L, oh=oh, oa=oa, fair=fair, bon=bon, mon=int(G.date.dt.month.values[i])))
RI = {r['i']: r for r in REC}

# ---------- ΠΕΡΙΓΡΑΦΙΚΟ ----------
P(f'NBA · ΜΑΤΣ ΕΠΙΣΤΡΟΦΗΣ γνωστο στο ανοιγμα · σεζον {sorted({r["sea"] for r in REC})} · ματς με γραμμη ανοιγματος {len(REC)}')
EK = [e for e in EVT if e['i'] in RI]
P(f'επιστροφες (παικτες ρολου): {len(EK)} · γνωστες στο ανοιγμα {sum(e["known"] for e in EK)} '
  f'(start {sum(e["known"] and e["typ"] == "start" for e in EK)}, mid {sum(e["known"] and e["typ"] == "mid" for e in EK)})')
P('\n=== ΠΕΡΙΓΡΑΦΙΚΟ: ομαδα με ΓΝΩΣΤΗ επιστροφη — υπολοιπο υπερ της (π.), μεσος ± SE (n) ===')
P('   μοντελο = πραγματικο − ΒΑΣΗ (live, χωρις μπονους) · αγορα = πραγματικο − δικαιη γραμμη ανοιγματος · + = η ομαδα πηγε ΚΑΛΥΤΕΡΑ')
def grp(lab, sel):
    xs = [(RI[e['i']], e) for e in EK if e['known'] and sel(e)]
    if len(xs) < 2: P(f'   {lab:30s} —'); return
    mo = np.array([(r['act'] - r['m0']) * e['sg'] for r, e in xs]); mk = np.array([(r['act'] - r['fair']) * e['sg'] for r, e in xs])
    cc = np.mean([e['c'] for r, e in xs])
    P(f'   {lab:30s} μοντελο {mo.mean():+5.2f}±{mo.std(ddof=1) / np.sqrt(len(mo)):4.2f} · αγορα {mk.mean():+5.2f}±{mk.std(ddof=1) / np.sqrt(len(mk)):4.2f} '
      f'· μεσο κοστος παικτη {cc:.2f} π. (n {len(xs)})')
grp('ΟΛΕΣ', lambda e: True)
grp('πρωτο ματς σεζον (start)', lambda e: e['typ'] == 'start')
grp('μεσα στη σεζον, ελειψε 1-2', lambda e: e['typ'] == 'mid' and e['nm'] <= 2)
grp('μεσα στη σεζον, ελειψε 3-9', lambda e: e['typ'] == 'mid' and 3 <= e['nm'] <= 9)
grp('μεσα στη σεζον, ελειψε 10+', lambda e: e['typ'] == 'mid' and e['nm'] >= 10)
grp('κοστος ≥2 π. (σταρ)', lambda e: e['c'] >= 2)
grp('κοστος 1-2 π.', lambda e: 1 <= e['c'] < 2)
grp('κοστος <1 π.', lambda e: e['c'] < 1)

# ---------- ΕΚΔΟΧΕΣ ----------
SEAS = sorted({r['sea'] for r in REC})
def margin(r, k, form):
    m = r['m0']
    for sg, L_ in r['bon'].items():
        for c, nm, typ in L_: m += sg * k * c * (1.0 if form == 'σταθερο' else nm / (nm + 5))
    return m
def rmse(k, form, ys):
    e = [(r['act'] - margin(r, k, form)) ** 2 for r in REC if r['sea'] in ys]; return float(np.sqrt(np.mean(e)))
def picks(mf, months=None):
    res = collections.defaultdict(list)
    for r in REC:
        if months and r['mon'] not in months: continue
        m = mf(r); pw, pp, pl = cover_(m, r['L'], SIG_); e1, e2 = pw * r['oh'] + pp - 1, pl * r['oa'] + pp - 1
        sd, e, od_ = (1, e1, r['oh']) if e1 >= e2 else (-1, e2, r['oa'])
        if e < .08: continue
        x = (r['act'] + r['L']) * sd; res[r['sea']].append((od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0))
    allr = [x for v in res.values() for x in v]
    return (100 * np.mean(allr) if allr else 0.0), len(allr), sum(allr), sum(sum(v) > 0 for v in res.values())
GRID = [(k, f) for k in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5) for f in ('σταθερο', 'με διαρκεια')]
OD = (10, 11, 12)
def line(lab, mf, rm_s):
    r1, n1, u1, p1 = picks(mf, OD); r2, n2, u2, p2 = picks(mf)
    bet = sum(rm_s[Y] < base_s[Y] - 1e-6 for Y in SEAS)
    P(f'{lab:28s} | {np.sqrt(np.mean([(r["act"] - mf(r)) ** 2 for r in REC])):8.4f} | {bet}/{len(SEAS)} | {r1:+6.1f}% ({n1:4d}) {u1:+6.1f}μ {p1}/{len(SEAS)} | {r2:+6.1f}% ({n2:4d}) {u2:+6.1f}μ')
    return bet, r1
base_s = {Y: rmse(0, 'σταθερο', [Y]) for Y in SEAS}
P(f'\n=== ΕΚΔΟΧΕΣ (ματς με γραμμη ανοιγματος· RMSE αλλαζει μονο στα ματς με γνωστη επιστροφη) ===')
P(f'{"εκδοχη":28s} | RMSE ολα | καλ.| ROI Οκτ-Δεκ ≥8%  (n)   μοναδ θετ | ROI ολη ≥8%  (n)   μοναδ')
_, rb = line('ΒΑΣΗ (live)', lambda r: r['m0'], base_s)
for k, f in GRID:
    line(f'k={k:<4g} {f}', lambda r, k=k, f=f: margin(r, k, f), {Y: rmse(k, f, [Y]) for Y in SEAS})
sel = {Y: min(GRID, key=lambda g: rmse(g[0], g[1], [x for x in SEAS if x != Y])) for Y in SEAS}
P(f'LOSO επιλογες ανα σεζον: ' + ' · '.join(f'{Y}: k={sel[Y][0]:g} {sel[Y][1]}' for Y in SEAS))
mfL = lambda r: margin(r, sel[r['sea']][0], sel[r['sea']][1])
rmL = {Y: rmse(sel[Y][0], sel[Y][1], [Y]) for Y in SEAS}
bet, r1 = line('LOSO', mfL, rmL)
P('ανα σεζον RMSE (ΒΑΣΗ / LOSO): ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rmL[Y]:.4f}' for Y in SEAS))
need = 4 if len(SEAS) >= 5 else len(SEAS) - 1
P(f'\nΚΡΙΤΗΡΙΟ: RMSE καλυτερο {bet}/{len(SEAS)} (απαιτ. ≥{need}) · ROI Οκτ-Δεκ {r1:+.1f}% vs ΒΑΣΗ {rb:+.1f}% (Δ {r1 - rb:+.1f}pp, απαιτ. > −1.5) → '
  f'{"ΠΕΡΝΑΕΙ" if bet >= need and r1 - rb > -1.5 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
# πληροφορια: παιζοντας τυφλα την ομαδα με γνωστη επιστροφη στο ανοιγμα
xs = [(RI[e['i']], e) for e in EK if e['known'] and e['c'] >= 1]
rr = []
for r, e in xs:
    od_ = r['oh'] if e['sg'] == 1 else r['oa']; x = (r['act'] + r['L']) * e['sg']; rr.append((od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0))
if rr: P(f'πληροφορια: τυφλα η ομαδα με γνωστη επιστροφη (κοστος ≥1 π.) στο ανοιγμα: {100 * np.mean(rr):+.1f}% ({len(rr)}, {sum(rr):+.1f}μ)')
open(os.path.join(SC, 't69_return_game_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
