# -*- coding: utf-8 -*-
"""t81_style_matchups.py — ΣΥΝΟΛΑ NBA: MATCHUPS ΣΤΥΛ (24/10/2026, Στελιος «ναι» στον ορισμο· πηγη pbpstats.com ανα ματς, nba_pbpstats_fetch.py).
Ερωτημα: η αγορα χανει το «ταιριασμα» στυλ; (επιθεση που ζει απο Χ × αμυνα που αφηνει Χ)
Δεδομενα: 5 σεζον 2021-26 · ανοιγμα Crown (_t35_totals.csv) · φετινα στοιχεια καθε ομαδας ΜΟΝΟ απο ματς ΠΡΙΝ (≥10 ματς καθε ομαδα).
4 στυλ (ποσοστα ως το ματς, αποκλιση απο τον μεσο ορο λιγκας ως την ιδια μερα):
  1 ΤΡΙΠΟΝΤΑ  = FG3A/FGA   (επιθεση) · ιδιο που αφηνει (αμυνα)
  2 ΡΑΚΕΤΑ    = AtRimFGA/FGA (σουτ στο καλαθι, pbpstats ζωνες)
  3 ΒΟΛΕΣ     = FTA/FGA
  4 ΕΠ. ΡΙΜΠ. = OREB/(OREB + αμυντικα ριμπ. αντιπαλου)
Χαρακτηριστικο ματς για καθε στυλ: (επιθ.Γ − Λ)·(αμυν.Φ − Λ) + (επιθ.Φ − Λ)·(αμυν.Γ − Λ)   [Γ γηπεδουχος, Φ φιλοξενουμενος, Λ λιγκα]
Στοχος: πραγματικο − δικαιη γραμμη ανοιγματος (fair). Γραμμικη (ridge) στα 4, μαθαινει στις 4 σεζον, ελεγχος στην 5η (LOSO).
Κανονας: over αν προβλεψη ≥ θ, under αν ≤ −θ, θ ∈ {2, 3} π. (LOSO με μοναδες). Αποτελεσμα στην τιμη ανοιγματος, CLV = κινηση δικαιης γραμμης.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: n ≥150 ΚΑΙ ROI >0 ΚΑΙ CLV >0 ΚΑΙ θετικο ≥4/5 σεζον ΚΑΙ καθε συντελεστης που «μετραει» ιδιο προσημο ≥4/5 σεζον (fit ανα σεζον).
Πληροφορια: Οκτ-Δεκ / Ιαν-Φεβ / Μαρ-Απρ · παραλλαγη με «επιπεδα» (αθροισμα στυλ, χωρις γινομενο) · ισχυς καθε στυλ μονο του.
Εξοδος: nba_tests/t81_style_matchups_out.txt"""
import os, sys, json, glob, bisect
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
SMAP = {'2021-22': 2022, '2022-23': 2023, '2023-24': 2024, '2024-25': 2025, '2025-26': 2026}
# ---- pbpstats: ανα ομαδα-σεζον, σειρα ματς με τα αθροισματα που χρειαζομαστε ----
F = ['FG2A', 'FG3A', 'AtRimFGA', 'FTA', 'OffRebounds', 'DefRebounds', 'Points']
LOG = {}   # (sea, team) -> DataFrame [Date, T_*, O_*]
for fn in glob.glob(os.path.join(ROOT, 'nba_pbpstats', '*_Team_*.json')):
    b = os.path.basename(fn)[:-5]; s, _, ab = b.split('_')
    if s not in SMAP: continue
    T = json.load(open(fn, encoding='utf-8')); Op = json.load(open(fn.replace('_Team_', '_Opponent_'), encoding='utf-8'))
    ot = {x['GameId']: x for x in Op}
    R = []
    for x in T:
        y = ot.get(x['GameId'])
        if y is None: continue
        R.append([x['Date']] + [float(x.get(k, 0) or 0) for k in F] + [float(y.get(k, 0) or 0) for k in F])
    LOG[(SMAP[s], ab)] = pd.DataFrame(R, columns=['Date'] + ['T_' + k for k in F] + ['O_' + k for k in F]).sort_values('Date').reset_index(drop=True)
P(f'pbpstats: {len(LOG)} ομαδες-σεζον · {sum(len(v) for v in LOG.values())} γραμμες')
CUM = {}
for k, d in LOG.items():
    c = d[[c for c in d.columns if c != 'Date']].cumsum(); c.insert(0, 'Date', d.Date.values); CUM[k] = c
def upto(sea, team, date):
    """αθροισματα απο ματς ΠΡΙΝ την ημερα · (n, Series)"""
    c = CUM.get((sea, team))
    if c is None: return 0, None
    j = bisect.bisect_left(list(c.Date.values), date)
    return (j, c.iloc[j - 1]) if j > 0 else (0, None)
def rates(s):
    fa = s.T_FG2A + s.T_FG3A; fo = s.O_FG2A + s.O_FG3A
    off = np.array([s.T_FG3A / fa, s.T_AtRimFGA / fa, s.T_FTA / fa, s.T_OffRebounds / (s.T_OffRebounds + s.O_DefRebounds)])
    dfn = np.array([s.O_FG3A / fo, s.O_AtRimFGA / fo, s.O_FTA / fo, s.O_OffRebounds / (s.O_OffRebounds + s.T_DefRebounds)])
    return off, dfn
# μεσος λιγκας ως την ημερα: αθροισμα ολων των ομαδων (ιδιοι τυποι)
LG = {}
def league(sea, date):
    k = (sea, date)
    if k not in LG:
        tot = None
        for (s2, t2) in CUM:
            if s2 != sea: continue
            n, s = upto(sea, t2, date)
            if n: tot = s.drop('Date') if tot is None else tot + s.drop('Date')
        LG[k] = rates(tot)[0] if tot is not None else None
    return LG[k]
# ---- αγορα ----
D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
NAMES = ['ΤΡΙΠΟΝΤΑ', 'ΡΑΚΕΤΑ', 'ΒΟΛΕΣ', 'ΕΠ.ΡΙΜΠ']
X, LV, keep = [], [], []
for idx, r in O.iterrows():
    d = str(r['date'])[:10]
    nh, sh = upto(r['sea'], r['home'], d); na, sa = upto(r['sea'], r['away'], d)
    if nh < 10 or na < 10: continue
    L = league(r['sea'], d)
    oh, dh = rates(sh); oa, da = rates(sa)
    X.append((oh - L) * (da - L) + (oa - L) * (dh - L)); LV.append((oh - L) + (da - L) + (oa - L) + (dh - L)); keep.append(idx)
O = O.loc[keep].reset_index(drop=True)
X = np.array(X); LV = np.array(LV)
O['y'] = O.tot - O.fair
SEAS = sorted(O.sea.unique()); SIG = 18.0; ND = NormalDist()
P(f'ματς με ≥10 προηγουμενα καθε ομαδα: {len(O)} · ανα σεζον ' + ' '.join(f'{s % 100}:{int((O.sea == s).sum())}' for s in SEAS))
def fit(Xm, y, lam=1.0):
    mu, sd = Xm.mean(0), Xm.std(0); Z = (Xm - mu) / sd
    A = Z.T @ Z + lam * np.eye(Z.shape[1]); b = np.linalg.solve(A, Z.T @ (y - y.mean()))
    return lambda Xn: y.mean() * 0 + ((Xn - mu) / sd) @ b, b   # σταθερα 0: δεν παιρνουμε θεση στη γενικη μεροληψια της σεζον
def settle(r, sd):
    x = (r['tot'] - r['T']) * sd; od = r['oo'] if sd > 0 else r['ou']
    return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
def picks(sub, g, th):
    R = []
    for (_, r), gg in zip(sub.iterrows(), g):
        if abs(gg) < th: continue
        sd = 1 if gg > 0 else -1
        R.append((r['sea'], sd, settle(r, sd), sd * (r['cfair'] - r['fair']), int(r['mon'])))
    return pd.DataFrame(R, columns=['sea', 'sd', 'u', 'clv', 'mon'])
def show(lab, d):
    if not len(d): P(f'  {lab:30s} —'); return 0, 0, 0, 0
    ps = d.groupby('sea').u.sum()
    P(f"  {lab:30s} {100 * d.u.mean():+6.1f}% ({len(d):4d}, {d.u.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π · over {int((d.sd > 0).sum())} / under {int((d.sd < 0).sum())} · "
      + ' '.join(f'{s % 100}:{ps[s]:+.1f}μ' for s in ps.index))
    return len(d), 100 * d.u.mean(), int((ps > 0).sum()), d.clv.mean()
def loso(Xm):
    G = np.zeros(len(O))
    for s in SEAS:
        tr = (O.sea != s).values; f, _ = fit(Xm[tr], O.y.values[tr]); G[~tr] = f(Xm[~tr])
    return G
# ---- Α. συντελεστες ανα σεζον (μονη της) + σφαλμα ----
P('\n=== Α. ΤΙ ΜΕΤΡΑΕΙ: συντελεστης ανα σεζον (π. ανα 1 τυπικη αποκλιση του «ταιριασματος»), fit σε καθε σεζον ΜΟΝΗ της ===')
SG = {}
for s in SEAS:
    m = (O.sea == s).values; _, b = fit(X[m], O.y.values[m]); SG[s] = b
for k, nm in enumerate(NAMES):
    v = [SG[s][k] for s in SEAS]; same = max(sum(x > 0 for x in v), sum(x < 0 for x in v))
    P(f'  {nm:9s} ' + ' '.join(f'{s % 100}:{SG[s][k]:+.2f}' for s in SEAS) + f' · ιδιο προσημο {same}/5')
P('  (για μεγεθος: 1 τυπικη αποκλιση = ενα «συνηθισμενο» ταιριασμα· +0.50 σημαινει μισο ποντο πανω στο συνολο)')
G = loso(X)
r0 = np.sqrt((O.y ** 2).mean()); r1 = np.sqrt(((O.y - G) ** 2).mean())
P(f'\n  σφαλμα γραμμης ανοιγματος (RMSE) {r0:.3f} π. → με διορθωση στυλ (LOSO) {r1:.3f} π. · συσχετιση προβλεψης-«κενου» {np.corrcoef(G, O.y)[0, 1]:+.3f}')
P(f'  εύρος προβλεψης: 90% των ματς μεταξυ {np.percentile(G, 5):+.2f} και {np.percentile(G, 95):+.2f} π.')
# ---- Β. picks ----
P('\n=== Β. PICKS (ανοιγμα Crown) ===')
cache = {th: pd.concat([picks(O[O.sea == s], G[(O.sea == s).values], th) for s in SEAS]) for th in (1, 2, 3)}
for th in (1, 2, 3): show(f'θ={th} π. (ολες οι σεζον)', cache[th])
sel = {s: max((2, 3), key=lambda th: cache[th][cache[th].sea != s].u.sum()) for s in SEAS}
P('  LOSO επιλογη θ: ' + ' · '.join(f'{s % 100}:{sel[s]}' for s in SEAS))
Lp = pd.concat([cache[sel[s]][cache[sel[s]].sea == s] for s in SEAS])
n, roi, pos, clv = show('LOSO κανονας', Lp)
if len(Lp):
    P('  ανα περιοδο: ' + ' · '.join(f'{lab} {100 * Lp[Lp.mon.isin(ms)].u.mean():+.1f}% ({int(Lp.mon.isin(ms).sum())})'
                                 for lab, ms in (('Οκτ-Δεκ', (10, 11, 12)), ('Ιαν-Φεβ', (1, 2)), ('Μαρ-Απρ', (3, 4)))))
# ---- Γ. πληροφορια ----
P('\n=== Γ. ΠΛΗΡΟΦΟΡΙΑ ===')
for k, nm in enumerate(NAMES):
    g1 = loso(X[:, [k]]); P(f'  μονο {nm:9s}: RMSE {np.sqrt(((O.y - g1) ** 2).mean()):.3f} (βαση {r0:.3f}) · συσχετιση {np.corrcoef(g1, O.y)[0, 1]:+.3f}')
g2 = loso(LV); P(f'  «ΕΠΙΠΕΔΑ» (αθροισμα στυλ, χωρις ταιριασμα): RMSE {np.sqrt(((O.y - g2) ** 2).mean()):.3f} · συσχετιση {np.corrcoef(g2, O.y)[0, 1]:+.3f}')
show('picks «επιπεδα» θ=2', pd.concat([picks(O[O.sea == s], g2[(O.sea == s).values], 2) for s in SEAS]))
sgn_ok = all(max(sum(SG[s][k] > 0 for s in SEAS), sum(SG[s][k] < 0 for s in SEAS)) >= 4 for k in range(4) if abs(np.mean([SG[s][k] for s in SEAS])) >= 0.2)
ok = n >= 150 and roi > 0 and clv > 0 and pos >= 4 and sgn_ok
P(f'\nΚΡΙΤΗΡΙΟ: n {n} (≥150) · ROI {roi:+.1f}% (>0) · CLV {clv:+.2f} (>0) · θετικες {pos}/5 (≥4) · προσημα σταθερα (στυλ με |μεσο| ≥0.2) {"ναι" if sgn_ok else "οχι"} → '
  f'{"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't81_style_matchups_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
