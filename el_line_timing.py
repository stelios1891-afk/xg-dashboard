# -*- coding: utf-8 -*-
"""el_line_timing.py — ΕΥΡΩΛΙΓΚΑ: Η ΓΡΑΜΜΗ ΑΝΑ ΩΡΑ ΠΡΙΝ ΤΟ ΤΖΑΜΠΟΛ, με ΣΩΣΤΕΣ ωρες (30/9/2026, εκκρεμοτητα Στελιου).
Nowgoal basketball 'ut' = 8 ωρες πισω (επιβεβαιωμενο 28/9: τελευταια pre / πρωτη live στο τζαμπολ−7.97ω) → πραγματικη = ut + 8ω.
Το παλιο el_clv_nowgoal_test «εισοδος 12ω» ηταν στην πραγματικοτητα ~4ω.
Αγορα: Crown (Nowgoal cid 3), χαντικαπ (ot 6) & συνολο (ot 6, t 23), σεζον 2021-22 … 2025-26 (E2021-E2025), κανονικη περιοδος.
Μοντελα (ΟΠΩΣ ΤΡΕΧΟΥΝ LIVE): χαντικαπ = v4/Β1 (0.5 περσι + 0.42 ειδικοι, K12, HL60, εδρα 5, ×1.1 απο 7ο αγωνα)·
  συνολο = v2 + Κ2 καμπυλη (LOSO). Σ 11.5 / 16.7.
Α. ακριβεια αγορας ανα ωρα (ιδια ματς) · Β. ποτε κινειται (μεριδιο κινησης, % προς κλεισιμο, «δικιο» κλιση, ωρα ΕΛΛΑΔΑΣ)
Γ. το μοντελο απεναντι στη γραμμη καθε ωρας: b, ROI ≥5/8/10% (τιμες Crown εκεινης της ωρας)
Δ. ΠΡΟΣΟΜΟΙΩΣΗ ALERTS: σαρωση καθε ωρα απο το ανοιγμα· alert = πρωτη ωρα με edge ≥8%. Για τα ιδια picks:
   ROI στην τιμη του alert vs στην τιμη κλεισιματος (αναμονη)· χωρισμενα με το αν η τιμη της πλευρας μας ΑΝΕΒΑΙΝΕ τις 3ω πριν το alert
   («η αγορα φευγει απο την πλευρα μας») και ποσο συνεχισε να κινειται μετα.
Εξοδος: el_line_timing_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
# ---- χαντικαπ: μοντελο v4 + αντιστοιχιση Nowgoal (απο el_clv_nowgoal_test) ----
NSH = {}
src = open('el_clv_nowgoal_test.py', encoding='utf-8').read().split("RSMASK = ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, NSH)
D = NSH['D']; mapping = NSH['mapping']; SE5 = NSH['SE5']
HPRED = NSH['PREDS']['καλυτερη ακριβεια']
# ---- συνολο: v2 + Κ2 (απο el_total_curve_test) ----
TSH = {}
src = open('el_total_curve_test.py', encoding='utf-8').read().split("VARS = ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, TSH)
assert len(TSH['D']) == len(D) and (TSH['D'].t.values == D.t.values).all(), 'διαφορετικο D'
TPRED = np.full(len(D), np.nan); TPRED[TSH['IDX']] = TSH['C2']
SM, ST = 11.5, 16.7
SHIFT = 8 * 3600
ROWS = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ot'] != 6 or r['cid'] != 3: continue
    t = r.get('t', 21)
    ROWS[(r['ngid'], t)] = r['rows']
N = NormalDist()
def ph_(o1, o2): return (1 / o1) / (1 / o1 + 1 / o2)
def series(ng, t, swap):
    out_ = []
    for x in sorted(ROWS.get((ng, t), []), key=lambda x: x[0]):
        if x[4] != 2 or x[1] is None or not x[2] or not x[3]: continue
        ut = x[0] + SHIFT
        if t == 21:
            L = -x[1] * (-1 if swap else 1); o1, o2 = (1 + x[2], 1 + x[3]) if not swap else (1 + x[3], 1 + x[2])
            mu = -L + SM * N.inv_cdf(min(max(ph_(o1, o2), 1e-4), 1 - 1e-4))
        else:
            L = x[1]; o1, o2 = 1 + x[2], 1 + x[3]
            mu = L + ST * N.inv_cdf(min(max(ph_(o1, o2), 1e-4), 1 - 1e-4))
        out_.append((ut, mu, L, o1, o2))
    return out_
def at(ser, tau):
    k = None
    for r in ser:
        if r[0] <= tau: k = r
        else: break
    return k
HS = [24, 20, 16, 12, 8, 6, 4, 3, 2, 1, 0.5, 0]
REC = {21: {}, 23: {}}
lastpre = []
for ng, (i, swap) in mapping.items():
    pos = D.index.get_loc(i)
    if D.phase.values[pos] != 'RS' or D.season.values[pos] not in SE5: continue
    tip = pd.Timestamp(D.t.values[pos]).tz_localize('UTC').timestamp() if pd.Timestamp(D.t.values[pos]).tzinfo is None else pd.Timestamp(D.t.values[pos]).timestamp()
    for t in (21, 23):
        ser = [r for r in series(ng, t, swap) if r[0] <= tip + 600]
        if len(ser) < 2: continue
        if t == 21: lastpre.append((ser[-1][0] - tip) / 3600)
        d_ = {'ser': ser, 'tip': tip, 'pos': pos, 'open': ser[0]}
        d_.update({h: at(ser, tip - h * 3600) for h in HS}); d_[0] = ser[-1]
        REC[t][pos] = d_
lp = np.array(lastpre)
P(f'ελεγχος ωρας: τελευταια τιμη Crown − τζαμπολ (ωρες, μετα τη διορθωση +8): διαμεσος {np.median(lp):+.2f} · 5% {np.percentile(lp, 5):+.2f} · 95% {np.percentile(lp, 95):+.2f}')
ACT = (D.hs - D.as_).values.astype(float); TOT = (D.hs + D.as_).values.astype(float)
# ελεγχος φορας των τιμων συνολου (u = over;)
R23 = REC[23]; cc = np.corrcoef([R23[p][0][1] - R23[p][0][2] for p in R23], [TOT[p] - R23[p][0][2] for p in R23])[0, 1]
P(f'ελεγχος συνολου: συσχετιση (αγορα−γραμμη) με (πραγματικο−γραμμη) = {cc:+.3f} (θετικη = σωστη φορα over/under)')
ATH = 'Europe/Athens'
for t, nm, Y in ((21, 'ΧΑΝΤΙΚΑΠ', ACT), (23, 'ΣΥΝΟΛΟ ΠΟΝΤΩΝ', TOT)):
    R = REC[t]
    op = np.array([(r['tip'] - r['open'][0]) / 3600 for r in R.values()])
    P('')
    P(f'=== {nm}: {len(R)} ματς · ανοιγμα Crown διαμεσος {np.median(op):.1f}ω πριν (25%: {np.percentile(op, 25):.1f} · 75%: {np.percentile(op, 75):.1f}) · καλυψη: '
      + ' '.join(f'{h}ω:{np.mean([r[h] is not None for r in R.values()]):.0%}' for h in HS if h >= 8) + ' ===')
    C = [p for p, r in R.items() if r[16] is not None]
    y = np.array([Y[p] for p in C])
    rm = {}
    for h in ['open'] + [x for x in HS if x <= 16]:
        rm[h] = np.sqrt(np.mean((y - np.array([R[p][h][1] for p in C])) ** 2))
    gain = rm['open'] - rm[0]
    P(f'  Α. ακριβεια (ιδια {len(C)} ματς με γραμμη απο τις 16ω): ' + ' · '.join(f'{("ανοιγμα" if h == "open" else ("κλεισιμο" if h == 0 else f"{h}ω"))} {rm[h]:.2f}' for h in rm))
    P('     % της βελτιωσης ανοιγμα→κλεισιμο που εχει γινει: ' + ' · '.join(f'{h}ω {(rm["open"] - rm[h]) / gain:.0%}' for h in rm if h not in ('open', 0)))
    marks = ['open'] + [x for x in HS if x <= 16]
    tot2 = sum(np.sum((np.array([R[p][b][1] for p in C]) - np.array([R[p][a][1] for p in C])) ** 2) for a, b in zip(marks[:-1], marks[1:]))
    P(f'  Β. {"διαστημα":14s} {"μεση |κιν.|":>11s} {"μεριδ. κιν.²":>12s} {"% προς κλεισ.":>13s} {"«δικιο» κλιση":>13s} {"κερδος RMSE":>12s}')
    for a, b in zip(marks[:-1], marks[1:]):
        m0 = np.array([R[p][a][1] for p in C]); m1 = np.array([R[p][b][1] for p in C]); mc = np.array([R[p][0][1] for p in C])
        mv = m1 - m0; nz = np.abs(mv) > 0.05
        tow = np.mean(np.sign(mv[nz]) == np.sign((mc - m0)[nz])) if nz.sum() else np.nan
        sl = np.polyfit(mv[nz], (y - m0)[nz], 1)[0] if nz.sum() > 30 else np.nan
        lab = f'{"ανοιγμα" if a == "open" else f"{a}ω"}→{"κλεισ." if b == 0 else f"{b}ω"}'
        P(f'     {lab:14s} {np.mean(np.abs(mv)):11.2f} {np.sum(mv ** 2) / tot2:12.0%} {tow:13.0%} {sl:13.2f} {rm[a] - rm[b]:+12.3f}   (κινησεις σε {nz.mean():.0%} των ματς)')
    hr = np.zeros(24)
    for p in C:
        ser = R[p]['ser']
        for p0, p1 in zip(ser[:-1], ser[1:]):
            hr[pd.Timestamp(p1[0], unit='s', tz='UTC').tz_convert(ATH).hour] += (p1[1] - p0[1]) ** 2
    P('     ωρα ΕΛΛΑΔΑΣ (μεριδιο κινησης²): ' + ' '.join(f'{h:02d}:{hr[h] / hr.sum():.0%}' for h in range(24) if hr[h] / hr.sum() >= 0.03))

# ---- Γ. μοντελο vs γραμμη καθε ωρας ----
def pick(t, mu_model, row):
    _, _, L, o1, o2 = row; sg = SM if t == 21 else ST
    thr = -L if t == 21 else L
    if abs(L - round(L)) < 1e-9:
        pw = 1 - NormalDist(mu_model, sg).cdf(thr + 0.5); pl = NormalDist(mu_model, sg).cdf(thr - 0.5)
    else:
        pw = 1 - NormalDist(mu_model, sg).cdf(thr); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
def settle(t, p, side, row, od):
    L = row[2]; v = ((ACT[p] + L) if t == 21 else (TOT[p] - L)) * side
    return (od - 1) if v > 0 else (0.0 if v == 0 else -1.0)
MODEL = {21: HPRED, 23: TPRED}
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ (v4/Β1)'), (23, 'ΣΥΝΟΛΟ (v2+Κ2)')):
    R = REC[t]; C = [p for p, r in R.items() if r[16] is not None and not np.isnan(MODEL[t][p])]
    Y = ACT if t == 21 else TOT
    P('')
    P(f'=== Γ. {nm}: μοντελο vs γραμμη καθε ωρας (ιδια {len(C)} ματς) ===')
    for h in (16, 12, 8, 6, 4, 2, 1, 0):
        mu = np.array([R[p][h][1] for p in C]); mv = np.array([MODEL[t][p] for p in C]); y = np.array([Y[p] for p in C])
        b = np.polyfit(mv - mu, y - mu, 1)[0]; cells = []
        for thr in (0.05, 0.08, 0.10):
            rr = []
            for p in C:
                side, e, od = pick(t, MODEL[t][p], R[p][h])
                if e >= thr: rr.append((settle(t, p, side, R[p][h], od), D.season.values[p]))
            if rr:
                a = np.array([x[0] for x in rr]); ss = np.array([x[1] for x in rr])
                pos_ = sum(1 for s in SE5 if (ss == s).any() and a[ss == s].mean() > 0)
                cells.append(f'≥{thr*100:.0f}%: {a.mean()*100:+.1f}% ({len(a)}) {pos_}/{len(SE5)}')
        P(f'    {("κλεισιμο" if h == 0 else f"{h}ω πριν"):9s} b {b:+.3f} | ' + ' | '.join(cells))

# ---- Δ. προσομοιωση alerts ----
P('')
P('=== Δ. ΠΡΟΣΟΜΟΙΩΣΗ ALERTS (σαρωση καθε ωρα απο το ανοιγμα· alert = πρωτη ωρα με edge ≥8%) ===')
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΟ')):
    R = REC[t]; recs = []
    for p, r in R.items():
        if np.isnan(MODEL[t][p]): continue
        tip = r['tip']; t0 = r['open'][0]
        k = 0
        while True:
            tau = t0 + k * 3600
            if tau >= tip: break
            row = at(r['ser'], tau)
            side, e, od = pick(t, MODEL[t][p], row)
            if e >= 0.08:
                prev = at(r['ser'], tau - 3 * 3600) or r['open']
                s_ = side if t == 21 else side          # χαντικαπ: +1 γηπ· συνολο: +1 over
                drift = (row[1] - prev[1]) * s_         # + = η αγορα κινηθηκε ΠΡΟΣ την πλευρα μας (τιμη μας επεσε)
                after = (r[0][1] - row[1]) * s_         # + = μετα το alert η αγορα ηρθε προς εμας
                c = r[0]; oc = c[3] if side == 1 else c[4]
                recs.append(dict(season=D.season.values[p], hrs=(tip - tau) / 3600, drift=drift, after=after,
                                 pnl_alert=settle(t, p, side, row, od), pnl_close=settle(t, p, side, c, oc),
                                 still=pick(t, MODEL[t][p], c)[0] == side and pick(t, MODEL[t][p], c)[1] >= 0.08))
                break
            k += 1
    Z = pd.DataFrame(recs)
    P(f'  {nm}: {len(Z)} alerts · διαμεσος ωρα alert {Z.hrs.median():.1f}ω πριν το τζαμπολ')
    def line_(lab, z):
        if not len(z): return
        pa, pc = z.pnl_alert.mean() * 100, z.pnl_close.mean() * 100
        pos_a = sum(1 for s in SE5 if (z.season == s).any() and z[z.season == s].pnl_alert.mean() > 0)
        pos_c = sum(1 for s in SE5 if (z.season == s).any() and z[z.season == s].pnl_close.mean() > 0)
        P(f'    {lab:44s} n {len(z):4d} · μετα το alert η αγορα {z.after.mean():+.2f} π. προς εμας · ROI στο alert {pa:+.1f}% ({pos_a}/5) · '
          f'ROI αν περιμεναμε ως το κλεισιμο {pc:+.1f}% ({pos_c}/5) · ακομα pick στο κλεισιμο {z.still.mean():.0%}')
    line_('ΟΛΑ τα alerts', Z)
    line_('η τιμη μας ΑΝΕΒΑΙΝΕ τις 3ω πριν (αγορα φευγει ≥0.5π)', Z[Z.drift <= -0.5])
    line_('σταθερη (±0.5π)', Z[Z.drift.abs() < 0.5])
    line_('η τιμη μας ΕΠΕΦΤΕ (αγορα ερχεται ≥0.5π)', Z[Z.drift >= 0.5])
    line_('alert ≥12ω πριν', Z[Z.hrs >= 12]); line_('alert <12ω πριν', Z[Z.hrs < 12])
open('el_line_timing_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
