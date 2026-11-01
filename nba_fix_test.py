# -*- coding: utf-8 -*-
"""nba_fix_test.py — NBA: διορθωσεις για ο,τι εδειξε το nba_diag (6/10/2026).
Φ1 ΑΠΟΣΥΜΠΙΕΣΗ ΧΑΝΤΙΚΑΠ: μοντελο ~ κλεισιμο κλιση .75 ενω πραγματικο ~ κλεισιμο 1.03 → διαφορα' = k · διαφορα, k {1, 1.1, 1.2, 1.3, 1.4}.
Φ2 ΣΥΝΟΛΑ — ΑΠΟΣΥΜΠΙΕΣΗ: συνολο' = κεντρο + k · (συνολο − κεντρο), κεντρο = μεσο συνολο μοντελου των προηγουμενων 14 ημερων, k {1, 1.15, 1.3, 1.45}.
Φ3 ΣΥΝΟΛΑ — ΕΠΙΠΕΔΟ: το μοντελο μενει πισω στο σκοραρισμα (πραγμ − μοντ +1.7)· διορθωση = κ · μεσο (πραγματικο − μοντελο) των τελευταιων 150 ματς
   (μονο οσα εχουν ηδη παιχτει), κ {0, .5, 1}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): καθε διορθωση επιλεγεται LOSO (RMSE)· ΜΠΑΙΝΕΙ αν καλυτερη σε ≥4/5 σεζον. Μετα: χασμα vs κλεισιμο, Κ2, ROI ≥8% (Crown ανοιγμα) Οκτ-Δεκ & ολη.
Εξοδος: nba_fix_test_out.txt"""
import sys, math, pickle, collections
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pickle.load(open('nba_diag_data.pkl', 'rb'))
G, HH, HT, MKH, MKT, EV, SIG, SIGT = (D[k] for k in ('G', 'HH', 'HT', 'MKH', 'MKT', 'EV', 'SIG', 'SIGT'))
S = G.season.values.astype(int); ACT = (G.hs - G.as_).values.astype(float); TOT = (G.hs + G.as_).values.astype(float)
MON = G.date.dt.month.values; OD = np.isin(MON, [10, 11, 12]); DT = G.date.values
order = np.argsort(DT, kind='stable')
def rm(v, tgt, ys):
    m = np.isin(S, ys) & np.isfinite(v); return float(np.sqrt(np.mean((tgt - v)[m] ** 2)))
def loso(PR, tgt, lab, base):
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; k = min(PR, key=lambda k: rm(PR[k], tgt, tr)); ch.append(k); held[S == Y] = PR[k][S == Y]
    d = [rm(held, tgt, [Y]) - rm(PR[base], tgt, [Y]) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
    P(f'  {lab:40s} {rm(PR[base], tgt, EV):.3f} → {rm(held, tgt, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · επιλογες {ch}' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
    return (held if ok else PR[base]), ok
nd = NormalDist(); Phi = nd.cdf
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def market(kind, v, lab):
    MK = MKH if kind == 'h' else MKT; A = ACT if kind == 'h' else TOT; sg = SIG if kind == 'h' else SIGT
    I = [i for i in MK if S[i] in EV and np.isfinite(v[i])]
    c = np.array([MK[i]['c'][1] for i in I]); a = A[I]; m = v[I]
    x, z = m - c, a - c; b = np.polyfit(x, z, 1); se = math.sqrt(np.sum((z - np.polyval(b, x)) ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = [np.polyfit(x[S[I] == Y], z[S[I] == Y], 1)[0] for Y in EV]
    cells = []
    for nm, msk in (('Οκτ-Δεκ', OD), ('ολη', np.ones(len(G), bool))):
        R = collections.defaultdict(list)
        for i in I:
            if not msk[i]: continue
            L, mk, o1, o2 = MK[i]['o']
            if kind == 'h':
                pw, pp, pl = cover(v[i], L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                q = (ACT[i] + L) * s_
            else:
                po, pq, pu = cover(v[i], -L, sg); e1, e2 = po * o1 + pq - 1, pu * o2 + pq - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                q = (TOT[i] - L) * s_
            if e < .08: continue
            R[S[i]].append((od - 1) if q > 0 else (0 if q == 0 else -1))
        u = [x for Y in EV for x in R[Y]]
        cells.append(f'{nm} {np.mean(u) * 100:+.1f}% ({len(u)}, {sum(np.mean(R[Y]) > 0 for Y in EV if R[Y])}/5)')
    P(f'    [{lab}] χασμα vs κλεισιμο {np.sqrt(np.mean(z ** 2 * 0 + (a - m) ** 2)) - np.sqrt(np.mean((a - c) ** 2)):+.2f} · μοντ−κλεισ {np.mean(m - c):+.2f} · κλιση μοντ~κλεισ {np.polyfit(c, m, 1)[0]:.2f} · '
      f'Κ2 {b[0]:+.2f} (t {b[0] / se:+.1f}, θετ {sum(p > 0 for p in per)}/5) · ROI ≥8% ανοιγμα: ' + ' · '.join(cells))
P('################ ΧΑΝΤΙΚΑΠ ################')
market('h', HH, 'σημερα')
PRh = {k: k * HH for k in (1.0, 1.1, 1.2, 1.3, 1.4)}
H1, okh = loso(PRh, ACT, 'Φ1 αποσυμπιεση χαντικαπ k', 1.0)
market('h', H1, 'με Φ1 (LOSO)')
for k in (1.2, 1.3): market('h', PRh[k], f'k {k} σταθερο')
P(''); P('################ ΣΥΝΟΛΑ ################')
market('t', HT, 'σημερα')
# κεντρο 14 ημερων & υπολοιπο 150 ματς (μονο παρελθον)
CEN = np.full(len(G), np.nan); RES = np.zeros(len(G))
from collections import deque
for y in sorted(set(S)):
    idx = order[S[order] == y]; win = deque(); res = deque(); ds = DT[idx]
    j0 = 0
    for jj, i in enumerate(idx):
        while j0 < jj and (ds[jj] - ds[j0]) / np.timedelta64(1, 'D') > 14: j0 += 1
        prev = [HT[idx[q]] for q in range(j0, jj) if ds[q] < ds[jj] and np.isfinite(HT[idx[q]])]
        CEN[i] = np.mean(prev) if len(prev) >= 20 else np.nanmean(HT[idx[:max(jj, 1)]]) if jj else HT[i]
        past = [TOT[idx[q]] - HT[idx[q]] for q in range(max(0, jj - 400), jj) if ds[q] < ds[jj] and np.isfinite(HT[idx[q]])][-150:]
        RES[i] = np.mean(past) if len(past) >= 30 else 0.0
PRt = {k: CEN + k * (HT - CEN) for k in (1.0, 1.15, 1.3, 1.45)}
T1, okt = loso(PRt, TOT, 'Φ2 αποσυμπιεση συνολων k', 1.0)
market('t', T1, 'με Φ2 (LOSO)')
PR3 = {k: T1 + k * RES for k in (0.0, .5, 1.0)}
T2, ok3 = loso(PR3, TOT, 'Φ3 επιπεδο (υπολοιπο 150 ματς) κ', 0.0)
market('t', T2, 'με Φ2+Φ3 (LOSO)')
P('  μοντ−πραγμ ανα μηνα (μετα): ' + ' · '.join(f'{mo}: {np.nanmean((TOT - T2)[(MON == mo) & np.isin(S, EV)]):+.2f}' for mo in (10, 11, 12, 1, 2, 3, 4)))
open('nba_fix_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
