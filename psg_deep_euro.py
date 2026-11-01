# -*- coding: utf-8 -*-
"""psg_deep_euro.py — 19/10/2026 (Στελιος: «γιατι το ευρωπαικο μοντελο υποτιμα την Παρι στην Ευρωπη;»). Πανω στο psg_deep_rows.pkl (psg_deep_build.py).
Ε1 επιθεση/αμυνα · Ε2 φασεις (xG, ΜΟΝΟ κανονικη διαρκεια) vs φινιρισμα · Ε3 υπολοιπες γαλλικες + ολες οι λιγκες · Ε5 ανα τυπο ματς + γενικη «συμπιεση»
Ε6 αγορα (κλεισιμο Crown/SBOBET) · Ε7 επιμονη/τυχη (split-half, σεζον→σεζον, πολλαπλες συγκρισεις, shrinkage)."""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
D = pd.read_pickle('psg_deep_rows.pkl')
D['rx_f'] = D.xf - D.mf; D['rx_a'] = D.ma - D.xa                     # + = καλυτερα απο μοντελο (φασεις)
D['fn_f'] = D.gf - D.xf; D['fn_a'] = D.xa - D.ga                     # + = φινιρισμα / τερματοφυλακας
D['rx'] = D.rx_f + D.rx_a; D['fn'] = D.fn_f + D.fn_a
D['rk'] = D.gd - D.kgd; D['km'] = D.kgd - D.mgd                      # πραγμ − αγορα · αγορα − μοντελο
PSG = 'Paris Saint-Germain'; P = D[D.team == PSG]; O = D[D.team != PSG]
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return (v.mean(), v.std(ddof=1) / np.sqrt(len(v)), len(v)) if len(v) > 1 else (np.nan, np.nan, len(v))
def f(v): m, s, n = ms(v); return f'{m:+.2f}±{s:.2f}'
print('=' * 120 + '\nΕ1+Ε2. ΠΑΡΙ 2022-26 — ΠΟΥ ΕΙΝΑΙ ΤΟ +0.80; (± = 1 τυπικο σφαλμα · xG μονο 90λ, χωρις παραταση/πεναλτι διαδικασιας)')
print(f'   {"":10s} {"n":>3s} │ {"ΣΥΝΟΛΟ":>11s} │ {"ΕΠΙΘΕΣΗ γκολ−μοντ":>17s} = {"φασεις xG−μοντ":>14s} + {"φινιρ. γκολ−xG":>14s} │ {"ΑΜΥΝΑ μοντ−γκολ":>15s} = {"φασεις μοντ−xG":>14s} + {"τερμ. xG−γκολ":>13s}')
def dec(lab, y):
    print(f'   {lab:10s} {len(y):3d} │ {f(y.rd):>11s} │ {f(y.gf - y.mf):>17s} = {f(y.rx_f):>14s} + {f(y.fn_f):>14s} │ {f(y.ma - y.ga):>15s} = {f(y.rx_a):>14s} + {f(y.fn_a):>13s}')
dec('ΟΛΑ', P)
for s, y in P.groupby('sea'): dec(f'σεζον {s}', y)
dec('χωρις ET', P[~P.et])
xo = P.xf_old - P.mf
print(f'   (με το παλιο XG που μετρουσε παραταση+πεναλτι: φασεις επιθεσης {f(xo)} — {int(P.et.sum())} ματς Παρι με παραταση)')
print(f'   Μεσοι ορ.: γκολ {P.gf.mean():.2f}-{P.ga.mean():.2f} · xG {P.xf.mean():.2f}-{P.xa.mean():.2f} · μοντελο {P.mf.mean():.2f}-{P.ma.mean():.2f} · αγορα (διαφορα) {P.kgd.mean():+.2f}')
print(f'   ΑΝΑΦΟΡΑ ολες οι αλλες ομαδες ({len(O)}): ΣΥΝΟΛΟ {f(O.rd)} · φασεις {f(O.rx)} · φινιρισμα {f(O.fn)}')

print('\n' + '=' * 120 + '\nΕ3. ΓΑΛΛΙΚΗ ΜΕΤΑΦΡΑΣΗ — αλλες ομαδες Ligue 1 στην Ευρωπη (ολες οι διοργανωσεις)')
F = D[(D.lg == 'Ligue1') & (D.team != PSG)]
print(f'   ΟΛΕΣ μαζι {len(F)} · ΣΥΝΟΛΟ {f(F.rd)} · φασεις {f(F.rx)} · φινιρισμα {f(F.fn)} · πραγμ−αγορα {f(F.rk)}')
for c, y in F.groupby('comp'): print(f'     {c:18s} {len(y):3d} · ΣΥΝΟΛΟ {f(y.rd)} · φασεις {f(y.rx)}')
for t, y in sorted(F.groupby('team'), key=lambda z: -len(z[1])):
    if len(y) >= 6: print(f'     {t:22s} {len(y):3d} · ΣΥΝΟΛΟ {f(y.rd)} · φασεις {f(y.rx)} · φινιρ {f(y.fn)}')
print('   ΑΝΑ ΛΙΓΚΑ (ολες οι ομαδες, ≥60 γραμμες) — ΧΩΡΙΣ την Παρι:')
L = O.groupby('lg').filter(lambda z: len(z) >= 60)
for lg, y in sorted(L.groupby('lg'), key=lambda z: -z[1].rd.mean()):
    print(f'     {lg:22s} {len(y):4d} · ΣΥΝΟΛΟ {f(y.rd)} · φασεις {f(y.rx)}')
print('   Μεγαλοι κάθε λιγκας top-5 (UCL, ≥15) για συγκριση:')
U = D[D.lg.isin(TOP5)]
tm = U.groupby('team').agg(n=('rd', 'size'), rd=('rd', 'mean'), rx=('rx', 'mean'), fn=('fn', 'mean'), mg=('mgd', 'mean'), rk=('rk', 'mean'))
for t, r in tm[tm.n >= 25].sort_values('rd', ascending=False).iterrows():
    print(f'     {t:22s} {int(r.n):3d} · ΣΥΝΟΛΟ {r.rd:+.2f} · φασεις {r.rx:+.2f} · φινιρ {r.fn:+.2f} · πραγμ−αγορα {r.rk:+.2f} · μοντ. διαφορα {r.mg:+.2f}')

print('\n' + '=' * 120 + '\nΕ5. ΠΑΡΙ ΑΝΑ ΤΥΠΟ ΜΑΤΣ (ΣΥΝΟΛΟ πραγμ−μοντ · φασεις · πραγμ−αγορα)')
P = P.assign(opp5=P.olg.isin(TOP5), role=np.where(P.mgd > .5, 'φαβ >0.5', np.where(P.mgd < -.25, 'αουτσ <−0.25', 'κοντα')))
for lab, col in (('εδρα', 'home'), ('φαση', 'phase'), ('αντιπαλος top-5', 'opp5'), ('ρολος (μοντελο)', 'role')):
    for k, y in P.groupby(col): print(f'   {lab:16s} {str(k):14s} {len(y):3d} · ΣΥΝΟΛΟ {f(y.rd)} · φασεις {f(y.rx)} · φινιρ {f(y.fn)} · πραγμ−αγορα {f(y.rk)}')
print('\n   ΓΕΝΙΚΟΣ ΜΗΧΑΝΙΣΜΟΣ «συμπιεση»: ολες οι ομαδες ΧΩΡΙΣ Παρι — πραγμ−μοντ ανα διαφορα που λεει το μοντελο')
bins = [-9, -1, -.5, 0, .5, 1, 1.5, 9]
O = O.assign(b=pd.cut(O.mgd, bins))
for b, y in O.groupby('b', observed=True): print(f'     μοντελο {str(b):13s} {len(y):4d} · ΣΥΝΟΛΟ {f(y.rd)} · πραγμ−αγορα {f(y.rk)} · Παρι εδω: {(pd.cut(P.mgd, bins) == b).sum()}')
c1 = np.polyfit(O.mgd, O.rd, 1); exp_p = np.polyval(c1, P.mgd).mean()
print(f'     ευθεια (ολες εκτος Παρι): πραγμ−μοντ = {c1[1]:+.3f} + {c1[0]:+.3f}×μοντ.διαφορα → «αναμενομενο» για τα ματς της Παρι {exp_p:+.2f} · Παρι μετα {P.rd.mean() - exp_p:+.2f}')
# top-5 ομαδες με ισχυ: «ελιτ» = μεση μοντ. διαφορα ομαδας ≥ +0.5 (≥15 ματς)
st = D.groupby('team').agg(n=('rd', 'size'), mg=('mgd', 'mean'), rd=('rd', 'mean'), lg=('lg', 'first'))
el = st[(st.n >= 15) & (st.mg >= .5)].drop(PSG, errors='ignore')
E = D[D.team.isin(el.index)]
print(f'     «ΕΛΙΤ» ομαδες (μεση μοντ. διαφορα ≥+0.5, ≥15 ματς, χωρις Παρι: {len(el)} ομαδες, {len(E)} ματς): ΣΥΝΟΛΟ {f(E.rd)} · φασεις {f(E.rx)} · πραγμ−αγορα {f(E.rk)}')
print('       ' + ' · '.join(f'{t} {r.rd:+.2f}' for t, r in el.sort_values('rd', ascending=False).iterrows()))
print(f'     ΔΙΑΡΚΕΙΑ: κατω απο ολο το δειγμα ΣΥΝΟΛΟ {f(D.rd)} (μηδεν εξ ορισμου, ελεγχος)')

print('\n' + '=' * 120 + '\nΕ6. ΑΓΟΡΑ — ειδε η αγορα την Παρι; (κλεισιμο, μεσος Crown/SBOBET· «αγορα» = διαφορα γκολ που δικαιολογει το χαντικαπ)')
print(f'   {"σεζον":8s} {"n":>3s} │ {"πραγμ":>6s} {"μοντ":>6s} {"αγορα":>6s} │ {"πραγμ−μοντ":>11s} {"πραγμ−αγορα":>12s} {"αγορα−μοντ":>11s} │ ROI χαντικαπ Παρι (κλεισιμο, τυφλα)')
for s, y in list(P.groupby('sea')) + [('ΟΛΑ', P)]:
    m, se, n = ms(y.pnl)
    print(f'   {s:8s} {len(y):3d} │ {y.gd.mean():+6.2f} {y.mgd.mean():+6.2f} {y.kgd.mean():+6.2f} │ {f(y.rd):>11s} {f(y.rk):>12s} {f(y.km):>11s} │ {100 * m:+6.1f}% ±{100 * se:.0f} ({(y.pnl > 0).sum()}-{(y.pnl < 0).sum()})')
print(f'   σφαλμα (RMSE) διαφορας: μοντελο {np.sqrt((P.rd ** 2).mean()):.2f} · αγορα {np.sqrt((P.rk ** 2).mean()):.2f} · ολες οι ομαδες: μοντελο {np.sqrt((D.rd ** 2).mean()):.2f} · αγορα {np.sqrt((D.rk ** 2).mean()):.2f}')
for t in ('Real Madrid', 'Borussia Dortmund', 'FC Porto', 'Manchester City', 'Bayern München', 'Inter', 'Barcelona', 'Arsenal'):
    y = D[D.team == t]
    if len(y) >= 15: print(f'     {t:20s} {len(y):3d} · πραγμ−μοντ {f(y.rd)} · πραγμ−αγορα {f(y.rk)} · αγορα−μοντ {f(y.km)} · ROI {100 * y.pnl.mean():+.1f}%')

print('\n' + '=' * 120 + '\nΕ7. ΕΠΙΜΟΝΗ ή ΤΥΧΗ; (ανα ομαδα-σεζον)')
D = D.sort_values(['team', 'sea', 'date'])
def persist(col, nmin=8):
    a = []; b = []
    for (t, s), y in D.groupby(['team', 'sea']):
        v = y[col].dropna().values
        if len(v) >= nmin: a.append(v[0::2].mean()); b.append(v[1::2].mean())
    r = np.corrcoef(a, b)[0, 1]; return r, len(a)
def s2s(col, nmin=6):
    T = D.groupby(['team', 'sea'])[col].agg(['mean', 'size']).reset_index(); T = T[T['size'] >= nmin]
    S = sorted(D.sea.unique()); a = []; b = []
    for k in range(len(S) - 1):
        x = T[T.sea == S[k]].set_index('team')['mean']; z = T[T.sea == S[k + 1]].set_index('team')['mean']; c = x.index.intersection(z.index)
        a += list(x[c]); b += list(z[c])
    return np.corrcoef(a, b)[0, 1], len(a)
print(f'   {"μετρο":28s} │ split-half μεσα στη σεζον (ζυγα/μονα ματς, ≥8) │ σεζον→επομενη σεζον (≥6 και στις 2)')
for lab, col in (('πραγμ−μοντελο (ΣΥΝΟΛΟ)', 'rd'), ('  φασεις xG−μοντελο', 'rx'), ('  φινιρισμα γκολ−xG', 'fn'), ('πραγμ−αγορα', 'rk'), ('αγορα−μοντελο', 'km')):
    r1, n1 = persist(col); r2, n2 = s2s(col)
    print(f'   {lab:28s} │ r = {r1:+.2f} (n={n1}, ±{1 / np.sqrt(n1):.2f})                     │ r = {r2:+.2f} (n={n2}, ±{1 / np.sqrt(n2):.2f})')
for lab, col in (('ΣΥΝΟΛΟ πραγμ−μοντ', 'rd'), ('πραγμ−αγορα', 'rk'), ('αγορα−μοντ', 'km')):
    T = D.groupby('team')[col].agg(['mean', 'std', 'size']); T = T[T['size'] >= 15]; T['se'] = T['std'] / np.sqrt(T['size']); T['z'] = T['mean'] / T['se']
    vt = max(T['mean'].var() - (T.se ** 2).mean(), 0); p = T.loc[PSG]
    shr = p['mean'] * vt / (vt + p.se ** 2) if vt > 0 else 0.0
    rank = int((T.z >= p.z).sum())
    print(f'   [{lab}] ομαδες ≥15 ματς: {len(T)} · διασπορα ομαδων {T["mean"].std():.2f} vs αναμενομενη απο τυχη {np.sqrt((T.se ** 2).mean()):.2f} → «αληθινη» SD {np.sqrt(vt):.2f}')
    print(f'      Παρι {p["mean"]:+.2f} ±{p.se:.2f} (z {p.z:+.1f}, {rank}η απο {len(T)}) · μετα συρρικνωση (empirical Bayes) {shr:+.2f} · '
          f'Bonferroni p ≈ {min(1, len(T) * math.erfc(abs(p.z) / math.sqrt(2))):.2f} (απλο p {math.erfc(abs(p.z) / math.sqrt(2)):.3f})')
SS = D.groupby(['team', 'sea']).rd.agg(['mean', 'size']).reset_index(); SS = SS[SS['size'] >= 4]
k4 = SS.groupby('team').filter(lambda z: len(z) == 4).groupby('team')['mean'].apply(lambda v: (v > 0).sum())
print(f'   4/4 σεζον θετικες (ομαδες με ≥4 ματς σε ολες τις 4 σεζον): {len(k4)} ομαδες · αναμενομενες απο τυχη {len(k4) / 16:.1f} · παρατηρηθηκαν '
      f'{int((k4 == 4).sum())} ({", ".join(k4[k4 == 4].index)}) · 0/4: {int((k4 == 0).sum())} ({", ".join(k4[k4 == 0].index)})')

print('\n' + '=' * 120 + '\nΕ8. ΓΕΝΙΚΟΣ ΜΗΧΑΝΙΣΜΟΣ «η αγορα ξερει κατι για την ομαδα» — προβλεπει το (αγορα−μοντελο) την αποκλιση πραγμ−μοντελο;')
b = np.polyfit(D.km, D.rd, 1)
print(f'   ανα ματς (ολες, {len(D)}): πραγμ−μοντ = {b[1]:+.3f} + {b[0]:.2f}×(αγορα−μοντ)  [1.00 = η αγορα εχει δικιο ολο, 0 = θορυβος]')
T = D.groupby(['team', 'sea']).agg(km=('km', 'mean'), rd=('rd', 'mean'), n=('rd', 'size')).reset_index()
S = sorted(D.sea.unique()); a = []; z = []; ww = []; tt = []
for k in range(1, len(S)):
    pr = T[(T.sea == S[k - 1]) & (T.n >= 6)].set_index('team'); cu = T[(T.sea == S[k]) & (T.n >= 6)].set_index('team'); c = pr.index.intersection(cu.index)
    a += list(pr.km[c]); z += list(cu.rd[c]); ww += list(cu.n[c]); tt += [(t, S[k]) for t in c]
a = np.array(a); z = np.array(z); ww = np.array(ww)
bb = np.polyfit(a, z, 1, w=np.sqrt(ww)); r = np.corrcoef(a, z)[0, 1]
print(f'   ΠΕΡΣΙΝΟ (αγορα−μοντ) ομαδας → ΦΕΤΙΝΟ πραγμ−μοντ: r = {r:+.2f} (n={len(a)} ομαδα-σεζον, ±{1 / np.sqrt(len(a)):.2f}) · κλιση {bb[0]:.2f}')
cur = T[T.n >= 6]; r0 = np.corrcoef(cur.km, cur.rd)[0, 1]
print(f'   ΙΔΙΑΣ σεζον (αγορα−μοντ) → πραγμ−μοντ: r = {r0:+.2f} (n={len(cur)}) · κλιση {np.polyfit(cur.km, cur.rd, 1, w=np.sqrt(cur.n))[0]:.2f}')
pp = [(t, s, x, y) for (t, s), x, y in zip(tt, a, z) if t == PSG]
print('   Παρι: ' + ' · '.join(f'{s}: περσι αγορα−μοντ {x:+.2f} → φετος πραγμ−μοντ {y:+.2f}' for t, s, x, y in pp))
