# -*- coding: utf-8 -*-
"""nba_absence_cutoffs.py — NBA: ΑΠΟΥΣΙΕΣ με ΜΕΤΑΒΛΗΤΟ κατωφλι ανα παικτη (8/10/2026, Στελιος «κανε το ιδιο και στο νβα» — ιδιο με dom_bk_absence_test).
Αφορμη: το 20′ στο nba_more_tests οριστηκε απο πριν (Στελιος: «20′ μπορει να παιζει και ο 6ος-7ος»).
Βαση = καθαρες προβλεψεις χαντικαπ nba_diag_data (με B2B) · αγορα Crown ανοιγμα/κλεισιμο · σεζον 2021-26 κανονικη περιοδος.
ΝΕΑ ΑΠΟΥΣΙΑ: παικτης με μεσο ορο ≥C′ (10 τελευταια που επαιξε), επαιξε σε 1 απο τα 3 τελευταια ματς, ΔΕΝ παιζει· C {15, 20, 25, 30}.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση): Α αγορα: κλιση (πραγμ − κλεισ/ανοιγ) ανα 10′ διαφορας απουσιας (φιλ − γηπ)· Β φιλτρο «χωρις pick αν η πλευρα μας
  λειπει ≥Χ′» Χ {20, 30, 50}: ΠΕΡΝΑ αν τα κομμενα χειροτερα σε ≥4/5 σεζον ΚΑΙ το ROI που μενει ανεβαινει. Αναφορα Οκτ-Δεκ. Εξοδος: nba_absence_cutoffs_out.txt"""
import sys, pickle, collections, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pickle.load(open('nba_diag_data.pkl', 'rb'))
G, HH, MKH, EV, SIG = D['G'], D['HH'], D['MKH'], D['EV'], D['SIG']
S = G.season.values.astype(int); ACT = (G.hs - G.as_).values.astype(float); OD = np.isin(G.date.dt.month.values, [10, 11, 12])
lab = lambda y: f'{y - 1}-{str(y)[2:]}'
Phi = NormalDist().cdf
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
PG = pd.read_csv('nba_player_games.csv', low_memory=False, usecols=['PLAYER_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MIN', 'stype'])
PG = PG[PG.stype.astype(str) != 'PO']
PG['team'] = PG.TEAM_ABBREVIATION.replace({'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}); PG['d'] = pd.to_datetime(PG.GAME_DATE).values.astype('datetime64[D]')
PG['MIN'] = pd.to_numeric(PG.MIN, errors='coerce').fillna(0)
CS = (15, 20, 25, 30)
ABS = {C: {} for C in CS}
for t, g in PG.groupby('team'):
    gd = sorted(g.d.unique()); played = {d: dict(zip(x.PLAYER_ID, x.MIN)) for d, x in g.groupby('d')}
    hist = collections.defaultdict(list)
    for j, d in enumerate(gd):
        prev3 = gd[max(0, j - 3):j]; cur = played[d]; miss = {C: 0.0 for C in CS}
        for pid, H in hist.items():
            rec = H[-10:]
            if not rec: continue
            avg = float(np.mean(rec))
            if any(pid in played[x] and played[x][pid] > 0 for x in prev3) and cur.get(pid, 0) <= 0:
                for C in CS:
                    if avg >= C: miss[C] += avg
        for C in CS: ABS[C][(t, np.datetime64(d, 'D'))] = miss[C]
        for pid, m in cur.items():
            if m > 0: hist[pid].append(m)
dD = G.date.values.astype('datetime64[D]')
AH = {C: np.array([ABS[C].get((G.home.values[i], dD[i]), np.nan) for i in range(len(G))]) for C in CS}
AA = {C: np.array([ABS[C].get((G.away.values[i], dD[i]), np.nan) for i in range(len(G))]) for C in CS}
P(f'ματς με αγορα: {sum(1 for i in MKH if S[i] in EV)}')
for C in CS:
    a = np.r_[AH[C], AA[C]]; a = a[np.isfinite(a)]
    P(f'  C {C}′: ομαδα-ματς με νεα απουσια {np.mean(a > 0):.0%} · μεσα λεπτα οταν υπαρχει {a[a > 0].mean():.0f}′')
P(''); P('## Α. ΑΓΟΡΑ: κλιση (πραγμ − γραμμη) ανα 10′ διαφορας απουσιας (φιλ − γηπ)· + = η αγορα/το μοντελο τις υποτιμα')
I = np.array([i for i in MKH if S[i] in EV and np.isfinite(HH[i])])
for C in CS:
    x = (AA[C][I] - AH[C][I]) / 10; ok = np.isfinite(x); x = x[ok]; Ii = I[ok]
    for nm, z in (('κλεισιμο', ACT[Ii] - np.array([MKH[i]['c'][1] for i in Ii])), ('ανοιγμα', ACT[Ii] - np.array([MKH[i]['o'][1] for i in Ii])), ('ΜΟΝΤΕΛΟ μας', ACT[Ii] - HH[Ii])):
        b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
        ys = sum(np.polyfit(x[S[Ii] == Y], z[S[Ii] == Y], 1)[0] > 0 for Y in EV)
        P(f'  C {C}′ {nm:12s} κλιση {b:+.2f} π. ανα 10′ (t {b / se:+.1f}, θετ {ys}/5)')
def picks():
    out_ = []
    for i in MKH:
        if S[i] not in EV or not np.isfinite(HH[i]): continue
        L, mk, o1, o2 = MKH[i]['o']; pw, pp, pl = cover(HH[i], L, SIG); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: continue
        q = (ACT[i] + L) * s_; u = (od - 1) if q > 0 else (0 if q == 0 else -1)
        r = dict(y=S[i], u=u, od_=bool(OD[i]))
        for C in CS:
            r[f'us{C}'] = AH[C][i] if s_ == 1 else AA[C][i]; r[f'op{C}'] = AA[C][i] if s_ == 1 else AH[C][i]
        out_.append(r)
    return pd.DataFrame(out_)
K = picks()
def cell(s):
    if not len(s): return '—'
    return f'{s.u.mean()*100:+.1f}% ({len(s)}, θετ {sum(1 for Y in EV if (s.y == Y).sum() >= 5 and s[s.y == Y].u.mean() > 0)}/5)'
P(''); P(f'## PICKS χαντικαπ ≥8% ανοιγμα: ολα {cell(K)} · Οκτ-Δεκ {cell(K[K.od_])}')
for C in CS:
    P(f'  C {C}′: η ΔΙΚΗ ΜΑΣ πλευρα λειπει {cell(K[K[f"us{C}"] > 0])} · μονο ο ΑΝΤΙΠΑΛΟΣ {cell(K[(K[f"op{C}"] > 0) & (K[f"us{C}"] == 0)])} · κανεις {cell(K[(K[f"us{C}"] == 0) & (K[f"op{C}"] == 0)])}')
P(''); P('## Β. ΦΙΛΤΡΟ «χωρις pick αν η πλευρα μας λειπει ≥Χ′»')
for C in CS:
    for X in (20, 30, 50):
        cut = K[K[f'us{C}'] >= X]; keep = K[~(K[f'us{C}'] >= X)]
        worse = sum(1 for Y in EV if (cut.y == Y).sum() >= 3 and cut[cut.y == Y].u.mean() < keep[keep.y == Y].u.mean())
        ok = worse >= 4 and keep.u.mean() > K.u.mean()
        kod = keep[keep.od_]
        P(f'  C {C}′ Χ {X}′: κοβει {cell(cut)} · μενουν {cell(keep)} · χειροτερα σε {worse}/5' + ('  <- ΠΕΡΝΑ' if ok else '  ✗') + f' · Οκτ-Δεκ μενουν {cell(kod)}')
open('nba_absence_cutoffs_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
