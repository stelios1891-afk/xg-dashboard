# -*- coding: utf-8 -*-
"""dom_bk_market.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ vs ΑΓΟΡΑ (2/10/2026, Στελιος «κατεβασε»): Ισπανια ACB + Ιταλια LBA.
Μοντελο = dom_bk_screen (walk-forward, box + τυχη, ΜΟΝΟ εγχωρια ματς) — η ιδια «ωμη» μηχανη που στην Ευρωλιγκα βγαζει 11.76 (αγορα 11.4).
Αγορα = Crown & Bet365 (Nowgoal, nowgoal_dom/odds.jsonl) · ΜΙΑ τιμη = μεσος των δυο βιβλιων (οπου υπαρχουν και τα δυο) · ανοιγμα & κλεισιμο.
Μετρα (οσες σεζον εχουν κατεβει): (1) λαθος μοντελου vs αγορας · (2) Κ2: κλιση b του (πραγματικο − αγορα) πανω στο (μοντελο − αγορα)
  (b ≥ 0.15 & t ≥ 2 = το μοντελο ξερει κατι που η αγορα δεν εχει) · (3) ROI χαντικαπ: (α) μοντελο μονο του σ 12.2, edge ≥8%,
  (β) μιξη 50% μοντελο / 50% αγορα, σ 12.3, edge ≥6% (οπως βρεθηκε στο EuroCup) · ανοιγμα & κλεισιμο Crown.
Σημειωση: ΠΡΩΤΗ ματια — καμια ρυθμιση πανω στα εγχωρια, οι ιδιες παραμετροι με την Ευρωλιγκα/EuroCup.
Εξοδος: dom_bk_market_out.txt"""
import sys, json, math, io, contextlib, collections, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
LGS = [a for a in sys.argv[1:]] or ['ACB', 'LBA']
src = open('dom_bk_screen.py', encoding='utf-8').read()
src = src.split("# ---- ΜΕΤΡΟ 2: προγραμμα ----")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace("for lg in L6 + ['EL', 'EC']:\n    pb, gn, info = run(lg, *E_box)", "for lg in [x for x in L6 if x in LGS_]:\n    pb, gn, info = run(lg, *E_box)")
NS = {'LGS_': LGS}
with contextlib.redirect_stdout(io.StringIO()):
    exec(src, NS)
G, PRED, act, NAME = NS['G'], NS['PRED'], NS['act'], NS['NAME']
N = NormalDist(); Phi = N.cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- Nowgoal → Flashscore (σκορ + ημερομηνια) ----
D = json.load(open('bk_domestic.json', encoding='utf-8'))
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_dom/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln); ROWS[r['ngid']][(r['t'], r['cid'])] = r['rows']
idx = collections.defaultdict(list)
for i in np.where(G.lg.isin(LGS).values)[0]:
    idx[(G.lg.values[i], int(G.hs.values[i]), int(G.as_.values[i]))].append(i)
def conv(rows, t, home_line=True):
    """γραμμη (σχηματος γηπεδουχου για χαντικαπ: −5.5 = δινει), τιμη1, τιμη2 (δεκαδικες) · ανοιγμα & κλεισιμο (μονο πριν το ματς)."""
    R = sorted([x for x in rows if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    if not R: return None
    f = lambda x: ((-x[1] if t == 21 else x[1]), 1 + x[2], 1 + x[3])
    return f(R[0]), f(R[-1])
MK = {}
for key, v in D.items():
    lg, sea = key.split('_')
    if lg not in LGS: continue
    for g in v['games']:
        ngid = int(g[0])
        if ngid not in ROWS: continue
        try: hs, as_ = int(g[4]), int(g[5])
        except Exception: continue
        dd = pd.Timestamp(g[1]).normalize()
        hit = next((i for i in idx.get((lg, hs, as_), []) if abs((G.t.values[i] - dd) / np.timedelta64(1, 'D')) <= 1.5), None)
        if hit is None: continue
        rec = {}
        for t in (21, 23):
            for cid in (3, 8):
                c = conv(ROWS[ngid].get((t, cid), []), t)
                if c: rec[(t, cid)] = c
        if (21, 3) in rec or (21, 8) in rec: MK[hit] = rec
P(f'αγορα αντιστοιχισμενη: {len(MK)} ματς · ' + ' · '.join(f"{lg} {sea}: {sum(1 for i in MK if G.lg.values[i] == lg and G.y.values[i] == int('20' + sea[:2]))}"
                                                               for lg in LGS for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26')))
def mu_of(L, o1, o2, s=12.2):
    ph = (1 / o1) / (1 / o1 + 1 / o2); return -L + s * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
def market(i, when):
    """ΜΙΑ τιμη: μεσος Crown/Bet365 της αναμενομενης διαφορας γηπεδουχου· γραμμη/τιμες Crown για ROI (αλλιως Bet365)."""
    mus = [mu_of(*MK[i][(21, c)][0 if when == 'o' else 1]) for c in (3, 8) if (21, c) in MK[i]]
    bk = MK[i].get((21, 3)) or MK[i].get((21, 8))
    return float(np.mean(mus)), bk[0 if when == 'o' else 1]
def cover(m, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((m + L - .5) / s); pl = Phi((-m - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m + L) / s); return pw, 0.0, 1 - pw
for lg in LGS:
    pb, gn = PRED[lg]
    ii = [i for i in MK if G.lg.values[i] == lg and np.isfinite(pb[i]) and G.y.values[i] >= 2021]
    if len(ii) < 50:
        P(f'\n{NAME[lg]}: λιγα ματς με αγορα ακομα ({len(ii)})'); continue
    yrs = sorted({int(G.y.values[i]) for i in ii})
    mc = np.array([market(i, 'c')[0] for i in ii]); mo = np.array([market(i, 'o')[0] for i in ii]); m = np.array([pb[i] for i in ii]); a = act[ii]
    yy = np.array([G.y.values[i] for i in ii]); gg = np.array([gn[i] for i in ii])
    P(f'\n=== {NAME[lg]} · {len(ii)} ματς · σεζον {[f"{y}-{(y + 1) % 100:02d}" for y in yrs]} ===')
    rm = lambda v, mm=None: float(np.sqrt(np.mean(((a - v) if mm is None else (a - v)[mm]) ** 2)))
    P(f'  ΛΑΘΟΣ: μοντελο {rm(m):.2f} · αγορα ανοιγμα {rm(mo):.2f} · κλεισιμο {rm(mc):.2f} · διαφορα μοντελου απο κλεισιμο {rm(m) - rm(mc):+.2f}'
      f'  (Ευρωλιγκα ιδια μηχανη: +0.36 · EuroCup: +0.7)')
    for lab, msk in (('αγων 1-5', gg <= 5), ('6-15', (gg >= 6) & (gg <= 15)), ('16+', gg >= 16)):
        if msk.sum() >= 30: P(f'    {lab:9s} n {msk.sum():4d} · μοντελο {rm(m, msk):.2f} · κλεισιμο {rm(mc, msk):.2f}')
    x = m - mc; z = a - mc
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = {y: np.polyfit(x[yy == y], z[yy == y], 1)[0] for y in yrs if (yy == y).sum() > 30}
    P(f'  Κ2 (ξερει κατι που δεν εχει το κλεισιμο;): b {b:+.3f} (t {b/se:+.1f}) · ανα σεζον ' + ' '.join(f'{str(y)[-2:]}:{v:+.2f}' for y, v in per.items())
      + ('  → ΝΑΙ' if b >= .15 and b / se >= 2 else '  → οχι'))
    for lab, w, sg, thr in (('μοντελο μονο του (σ 12.2, ≥8%)', 1.0, 12.2, .08), ('μιξη 50/50 με αγορα (σ 12.3, ≥6%)', 0.5, 12.3, .06)):
        cells = []
        for when in ('o', 'c'):
            R = []
            for k, i in enumerate(ii):
                mk_mu, (L, o1, o2) = market(i, when)
                mm = mk_mu + w * (m[k] - mk_mu)
                pw, pp, pl = cover(mm, L, sg)
                e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e >= thr:
                    v = (a[k] + L) * side; R.append(((od - 1) if v > 0 else (0 if v == 0 else -1), yy[k]))
            ar = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R))
            pos = sum(1 for y in ys if np.mean([q[0] for q in R if q[1] == y]) > 0)
            cells.append(f'{"ανοιγμα" if when == "o" else "κλεισιμο"} {ar.mean()*100 if len(ar) else 0:+.1f}% ({len(ar)}, {ar.sum():+.1f}u, {pos}/{len(ys)})')
        P(f'  ROI {lab}: ' + ' · '.join(cells))
open('dom_bk_market_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
