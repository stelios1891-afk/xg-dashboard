# -*- coding: utf-8 -*-
"""t19_janfeb_diag.py — ΓΙΑΤΙ ΙΑΝ-ΦΕΒ ΜΕΤΡΙΑ; ΔΙΑΓΝΩΣΤΙΚΑ (20/10/2026, Στελιος). ΠΕΡΙΓΡΑΦΙΚΟ.
Μοντελο = live (production + B2B + απουσιες αντικ. −2 + μεταγραφες α1). Picks = edge ≥8% στο ανοιγμα (Crown). Περιοδοι: Οκτ · Νοε-Δεκ · Ιαν-Φεβ · Μαρ
(Απριλιος εκτος — γνωστο θεμα κινητρου).
1) λαθος μοντελου vs κλεισιματος, φαβορι/αουτσαιντερ  2) CLV: κινηση ανοιγμα→κλεισιμο προς το pick  3) ΣΕ ΠΟΙΕΣ ΟΜΑΔΕΣ: θεση στη βαθμολογια
   (ποσοστο νικων ως τοτε, κατα ταξη 1-30) — ποσα picks σε ΑΔΥΝΑΜΕΣ ομαδες καθε μηνα & ROI, και υπολοιπο μοντελου για τις αδυναμες
   (Στελιος: «μηπως τον Μαρτιο το μοντελο τις θεωρει πια αδυναμες και δεν τις πονταρει;»)  4) απουσιες: ποσες/ποσο μεγαλες, και αν το κοστος μας
   ειναι σωστο ανα περιοδο  5) συμπιεση: μεγαλα φαβορι (μοντελο ≥8 π.) — υποτιμα το μοντελο τη διαφορα; Εξοδος: t19_janfeb_diag_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE = ns['BASE']; MKH = ns['MKH']
LH, LA = ns['LH'], ns['LA']
inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']
V = BASE + ns['adj'](1.0, -2.0, None)
ABS = 0.75 * (LH - LA)                                     # το κομματι των απουσιων στη V (γηπ)
MON = G.date.dt.month.values
PER = np.array(['Οκτ' if m == 10 else 'Νοε-Δεκ' if m in (11, 12) else 'Ιαν-Φεβ' if m in (1, 2) else 'Μαρ' if m == 3 else 'Απρ' for m in MON])
# βαθμολογια ως τη μερα του αγωνα (ποσοστο νικων, ταξη 1 = καλυτερη)
W = collections.Counter(); N = collections.Counter(); RANK = {}
order = np.argsort(dD, kind='stable'); day_games = collections.defaultdict(list)
for i in order: day_games[(SEAS_G[i], dD[i])].append(i)
for (s, d) in sorted(day_games):
    teams = {t for (ss, t) in N if ss == s} | {G.home.values[i] for i in day_games[(s, d)]} | {G.away.values[i] for i in day_games[(s, d)]}
    pct = {t: (W[(s, t)] + 1) / (N[(s, t)] + 2) for t in teams}
    rk = {t: r + 1 for r, t in enumerate(sorted(pct, key=lambda t: -pct[t]))}
    for i in day_games[(s, d)]:
        RANK[(i, G.home.values[i])] = rk[G.home.values[i]]; RANK[(i, G.away.values[i])] = rk[G.away.values[i]]
    for i in day_games[(s, d)]:
        h, a = G.home.values[i], G.away.values[i]; N[(s, h)] += 1; N[(s, a)] += 1
        if ACT[i] > 0: W[(s, h)] += 1
        elif ACT[i] < 0: W[(s, a)] += 1
rows = []
for i, d in MKH.items():
    if SEAS_G[i] not in EV or not np.isfinite(V[i]) or PER[i] == 'Απρ': continue
    L, mk, o1, o2 = d['o']; cl = d['c'][1]
    pw, pp, pl = cover_(V[i], L, SIG_); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    team = G.home.values[i] if s_ == 1 else G.away.values[i]; opp = G.away.values[i] if s_ == 1 else G.home.values[i]
    r = dict(i=i, sea=SEAS_G[i], per=PER[i], em=(ACT[i] - V[i]) ** 2, ec=(ACT[i] - cl) ** 2, pick=e >= .08, fav=(L * s_) < 0,
             rk=RANK.get((i, team), 15), rko=RANK.get((i, opp), 15), clv=s_ * (cl - mk), absz=abs(ABS[i]),
             vline=V[i], act=ACT[i], cl=cl, hr=RANK.get((i, G.home.values[i]), 15), ar=RANK.get((i, G.away.values[i]), 15),
             res_bad=np.nan)
    if e >= .08:
        x = (ACT[i] + L) * s_; r['res'] = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    rows.append(r)
import pandas as pd
X = pd.DataFrame(rows)
PERS = ('Οκτ', 'Νοε-Δεκ', 'Ιαν-Φεβ', 'Μαρ')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def roi(d):
    if not len(d): return '      —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
P('NBA · ΔΙΑΓΝΩΣΤΙΚΑ ΙΑΝ-ΦΕΒ vs ΥΠΟΛΟΙΠΟΙ ΜΗΝΕΣ (χωρις Απριλιο) · live μοντελο · 5 σεζον · picks ≥8% ανοιγμα')
P(''); P('=== 1. ΛΑΘΟΣ: μοντελο vs κλεισιμο (ολα τα ματς) ===')
for p in PERS:
    d = X[X.per == p]; P(f'  {p:8s} {len(d):5d} ματς · μοντελο {np.sqrt(d.em.mean()):5.2f} · κλεισιμο {np.sqrt(d.ec.mean()):5.2f} · χασμα {np.sqrt(d.em.mean()) - np.sqrt(d.ec.mean()):+.2f}')
P(''); P('=== 2. PICKS & CLV (κινηση αγορας ανοιγμα→κλεισιμο προς το pick, + = η αγορα ηρθε προς εμας) ===')
for p in PERS:
    d = X[(X.per == p) & X.pick]
    for lab, dd in (('φαβορι', d[d.fav]), ('αουτσαιντερ', d[~d.fav])):
        P(f'  {p:8s} {lab:12s} ROI {roi(dd)} · CLV {dd.clv.mean():+.2f}π · ηρθε προς εμας {100 * (dd.clv > 0.25).mean():.0f}% / κοντρα {100 * (dd.clv < -0.25).mean():.0f}%')
P(''); P('=== 3. ΣΕ ΠΟΙΕΣ ΟΜΑΔΕΣ ΠΟΝΤΑΡΟΥΜΕ (θεση της ομαδας του pick στη βαθμολογια ως τοτε) ===')
for p in PERS:
    d = X[(X.per == p) & X.pick]
    for lab, m in (('αδυναμες (θεση 23-30)', d.rk >= 23), ('μεσαιες (9-22)', (d.rk >= 9) & (d.rk <= 22)), ('δυνατες (1-8)', d.rk <= 8)):
        dd = d[m]; P(f'  {p:8s} {lab:22s} {100 * len(dd) / max(len(d), 1):4.0f}% των picks · ROI {roi(dd)} · αουτσ. εκει {100 * (~dd.fav).mean() if len(dd) else 0:.0f}%')
P('  -- υπολοιπο μοντελου για τις ΑΔΥΝΑΜΕΣ ομαδες (θεση 23-30) σε ΟΛΑ τα ματς τους (+ = επαιξαν καλυτερα απο την προβλεψη) & το ιδιο για την αγορα --')
for p in PERS:
    d = X[X.per == p]
    rm_, rc_ = [], []
    for r in d.itertuples(index=False):
        for rk, sg in ((r.hr, 1), (r.ar, -1)):
            if rk >= 23: rm_.append(sg * (r.act - r.vline)); rc_.append(sg * (r.act - r.cl))
    rm_, rc_ = np.array(rm_), np.array(rc_)
    P(f'  {p:8s} n {len(rm_):4d} · μοντελο {rm_.mean():+5.2f} ± {rm_.std() / np.sqrt(len(rm_)):.2f} · αγορα κλεισ. {rc_.mean():+5.2f} ± {rc_.std() / np.sqrt(len(rc_)):.2f}')
P(''); P('=== 4. ΑΠΟΥΣΙΕΣ: μεγεθος και ακριβεια ανα περιοδο ===')
for p in PERS:
    d = X[X.per == p]; big = d[d.absz >= 1]
    # ποσο κοστιζει πραγματικα 1 δικος μας ποντος απουσιας: κλιση (πραγμ − μοντελο χωρις απουσιες) πανω στη διορθωση
    ii = d.i.values; y = ACT[ii] - (V[ii] - ABS[ii]); xx = ABS[ii]
    m = np.abs(xx) > 0
    k = np.polyfit(xx[m], y[m], 1)[0] if m.sum() > 50 else np.nan
    P(f'  {p:8s} μεση |διορθωση απουσιων| {d.absz.mean():.2f}π · ματς με ≥1π {100 * len(big) / len(d):.0f}% · πραγματικο κοστος ανα δικο μας ποντο {k:.2f} (1.00 = σωστο)')
P(''); P('=== 5. ΣΥΜΠΙΕΣΗ: ματς οπου το μοντελο βλεπει μεγαλο φαβορι (≥8 π.) ===')
for p in PERS:
    d = X[(X.per == p) & (X.vline.abs() >= 8)]
    sg = np.sign(d.vline)
    P(f'  {p:8s} n {len(d):4d} · μοντελο {np.mean(np.abs(d.vline)):5.1f} · αγορα κλεισ. {np.mean(sg * d.cl):5.1f} · πραγματικο {np.mean(sg * d.act):5.1f}')
open(os.path.join(SC, 't19_janfeb_diag_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
