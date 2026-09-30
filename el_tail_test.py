# -*- coding: utf-8 -*-
"""el_tail_test.py — ΟΥΡΕΣ ΤΟΥ ΜΟΝΤΕΛΟΥ στα μεγαλα φαβορι/αουτσαιντερ (1/10/2026, Στελιος «τρεξε το 4»).
Αφορμη (el_moneyline_test): οταν το μοντελο λεει φαβορι 80-100% → μοντελο 84.9% · πραγματικα 92.0% · αγορα 82.2%·
  picks 1-2 σε αουτσαιντερ 5.0+ −75%· χαντικαπ ιδια πλευρα σε αουτσαιντερ 3+ μονο +10 μον. / 203.
ΔΥΟ ΕΞΗΓΗΣΕΙΣ: (α) ΜΕΡΟΛΗΨΙΑ — το μοντελο υποτιμα τη διαφορα των μεγαλων φαβορι · (β) ΔΙΑΣΠΟΡΑ — γυρω απο μεγαλες διαφορες το
  σκορ ειναι πιο «σφιχτο» απο σ = 11.5.
Δεδομενα: RS E2021-25 · live μοντελο (h_new) · Crown κλεισιμο (αναμενομενη διαφορα αγορας).
1. Ανα μεγεθος διαφορας μοντελου (απο τη ματια του φαβορι): μεση αποκλιση πραγματικου απο μοντελο & απο αγορα, διασπορα.
2. Βαθμονομηση: P(νικη φαβορι) & P(καλυψη γραμμης κλεισιματος) μοντελου vs πραγματικα, ανα ζωνη.
3. ΔΙΟΡΘΩΣΕΙΣ (LOSO): (Α) τεντωμα μεγαλων διαφορων m' = m + k·sgn(m)·max(|m|−t, 0) · (Β) σ(m) = 11.5·(1 − c·min(|m|,12)/12).
   ΚΡΙΤΗΡΙΟ (δηλωμενο): log-loss καλυψης της γραμμης κλεισιματος καλυτερο σε ≥4/5 σεζον · RMSE · και picks χαντικαπ (alert Crown) οχι χειροτερα.
Εξοδος: el_tail_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
D, REC, PR, key, pick, settle, SE5, ACT = (NS[k] for k in ('D', 'REC', 'PR', 'key', 'pick', 'settle', 'SE5', 'ACT'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf; S0 = 11.5
rows = []
for p, r in REC[21].items():
    m = PR.get(key(p), {}).get('h_new')
    if m is None or not np.isfinite(m): continue
    c = r['ser'][-1]
    rows.append(dict(p=p, sea=D.season.values[p], m=m, mk=c[1], L=c[2], act=ACT[p]))
Z = pd.DataFrame(rows)
Z['sg'] = np.sign(Z.m).replace(0, 1)
Z['am'] = Z.m.abs()
Z['r_mod'] = (Z.act - Z.m) * Z.sg; Z['r_mkt'] = (Z.act - Z.mk) * Z.sg
P(f'ματς RS E2021-25 με μοντελο & Crown κλεισιμο: {len(Z)}')
P(''); P('=== 1. ΑΝΑ ΜΕΓΕΘΟΣ ΔΙΑΦΟΡΑΣ ΜΟΝΤΕΛΟΥ (απο τη ματια του φαβορι του μοντελου) ===')
for lo, hi in ((0, 3), (3, 6), (6, 9), (9, 12), (12, 99)):
    x = Z[(Z.am >= lo) & (Z.am < hi)]
    se = x.r_mod.std() / math.sqrt(len(x))
    per = ' '.join(f'{Y[-2:]}:{x[x.sea == Y].r_mod.mean():+.1f}' for Y in SE5 if (x.sea == Y).sum() >= 5)
    P(f'  |μοντελο| {lo:>2}-{hi if hi < 99 else "+":>2}: n {len(x):4d} · πραγματικο − μοντελο {x.r_mod.mean():+5.2f} (t {x.r_mod.mean()/se:+.1f}) · − αγορα {x.r_mkt.mean():+5.2f} · '
      f'αγορα − μοντελο {((x.mk - x.m) * x.sg).mean():+5.2f} · διασπορα (πραγμ − μοντ) {(x.act - x.m).std():5.2f} · [{per}]')
P(''); P('=== 2. ΒΑΘΜΟΝΟΜΗΣΗ ΜΟΝΤΕΛΟΥ (σ 11.5) ===')
Z['pw'] = [Phi(a / S0) for a in Z.am]; Z['win'] = (Z.r_mod + Z.am > 0).astype(float)      # νικη φαβορι του μοντελου
for lo, hi in ((0.5, .65), (.65, .8), (.8, .9), (.9, 1.01)):
    x = Z[(Z.pw >= lo) & (Z.pw < hi)]
    if len(x) >= 10: P(f'  P(νικη φαβορι) μοντελου {lo:.0%}-{min(hi, 1):.0%}: n {len(x):4d} · μοντελο {x.pw.mean():.1%} · πραγματικα {x.win.mean():.1%}')
def cover_p(m, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((m + L - 0.5) / s); pl = Phi((-m - L - 0.5) / s); return pw, 1 - pw - pl
    return Phi((m + L) / s), 0.0
def ll_cover(mv, sv):
    """log-loss καλυψης της γραμμης κλεισιματος (γηπεδουχος) — χωρις τα push."""
    tot = 0.0; n = 0
    for m, s, L, a in zip(mv, sv, Z.L, Z.act):
        v = a + L
        if abs(v) < 1e-9: continue
        pw, pp = cover_p(m, L, s); pc = min(max(pw / (1 - pp) if pp < 1 else 0.5, 1e-4), 1 - 1e-4)
        tot += -math.log(pc if v > 0 else 1 - pc); n += 1
    return tot / n
P(''); P('=== 3. ΔΙΟΡΘΩΣΕΙΣ (LOSO: παραμετρος απο τις ΑΛΛΕΣ σεζον, ελαχιστο log-loss καλυψης) ===')
def per_season(mv, sv):
    return {Y: ll_cover(mv[Z.sea.values == Y], sv[Z.sea.values == Y]) if False else None for Y in SE5}
def ll_mask(mv, sv, msk):
    tot = 0.0; n = 0
    for m, s, L, a, ok in zip(mv, sv, Z.L, Z.act, msk):
        if not ok: continue
        v = a + L
        if abs(v) < 1e-9: continue
        pw, pp = cover_p(m, L, s); pc = min(max(pw / (1 - pp) if pp < 1 else 0.5, 1e-4), 1 - 1e-4)
        tot += -math.log(pc if v > 0 else 1 - pc); n += 1
    return tot / max(n, 1)
base_m = Z.m.values; base_s = np.full(len(Z), S0)
VAR = {('base',): (base_m, base_s)}
for t in (6, 9):
    for k in (0.1, 0.2, 0.3, 0.5):
        VAR[('A', t, k)] = (Z.m.values + k * Z.sg.values * np.maximum(Z.am.values - t, 0), base_s)
for c in (0.05, 0.1, 0.15, 0.2, 0.3):
    VAR[('B', c)] = (base_m, S0 * (1 - c * np.minimum(Z.am.values, 12) / 12))
seas = Z.sea.values
def summary(fam):
    held_m, held_s = base_m.copy(), base_s.copy(); ch = []
    for Y in SE5:
        tr = seas != Y
        cands = [k for k in VAR if k[0] in (fam, 'base')]
        best = min(cands, key=lambda k: ll_mask(VAR[k][0], VAR[k][1], tr)); ch.append(best)
        te = seas == Y; held_m[te] = VAR[best][0][te]; held_s[te] = VAR[best][1][te]
    d = [ll_mask(held_m, held_s, seas == Y) - ll_mask(base_m, base_s, seas == Y) for Y in SE5]
    rm0 = [np.sqrt(np.mean((Z.act.values - base_m)[seas == Y] ** 2)) for Y in SE5]
    rm1 = [np.sqrt(np.mean((Z.act.values - held_m)[seas == Y] ** 2)) for Y in SE5]
    w_ = sum(x < 0 for x in d)
    P(f'  {"Α τεντωμα" if fam == "A" else "Β σφιχτες ουρες"}: επιλογες {ch} · log-loss καλυψης ανα σεζον ' + ' '.join(f'{x*1000:+.2f}' for x in d)
      + f' (×1000) → καλυτερο {w_}/5 {"ΠΕΡΝΑ" if w_ >= 4 else "✗"} · RMSE ανα σεζον ' + ' '.join(f'{a - b:+.3f}' for a, b in zip(rm1, rm0)))
    return held_m, held_s
HA = summary('A'); HB = summary('B')
P('  (in-sample log-loss καλυψης ×1000: ' + ' · '.join(f'{k}: {ll_mask(v[0], v[1], np.ones(len(Z), bool))*1000:.2f}' for k, v in list(VAR.items())[:1] + [kv for kv in VAR.items() if kv[0][0] in ('A', 'B')][:12]) + ')')
# ---- picks χαντικαπ στο alert με τις διορθωσεις (LOSO) ----
P(''); P('=== 4. PICKS ΧΑΝΤΙΚΑΠ (alert Crown, edge ≥8%, κανονας 2ωρου) με τις διορθωσεις ===')
def picks_with(mv, sv):
    idx = {p: i for i, p in enumerate(Z.p)}
    res = []
    for p, r in REC[21].items():
        if p not in idx: continue
        i = idx[p]; m, s = mv[i], sv[i]
        ser, tip = r['ser'], r['tip']
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            _, _, L, o1, o2 = row
            pw, pp = cover_p(m, L, s); pl = 1 - pw - pp
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < 0.08: continue
            if k_ > 0 and (tip - row[0]) / 3600 < 2: break
            dog = (side * np.sign(m) < 0)
            res.append((settle(21, p, side, row, od), D.season.values[p], dog, abs(L)))
            break
    return res
for nm, (mv, sv) in (('σημερα', (base_m, base_s)), ('Α τεντωμα (LOSO)', HA), ('Β σφιχτες ουρες (LOSO)', HB)):
    R = picks_with(mv, sv); a = np.array([x[0] for x in R])
    big = [x[0] for x in R if x[3] >= 8]; dogbig = [x[0] for x in R if x[3] >= 8 and x[2]]
    per = ' '.join(f'{Y[-2:]}:{sum(x[0] for x in R if x[1] == Y):+.1f}' for Y in SE5)
    P(f'  {nm:24s} n {len(a)} · ROI {a.mean()*100:+.1f}% · μοναδες {a.sum():+.1f} [{per}] · γραμμες ≥8: n {len(big)} {sum(big):+.1f} μον. · εκ των οποιων αουτσαιντερ του μοντελου n {len(dogbig)} {sum(dogbig):+.1f}')
open('el_tail_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
