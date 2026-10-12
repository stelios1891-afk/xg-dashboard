"""uecl_b_dog_test.py — 12/10/2026 (ευρημα του uecl_why: στη Β το χαντικαπ ΥΠΕΡ της ομαδας ΧΩΡΙΣ FotMob οταν ειναι αουτσαιντερ, edge ≥10%,
63 picks +25.2% 4/4). Ολα τα τεστ του UCL (οπως uecl_battery): Κ1-Κ4 + γειτονικα κατωφλια, κατωφλια/LOSO, χρονισμος (εισοδος vs κλεισιμο),
fair xG, ανα πηγη/εντος-εκτος/φαση, βαθμονομηση. Conference League 4 σεζον, p_cover (κανονας dogs), 1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
LABS = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ+Elo'}
rows = []
for i in UI:
    if cat(i) != 'B' or LH_N[i] <= 0: continue
    j = VI[str(MIDS[i])]; fmh = V6['src_h'][j] == 'shots'; ns = -1 if fmh else 1          # πλευρα της ομαδας ΧΩΡΙΣ FotMob
    src = LABS.get(V6['src_a'][j] if fmh else V6['src_h'][j]); D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s; ln = L if ns == 1 else -L; o = oh if ns == 1 else oa; oo = oa if ns == 1 else oh
            if ln < 0.5 or not (1.70 <= o <= 2.10): continue
            pw, pp = picks.p_cover(D, ns, ln)
            rows.append(dict(i=i, bk=bk, h=h, side=ns, ln=ln, sea=SEA[i], ph=PH[i], src=src, home=ns == 1, e=edge(pw, pp, o), od=o,
                             pm=pw / max(1 - pp, 1e-9), pk=(1 / o) / (1 / o + 1 / oo), mk=ns * implied_margin(i, L, oh, oa),
                             pnl=picks.settle(GD[i], ns, ln, o)))
X = pd.DataFrame(rows)
def fp(th): return X[X.e >= th].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1).copy()
def roi(x): return x.groupby('bk').pnl.mean().mean() if len(x) else np.nan
def close(r):
    s = snap_ah(MIDS[r.i], r.bk, 0)
    if not s: return np.nan, np.nan
    L, oh, oa = s; ln = L if r.side == 1 else -L; o = oh if r.side == 1 else oa
    return picks.settle(GD[r.i], r.side, ln, o), r.side * implied_margin(r.i, L, oh, oa)
F = fp(.10); cl = [close(r) for r in F.itertuples()]; F['pc'] = [a for a, b in cl]; F['clv'] = [b for a, b in cl] - F.mk
print('ΚΑΤΗΓΟΡΙΑ Β — ΑΟΥΤΣΑΙΝΤΕΡ ΧΩΡΙΣ FotMob (παιρνει ≥0.5), edge ≥10%')
print(f'   {cc(F)} · νεα μορφη {cc(F[F.sea.isin(NEW)])}')
m = F.groupby('bk').pnl.mean(); ps = F.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
k1 = bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
outs, allx = loso(X, (0, .02, .04, .06, .08, .10, .12, .14, .16), ('i', 'bk')); k2 = roi(allx) > 0
cv = F.clv.dropna(); k3 = cv.mean() > 0
act = (F.pnl > 0).mean(); k4 = abs(F.pm.mean() - act) <= max(.05, abs(F.pk.mean() - act))
nb = [roi(fp(t)) for t in (.08, .12)]; kg = all(v > 0 for v in nb)
print(f'   Κ1 {"✓" if k1 else "✗"} · Κ2 {"✓" if k2 else "✗"} (LOSO {" ".join(f"{h[2:]}:{int(t * 100)}" for h, t, _ in outs)} → {100 * roi(allx):+.1f}%) · '
      f'Κ3 {"✓" if k3 else "✗"} (CLV {cv.mean():+.3f} γκολ, προς εμας {100 * (cv > 0).mean():.0f}% / κοντρα {100 * (cv < 0).mean():.0f}%) · '
      f'Κ4 {"✓" if k4 else "✗"} (κερδος: μοντ {100 * F.pm.mean():.0f}% αγορα {100 * F.pk.mean():.0f}% πραγμ {100 * act:.0f}%) · '
      f'γειτονικα {"✓" if kg else "✗"} ({" / ".join(f"{100 * v:+.0f}%" for v in nb)}) · ΣΥΝΟΛΟ {sum([k1, k2, k3, k4, kg])}/5')
print('   κατωφλια: ' + ' · '.join(f'≥{int(t * 100)}% {cc(fp(t))[:26]}' for t in (0, .04, .08, .10, .12, .16, .20)))
print('   ΤΥΦΛΑ (χωρις μοντελο, καθε τετοιο αουτσαιντερ στην πρωτη τιμη): ' + cc(X.sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)))
for lab, mm in (('εντος', F.home), ('εκτος', ~F.home), ('φαση λιγκας', F.ph == 'league'), ('νοκ-αουτ', F.ph == 'KO'),
                ('πηγη γκολ+Elo', F.src == 'γκολ+Elo'), ('πηγη Ben', F.src == 'Ben')):
    print(f'      {lab:14s} {cc(F[mm])}')
print('   ΧΡΟΝΙΣΜΟΣ (εισοδος vs ΙΔΙΑ picks στο κλεισιμο):')
for hi, lo, wl in ((72, 48, '72-48ω'), (36, 18, '36-18ω'), (12, 6, '12-6ω'), (4, 1, '4-1ω'), (0, 0, 'μονο κλεισιμο')):
    y = F[(F.h <= hi) & (F.h >= lo)]
    if len(y): print(f'      βγηκε {wl:14s} {len(y) / 2:4.1f} picks · εισοδος {100 * roi(y):+5.0f}% · κλεισιμο {100 * y.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+5.0f}% · κινηση {y.clv.mean():+.2f} γκολ')
print(f'      ΟΛΑ: εισοδος {100 * roi(F):+.1f}% · κλεισιμο {100 * F.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+.1f}%')
def xv(r):
    x = XG.get(r.i)
    if not x: return np.nan
    d = picks.gd_dist(max(x[0], .05), max(x[1], .05)); pw, pp = picks.p_cover(d, r.side, r.ln)
    return r.od / ((1 - pp) / max(pw, 1e-9)) - 1
F['xv'] = [xv(r) for r in F.itertuples()]
print(f'   FAIR xG: ROI πραγματικο {100 * roi(F):+.1f}% · ΑΞΙΑ xG {100 * F.groupby("bk").xv.mean().mean():+.1f}% · ανα σεζον ' +
      ' '.join(f'{s[2:]} {100 * y.xv.mean():+.0f}' for s, y in F.groupby('sea')))
F.to_csv('uecl_b_dog_picks.csv', index=False)
