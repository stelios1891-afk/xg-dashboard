# -*- coding: utf-8 -*-
"""el_market_prior_test.py — ΤΕΣΤ: «μαθαινω τις μεταγραφες απο την αγορα» στο χαντικαπ (25/9/2026, αιτημα Στελιου:
Ζαλγκιρις πηρε Βαλαντσιουνα, Μπαρτσα/Βαλενθια αποδυναμωθηκαν, Ολυμπιακος υποτιμημενος — «πρεπει να προσαρμοστουμε»).

ΙΔΕΑ: οι closing γραμμες Pinnacle των ματς που ΗΔΗ παιχτηκαν φετος δειχνουν ποσο δυνατη θεωρει η αγορα καθε ομαδα
(μαζι με οσα ξερει για μεταγραφες/απουσιες). Πριν απο καθε ματς:
  rating αγορας = ridge πανω στις γραμμες των προηγουμενων ματς της σεζον (γραμμη γηπ = εδρα + R_γηπ − R_φιλ, ουδετερα χωρις εδρα)
  προβλεψη = v1 + W × (προβλεψη αγορας − v1)   μονο στις αγωνιστικες ≤ R_END (μετα: σκετο v1)
  (1η αγωνιστικη: καμια γραμμη ακομα → σκετο v1. Η γραμμη του ΙΔΙΟΥ ματς δεν χρησιμοποιειται ποτε.)
ΠΛΕΓΜΑ: W {0.25, 0.5, 0.75, 1.0} × R_END {6, 10, ολη η σεζον} × ridge λ {2, 5}  (+ v1 = W 0)
ΕΠΙΛΟΓΗ: LOSO — για καθε σεζον-εξω διαλεγεται ο συνδυασμος με το καλυτερο ROI (edge ≥5%) στις αλλες 5.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΜΙΑ εκτελεση): ΠΕΡΝΑ αν στα ενωμενα held-out, σε σχεση με v1:
  ROI μεγαλυτερο σε edge ≥5% ΚΑΙ ≥8% ΚΑΙ ≥10%, με κερδοφορες σεζον οχι λιγοτερες (ιδιο σε καθε οριο).
Αναφορα (οχι κριτηριο): μοναδες, b, αγωνιστικες 2-10 χωριστα. Κανονικη περιοδος, χαντικαπ, Pinnacle closing 2020-25.
Εξοδος: el_market_prior_test_out.txt"""
import sys, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o = []
src = open('el_roi_v2.py', encoding='utf-8').read().split("P('Edge = P")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o
def P(s=''):
    print(s, flush=True); out.append(str(s))

# αγωνιστικη ≈ ματς κανονικης περιοδου που εχει παιξει η ομαδα με τα περισσοτερα +1
rs_all = D[D.phase == 'RS'].sort_values('date'); cnt, gno = {}, {}
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    gno[i] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
RND = np.array([gno.get(i, 99) for i in IDX])
NEU = (D.ff.values | D.relocated.values)[IDX]
DATE = D.date.values[IDX]; HOME = D.home.values[IDX]; AWAY = D.away.values[IDX]
dnum = np.array([(pd.Timestamp(d) - pd.Timestamp(DATE.min())).days for d in DATE])

def market_pred(lam):
    """για καθε ματς: διαφορα γηπεδουχου κατα την αγορα, απο τις γραμμες ΜΟΝΟ των προηγουμενων ημερων της σεζον (nan αν δεν υπαρχουν)."""
    mp = np.full(len(IDX), np.nan)
    for s in EVAL:
        js = np.where(SE == s)[0]
        teams = sorted(set(HOME[js]) | set(AWAY[js])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        for d in np.unique(dnum[js]):
            past = js[dnum[js] < d]; cur = js[dnum[js] == d]
            if len(past) < 3: continue
            A = np.zeros((len(past) + n, 1 + n)); y = np.zeros(len(past) + n)
            for r, j in enumerate(past):
                A[r, 0] = 0.0 if NEU[j] else 1.0; A[r, 1 + ix[HOME[j]]] = 1; A[r, 1 + ix[AWAY[j]]] = -1; y[r] = MM[j]
            A[len(past) + np.arange(n), 1 + np.arange(n)] = np.sqrt(lam)
            x = np.linalg.lstsq(A, y, rcond=None)[0]
            hm = x[0] if x[0] > 0 else 3.0
            for j in cur:
                mp[j] = (0.0 if NEU[j] else hm) + x[1 + ix[HOME[j]]] - x[1 + ix[AWAY[j]]]
    return mp
MP = {lam: market_pred(lam) for lam in (2, 5)}
GRID = list(itertools.product([0.25, 0.5, 0.75, 1.0], [6, 10, 99], [2, 5]))
def pred(c):
    W, R_END, lam = c; mp = MP[lam]
    use = (RND <= R_END) & ~np.isnan(mp)
    return np.where(use, M_V1 + W * (np.nan_to_num(mp) - M_V1), M_V1)
def sp(m):
    b = bets(m, T_LO); b = b[b.mkt == 'sp'].copy()
    jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
    b['rnd'] = RND[jj]; return b
BV1 = sp(M_V1); BG = {c: sp(pred(c)) for c in GRID}
SS = [s for s in EVAL if (BV1.season == s).sum() >= 30]

def roi(b, thr, seasons):
    x = b[(b.edge >= thr) & b.season.isin(seasons)]
    return x.p.mean() if len(x) else -9
held = []
P('=== LOSO επιλογη (ROI edge ≥5% στις αλλες 5 σεζον) ===')
for s in SS:
    tr = [t for t in SS if t != s]
    best = max(GRID, key=lambda c: roi(BG[c], 0.05, tr))
    b = BG[best]; held.append(b[b.season == s])
    P(f'  {s[-4:]} εξω: W {best[0]} · εως αγων {best[1] if best[1] < 99 else "ολη"} · λ {best[2]} → ROI εξω {roi(b, .05, [s])*100:+.1f}% vs v1 {roi(BV1, .05, [s])*100:+.1f}%')
H = pd.concat(held)
def cell(x):
    return f'{x.p.mean()*100:+5.1f}% ({len(x)}, {x.p.sum():+.1f}u)' if len(x) else '—'
P('')
P('=== ΑΠΟΤΕΛΕΣΜΑ (ενωμενα held-out) ===')
ok = True
for thr in (0.03, 0.05, 0.08, 0.10, 0.15):
    a, v = H[H.edge >= thr], BV1[BV1.edge >= thr]
    pa = sum(1 for s in SS if len(a[a.season == s]) and a[a.season == s].p.mean() > 0)
    pv = sum(1 for s in SS if len(v[v.season == s]) and v[v.season == s].p.mean() > 0)
    if thr in (0.05, 0.08, 0.10): ok &= (a.p.mean() > v.p.mean()) and pa >= pv
    P(f'  edge ≥{thr*100:2.0f}%: με αγορα {cell(a)} {pa}/6 · v1 {cell(v)} {pv}/6')
P('')
P('  μονο αγωνιστικες 2-10 (εκει που αλλαζει κατι), edge ≥5%:')
P(f'    με αγορα {cell(H[(H.edge >= .05) & (H.rnd >= 2) & (H.rnd <= 10)])} · v1 {cell(BV1[(BV1.edge >= .05) & (BV1.rnd >= 2) & (BV1.rnd <= 10)])}')
P('')
P('  (αναφορα) καθε συνδυασμος σε ολες τις σεζον, edge ≥5% / ≥8%:')
for c in GRID:
    b = BG[c]; P(f'    W {c[0]:<4} εως {str(c[1]) if c[1] < 99 else "ολη":>4} λ {c[2]}: {cell(b[b.edge >= .05])} · {cell(b[b.edge >= .08])}')
P('')
P(f'→ {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ — μενει το v1"}')
open('el_market_prior_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
