# -*- coding: utf-8 -*-
"""t38_totals_forward.py — ΣΥΝΟΛΑ NBA: ΜΕΛΛΟΝΤΙΚΟ ΤΕΣΤ + ΚΙΝΗΤΡΟ (21/10/2026, Στελιος «συνεχισε με οτι τεστ θελεις»).
Βαση _t35_totals.csv (ανοιγμα). Μηχανη Μ2 = αγορα + ridge(μ − αγορα, LO, LD, αμφιβολοι, περιοδος, γραμμη, αγων ≤10) (t36).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 Α WALK-FORWARD (καθε σεζον εκπαιδευεται ΜΟΝΟ στις προηγουμενες): 2024 ← 2022-23 · 2025 ← 2022-24 · 2026 ← 2022-25 · κατωφλι 6%.
   ΠΕΡΝΑ αν ROI > 0 σε ≥2/3 σεζον ΚΑΙ συνολικα > 0 ΚΑΙ CLV > 0 ΚΑΙ RMSE καλυτερο απο την αγορα σε ≥2/3.
 Β ΚΙΝΗΤΡΟ (Μαρ-Απρ): γκρουπ t27 (ΧΚ = κλειδωμενη/αδιαφορη/tanking/πρακτικα εκτος · ΜΚ = μαχη θεσης/play-in) → ματς με 0/1/2 ομαδες ΧΚ:
   πραγματικο − αγορα (περιγραφικο). Μ2β = Μ2 με «αριθμος ομαδων ΧΚ» αντι για τον μηνα Μαρ-Απρ · Μ2γ = και τα δυο.
   LOSO RMSE + ROI ≥6%: το Μ2β/γ αντικαθιστα το Μ2 αν RMSE καλυτερο σε ≥3/5 ΚΑΙ ROI οχι χειροτερο.
Εξοδος: t38_totals_forward_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
exec(src)
t27 = open(os.path.join(SC, 't27_april_rules.py'), encoding='utf-8').read().split("OLD = pd.read_csv")[0]
ns = {'__file__': os.path.join(SC, 't27_april_rules.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(t27, ns)
GRP, PRACT, SEAS, dDg = ns['GRP'], ns['PRACT'], ns['SEAS'], ns['dD']
NOM = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING')
def nomot(i, t):
    s, d = SEAS[i], dDg[i]; g = GRP.get((s, d, t), 'νωρις')
    return int(g in NOM or (s, d, t) in PRACT)
D = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
D['nchk'] = [nomot(i, h) + nomot(i, a) for i, h, a in zip(D.i, D.home, D.away)]
ys = D.sea.values; y = (D.tot - D.fair).values
out2 = []
def P2(s=''): print(s, flush=True); out2.append(str(s))
def fit_pred(Xf, tr, te, lam=50):
    A = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ y[tr])
    return D.fair.values[te] + np.c_[np.ones(te.sum()), Xf[te]] @ b
# ---------- Α ----------
P2('=== Α · WALK-FORWARD (εκπαιδευση μονο σε προηγουμενες σεζον) · Μ2 · ≥6% · ανοιγμα ===')
Xf = feats(D); D['wf'] = np.nan; ok_roi = ok_rm = 0; tot_u = []
for s in (2024, 2025, 2026):
    tr = ys < s; te = ys == s; D.loc[te, 'wf'] = fit_pred(Xf, tr, te)
    d = D[te]; pk = picks(d, col='wf', thr=.06)
    rm_w = np.sqrt(np.mean((d.tot - d.wf) ** 2)); rm_m = np.sqrt(np.mean((d.tot - d.fair) ** 2))
    ok_roi += pk.res.mean() > 0; ok_rm += rm_w < rm_m; tot_u.append(pk)
    P2(f'  {s} (εκπαιδευση {sorted(set(ys[tr]))}): RMSE Μ2 {rm_w:.3f} vs αγορα {rm_m:.3f} · picks {cell(pk)} | over {cell(pk[pk.sd == 1])} | under {cell(pk[pk.sd == -1])}')
    P2('       ανα μηνα: ' + ' · '.join(f'{m}: {100 * pk[pk.mon == m].res.mean():+.0f}% ({len(pk[pk.mon == m])})' for m in (10, 11, 12, 1, 2, 3, 4) if len(pk[pk.mon == m])))
T_ = pd.concat(tot_u)
P2(f'  ΣΥΝΟΛΟ 2024-26: {cell(T_)} → {"ΠΕΡΝΑ" if ok_roi >= 2 and T_.res.mean() > 0 and T_.clv.mean() > 0 and ok_rm >= 2 else "ΔΕΝ περνα"} (ROI θετικο {ok_roi}/3, RMSE καλυτερο {ok_rm}/3)')
# ---------- Β ----------
P2(''); P2('=== Β · ΚΙΝΗΤΡΟ (Μαρ-Απρ): ματς με 0/1/2 ομαδες χωρις κινητρο — πραγματικο − αγορα ανοιγματος ===')
MA = D[D.mon.isin([3, 4])]
for k in (0, 1, 2):
    d = MA[MA.nchk == k]; P2(f'  {k} ομαδες ΧΚ: n {len(d):4d} · πραγμ − αγορα {(d.tot - d.fair).mean():+5.2f} ± {(d.tot - d.fair).std() / np.sqrt(max(len(d), 1)):.2f} · Μαρ {(d[d.mon == 3].tot - d[d.mon == 3].fair).mean():+5.2f} ({len(d[d.mon == 3])}) · Απρ {(d[d.mon == 4].tot - d[d.mon == 4].fair).mean():+5.2f} ({len(d[d.mon == 4])})')
base = feats(D)
VAR = {'Μ2': base, 'Μ2β (ΧΚ αντι Μαρ-Απρ)': np.c_[np.delete(base, 6, axis=1), D.nchk.values],
       'Μ2γ (και τα δυο)': np.c_[base, D.nchk.values], 'Μ2δ (+ Απρ χωριστα)': np.c_[base, (D.mon == 4).astype(float)]}
RES = {}
for jj, (nm, Xv) in enumerate(VAR.items()):
    pr = np.zeros(len(D))
    for s in SE:
        te = ys == s; pr[te] = fit_pred(Xv, ys != s, te)
    D[f'p{jj}'] = pr; pk = picks(D, col=f'p{jj}', thr=.06)
    rms = {s: np.sqrt(np.mean((D.tot[ys == s] - pr[ys == s]) ** 2)) for s in SE}; RES[nm] = (rms, pk)
for nm, (rms, pk) in RES.items():
    bet = sum(rms[s] < RES['Μ2'][0][s] - 1e-9 for s in SE)
    P2(f'  {nm:24s} RMSE ' + ' · '.join(f'{rms[s]:.3f}' for s in SE) + f' · καλυτερο απο Μ2 {bet}/5 · picks {cell(pk)} · Μαρ-Απρ {cell(pk[pk.mon.isin([3, 4])])}')
open(os.path.join(SC, 't38_totals_forward_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
