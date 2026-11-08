# -*- coding: utf-8 -*-
"""ucl_dog_loso.py — 19/10/2026 (Στελιος: «το LOSO τι θα διαλεγε;»). Ιδιος κανονας live με ucl_dog_band_test (πρωτη εμφανιση ≤168ω, οχι <2ω,
τιμιος χρονος, κατηγορια Α, Crown & SBOBET). Για καθε κατωφλι T ∈ {4,6,8,10,12,14%}: picks = ΠΡΩΤΗ εμφανιση με edge ≥ T.
LOSO: για καθε κρυμμενη σεζον, διαλεγει το T με τις περισσοτερες μοναδες στις αλλες 3 → το εφαρμοζει στην κρυμμενη. Και με κριτηριο ROI (≥10 picks)."""
import sys
_s = open('ucl_dog_band_test.py', encoding='utf-8').read()
_s = _s[:_s.index('R = []')]
exec(_s)
TH = (0.04, 0.06, 0.08, 0.10, 0.12, 0.14); SE = ['2223', '2324', '2425', '2526']
rows = []
for k_ in range(len(x)):
    if x.cat[k_] != 'A': continue
    i = int(x.i[k_])
    for bk in ('Crown', 'SBOBET'):
        for side in (1, -1):
            seq = []
            for h in HS:
                s = snapT(mids[k_], bk, h)
                if not s: continue
                L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                if ln < 0.5 or not (1.70 <= o <= 2.10): continue
                lh, la = model_at(k_, h); pw, pp = picks.p_cover(ES.eu_dist(lh, la, .85), side, ln)
                seq.append((h, ln, o, edge(pw, pp, o)))
            for T in TH:
                f = next((q for q in seq if q[3] >= T), None)
                if f: rows.append(dict(th=T, sea=x.sea[k_], bk=bk, pnl=picks.settle(GD[i], side, f[1], f[2])))
D = pd.DataFrame(rows)
def units(y):
    if not len(y): return 0.0, 0.0, 0
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); return m.mean() * n, m.mean(), n
print('ΚΑΤΩΦΛΙΑ (ολες οι σεζον, μεσος βιβλιων):')
for T in TH:
    y = D[D.th == T]; u, r, n = units(y); s = y.groupby('sea').pnl.mean()
    print(f'   ≥{int(T * 100):2d}%  {n:4.0f} picks  ROI {100 * r:+6.1f}%  μοναδες {u:+6.1f}  · ' + ' '.join(f'{k}:{100 * v:+.0f}%' for k, v in s.items()) + f'  ({int((s > 0).sum())}/4)')
for crit in ('μοναδες', 'ROI'):
    print(f'\nLOSO (επιλογη με {crit} στις αλλες 3 σεζον):')
    tot = []
    for hold in SE:
        tr = D[D.sea != hold]
        sc = {}
        for T in TH:
            u, r, n = units(tr[tr.th == T])
            sc[T] = u if crit == 'μοναδες' else (r if n >= 10 else -9)
        best = max(sc, key=sc.get)
        te = D[(D.sea == hold) & (D.th == best)]; u, r, n = units(te)
        u4, r4, n4 = units(D[(D.sea == hold) & (D.th == .04)]); u10, r10, n10 = units(D[(D.sea == hold) & (D.th == .10)])
        tot.append((u, n, u4, n4, u10, n10))
        print(f'   κρυμμενη {hold}: διαλεγει ≥{int(best * 100)}% → {n:3.0f} picks ROI {100 * r:+6.1f}% ({u:+.1f}μ) · [σταθερο 4%: {100 * r4:+.1f}% ({u4:+.1f}μ) · σταθερο 10%: {100 * r10:+.1f}% ({u10:+.1f}μ)]')
    t = np.array(tot)
    print(f'   ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ συνολο: LOSO {t[:,0].sum():+.1f}μ / {t[:,1].sum():.0f} picks ({100 * t[:,0].sum() / t[:,1].sum():+.1f}%) · '
          f'σταθερο 4%: {t[:,2].sum():+.1f}μ ({100 * t[:,2].sum() / t[:,3].sum():+.1f}%) · σταθερο 10%: {t[:,4].sum():+.1f}μ ({100 * t[:,4].sum() / t[:,5].sum():+.1f}%)')
