# -*- coding: utf-8 -*-
"""t61_value_systems.py — ΠΟΣΟ ΚΑΛΑ ΕΙΝΑΙ ΤΑ ΣΥΣΤΗΜΑΤΑ ΑΞΙΑΣ ΠΑΙΚΤΗ (22/10/2026, Στελιος: «ποσο καλα ειναι; και ποσο καλα οταν χτιζονται live;»).
Βαση: t59_inseason_value.py (exec ως "def vmix(M):") → AB_ (απουσιες με βαρος, λεπτα live, περσινη value, φετινη box ως τη μερα), D (ματς, m0, act),
  feats/FIT/MU_BY/ST/END (φετινη box αξια σε κλιμακα value, εκπαιδευση μονο σε s′ < s).
Επιμερους περσινα συστηματα: nba_roster_adj.py M = {DARKO, LEBRON, BPM} (ιδια συρρικνωση × mp/(mp+500) με το live value()).
Α. Βαθμονομηση κοστους απουσιας: κοστος = w·0.75·(v+2)·λεπτα/48, καθαρο = κοστος φιλοξ − κοστος γηπ. OLS (act − m0) = a + b·καθαρο (b=1 σωστο μεγεθος),
   RMSE act − (m0 + καθαρο). Ανα ζωνη φετινων λεπτων / ομαδα παικτη: πολλαπλη OLS με ενα καθαρο κοστος ανα ζωνη (ολες μαζι).
Β. Σταθεροποιηση φετινης box: παικτες ≥1500′ στη σεζον · box μετα απο N λεπτα vs box τελους (ιδια) και vs box ΥΠΟΛΟΙΠΟΥ σεζον (χωρις επικαλυψη).
Γ. 3 παραδειγματα σε 15/11, 15/1, 15/3.
Εξοδος: t61_value_systems_out.txt"""
import os, sys, io, contextlib, bisect
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# ---- t59 ως vmix ----
src = open(os.path.join(SC, 't59_inseason_value.py'), encoding='utf-8').read().split('def vmix(M):')[0]
g = {'__file__': os.path.join(SC, 't59_inseason_value.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
AB_, D, feats, FIT, MU_BY, ST, END, NM, VAL = g['AB_'], g['D'], g['feats'], g['FIT'], g['MU_BY'], g['ST'], g['END'], g['NM'], g['VAL']
# ---- επιμερους συστηματα (nba_roster_adj) ----
cwd = os.getcwd(); os.chdir(ROOT)
rsrc = open(os.path.join(ROOT, 'nba_roster_adj.py'), encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
R = {}
with contextlib.redirect_stdout(_B()): exec(rsrc, R)
os.chdir(cwd)
VM, MPT, value, AR = R['M'], R['MPT'], R['value'], R['A']
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
SYS = list(VM.keys())
def vsys(name, p, y, fb):
    Dm = VM[name]
    if (p, y) not in Dm: return fb
    mp = MPT.get((p, y), 0.0); return float(Dm[(p, y)]) * mp / (mp + 500)
# ελεγχος: ξαναυπολογισμος live value == cache
vchk = np.array([value(p, s - 1) for p, s in zip(AB_.pid, AB_.s)])
P(f'ελεγχος: value(pid, s−1) ξαναυπολογισμενη vs cache: μεγιστη διαφορα {np.max(np.abs(vchk - AB_.vprev.values)):.2e} (πρεπει 0) · συστηματα στο M: {SYS}')
for nm_ in SYS:
    AB_[f'v_{nm_}'] = [vsys(nm_, p, s - 1, -1.0) for p, s in zip(AB_.pid, AB_.s)]
    AB_[f'f_{nm_}'] = [vsys(nm_, p, s - 1, vp) for p, s, vp in zip(AB_.pid, AB_.s, AB_.vprev)]
    AB_[f'has_{nm_}'] = [(p, s - 1) in VM[nm_] for p, s in zip(AB_.pid, AB_.s)]
AB_['v_box'] = AB_.vnow.values
AB_['v_mix'] = (AB_.minnow.values * AB_.vnow.values + 500 * AB_.vprev.values) / (AB_.minnow.values + 500)
# ομαδα παικτη: κυρια ομαδα περσι (περισσοτερα λεπτα σε s−1)
TM = AR.groupby(['pid', 's', 'team']).MIN.sum().reset_index().sort_values('MIN', ascending=False).drop_duplicates(['pid', 's'])
MAINT = {(p, int(s)): t for p, s, t in zip(TM.pid, TM.s, TM.team)}
def grp(r):
    if not r.known: return 'χωρις περσινη αξια (rookie κλπ)'
    pt = MAINT.get((r.pid, r.s - 1))
    if pt is None: return 'περσινη αξια αλλα 0′ περσι'
    return 'ιδια ομαδα με περσι' if pt == r.team else 'αλλαξε ομαδα'
AB_['grp'] = [grp(r) for r in AB_.itertuples(index=False)]
GRPS = ['ιδια ομαδα με περσι', 'αλλαξε ομαδα', 'χωρις περσινη αξια (rookie κλπ)', 'περσινη αξια αλλα 0′ περσι']
BINS = [(0, 300), (300, 800), (800, 1500), (1500, 1e9)]
def blab(b): return f'{b[0]}-{b[1]}′' if b[1] < 1e8 else f'{b[0]}′+'
AB_['bin'] = [next(k for k, b in enumerate(BINS) if b[0] <= m < b[1]) for m in AB_.minnow.values]
nD = len(D); Y = D.act.values - D.m0.values; ys = D.sea.values; SE = sorted(D.sea.unique())
def netcost(v, mask=None):
    c = AB_.w.values * 0.75 * (v + 2.0) * AB_.m.values / 48 * AB_.sg.values
    if mask is not None: c = np.where(mask, c, 0.0)
    adj = np.zeros(nD); np.add.at(adj, AB_.q.values, c); return adj
def ols(y, Xs):
    X = np.c_[np.ones(len(y)), np.column_stack(Xs)]
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    s2 = e @ e / (len(y) - X.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return b[1:], se[1:]
def rmse(y): return float(np.sqrt(np.mean(y ** 2)))
VARS = [('περσινο συνθετο (LIVE)', 'vprev')] + [(f'περσινο {n} μονο (λειπει → −1)', f'v_{n}') for n in SYS] + \
       [(f'περσινο {n} μονο (λειπει → συνθετο)', f'f_{n}') for n in SYS] + [('φετινη box μονο', 'v_box'), ('μιξη M=500 (t59)', 'v_mix')]
ADJ = {k: netcost(AB_[k].values) for _, k in VARS}
base_e2 = (Y - ADJ['vprev']) ** 2
P(''); P(f'Α1. ΒΑΘΜΟΝΟΜΗΣΗ ΚΟΣΤΟΥΣ ΑΠΟΥΣΙΑΣ ΑΝΑ ΣΥΣΤΗΜΑ · ματς {nD} (σεζον 2022-2026, ανοιγμα) · εγγραφες αποντων {len(AB_)}')
P(f'   καλυψη (εγγραφες με τιμη στο συστημα για s−1): ' + ' · '.join(f'{n} {100 * AB_[f"has_{n}"].mean():.1f}%' for n in SYS) + f' · συνθετο {100 * AB_.known.mean():.1f}%')
P(f'   RMSE χωρις καθολου απουσιες (act − m0): {rmse(Y):.4f} π.')
P(f'   {"συστημα":42s} | κλιση b (±ΤΣ)    | RMSE π.  | ΔMSE vs LIVE ανα ματς (±ΤΣ) | μεσο |καθαρο κοστος| π.')
for lab_, k in VARS:
    b, se = ols(Y, [ADJ[k]]); e2 = (Y - ADJ[k]) ** 2; dd = e2 - base_e2
    P(f'   {lab_:42s} | {b[0]:.3f} (±{se[0]:.3f}) | {rmse(Y - ADJ[k]):.4f} | {dd.mean():+.4f} (±{dd.std(ddof=1) / np.sqrt(nD):.4f}) | {np.mean(np.abs(ADJ[k])):.3f}')
# κοινο υποσυνολο: ματς οπου ΟΛΟΙ οι αποντες εχουν ΟΛΑ τα συστηματα
allhas = np.ones(len(AB_), bool)
for n in SYS: allhas &= AB_[f'has_{n}'].values
bad = np.zeros(nD, bool); np.logical_or.at(bad, AB_.q.values, ~allhas); cm = ~bad
P(f'   -- κοινο υποσυνολο: ματς οπου καθε αποντας εχει και τα {len(SYS)} συστηματα (n ματς {int(cm.sum())}) --')
for lab_, k in [VARS[0]] + [(f'περσινο {n} μονο', f'v_{n}') for n in SYS] + VARS[-2:]:
    b, se = ols(Y[cm], [ADJ[k][cm]])
    P(f'   {lab_:42s} | {b[0]:.3f} (±{se[0]:.3f}) | RMSE {rmse((Y - ADJ[k])[cm]):.4f}')
# ---- Α2 ανα ζωνη φετινων λεπτων ----
def split_table(title, keycol, labels):
    P(''); P(title)
    cnt = [int((AB_[keycol].values == j).sum()) for j in range(len(labels))]
    P('   εγγραφες ανα ζωνη: ' + ' · '.join(f'{l} {c}' for l, c in zip(labels, cnt)))
    P(f'   {"συστημα":28s} | ' + ' | '.join(f'{l[:24]:>24s}' for l in labels))
    for lab_, k in [VARS[0]] + [(f'{n} (λειπει→−1)', f'v_{n}') for n in SYS] + [('φετινη box μονο', 'v_box'), ('μιξη M=500', 'v_mix')]:
        Xs = [netcost(AB_[k].values, AB_[keycol].values == j) for j in range(len(labels))]
        b, se = ols(Y, Xs)
        P(f'   {lab_[:28]:28s} | ' + ' | '.join(f'{f"b {bb:.2f} (±{ss:.2f})":>24s}' for bb, ss in zip(b, se)))
    # RMSE στα ματς που εχουν αποντα της ζωνης
    row = []
    for j in range(len(labels)):
        has = np.zeros(nD, bool); np.logical_or.at(has, AB_.q.values, AB_[keycol].values == j)
        row.append(f'n {int(has.sum())}: LIVE {rmse((Y - ADJ["vprev"])[has]):.3f} / μιξη {rmse((Y - ADJ["v_mix"])[has]):.3f}')
    P('   RMSE ματς με αποντα της ζωνης: ' + ' · '.join(f'[{l}] {r}' for l, r in zip(labels, row)))
split_table('Α2. ΚΛΙΣΗ ΑΝΑ ΦΕΤΙΝΑ ΛΕΠΤΑ ΤΟΥ ΑΠΟΝΤΑ ΩΣ ΤΗ ΜΕΡΑ (πολλαπλη OLS, ενα κοστος ανα ζωνη) · b=1 σωστο, <1 υπερεκτιμα, >1 υποεκτιμα',
            'bin', [blab(b) for b in BINS])
AB_['gi'] = [GRPS.index(x) for x in AB_.grp]
split_table('Α3. ΚΛΙΣΗ ΑΝΑ ΟΜΑΔΑ ΠΑΙΚΤΗ (κυρια περσινη ομαδα = περισσοτερα λεπτα σε s−1)', 'gi', GRPS)
P(''); P('Α4. ΚΛΙΣΗ ΑΝΑ ΣΕΖΟΝ (b ±ΤΣ · RMSE)')
for lab_, k in (VARS[0], ('φετινη box μονο', 'v_box'), ('μιξη M=500', 'v_mix')):
    cells = []
    for s in SE:
        mk = ys == s; b, se = ols(Y[mk], [ADJ[k][mk]]); cells.append(f'{s}: {b[0]:.2f} (±{se[0]:.2f}) RMSE {rmse((Y - ADJ[k])[mk]):.3f}')
    P(f'   {lab_:24s} | ' + ' | '.join(cells))
# ---- Β. σταθεροποιηση ----
P(''); P('Β. ΠΟΣΟ ΓΡΗΓΟΡΑ ΣΤΑΘΕΡΟΠΟΙΕΙΤΑΙ Η ΦΕΤΙΝΗ BOX ΑΞΙΑ · παικτες με ≥1500′ στη σεζον (σεζον 2022-2026) · κλιμακα value()')
NS_ = (100, 250, 500, 750, 1000)
recs = []
for (p, s), st in ST.items():
    if s not in FIT: continue
    dd, t0, cs, cm_, cr = st
    if cr[-1] < 1500: continue
    coef, mu = FIT[s], MU_BY[s]; dEnd = END[(p, s)]
    fe, _, _, _ = feats(p, s, dEnd, mu); vend = coef[0] + fe @ coef[1:]
    known = any((p, s - 1) in Dm for Dm in VM.values()); vp = value(p, s - 1)
    pt = MAINT.get((p, s - 1)); ct = MAINT.get((p, s))
    gname = GRPS[2] if not known else (GRPS[3] if pt is None else (GRPS[0] if pt == ct else GRPS[1]))
    for N in NS_:
        j = int(np.searchsorted(cr, N))                    # πρωτο ματς οπου τα σωρευτικα λεπτα ≥ N
        d = int(dd[j]) + 1; fn, mn, _, _ = feats(p, s, d, mu); vN = coef[0] + fn @ coef[1:]
        # υπολοιπο σεζον: ματς μετα το j (ιδια φθορα, ιδιο μαζεμα)
        fac = 2.0 ** (-(dEnd - t0) / g['HLD']); ss = (cs[-1] - cs[j]) * fac; ms = (cm_[-1] - cm_[j]) * fac
        vrest = coef[0] + ((ss + g['M0'] * mu) / (ms + g['M0']) - mu) @ coef[1:]
        recs.append(dict(p=p, s=s, N=N, mn=mn, vN=vN, vend=vend, vrest=vrest, vp=vp, known=known, grp=gname,
                         vmix=(mn * vN + 500 * vp) / (mn + 500), **{f'v_{n}': vsys(n, p, s - 1, -1.0) for n in SYS}))
B = pd.DataFrame(recs)
P(f'   παικτες-σεζον {B[B.N == 100].shape[0]} · ανα ομαδα: ' + ' · '.join(f'{gn} {int((B[B.N == 100].grp == gn).sum())}' for gn in GRPS))
def cr_(a, b):
    if np.std(a) < 1e-9 or np.std(b) < 1e-9: return '   —  '
    return f'{np.corrcoef(a, b)[0, 1]:.3f}'
def btab(Bx, target, tlab):
    P(f'   στοχος = {tlab} · κελι = συσχετιση (RMSE σε μοναδες value)')
    P(f'   {"N φετινα λεπτα":16s} | {"φετινη box ως N":22s} | {"περσινη value (LIVE)":22s} | {"μιξη M=500":22s} | ' + ' | '.join(f'{"περσινο " + n:22s}' for n in SYS))
    for N in NS_:
        x = Bx[Bx.N == N]; t = x[target].values
        cells = [f'{cr_(x[c].values, t)} ({rmse(x[c].values - t):.2f})' for c in ['vN', 'vp', 'vmix'] + [f'v_{n}' for n in SYS]]
        P(f'   {f"N={N} (n {len(x)})":16s} | ' + ' | '.join(f'{c:22s}' for c in cells))
P('Β1. ΟΛΟΙ:'); btab(B, 'vend', 'box ΤΕΛΟΥΣ σεζον (περιεχει τα ιδια N λεπτα)'); btab(B, 'vrest', 'box ΥΠΟΛΟΙΠΟΥ σεζον (μονο λεπτα ΜΕΤΑ το N, χωρις επικαλυψη)')
for gn in GRPS[:3]:
    Bx = B[B.grp == gn]
    if not len(Bx): continue
    P(f'Β2. {gn}:'); btab(Bx, 'vrest', 'box ΥΠΟΛΟΙΠΟΥ σεζον')
P('Β3. ΣΗΜΕΙΟ ΔΙΑΣΤΑΥΡΩΣΗΣ (στοχος box υπολοιπου): πρωτο N οπου corr(φετινη) > corr(περσινη)')
for gn in ['ολοι'] + GRPS[:2]:
    Bx = B if gn == 'ολοι' else B[B.grp == gn]; hit = None
    for N in NS_:
        x = Bx[Bx.N == N]
        if np.corrcoef(x.vN, x.vrest)[0, 1] > np.corrcoef(x.vp, x.vrest)[0, 1]: hit = N; break
    P(f'   {gn}: {"N=" + str(hit) if hit else "δεν ξεπερνα ως N=1000"}')
# ---- Γ. παραδειγματα ----
P(''); P('Γ. ΠΑΡΑΔΕΙΓΜΑΤΑ (τιμη καθε συστηματος σε 15/11, 15/1, 15/3 της σεζον · κλιμακα value, π./100 κατοχες)')
EX = [('αλλαξε ομαδα & επεσε', '201566', 2022), ('rookie', '1641705', 2024), ('σταθερος σταρ', '203999', 2024), ('σταθερος σταρ (2)', '201939', 2023)]
for tag, p, s in EX:
    if (p, s) not in ST: P(f'   [{tag}] {p} {s}: δεν υπαρχει box'); continue
    coef, mu = FIT[s], MU_BY[s]; dd = ST[(p, s)][0]
    fe, mnE, _, _ = feats(p, s, END[(p, s)], mu)
    sysv = ' · '.join(f'{n} {vsys(n, p, s - 1, float("nan")):+.2f}' for n in SYS)
    P(f'   [{tag}] {NM.get(p)} [pid {p}] σεζον {s} · ομαδα περσι {MAINT.get((p, s - 1))} → φετος {MAINT.get((p, s))} · περσινη value (LIVE) {value(p, s - 1):+.2f} '
      f'(επιμερους περσι, συρρικνωμενα: {sysv}) · box ΤΕΛΟΥΣ {coef[0] + fe @ coef[1:]:+.2f} ({mnE:.0f}′) · value({s}) τελικη συνθετη {value(p, s):+.2f}')
    for mm, yy in ((11, s - 1), (1, s), (3, s)):
        d = int(np.datetime64(f'{yy}-{mm:02d}-15', 'D').astype(np.int64)); fn, mn, ng, last = feats(p, s, d, mu)
        vN = coef[0] + fn @ coef[1:] if ng else float('nan'); vp = value(p, s - 1); vm = (mn * vN + 500 * vp) / (mn + 500) if ng else vp
        P(f'      15/{mm:02d}/{yy}: φετινα λεπτα {mn:5.0f}′ σε {ng:2d} ματς (τελευταιο box {np.datetime64(last, "D") if last else "—"}) · LIVE {vp:+.2f} · box {vN:+.2f} · μιξη M=500 {vm:+.2f}')
open(os.path.join(SC, 't61_value_systems_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
