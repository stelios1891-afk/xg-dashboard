# -*- coding: utf-8 -*-
"""nba_diag.py — NBA: ΠΟΥ ΧΑΝΕΙ ΤΟ ΜΟΝΤΕΛΟ απεναντι στην αγορα (6/10/2026, Στελιος «που χανει στα χαντικαπ και στα συνολα; ποιος μηχανισμος
χρειαζεται βελτιωση, ποιος λειπει;»). ΜΟΝΟ κανονικη περιοδος, καθαρες προβλεψεις (nba_full_clean_test → nba_diag_data.pkl), Crown ανοιγμα/κλεισιμο.
Για καθε κομματι: «χασμα» = λαθος μοντελου − λαθος κλεισιματος (RMSE, ποντοι)· μεροληψια = μεσο (πραγματικο − μοντελο) / (πραγματικο − κλεισιμο).
Ενοτητες: 1 μηνας · 2 ειδησεις (κινηση γραμμης ανοιγμα→κλεισιμο) · 3 μεγεθος φαβορι (συμπιεση) · 4 εδρα · 5 ξεκουραση/B2B · 6 ομαδες (ποιες χανει)
7 αλλαγη ρυθμου/ταση σκορ μεσα στη σεζον (συνολα) · 8 που ειναι η αξια (Κ2 ανα κομματι). Περιγραφικο — καμια αλλαγη στο μοντελο απο εδω."""
import sys, math, pickle, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pickle.load(open('nba_diag_data.pkl', 'rb'))
G, HH, HT, MKH, MKT, GN, B2H, B2A, EV = (D[k] for k in ('G', 'HH', 'HT', 'MKH', 'MKT', 'GN', 'B2H', 'B2A', 'EV'))
S = G.season.values.astype(int); ACT = (G.hs - G.as_).values.astype(float); TOT = (G.hs + G.as_).values.astype(float)
MON = G.date.dt.month.values
# ημερες ξεκουρασης
REST_H = np.full(len(G), 9.0); REST_A = np.full(len(G), 9.0); last = {}
for i in np.argsort(G.date.values, kind='stable'):
    for t, arr in ((G.home.values[i], REST_H), (G.away.values[i], REST_A)):
        k = (S[i], t)
        if k in last: arr[i] = min(9.0, (G.date.values[i] - last[k]) / np.timedelta64(1, 'D') - 1)
    for t in (G.home.values[i], G.away.values[i]): last[(S[i], t)] = G.date.values[i]
def rows(kind):
    MK = MKH if kind == 'h' else MKT; A = ACT if kind == 'h' else TOT; M = HH if kind == 'h' else HT
    I = np.array([i for i in MK if S[i] in EV and np.isfinite(M[i])])
    o = np.array([MK[i]['o'][1] for i in I]); c = np.array([MK[i]['c'][1] for i in I])
    return I, A[I], M[I], o, c
def stat(a, m, c, o=None):
    e_m = np.sqrt(np.mean((a - m) ** 2)); e_c = np.sqrt(np.mean((a - c) ** 2))
    x = m - c; z = a - c
    b = np.polyfit(x, z, 1)[0] if len(x) > 30 and x.std() > 0 else np.nan
    se = (np.sqrt(np.sum((z - np.polyval(np.polyfit(x, z, 1), x)) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)) if len(x) > 30 else np.nan)
    return dict(n=len(a), gap=e_m - e_c, bm=np.mean(a - m), bc=np.mean(a - c), dmc=np.mean(m - c), k2=b, t=b / se if se else np.nan,
                eo=np.sqrt(np.mean((a - o) ** 2)) - e_c if o is not None else np.nan)
def line(lab, s):
    return (f'  {lab:28s} n {s["n"]:5d} · χασμα {s["gap"]:+.2f} · πραγμ−μοντ {s["bm"]:+.2f} · πραγμ−κλεισ {s["bc"]:+.2f} · μοντ−κλεισ {s["dmc"]:+.2f} · '
            f'Κ2 {s["k2"]:+.2f} (t {s["t"]:+.1f})' + (f' · ανοιγμα−κλεισ. {s["eo"]:+.2f}' if np.isfinite(s['eo']) else ''))
for kind, nm in (('h', 'ΧΑΝΤΙΚΑΠ (διαφορα γηπ.)'), ('t', 'ΣΥΝΟΛΑ')):
    I, a, m, o, c = rows(kind)
    P(''); P(f'######################## {nm} ########################')
    P(line('ΟΛΑ', stat(a, m, c, o)))
    P(''); P(' 1. ΑΝΑ ΜΗΝΑ')
    for mo, lab in ((10, 'Οκτωβριος'), (11, 'Νοεμβριος'), (12, 'Δεκεμβριος'), (1, 'Ιανουαριος'), (2, 'Φεβρουαριος'), (3, 'Μαρτιος'), (4, 'Απριλιος')):
        k = MON[I] == mo
        if k.sum() > 50: P(line(lab, stat(a[k], m[k], c[k], o[k])))
    P(''); P(' 2. ΕΙΔΗΣΕΙΣ: κινηση γραμμης ανοιγμα → κλεισιμο (απουσιες, ξεκουραση, ενδεκαδα — οτι μαθαινει η αγορα την τελευταια μερα)')
    mv = np.abs(c - o)
    for lo, hi in ((0, .5), (.5, 1.5), (1.5, 3), (3, 99)):
        k = (mv >= lo) & (mv < hi)
        if k.sum() > 50: P(line(f'κινηση {lo}-{hi if hi < 99 else "+"} π.', stat(a[k], m[k], c[k], o[k])))
    tow = np.sign(m - o) * (c - o)
    P(f'  η αγορα κινειται ΠΡΟΣ το μοντελο κατα {np.mean(tow):+.2f} π. (υπερ {np.mean(tow > .1) * 100:.0f}% / κατα {np.mean(tow < -.1) * 100:.0f}%) · '
      f'το μοντελο «βλεπει» {np.corrcoef(m - o, c - o)[0, 1]:.2f} της κινησης (συσχετιση)')
    P(''); P(' 3. ΜΕΓΕΘΟΣ ΓΡΑΜΜΗΣ (συμπιεση: κλιση πραγματικου πανω στο κλεισιμο / μοντελου πανω στο κλεισιμο)')
    if kind == 'h':
        for lo, hi in ((-99, -9), (-9, -4.5), (-4.5, 0), (0, 4.5), (4.5, 9), (9, 99)):
            k = (c >= lo) & (c < hi)
            if k.sum() > 50: P(line(f'κλεισιμο γηπ. {lo:+}…{hi:+}', stat(a[k], m[k], c[k], o[k])))
        P(f'  κλιση μοντελο ~ κλεισιμο {np.polyfit(c, m, 1)[0]:.2f} · πραγματικο ~ κλεισιμο {np.polyfit(c, a, 1)[0]:.2f} (1 = ιδιο ευρος)')
    else:
        q = np.quantile(c, [.2, .4, .6, .8])
        for lo, hi in zip([-1] + list(q), list(q) + [999]):
            k = (c >= lo) & (c < hi)
            P(line(f'κλεισιμο {lo:.0f}…{hi:.0f}', stat(a[k], m[k], c[k], o[k])))
        P(f'  κλιση μοντελο ~ κλεισιμο {np.polyfit(c, m, 1)[0]:.2f} · πραγματικο ~ κλεισιμο {np.polyfit(c, a, 1)[0]:.2f}')
    if kind == 'h':
        P(''); P(' 4. ΕΔΡΑ ανα σεζον (μεση διαφορα γηπ.)')
        for y in EV:
            k = S[I] == y; P(f'  {y - 1}-{str(y)[2:]}: πραγματικο {a[k].mean():+.2f} · μοντελο {m[k].mean():+.2f} · κλεισιμο {c[k].mean():+.2f}')
    P(''); P(' 5. ΞΕΚΟΥΡΑΣΗ (ημερες ρεπο γηπ./φιλ.)')
    rh, ra = REST_H[I], REST_A[I]
    for lab, k in (('γηπ. B2B, φιλ. οχι', (rh == 0) & (ra > 0)), ('φιλ. B2B, γηπ. οχι', (ra == 0) & (rh > 0)), ('και οι δυο B2B', (rh == 0) & (ra == 0)),
                   ('ισα (≥1 μερα)', (rh >= 1) & (ra >= 1) & (rh == ra)), ('γηπ. +1 μερα παραπανω', (rh - ra == 1) & (ra >= 1)), ('φιλ. +1 μερα παραπανω', (ra - rh == 1) & (rh >= 1)),
                   ('γηπ. ≥3 μερες ρεπο', rh >= 3), ('φιλ. ≥3 μερες ρεπο', ra >= 3)):
        if k.sum() > 50: P(line(lab, stat(a[k], m[k], c[k], o[k])))
    P(''); P(' 6. ΟΜΑΔΕΣ: σε ποιες ομαδες-σεζον το μοντελο χανει περισσοτερο απο την αγορα (μεσο |λαθος| μοντελου − κλεισιματος, γηπ. ή φιλ.)')
    E = collections.defaultdict(list)
    for j, i in enumerate(I):
        for t in (G.home.values[i], G.away.values[i]): E[(S[i], t)].append((abs(a[j] - m[j]) - abs(a[j] - c[j]), m[j] - c[j]))
    T = sorted(((np.mean([x[0] for x in v]), k, len(v), np.mean([x[1] for x in v])) for k, v in E.items() if len(v) >= 40), reverse=True)
    for g_, k, n_, d_ in T[:10]: P(f'  {k[0] - 1}-{str(k[0])[2:]} {k[1]:4s} n {n_:3d} · χειροτερα απο αγορα κατα {g_:+.2f} π./ματς · μεση διαφωνια μοντ−κλεισ {d_:+.2f}')
    gaps = np.array([x[0] for x in T])
    P(f'  κατανομη ομαδων-σεζον: διαμεσος {np.median(gaps):+.2f} · 90% {np.quantile(gaps, .9):+.2f} · 10% {np.quantile(gaps, .1):+.2f}')
    P(''); P(' 7. ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ: αγωνας ομαδας (GN)')
    for lo, hi in ((1, 10), (11, 25), (26, 50), (51, 70), (71, 83)):
        k = (GN[I] >= lo) & (GN[I] <= hi)
        if k.sum() > 50: P(line(f'αγωνας {lo}-{hi}', stat(a[k], m[k], c[k], o[k])))
open('nba_diag_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
