# -*- coding: utf-8 -*-
"""t14_open_picks_news.py — PICKS ΑΝΟΙΓΜΑΤΟΣ & ΑΠΟΥΣΙΕΣ ΠΟΥ ΒΓΑΙΝΟΥΝ ΜΕΤΑ (20/10/2026, Στελιος: «ποσα απο τα μπετς στο ανοιγμα
επηρεαζονται απο απουσιες στη συνεχεια, μεσα στη μερα;»). ΠΕΡΙΓΡΑΦΙΚΟ, οχι κανονας.
PICK = οπως το live: βαση (production + B2B 3 + γνωστες απουσιες K=2 με αντικαταστατη −2) · edge ≥8% στη γραμμη ΑΝΟΙΓΜΑΤΟΣ (Crown).
«ΝΕΑ» απουσια = παικτης ρολου (≥20′) που επαιξε στο προηγουμενο ματς και ΔΕΝ παιζει σημερα (box score· η ειδηση βγαινει συνηθως
μετα το ανοιγμα — βλ. t9: το ανοιγμα εχει μονο το 1/3 του κοστους). Κοστος = 0.75·(αξια+2)·λεπτα/48 (live φορμουλα).
Για καθε pick: νεα απουσια στη ΔΙΚΗ ΜΑΣ πλευρα / στον ΑΝΤΙΠΑΛΟ / καμια · ισχυει ακομα αν το μοντελο μαθει την απουσια (edge ≥8%
στη γραμμη ανοιγματος και στη γραμμη κλεισιματος) · ROI στο ανοιγμα. Εξοδος: t14_open_picks_news_out.txt"""
import os, io, sys, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'news_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'news_test.py'), encoding='utf-8').read().split("def reg(y, X, m):")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; MG = np.asarray(ns['MG'], float)
FRESH, value, MKH, SIG, OD = ns['FRESH'], ns['value'], ns['MKH'], ns['SIG'], ns['OD']
ACT = (G.hs - G.as_).values.astype(float)
from statistics import NormalDist
Phi = NormalDist().cdf
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
# βαση live (αντικαταστατης −2)
ns['REP'] = -2.0
LH = np.zeros(len(G)); LA = np.zeros(len(G))
for i in range(len(G)):
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    LH[i], _ = ns['team_loss'](h, d, 2); LA[i], _ = ns['team_loss'](a, d, 2)
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
BASE = MG + 3.0 * (B2A - B2H) + 0.75 * (LH - LA)
# νεες απουσιες ανα πλευρα (δικοι μας ποντοι)
NH = np.zeros(len(G)); NA = np.zeros(len(G)); TOPH = np.zeros(len(G)); TOPA = np.zeros(len(G))
for i in range(len(G)):
    for side, t in ((1, G.home.values[i]), (-1, G.away.values[i])):
        for p, avg in FRESH.get((t, dD[i]), []):
            c = 0.75 * (value(p, SEAS_G[i] - 1) + 2.0) * avg / 48
            if side == 1: NH[i] += c; TOPH[i] = max(TOPH[i], c)
            else: NA[i] += c; TOPA[i] = max(TOPA[i], c)
KNEW = BASE - NH + NA                                     # αν το μοντελο ηξερε τις νεες απουσιες
rows = []
for i, d in MKH.items():
    if SEAS_G[i] not in EV or not np.isfinite(BASE[i]): continue
    L, mk, o1, o2 = d['o']; Lc, mkc, c1, c2 = d['c']
    pw, pp, pl = cover(BASE[i], L, SIG); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: continue
    x = (ACT[i] + L) * s_; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    ours = NH[i] if s_ == 1 else NA[i]; opp = NA[i] if s_ == 1 else NH[i]
    pw2, pp2, pl2 = cover(KNEW[i], L, SIG); ek_o = (pw2 * o1 + pp2 - 1) if s_ == 1 else (pl2 * o2 + pp2 - 1)
    pw3, pp3, pl3 = cover(KNEW[i], Lc, SIG); ek_c = (pw3 * c1 + pp3 - 1) if s_ == 1 else (pl3 * c2 + pp3 - 1)
    xc = (ACT[i] + Lc) * s_; odc = c1 if s_ == 1 else c2; resc = (odc - 1) if xc > 0 else (0.0 if xc == 0 else -1.0)
    rows.append(dict(i=i, sea=SEAS_G[i], od=bool(OD[i]), res=res, resc=resc, ours=ours, opp=opp, top_ours=TOPH[i] if s_ == 1 else TOPA[i],
                     still_o=ek_o >= .08, still_c=ek_c >= .08, move=s_ * (mkc - mk)))
import pandas as pd
X = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d, col='res'):
    if not len(d): return '      —'
    ps = d.groupby('sea')[col].sum()
    return f'{100 * d[col].mean():+6.1f}% ({len(d):4d}, {d[col].sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
P('NBA · PICKS ΑΝΟΙΓΜΑΤΟΣ (edge ≥8%, live βαση) & ΝΕΕΣ ΑΠΟΥΣΙΕΣ ΠΟΥ ΒΓΗΚΑΝ ΜΕΤΑ · 5 σεζον, Crown')
P('κελι = ROI στην τιμη ανοιγματος (picks, μοναδες, θετικες σεζον) · «κινηση» = αγορα ανοιγμα→κλεισιμο, + = προς εμας')
for lab, D_ in (('ΟΚΤ-ΔΕΚ', X[X.od]), ('ΟΛΗ Η ΣΕΖΟΝ', X)):
    P(''); P(f'=== {lab}: {len(D_)} picks ===')
    groups = (('καμια νεα απουσια (<0.5 π.)', (D_.ours < .5) & (D_.opp < .5)),
              ('νεα απουσια στον ΑΝΤΙΠΑΛΟ (≥0.5)', (D_.ours < .5) & (D_.opp >= .5)),
              ('νεα απουσια στη ΔΙΚΗ ΜΑΣ πλευρα (≥0.5)', (D_.ours >= .5) & (D_.opp < .5)),
              ('    ↳ μικρη 0.5-1.5', (D_.ours >= .5) & (D_.ours < 1.5) & (D_.opp < .5)),
              ('    ↳ μεγαλη ≥1.5', (D_.ours >= 1.5) & (D_.opp < .5)),
              ('και στις 2 πλευρες', (D_.ours >= .5) & (D_.opp >= .5)))
    for g, m in groups:
        d = D_[m]
        P(f'  {g:42s} {100 * len(d) / len(D_):4.0f}% · {cell(d)} · κινηση {d.move.mean() if len(d) else 0:+5.2f}')
    P('  -- αν το μοντελο ΗΞΕΡΕ την απουσια (επαναυπολογισμος στη γραμμη ανοιγματος / κλεισιματος) --')
    af = D_[(D_.ours >= .5) | (D_.opp >= .5)]
    for g, m in (('ισχυει ακομα στο ανοιγμα', af.still_o), ('ΔΕΝ ισχυει πια (στο ανοιγμα)', ~af.still_o),
                 ('ισχυει ακομα και στη γραμμη κλεισιματος', af.still_c), ('δεν ισχυει στη γραμμη κλεισιματος', ~af.still_c)):
        d = af[m]; P(f'  {g:42s} {100 * len(d) / max(len(af), 1):4.0f}% των επηρεασμενων · ανοιγμα {cell(d)} · κλεισιμο {cell(d, "resc")}')
    ours = D_[D_.ours >= .5]
    P(f'  δικη μας απουσια: πεθαινει το pick {100 * (~ours.still_o).mean() if len(ours) else 0:.0f}% · ROI οσων πεθαινουν {cell(ours[~ours.still_o])} · οσων μενουν {cell(ours[ours.still_o])}')
open(os.path.join(SC, 't14_open_picks_news_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
