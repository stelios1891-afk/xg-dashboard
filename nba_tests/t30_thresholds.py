# -*- coding: utf-8 -*-
"""t30_thresholds.py — Τ9 ΚΑΤΩΦΛΙ + Τ10 ΜΕΤΑ ΤΗΝ ΠΡΟΘΕΣΜΙΑ ΜΕΤΑΓΡΑΦΩΝ με τον ΑΚΡΙΒΗ κανονα του live (21/10/2026, Στελιος «τρεξτο»).
Βαση: _t29_games.csv (αντιγραφο live + επισημες αναφορες). Κανονας live: edge ≥ κατωφλι ΚΑΙ στην πρωτη γραμμη ΚΑΙ στην τρεχουσα (με την τρεχουσα
προβλεψη)· αγωνας ≤75· στους 71-75 οχι pick υπερ ομαδας χωρις κινητρο κοντρα σε ομαδα με κινητρο (live απο 21/10).
ΔΥΟ ΕΚΔΟΧΕΣ ΣΤΙΓΜΗΣ: Α = pick στο ανοιγμα (πρωτη = τρεχουσα γραμμη) · Β = pick στο Τ−30′ (προβλεψη Τ−30′, edge ≥ κατωφλι και στη γραμμη ανοιγματος
ΚΑΙ στη γραμμη Τ−30′, τιμη Τ−30′) — τα δυο ακρα του τι κανει ο scanner.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 Τ9 επιλογες: «8» (σημερα) · «10» · «12» (ολη η σεζον) · «8/12» (12% μονο Ιαν-Φεβ) · «10/12» (10% + 12% Ιαν-Φεβ).
   LOSO: για καθε σεζον η επιλογη με τις περισσοτερες μοναδες στις αλλες 4, εφαρμογη στην 5η.
   ΠΕΡΝΑ αν, ΣΤΟ Α ΚΑΙ ΣΤΟ Β: μοναδες LOSO > «8» συνολικα ΚΑΙ οχι χειροτερα σε ≥4/5 σεζον. (Και περιγραφικα Οκτ-Δεκ χωριστα.)
 Τ10 μερες 1-10 μετα την προθεσμια: «κανονικα» · «12%» · «15%» · «κανενα pick»· ιδιο LOSO/κριτηριο, πανω στο «8» ΚΑΙ πανω στον νικητη του Τ9.
Εξοδος: t30_thresholds_out.txt"""
import os, sys, io, contextlib
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
import pickle
SIG = float(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['SIG'])
X = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X['d'] = pd.to_datetime(X.date)
t27 = open(os.path.join(SC, 't27_april_rules.py'), encoding='utf-8').read().split("OLD = pd.read_csv")[0]
ns = {'__file__': os.path.join(SC, 't27_april_rules.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(t27, ns)
sys.stdout.reconfigure(encoding='utf-8')
GRP, PRACT, SEAS, dDg = ns['GRP'], ns['PRACT'], ns['SEAS'], ns['dD']
NOM = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING'); MOT = ('ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN')
def grp(i, t):
    s, d = SEAS[i], dDg[i]; g = GRP.get((s, d, t), 'νωρις')
    return 'ΧΚ' if (g in NOM or (s, d, t) in PRACT) else ('ΜΚ' if g in MOT else 'αλλο')
O = X[X.tau == 'ανοιγμα'].set_index('i'); C = X[X.tau == 'Τ−30′'].set_index('i')
ids = O.index.intersection(C.index)
DL = {2022: '2022-02-10', 2023: '2023-02-09', 2024: '2024-02-08', 2025: '2025-02-06', 2026: '2026-02-05'}
_N = NormalDist()
def cover(m, L):
    if abs(L - round(L)) < 1e-9:
        pw = _N.cdf((m + L - 0.5) / SIG); pl = _N.cdf((-m - L - 0.5) / SIG); return pw, 1 - pw - pl, pl
    pw = _N.cdf((m + L) / SIG); return pw, 0.0, 1 - pw
def edges(m, L, oh, oa):
    pw, pp, pl = cover(m, L); return pw * oh + pp - 1, pl * oa + pp - 1
rows = []
for i in ids:
    o, c = O.loc[i], C.loc[i]
    if o.gn > 75: continue
    gh, ga = (grp(i, o.home), grp(i, o.away)) if o.gn >= 71 else ('', '')
    dl = (o.d - pd.Timestamp(DL[int(o.sea)])).days
    eA = edges(o.m, o.L, o.oh, o.oa)
    eB_cur = edges(c.m, c.L, c.oh, c.oa); eB_first = edges(c.m, o.L, o.oh, o.oa)
    for sd in (1, -1):
        k = 0 if sd == 1 else 1
        if o.gn >= 71 and ((gh, ga) if sd == 1 else (ga, gh)) == ('ΧΚ', 'ΜΚ'): continue
        for ver, e, e0, L, od in (('Α', eA[k], eA[k], o.L, o.oh if sd == 1 else o.oa), ('Β', eB_cur[k], eB_first[k], c.L, c.oh if sd == 1 else c.oa)):
            x = (o.act + L) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            rows.append(dict(i=i, sea=int(o.sea), mon=int(o.mon), dl=dl, sd=sd, ver=ver, e=min(e, e0), res=res, clv=sd * (c.cfair - (o.fair if ver == 'Α' else c.fair))))
R = pd.DataFrame(rows)
SEASONS = sorted(R.sea.unique())
def thr_of(opt, mon, dl, post=None):
    base, jf = {'8': (8, 8), '10': (10, 10), '12': (12, 12), '8/12': (8, 12), '10/12': (10, 12)}[opt]
    t = jf if mon in (1, 2) else base
    if post is not None and 1 <= dl <= 10:
        t = {'κανονικα': t, '12%': max(t, 12), '15%': max(t, 15), 'κανενα': 999}[post]
    return t / 100
def select(ver, opt, post=None):
    d = R[R.ver == ver]
    th = np.array([thr_of(opt, m, l, post) for m, l in zip(d.mon, d.dl)])
    d = d[d.e >= th]
    return d.sort_values('e', ascending=False).drop_duplicates('i')          # μια πλευρα ανα ματς (η μεγαλυτερη)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
def loso(ver, opts, mk, base):
    S = {k: mk(k) for k in opts}; U = {k: S[k].groupby('sea').res.sum().reindex(SEASONS, fill_value=0) for k in opts}
    ch, diff = [], []
    for s in SEASONS:
        best = max(opts, key=lambda k: (U[k].drop(s).sum(), k == base)); ch.append(best); diff.append(U[best][s] - U[base][s])
    return S, ch, diff
P('NBA · Τ9/Τ10 ΚΑΤΩΦΛΙ με τον κανονα του live (πρωτη + τρεχουσα γραμμη) · αγωνας ≤75 · Α = ανοιγμα · Β = Τ−30′')
P(''); P('=== Τ9 · ΚΑΤΩΦΛΙ ===')
OPTS = ('8', '10', '12', '8/12', '10/12'); verdict9 = {}
for ver in ('Α', 'Β'):
    S, ch, diff = loso(ver, OPTS, lambda k: select(ver, k), '8')
    for k in OPTS:
        d = S[k]; P(f'  {ver} «{k:5s}» ολη {cell(d)} | Οκτ-Δεκ {cell(d[d.mon.isin([10, 11, 12])])} | Ιαν-Φεβ {cell(d[d.mon.isin([1, 2])])} | Μαρ-Απρ {cell(d[d.mon.isin([3, 4])])}')
    ok = sum(1 for x in diff if x >= 0); tot = sum(diff); verdict9[ver] = (tot > 0 and ok >= 4, ch)
    P(f'  {ver} LOSO επιλογες {ch} · μοναδες − «8»: {tot:+.1f} (οχι χειροτερο {ok}/5: {", ".join(f"{x:+.1f}" for x in diff)}) → {"✓" if verdict9[ver][0] else "✗"}'); P('')
P(f'  → Τ9 {"ΠΕΡΝΑ" if verdict9["Α"][0] and verdict9["Β"][0] else "ΔΕΝ περνα"} (κριτηριο: ✓ και στο Α και στο Β)')
from collections import Counter
win9 = Counter(verdict9['Α'][1] + verdict9['Β'][1]).most_common(1)[0][0]
P(''); P(f'=== Τ10 · ΜΕΡΕΣ 1-10 ΜΕΤΑ ΤΗΝ ΠΡΟΘΕΣΜΙΑ (πανω στο «8» και πανω στο «{win9}») ===')
POSTS = ('κανονικα', '12%', '15%', 'κανενα')
for base_opt in ('8', win9):
    res10 = {}
    for ver in ('Α', 'Β'):
        S, ch, diff = loso(ver, POSTS, lambda k: select(ver, base_opt, post=k), 'κανονικα')
        P(f'  βαση «{base_opt}» · {ver}: ' + ' · '.join(f'{k}: μετα-προθεσμια {cell(S[k][S[k].dl.between(1, 10)])}' for k in POSTS))
        ok = sum(1 for x in diff if x >= 0); tot = sum(diff); res10[ver] = tot > 0 and ok >= 4
        P(f'           LOSO {ch} · μοναδες − κανονικα: {tot:+.1f} (οχι χειροτερο {ok}/5: {", ".join(f"{x:+.1f}" for x in diff)}) → {"✓" if res10[ver] else "✗"}')
    P(f'  → Τ10 (βαση «{base_opt}») {"ΠΕΡΝΑ" if res10["Α"] and res10["Β"] else "ΔΕΝ περνα"}'); P('')
open(os.path.join(SC, 't30_thresholds_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
