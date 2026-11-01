"""
southam_t9_rules.py — 5/10/2026 ΟΜΑΔΑ 8 (Στελιος «τρεξτο»): ΚΑΝΟΝΕΣ PICKS χαντικαπ για Βραζιλια/MLS πανω στη v2 μηχανη (νεες κοκκινες).
Μηχανη: southam_phase3_rows_v2emps.csv (λ μοντελου + γραμμες Crown/SBOBET ανα χρονο).
Αγκυρα αγορας (οπως CORE7, core7_anchor): ανα λιγκα-σεζον, με τη σειρα των ματς, μετατοπιση ομαδας off[t]· μετα απο καθε ματς (αγων ≥7)
  off += 0.5·(υπεροχη τελικης αγορας Crown − υπεροχη μοντελου)/2 (± για γηπεδουχο/φιλοξ). Βαρος w: S = S0 + w·(S_αγκ − S0), w ∈ {0, 0.5, 1}.
Πλεγμα ανα λιγκα: ρολος (dog ≥+0.5 / φαβορι ≤−0.5) × παραθυρο (7-14 / 15+) × χρονος (ανοιγμα / 24ω / κλεισιμο) × τεταρτα (παλια p_cover / σωστα)
  × αγκυρα w × κατωφλι edge (6/8/10/12/14%) · τιμη 1.70-2.10.
ΑΞΙΟΛΟΓΗΣΗ: μοναδες & ROI ανα βιβλιο, σεζον θετικες (μεσος 2 βιβλιων). LOSO ανα (λιγκα, ρολος, παραθυρο, χρονος): η ρυθμιση (τεταρτα × w × κατωφλι)
  διαλεγεται απο τις αλλες σεζον (μοναδες, μεσος βιβλιων) → εκτος δειγματος.
ΠΡΟ-ΔΗΛΩΣΗ «ΥΠΟΨΗΦΙΟΣ ΚΑΝΟΝΑΣ» (για σκια, οχι live): LOSO εκτος δειγματος > 0 ΚΑΙ σε ≥(N−1)/N σεζον θετικο (Βραζ 3/4, MLS 5/6) ΚΑΙ ≥40 picks/βιβλιο.
"""
import sys, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
R = pd.read_csv('southam_phase3_rows_v2emps.csv', dtype={'mid': str, 'season': str})
R = R[R.per != '1-6'].copy()
# ---- αγκυρα: μαθαινει απο την τελικη Crown (msup) ----
CL = R[(R.win == 'close') & (R.book == 'Crown')].drop_duplicates('mid').set_index('mid')
first = R.drop_duplicates('mid').sort_values('ko')
OFF = {}
for (lg, sea), g in first.groupby(['league', 'season']):
    off = {}
    for r in g.itertuples():
        s = (r.lh_base - r.la_base) + off.get(r.home, 0.) - off.get(r.away, 0.)
        OFF[r.mid] = s
        if r.mid in CL.index and pd.notna(CL.at[r.mid, 'msup']):
            e = CL.at[r.mid, 'msup'] - s
            off[r.home] = off.get(r.home, 0.) + 0.5 * e / 2; off[r.away] = off.get(r.away, 0.) - 0.5 * e / 2
R['S0'] = R.lh_base - R.la_base; R['SA'] = R.mid.map(OFF); R['T'] = R.lh_base + R.la_base
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
_DD = {}
def dist(lh, la):
    k = (round(lh, 3), round(la, 3))
    if k not in _DD: _DD[k] = picks.gd_dist_dom(max(lh, .05), max(la, .05))
    return _DD[k]
rows = []
for r in R[R.win.isin(['open', '24h', 'close'])].itertuples():
    for w in (0.0, 0.5, 1.0):
        S = r.S0 + w * (r.SA - r.S0); d = dist((r.T + S) / 2, (r.T - S) / 2)
        for side, ln, o in ((1, r.ah, r.oh), (-1, -r.ah, r.oa)):
            if abs(ln) < 0.5 or not (1.70 <= o <= 2.10): continue
            role = 'dog' if ln > 0 else 'fav'
            pw, pp = picks.p_cover(d, side, ln); e_old = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            e_ok = 0.
            for L in parts(ln):
                a, b = picks.p_cover(d, side, L); e_ok += (a * (o - 1) * (1 - picks.MARGIN) - (1 - a - b)) / len(parts(ln))
            pnl = picks.settle(r.gd, side, ln, o)
            for q, e in (('παλια', e_old), ('σωστα', e_ok)):
                if e >= 0.06:
                    rows.append((r.league, r.season, r.book, r.win, r.per, role, q, w, e, pnl, r.mid))
B = pd.DataFrame(rows, columns=['league', 'season', 'book', 'win', 'per', 'role', 'q', 'w', 'edge', 'pnl', 'mid'])
B.to_pickle('southam_t9_bets.pkl')
THR = (0.06, 0.08, 0.10, 0.12, 0.14)
CFG = [(q, w, t) for q in ('παλια', 'σωστα') for w in (0.0, 0.5, 1.0) for t in THR]
def cell(d, q, w, t): return d[(d.q == q) & (d.w == w) & (d.edge >= t)]
def st(d, nse):
    if len(d) < 10: return f'n{len(d)//2:4d}' + ' ' * 22
    a = [d[d.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]; ps = d.groupby('season').pnl.mean()
    return f'n{len(d)//2:4d} {100*np.nanmean(a):+6.1f}% {d.pnl.sum()/2:+6.1f}u {int((ps > 0).sum())}/{nse}'
print('ΟΜΑΔΑ 8 — κανονες picks χαντικαπ (v2, νεες κοκκινες) · n = picks ανα βιβλιο · ROI/μοναδες μεσος Crown/SBOBET · σεζον θετικες')
summary = []
for lg in ('Brazil', 'MLS'):
    nse = R[R.league == lg].season.nunique()
    for role in ('dog', 'fav'):
        for per in ('7-14', '15+'):
            for win in ('open', '24h', 'close'):
                X = B[(B.league == lg) & (B.role == role) & (B.per == per) & (B.win == win)]
                if len(X) < 20: continue
                # LOSO
                seas = sorted(R[R.league == lg].season.unique()); oos = []; ch = []
                for s in seas:
                    tr = X[X.season != s]; te = X[X.season == s]
                    best = max(CFG, key=lambda c: cell(tr, *c).pnl.sum())
                    ch.append(best); oos.append(cell(te, *best).pnl.sum() / 2)
                cfg_mode = max(set(ch), key=ch.count)
                summary.append((lg, role, per, win, sum(oos), sum(x > 0 for x in oos), len(seas), cfg_mode, st(cell(X, *cfg_mode), nse),
                                st(cell(X, 'παλια' if role == 'dog' else 'σωστα', 0.0, 0.10), nse), oos))
print('\n λιγκα  ρολος παραθ. χρονος | LOSO εκτος δειγματος (σεζον θετικες) | συχνοτερη επιλογη → ολο το δειγμα | ΑΠΛΟΣ κανονας CORE7 (w0, ≥10%)')
for lg, role, per, win, so, pos, ns, cfg, s_cfg, s_base, oos in summary:
    tag = ''
    need = ns - 1
    nb = len(cell(B[(B.league == lg) & (B.role == role) & (B.per == per) & (B.win == win) & (B.book == 'Crown')], *cfg))
    if so > 0 and pos >= need and nb >= 40: tag = '  ← ΥΠΟΨΗΦΙΟΣ'
    print(f' {lg:6s} {role:4s} {per:5s} {win:6s} | {so:+6.1f}u ({pos}/{ns}) [{" ".join(f"{x:+.1f}" for x in oos)}] | '
          f'{cfg[0]} w{cfg[1]:.1f} ≥{int(cfg[2]*100)}% → {s_cfg} | {s_base}{tag}')
# ---- αναλυτικοι πινακες για τα 2 «καλα» κελια του ευρηματος (MLS dog 7-14) & 15+ dogs ----
print('\nΑΝΑΛΥΤΙΚΑ: MLS αουτσαιντερ 7-14 και 15+ — κατωφλι × αγκυρα (σωστα | παλια τεταρτα), κλεισιμο | ανοιγμα')
for per in ('7-14', '15+'):
    for win in ('close', 'open'):
        X = B[(B.league == 'MLS') & (B.role == 'dog') & (B.per == per) & (B.win == win)]
        print(f'  [MLS dog {per} {win}]')
        for w in (0.0, 0.5, 1.0):
            print(f'    αγκ {w:.1f}: ' + ' · '.join(f'≥{int(t*100)}% {st(cell(X, "παλια", w, t), 6).strip()}' for t in (0.06, 0.10, 0.14)))
