"""nonfm_transfer_test.py — 12/10/2026 (Στελιος: «τις ομαδες χωρις FotMob, με οποιον κι αν παιζουν, πως τις προσεγγιζουμε σε σχεση με αγορα και
πραγματικοτητα; αν βγαλουμε συμπερασμα απο αυτες, ισχυει το ιδιο οταν παιζουν μεταξυ τους; το Γ vs Γ στο UCL ειναι πολυ μικρο δειγμα»).
ΜΕΤΑΦΕΡΕΤΑΙ το λαθος μας στις ομαδες χωρις FotMob απο τα ματς vs FotMob (Β) στα ματς μεταξυ τους (Γ); UCL+UEL+UECL, 4 σεζον.
  Α) ΟΜΑΔΙΚΑ: ολες οι εμφανισεις ομαδων χωρις FotMob (με οποιον κι αν παιζουν), ανα διοργανωση και ανα τυπο αντιπαλου
  Β) ΑΝΑ ΟΜΑΔΑ: το λαθος μιας ομαδας στα Β (επιθεση/αμυνα) προβλεπει το λαθος της στα Γ; (συσχετιση + διορθωση μονο με ΠΡΟΗΓΟΥΜΕΝΑ Β ματς)
  λαθος = πραγματικο − μοντελο, σε ΓΚΟΛ και σε xG (το xG εχει λιγοτερη τυχη). Διαγνωστικο — τιποτα live.
"""
import sys, io, contextlib
sys.stdout.reconfigure(encoding='utf-8')
_src = open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0]
exec(_src)
KOt = u['KO']
S['ko'] = [KOt.get(MIDS[i], 0) for i in S.i]
S['res_g'] = S.g - S.lam; S['res_x'] = S.xg - S.lam; S['res_k'] = S.g - S.k
O = opp(S).reset_index(drop=True)
S = S.reset_index(drop=True)
S['dres_g'] = O.g.values - O.lam.values; S['dres_x'] = O.xg.values - O.lam.values; S['dres_k'] = O.g.values - O.k.values
S['o_g'], S['o_lam'], S['o_xg'], S['o_k'] = O.g.values, O.lam.values, O.xg.values, O.k.values
NF = S[S.src != 'FotMob'].copy(); NF['vs'] = np.where(NF.osrc == 'FotMob', 'vs ΜΕ FotMob', 'vs ΧΩΡΙΣ FotMob')
def line(x, lab):
    if len(x) < 8: return f'   {lab:30s} n{len(x):3d} (λιγα)'
    f = lambda c: f'{x[c].mean():+.2f}±{se(x[c]):.2f}'
    return (f'   {lab:30s} n{len(x):3d} · ΒΑΖΕΙ: γκολ−μοντ {f("res_g")} · xG−μοντ {f("res_x")} · γκολ−αγορα {x.res_k.mean():+.2f} '
            f'| ΤΡΩΕΙ: γκολ−μοντ {f("dres_g")} · xG−μοντ {f("dres_x")} · γκολ−αγορα {x.dres_k.mean():+.2f}')
print('Α) ΟΜΑΔΕΣ ΧΩΡΙΣ FotMob, ΟΛΕΣ ΟΙ ΕΜΦΑΝΙΣΕΙΣ (+ = βαζει/τρωει περισσοτερα απ οσα λεμε)')
print(line(NF, 'ΟΛΑ'))
for cm in ('UCL', 'UEL', 'UECL'):
    x = NF[NF.comp == cm]; print(line(x, f'{cm} ολα'))
    for v in ('vs ΜΕ FotMob', 'vs ΧΩΡΙΣ FotMob'): print(line(x[x.vs == v], f'   {cm} {v}'))
for s_ in ('Ben', 'γκολ+Elo'):
    for v in ('vs ΜΕ FotMob', 'vs ΧΩΡΙΣ FotMob'): print(line(NF[(NF.src == s_) & (NF.vs == v)], f'{s_} {v}'))
print('   (συγκριση: ομαδες ΜΕ FotMob vs ΜΕ FotMob)'); print(line(S[(S.src == 'FotMob') & (S.osrc == 'FotMob')], 'FotMob vs FotMob'))
print('   (και: ομαδες ΜΕ FotMob οταν παιζουν vs ΧΩΡΙΣ FotMob)'); print(line(S[(S.src == 'FotMob') & (S.osrc != 'FotMob')], 'FotMob vs ΧΩΡΙΣ'))
# ===== Β =====
print('\nΒ) ΑΝΑ ΟΜΑΔΑ — το λαθος της ομαδας στα ματς vs FotMob ΠΡΟΒΛΕΠΕΙ το λαθος της στα ματς vs ομαδες χωρις FotMob;')
B = NF[NF.vs == 'vs ΜΕ FotMob']; G = NF[NF.vs == 'vs ΧΩΡΙΣ FotMob']
tb = B.groupby('team').agg(nb=('i', 'size'), ab_g=('res_g', 'mean'), ab_x=('res_x', 'mean'), db_g=('dres_g', 'mean'), db_x=('dres_x', 'mean'))
tg = G.groupby('team').agg(ng=('i', 'size'), ag_g=('res_g', 'mean'), ag_x=('res_x', 'mean'), dg_g=('dres_g', 'mean'), dg_x=('dres_x', 'mean'))
T = tb.join(tg, how='inner'); T = T[(T.nb >= 4) & (T.ng >= 2)]
def wcorr(a, b, w):
    a, b, w = map(np.asarray, (a, b, w)); ma, mb = np.average(a, weights=w), np.average(b, weights=w)
    return np.average((a - ma) * (b - mb), weights=w) / np.sqrt(np.average((a - ma) ** 2, weights=w) * np.average((b - mb) ** 2, weights=w))
w = np.minimum(T.nb, T.ng)
print(f'   ομαδες με ≥4 ματς vs FotMob ΚΑΙ ≥2 vs χωρις: {len(T)} (ματς Γ που καλυπτουν: {int(T.ng.sum())})')
for lab, a, b in (('ΕΠΙΘΕΣΗ, γκολ', 'ab_g', 'ag_g'), ('ΕΠΙΘΕΣΗ, xG', 'ab_x', 'ag_x'), ('ΑΜΥΝΑ, γκολ', 'db_g', 'dg_g'), ('ΑΜΥΝΑ, xG', 'db_x', 'dg_x')):
    print(f'   συσχετιση λαθους ({lab}): {wcorr(T[a], T[b], w):+.2f}')
# διορθωση με μονο ΠΡΟΗΓΟΥΜΕΝΑ ματς vs FotMob (συρρικνωση n/(n+K))
K = 8
def prior(team, ko, col):
    x = B[(B.team == team) & (B.ko < ko)][col]
    return x.sum() / (len(x) + K) if len(x) else 0.0, len(x)
rows = []
for r in G.itertuples():
    oteam = S.loc[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')], 'team']
    pa, na = prior(r.team, r.ko, 'res_g'); pd_, nd = prior(oteam, r.ko, 'dres_g')
    pax, _ = prior(r.team, r.ko, 'res_x'); pdx, _ = prior(oteam, r.ko, 'dres_x')
    rows.append(dict(g=r.g, xg=r.xg, lam=r.lam, k=r.k, c_g=r.lam + pa + pd_, c_x=r.lam + pax + pdx, n=na + nd, comp=r.comp))
R = pd.DataFrame(rows)
print(f'\n   ΔΟΚΙΜΗ: στα ματς Γ, γκολ καθε πλευρας = μοντελο + (λαθος επιθεσης της ομαδας + λαθος αμυνας του αντιπαλου στα ΠΡΟΗΓΟΥΜΕΝΑ ματς τους vs FotMob, ×n/(n+{K}))')
print(f'   πλευρες Γ: {len(R)} · με τουλαχιστον 1 προηγουμενο ματς: {(R.n > 0).sum()}')
for lab, m in (('ολες', R.n >= 0), ('με ιστορικο ≥4 ματς', R.n >= 4)):
    x = R[m & R.k.notna()]
    mse = lambda p, y: ((x[y] - x[p]) ** 2).mean()
    print(f'   {lab:22s} n{len(x):3d} · μεσο τετρ. λαθος ΓΚΟΛ: μοντελο {mse("lam", "g"):.3f} · διορθ. με γκολ {mse("c_g", "g"):.3f} · διορθ. με xG {mse("c_x", "g"):.3f} · αγορα {mse("k", "g"):.3f}'
          f' | ως προς xG: μοντελο {mse("lam", "xg"):.3f} · διορθ. {mse("c_x", "xg"):.3f}')
