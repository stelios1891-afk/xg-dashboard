"""
intl_gd_fix_eval.py — ΑΞΙΟΛΟΓΗΣΗ ΔΙΟΡΘΩΣΗΣ ΚΑΤΑΝΟΜΗΣ ΔΙΑΦΟΡΑΣ ΓΚΟΛ (25/9/2026, εντολη Στελιου «διορθωσε τα χαντικαπ αουτσαιντερ»).
Διαγνωση: στα Μ1/Μ3 η υπεροχη = 0.49 γκολ/100 Elo μετρημενο ΧΩΡΙΣ αξια, εφαρμοζεται σε Elo+αξια (σωστη κλιση ~0.43) → φαβορι μεσο +1.50 vs +1.29,
«+3 και πανω» 47% vs 37% στα μεγαλα φαβορι· σε κοντινα ματς η κατανομη πολυ «απλωμενη».
Εκδοχες (intl_window_test.py GD_FIX): none (live) · slope = κλιση ανα μοντελο (LOSO) · shape = slope + κοινα γκολ λ3 (LOSO με log-likelihood διαφορας γκολ).
ΠΡΟ-ΔΗΛΩΣΗ (πριν δω αποτελεσματα):
  (1) ΑΚΡΙΒΕΙΑ: log-likelihood πραγματικης διαφορας γκολ (αγωνιστικα, LOSO) καλυτερη απο none σε ≥4/5 σεζον, για καθε μοντελο.
  (2) PICKS (72ω, σωστα τεταρτα, Crown ΚΑΙ SBOBET): συναινεση ≥2/3 ROI οχι χειροτερο · dogs ROI καλυτερο · φαβορι ROI οχι κατω απο −1 μοναδα.
  Περνα = (1) ΚΑΙ (2). Αν περνουν και οι δυο, προτιμαται η απλουστερη (slope) εκτος αν η shape ειναι καλυτερη στο (1) ΚΑΙ στο (2).
"""
import sys, math, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'ev'}
exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, MODELS, picks, T_of, A_GOAL = (G[k] for k in ('D', 'MODELS', 'picks', 'T_of', 'A_GOAL'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]; SEAS = sorted(C.season.unique())
def ll(sub, m, a, l3):
    t = 0.0
    for r in sub.itertuples():
        d = getattr(r, f'd_{m}'); T = T_of(d, r)
        if a is None:          # none = live (0.49 για ολα, χωρις λ3) — ιδιο με intl_window_test
            s = A_GOAL * d; lh, la = max((T + s) / 2, .15), max((T - s) / 2, .15)
        else:
            s = a * d; lh, la = max((T + s) / 2 - l3, .10), max((T - s) / 2 - l3, .10)
        t += math.log(max(picks.gd_dist(lh, la).get(int(r.gd), 1e-9), 1e-9))
    return t / len(sub)
P('(1) ΑΚΡΙΒΕΙΑ — μεσο log-likelihood πραγματικης διαφορας γκολ ανα ματς (μεγαλυτερο = καλυτερο), LOSO')
res = {}
for m in MODELS:
    rows = []
    for sea in SEAS:
        tr, te = C[C.season != sea], C[C.season == sea]
        dd = tr[f'd_{m}'].values.astype(float); a = float(np.sum(dd * tr.gd.values) / np.sum(dd ** 2))
        l3 = max(np.arange(0, 0.61, 0.05), key=lambda z: ll(tr, m, a, z) * len(tr))
        rows.append((sea, ll(te, m, None, 0), ll(te, m, a, 0.0), ll(te, m, a, l3)))
    R = pd.DataFrame(rows, columns=['σεζον', 'none', 'slope', 'shape'])
    n = [len(C[C.season == s]) for s in SEAS]; w = np.array(n) / sum(n)
    tot = {k: float(np.sum(R[k] * w)) for k in ('none', 'slope', 'shape')}
    bs = int((R.slope > R.none).sum()); bh = int((R['shape'] > R.none).sum())
    res[m] = (bs >= 4, bh >= 4)
    P(f'  {m}: none {tot["none"]:.4f} · slope {tot["slope"]:.4f} ({bs}/5) · shape {tot["shape"]:.4f} ({bh}/5) · ανα σεζον: '
      + ' · '.join(f"{r.σεζον}: {r.none:.3f}/{r.slope:.3f}/{r.shape:.3f}" for r in R.itertuples()))
P('\n(2) PICKS — 72ω, σωστα τεταρτα (n / ROI / θετικες σεζον / μοναδες)')
F = {'none': 'intl_window_test_proper_ahproper_bets.csv', 'slope': 'intl_window_test_proper_ahproper_gdslope_bets.csv', 'shape': 'intl_window_test_proper_ahproper_gdshape_bets.csv'}
def cons(b):
    b = b[b.model.isin(['M1', 'M2', 'M3'])].copy(); b['mkt'] = np.where(b.rule == 'OVER', 'O', 'AH'); b['dir'] = np.where(b.rule == 'OVER', 0, b.side)
    rows = [g.sort_values('hours').iloc[0] for _, g in b.groupby(['book', 'mid', 'mkt', 'dir']) if g.model.nunique() >= 2]
    return pd.DataFrame(rows)
def cell(g):
    if len(g) < 5: return f'n{len(g)} —'
    s = g.groupby('season').pnl.mean(); return f'n{len(g):4d} {g.pnl.mean() * 100:+5.1f}% {int((s > 0).sum())}/{s.size} {g.pnl.sum():+6.1f}u'
BB = {}
for k, f in F.items():
    b = pd.read_csv(f, dtype={'mid': str, 'season': str}); b = b[b.win == '72ω']; BB[k] = (b, cons(b))
for lab, filt in (('DOG', lambda x: x.rule == 'AH dog'), ('ΦΑΒΟΡΙ', lambda x: x.rule == 'AH fav'), ('OVER', lambda x: x.rule == 'OVER'), ('ΟΛΑ', lambda x: x.rule.notna())):
    P(f'--- {lab} ---')
    for who in ('ΣΥΝΑΙΝΕΣΗ', 'M1', 'M2', 'M3'):
        cells = []
        for k in F:
            b = BB[k][1] if who == 'ΣΥΝΑΙΝΕΣΗ' else BB[k][0][BB[k][0].model == who]
            cells.append(f'{k}: ' + ' | '.join(cell(b[(b.book == bk) & filt(b)]) for bk in ('Crown', 'SBOBET')))
        P(f'  {who:10s} ' + '   ║   '.join(cells))
P('\nΚΡΙΤΗΡΙΟ (2) στη ΣΥΝΑΙΝΕΣΗ:')
for k in ('slope', 'shape'):
    ok = True; det = []
    for bk in ('Crown', 'SBOBET'):
        c0, c1 = BB['none'][1], BB[k][1]; c0 = c0[c0.book == bk]; c1 = c1[c1.book == bk]
        r = lambda x: x.pnl.mean() * 100
        allok = r(c1) >= r(c0) - 1e-9; dogok = r(c1[c1.rule == 'AH dog']) > r(c0[c0.rule == 'AH dog']); favok = r(c1[c1.rule == 'AH fav']) >= r(c0[c0.rule == 'AH fav']) - 1.0
        ok &= allok and dogok and favok
        det.append(f'{bk}: ολα {r(c0):+.1f}→{r(c1):+.1f} {"✓" if allok else "✗"} · dogs {r(c0[c0.rule == "AH dog"]):+.1f}→{r(c1[c1.rule == "AH dog"]):+.1f} {"✓" if dogok else "✗"} · φαβ {r(c0[c0.rule == "AH fav"]):+.1f}→{r(c1[c1.rule == "AH fav"]):+.1f} {"✓" if favok else "✗"}')
    acc = all(res[m][0 if k == 'slope' else 1] for m in MODELS)
    P(f'  {k:6s}: (1) ακριβεια {"✓" if acc else "✗"} ({", ".join(m for m in MODELS if res[m][0 if k == "slope" else 1])}) · (2) ' + ' ║ '.join(det) + f'  →  {"ΠΕΡΝΑ" if (acc and ok) else "ΔΕΝ ΠΕΡΝΑ"}')
open('intl_gd_fix_eval_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
