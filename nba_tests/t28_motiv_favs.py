# -*- coding: utf-8 -*-
"""t28_motiv_favs.py — Τ6 + Τ7 + Τ8: ΦΑΒΟΡΙ ΜΕ ΚΙΝΗΤΡΟ ΚΟΝΤΡΑ ΣΕ ΟΜΑΔΕΣ ΧΩΡΙΣ ΚΙΝΗΤΡΟ (21/10/2026, Στελιος: «αν το μοντελο χανει πικς φαβορι
κοντρα σε tanking/αδιαφορες/κλειδωμενες γιατι τις βλεπει πιο ισορροπημενες απο την πραγματικοτητα, ισως με ποινη ή χαμηλοτερο κατωφλι
να βρουμε περισσοτερα φαβορι πικς»).
ΜΗΧΑΝΗ = t22/t24c (αντιγραφο live χωρις «εχασε 2», απουσιες απο την τελευταια επισημη αναφορα ≤ τ, μονο Out, τιμη Crown στο τ).
ΟΛΑ τα ματς αγωνων 61-82 (οχι μονο picks) σε 3 στιγμες (ανοιγμα · Τ−2ω · Τ−30′) → nba_tests/_t28_games.csv. Γκρουπ: t27 (+ «πρακτικα εκτος»).
ΧΩΡΙΣ ΚΙΝΗΤΡΟ (ΧΚ) = κλειδωμενη/αδιαφορη/tanking/πρακτικα εκτος · ΜΕ ΚΙΝΗΤΡΟ (ΜΚ) = μαχη θεσης 1-6 / play-in.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 Τ6 «76-82 ΜΟΝΟ ΦΑΒΟΡΙ» (edge ≥8%, χωρις picks υπερ ΧΚ κοντρα σε ΜΚ): ΠΕΡΝΑ αν ROI > 0 σε ≥4/5 σεζον ΣΕ ΚΑΘΕ στιγμη ΚΑΙ CLV > 0 στο ανοιγμα.
   + χωριστα 76-78 / 79-82 + 3 παραδειγματα.
 Τ7 ΠΟΙΝΗ δ π. στην ομαδα ΧΚ οταν παιζει με ΜΚ (δ ∈ {0,1,2,3,4}), αγωνες 71-75 (ολα) και 76-82 (μονο φαβορι, οπως Τ6):
   LOSO — δ με τις περισσοτερες μοναδες στις αλλες 4 σεζον, εφαρμογη στην 5η. ΠΕΡΝΑ αν μοναδες LOSO > δ=0 συνολικα ΚΑΙ σε ≥4/5 σεζον
   (ισοτητα = οχι χειροτερο) ΚΑΙ CLV των νεων picks > 0, στο ανοιγμα ΚΑΙ στο Τ−30′.
 Τ8 ΚΑΤΩΦΛΙ για picks ΥΠΕΡ ΜΚ κοντρα σε ΧΚ ∈ {8,6,4,2}% (τα υπολοιπα μενουν 8%), ιδια περιοχη/κριτηρια με Τ7.
Εξοδος: t28_motiv_favs_out.txt"""
import os, sys, io, contextlib, pickle, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
FN = os.path.join(SC, '_t28_games.csv')
import numpy as np, pandas as pd
if not os.path.exists(FN) or os.environ.get('T28_REBUILD'):
    src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g22 = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(src, g22)
    G, SEAS_G, dD, EV, ACT, VNO, SER, SHIFT = (g22[k] for k in ('G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT'))
    W_A, abs_cost, line_at, REP_SEASONS = g22['W_A'], g22['abs_cost'], g22['line_at'], g22['REP_SEASONS']
    GN = np.asarray(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['GN'])
    rows = []
    for i, (sw, tip, r21, _) in SER.items():
        s = int(SEAS_G[i])
        if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]) or GN[i] < 61: continue
        rr = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rr = [x for x in rr if x[0] <= tip + 900]
        if not rr: continue
        close = line_at(rr, tip, sw); h, a, d = G.home.values[i], G.away.values[i], dD[i]
        for lab, hrs in (('ανοιγμα', None), ('Τ−2ω', 2), ('Τ−30′', 0.5)):
            tau = rr[0][0] if hrs is None else tip - hrs * 3600
            if hrs is not None and tau < rr[0][0]: continue
            ln = line_at(rr, tau, sw)
            if not ln: continue
            L, oh, oa, fair, _ = ln
            ch, _ = abs_cost(h, d, s, tau, W_A); ca, _ = abs_cost(a, d, s, tau, W_A)
            rows.append(dict(i=i, sea=s, gn=int(GN[i]), tau=lab, home=h, away=a, m=VNO[i] - ch + ca, L=L, oh=oh, oa=oa, fair=fair, cfair=close[3], act=ACT[i]))
    pd.DataFrame(rows).to_csv(FN, index=False)
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_csv(FN)
# --- γκρουπ (t27) ---
t27 = open(os.path.join(SC, 't27_april_rules.py'), encoding='utf-8').read().split("OLD = pd.read_csv")[0]
ns = {'__file__': os.path.join(SC, 't27_april_rules.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(t27, ns)
GRP, PRACT, SEAS, dDg = ns['GRP'], ns['PRACT'], ns['SEAS'], ns['dD']
NOM = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING'); MOT = ('ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN')
def grp(i, t):
    s, d = SEAS[i], dDg[i]; g = GRP.get((s, d, t), 'νωρις')
    return 'ΧΚ' if (g in NOM or (s, d, t) in PRACT) else ('ΜΚ' if g in MOT else 'αλλο')
X['gh'] = [grp(i, t) for i, t in zip(X.i, X.home)]; X['ga'] = [grp(i, t) for i, t in zip(X.i, X.away)]
from statistics import NormalDist
_N = NormalDist()
SIG = 13.5
try:
    import ast
    SIG = float(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['SIG'])
except Exception: pass
def cover(m, L):
    if abs(L - round(L)) < 1e-9:
        pw = _N.cdf((m + L - 0.5) / SIG); pl = _N.cdf((-m - L - 0.5) / SIG); return pw, 1 - pw - pl, pl
    pw = _N.cdf((m + L) / SIG); return pw, 0.0, 1 - pw
def picks(D, pen=0.0, thr_mk=0.08, favs_only=False):
    """→ DataFrame picks (μια ανα ματς/στιγμη) με res, clv, side, fav, kind"""
    out = []
    for r in D.itertuples(index=False):
        m = r.m
        if pen:
            if r.gh == 'ΧΚ' and r.ga == 'ΜΚ': m -= pen
            elif r.ga == 'ΧΚ' and r.gh == 'ΜΚ': m += pen
        pw, pp, pl = cover(m, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        for sd, e, od in ((1, e1, r.oh), (-1, e2, r.oa)):
            us, them = (r.gh, r.ga) if sd == 1 else (r.ga, r.gh)
            thr = thr_mk if (us == 'ΜΚ' and them == 'ΧΚ') else 0.08
            if e < thr or e < (e2 if sd == 1 else e1): continue
            if us == 'ΧΚ' and them == 'ΜΚ': continue                      # κανονας 2 (live στους 71-75)
            own = r.L if sd == 1 else -r.L
            if favs_only and own >= 0: continue
            x = (r.act + r.L) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            out.append(dict(i=r.i, sea=r.sea, gn=r.gn, tau=r.tau, sd=sd, own=own, res=res, clv=sd * (r.cfair - r.fair), e=e,
                            kind=f'{us}→{them}', m=m, L=r.L, act=r.act, home=r.home, away=r.away))
    return pd.DataFrame(out)
SEASONS = sorted(X.sea.unique())
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if d is None or not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):3d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
TAUS = ('ανοιγμα', 'Τ−2ω', 'Τ−30′')
P('NBA · Τ6/Τ7/Τ8 ΦΑΒΟΡΙ ΜΕ ΚΙΝΗΤΡΟ vs ΟΜΑΔΕΣ ΧΩΡΙΣ ΚΙΝΗΤΡΟ · αγωνες 61-82 · απουσιες απο επισημες αναφορες · σ = ' + f'{SIG}')
P(f'ματς×στιγμες: {len(X)} · ΧΚ vs ΜΚ ματς (ανοιγμα): {int(((X.tau == "ανοιγμα") & (((X.gh == "ΧΚ") & (X.ga == "ΜΚ")) | ((X.ga == "ΧΚ") & (X.gh == "ΜΚ")))).sum())}')
# ---------- Τ6 ----------
P(''); P('=== Τ6 · ΑΓΩΝΕΣ 76-82 ΜΟΝΟ ΦΑΒΟΡΙ (edge ≥8%, χωρις υπερ ΧΚ vs ΜΚ) ===')
ok6 = True
for tau in TAUS:
    D = X[(X.tau == tau) & (X.gn >= 76)]
    pa = picks(D); pf = pa[pa.own < 0] if len(pa) else pa; pdg = pa[pa.own > 0] if len(pa) else pa
    ps = pf.groupby('sea').res.sum().reindex(SEASONS, fill_value=0)
    good = int((ps > 0).sum()); ok6 &= good >= 4
    if tau == 'ανοιγμα': ok6 &= pf.clv.mean() > 0
    P(f'  {tau:8s} φαβορι {cell(pf)} · ανα σεζον {", ".join(f"{x:+.1f}" for x in ps)} | (αουτσαιντερ {cell(pdg)})')
    for lo, hi in ((76, 78), (79, 82)): P(f'           {lo}-{hi}: φαβορι {cell(pf[(pf.gn >= lo) & (pf.gn <= hi)])}')
    if tau == 'ανοιγμα':
        P('           ανα ειδος: ' + ' · '.join(f'{k} {cell(d)}' for k, d in pf.groupby('kind') if len(d) >= 8))
        G0 = ns['G']
        for r in pf.sample(min(4, len(pf)), random_state=3).itertuples():
            P(f'           παραδειγμα {str(G0.date.values[r.i])[:10]} {r.home}-{r.away} · στηριζουμε {r.home if r.sd == 1 else r.away} {r.own:+g} ({r.kind}) · '
              f'μοντελο {r.m if r.sd == 1 else -r.m:+.1f} · αποτελεσμα {r.act * r.sd:+.0f} → {r.res:+.2f}μ')
P(f'  → Τ6 {"ΠΕΡΝΑ" if ok6 else "ΔΕΝ περνα"} (κριτηριο: ROI > 0 σε ≥4/5 σεζον σε καθε στιγμη + CLV ανοιγματος > 0)')
# ---------- Τ7 / Τ8 ----------
def loso(name, grid, mk_picks, base_key):
    for tau in ('ανοιγμα', 'Τ−2ω', 'Τ−30′'):
        U = {}; PK = {}
        for k in grid:
            p = mk_picks(tau, k); PK[k] = p
            U[k] = p.groupby('sea').res.sum().reindex(SEASONS, fill_value=0.0) if len(p) else pd.Series(0.0, index=SEASONS)
        ch, diff, added = [], [], []
        for s in SEASONS:
            best = max(grid, key=lambda k: (U[k].drop(s).sum(), -abs(k - base_key))); ch.append(best)
            diff.append(U[best][s] - U[base_key][s])
            b0 = PK[base_key]; b1 = PK[best]
            if len(b1):
                k0 = set(zip(b0.i, b0.sd)) if len(b0) else set()
                added.append(b1[(b1.sea == s).values & np.array([(a, b) not in k0 for a, b in zip(b1.i, b1.sd)], dtype=bool)])
        A_ = pd.concat(added) if added else pd.DataFrame()
        good = sum(1 for x in diff if x >= 0); tot = sum(diff)
        verdict = tot > 0 and good >= 4 and len(A_) > 0 and A_.clv.mean() > 0
        P(f'  {tau:8s} ' + ' · '.join(f'{k}: {cell(PK[k])}' for k in grid))
        P(f'           LOSO επιλογες {ch} · μοναδες − βαση {tot:+.1f} (οχι χειροτερο {good}/5: {", ".join(f"{x:+.1f}" for x in diff)}) · '
          f'νεα picks {len(A_)} CLV {A_.clv.mean() if len(A_) else float("nan"):+.2f} → {"ΠΕΡΝΑ" if verdict else "ΔΕΝ περνα"}')
for lo, hi, fo, lab in ((71, 75, False, 'αγωνες 71-75 (ολα τα picks)'), (76, 82, True, 'αγωνες 76-82 (μονο φαβορι)')):
    P(''); P(f'=== Τ7 · ΠΟΙΝΗ δ στην ομαδα ΧΩΡΙΣ κινητρο οταν παιζει με ομαδα ΜΕ κινητρο · {lab} ===')
    loso('Τ7', (0, 1, 2, 3, 4), lambda tau, k: picks(X[(X.tau == tau) & (X.gn >= lo) & (X.gn <= hi)], pen=float(k), favs_only=fo), 0)
    P(''); P(f'=== Τ8 · ΚΑΤΩΦΛΙ για picks ΥΠΕΡ ομαδας με κινητρο κοντρα σε ΧΚ (%) · {lab} ===')
    loso('Τ8', (8, 6, 4, 2), lambda tau, k: picks(X[(X.tau == tau) & (X.gn >= lo) & (X.gn <= hi)], thr_mk=k / 100, favs_only=fo), 8)
# περιγραφικο: ποσο «ισορροπημενα» βλεπει το μοντελο τα ματς ΜΚ vs ΧΚ
P(''); P('=== ΠΕΡΙΓΡΑΦΙΚΟ: ματς ΜΚ vs ΧΚ — προβλεψη vs πραγματικο (απο την πλευρα της ομαδας ΜΕ κινητρο, ανοιγμα) ===')
D = X[(X.tau == 'ανοιγμα') & (((X.gh == 'ΧΚ') & (X.ga == 'ΜΚ')) | ((X.ga == 'ΧΚ') & (X.gh == 'ΜΚ')))].copy()
sg = np.where(D.gh == 'ΜΚ', 1, -1)
D['mod'] = sg * D.m; D['mkt'] = -sg * D.L; D['real'] = sg * D.act; D['cl'] = sg * D.cfair
for lo, hi in ((61, 70), (71, 75), (76, 82)):
    d = D[(D.gn >= lo) & (D.gn <= hi)]
    P(f'  αγωνες {lo}-{hi}: n {len(d)} · μοντελο {d["mod"].mean():+5.2f} · αγορα ανοιγ. {d.mkt.mean():+5.2f} · κλεισ. {d.cl.mean():+5.2f} · πραγματικο {d.real.mean():+5.2f}')
open(os.path.join(SC, 't28_motiv_favs_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
