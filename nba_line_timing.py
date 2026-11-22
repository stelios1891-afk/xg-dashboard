# -*- coding: utf-8 -*-
"""nba_line_timing.py — NBA: Η ΓΡΑΜΜΗ ΑΝΑ ΩΡΑ ΠΡΙΝ ΤΟ ΤΖΑΜΠΟΛ (Crown, Nowgoal) (28/9/2026, ερωτημα Στελιου).
Nowgoal basketball 'ut' ειναι 8 ωρες πισω (η τελευταια τιμη πεφτει σταθερα στο −7.97ω) → ut_πραγματικο = ut + 8ω.
Τζαμπολ = ωρα Πεκινου − 8. Η Crown ανοιγει ~18ω πριν (διαμεσος) → οριζοντες 12/10/8/6/4/3/2/1/0.5ω + κλεισιμο.
Γραμμη σε ωρα h = η τελευταια τιμη πριν απο (τζαμπολ − h). Αναμενομενη διαφορα = −L + σ·Φ⁻¹(p γηπ. χωρις γκανιοτα) (και για συνολα).
Α. Ακριβεια αγορας ανα ωρα (ΙΔΙΑ ματς: οσα εχουν γραμμη και στις 12ω).
Β. Ποτε κινειται: ανα διαστημα μεση κινηση, μεριδιο της συνολικης κινησης, % προς το κλεισιμο, «εχει δικιο;» (κλιση του
   αποτελεσματος στην κινηση: 1 = σωστη ολοκληρη, <1 = υπερβολη) και κερδος ακριβειας (RMSE πριν − μετα)· + ωρα ΝΥ της κινησης.
Γ. Το μοντελο μας απεναντι στη γραμμη καθε ωρας (τιμες εκεινης της ωρας): b, ROI ≥5/8/10%.
Εξοδος: nba_line_timing_out.txt"""
import sys, math, json
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_gap_fatigue_test.py', encoding='utf-8').read().split("Xe = np.column_stack")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
IPHI = NormalDist().inv_cdf
SHIFT = 8 * 3600
HS = [12, 10, 8, 6, 4, 3, 2, 1, 0.5, 0]

# ---- αντιστοιχιση ngid → ματς G (ιδια λογικη με nba_model_test) ----
MAP = {}
for sea, se in NGS.items():
    try: S = json.load(open(f'nowgoal_nba/sched_{sea}.json', encoding='utf-8'))
    except FileNotFoundError: continue
    for g in S:
        if g['hs'] is None: continue
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
        us = tip.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize()
        cand = [i for i in key.get((se, g['hs'], g['as_']), []) if abs((G.date[i] - us).days) <= 1]; swap = False
        if not cand:
            cand = [i for i in key.get((se, g['as_'], g['hs']), []) if abs((G.date[i] - us).days) <= 1]; swap = True
        if len(cand) == 1: MAP[cand[0]] = (g['ngid'], swap, tip.timestamp())
TSIG = 18.0
def series(i, t):
    ngid, swap, tip = MAP[i]
    rows = sorted([(x[0] + SHIFT, x[1], x[2], x[3]) for x in ODDS.get((ngid, t), []) if x[1] is not None and x[2] and x[3]])
    res = []
    for ut, g, u, d in rows:
        if t == 21:
            L = -g * (-1 if swap else 1); oh, oa = (1 + u, 1 + d) if not swap else (1 + d, 1 + u)
            p = (1 / oh) / (1 / oh + 1 / oa); mu = -L + SIG * IPHI(p)
            res.append((ut, mu, L, oh, oa))
        else:
            ov, un = 1 + u, 1 + d; p = (1 / ov) / (1 / ov + 1 / un)
            res.append((ut, g + TSIG * IPHI(p), g, ov, un))
    return tip, res
def at(res, tau):
    k = None
    for r in res:
        if r[0] <= tau: k = r
        else: break
    return k
EV = [s for s in TS if s in EVAL]
GI = [i for i in IDX if G.season[i] in EV and i in MAP]
REC = {21: {}, 23: {}}
for t in (21, 23):
    for i in GI:
        tip, res = series(i, t)
        if not res: continue
        d_ = {'open': res[0], 'ser': res, 'tip': tip}; d_.update({h: at(res, tip - h * 3600) for h in HS}); REC[t][i] = d_
ACTG = (G.hs - G.as_).values.astype(float); TOTG = (G.hs + G.as_).values.astype(float)
for t, nm, YY in ((21, 'ΧΑΝΤΙΚΑΠ', ACTG), (23, 'ΣΥΝΟΛΟ ΠΟΝΤΩΝ', TOTG)):
    R = REC[t]
    P(f'=== {nm}: {len(R)} ματς · ανοιγμα Crown (ωρες πριν) διαμεσος {np.median([(r["tip"] - r["open"][0]) / 3600 for r in R.values()]):.1f} · '
      + ' '.join(f'{h}ω:{np.mean([r[h] is not None for r in R.values()]):.0%}' for h in HS if h >= 6) + ' ===')
    C = [i for i, r in R.items() if r[12] is not None]
    y = np.array([YY[i] for i in C])
    P(f'  Α. ακριβεια (ιδια {len(C)} ματς με γραμμη απο τις 12ω):')
    rm = {}
    for h in ['open'] + HS:
        mu = np.array([R[i][h][1] for i in C]); rm[h] = np.sqrt(np.mean((y - mu) ** 2))
    gain = rm['open'] - rm[0]
    P('    ' + ' · '.join(f'{("ανοιγμα" if h == "open" else ("κλεισιμο" if h == 0 else f"{h}ω"))} {rm[h]:.3f}' for h in ['open'] + HS))
    P('    % της βελτιωσης ανοιγμα→κλεισιμο που εχει γινει: ' + ' · '.join(f'{h}ω {(rm["open"] - rm[h]) / gain:.0%}' for h in HS[:-1]))
    P('  Β. ποτε κινειται (ιδια ματς):')
    P(f'    {"διαστημα":14s} {"μεση |κιν.|":>11s} {"μεριδ. κιν.²":>12s} {"% προς κλεισ.":>13s} {"«δικιο» κλιση":>13s} {"κερδος RMSE":>12s}')
    marks = ['open'] + HS
    tot2 = sum(np.sum((np.array([R[i][b][1] for i in C]) - np.array([R[i][a][1] for i in C])) ** 2) for a, b in zip(marks[:-1], marks[1:]))
    for a, b in zip(marks[:-1], marks[1:]):
        m0 = np.array([R[i][a][1] for i in C]); m1 = np.array([R[i][b][1] for i in C]); mc = np.array([R[i][0][1] for i in C])
        mv = m1 - m0; nz = np.abs(mv) > 0.05
        tow = np.mean(np.sign(mv[nz]) == np.sign((mc - m0)[nz])) if nz.sum() else np.nan
        sl = np.polyfit(mv[nz], (y - m0)[nz], 1)[0] if nz.sum() > 30 else np.nan
        lab = f'{"ανοιγμα" if a == "open" else f"{a}ω"}→{"κλεισ." if b == 0 else f"{b}ω"}'
        P(f'    {lab:14s} {np.mean(np.abs(mv)):11.2f} {np.sum(mv ** 2) / tot2:12.0%} {tow:13.0%} {sl:13.2f} {rm[a] - rm[b]:+12.3f}   (κινησεις {nz.mean():.0%} των ματς)')
    # ωρα Νεας Υορκης των κινησεων (τετραγωνο κινησης), ολη η διαδρομη
    hr = np.zeros(24); cnt = np.zeros(24)
    for i in C:
        ser = R[i]['ser']
        for p0, p1 in zip(ser[:-1], ser[1:]):
            hh = pd.Timestamp(p1[0], unit='s', tz='UTC').tz_convert('America/New_York').hour
            hr[hh] += (p1[1] - p0[1]) ** 2; cnt[hh] += 1
    P('    ωρα ΝΥ (μεριδιο κινησης²): ' + ' '.join(f'{h:02d}:{hr[h] / hr.sum():.0%}' for h in range(24) if hr[h] / hr.sum() >= 0.02))
    P('')

# ---- Γ. μοντελο vs γραμμη ανα ωρα ----
OTP = ((G.hs + G.as_) * (1 - 48 / G.mins)).values; OT_ADD = float(OTP[np.isin(G.season.values, EV)].mean())
MODS = {'μοντελο ομαδων': BASES['μοντελο ομαδων'],
        'ομαδες + κουραση/ταξιδι/κινητρο': loso([BASES['μοντελο ομαδων']] + [XF[:, j] for j in range(XF.shape[1])]),
        '«τελεια πληροφορια» + ολα': loso([BASES['καλυτερο «τελειας πληροφοριας»']] + [XF[:, j] for j in range(XF.shape[1])])}
TMOD = run(h=2.0, lam=8, HL=60, carry=0.7, lw=0.5)[1] + OT_ADD
def bets(t, m, h, thr, C):
    rows = []
    for i in C:
        r = REC[t][i][h]; _, _, L, o1, o2 = r
        if t == 21: mu, sg, res = m[i], SIG, ACTG[i] + L
        else: mu, sg, res = m[i], TSIG, TOTG[i] - L
        if abs(L - round(L)) < 1e-9:
            if t == 21: pw = 1 - NormalDist(mu, sg).cdf(-L + 0.5); pl = NormalDist(mu, sg).cdf(-L - 0.5)
            else: pw = 1 - NormalDist(mu, sg).cdf(L + 0.5); pl = NormalDist(mu, sg).cdf(L - 0.5)
        else:
            if t == 21: pw = 1 - NormalDist(mu, sg).cdf(-L)
            else: pw = 1 - NormalDist(mu, sg).cdf(L)
            pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < thr: continue
        v = res * side
        rows.append(dict(season=G.season[i], p=(od - 1) if v > 0 else (0 if v == 0 else -1)))
    return pd.DataFrame(rows)
for t, nm, mods, YY in ((21, 'ΧΑΝΤΙΚΑΠ', MODS, ACTG), (23, 'ΣΥΝΟΛΟ', {'μοντελο ομαδων (συνολα)': TMOD}, TOTG)):
    R = REC[t]; C = [i for i, r in R.items() if r[12] is not None]
    P(f'=== Γ. {nm}: μοντελο vs γραμμη καθε ωρας (ιδια {len(C)} ματς, τιμες Crown εκεινης της ωρας) ===')
    for mn, m in mods.items():
        P(f'  {mn}')
        for h in (10, 8, 6, 4, 2, 1, 0):
            mu = np.array([R[i][h][1] for i in C]); mv = np.array([m[i] for i in C]); y = np.array([YY[i] for i in C])
            b = np.polyfit(mv - mu, y - mu, 1)[0]; cells = []
            for thr in (0.05, 0.08, 0.10):
                Bt = bets(t, m, h, thr, C); pos = sum(1 for s in EV if len(Bt[Bt.season == s]) and Bt[Bt.season == s].p.mean() > 0)
                cells.append(f'≥{thr*100:.0f}%: {Bt.p.mean()*100:+.1f}% ({len(Bt)}) {pos}/{len(EV)}')
            P(f'    {("κλεισιμο" if h == 0 else f"{h}ω πριν"):9s} b {b:+.3f} | ' + ' | '.join(cells))
    P('')
open('nba_line_timing_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
