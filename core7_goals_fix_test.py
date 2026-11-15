"""
core7_goals_fix_test.py — ΤΕΣΤ 1/10/2026 (Στελιος «τρεξτα»): ΦΑΣΗ 2 — λυσεις για το χασμα γκολ (core7_goals_gap_diag: συμπιεση εκτασης,
φαβορι υποτιμημενα, επιπεδο −0.06 σε 7-14 & 26+, πολλα 0-0). Βαση: core7_goals_gap_rows.csv (αγων. 7+, 4 σεζον, Crown κλεισιμο συνολου).
ΕΚΔΟΧΕΣ (ολες οι παραμετροι LOSO: εκτιμωνται στις ΑΛΛΕΣ 3 σεζον):
  Λ1 «απλωμα»: T' = a + k·T (γκολ ~ T μοντελου)· υπεροχη ιδια
  Λ2 ανα πλευρα: γκολ_φαβ = a1 + k1·λ_φαβ, γκολ_ντογκ = a2 + k2·λ_ντογκ (φαβ/ντογκ κατα ΜΟΝΤΕΛΟ)
  Λ3 επιπεδο ανα περιοδο: T × c_περιοδου (7-14 / 15-25 / 26+)
  Λ4 αγκυρα συνολων: καθε ομαδα διορθωση o· T' = T + o_h + o_a· μετα το ματς e = T_αγορας − T' → o_h,o_a += λ·e/2 (μαθηση md≥6) λ .2/.5
  Λ5 = Λ2 + Λ3 · Λ6 = Λ2 + Λ4(.2)
  Μ  μηχανισμοι εισοδου (μονο 15+, παλια=νεα μηχανη): χωρις συμπιεση · πεναλτι .76 · και τα δυο · αμυνα 50% γκολ
ΜΕΤΡΑ: LL = μεση log-πιθανοτητα του ΠΡΑΓΜΑΤΙΚΟΥ συνολου γκολ (Dixon-Coles), Brier over 2.5, χασμα Q5 & μεγαλων φαβορι,
  b = πληροφορια περα απο την αγορα, ROI over/under (Crown & Bet365 κλεισιμο, 1.70-2.10, edge ≥10%) στις 15+.
ΠΡΟ-ΔΗΛΩΣΗ: ΑΚΡΙΒΕΣΤΕΡΟ αν LL > σημερα σε ≥3/4 σεζον. ΥΠΟΨΗΦΙΟ ΣΤΟΙΧΗΜΑΤΟΣ μονο αν επιπλεον b > 0 με t ≥ 2 Ή ROI over/under 15+
  > 0 ΚΑΙ στα 2 βιβλια με ≥3/4 σεζον (Crown) και n ≥ 40. Δεν αλλαζει τιποτα live.
"""
import sys, os, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str}).sort_values(['league', 'date']).reset_index(drop=True)
SEAS = sorted(W.season.unique())
W['win'] = np.where(W.md >= 25, '26+', np.where(W.md >= 14, '15-25', '7-14'))
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
    except Exception: return None
NG = {}
mids = set(W.mid)
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ou') or str(r['mid']) not in mids: continue
        best = None
        for mt, ov, gl, un in r['ou']:
            L = pl(gl)
            try: oo, uu = float(ov) + 1, float(un) + 1
            except (TypeError, ValueError): continue
            if L is None or mt is None or oo <= 1 or uu <= 1: continue
            if best is None or mt > best[0]: best = (mt, L, oo, uu)
        if best: NG[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = best[1:]
def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05)); d = np.zeros(25)
    for i in range(13):
        for j in range(13): d[i + j] += M[i, j]
    return d
def evaluate(lh, la, lab):
    T = lh + la; ll = np.zeros(len(W)); bo = np.zeros(len(W)); rows = []
    for i, r in enumerate(W.itertuples()):
        d = tdist(lh[i], la[i]); tg = int(r.tg); ll[i] = np.log(max(d[tg], 1e-12)); po = d[3:].sum(); bo[i] = (po - (tg > 2)) ** 2
        if r.md >= 14:
            for bk in ('Crown', 'Bet365'):
                q = NG.get((r.mid, bk))
                if not q: continue
                L, oo, uu = q; parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
                for over, o in ((True, oo), (False, uu)):
                    if not (1.70 <= o <= 2.10): continue
                    e = s_ = 0
                    for x in parts:
                        ks = np.arange(25); pw = d[(ks > x + .01) if over else (ks < x - .01)].sum(); pp = d[np.abs(ks - x) < .01].sum()
                        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
                        m = (tg - x) if over else (x - tg); s_ += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
                    if e >= 0.10: rows.append((bk, r.season, 'OVER' if over else 'UNDER', s_))
    X = np.column_stack([np.ones(len(W)), W.T_mkt.values, T - W.T_mkt.values]); y = W.tg.values.astype(float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / (len(y) - 3)); tb = b[2] / np.sqrt(cov[2, 2])
    fav = np.where(W.fav_home, lh, la); big = (W.s_mkt.abs() >= 1.2).values
    q5 = (W.T_mkt >= W.T_mkt.quantile(.8)).values
    return dict(lab=lab, ll=ll, bo=bo, T=T, b=b[2], tb=tb, q5=T[q5].mean() - W.tg.values[q5].mean(),
                favbig=fav[big].mean() - W.g_fav.values[big].mean(), lvl=T.mean() - W.tg.mean(),
                ou=pd.DataFrame(rows, columns=['book', 'season', 'side', 'pnl']))
xh0, xa0 = W.xh.values.copy(), W.xa.values.copy(); T0 = xh0 + xa0; s0 = xh0 - xa0
def with_T(Tn): return np.maximum((Tn + s0) / 2, .05), np.maximum((Tn - s0) / 2, .05)
def loso(fit, apply):
    out = np.zeros(len(W))
    for se in SEAS:
        tr = (W.season != se).values; te = ~tr; p = fit(tr); out[te] = apply(p, te)[te] if np.ndim(apply(p, te)) else apply(p, te)
    return out
def fitlin(x, y):
    X = np.column_stack([np.ones(len(x)), x]); return np.linalg.lstsq(X, y, rcond=None)[0]
R = [evaluate(xh0, xa0, 'ΣΗΜΕΡΑ')]
# Λ1
Tn = np.zeros(len(W))
for se in SEAS:
    tr = (W.season != se).values; a, k = fitlin(T0[tr], W.tg.values[tr]); Tn[~tr] = a + k * T0[~tr]
R.append(evaluate(*with_T(Tn), 'Λ1 απλωμα')); T_L1 = Tn
# Λ2
favm = xh0 >= xa0; lf = np.where(favm, xh0, xa0); ld = np.where(favm, xa0, xh0)
gf = np.where(favm, W.hg, W.ag).astype(float); gd_ = np.where(favm, W.ag, W.hg).astype(float)
nf, nd = np.zeros(len(W)), np.zeros(len(W))
for se in SEAS:
    tr = (W.season != se).values
    a1, k1 = fitlin(lf[tr], gf[tr]); a2, k2 = fitlin(ld[tr], gd_[tr]); nf[~tr] = a1 + k1 * lf[~tr]; nd[~tr] = a2 + k2 * ld[~tr]
    print(f'  Λ2 fold {se}: φαβ {a1:+.2f} + {k1:.2f}·λ · ντογκ {a2:+.2f} + {k2:.2f}·λ')
L2h, L2a = np.maximum(np.where(favm, nf, nd), .05), np.maximum(np.where(favm, nd, nf), .05)
R.append(evaluate(L2h, L2a, 'Λ2 ανα πλευρα'))
# Λ3
def phase(h, a):
    c = np.ones(len(W))
    for se in SEAS:
        tr = (W.season != se).values
        for w in ('7-14', '15-25', '26+'):
            m = (W.win == w).values
            c[~tr & m] = W.tg.values[tr & m].sum() / (h + a)[tr & m].sum()
    return h * c, a * c
R.append(evaluate(*phase(xh0, xa0), 'Λ3 επιπεδο/περιοδο'))
# Λ4
def tanchor(h, a, lam):
    T = h + a; out = T.copy()
    for lg, idx in W.groupby('league').groups.items():
        off = {}; cur = None
        for i in idx:
            r = W.loc[i]
            if r.season != cur: off = {}; cur = r.season
            t = T[i] + off.get(r.h, 0) + off.get(r.a, 0); out[i] = t
            if r.md >= 6:
                e = r.T_mkt - t; off[r.h] = off.get(r.h, 0) + lam * e / 2; off[r.a] = off.get(r.a, 0) + lam * e / 2
    s = h - a; return np.maximum((out + s) / 2, .05), np.maximum((out - s) / 2, .05)
for lam in (0.2, 0.5): R.append(evaluate(*tanchor(xh0, xa0, lam), f'Λ4 αγκυρα συνολων {lam}'))
R.append(evaluate(*phase(L2h, L2a), 'Λ5 = Λ2 + Λ3'))
R.append(evaluate(*tanchor(L2h, L2a, 0.2), 'Λ6 = Λ2 + Λ4(.2)'))
# αναφορα: η ιδια η αγορα
R.append(evaluate(np.maximum((W.T_mkt + W.s_mkt).values / 2, .05), np.maximum((W.T_mkt - W.s_mkt).values / 2, .05), '[ΑΓΟΡΑ]'))
base = R[0]
def show(RR, mask=None, title=''):
    print(f'\n{title}')
    for x in RR:
        m = np.ones(len(W), bool) if mask is None else mask
        ll = x['ll'][m]; better = sum(ll[W.season.values[m] == s].mean() > base['ll'][m][W.season.values[m] == s].mean() + 1e-12 for s in SEAS)
        o = x['ou']; cells = []
        for bk in ('Crown', 'Bet365'):
            y = o[o.book == bk]; cells.append(f'n{len(y):4d} {100*y.pnl.mean() if len(y) else 0:+5.1f}%' + (f' {int((y.groupby("season").pnl.mean() > 0).sum())}/4' if len(y) else ''))
        print(f'  {x["lab"]:22s} LL {ll.mean():.5f} (Δ {1e4*(ll.mean() - base["ll"][m].mean()):+6.1f}×10⁻⁴, {better}/4) · Brier>2.5 {x["bo"][m].mean():.4f} · '
              f'επιπεδο {x["lvl"]:+.3f} · Q5 {x["q5"]:+.3f} · μεγ.φαβ {x["favbig"]:+.3f} · b {x["b"]:+.2f} (t {x["tb"]:+.1f}) · O/U 15+ ≥10%: Crown {cells[0]} | B365 {cells[1]}')
show(R, None, 'ΟΛΑ (αγων. 7+) — LL μεγαλυτερο = καλυτερο · σε ( ) σεζον καλυτερες απο σημερα')
show(R, (W.md >= 14).values, 'ΜΟΝΟ 15+ (LL/Brier), λοιπα μετρα ολα τα ματς')
# Μ μηχανισμοι 15+
key = ['league', 'season', 'h', 'a', 'date']
M15 = (W.md >= 14).values
RM = [dict(base, lab='ΣΗΜΕΡΑ')]
for lab, v in (('χωρις συμπιεση', 'nocomp'), ('πεναλτι 0.76', 'pen76'), ('και τα δυο', 'both'), ('αμυνα 50% γκολ', 'd50')):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str})[['mid', 'xg_h', 'xg_a']]
    m = W[['mid']].merge(P, on='mid', how='left')
    h = np.where(M15, m.xg_h.clip(.05, 6).values, xh0); a = np.where(M15, m.xg_a.clip(.05, 6).values, xa0)
    RM.append(evaluate(h, a, lab))
show(RM, M15, 'Μ. ΜΗΧΑΝΙΣΜΟΙ ΕΙΣΟΔΟΥ — μονο 15+ (αλλαγμενα μονο τα 15+ ματς)')
print('\nΚΡΙΣΗ (ολα 7+):')
for x in R[1:-1]:
    better = sum(x['ll'][(W.season == s).values].mean() > base['ll'][(W.season == s).values].mean() for s in SEAS)
    o = x['ou']; bet = x['tb'] >= 2 and x['b'] > 0
    cr, b3 = o[o.book == 'Crown'], o[o.book == 'Bet365']
    if len(cr) >= 40 and cr.pnl.mean() > 0 and len(b3) and b3.pnl.mean() > 0 and int((cr.groupby('season').pnl.mean() > 0).sum()) >= 3: bet = True
    print(f'  {x["lab"]:22s} ακριβεια {"✓" if better >= 3 else "✗"} ({better}/4) · στοιχημα {"✓ ΥΠΟΨΗΦΙΟ" if (better >= 3 and bet) else "✗"}')
