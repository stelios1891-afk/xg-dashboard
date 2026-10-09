"""
core7_hype_test.py — 9/10/2026 (Στελιος «τρεξτο»): ΚΑΛΟΚΑΙΡΙΝΟ HYPE ΤΗΣ ΑΓΟΡΑΣ σε στοιχηματα (CORE7 2223-2526).
Hype ομαδας H = δυναμη αγορας αγων 1-3 (φετος) − δυναμη αγορας αγων 27-τελος (περσι), απο γραμμες χαντικαπ Pinnacle κλεισιματος
(fresh_model/matches.csv, ridge ανα λιγκα-σεζον, ιδια μεθοδος με y5_hype). Γνωστο μετα την 3η αγωνιστικη. Νεοφωτιστες: χωρις H.
Υποθεση (y5, Σεπ): αναβαθμισεις αναιρουνται 30-70% ως την 10η · υποβαθμισεις ΜΕΝΟΥΝ.
Τ1 ΤΥΦΛΟ: χαντικαπ ΚΟΝΤΡΑ στην ομαδα με το μεγαλυτερο καθαρο hype (H_ομαδας − H_αντιπαλου ≥ κατωφλι), αγων 4-14.
Τ2 ΦΙΛΤΡΟ στα δικα μας picks 6-14 (core7_early_weakness_picks.pkl): (α) κοβω picks ΥΠΕΡ ομαδας που η αγορα ΥΠΟΒΑΘΜΙΣΕ (H ≤ −κατ.)·
   (β) περιγραφικα: picks ΚΟΝΤΡΑ σε αναβαθμισμενη.
ΠΡΟ-ΔΗΛΩΣΗ: κατωφλι με LOSO απο {0.2,0.3,0.4,0.5,0.6}. Τ1 περνα αν LOSO ROI (μεσος βιβλιων) >0 σε ≥3/4 σεζον, Pinnacle >0 ΚΑΙ ≥1 αλλο >0, n≥60.
Τ2 περνα αν τα κομμενα αρνητικα σε ≥3/4 σεζον ΚΑΙ ≥2/3 βιβλια ΚΑΙ τα υπολοιπα καλυτερα απο σημερα σε ≥3/4 σεζον.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
m = pd.read_csv('fresh_model/matches.csv', dtype={'mid': str, 'season': str}); tg = pd.read_csv('fresh_model/teamgames.csv', dtype={'mid': str, 'season': str})
m = m[m.AHCh.notna()].copy(); m['S'] = -m.AHCh
md = tg[['mid', 'team', 'is_home', 'md']]
m = m.merge(md[md.is_home == 1][['mid', 'md']].rename(columns={'md': 'md_h'}), on='mid').merge(md[md.is_home == 0][['mid', 'md']].rename(columns={'md': 'md_a'}), on='mid')
nt = tg.groupby(['league', 'season']).team.nunique().rename('nt').reset_index(); m = m.merge(nt, on=['league', 'season']); m['G'] = 2 * (m.nt - 1)
def fit(df, lam=0.01):
    teams = sorted(set(df.hid) | set(df.aid)); ix = {t: i for i, t in enumerate(teams)}; X = np.zeros((len(df), len(teams) + 1)); X[:, 0] = 1
    for r, (h, a) in enumerate(zip(df.hid, df.aid)): X[r, 1 + ix[h]] = 1; X[r, 1 + ix[a]] = -1
    P = np.eye(len(teams) + 1) * lam; P[0, 0] = 0; b = np.linalg.solve(X.T @ X + P, X.T @ df.S.values); s = b[1:] - b[1:].mean()
    return dict(zip(teams, s))
EARLY, PREV = {}, {}
for (lg, se), d in m.groupby(['league', 'season']):
    G = int(d.G.iloc[0]); lo = 27 if G == 38 else 24
    e = d[d.md_h.between(1, 3) & d.md_a.between(1, 3)]; p = d[d.md_h.between(lo, G) & d.md_a.between(lo, G)]
    if len(e) >= 5: EARLY[(lg, se)] = fit(e)
    if len(p) >= 5: PREV[(lg, se)] = fit(p)
PRV = {'2223': '2122', '2324': '2223', '2425': '2324', '2526': '2425'}
H = {}
for (lg, se), st in EARLY.items():
    if se not in PRV: continue
    pv = PREV.get((lg, PRV[se]), {})
    for t, s_ in st.items(): H[(t, se)] = s_ - pv[t] if t in pv else np.nan
Hs = pd.Series(H); print(f'hype: {Hs.notna().sum()} ομαδες-σεζον (νεοφωτιστες χωρις: {Hs.isna().sum()}) · sd {Hs.std():.2f} · αναβαθμισεις ≥0.3: {(Hs >= .3).sum()} · υποβαθμισεις ≤−0.3: {(Hs <= -.3).sum()}')
# ---- βιβλια: Pinnacle (fresh_model) + Crown/Bet365 (Nowgoal μεσω core7_sos15_final) ----
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read(); src = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'hy'}
with contextlib.redirect_stdout(_Q()): exec(src, g)
NG = g['NG']
X = m[m.season.isin(list(PRV))].copy()
X['mdm'] = np.minimum(X.md_h, X.md_a)                 # αγωνιστικη (1-based)
X = X[X.mdm.between(4, 14)].copy()
X['Hh'] = [H.get((t, s_)) for t, s_ in zip(X.hid, X.season)]; X['Ha'] = [H.get((t, s_)) for t, s_ in zip(X.aid, X.season)]
X = X.dropna(subset=['Hh', 'Ha']); X['net'] = X.Hh - X.Ha; X['gd'] = X.hg - X.ag
rows = []
for r in X.itertuples():
    if abs(r.net) < 0.2: continue
    side = -1 if r.net > 0 else 1          # ΚΟΝΤΡΑ στην πιο «hyped»
    q = [('Pinnacle', (r.AHCh, r.PCAHH, r.PCAHA))] + [(bk, (NG.get((r.mid, bk)) or (None, (np.nan,) * 3))[1]) for bk in ('Crown', 'Bet365')]
    for bk, (L, oh, oa) in q:
        if not (L == L and oh == oh): continue
        hc = L if side == 1 else -L; o = oh if side == 1 else oa
        rows.append(dict(season=r.season, book=bk, mdm=r.mdm, net=abs(r.net), dog=hc > 0, hc=hc, pnl=picks.settle(r.gd, side, hc, o)))
T = pd.DataFrame(rows)
def fm(d):
    if len(d) < 6: return f'n{len(d) / 3:5.0f}' + ' ' * 34
    ps = d.groupby('season').pnl.mean(); pb = d.groupby('book').pnl.mean()
    return f'n{len(d) / d.book.nunique():5.0f} {100 * d.pnl.mean():+6.1f}% {d.pnl.sum() / d.book.nunique():+6.1f}u σεζ {int((ps > 0).sum())}/{ps.size} βιβλ {int((pb > 0).sum())}/{pb.size}'
print('\nΤ1 ΤΥΦΛΟ κοντρα στην πιο «hyped» ομαδα (χαντικαπ κλεισιματος· ROI μεσος βιβλιων)')
for thr in (0.2, 0.3, 0.4, 0.5, 0.6):
    x = T[T.net >= thr]
    print(f'   καθαρο hype ≥{thr}: {fm(x)} · αγων 4-6 {fm(x[x.mdm <= 6])[:22]} · 7-10 {fm(x[x.mdm.between(7, 10)])[:22]} · 11-14 {fm(x[x.mdm >= 11])[:22]}')
x = T[T.net >= 0.3]
print(f'   (≥0.3) ως αουτσαιντερ {fm(x[x.dog])} · ως φαβορι/ισο {fm(x[~x.dog])}')
res = []
for te in sorted(T.season.unique()):
    tr = T[T.season != te]; best = max((0.2, 0.3, 0.4, 0.5, 0.6), key=lambda t: tr[tr.net >= t].pnl.sum())
    k = T[(T.season == te) & (T.net >= best)]; res.append(k); print(f'   LOSO εκτος {te}: κατωφλι {best} → {fm(k)}')
R = pd.concat(res); ps = R.groupby('season').pnl.mean(); pb = R.groupby('book').pnl.mean()
c = (ps > 0).sum() >= 3 and pb.get('Pinnacle', -1) > 0 and ((pb.drop('Pinnacle', errors='ignore') > 0).sum() >= 1) and len(R) / 3 >= 60
print(f'   LOSO συνολο {fm(R)} → Τ1 {"ΠΕΡΝΑ" if c else "ΔΕΝ ΠΕΡΝΑ"}')
# ---- Τ2: δικα μας picks ----
B = pd.read_pickle('core7_early_weakness_picks.pkl'); B = B[B.md.between(5, 13)].copy()
B['H_team'] = [H.get((t, s_)) for t, s_ in zip(B.team, B.season)]; B['H_opp'] = [H.get((t, s_)) for t, s_ in zip(B.opp, B.season)]
print(f'\nΤ2 ΔΙΚΑ ΜΑΣ picks αγων 6-14 (dogs + κοντα φαβορι): ολα {fm(B)}')
for role in ('dog', 'fav'):
    y = B[B.role == role]
    print(f'   [{role}] ολα {fm(y)}')
    for lab, c_ in (('ΥΠΕΡ υποβαθμισμενης (H ≤ −0.3)', y.H_team <= -.3), ('ΥΠΕΡ αναβαθμισμενης (H ≥ 0.3)', y.H_team >= .3),
                    ('ΚΟΝΤΡΑ σε αναβαθμισμενη (H αντ. ≥ 0.3)', y.H_opp >= .3), ('ΚΟΝΤΡΑ σε υποβαθμισμενη (H αντ. ≤ −0.3)', y.H_opp <= -.3),
                    ('καμια απο τις 2 με |H|≥0.3', (y.H_team.abs() < .3) & (y.H_opp.abs() < .3)), ('νεοφωτιστη εμπλεκεται', y.H_team.isna() | y.H_opp.isna())):
        print(f'      {lab:40s} {fm(y[c_])}')
res = []; ok = []
for te in sorted(B.season.unique()):
    tr = B[B.season != te]; best = max((0.2, 0.3, 0.4, 0.5, 0.6), key=lambda t: tr[~(tr.H_team <= -t)].pnl.sum())
    te_ = B[B.season == te]; cut = te_[te_.H_team <= -best]; keep = te_[~(te_.H_team <= -best)]
    res.append((te, best, cut, keep, te_)); print(f'   LOSO εκτος {te}: κοβω ΥΠΕΡ υποβαθμισμενης H ≤ −{best} → κομμενα {fm(cut)} · μενουν {fm(keep)} · σημερα {fm(te_)}')
CUT = pd.concat([r_[2] for r_ in res]); KEEP = pd.concat([r_[3] for r_ in res])
pc = CUT.groupby('season').pnl.mean(); pbk = CUT.groupby('book').pnl.mean()
better = sum(r_[3].pnl.mean() > r_[4].pnl.mean() for r_ in res if len(r_[3]))
c1 = (pc < 0).sum() >= 3; c2 = (pbk < 0).sum() >= 2; c3 = better >= 3
print(f'   ΣΥΝΟΛΟ κομμενα {fm(CUT)} · μενουν {fm(KEEP)} · σημερα {fm(B)}')
print(f'   ΚΡΙΣΗ Τ2: κομμενα αρνητικα σεζον {int((pc < 0).sum())}/{pc.size} {"✓" if c1 else "✗"} · βιβλια {int((pbk < 0).sum())}/3 {"✓" if c2 else "✗"} · υπολοιπα καλυτερα {better}/4 {"✓" if c3 else "✗"} → {"ΠΕΡΝΑ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑ"}')
# ---- πληροφοριακα: πραγματικο − αγορα ανα hype (επαναληψη y5 σε αποτελεσματα, οχι αναθεωρηση γραμμων) ----
print('\nΠΛΗΡΟΦΟΡΙΑΚΑ — πραγματικη διαφορα γκολ − γραμμη, σκοπια ομαδας, ανα hype (αγων 4-14, ολα τα ματς)')
Z = []
for r in X.itertuples():
    Z.append(dict(H=r.Hh, res=r.gd + r.AHCh, season=r.season, mdm=r.mdm)); Z.append(dict(H=r.Ha, res=-(r.gd + r.AHCh), season=r.season, mdm=r.mdm))
Z = pd.DataFrame(Z)
for lab, c_ in (('H ≤ −0.4', Z.H <= -.4), ('−0.4…−0.15', Z.H.between(-.4, -.15)), ('±0.15', Z.H.abs() < .15), ('0.15…0.4', Z.H.between(.15, .4)), ('H ≥ 0.4', Z.H >= .4)):
    z = Z[c_]; ps = z.groupby('season').res.mean()
    print(f'   {lab:12s} n{len(z):5d} · γκολ − γραμμη {z.res.mean():+.3f} ±{z.res.std() / np.sqrt(len(z)):.3f} (σεζον >0 {int((ps > 0).sum())}/{ps.size}) · αγων 4-10 {z[z.mdm <= 10].res.mean():+.3f} · 11-14 {z[z.mdm >= 11].res.mean():+.3f}')
