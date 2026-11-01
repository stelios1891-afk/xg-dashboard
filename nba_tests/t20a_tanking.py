# -*- coding: utf-8 -*-
"""t20a_tanking.py — ΑΔΥΝΑΜΕΣ vs TANKING (21/10/2026, Στελιος: «ξεχωρισε τις αδυναμες με τις ομαδες tanking — δεν ειναι ολες οι χαμηλα
στη βαθμολογια κοντα στο Νο 1 του draft»). ΠΕΡΙΓΡΑΦΙΚΟ.
ΟΡΙΣΜΟΙ (γραφτηκαν πριν το τρεξιμο), με τη βαθμολογια ΩΣ τη μερα του αγωνα:
  ΑΔΥΝΑΜΗ = θεση 23-30 στη λιγκα (ποσοστο νικων) — οπως το t19.
  TANKING = ≥40 ματς ΚΑΙ ≥6 νικες πισω απο τη 10η θεση της περιφερειας (εκτος play-in, ουσιαστικα χωρις στοχο).
  «ΜΑΧΗ ΓΙΑ ΝΟ 1» = ≥40 ματς ΚΑΙ μια απο τις 3 χειροτερες της λιγκας (ιδιες πιθανοτητες λοταριας 14%).
Μοντελο = live (production + B2B + απουσιες αντικ. −2 + μεταγραφες α1). Picks = edge ≥8% στο ανοιγμα (Crown). Ανα περιοδο (χωρις Απριλιο,
και ο Απριλιος χωριστα για συγκριση). Εξοδος: t20a_tanking_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE = ns['BASE']; MKH = ns['MKH']
inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']
V = BASE + ns['adj'](1.0, -2.0, None)
EAST = set('ATL BOS BRK CHO CHI CLE DET IND MIA MIL NYK ORL PHI TOR WAS'.split())
MON = G.date.dt.month.values
PER = np.array(['Οκτ-Δεκ' if m in (10, 11, 12) else 'Ιαν-Φεβ' if m in (1, 2) else 'Μαρ' if m == 3 else 'Απρ' for m in MON])
W = collections.Counter(); L_ = collections.Counter(); ST = {}
day = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'): day[(SEAS_G[i], dD[i])].append(i)
for (s, d) in sorted(day):
    teams = {t for (ss, t) in set(W) | set(L_) if ss == s}
    for i in day[(s, d)]: teams |= {G.home.values[i], G.away.values[i]}
    rec = {t: (W[(s, t)], L_[(s, t)]) for t in teams}
    pct = {t: (w + .5) / (w + l + 1) for t, (w, l) in rec.items()}
    lg = sorted(teams, key=lambda t: -pct[t]); lrank = {t: r + 1 for r, t in enumerate(lg)}
    gb10 = {}
    for conf in (EAST, set(teams) - EAST):
        ct = sorted([t for t in teams if t in conf], key=lambda t: -pct[t])
        if len(ct) >= 10:
            w10, l10 = rec[ct[9]]
            for t in ct: gb10[t] = ((w10 - rec[t][0]) + (rec[t][1] - l10)) / 2
    for i in day[(s, d)]:
        for t in (G.home.values[i], G.away.values[i]):
            gp = sum(rec[t]); ST[(i, t)] = dict(rank=lrank[t], gb=gb10.get(t, 0), gp=gp, n=len(teams))
    for i in day[(s, d)]:
        h, a = G.home.values[i], G.away.values[i]
        if ACT[i] > 0: W[(s, h)] += 1; L_[(s, a)] += 1
        elif ACT[i] < 0: W[(s, a)] += 1; L_[(s, h)] += 1
def kind(i, t):
    x = ST.get((i, t))
    if not x: return 'μεσαια/δυνατη'
    nb = x['n']
    if x['gp'] >= 40 and x['rank'] >= nb - 2: return 'ΜΑΧΗ ΝΟ1'
    if x['gp'] >= 40 and x['gb'] >= 6: return 'TANKING'
    if x['rank'] >= 23: return 'αδυναμη (οχι tanking)'
    return 'μεσαια/δυνατη'
rows = []
for i, d in MKH.items():
    if SEAS_G[i] not in EV or not np.isfinite(V[i]): continue
    L, mk, o1, o2 = d['o']; cl = d['c'][1]
    pw, pp, pl = cover_(V[i], L, SIG_); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    for t, sg in ((G.home.values[i], 1), (G.away.values[i], -1)):
        r = dict(i=i, sea=SEAS_G[i], per=PER[i], k=kind(i, t), rm=sg * (ACT[i] - V[i]), rc=sg * (ACT[i] - cl), ro=sg * (ACT[i] - mk),
                 pick=(e >= .08 and s_ == sg), against=(e >= .08 and s_ == -sg))
        if e >= .08:
            x = (ACT[i] + L) * s_; r['res'] = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        rows.append(r)
import pandas as pd
X = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def roi(d):
    if not len(d): return '      —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
P('NBA · ΑΔΥΝΑΜΕΣ vs TANKING vs ΜΑΧΗ ΓΙΑ ΝΟ1 · 5 σεζον · live μοντελο · + = η ομαδα επαιξε καλυτερα απο την προβλεψη')
P('TANKING = ≥40 ματς & ≥6 νικες πισω απο τη 10η της περιφερειας · ΜΑΧΗ ΝΟ1 = ≥40 ματς & 3 χειροτερες της λιγκας · αδυναμη = θεση 23-30 (υπολοιπες)')
for per in ('Οκτ-Δεκ', 'Ιαν-Φεβ', 'Μαρ', 'Απρ'):
    P(''); P(f'=== {per} ===')
    D_ = X[X.per == per]
    for k in ('ΜΑΧΗ ΝΟ1', 'TANKING', 'αδυναμη (οχι tanking)', 'μεσαια/δυνατη'):
        d = D_[D_.k == k]
        if not len(d): continue
        P(f'  {k:24s} ματς {len(d):5d} · υπολοιπο μοντελο {d.rm.mean():+5.2f} · αγορα ανοιγ. {d.ro.mean():+5.2f} · κλεισ. {d.rc.mean():+5.2f} · '
          f'picks ΥΠΕΡ τους {roi(d[d.pick])} · picks ΚΟΝΤΡΑ τους {roi(d[d.against])}')
open(os.path.join(SC, 't20a_tanking_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
