# -*- coding: utf-8 -*-
"""el_absence_test.py — EUROLEAGUE: ΑΠΟΥΣΙΕΣ ΠΑΙΚΤΩΝ (8/10/2026, Στελιος «ναι» — πηγη live: RotoWire EuroLeague daily lineups, OUT/GTD μερες πριν).
Ιδιο με nba_absence_cutoffs / bcl_absence_test. Δεδομενα: el_players.json (επισημο API, λεπτα ανα παικτη, Ευρωλιγκα 2017-26).
Προβλεψεις = LIVE μοντελο (el_newmodel_preds h_new: Β1 + ειδικοι + προετοιμασια + εγχωρια 11+) · αγορα Crown (el_line_timing REC), ανοιγμα & κλεισιμο.
Σεζον E2021-E2025, κανονικη περιοδος. ΝΕΑ ΑΠΟΥΣΙΑ: παικτης με μεσο ≥C′ (10 τελευταια που επαιξε), επαιξε σε 1 απο τα 3 τελευταια ματς, ΔΕΝ παιζει.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση): Α αγορα/μοντελο κλιση ανα 10′ (φιλ − γηπ). Β φιλτρο «χωρις pick χαντικαπ (live κανονας ≥8%, σ 11.5, ανοιγμα)
  αν η πλευρα μας λειπει ≥Χ′» Χ {20,30,50} × C {15,20,25,30}: ΠΕΡΝΑ αν τα κομμενα χειροτερα σε ≥4/5 σεζον ΚΑΙ το ROI που μενει ανεβαινει.
Εξοδος: el_absence_out.txt"""
import sys, io, contextlib, json, pickle, collections, math
import numpy as np, pandas as pd
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D, REC = ns['D'], ns['REC']
Phi = NormalDist().cdf
NP = pickle.load(open('el_newmodel_preds.pkl', 'rb'))
PL = json.load(open('el_players.json', encoding='utf-8'))
SE = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']; CS = (15, 20, 25, 30); XS = (20, 30, 50)
# ---- ματς παικτων ανα ομαδα (ολες οι σεζον Ευρωλιγκας) ----
TG = collections.defaultdict(list)
for k, g in PL.items():
    if g.get('comp') != 'E' or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    TG[g['hcode']].append((ts, {p[0]: (p[3] or 0) for p in g['ph']})); TG[g['acode']].append((ts, {p[0]: (p[3] or 0) for p in g['pa']}))
for v in TG.values(): v.sort(key=lambda x: x[0])
def missing(team, ts, C):
    g = [x for x in TG[team] if x[0] < ts - 3600]; today = next((x[1] for x in TG[team] if abs(x[0] - ts) < 3600), None)
    if len(g) < 3 or today is None: return None
    last3 = [x[1] for x in g[-3:]]; hist = collections.defaultdict(list)
    for _, pl in g[-40:]:
        for p, mn in pl.items():
            if mn > 0: hist[p].append(mn)
    tot = 0.0
    for p in set().union(*[{q for q, m in x.items() if m > 0} for x in last3]):
        if today.get(p, 0) > 0: continue
        rec = hist[p][-10:]; avg = sum(rec) / len(rec)
        if avg >= C: tot += avg
    return tot
def cover(m_, L, s=11.5):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
rows = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos])
    key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    m = float(NP[key]['h_new']); act = float(D.hs.values[pos] - D.as_.values[pos]); ts = t.timestamp()
    ut, mu_o, L, o1, o2 = d_['open']; mu_c = d_[0][1]
    pw, pp, pl = cover(m, L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    u = None
    if e >= .08: x = (act + L) * side; u = (od - 1) if x > 0 else (0 if x == 0 else -1)
    r = dict(y=sea, act=act, m=m, mo=mu_o, mc=mu_c, u=u, side=side)
    for C in CS: r[f'h{C}'], r[f'a{C}'] = missing(hc, ts, C), missing(ac, ts, C)
    rows.append(r)
R = pd.DataFrame(rows)
P(f'ματς Ευρωλιγκας E2021-25 με αγορα + live προβλεψη: {len(R)} · picks χαντικαπ ≥8% ανοιγμα: {R.u.notna().sum()} · ROI {R.u.mean()*100:+.1f}%')
for C in CS:
    ok = R[f'h{C}'].notna() & R[f'a{C}'].notna(); S = R[ok]; a_ = np.r_[S[f'h{C}'], S[f'a{C}']]
    P(''); P(f'## C {C}′ · ματς με ιστορικο {ok.sum()} · ομαδα-ματς με απουσια {np.mean(a_ > 0):.0%} · μεσα λεπτα {a_[a_ > 0].mean():.0f}′')
    x = (S[f'a{C}'] - S[f'h{C}']) / 10; cells = []
    for lab, col in (('κλεισ', 'mc'), ('ανοιγ', 'mo'), ('μοντ', 'm')):
        z = S.act - S[col]; b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x)
        se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); ys = sum(np.polyfit(x[S.y == Y], z[S.y == Y], 1)[0] > 0 for Y in SE)
        cells.append(f'{lab} {b:+.2f} (t {b / se:+.1f}, {ys}/5)')
    P('   κλιση ανα 10′ απουσιας: ' + ' · '.join(cells))
    K = S[S.u.notna()].copy(); K['us'] = np.where(K.side == 1, K[f'h{C}'], K[f'a{C}']); K['op'] = np.where(K.side == 1, K[f'a{C}'], K[f'h{C}'])
    def cell(s): return f'{s.u.mean()*100:+.1f}% ({len(s)}, θετ {sum(1 for Y in SE if (s.y == Y).sum() >= 5 and s[s.y == Y].u.mean() > 0)}/5)' if len(s) else '—'
    P(f'   picks: ολα {cell(K)} · η ΔΙΚΗ ΜΑΣ πλευρα λειπει {cell(K[K.us > 0])} · μονο ο ΑΝΤΙΠΑΛΟΣ {cell(K[(K.op > 0) & (K.us == 0)])} · κανεις {cell(K[(K.us == 0) & (K.op == 0)])}')
    for X in XS:
        cut = K[K.us >= X]; keep = K[K.us < X]
        worse = sum(1 for Y in SE if (cut.y == Y).sum() >= 3 and cut[cut.y == Y].u.mean() < keep[keep.y == Y].u.mean()); ny = sum(1 for Y in SE if (cut.y == Y).sum() >= 3)
        okf = ny >= 4 and worse >= 4 and len(keep) and keep.u.mean() > K.u.mean()
        P(f'   φιλτρο Χ {X}′: κοβει {cell(cut)} · μενουν {cell(keep)} · χειροτερα σε {worse}/{ny}' + ('  <- ΠΕΡΝΑ' if okf else '  ✗'))
open('el_absence_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
