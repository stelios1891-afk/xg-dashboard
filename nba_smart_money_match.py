# -*- coding: utf-8 -*-
"""nba_smart_money_match.py — NBA: ΤΑΥΤΙΖΕΤΑΙ Η ΚΙΝΗΣΗ ΤΩΝ «ΕΞΥΠΝΩΝ» ΜΕ ΤΑ ΔΙΚΑ ΜΑΣ BETS; (28/9/2026, ερωτημα Στελιου)
Απο το nba_line_timing: το 54% της κινησης γινεται 11:00-12:00 ωρα ΝΥ. Εδω: ματς με τζαμπολ ≥18:00 ΝΥ (βραδινα),
  γραμμη ΕΙΣΟΔΟΥ = 09:00 ΝΥ της μερας του ματς (πριν το παραθυρο) · «εξυπνη» κινηση = 09:00→13:00 · αργη = 13:00→κλεισιμο.
Διαφωνια μας d = μοντελο − αναμενομενη διαφορα αγορας στις 09:00.
  1. Κλιση κινησης πανω στο d: ποσο απο τη διαφωνια μας «υιοθετει» η αγορα (0 = τιποτα, 1 = ολη) + συσχετιση, t.
  2. Απο τις ΜΕΓΑΛΕΣ εξυπνες κινησεις (≥0.5 π.): σε ποσες ημασταν απο την ιδια πλευρα (βαση 50%).
  3. Τα picks μας (edge ≥5/8% στις τιμες 09:00): % που η κινηση πηγε μαζι μας / αντιθετα / τιποτα και ROI σε καθε ομαδα.
  4. Ποιο κομματι του μοντελου ταιριαζει με τα εξυπνα: βαση ομαδων vs κουραση/ταξιδι/κινητρο (πολυμεταβλητη).
Μοντελα: ομαδων · ομαδες+κουραση/ταξιδι/κινητρο · «τελεια πληροφορια»+ολα (ξερει ποιος επαιξε — ταβανι). Χαντικαπ + συνολα.
Εξοδος: nba_smart_money_match_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_line_timing.py', encoding='utf-8').read().split("for t, nm, mods, YY in")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
NY = 'America/New_York'
def snap(t, i):
    r = REC[t][i]; tipny = pd.Timestamp(r['tip'], unit='s', tz='UTC').tz_convert(NY)
    if tipny.hour < 18: return None
    day = tipny.normalize()
    a, b = at(r['ser'], (day + pd.Timedelta(hours=9)).timestamp()), at(r['ser'], (day + pd.Timedelta(hours=13)).timestamp())
    if a is None or b is None: return None
    return a, b, r['ser'][-1]
FATIGUE_PART = MODS['ομαδες + κουραση/ταξιδι/κινητρο'] - MODS['μοντελο ομαδων']
def edge_pick(t, mu, row):
    _, _, L, o1, o2 = row; sg = SIG if t == 21 else TSIG
    thr_line = -L if t == 21 else L
    if abs(L - round(L)) < 1e-9:
        pw = 1 - NormalDist(mu, sg).cdf(thr_line + 0.5); pl = NormalDist(mu, sg).cdf(thr_line - 0.5)
    else:
        pw = 1 - NormalDist(mu, sg).cdf(thr_line); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
for t, nm, mods, YY in ((21, 'ΧΑΝΤΙΚΑΠ', MODS, ACTG), (23, 'ΣΥΝΟΛΟ ΠΟΝΤΩΝ', {'μοντελο ομαδων (συνολα)': TMOD}, TOTG)):
    rows = []
    for i in REC[t]:
        s = snap(t, i)
        if s: rows.append((i,) + s)
    I = np.array([r[0] for r in rows]); m09 = np.array([r[1][1] for r in rows]); m13 = np.array([r[2][1] for r in rows]); mc = np.array([r[3][1] for r in rows])
    smart, late = m13 - m09, mc - m13
    P(f'=== {nm}: {len(rows)} βραδινα ματς με γραμμη 09:00 & 13:00 ΝΥ · μεση |εξυπνη κινηση| {np.mean(np.abs(smart)):.2f} π. · |αργη| {np.mean(np.abs(late)):.2f} π. ===')
    for mn, m in mods.items():
        d = m[I] - m09
        P(f'  {mn}:  μεση |διαφωνια μας| στις 09:00 {np.mean(np.abs(d)):.2f} π.')
        for lab, mv in (('09→13 εξυπνη', smart), ('13→κλεισ. αργη', late), ('09→κλεισ. ολη', mc - m09)):
            X = np.column_stack([np.ones(len(d)), d]); c = np.linalg.lstsq(X, mv, rcond=None)[0]; r = mv - X @ c
            se = np.sqrt((r @ r) / (len(d) - 2) / np.sum((d - d.mean()) ** 2))
            P(f'    1. {lab:15s} υιοθετει {c[1]:+.3f} της διαφωνιας μας (t {c[1] / se:+.1f}) · συσχετιση {np.corrcoef(d, mv)[0, 1]:+.3f}')
        big = np.abs(smart) >= 0.5
        same = np.mean(np.sign(d[big]) == np.sign(smart[big]))
        bigd = big & (np.abs(d) >= 2)
        P(f'    2. μεγαλες εξυπνες κινησεις (≥0.5 π.): {big.sum()} · ημασταν ιδια πλευρα {same:.1%} (βαση 50%) · οταν διαφωνουσαμε ≥2 π.: {np.mean(np.sign(d[bigd]) == np.sign(smart[bigd])):.1%} ({bigd.sum()})')
        for thr in (0.05, 0.08):
            grp = {'μαζι μας': [], 'αντιθετα': [], 'καμια': []}
            for j, i in enumerate(I):
                side, e, od = edge_pick(t, m[i], rows[j][1])
                if e < thr: continue
                L = rows[j][1][2]
                res = (YY[i] + L) if t == 21 else (YY[i] - L)
                v = res * side; p = (od - 1) if v > 0 else (0 if v == 0 else -1)
                mvs = smart[j] * side
                k = 'μαζι μας' if mvs >= 0.25 else ('αντιθετα' if mvs <= -0.25 else 'καμια')
                grp[k].append((p, G.season[i], mc[j] - m09[j]))
            n = sum(len(v) for v in grp.values())
            P(f'    3. picks ≥{thr*100:.0f}% (τιμη 09:00): {n} · ' + ' · '.join(
                f'{k} {len(v) / n:.0%} → ROI {np.mean([x[0] for x in v]) * 100:+.1f}% ({sum(1 for s in EV if np.mean([x[0] for x in v if x[1] == s] or [0]) > 0)}/{len(EV)})'
                for k, v in grp.items() if v))
        P('')
    if t == 21:
        dT = MODS['μοντελο ομαδων'][I] - m09; dF = FATIGUE_PART[I]
        X = np.column_stack([np.ones(len(I)), dT, dF]); c = np.linalg.lstsq(X, smart, rcond=None)[0]; r = smart - X @ c
        cov = np.linalg.inv(X.T @ X) * (r @ r) / (len(I) - 3); tt = c / np.sqrt(np.diag(cov))
        P(f'  4. εξυπνη κινηση = {c[1]:+.3f}×(ομαδες − αγορα) (t {tt[1]:+.1f}) {c[2]:+.3f}×(κομματι κουρασης/ταξιδιου/κινητρου) (t {tt[2]:+.1f})')
        X2 = np.column_stack([np.ones(len(I)), dT, dF]); c2 = np.linalg.lstsq(X2, mc - m09, rcond=None)[0]
        P(f'     ολη η κινηση 09→κλεισ. = {c2[1]:+.3f}×ομαδες {c2[2]:+.3f}×κουραση')
        P('')
open('nba_smart_money_match_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 5. «περιμενε επιβεβαιωση»: pick στις 09:00, παιζεται ΣΤΙΣ 13:00 (τιμη 13:00) μονο αν η εξυπνη κινηση πηγε μαζι μας ----
P('=== 5. ΧΑΝΤΙΚΑΠ: περιμενε επιβεβαιωση — pick στις 09:00, πονταρισμα στην ΤΙΜΗ 13:00 ===')
rows = []
for i in REC[21]:
    s = snap(21, i)
    if s: rows.append((i,) + s)
for mn in ('μοντελο ομαδων', 'ομαδες + κουραση/ταξιδι/κινητρο'):
    m = MODS[mn]
    for thr in (0.05, 0.08):
        for need, lab in ((0.25, 'κινηση μαζι μας ≥0.25'), (0.5, 'κινηση μαζι μας ≥0.5')):
            for still in (None, 0.0):
                res_ = []
                for j, (i, a, b, c) in enumerate(rows):
                    side, e, _ = edge_pick(21, m[i], a)
                    if e < thr or (b[1] - a[1]) * side < need: continue
                    s13, e13, _ = edge_pick(21, m[i], b)
                    if still is not None and (s13 != side or e13 < still): continue
                    L, oh, oa = b[2], b[3], b[4]; od = oh if side == 1 else oa
                    v = (ACTG[i] + L) * side
                    res_.append(((od - 1) if v > 0 else (0 if v == 0 else -1), G.season[i]))
                if not res_: continue
                pos = sum(1 for s in EV if np.mean([x[0] for x in res_ if x[1] == s] or [0]) > 0)
                P(f'  {mn:32s} ≥{thr*100:.0f}% · {lab} · {"και ακομα θετικο edge στις 13:00" if still is not None else "χωρις ελεγχο 13:00":32s}: '
                  f'{len(res_)} bets · ROI {np.mean([x[0] for x in res_]) * 100:+.1f}% ({pos}/{len(EV)})')
open('nba_smart_money_match_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
