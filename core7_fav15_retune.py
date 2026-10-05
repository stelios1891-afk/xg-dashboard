"""
core7_fav15_retune.py — 5/10/2026 (Στελιος «τρεξτο»): ΦΑΒΟΡΙ 15+ με τη ΝΕΑ φορμουλα κοκκινων — ισχυουν ακομα οι ρυθμισεις;
Μηχανη = live (σωστο SoS 0.75 @7-14, κοκκινες red_modes 'emps' → core7_mech_preds_cur_0.75_6_13~emps.csv), ιδια μηχανη picks με
core7_sos15_final (αγκυρα μαθαινει απο 7η, σωστα τεταρτα, 1.70-2.10, γραμμη ≤ −0.5, αγωνιστικες 15+), κλεισιμο Pinnacle/Crown/Bet365.
Πλεγμα: αγκυρα w ∈ {0.5, 0.7 (σημερα), 1.0} × κατωφλι edge ∈ {8, 10 (σημερα), 12, 13%} × ταβανι ∈ {κανενα, 15%, 13%}.
ΠΡΟ-ΔΗΛΩΣΗ: μια ρυθμιση αντικαθιστα τη σημερινη (w .7, ≥10%, χωρις ταβανι) ΜΟΝΟ αν ΚΑΙ ΤΑ ΤΡΙΑ:
  (1) μοναδες > σημερα σε ≥2/3 βιβλια · (2) θετικη σε ≥3/4 σεζον (μεσος 3 βιβλιων) · (3) LOSO: η επιλογη απο τις αλλες 3 σεζον
  (κριτηριο: μοναδες, μεσος 3 βιβλιων) βγαζει εκτος δειγματος περισσοτερες μοναδες απο τη σημερινη. Αλλιως τιποτα δεν αλλαζει.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read()
pre = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'fav15rt'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, run_L, load, NG, ev_ok, picks, I15, SEAS = g['D'], g['run_L'], g['load'], g['NG'], g['ev_ok'], g['picks'], g['I15'], g['SEAS']
xh, xa, _ = load('cur_0.75_6_13~emps'); D['xh'] = xh; D['xa'] = xa
S0, SA = run_L(0, 0, 6), run_L(0.5, 0, 6); T = xh + xa
rows = []
for w in (0.5, 0.7, 1.0):
    S = S0 + w * (SA - S0)
    for i in I15:
        r = D.loc[i]
        quotes = [('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None)]
        for bk in ('Crown', 'Bet365'):
            q = NG.get((r.mid, bk)); quotes.append((bk, q[1] if q else None))
        dist = picks.gd_dist_dom(max((T[i] + S[i]) / 2, .05), max((T[i] - S[i]) / 2, .05))
        for bk, q in quotes:
            if q is None or q[0] != q[0]: continue
            L, oh, oa = q
            if abs(L) < 0.5: continue
            side = 1 if L < 0 else -1; ud = -abs(L); o = oh if side == 1 else oa
            if not (1.70 <= o <= 2.10): continue
            e = ev_ok(dist, side, ud, o)
            if e >= 0.05:
                rows.append(dict(w=w, book=bk, season=r.season, mid=r.mid, edge=e, line=ud, pnl=picks.settle(r.gd, side, ud, o)))
C = pd.DataFrame(rows)
BK = ('Pinnacle', 'Crown', 'Bet365')
GRID = [(w, lo, hi) for w in (0.5, 0.7, 1.0) for lo in (0.08, 0.10, 0.12, 0.13) for hi in (9, 0.15, 0.13) if hi > lo]
def sel(w, lo, hi, d=C): return d[(d.w == w) & (d.edge >= lo) & (d.edge < hi)]
def lab(w, lo, hi): return f'αγκ {w:.1f} · edge ≥{int(lo*100)}%' + (f' <{int(hi*100)}%' if hi < 9 else '')
NOW = (0.7, 0.10, 9)
print('ΦΑΒΟΡΙ 15+ με ΝΕΕΣ κοκκινες — μοναδες (ROI) σεζον-θετικες · Pinnacle | Crown | Bet365 · μεσος 3 βιβλιων')
tab = []
for k in GRID:
    x = sel(*k); cells = []; u3 = []
    for bk in BK:
        y = x[x.book == bk]; ps = y.groupby('season').pnl.mean()
        cells.append(f'n{len(y):3d} {y.pnl.sum():+6.1f}u ({100*y.pnl.mean():+5.1f}%) {int((ps > 0).sum())}/4' if len(y) else 'n  0')
        u3.append(y.pnl.sum())
    ps3 = x.groupby('season').pnl.mean()
    tab.append((k, np.mean(u3), u3, int((ps3 > 0).sum())))
    print(f'  {lab(*k):30s}{" ← ΣΗΜΕΡΑ" if k == NOW else "         "} ' + ' | '.join(cells) + f' · μεσος {np.mean(u3):+6.1f}u · σεζον {int((ps3 > 0).sum())}/4')
# ζωνες edge (w .7)
print('\nΖΩΝΕΣ EDGE (αγκυρα 0.7) — μοναδες ανα βιβλιο:')
for lo, hi in ((0.05, 0.08), (0.08, 0.10), (0.10, 0.13), (0.13, 0.18), (0.18, 9)):
    x = sel(0.7, lo, hi)
    print(f'  {int(lo*100)}-{int(hi*100) if hi < 9 else "∞"}%: ' + ' | '.join(f'n{len(x[x.book == b]):3d} {x[x.book == b].pnl.sum():+5.1f}u' for b in BK)
          + ' · ανα σεζον (Pinnacle) ' + ' '.join(f'{s}:{x[(x.book == "Pinnacle") & (x.season == s)].pnl.sum():+.1f}' for s in SEAS))
# LOSO
print('\nLOSO (επιλογη με μοναδες, μεσος 3 βιβλιων, απο τις αλλες 3 σεζον):')
gain = []
for s in SEAS:
    tr = C[C.season != s]; te = C[C.season == s]
    best = max(GRID, key=lambda k: np.mean([sel(*k, tr)[sel(*k, tr).book == b].pnl.sum() for b in BK]))
    ob = np.mean([sel(*best, te)[sel(*best, te).book == b].pnl.sum() for b in BK]); on = np.mean([sel(*NOW, te)[sel(*NOW, te).book == b].pnl.sum() for b in BK])
    gain.append(ob - on); print(f'  {s}: διαλεγει «{lab(*best)}» → εκτος δειγματος {ob:+.1f}u vs σημερα {on:+.1f}u ({ob - on:+.1f})')
print(f'  ΣΥΝΟΛΟ LOSO vs σημερα: {sum(gain):+.1f}u · καλυτερο σε {sum(x > 1e-9 for x in gain)}/4 σεζον')
# ΚΡΙΣΗ
now = [t for t in tab if t[0] == NOW][0]
print('\nΚΡΙΣΗ (προ-δηλωμενη): ρυθμισεις που περνουν (1) ≥2/3 βιβλια καλυτερα ΚΑΙ (2) ≥3/4 σεζον:')
cand = [t for t in tab if t[0] != NOW and sum(a > b for a, b in zip(t[2], now[2])) >= 2 and t[3] >= 3]
for t in sorted(cand, key=lambda t: -t[1]):
    print(f'  {lab(*t[0]):30s} μεσος {t[1]:+.1f}u (σημερα {now[1]:+.1f}u)')
print(f'  (3) LOSO συνολο {sum(gain):+.1f}u → ' + ('ΑΛΛΑΓΗ υποψηφια (αν ταιριαζει με τα (1)-(2))' if sum(gain) > 0 else 'ΚΑΜΙΑ ΑΛΛΑΓΗ — οι σημερινες ρυθμισεις μενουν'))
