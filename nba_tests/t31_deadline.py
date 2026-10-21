# -*- coding: utf-8 -*-
"""t31_deadline.py — ΒΑΘΙΑ ΑΝΑΛΥΣΗ «ΜΕΤΑ ΤΗΝ ΠΡΟΘΕΣΜΙΑ ΜΕΤΑΓΡΑΦΩΝ» (21/10/2026, Στελιος «παμε να αναλυσουμε παραπανω το 3»).
Βαση: _t29_games.csv (αντιγραφο live ΜΕ μεταγραφες, απουσιες απο επισημες αναφορες). Picks: κανονας live (πρωτη = τρεχουσα γραμμη στο ανοιγμα),
8% (και 12% Ιαν-Φεβ, οπως το live απο 21/10).
ΕΡΩΤΗΣΕΙΣ (περιγραφικα):
 Α ΧΡΟΝΟΣ: μερες μετα την προθεσμια 1-5 · 6-10 · 11-20 · 21-30 — και ΠΡΙΝ / ΜΕΤΑ το All-Star break (1ο ματς μετα απο ≥5 μερες κενο τον Φεβ).
 Β ΠΟΙΟΣ ΑΛΛΑΞΕ: ομαδες με μεταγραφες της προθεσμιας (παικτης με νεα ομαδα, 1ο ματς −20…+15 μερες απο την προθεσμια):
    «πηρε» (λεπτα που ηρθαν − λεπτα που εφυγαν ≥ +10) · «εδωσε» (≤ −10) · «αλλαξε ισα» · «καμια». Λαθος μοντελου & κλεισιματος, ROI picks υπερ/κοντρα.
 Γ ΤΙ PICKS: φαβορι/αουτσαιντερ, εντος/εκτος, ποιος ειναι ο αντιπαλος.
 Δ ΤΙ ΒΛΕΠΕΙ ΤΟ ΜΟΝΤΕΛΟ: διορθωση μεταγραφων (μοντελο με − χωρις) για τις ομαδες που «πηραν»/«εδωσαν» vs τι εγινε.
 Ε 3 παραδειγματα χαμενων picks με λεπτομερειες.
Εξοδος: t31_deadline_out.txt"""
import os, sys, collections
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
sys.stdout.reconfigure(encoding='utf-8')
import pickle
SIG = float(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['SIG'])
X = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X['d'] = pd.to_datetime(X.date)
DL = {2022: '2022-02-10', 2023: '2023-02-09', 2024: '2024-02-08', 2025: '2025-02-06', 2026: '2026-02-05'}
X['dl'] = [(d - pd.Timestamp(DL[s])).days for d, s in zip(X.d, X.sea)]
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
A = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MIN', 'season', 'stype'])
A = A[A.stype == 'RS'].copy(); A['MIN'] = pd.to_numeric(A.MIN, errors='coerce').fillna(0); A = A[A.MIN > 0]
A['team'] = A.TEAM_ABBREVIATION.replace(AB); A['s'] = A.season.str[:4].astype(int) + 1; A['d'] = pd.to_datetime(A.GAME_DATE)
A = A[A.s.isin(DL.keys())].sort_values('d')
# --- μεταγραφες προθεσμιας ---
MOVES = []
for (pid, s), g in A.groupby(['PLAYER_ID', 's']):
    seq = g[['d', 'team', 'MIN']].values
    for k in range(1, len(seq)):
        if seq[k][1] != seq[k - 1][1]:
            dn = seq[k][0]; dd = (dn - pd.Timestamp(DL[s])).days
            if -20 <= dd <= 15:
                old = g[(g.team == seq[k - 1][1]) & (g.d < dn)].MIN.tail(10).mean()
                new = g[(g.team == seq[k][1]) & (g.d >= dn)].MIN.head(5).mean()
                MOVES.append(dict(s=s, pid=pid, name=g.PLAYER_NAME.iloc[0], frm=seq[k - 1][1], to=seq[k][1], dnew=dn, old_min=old, new_min=new))
M = pd.DataFrame(MOVES)
NET = collections.defaultdict(float); INV = collections.defaultdict(float); WHO = collections.defaultdict(list)
for r in M.itertuples(index=False):
    NET[(r.s, r.to)] += r.new_min; INV[(r.s, r.to)] += r.new_min; WHO[(r.s, r.to)].append(f'+{r.name} {r.new_min:.0f}′')
    NET[(r.s, r.frm)] -= r.old_min; INV[(r.s, r.frm)] += r.old_min; WHO[(r.s, r.frm)].append(f'−{r.name} {r.old_min:.0f}′')
def tclass(s, t):
    n, inv = NET.get((s, t), 0.0), INV.get((s, t), 0.0)
    if inv < 10: return 'καμια'
    return 'πηρε' if n >= 10 else ('εδωσε' if n <= -10 else 'ισα')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'NBA · ΜΕΤΑ ΤΗΝ ΠΡΟΘΕΣΜΙΑ ΜΕΤΑΓΡΑΦΩΝ · μεταγραφες παραθυρου: {len(M)} παικτες · ' +
  ' · '.join(f'{s}: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(tclass(s, t) for t in set(A[A.s == s].team)).items()) for s in DL))
_N = NormalDist()
def cover(m, L):
    if abs(L - round(L)) < 1e-9:
        pw = _N.cdf((m + L - 0.5) / SIG); pl = _N.cdf((-m - L - 0.5) / SIG); return pw, 1 - pw - pl, pl
    pw = _N.cdf((m + L) / SIG); return pw, 0.0, 1 - pw
O = X[(X.tau == 'ανοιγμα') & (X.gn <= 75)].copy()
# ASB: πρωτη μερα μετα το κενο ≥4 μερων τον Φεβρουαριο (ανα σεζον)
ASB = {}
for s, g in O[O.mon == 2].groupby('sea'):
    ds = sorted(g.d.unique()); gaps = [(ds[k], (ds[k] - ds[k - 1]).days) for k in range(1, len(ds))]
    ASB[s] = max(gaps, key=lambda x: x[1])[0]
O['post_asb'] = [d >= ASB.get(s, pd.Timestamp('2100-01-01')) for d, s in zip(O.d, O.sea)]
P('All-Star (1η μερα μετα το κενο): ' + ' · '.join(f'{s}: {str(d)[:10]} (προθεσμια +{(d - pd.Timestamp(DL[s])).days})' for s, d in sorted(ASB.items())))
R = []
for r in O.itertuples(index=False):
    pw, pp, pl = cover(r.m, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
    sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
    us, them = (r.home, r.away) if sd == 1 else (r.away, r.home)
    x = (r.act + r.L) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    R.append(dict(i=r.i, sea=r.sea, d=r.d, mon=r.mon, dl=r.dl, asb=r.post_asb, sd=sd, e=e, own=r.L if sd == 1 else -r.L, res=res,
                  clv=sd * (r.cfair - r.fair), us=us, them=them, cu=tclass(r.sea, us), ct=tclass(r.sea, them), m=r.m, m0=r.m0, L=r.L, act=r.act))
R = pd.DataFrame(R)
PK = R[(R.e >= np.where(R.mon.isin([1, 2]), .12, .08))]
PK8 = R[R.e >= .08]
def cell(d):
    if not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):3d}, {d.res.sum():+5.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
# ---------- Α ----------
P(''); P('=== Α · ΧΡΟΝΟΣ (picks στο ανοιγμα· 8% / live 12% Ιαν-Φεβ) ===')
for lab, lo, hi in (('10-1 μερες ΠΡΙΝ', -10, 0), ('1-5 μετα', 1, 5), ('6-10 μετα', 6, 10), ('11-20 μετα', 11, 20), ('21-30 μετα', 21, 30)):
    a = PK8[PK8.dl.between(lo, hi)]; b = PK[PK.dl.between(lo, hi)]
    P(f'  {lab:16s} 8%: {cell(a)} | live: {cell(b)}')
w = PK8[PK8.dl.between(1, 20)]
P(f'  μετα-προθεσμια 1-20 · ΠΡΙΝ το All-Star {cell(w[~w.asb])} · ΜΕΤΑ το All-Star {cell(w[w.asb])}')
# ---------- Β ----------
P(''); P('=== Β · ΠΟΙΟΣ ΑΛΛΑΞΕ (μερες 1-20 μετα) — λαθος απο την πλευρα της ομαδας ===')
TL = []
for r in O[O.dl.between(1, 20)].itertuples(index=False):
    for t, sg in ((r.home, 1), (r.away, -1)):
        TL.append(dict(sea=r.sea, t=t, cls=tclass(r.sea, t), rm=sg * (r.act - r.m), rc=sg * (r.act - r.cfair), tr=sg * (r.m - r.m0 + 0 * r.abs_h)))
TT = pd.DataFrame(TL)
for c in ('πηρε', 'εδωσε', 'ισα', 'καμια'):
    d = TT[TT.cls == c]
    P(f'  {c:6s} n {len(d):4d} · λαθος μοντελου {d.rm.mean():+5.2f} · λαθος κλεισιματος {d.rc.mean():+5.2f}')
P('  picks (8%, μερες 1-20) ανα ομαδα που στηριζουμε → αντιπαλο:')
for (cu, ct), d in sorted(w.groupby(['cu', 'ct']), key=lambda x: -len(x[1])):
    if len(d) >= 6: P(f'     {cu:6s} → {ct:6s} {cell(d)}')
# ---------- Γ ----------
P(''); P('=== Γ · ΤΙ PICKS (8%, μερες 1-10 / 11-20) ===')
for lab, lo, hi in (('1-10', 1, 10), ('11-20', 11, 20)):
    d = PK8[PK8.dl.between(lo, hi)]
    P(f'  {lab:6s} φαβορι {cell(d[d.own < 0])} | αουτσ. {cell(d[d.own > 0])} | εντος {cell(d[d.sd == 1])} | εκτος {cell(d[d.sd == -1])}')
    P(f'         ζωνες edge: ' + ' · '.join(f'{lo2}-{hi2}% {100 * x.res.mean():+.0f}% ({len(x)})' for lo2, hi2 in ((8, 12), (12, 20), (20, 99)) for x in [d[(d.e >= lo2 / 100) & (d.e < hi2 / 100)]]))
# ---------- Ε ----------
P(''); P('=== Ε · ΠΑΡΑΔΕΙΓΜΑΤΑ χαμενων picks (μερες 1-10) ===')
for r in PK8[PK8.dl.between(1, 10) & (PK8.res < 0)].sort_values('e', ascending=False).head(4).itertuples():
    P(f'  {str(r.d)[:10]} στηριζουμε {r.us} {r.own:+g} vs {r.them} · edge {100 * r.e:.0f}% · μοντελο {r.us} {(r.m if r.sd == 1 else -r.m):+.1f} (διορθ. απουσιων/μεταγρ. {(r.m - r.m0) * r.sd:+.1f}) · '
      f'αποτελεσμα {r.act * r.sd:+.0f} · {r.us}: {", ".join(WHO.get((r.sea, r.us), [])) or "—"} | {r.them}: {", ".join(WHO.get((r.sea, r.them), [])) or "—"}')
open(os.path.join(SC, 't31_deadline_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
