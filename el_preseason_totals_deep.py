# -*- coding: utf-8 -*-
"""el_preseason_totals_deep.py — ΒΑΘΥΤΕΡΑ: προετοιμασια στα ΣΥΝΟΛΑ (1/10/2026, ερωτηματα Στελιου).
Βαση: el_preseason_totals_test.py (ταση ποντων r_T απο φιλικα, διορθωση σταθερη κ·(r_T γηπ + r_T φιλ) στις αγων 1-10).
A. ΣΒΗΣΙΜΟ: διορθωση × (11 − αγων)/10 (πληρης στην 1η, μηδεν στην 11η) · επισης × (16 − αγων)/15 (ως την 15η). κ {.25,.5,.75,1}, LOSO.
B. ΣΥΝΑΙΝΕΣΗ (Pinnacle closing, ≥8%): picks που βγαζουν ΚΑΙ τα δυο (παλιο & νεο, ιδια πλευρα) · μονο παλιο · μονο νεο — ανα over/under.
C. ΓΡΑΜΜΗ ΑΝΟΙΓΜΑΤΟΣ (Crown, Nowgoal t=23, ωρες +8): κινηση ανοιγμα→κλεισιμο vs (μοντελο − ανοιγμα): ποσο «υιοθετει» η αγορα
   απο τη διαφωνια του παλιου/νεου· picks ≥8% στην τιμη ΑΝΟΙΓΜΑΤΟΣ: κινηση γραμμης προς εμας & ROI — ανα over/under.
Εξοδος: el_preseason_totals_deep_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
NS = {}
exec(open('el_preseason_totals_test.py', encoding='utf-8').read().replace("open('el_preseason_totals_test_out.txt', 'w'", "open('_unused_pt.txt', 'w'"), NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, IDX, TOT, PRC, SE, RS, RND, C2, probs, PRE_T, DH, DA, SEAS = (NS[k] for k in ('D', 'IDX', 'TOT', 'PRC', 'SE', 'RS', 'RND', 'C2', 'probs', 'PRE_T', 'DH', 'DA', 'SEAS'))
ST = 16.7; base = np.array(C2, float); E10 = RS & (RND <= 10)
RSUM = np.array([PRE_T.get((SE[j], DH[j]), 0.0) + PRE_T.get((SE[j], DA[j]), 0.0) for j in range(len(IDX))])
def rm(v, ss): m = E10 & np.isin(SE, ss); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
def loso(preds):
    held = base.copy(); ch = []
    for Y in SEAS:
        tr = [s for s in SEAS if s != Y]; k = min(preds, key=lambda k: rm(preds[k], tr)); ch.append(k); held[SE == Y] = preds[k][SE == Y]
    return held, ch
def pick(tt, j, TL=None, ov=None, un=None):
    TL = PRC[j, 3] if TL is None else TL; ov = PRC[j, 4] if ov is None else ov; un = PRC[j, 5] if un is None else un
    po, pq, pu = probs(tt, -TL, ST); eo, eu = po * ov + pq - 1, pu * un + pq - 1
    over, e, o = (True, eo, ov) if eo >= eu else (False, eu, un)
    v = (TOT[j] - TL) * (1 if over else -1)
    return ('over' if over else 'under'), e, ((o - 1) if v > 0 else (0 if v == 0 else -1))
def roi_line(tt):
    res = {'over': [], 'under': []}
    for j in range(len(IDX)):
        if not (E10[j] and SE[j] in SEAS) or np.isnan(PRC[j, 3]): continue
        s, e, p = pick(tt[j], j)
        if e >= 0.08: res[s].append((p, SE[j]))
    f = lambda L: f'{np.mean([x[0] for x in L])*100:+.1f}% ({len(L)}) {sum(1 for s in SEAS if any(x[1] == s for x in L) and np.mean([x[0] for x in L if x[1] == s]) > 0)}/5' if L else '—'
    return f"over {f(res['over'])} · under {f(res['under'])} · ολα {f(res['over'] + res['under'])}"
mk10 = E10 & np.isin(SE, SEAS) & np.isfinite(PRC[:, 3])
def bline(v): return np.polyfit((v - PRC[:, 3])[mk10], (TOT - PRC[:, 3])[mk10], 1)[0]
# ---- A. σβησιμο ----
P('=== A. ΣΒΗΣΙΜΟ της διορθωσης (LOSO, αγων 1-10) ===')
VAR = {'σταθερη ως 10η (τεστ)': lambda k: base + np.where(RND <= 10, k * RSUM, 0),
       'σβηνει ως 11η': lambda k: base + k * RSUM * np.clip((11 - RND) / 10, 0, 1),
       'σβηνει ως 16η': lambda k: base + k * RSUM * np.clip((16 - RND) / 15, 0, 1)}
HELD = {}
for nm, f in VAR.items():
    preds = {0.0: base}; preds.update({k: f(k) for k in (0.25, 0.5, 0.75, 1.0)})
    h, ch = loso(preds); HELD[nm] = h
    diffs = [rm(h, [Y]) - rm(base, [Y]) for Y in SEAS]; w_ = sum(d < 0 for d in diffs)
    P(f'  {nm:24s} κ {ch} · RMSE {rm(base, SEAS):.3f} → {rm(h, SEAS):.3f} · ' + ' '.join(f'{d:+.3f}' for d in diffs) + f' → {w_}/5 · b {bline(h):+.3f} · ROI ≥8% {roi_line(h)}')
P(f'  ΒΑΣΗ (live)              b {bline(base):+.3f} · ROI ≥8% {roi_line(base)}')
# ---- B. συναινεση ----
P('')
P('=== B. ΣΥΝΑΙΝΕΣΗ (Pinnacle closing, ≥8%) ===')
for nm in ('σταθερη ως 10η (τεστ)', 'σβηνει ως 11η'):
    new = HELD[nm]; G = {}
    for j in range(len(IDX)):
        if not (E10[j] and SE[j] in SEAS) or np.isnan(PRC[j, 3]): continue
        so, eo_, po_ = pick(base[j], j); sn, en_, pn_ = pick(new[j], j)
        a, b = eo_ >= 0.08, en_ >= 0.08
        if a and b and so == sn: G.setdefault(('ΚΑΙ ΤΑ ΔΥΟ', so), []).append((po_, SE[j]))
        else:
            if a: G.setdefault(('μονο ΠΑΛΙΟ', so), []).append((po_, SE[j]))
            if b: G.setdefault(('μονο ΝΕΟ', sn), []).append((pn_, SE[j]))
    P(f'  νεο = {nm}:')
    for grp in ('ΚΑΙ ΤΑ ΔΥΟ', 'μονο ΠΑΛΙΟ', 'μονο ΝΕΟ'):
        cells = []
        for sd in ('over', 'under'):
            L = G.get((grp, sd), [])
            cells.append(f"{sd} {np.mean([x[0] for x in L])*100:+.1f}% ({len(L)}) {sum(1 for s in SEAS if any(x[1] == s for x in L) and np.mean([x[0] for x in L if x[1] == s]) > 0)}/5" if L else f'{sd} —')
        L = G.get((grp, 'over'), []) + G.get((grp, 'under'), [])
        P(f'    {grp:11s}: ' + ' · '.join(cells) + (f' · ολα {np.mean([x[0] for x in L])*100:+.1f}% ({len(L)})' if L else ''))
# ---- C. γραμμη ανοιγματος (Crown) ----
P('')
ROWS = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ot'] == 6 and r['cid'] == 3 and r.get('t') == 23: ROWS[r['ngid']] = r['rows']
sched = []
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    try: sched += json.load(open(f'nowgoal_el/sched_{sea}.json', encoding='utf-8'))
    except FileNotFoundError: pass
tip_of = {}
Dt = pd.to_datetime(D.t, utc=True) if 't' in D.columns else pd.to_datetime(D.utc, utc=True)
key = {}
for j, i in enumerate(IDX):
    key.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append((j, Dt.values[i]))
OPEN = {}
for g in sched:
    if g.get('hs') is None or g['ngid'] not in ROWS: continue
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
    for j, tt in key.get((g['hs'], g['as_']), []):
        if abs(pd.Timestamp(tt).tz_localize(None) - tip) <= pd.Timedelta(hours=3):
            rows = sorted([x for x in ROWS[g['ngid']] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
            if len(rows) >= 2:
                OPEN[j] = dict(o=(rows[0][1], 1 + rows[0][2], 1 + rows[0][3]), c=(rows[-1][1], 1 + rows[-1][2], 1 + rows[-1][3]))
            break
sel = [j for j in OPEN if E10[j] and SE[j] in SEAS]
P(f'=== C. ΓΡΑΜΜΗ ΑΝΟΙΓΜΑΤΟΣ (Crown) — αγων 1-10: {len(sel)} ματς με ανοιγμα & κλεισιμο ===')
TO = np.array([OPEN[j]['o'][0] for j in sel]); TC = np.array([OPEN[j]['c'][0] for j in sel]); mv = TC - TO
P(f'  μεση |κινηση| ανοιγμα→κλεισιμο {np.mean(np.abs(mv)):.2f} π. · κινησεις σε {np.mean(np.abs(mv) > 0):.0%} των ματς')
for nm, v in (('ΠΑΛΙΟ', base), ('ΝΕΟ (σταθερη)', HELD['σταθερη ως 10η (τεστ)']), ('ΝΕΟ (σβηνει)', HELD['σβηνει ως 11η'])):
    d = np.array([v[j] for j in sel]) - TO
    b = np.polyfit(d, mv, 1)[0]; agree = np.mean(np.sign(mv[(np.abs(d) > 2) & (mv != 0)]) == np.sign(d[(np.abs(d) > 2) & (mv != 0)]))
    P(f'  {nm:15s}: η αγορα «υιοθετει» {b:+.3f} της διαφωνιας μας (ανοιγμα→κλεισιμο) · οταν διαφωνουμε >2π και κινειται: προς εμας {agree:.0%}')
P('  picks ≥8% στην τιμη ΑΝΟΙΓΜΑΤΟΣ Crown: κινηση γραμμης ως το κλεισιμο (+ = προς εμας) & ROI')
for nm, v in (('ΠΑΛΙΟ', base), ('ΝΕΟ (σταθερη)', HELD['σταθερη ως 10η (τεστ)']), ('ΝΕΟ (σβηνει)', HELD['σβηνει ως 11η'])):
    res = {'over': [], 'under': []}
    for j in sel:
        TL, ov, un = OPEN[j]['o']; s, e, p = pick(v[j], j, TL, ov, un)
        if e < 0.08: continue
        m_ = (OPEN[j]['c'][0] - TL) * (1 if s == 'over' else -1)
        res[s].append((m_, p))
    cells = [f"{sd}: κινηση {np.mean([x[0] for x in L]):+.2f} π. · ROI {np.mean([x[1] for x in L])*100:+.1f}% ({len(L)})" if L else f'{sd}: —' for sd, L in res.items()]
    P(f'    {nm:15s} ' + ' | '.join(cells))
open('el_preseason_totals_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
