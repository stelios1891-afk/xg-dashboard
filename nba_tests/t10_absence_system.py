# -*- coding: utf-8 -*-
"""t10_absence_system.py — ΕΙΝΑΙ ΚΑΛΟ ΤΟ ΣΥΣΤΗΜΑ ΑΠΟΥΣΙΩΝ; (20/10/2026, Στελιος: «ειτε η απουσια βγει πριν ειτε μετα δεν εχει σημασια,
σημασια εχει να τις τιμολογουμε σωστα — σπανια οι ομαδες ειναι 100%»). ΠΕΡΙΓΡΑΦΙΚΟ + συγκριση εναλλακτικων, οχι κανονας.
ΟΛΕΣ οι απουσιες της ημερας (εκ των υστερων, box score): παικτης ρολου (≥20′ μ.ο. 10 τελευταιων φετος για την ομαδα) που ΔΕΝ επαιξε,
χωρις ανταλλαγη — ξαφνικες (επαιξε στο προηγουμενο) ΚΑΙ μακροχρονιες. Διαρκεια = αγωνες ομαδας που λειπει (μαζι με σημερα).
LIVE συστημα = 0.75 × Σ(αξια + 1) × λεπτα/48 (ιδιο για ολες, ανεξαρτητα απο διαρκεια) πανω στη μηχανη (+ B2B 3).
Συγκριση με: ΠΡΑΓΜΑΤΙΚΟ αποτελεσμα και ΚΛΕΙΣΙΜΟ αγορας (Crown) — ποσο τιμολογει η καθε πλευρα και ποιος βγαινει σωστος.
Εναλλακτικες (LOSO 5 σεζον, RMSE): συντελεστης, επιπεδο αντικαταστατη, «σταρ» εξτρα, σβησιμο με τη διαρκεια, φθινουσα για πολλες απουσιες.
Εξοδος: t10_absence_system_out.txt"""
import os, io, sys, contextlib, collections, itertools
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'news_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'news_test.py'), encoding='utf-8').read().split("def reg(y, X, m):")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; A = ns['A']; value = ns['value']; traded = ns['traded']
OPN, CLS = ns['OPN'], ns['CLS']; ev_m = ns['ev_m']; MG = np.asarray(ns['MG'], float); EV = sorted(set(SEAS_G[ev_m]))
ACT = (G.hs - G.as_).values.astype(float)
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
M0 = MG + 3.0 * (B2A - B2H)                         # μηχανη ΧΩΡΙΣ απουσιες

# ---------- ολες οι απουσιες της ημερας ----------
ABS = {}                                            # (team, day) → [(v, avg_min, duration)]
for (t, s), g in A.groupby(['team', 's']):
    days = sorted(g.d.unique()); played = {d: dict(zip(x.pid, x.MIN)) for d, x in g.groupby('d')}
    hist = collections.defaultdict(list)
    for j, d in enumerate(days):
        lst = []
        for p, H in hist.items():
            avg = float(np.mean([m for _, m in H[-10:]]))
            if avg < 20 or played[d].get(p, 0) > 0: continue
            lastp = H[-1][0]
            if traded(p, t, lastp, d): continue
            dur = sum(1 for x in days[:j + 1] if x > lastp)
            lst.append((value(p, s - 1), avg, dur))
        if lst: ABS[(t, np.datetime64(d))] = lst
        for p, m in played[d].items():
            if m > 0: hist[p].append((d, m))
GL = []                                             # ανα αγωνα: λιστα (side, v, avg, dur)
for i in range(len(G)):
    L = []
    for side, t in ((1, G.home.values[i]), (-1, G.away.values[i])):
        for v, avg, dur in ABS.get((t, dD[i]), []): L.append((side, v, avg, dur))
    GL.append(L)

def cost(i, K=0.75, REP=-1.0, star=0.0, decay=None, conc=1.0):
    """διορθωση περιθωριου γηπεδουχου (−: χανει ο γηπ). decay: (d1, w2, d2, w3) βαρος ανα διαρκεια · conc: Σ^conc ανα ομαδα"""
    tot = {1: 0.0, -1: 0.0}
    for side, v, avg, dur in GL[i]:
        ve = v + star * max(v - 2.0, 0.0)
        w = 1.0
        if decay: w = 1.0 if dur <= decay[0] else (decay[1] if dur <= decay[2] else decay[3])
        tot[side] += w * max(ve - REP, 0.0) * avg / 48
    f = lambda x: x ** conc if x > 0 else 0.0
    return -K * (f(tot[1]) - f(tot[-1]))
LIVE = np.array([cost(i) for i in range(len(GL))])
PRED = M0 + LIVE
NA = np.array([len(x) for x in GL]); DUR = [max([d for *_, d in x], default=0) for x in GL]
m0 = ev_m & np.isfinite(CLS)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def reg(y, X, m):
    y = y[m]; X = np.c_[np.ones(m.sum()), *[x[m] for x in X]]; c, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ c; s2 = r.var() * len(y) / (len(y) - X.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X))); return c[1:], se[1:]
rm = lambda a, b, m: float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))

P('NBA · ΕΙΝΑΙ ΚΑΛΟ ΤΟ ΣΥΣΤΗΜΑ ΑΠΟΥΣΙΩΝ; · ΟΛΕΣ οι απουσιες ρολου της ημερας (ξαφνικες + μακροχρονιες) · 5 σεζον, κλεισιμο Crown')
P(f'αγωνες {m0.sum()} · με ≥1 απουσια ρολου: {(m0 & (NA > 0)).mean() / m0.mean() * 100:.0f}% · μεσος αριθμος απωντων ανα ματς {NA[m0].mean():.2f} · '
  f'μεση |διορθωση| live {np.abs(LIVE[m0]).mean():.2f} π.')

P(''); P('=== 1. ΣΥΝΟΛΙΚΗ ΕΙΚΟΝΑ: λαθος (RMSE) απεναντι στο ΑΠΟΤΕΛΕΣΜΑ ===')
P(f'  μηχανη χωρις απουσιες {rm(M0, ACT, m0):.3f} · LIVE με απουσιες {rm(PRED, ACT, m0):.3f} · κλεισιμο αγορας {rm(CLS, ACT, m0):.3f} · ανοιγμα {rm(OPN, ACT, m0 & np.isfinite(OPN)):.3f}')
P(f'  αποσταση απο το κλεισιμο: χωρις απουσιες {rm(M0, CLS, m0):.3f} → LIVE {rm(PRED, CLS, m0):.3f}  (οσο πιο μικρη, τοσο πιο κοντα στην αγορα)')
for s in EV:
    ms = m0 & (SEAS_G == s)
    P(f'    {s}: χωρις {rm(M0, ACT, ms):.3f} · LIVE {rm(PRED, ACT, ms):.3f} · κλεισιμο {rm(CLS, ACT, ms):.3f} · αποσταση απο κλεισιμο {rm(M0, CLS, ms):.2f} → {rm(PRED, CLS, ms):.2f}')

P(''); P('=== 2. ΑΝΑ ΜΕΓΕΘΟΣ ΑΠΟΥΣΙΩΝ: χανουμε εδαφος απο την αγορα οταν λειπουν πολλοι; ===')
P('  (καθαρη διαφορα απουσιων των 2 ομαδων σε δικους μας ποντους · «χασμα» = RMSE LIVE − RMSE κλεισιματος απεναντι στο αποτελεσμα)')
P(f'  {"live διορθωση":16s} {"n":>5s} {"RMSE χωρις":>10s} {"RMSE LIVE":>9s} {"RMSE κλεισ.":>11s} {"χασμα":>6s} {"εμεις":>6s} {"αγορα":>6s} {"πραγμ.":>7s}')
X = np.abs(LIVE); sgn = np.sign(LIVE)
for lo, hi in ((0, .25), (.25, 1), (1, 2), (2, 3.5), (3.5, 99)):
    m = m0 & (X >= lo) & (X < hi)
    P(f'  {f"{lo:g}-{hi:g}" if hi < 99 else f"≥{lo:g}":16s} {m.sum():5d} {rm(M0, ACT, m):10.3f} {rm(PRED, ACT, m):9.3f} {rm(CLS, ACT, m):11.3f} '
      f'{rm(PRED, ACT, m) - rm(CLS, ACT, m):+6.2f} {np.mean(-sgn[m] * LIVE[m]) if lo > 0 else 0:6.2f} {np.mean(-sgn[m] * (CLS - M0)[m]) if lo > 0 else 0:6.2f} '
      f'{np.mean(-sgn[m] * (ACT - M0)[m]) if lo > 0 else 0:7.2f}')
P('  εμεις / αγορα / πραγμ. = μεσο κοστος για την ομαδα με τις περισσοτερες απουσιες (αγορα = κλεισιμο − μηχανη χωρις απουσιες)')

P(''); P('=== 3. ΑΝΑ ΔΙΑΡΚΕΙΑ: ανα 1 «δικο μας» ποντο, ποσο κοστιζει πραγματικα και ποσο τιμολογει η αγορα (μαζι, ελεγχος) ===')
BK = ((1, 1, 'ξαφνικη (1ος αγωνας)'), (2, 5, '2-5 αγωνες'), (6, 15, '6-15 αγωνες'), (16, 999, '16+ αγωνες'))
XS = []
for lo, hi, _ in BK:
    XS.append(np.array([cost(i, decay=None) if False else -0.75 * sum(sd * max(v + 1, 0) * a / 48 for sd, v, a, d in GL[i] if lo <= d <= hi) for i in range(len(GL))]))
cA, sA = reg(ACT - M0, XS, m0); cC, sC = reg(CLS - M0, XS, m0); cL, sL = reg(ACT - CLS, XS, m0)
for k, (lo, hi, lab) in enumerate(BK):
    n = int((m0 & (np.abs(XS[k]) >= .25)).sum())
    P(f'  {lab:22s} (n {n:4d}) · πραγματικο {cA[k]:5.2f} ± {sA[k]:.2f} · αγορα κλεισιμο {cC[k]:5.2f} ± {sC[k]:.2f} · μενει μετα το κλεισιμο {cL[k]:+5.2f} ± {sL[k]:.2f}')
P('  (1.00 = ακριβως οσο το live· η μηχανη ratings «απορροφα» σιγα σιγα τις μακριες απουσιες, γι αυτο εκει το εξτρα κοστος πεφτει)')

P(''); P('=== 4. ΟΤΑΝ ΔΙΑΦΩΝΟΥΜΕ ΜΕ ΤΗΝ ΑΓΟΡΑ — ποιος εχει δικιο; αποτελεσμα − κλεισιμο = b × (LIVE − κλεισιμο) ===')
P('  b = 0 → σωστη η αγορα · b = 1 → σωστοι εμεις · ενδιαμεσα = καθε πλευρα εχει κατι')
for lab, m in (('ματς χωρις απουσιες (|διορθ.|<0.25)', m0 & (X < .25)), ('μικρες απουσιες (0.25-2)', m0 & (X >= .25) & (X < 2)),
               ('μεγαλες απουσιες (≥2)', m0 & (X >= 2)), ('ΟΛΑ', m0)):
    c, se = reg(ACT - CLS, [PRED - CLS], m); ps = []
    for s in EV:
        cs, _ = reg(ACT - CLS, [PRED - CLS], m & (SEAS_G == s)); ps.append(f'{cs[0]:+.2f}')
    P(f'  {lab:38s} n {m.sum():4d} · b {c[0]:+.2f} ± {se[0]:.2f} · ανα σεζον {" ".join(ps)}')
c, se = reg(ACT - CLS, [M0 - CLS, LIVE], m0)
P(f'  χωριστα: διαφωνια μηχανης b {c[0]:+.2f} ± {se[0]:.2f} · κομματι απουσιων {c[1]:+.2f} ± {se[1]:.2f}  (το δευτερο = αν οι απουσιες μας προσθετουν κατι πανω απο το κλεισιμο)')

P(''); P('=== 5. ΕΙΝΑΙ Ο ΔΙΚΟΣ ΜΑΣ ΤΡΟΠΟΣ Ο ΚΑΛΥΤΕΡΟΣ; εναλλακτικες, LOSO (διαλεγω στις 4 σεζον, μετραω στην 5η) ===')
GRID = dict(K=(0.5, 0.75, 1.0, 1.25), REP=(-2.0, -1.0, -0.5), star=(0.0, 0.5), decay=(None, (5, 0.6, 15, 0.3)), conc=(1.0, 0.8))
combos = list(itertools.product(*GRID.values()))
P(f'  πλεγμα {len(combos)} παραλλαγων: συντελεστης {GRID["K"]} · αντικαταστατης {GRID["REP"]} · σταρ εξτρα (αξια>2) {GRID["star"]} · '
  f'σβησιμο με διαρκεια {GRID["decay"]} · φθινουσα πολλων απουσιων Σ^{GRID["conc"]}')
VAL = {}
for cb in combos:
    VAL[cb] = M0 + np.array([cost(i, *cb) for i in range(len(GL))])
live_cb = (0.75, -1.0, 0.0, None, 1.0)
def loso(metric_target):
    pred = np.full(len(G), np.nan); picks = {}
    for s in EV:
        tr = m0 & (SEAS_G != s)
        best = min(combos, key=lambda cb: rm(VAL[cb], metric_target, tr)); picks[s] = best; ms = SEAS_G == s; pred[ms] = VAL[best][ms]
    return pred, picks
for tgt_lab, tgt in (('ΑΠΟΤΕΛΕΣΜΑ', ACT), ('ΚΛΕΙΣΙΜΟ αγορας', CLS)):
    pr, pk = loso(tgt)
    P(f'  στοχος {tgt_lab}: LOSO {rm(pr, tgt, m0):.3f} vs LIVE {rm(VAL[live_cb], tgt, m0):.3f} vs χωρις απουσιες {rm(M0, tgt, m0):.3f}')
    for s in EV: P(f'      {s}: επελεξε {pk[s]}')
    rank = sorted(combos, key=lambda cb: rm(VAL[cb], tgt, m0))
    P(f'    καλυτερες 5 (ολα μαζι): ' + ' | '.join(f'{cb} {rm(VAL[cb], tgt, m0):.3f}' for cb in rank[:5]))
    P(f'    θεση του LIVE: {rank.index(live_cb) + 1}/{len(combos)}')
P('  (στη σειρα: συντελεστης, αντικαταστατης, σταρ, σβησιμο, φθινουσα)')
open(os.path.join(SC, 't10_absence_system_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
