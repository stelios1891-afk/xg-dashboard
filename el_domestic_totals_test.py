# -*- coding: utf-8 -*-
"""el_domestic_totals_test.py — ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ ΣΤΑ ΣΥΝΟΛΑ ΠΟΝΤΩΝ της Ευρωλιγκας (1/10/2026, Στελιος: «το 7 ειναι πολυ σημαντικο» —
στο χαντικαπ περασε 5/5 απο τον 11ο αγωνα, στα συνολα δεν ειχε δοκιμαστει ποτε).
ΕΓΧΩΡΙΑ ΤΑΣΗ ΠΟΝΤΩΝ (bk_domestic.json, Nowgoal, 10 λιγκες, walk-forward): για καθε λιγκα-σεζον ridge στο ΣΥΝΟΛΟ καθε ματς:
  συνολο = επιπεδο λιγκας (ελευθερο) + τ_γηπ + τ_φιλ, αφετηρια τ0 = 0.7 × περσινο τελος (βαρος 8 ματς) — ιδιες σταθερες με το χαντικαπ.
  ΣΗΜΑ την ημερα d: ΔT = τ(ματς ΠΡΙΝ τη d) − τ0 = ποσο πιο «ανοιχτα» παιζει ΦΕΤΟΣ στο πρωταθλημα απ' οτι περιμεναμε.
ΜΟΝΤΕΛΟ: συνολο EL = live (v2 + Κ2 · LOSO) + κ·(ΔT_γηπ + ΔT_φιλ) · Α: σταθερο · Β: σβηνει με τα ματς EL × 12/(12 + αγων).
  Ενεργο: (i) απο τον 11ο αγωνα (οπως το χαντικαπ) · (ii) ολη η σεζον. κ {.25, .5, .75, 1}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (κ απο τις αλλες 4 σεζον)· RMSE συνολου αγων 11+ καλυτερο απο το live σε ≥4/5 σεζον (E2021-E2025).
Αναφορα: b vs Pinnacle closing, ROI over/under ≥8% (closing) αγων 11+. Εξοδος: el_domestic_totals_test_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
A = {}
exec(open('el_domestic_rating_test.py', encoding='utf-8').read().split('# ---- 3. EL μοντελο')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
     .replace("open('el_domestic_rating_test_out.txt', 'w'", "open('_unused_dt.txt', 'w'"), A)
MAP, DOM, D0, LEAGUES, math = A['MAP'], A['DOM'], A['D0'], A['LEAGUES'], A['math']
T = {}
exec(open('el_preseason_totals_test.py', encoding='utf-8').read().split('# ---- 1. διαγνωση ----')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
     .replace("open('el_preseason_totals_test_out.txt', 'w'", "open('_unused_dt2.txt', 'w'"), T)
D, IDX, TOT, PRC, SE, RS, RND, C2, probs, SEAS = (T[k] for k in ('D', 'IDX', 'TOT', 'PRC', 'SE', 'RS', 'RND', 'C2', 'probs', 'SEAS'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
# ---- εγχωρια ταση ποντων walk-forward ----
def tot_series():
    S = {}
    for L in LEAGUES:
        keys = sorted([k for k in DOM if k.startswith(L + '_')], key=lambda k: k.split('_')[1]); prev_end = {}
        for k in keys:
            G_ = [g for g in DOM[k]['games'] if str(g[4]).strip() not in ('', '-1', 'None') and str(g[5]).strip() not in ('', '-1', 'None')]
            G_ = [g for g in G_ if 100 < float(g[4]) + float(g[5]) < 260]
            if not G_: prev_end = {}; continue
            gd = np.array([(pd.Timestamp(g[1][:10]) - D0).days for g in G_]); hid = [int(g[2]) for g in G_]; aid = [int(g[3]) for g in G_]
            y = np.array([float(g[4]) + float(g[5]) for g in G_])
            teams = sorted(set(hid) | set(aid)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
            hi = np.array([ix[t] for t in hid]); ai = np.array([ix[t] for t in aid])
            T0 = np.array([0.7 * prev_end.get(t, 0.0) for t in teams])
            def fit(msk):
                m = msk.sum(); Am = np.zeros((m + n, n + 1)); b = np.zeros(m + n)
                r = np.arange(m); Am[r, hi[msk]] = 1; Am[r, ai[msk]] += 1; Am[r, n] = 1; b[:m] = y[msk]
                s8 = math.sqrt(8.0); Am[m + np.arange(n), np.arange(n)] = s8; b[m:] = s8 * T0
                return np.linalg.lstsq(Am, b, rcond=None)[0][:n]
            es = 'E20' + k.split('_')[1][:2]
            for d in np.unique(gd):
                msk = gd < d
                Td = fit(msk) if msk.any() else T0
                for t, i in ix.items(): S.setdefault((es, t, L), []).append((d, Td[i] - T0[i]))
            Tend = fit(np.ones(len(G_), bool))
            prev_end = {t: Tend[i] for t, i in ix.items()}
    return S
ST = tot_series()
def shift(Y, code, d):
    k = MAP.get((Y, code))
    if not k or k not in ST: return 0.0
    v = 0.0
    for dd, x in ST[k]:
        if dd <= d - 1: v = x
        else: break
    return v
H, AW = D.home.values[IDX], D.away.values[IDX]
DN = np.array([(pd.Timestamp(D.date.values[i]) - D0).days for i in IDX])
SIG = np.array([shift(SE[j], H[j], DN[j]) + shift(SE[j], AW[j], DN[j]) for j in range(len(IDX))])
base = np.array(C2, float)
m11 = RS & (RND >= 11) & np.isin(SE, SEAS)
P(f'ΣΗΜΑ ΔT (γηπ+φιλ): καλυψη {np.mean(SIG[m11] != 0):.0%} των ματς 11+ · διασπορα {SIG[m11].std():.2f} π. · μεσος {SIG[m11].mean():+.2f}')
res = TOT - base
P(f'  κλιση (πραγματικο − live) στο ΔT, αγων 11+: {np.polyfit(SIG[m11], res[m11], 1)[0]:+.3f} · ανα σεζον ' +
  ' '.join(f'{Y[-2:]}:{np.polyfit(SIG[m11 & (SE == Y)], res[m11 & (SE == Y)], 1)[0]:+.2f}' for Y in SEAS))
mk = m11 & np.isfinite(PRC[:, 3])
P(f'  κλιση (αγορα − live) στο ΔT: {np.polyfit(SIG[mk], (PRC[:, 3] - base)[mk], 1)[0]:+.3f} · (πραγματικο − αγορα): {np.polyfit(SIG[mk], (TOT - PRC[:, 3])[mk], 1)[0]:+.3f}')
def rm(v, ss, msk): m = msk & np.isin(SE, ss); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
def roi(v, msk):
    res_ = {'over': [], 'under': []}
    for j in np.where(msk & np.isfinite(PRC[:, 3]))[0]:
        TL, ov, un = PRC[j, 3], PRC[j, 4], PRC[j, 5]
        po, pq, pu = probs(v[j], -TL, 16.7); eo, eu = po * ov + pq - 1, pu * un + pq - 1
        over, e, o = (True, eo, ov) if eo >= eu else (False, eu, un)
        if e < 0.08: continue
        x = (TOT[j] - TL) * (1 if over else -1); res_['over' if over else 'under'].append(((o - 1) if x > 0 else (0 if x == 0 else -1), SE[j]))
    f = lambda L: f'{np.mean([a for a, _ in L])*100:+.1f}% ({len(L)}) {sum(1 for s in SEAS if any(b == s for _, b in L) and np.mean([a for a, b in L if b == s]) > 0)}/5' if L else '—'
    return f"over {f(res_['over'])} · under {f(res_['under'])} · ολα {f(res_['over'] + res_['under'])}"
P(''); P('=== LOSO (κ απο τις αλλες σεζον) ===')
for nm, fac in (('Α σταθερο', np.ones(len(IDX))), ('Β σβηνει 12/(12+αγων)', 12 / (12 + RND))):
    for scope, sc in (('απο 11ο', RND >= 11), ('ολη σεζον', RND >= 1)):
        preds = {0.0: base}; preds.update({k: base + np.where(sc, k * fac * SIG, 0) for k in (0.25, 0.5, 0.75, 1.0)})
        held = base.copy(); ch = []
        for Y in SEAS:
            tr = [s for s in SEAS if s != Y]; k = min(preds, key=lambda k: rm(preds[k], tr, m11)); ch.append(k); held[SE == Y] = preds[k][SE == Y]
        diffs = [rm(held, [Y], m11) - rm(base, [Y], m11) for Y in SEAS]; w_ = sum(d < 0 for d in diffs)
        b0 = np.polyfit((base - PRC[:, 3])[mk], (TOT - PRC[:, 3])[mk], 1)[0]; b1 = np.polyfit((held - PRC[:, 3])[mk], (TOT - PRC[:, 3])[mk], 1)[0]
        P(f'  {nm:22s} {scope:10s} κ {ch} · RMSE 11+ {rm(base, SEAS, m11):.3f} → {rm(held, SEAS, m11):.3f} · ' + ' '.join(f'{d:+.3f}' for d in diffs)
          + f' → {w_}/5 {"ΠΕΡΝΑ" if w_ >= 4 else "✗"} · b {b0:+.3f} → {b1:+.3f}')
        P(f'      ROI ≥8% αγων 11+: live {roi(base, m11)}')
        P(f'                        νεο  {roi(held, m11)}')
open('el_domestic_totals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ποια picks αλλαζουν (closing, αγων 11+, Α σταθερο κ .25) ----
new = base + np.where(RND >= 11, 0.25 * SIG, 0)
P(''); P('=== ΠΟΙΑ PICKS ΑΛΛΑΖΟΥΝ (Pinnacle closing ≥8%, αγων 11+, κ .25 σταθερο) ===')
def pk(v, j):
    TL, ov, un = PRC[j, 3], PRC[j, 4], PRC[j, 5]
    po, pq, pu = probs(v[j], -TL, 16.7); eo, eu = po * ov + pq - 1, pu * un + pq - 1
    over, e, o = (True, eo, ov) if eo >= eu else (False, eu, un)
    x = (TOT[j] - TL) * (1 if over else -1)
    return ('over' if over else 'under'), e, ((o - 1) if x > 0 else (0 if x == 0 else -1))
G = {}
for j in np.where(m11 & np.isfinite(PRC[:, 3]))[0]:
    s0, e0, p0 = pk(base, j); s1, e1, p1 = pk(new, j)
    a, b = e0 >= .08, e1 >= .08
    sg = SIG[j] * (1 if s1 == 'over' else -1)
    if a and b and s0 == s1: G.setdefault(('ΚΟΙΝΑ', s0), []).append((p0, SE[j], sg))
    else:
        if a: G.setdefault(('μονο LIVE (τα κοβει)', s0), []).append((p0, SE[j], SIG[j] * (1 if s0 == 'over' else -1)))
        if b: G.setdefault(('μονο ΝΕΟ (τα προσθετει)', s1), []).append((p1, SE[j], sg))
for grp in ('ΚΟΙΝΑ', 'μονο LIVE (τα κοβει)', 'μονο ΝΕΟ (τα προσθετει)'):
    for sd in ('over', 'under'):
        L = G.get((grp, sd), [])
        if L: P(f'  {grp:24s} {sd:5s}: {np.mean([x[0] for x in L])*100:+6.1f}% ({len(L):3d}) {sum(1 for s in SEAS if any(x[1] == s for x in L) and np.mean([x[0] for x in L if x[1] == s]) > 0)}/5 · εγχωριο σημα προς την πλευρα {np.mean([x[2] for x in L]):+.1f} π.')
# under ανα κατευθυνση σηματος
P('  ΟΛΑ τα under του ΝΕΟΥ ανα εγχωριο σημα (− = οι ομαδες παιζουν πιο ΚΛΕΙΣΤΑ εγχωρια):')
U = [(pk(new, j), SIG[j], SE[j]) for j in np.where(m11 & np.isfinite(PRC[:, 3]))[0]]
U = [(r[2], s, y) for r, s, y in U if r[0] == 'under' and r[1] >= .08]
for lo, hi, lab in ((-99, -4, 'σημα ≤ −4'), (-4, 0, '−4…0'), (0, 4, '0…+4'), (4, 99, '≥ +4')):
    z = [p for p, s, y in U if lo <= s < hi]
    if z: P(f'    {lab:10s} {np.mean(z)*100:+6.1f}% ({len(z)})')
open('el_domestic_totals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
