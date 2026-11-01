# -*- coding: utf-8 -*-
"""ucl_after_entry_drift.py — CHAMPIONS LEAGUE ΣΥΝΟΛΑ: ΑΦΟΥ ΒΓΕΙ ΤΟ PICK, ΣΥΝΕΧΙΖΕΙ Η ΑΓΟΡΑ ΚΟΝΤΡΑ; ΚΑΛΥΤΕΡΑ ΣΤΟ 4ω/2ω/ΚΛΕΙΣΙΜΟ; (13/10/2026,
Στελιος: Arsenal–Lille under 3 (βγηκε 9.4ω πριν) & Atletico–United over 3 (12.6ω) «εχουν φαει ακομα περισσοτερη κοντρα απο οταν τα παιξα …
ιστορικα αν αυτα τα picks μεχρι το κλεισιμο ή 4, 2 ωρες πριν συνεχιζουν να τρωνε κοντρα? ισως στο κλεισιμο ειναι καλυτερα?»).
Πηγη: ucl_bb_timing_alerts.pkl (σημερινοι κανονες, πρωτη εμφανιση ≤72ω, Crown & SBOBET) + τροχιες OU Nowgoal.
Για καθε pick συνολων: «δικαιο συνολο» αγορας (γκολ) στην εισοδο, +3ω μετα, 6ω/4ω/2ω πριν, κλεισιμο → κινηση (+ = προς το pick, − = κοντρα)
ΚΑΙ ROI αν το ΙΔΙΟ pick (ιδια πλευρα) παιζοταν σε καθε στιγμη (γραμμη/αποδοση εκεινης της στιγμης).
Ομαδες: (α) ολα · (β) ιδια μερα 8-16ω πριν (σαν τα σημερινα) · (γ) ΟΣΑ ΕΙΧΑΝ ΗΔΗ ΦΑΕΙ ΚΟΝΤΡΑ ≥0.10 στις πρωτες 3ω μετα την εισοδο
(σαν τα σημερινα) → τι εγινε μετα. Νεα μορφη 2024-26 (βαση live)· ολες οι σεζον = πλαισιο. ΠΕΡΙΓΡΑΦΙΚΟ. Εξοδος: ucl_after_entry_drift_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('ucl_bb_timing.py', encoding='utf-8').read()
src = src[:src.index('rows = []\n# 13/10')]
g = {'__name__': 'drift'}
class _B(io.StringIO):
    def reconfigure(self, **k): pass
with contextlib.redirect_stdout(_B()): exec(src, g)
TOU, KO, mtot, settle_ou, GH, GA = (g[k] for k in ('TOU', 'KO', 'mtot', 'settle_ou', 'GH', 'GA'))
X = pd.read_pickle('ucl_bb_timing_alerts.pkl')
X = X[X.mk.isin(['over', 'under'])].copy()
def state(seq, ts):
    prev = [x for x in seq if x[0] <= ts]
    return prev[-1] if prev else None
PTS = [('+3ω μετα', None), ('6ω πριν', 6), ('4ω πριν', 4), ('2ω πριν', 2), ('κλεισιμο', 0)]
rows = []
for r in X.itertuples():
    seq = TOU.get((r.mid, r.bk)); ko = KO[r.mid]
    if not seq: continue
    te = ko - r.hrs * 3600; sg = 1 if r.mk == 'over' else -1; tot = GH[r.i] + GA[r.i]
    e0 = state(seq, te + 1)
    if e0 is None: continue
    f0 = mtot(e0[1], e0[2], e0[3]) * sg
    d = dict(sea=r.sea, bk=r.bk, mk=r.mk, cat=r.cat, hrs=r.hrs, pa=r.pa)
    for lab, h in PTS:
        ts = te + 3 * 3600 if h is None else (ko - h * 3600 if h else ko + 900)
        if ts < te: ts = te                                  # pick βγηκε μετα απο αυτη τη στιγμη → ιδια με την εισοδο
        s = state(seq, ts)
        d['mv_' + lab] = mtot(s[1], s[2], s[3]) * sg - f0
        od = s[2] if r.mk == 'over' else s[3]
        d['p_' + lab] = settle_ou(tot, s[1], od, r.mk == 'over')
    rows.append(d)
D = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def roi(d, col):
    g_ = d.groupby('bk')[col]; return f'{100*g_.mean().mean():+6.1f}%'
def block(d, title):
    if not len(d):
        P(f'  {title}: —'); return
    n = d.groupby('bk').size().mean()
    P(f'  {title} · {n:.0f} picks')
    P('     ' + ' · '.join(f'{lab}: κιν {d["mv_" + lab].mean():+.2f} ({100*(d["mv_" + lab] <= -0.05).mean():.0f}% κοντρα / {100*(d["mv_" + lab] >= 0.05).mean():.0f}% προς)' for lab, _ in PTS))
    P('     ROI αν το επαιζα: στην εισοδο ' + roi(d, 'pa') + ' · ' + ' · '.join(f'{lab} {roi(d, "p_" + lab)}' for lab, _ in PTS))
    P('     ανα σεζον (εισοδος → κλεισιμο): ' + ' '.join(f'{s}:{100*x.pa.mean():+.0f}→{100*x["p_κλεισιμο"].mean():+.0f}' for s, x in d.groupby('sea')))
P('CHAMPIONS LEAGUE ΣΥΝΟΛΑ · ΤΙ ΚΑΝΕΙ Η ΑΓΟΡΑ ΑΦΟΥ ΒΓΕΙ ΤΟ PICK · μεσος Crown/SBOBET')
P('κινηση = «δικαιο συνολο» αγορας απο την εισοδο ως τη στιγμη, σε γκολ (+ = προς το pick, − = κοντρα)· ROI = το ΙΔΙΟ pick στη γραμμη/αποδοση εκεινης της στιγμης')
early3 = lambda d: d['mv_+3ω μετα'] <= -0.10
for sl, ss in (('ΝΕΑ ΜΟΡΦΗ 2024-26', ['2425', '2526']), ('ΟΛΕΣ ΟΙ ΣΕΖΟΝ (πλαισιο)', None)):
    P(''); P('#' * 90); P(f'### {sl}'); P('#' * 90)
    for m in ('over', 'under'):
        d0 = D[(D.mk == m) & (D.sea.isin(ss) if ss else True)]
        P(''); P(f'=== {m.upper()} ===')
        block(d0, 'ΟΛΑ')
        sd = d0[(d0.hrs >= 8) & (d0.hrs < 16)]
        block(sd, 'βγηκαν 8-16ω πριν (σαν τα σημερινα)')
        block(d0[early3(d0)], 'ΕΦΑΓΑΝ ΚΟΝΤΡΑ ≥0.10 στις 3ω μετα την εισοδο')
        block(sd[early3(sd)], 'βγηκαν 8-16ω ΚΑΙ εφαγαν κοντρα ≥0.10 στις 3ω')
        if m == 'over':
            block(d0[(d0.cat == 'FF') & early3(d0)], 'FotMob+FotMob & κοντρα ≥0.10 στις 3ω')
P(''); P('(σημ.) ροη μετα τις 3ω για οσα ηδη εφαγαν κοντρα: συγκρινε «+3ω μετα» με «4ω/2ω/κλεισιμο» — αν η κινηση μεγαλωνει, η κοντρα συνεχιζει.')
open('ucl_after_entry_drift_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
