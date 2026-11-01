# -*- coding: utf-8 -*-
"""t29_janfeb.py — ΙΑΝΟΥΑΡΙΟΣ-ΦΕΒΡΟΥΑΡΙΟΣ: 7 ΤΕΣΤ (21/10/2026, Στελιος «τρεξτα ολα»). Βαση: _t29_games.csv (t29_build: αντιγραφο live,
απουσιες απο επισημες αναφορες στη στιγμη της τιμης, Crown ανοιγμα & Τ−30′). Picks = edge ≥8%, αγωνας ≤70 (ο Απριλιος εχει δικους κανονες).
ΠΕΡΙΟΔΟΙ: Οκτ-Δεκ · Ιαν · Φεβ · Μαρ.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο):
 0 ΒΑΣΗ (περιγραφικο): ROI ανα περιοδο × φαβορι/αουτσαιντερ × μεγεθος γραμμης × εντος/εκτος.
 1 ΤΥΧΗ: αναμενομενο ROI απο το ΚΛΕΙΣΙΜΟ (πιθανοτητα καλυψης με τη δικαιη γραμμη κλεισιματος × τιμη μας) vs πραγματικο· z = διαφορα/SE.
   «Τυχη» αν |z| < 2.
 2 ΒΑΘΜΟΝΟΜΗΣΗ: ζωνες edge (8-10, 10-14, 14-20, 20+) → δηλωμενο / αναμενομενο απο κλεισιμο / πραγματικο, ανα περιοδο.
   Τ2: κατωφλι Ιαν-Φεβ ∈ {8,10,12,15}% (αλλοι μηνες 8%), LOSO με μοναδες στις αλλες 4· ΠΕΡΝΑ αν μοναδες LOSO > 8% συνολικα ΚΑΙ οχι χειροτερα σε ≥4/5 σεζον.
 3 ΦΟΡΜΑ: φ = μεσος ορος (πραγματικο − μοντελο) της ομαδας στα 10 προηγουμενα ματς (≥5), διαφορα γηπ − φιλ.
   Περιγραφικο: συσχετιση με το λαθος του μοντελου ΚΑΙ με το λαθος του κλεισιματος (αν η αγορα το εχει ηδη).
   Τ3: m + k·φ, k ∈ {0,.1,.2,.3,.5}, LOSO με RMSE (ολη η σεζον) · ΠΕΡΝΑ αν RMSE Ιαν-Φεβ καλυτερο σε ≥4/5 ΚΑΙ ROI Ιαν-Φεβ ΚΑΙ ολης οχι χειροτερα >1.5pp.
 4 ΠΡΟΓΡΑΜΜΑ: 3ο ματς σε 4 μερες · 4ο σε 6 · 1ο ματς μετα το All-Star · τελευταιο πριν (ανα ομαδα).
   Περιγραφικο: λαθος μοντελου & κλεισιματος απο την πλευρα της ομαδας. Τ4: c·(3σε4_γηπ − 3σε4_φιλ) + c·(4σε6 …), c ∈ {0,.5,1,1.5,2}, LOSO RMSE·
   ΠΕΡΝΑ αν RMSE καλυτερο σε ≥4/5 ΚΑΙ ROI ολης οχι χειροτερο >1.5pp.
 5 ΠΡΟΘΕΣΜΙΑ ΜΕΤΑΓΡΑΦΩΝ: 10 μερες πριν / 10 μετα · ομαδες «πωλητες» (ποσοστο <.45) / «αγοραστες» (≥.55) / μεσαιες.
   Περιγραφικο: λαθος μοντελου & αγορας, ROI picks υπερ/κοντρα.
 6 ΠΡΟΩΡΗ «ΠΑΡΑΤΗΣΗ» (ESPN πενταδες, Ιαν-Μαρ): π = μεσος ορος της πτωσης λεπτων 5 βασικων στα 5 προηγουμενα ματς (ex-ante).
   Ομαδες με π ≤ −15 vs υπολοιπες: λαθος μοντελου & κλεισιματος στο επομενο ματς, ROI picks υπερ/κοντρα. (Περιγραφικο· αν t ≥ 2 → μελλοντικο τεστ.)
Εξοδος: t29_janfeb_out.txt"""
import os, sys, collections, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
sys.stdout.reconfigure(encoding='utf-8')
import pickle
SIG = float(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['SIG'])
X = pd.read_csv(os.path.join(SC, '_t29_games.csv'))
X['d'] = pd.to_datetime(X.date)
X['per'] = X.mon.map({10: 'Οκτ-Δεκ', 11: 'Οκτ-Δεκ', 12: 'Οκτ-Δεκ', 1: 'Ιαν', 2: 'Φεβ', 3: 'Μαρ', 4: 'Απρ'})
PERS = ('Οκτ-Δεκ', 'Ιαν', 'Φεβ', 'Μαρ')
SEASONS = sorted(X.sea.unique())
_N = NormalDist()
def cover(m, L):
    if abs(L - round(L)) < 1e-9:
        pw = _N.cdf((m + L - 0.5) / SIG); pl = _N.cdf((-m - L - 0.5) / SIG); return pw, 1 - pw - pl, pl
    pw = _N.cdf((m + L) / SIG); return pw, 0.0, 1 - pw
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def picks(D, col='m', thr=0.08, thr_fn=None):
    R = []
    for r in D.itertuples(index=False):
        m = getattr(r, col); pw, pp, pl = cover(m, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        t_ = thr_fn(r) if thr_fn else thr
        if e < t_: continue
        x = (r.act + r.L) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        cw, cp, cl = cover(r.cfair, r.L); evc = ((cw if sd == 1 else cl) * od + cp - 1)
        R.append(dict(i=r.i, sea=r.sea, per=r.per, mon=r.mon, sd=sd, e=e, own=r.L if sd == 1 else -r.L, res=res, evc=evc,
                      clv=sd * (r.cfair - r.fair), home=sd == 1, team=r.home if sd == 1 else r.away))
    return pd.DataFrame(R)
def cell(d):
    if d is None or not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
B = X[X.gn <= 70]
P('NBA · ΙΑΝΟΥΑΡΙΟΣ-ΦΕΒΡΟΥΑΡΙΟΣ · 7 τεστ · αντιγραφο live + επισημες αναφορες · picks ≥8%, αγωνας ≤70')
# ================= 0 =================
P(''); P('=== 0 · ΒΑΣΗ ανα περιοδο ===')
PK = {tau: picks(B[B.tau == tau]) for tau in ('ανοιγμα', 'Τ−30′')}
for tau, pk in PK.items():
    P(f'  -- {tau} --')
    for per in PERS:
        d = pk[pk.per == per]
        P(f'  {per:8s} ολα {cell(d)} · CLV {d.clv.mean():+.2f} | φαβορι {cell(d[d.own < 0])} | αουτσ. {cell(d[d.own > 0])}')
        if tau == 'ανοιγμα':
            bins = [(-99, -7, 'φαβ ≥7'), (-7, -3, 'φαβ 3-7'), (-3, 0, 'φαβ <3'), (0, 3, 'αουτσ <3'), (3, 7, 'αουτσ 3-7'), (7, 99, 'αουτσ ≥7')]
            P('           ' + ' · '.join(f'{lab} {100 * d[(d.own > lo) & (d.own <= hi)].res.mean():+.0f}% ({len(d[(d.own > lo) & (d.own <= hi)])})' for lo, hi, lab in bins))
            P(f'           εντος {cell(d[d.home])} · εκτος {cell(d[~d.home])}')
# ================= 1 =================
P(''); P('=== 1 · ΤΥΧΗ: πραγματικο ROI vs αναμενομενο απο το κλεισιμο ===')
for tau, pk in PK.items():
    for per in PERS:
        d = pk[pk.per == per]; diff = d.res.mean() - d.evc.mean(); se = d.res.std() / np.sqrt(len(d)); z = diff / se
        P(f'  {tau:8s} {per:8s} n {len(d):4d} · πραγματικο {100 * d.res.mean():+5.1f}% · αναμενομενο απο κλεισιμο {100 * d.evc.mean():+5.1f}% · '
          f'διαφορα {100 * diff:+5.1f}pp (z {z:+.1f}) → {"μεσα στην τυχη" if abs(z) < 2 else "ΕΚΤΟΣ τυχης"}')
# ================= 2 =================
P(''); P('=== 2 · ΒΑΘΜΟΝΟΜΗΣΗ (ανοιγμα): δηλωμενο edge / αναμενομενο απο κλεισιμο / πραγματικο ===')
pk = PK['ανοιγμα']
for per in PERS:
    d = pk[pk.per == per]
    P(f'  {per:8s} ' + ' · '.join(f'{lo}-{hi}%: {100 * x.e.mean():.0f}/{100 * x.evc.mean():+.0f}/{100 * x.res.mean():+.0f}% ({len(x)})'
                                  for lo, hi in ((8, 10), (10, 14), (14, 20), (20, 99)) for x in [d[(d.e >= lo / 100) & (d.e < hi / 100)]]))
P('  Τ2 · κατωφλι Ιαν-Φεβ (LOSO, μοναδες ολης της σεζον):')
for tau in ('ανοιγμα', 'Τ−30′'):
    U = {}
    for th in (8, 10, 12, 15):
        p = picks(B[B.tau == tau], thr_fn=lambda r, th=th: th / 100 if r.mon in (1, 2) else 0.08)
        U[th] = (p.groupby('sea').res.sum().reindex(SEASONS, fill_value=0), p)
    ch, diff = [], []
    for s in SEASONS:
        best = max(U, key=lambda k: (U[k][0].drop(s).sum(), -k)); ch.append(best); diff.append(U[best][0][s] - U[8][0][s])
    ok = sum(1 for x in diff if x >= 0); tot = sum(diff)
    P(f'    {tau:8s} ' + ' · '.join(f'{k}%: Ιαν-Φεβ {cell(U[k][1][U[k][1].mon.isin([1, 2])])}' for k in U))
    P(f'             LOSO {ch} · μοναδες − 8%: {tot:+.1f} (οχι χειροτερο {ok}/5: {", ".join(f"{x:+.1f}" for x in diff)}) → {"ΠΕΡΝΑ" if tot > 0 and ok >= 4 else "ΔΕΝ περνα"}')
# ================= μακρια μορφη ανα ομαδα =================
O = X[X.tau == 'ανοιγμα'].sort_values(['d', 'i']).copy()
TL = []
for r in O.itertuples(index=False):
    TL.append((r.i, r.sea, r.d, r.home, r.away, 1, r.m, r.act, r.cfair))
    TL.append((r.i, r.sea, r.d, r.away, r.home, -1, -r.m, -r.act, -r.cfair))
T = pd.DataFrame(TL, columns=['i', 'sea', 'd', 't', 'o', 'sg', 'mt', 'at', 'ct'])
T['rm'] = T['at'] - T.mt; T['rc'] = T['at'] - T.ct
T = T.sort_values(['sea', 't', 'd']).reset_index(drop=True)
g = T.groupby(['sea', 't'])
T['form'] = g.rm.transform(lambda s: s.shift(1).rolling(10, min_periods=5).mean())
T['prev_d'] = g.d.shift(1)
T['rest'] = (T.d - T.prev_d).dt.days
dl = {k: g.d.shift(k) for k in (2, 3)}
T['in4'] = ((T.d - dl[2]).dt.days <= 3).astype(int)                              # 3ο ματς σε 4 μερες
T['in6'] = ((T.d - dl[3]).dt.days <= 5).astype(int)                              # 4ο ματς σε 6 μερες
T['next_rest'] = (g.d.shift(-1) - T.d).dt.days
T['mon'] = T.d.dt.month
T['asb_after'] = ((T.mon == 2) & (T.rest >= 5)).astype(int)                     # 1ο μετα το All-Star (≥5 μερες κενο τον Φεβρουαριο)
T['asb_before'] = ((T.mon == 2) & (T.next_rest >= 5)).astype(int)
T['w'] = (T['at'] > 0).astype(int)
T['pct'] = g.w.transform(lambda s: s.shift(1).expanding().mean())
TK = {(r.i, r.t): r for r in T.itertuples(index=False)}
def team_feat(df, col):
    h = np.array([getattr(TK[(i, t)], col) for i, t in zip(df.i, df.home)], dtype=float)
    a = np.array([getattr(TK[(i, t)], col) for i, t in zip(df.i, df.away)], dtype=float)
    return h, a
B = B.copy()
fh, fa = team_feat(B, 'form'); B['fd'] = np.nan_to_num(fh) - np.nan_to_num(fa)
for c in ('in4', 'in6', 'asb_after', 'asb_before'):
    h, a = team_feat(B, c); B[c + '_d'] = h - a
B['per'] = B.mon.map({10: 'Οκτ-Δεκ', 11: 'Οκτ-Δεκ', 12: 'Οκτ-Δεκ', 1: 'Ιαν', 2: 'Φεβ', 3: 'Μαρ', 4: 'Απρ'})
rmse = lambda e: float(np.sqrt(np.mean(np.square(e))))
JF = B.mon.isin([1, 2])
# ================= 3 =================
P(''); P('=== 3 · ΦΟΡΜΑ (υπολοιπο μοντελου στα 10 προηγουμενα ματς) ===')
Tf = T[T.form.notna()]
for per, ms in (('Οκτ-Δεκ', (10, 11, 12)), ('Ιαν-Φεβ', (1, 2)), ('Μαρ', (3,))):
    d = Tf[Tf.mon.isin(ms)]
    b_m = np.polyfit(d.form, d.rm, 1)[0]; b_c = np.polyfit(d.form, d.rc, 1)[0]
    P(f'  {per:8s} n {len(d)} · κλιση στο λαθος ΜΟΝΤΕΛΟΥ {b_m:+.3f} (r {np.corrcoef(d.form, d.rm)[0, 1]:+.3f}) · στο λαθος ΚΛΕΙΣΙΜΟΥ {b_c:+.3f} (r {np.corrcoef(d.form, d.rc)[0, 1]:+.3f})')
def test_add(name, KS, colf, crit_all=True):
    for tau in ('ανοιγμα', 'Τ−30′'):
        D = B[B.tau == tau].copy(); res = {}
        for k in KS:
            D['mk'] = D.m + k * colf(D); res[k] = D[['sea', 'mon', 'act', 'mk']].assign(err=D.act - D.mk)
        ch, win = [], 0
        for s in SEASONS:
            best = min(KS, key=lambda k: rmse(res[k][res[k].sea != s].err)); ch.append(best)
            a0 = res[KS[0]]; a1 = res[best]; m0 = (a0.sea == s) & a0.mon.isin([1, 2]) if not crit_all else (a0.sea == s)
            win += rmse(a1[m0].err) < rmse(a0[m0].err) or best == KS[0]
        # ROI με το LOSO k ανα σεζον
        D['mk'] = D.m + np.array([dict(zip(SEASONS, ch))[s] for s in D.sea]) * colf(D)
        p0 = picks(D, col='m'); p1 = picks(D, col='mk')
        r_jf = (100 * p1[p1.mon.isin([1, 2])].res.mean(), 100 * p0[p0.mon.isin([1, 2])].res.mean()); r_all = (100 * p1.res.mean(), 100 * p0.res.mean())
        ok = win >= 4 and (r_jf[0] - r_jf[1]) > -1.5 and (r_all[0] - r_all[1]) > -1.5 and any(c != KS[0] for c in ch)
        P(f'  {name} · {tau:8s} RMSE ' + ' · '.join(f'{k}: {rmse(res[k].err):.4f}' for k in KS) + f' | LOSO {ch} · καλυτερο {win}/5 · '
          f'ROI Ιαν-Φεβ {r_jf[1]:+.1f} → {r_jf[0]:+.1f}% · ολη {r_all[1]:+.1f} → {r_all[0]:+.1f}% → {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"}')
test_add('Τ3 φορμα', (0, .1, .2, .3, .5), lambda D: D.fd, crit_all=False)
# ================= 4 =================
P(''); P('=== 4 · ΠΡΟΓΡΑΜΜΑ (λαθος απο την πλευρα της ομαδας · μοντελο / κλεισιμο) ===')
for c, lab in (('in4', '3ο ματς σε 4 μερες'), ('in6', '4ο ματς σε 6 μερες'), ('asb_after', '1ο μετα το All-Star'), ('asb_before', 'τελευταιο πριν το All-Star')):
    for per, ms in (('ολη', tuple(range(1, 13))), ('Ιαν-Φεβ', (1, 2))):
        d1 = T[(T[c] == 1) & T.mon.isin(ms)]; d0 = T[(T[c] == 0) & T.mon.isin(ms)]
        tt = (d1.rm.mean() - d0.rm.mean()) / np.sqrt(d1.rm.var() / len(d1) + d0.rm.var() / len(d0))
        P(f'  {lab:26s} {per:8s} n {len(d1):5d} · μοντελο {d1.rm.mean():+5.2f} (vs {d0.rm.mean():+5.2f}, t {tt:+.1f}) · κλεισιμο {d1.rc.mean():+5.2f} (vs {d0.rc.mean():+5.2f})')
test_add('Τ4 3σε4+4σε6', (0, .5, 1, 1.5, 2), lambda D: -(D.in4_d + D.in6_d), crit_all=True)
# ================= 5 =================
P(''); P('=== 5 · ΠΡΟΘΕΣΜΙΑ ΜΕΤΑΓΡΑΦΩΝ (10 μερες πριν / 10 μετα) ===')
DL = {2022: '2022-02-10', 2023: '2023-02-09', 2024: '2024-02-08', 2025: '2025-02-06', 2026: '2026-02-05'}
T['dl'] = (T.d - pd.to_datetime(T.sea.map(DL))).dt.days
T['cls'] = np.where(T.pct < .45, 'πωλητης', np.where(T.pct >= .55, 'αγοραστης', 'μεσαια'))
for lab, lo, hi in (('10 μερες ΠΡΙΝ', -10, 0), ('10 μερες ΜΕΤΑ', 1, 10)):
    for cl in ('πωλητης', 'μεσαια', 'αγοραστης'):
        d = T[(T.dl >= lo) & (T.dl <= hi) & (T.cls == cl)]
        P(f'  {lab:14s} {cl:10s} n {len(d):4d} · λαθος μοντελου {d.rm.mean():+5.2f} · κλεισιματος {d.rc.mean():+5.2f}')
DATE = dict(zip(X.i, X.d)); pk = PK['ανοιγμα'].copy(); pk['dl'] = [(DATE[i] - pd.Timestamp(DL[s])).days for i, s in zip(pk.i, pk.sea)]
for lab, lo, hi in (('10 μερες ΠΡΙΝ', -10, 0), ('10 μερες ΜΕΤΑ', 1, 10), ('υπολοιπος Ιαν-Φεβ', None, None)):
    d = pk[(pk.dl >= lo) & (pk.dl <= hi)] if lo is not None else pk[pk.mon.isin([1, 2]) & ~pk.dl.between(-10, 10)]
    P(f'  picks {lab:18s} {cell(d)} · CLV {d.clv.mean():+.2f}')
# ================= 6 =================
P(''); P('=== 6 · ΠΡΟΩΡΗ ΠΑΡΑΤΗΣΗ (ESPN πενταδες: πτωση λεπτων 5 βασικων στα 5 προηγουμενα ματς) ===')
F = pd.read_csv(os.path.join(SC, '_t25_feats.csv')); F['d'] = pd.to_datetime(F.date); F = F.sort_values(['sea', 'team', 'd'])
F['dc'] = F.core_min - F.core_min_avg
F['drop5'] = F.groupby(['sea', 'team']).dc.transform(lambda s: s.shift(1).rolling(5, min_periods=4).mean())
FK = {(r.d, r.team): r.drop5 for r in F.itertuples(index=False)}
T['drop5'] = [FK.get((d, t), np.nan) for d, t in zip(T.d, T.t)]
for per, ms in (('Ιαν-Φεβ', (1, 2)), ('Μαρ', (3,))):
    d = T[T.mon.isin(ms) & T.drop5.notna()]
    for lab, mm in (('πτωση ≤ −15', d.drop5 <= -15), ('−15…−5', (d.drop5 > -15) & (d.drop5 <= -5)), ('> −5', d.drop5 > -5)):
        x = d[mm]; P(f'  {per:8s} {lab:12s} n {len(x):4d} · λαθος μοντελου {x.rm.mean():+5.2f} · κλεισιματος {x.rc.mean():+5.2f} · ποσοστο νικων πριν {x.pct.mean():.2f}')
    x = d[d.drop5 <= -15]; y = d[d.drop5 > -5]
    tt = (x.rc.mean() - y.rc.mean()) / np.sqrt(x.rc.var() / len(x) + y.rc.var() / len(y)); P(f'           t (κλεισιμο, ≤−15 vs >−5) {tt:+.1f}')
DK = {(i, t): v for i, t, v in zip(T.i, T.t, T.drop5)}; pk = PK['ανοιγμα']; pk = pk.assign(drop_us=[DK.get((i, t), np.nan) for i, t in zip(pk.i, pk.team)])
for lab, mm in (('υπερ ομαδας με πτωση ≤−15', pk.drop_us <= -15), ('υπερ ομαδας >−5', pk.drop_us > -5)):
    d = pk[mm & pk.mon.isin([1, 2, 3])]; P(f'  picks Ιαν-Μαρ {lab:28s} {cell(d)}')
P(''); P('=== Τ2β (ΝΕΑ υποθεση απο τον πινακα 2 — μετα το τρεξιμο): ενιαιο κατωφλι ΟΛΗ τη σεζον ∈ {8,9,10,12}%, LOSO μοναδες ===')
for tau in ('ανοιγμα', 'Τ−30′'):
    U = {}
    for th in (8, 9, 10, 12):
        p = picks(B[B.tau == tau], thr=th / 100); U[th] = (p.groupby('sea').res.sum().reindex(SEASONS, fill_value=0), p)
    ch, diff = [], []
    for s_ in SEASONS:
        best = max(U, key=lambda k: (U[k][0].drop(s_).sum(), -k)); ch.append(best); diff.append(U[best][0][s_] - U[8][0][s_])
    P(f'  {tau:8s} ' + ' · '.join(f'{k}%: {cell(U[k][1])}' for k in U) + f' | LOSO {ch} · − 8%: {sum(diff):+.1f} ({", ".join(f"{x:+.1f}" for x in diff)})')
open(os.path.join(SC, 't29_janfeb_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
