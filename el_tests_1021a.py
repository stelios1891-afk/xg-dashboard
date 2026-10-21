# -*- coding: utf-8 -*-
"""el_tests_1021a.py — EUROLEAGUE: 3 ΤΕΣΤ με τη γνωση του NBA (21/10/2026, Στελιος «ολα τρεξτα»).
Βαση: el_line_timing.py (Crown χαντικαπ/συνολο με ωρα, E2021-25 κανονικη περιοδος, live μοντελα HPRED/TPRED, σ 11.5/16.7).
Τ4 ΠΛΗΡΟΦΟΡΙΑ ΜΟΝΤΕΛΟΥ ΑΝΑ ΩΡΑ (περιγραφικο): κλιση (πραγμ − κλεισιμο) πανω στο (μοντελο − αγορα στο τ), τ = ανοιγμα / 8ω / 2ω / 30′,
   + κλιση (κλεισιμο − αγορα τ) = ποσο παει η αγορα προς το μοντελο. NBA: +0.26-0.30 5/5 σε ολες τις στιγμες.
Τ3α ΣΥΝΟΛΑ — ΛΑΘΟΣ ΤΗΣ ΑΓΟΡΑΣ ΑΝΑ ΠΕΡΙΟΔΟ: πραγμ − κλεισιμο (και − ανοιγμα) ανα μηνα, ανα σεζον· + picks live συνολων ≥8% ανα μηνα.
   ΠΡΟ-ΔΗΛΩΜΕΝΟ: «σταθερο λαθος» = μηνας με ιδιο προσημο σε ≥4/5 σεζον ΚΑΙ |μεσο| ≥1.5 π. (→ υποψηφιο για διορθωση, οχι live).
Τ2 ΚΙΝΗΤΡΟ ΤΕΛΕΥΤΑΙΩΝ ΑΓΩΝΙΣΤΙΚΩΝ (τελευταιοι 9 αγωνες καθε ομαδας): βαθμολογια με νικες πριν απο καθε ματς.
   Ζωνες: E2022+ 1-4 εδρα · 5-6 πλει-οφ · 7-10 πλει-ιν · 11+ εκτος (E2021: 1-4 · 5-8 · 9+ εκτος).
   ΧΩΡΙΣ ΚΙΝΗΤΡΟ (ΧΚ) = μαθηματικα εκτος · ή πρακτικα εκτος (≥3 νικες πισω απο την τελευταια θεση προκρισης με ≤6 ματς) ·
   ή ΚΛΕΙΔΩΜΕΝΗ (δεν μπορει να πεσει ουτε να ανεβει ζωνη, με τις νικες). Αλλες = ΜΕ ΚΙΝΗΤΡΟ (ΜΚ).
   ΠΡΟ-ΔΗΛΩΜΕΝΟ (οπως NBA): κοβουμε picks χαντικαπ (live, ≥8% ανοιγμα) ΥΠΕΡ ΧΚ ΚΟΝΤΡΑ σε ΜΚ αν: ROI τους < 0 με n ≥ 15 ΚΑΙ
   οι μοναδες ολων των picks των τελευταιων 9 αγωνων ΧΩΡΙΣ αυτα ≥ με αυτα ΚΑΙ αρνητικα σε ≥ (σεζον με ≥3 τετοια picks) − 1.
   Περιγραφικα: συνολα (πραγμ − κλεισιμο) με 0/1/2 ομαδες ΧΚ, picks συνολων.
Εξοδος: el_tests_1021a_out.txt"""
import sys, io, contextlib, collections
import numpy as np, pandas as pd
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
D, REC, HP, TP, SE5 = ns['D'], ns['REC'], ns['HPRED'], ns['TPRED'], ns['SE5']
ACT = (D.hs - D.as_).values.astype(float); TOT = (D.hs + D.as_).values.astype(float)
SEAS = sorted(SE5); Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float); b = np.polyfit(x, y, 1); r = y - np.polyval(b, x)
    return b[0], np.sqrt(np.sum(r ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
# ================= Τ4 =================
P('=== Τ4 · ΠΛΗΡΟΦΟΡΙΑ ΤΟΥ ΜΟΝΤΕΛΟΥ ΑΝΑ ΩΡΑ (κλιση πραγμ − κλεισιμο πανω στο μοντελο − αγορα) ===')
for t, nm, Y, PR in ((21, 'ΧΑΝΤΙΚΑΠ', ACT, HP), (23, 'ΣΥΝΟΛΟ', TOT, TP)):
    for lab, h in (('ανοιγμα', 'open'), ('8ω πριν', 8), ('2ω πριν', 2), ('30′ πριν', 0.5)):
        x, y, mv, ss = [], [], [], []
        for p, r in REC[t].items():
            m = r.get(h) if h != 'open' else r['open']
            if m is None or not np.isfinite(PR[p]): continue
            x.append(PR[p] - m[1]); y.append(Y[p] - r[0][1]); mv.append(r[0][1] - m[1]); ss.append(D.season.values[p])
        x, y, mv, ss = map(np.array, (x, y, mv, ss)); b, se = slope(x, y)
        per = ' '.join(f'{s[-2:]}:{slope(x[ss == s], y[ss == s])[0]:+.2f}' for s in SEAS)
        P(f'  {nm:8s} {lab:9s} n {len(x)} · μετα το κλεισιμο {b:+.3f} ± {se:.3f} · ανα σεζον {per} · η αγορα παει προς το μοντελο {slope(x, mv)[0]:+.3f}')
# ================= Τ3α =================
P(''); P('=== Τ3α · ΣΥΝΟΛΑ: πραγματικο − αγορα ανα μηνα (κλεισιμο / ανοιγμα) ===')
R23 = REC[23]; rows = []
for p, r in R23.items():
    rows.append(dict(p=p, s=D.season.values[p], mon=pd.Timestamp(D.t.values[p]).month, cl=TOT[p] - r[0][1], op=TOT[p] - r['open'][1], tp=TP[p], o=r['open']))
T3 = pd.DataFrame(rows)
for m in (10, 11, 12, 1, 2, 3, 4, 5):
    x = T3[T3.mon == m]
    if len(x) < 30: continue
    per = {s: x[x.s == s].cl.mean() for s in SEAS if (x.s == s).sum() >= 8}
    same = max(sum(v > 0 for v in per.values()), sum(v < 0 for v in per.values()))
    flag = ' ← ΣΤΑΘΕΡΟ' if same >= 4 and abs(x.cl.mean()) >= 1.5 else ''
    P(f'  μηνας {m:2d}: n {len(x):4d} · − κλεισιμο {x.cl.mean():+5.2f} ± {x.cl.std() / np.sqrt(len(x)):.2f} · − ανοιγμα {x.op.mean():+5.2f} · ανα σεζον ' +
      ' '.join(f'{s[-2:]}:{v:+.1f}' for s, v in per.items()) + f' (ιδιο προσημο {same}/{len(per)}){flag}')
def tpick(r, mu, thr=.08):
    _, _, T_, oo, ou = r
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - mu) / 16.7); pu = Phi((T_ - .5 - mu) / 16.7)
    else: po = 1 - Phi((T_ - mu) / 16.7); pu = 1 - po
    pq = 1 - po - pu; eo, eu = po * oo + pq - 1, pu * ou + pq - 1
    if max(eo, eu) < thr: return None
    return (1, oo) if eo >= eu else (-1, ou)
P('  picks live συνολων ≥8% (ανοιγμα) ανα μηνα:')
for m in (10, 11, 12, 1, 2, 3, 4, 5):
    res = []
    for r in T3[T3.mon == m].itertuples():
        if not np.isfinite(r.tp): continue
        k = tpick(r.o, r.tp)
        if not k: continue
        x = (TOT[r.p] - r.o[2]) * k[0]; res.append(((k[1] - 1) if x > 0 else (0 if x == 0 else -1), k[0]))
    if res:
        a = np.array([u for u, _ in res]); sd = np.array([s for _, s in res])
        P(f'    {m:2d}: {100 * a.mean():+6.1f}% ({len(a)}) · over {100 * a[sd == 1].mean() if (sd == 1).any() else float("nan"):+.1f}% ({(sd == 1).sum()}) · under {100 * a[sd == -1].mean() if (sd == -1).any() else float("nan"):+.1f}% ({(sd == -1).sum()})')
# ================= Τ2 =================
P(''); P('=== Τ2 · ΚΙΝΗΤΡΟ ΤΕΛΕΥΤΑΙΩΝ 9 ΑΓΩΝΩΝ ===')
RS = D[(D.phase == 'RS') & D.season.isin(SEAS)].copy(); RS['ts'] = [pd.Timestamp(x).timestamp() for x in RS.t.values]
STATUS = {}                                   # pos → (status_h, status_a, gn_left_h, gn_left_a)
for s in SEAS:
    G = RS[RS.season == s].sort_values('ts'); teams = sorted(set(G.home) | set(G.away))
    total = collections.Counter(list(G.home) + list(G.away)); W = collections.Counter(); PL = collections.Counter()
    zones = [(1, 4), (5, 6), (7, 10), (11, 99)] if s != 'E2021' else [(1, 4), (5, 8), (9, 99)]
    cut = 10 if s != 'E2021' else 8
    for pos, r in zip(G.index, G.itertuples()):
        if PL[r.home] > 0 and PL[r.away] > 0:
            rank = sorted(teams, key=lambda t: -W[t]); wins = [W[t] for t in rank]; maxw = {t: W[t] + total[t] - PL[t] for t in teams}
            def zone_of(i): return next(j for j, (a, b) in enumerate(zones) if a <= i + 1 <= b)
            def status(t):
                i = rank.index(t); left = total[t] - PL[t]; z = zone_of(i)
                if left > 9: return 'νωρις'
                last_q = wins[cut - 1] if len(wins) >= cut else 0
                if maxw[t] < last_q: return 'ΧΚ'                                    # μαθηματικα εκτος
                if i + 1 > cut and last_q - W[t] >= 3 and left <= 6: return 'ΧΚ'      # πρακτικα εκτος
                a, b = zones[z]
                below = rank[b:] if b < len(rank) else []
                above_last = rank[a - 2] if a >= 2 else None
                cant_drop = all(maxw[u] < W[t] for u in below[:1]) if below else True
                cant_rise = (maxw[t] < W[above_last]) if above_last else True
                return 'ΧΚ' if (cant_drop and cant_rise) else 'ΜΚ'
            STATUS[pos] = (status(r.home), status(r.away))
        if r.hs > r.as_: W[r.home] += 1
        else: W[r.away] += 1
        PL[r.home] += 1; PL[r.away] += 1
cnt = collections.Counter(v for st in STATUS.values() for v in st)
P(f'  καταστασεις ομαδων-ματς: {dict(cnt)}')
SM = 11.5
def hpick(r, mu, thr=.08):
    _, _, L, o1, o2 = r
    if abs(L - round(L)) < 1e-9: pw = Phi((mu + L - .5) / SM); pl = Phi((-mu - L - .5) / SM)
    else: pw = Phi((mu + L) / SM); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    if max(e1, e2) < thr: return None
    return (1, o1, L) if e1 >= e2 else (-1, o2, L)
G9 = []
for pos, (sh, sa) in STATUS.items():
    if sh == 'νωρις' and sa == 'νωρις': continue
    r = REC[21].get(pos)
    if r is None or not np.isfinite(HP[pos]): continue
    k = hpick(r['open'], HP[pos])
    if not k: continue
    side, od, L = k; x = (ACT[pos] + L) * side; res = (od - 1) if x > 0 else (0 if x == 0 else -1)
    own, opp = (sh, sa) if side == 1 else (sa, sh)
    G9.append(dict(s=D.season.values[pos], own=own, opp=opp, res=res))
G9 = pd.DataFrame(G9)
def cell(x):
    if not len(x): return '—'
    ps = x.groupby('s').res.sum()
    return f'{100 * x.res.mean():+6.1f}% ({len(x):3d}, {x.res.sum():+5.1f}μ) · ' + ' '.join(f'{s[-2:]}:{v:+.1f}' for s, v in ps.items())
P(f'  picks χαντικαπ ≥8% (ανοιγμα) στα ματς των τελευταιων 9 αγωνων: {cell(G9)}')
for lab, m in (('ΥΠΕΡ ΧΚ κοντρα σε ΜΚ', (G9.own == 'ΧΚ') & (G9.opp == 'ΜΚ')), ('ΥΠΕΡ ΜΚ κοντρα σε ΧΚ', (G9.own == 'ΜΚ') & (G9.opp == 'ΧΚ')),
               ('και οι 2 ΧΚ', (G9.own == 'ΧΚ') & (G9.opp == 'ΧΚ')), ('και οι 2 ΜΚ', (G9.own == 'ΜΚ') & (G9.opp == 'ΜΚ'))):
    P(f'    {lab:22s} {cell(G9[m])}')
cutm = (G9.own == 'ΧΚ') & (G9.opp == 'ΜΚ'); x = G9[cutm]
ps = x.groupby('s').res.sum(); sea3 = [s for s in ps.index if (x.s == s).sum() >= 3]
ok = len(x) >= 15 and x.res.mean() < 0 and G9[~cutm].res.sum() >= G9.res.sum() and sum(ps[s] < 0 for s in sea3) >= len(sea3) - 1
P(f'  → κανονας «κοψε ΥΠΕΡ ΧΚ κοντρα σε ΜΚ»: {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"} · μοναδες χωρις αυτα {G9[~cutm].res.sum():+.1f} vs με {G9.res.sum():+.1f}')
P('  ΣΥΝΟΛΑ στους τελευταιους 9: πραγμ − κλεισιμο ανα αριθμο ομαδων ΧΚ · picks live συνολων ≥8%')
TT = []
for pos, (sh, sa) in STATUS.items():
    if sh == 'νωρις' and sa == 'νωρις': continue
    r = R23.get(pos)
    if r is None: continue
    n = (sh == 'ΧΚ') + (sa == 'ΧΚ'); k = tpick(r['open'], TP[pos]) if np.isfinite(TP[pos]) else None
    res = None
    if k: x = (TOT[pos] - r['open'][2]) * k[0]; res = (k[1] - 1) if x > 0 else (0 if x == 0 else -1)
    TT.append(dict(s=D.season.values[pos], n=n, cl=TOT[pos] - r[0][1], res=res, side=k[0] if k else 0))
TT = pd.DataFrame(TT)
for n in (0, 1, 2):
    x = TT[TT.n == n]; pk = x.dropna(subset=['res'])
    P(f'    {n} ομαδες ΧΚ: n {len(x):4d} · πραγμ − κλεισιμο {x.cl.mean():+5.2f} ± {x.cl.std() / np.sqrt(max(len(x), 1)):.2f} · ανα σεζον ' +
      ' '.join(f'{s[-2:]}:{v:+.1f}' for s, v in x.groupby('s').cl.mean().items()) +
      f' · picks {100 * pk.res.mean() if len(pk) else float("nan"):+.1f}% ({len(pk)}, over {(pk.side == 1).sum()} / under {(pk.side == -1).sum()})')
open('el_tests_1021a_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
