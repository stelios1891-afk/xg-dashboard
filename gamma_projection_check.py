"""gamma_projection_check.py — 12/10/2026 (Στελιος: «το ερωτημα ειναι αν ειναι σωστα ή οχι τα projections μας στα ματς Γ»).
ΕΙΝΑΙ ΣΩΣΤΑ ΤΑ PROJECTIONS ΣΤΑ ΜΑΤΣ Γ (κανεις FotMob); UCL+UEL+UECL 4 σεζον (UCL Γ μονο 3 → κυριως UEL/UECL), συγκριση με Α και Β.
  1) ΦΑΒΟΡΙ / ΑΟΥΤΣΑΙΝΤΕΡ (του μοντελου): γκολ / xG / αγορα ως ποσοστο του μοντελου (100% = σωστο)
  2) ΠΛΗΡΟΦΟΡΙΑ: πραγματικο = αγορα + b·(μοντελο − αγορα)· b>0 = το μοντελο ξερει κατι που η αγορα δεν ξερει (b=1: σωστο το μοντελο, b=0: σωστη η αγορα)
  3) ΑΚΡΙΒΕΙΑ: μεσο τετρ. λαθος μοντελο vs αγορα (διαφορα & συνολο)
  4) τι θα γινοταν με το ×1.16 φαβορι του UCL στα Γ
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
M = []
for i, x in S.groupby('i'):
    h = x[x.venue == 'εντος'].iloc[0]; a = x[x.venue == 'εκτος'].iloc[0]
    f, d = (h, a) if h.lam >= a.lam else (a, h)
    M.append(dict(i=i, comp=h.comp, cat=h['cat'], sea=h.sea, fg=f.g, fl=f.lam, fx=f.xg, fk=f.k, dg=d.g, dl=d.lam, dx=d.xg, dk=d.k,
                  m=f.lam - d.lam, km=f.k - d.k, y=f.g - d.g, yx=f.xg - d.xg, Tm=h.lou + a.lou, kT=h.k + a.k, tg=h.g + a.g))
M = pd.DataFrame(M); M = M[M.fk.notna() & M.dk.notna()]
def pct(a, b): return f'{100 * a.sum() / b.sum():4.0f}%'
def ols(y, x0, x1):
    X = np.column_stack([np.ones(len(y)), x0, x1]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / max(len(y) - 3, 1)); return b[2], b[2] / np.sqrt(cov[2, 2])
GROUPS = [('Γ ολα', M.cat == 'Γ'), ('Γ Europa', (M.cat == 'Γ') & (M.comp == 'UEL')), ('Γ Conference', (M.cat == 'Γ') & (M.comp == 'UECL')),
          ('Β ολα', M.cat == 'Β'), ('Α ολα', M.cat == 'Α'), ('Β UCL', (M.cat == 'Β') & (M.comp == 'UCL')), ('Α UCL', (M.cat == 'Α') & (M.comp == 'UCL'))]
print('1. ΦΑΒΟΡΙ / ΑΟΥΤΣΑΙΝΤΕΡ ΤΟΥ ΜΟΝΤΕΛΟΥ — ως ποσοστο της προβλεψης μας (100% = σωστο, >100% = τα υποτιμαμε)')
for lab, m in GROUPS:
    x = M[m]
    print(f'   {lab:14s} n{len(x):4d} · ΦΑΒΟΡΙ γκολ {pct(x.fg, x.fl)} xG {pct(x.fx, x.fl)} αγορα {pct(x.fk, x.fl)} · '
          f'ΑΟΥΤΣ. γκολ {pct(x.dg, x.dl)} xG {pct(x.dx, x.dl)} αγορα {pct(x.dk, x.dl)} · '
          f'ΔΙΑΦΟΡΑ πραγμ {x.y.mean():+.2f} xG {x.yx.mean():+.2f} μοντ {x.m.mean():+.2f} αγορα {x.km.mean():+.2f}')
print('\n2. ΠΛΗΡΟΦΟΡΙΑ ΠΕΡΑ ΑΠΟ ΤΗΝ ΑΓΟΡΑ (κλεισιμο): b (t) · b≈1 σωστο μοντελο, b≈0 η αγορα τα ξερει ολα, b<0 το μοντελο χαλαει')
for lab, m in GROUPS:
    x = M[m]
    b1, t1 = ols(x.y.values, x.km.values, (x.m - x.km).values); b2, t2 = ols(x.tg.values, x.kT.values, (x.Tm - x.kT).values)
    b3, t3 = ols(x.yx.values, x.km.values, (x.m - x.km).values)
    print(f'   {lab:14s} n{len(x):4d} · ΔΙΑΦΟΡΑ γκολ b {b1:+.2f} (t {t1:+.1f}) · ΔΙΑΦΟΡΑ xG b {b3:+.2f} (t {t3:+.1f}) · ΣΥΝΟΛΟ γκολ b {b2:+.2f} (t {t2:+.1f}) · '
          f'μεση |μοντ−αγορα| διαφορα {np.abs(x.m - x.km).mean():.2f} συνολο {np.abs(x.Tm - x.kT).mean():.2f}')
print('\n3. ΑΚΡΙΒΕΙΑ (μεσο τετραγωνικο λαθος, μικροτερο = καλυτερο)')
for lab, m in GROUPS:
    x = M[m]; q = lambda p, y: ((x[y] - x[p]) ** 2).mean()
    print(f'   {lab:14s} ΔΙΑΦΟΡΑ μοντελο {q("m", "y"):.3f} vs αγορα {q("km", "y"):.3f} · ΣΥΝΟΛΟ μοντελο {q("Tm", "tg"):.3f} vs αγορα {q("kT", "tg"):.3f}')
print('\n4. ΤΟ ×1.16 ΣΤΟ ΦΑΒΟΡΙ (οπως στο UCL) ΑΝ ΕΜΠΑΙΝΕ ΣΤΑ Γ: μεσο τετρ. λαθος διαφορας')
for lab, m in GROUPS[:3]:
    x = M[m]; m16 = x.fl * 1.16 - x.dl
    print(f'   {lab:14s} σημερα {((x.y - x.m) ** 2).mean():.3f} · με ×1.16 {((x.y - m16) ** 2).mean():.3f} · αγορα {((x.y - x.km) ** 2).mean():.3f} · '
          f'μεση διαφορα: πραγμ {x.y.mean():+.2f} / σημερα {x.m.mean():+.2f} / ×1.16 {m16.mean():+.2f}')
