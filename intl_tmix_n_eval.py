"""
intl_tmix_n_eval.py — (1) ΠΟΣΑ ΜΑΤΣ για το xG ομαδων (N = 6/8/12/16/20) · (2) OVER ΚΑΙ ΣΕ ΜΗ ΚΟΝΤΙΝΑ με το νεο T. 26/9/2026 (Στελιος).
ΠΡΟ-ΔΗΛΩΣΗ (ΠΡΙΝ δω αποτελεσματα):
  (1) ΑΚΡΙΒΕΙΑ: Poisson log-lik συνολου γκολ (και MAE), νεο T = b0 + b1·T_live(Μ1) + b2·xG_N, b LOSO ανα σεζον, κοινο δειγμα αγωνιστικων.
      ROI: συναινεση 72ω (over + ολα), live βαση (Σχ.Β + βαθια φαβορι).
      ΑΛΛΑΓΗ απο N=12 μονο αν ενα αλλο N: log-lik καλυτερο σε ≥4/5 σεζον απο το 12 ΚΑΙ over συναινεσης (μεσος 2 βιβλιων) οχι χειροτερο.
  (2) OVER ΣΕ ΜΗ ΚΟΝΤΙΝΑ (οχι κοντινο, οχι νοκ-αουτ) με νεο T (N=12): μπαινουν αν ROI > 0 ΚΑΙ στα 2 βιβλια ΚΑΙ ≥4/5 σεζον,
      ΚΑΙ το συνολο της συναινεσης με αυτα δεν πεφτει. (Αναφορα και με το σημερινο T.)
"""
import sys, os, contextlib, math, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
out = []
def P(s=''):
    print(s, flush=True); out.append(s)
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'ne'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, T_of = G['D'], G['T_of']
C = D[D.ctype.isin(['nl', 'qual', 'tourn'])].copy(); C['T0'] = [T_of(r.d_M1, r) for r in C.itertuples()]
NS = (6, 8, 12, 16, 20); XG = {}
for N in NS:
    x = pd.read_csv(f'intl_xg_teamN{N}.csv', dtype={'mid': str}); x = x[x.n >= 3]; XG[N] = dict(zip(x.mid, x.xgsum))
C = C[C.mid.astype(str).isin(set.intersection(*[set(XG[N]) for N in NS]))].copy()
SEAS = sorted(C.season.unique())
def pll(T, y): return float(np.mean([-t + k * math.log(t) - math.lgamma(k + 1) for t, k in zip(T, y)]))
P(f'(1) ΑΚΡΙΒΕΙΑ ΣΥΝΟΛΟΥ ΓΚΟΛ — {len(C)} αγωνιστικα ματς (κοινο δειγμα), LOSO ανα σεζον · log-lik (μεγαλυτερο = καλυτερο) / MAE')
res = {}
for lab in ['T σημερα (χωρις xG ομαδων)'] + [f'N={N}' for N in NS]:
    per = {}; allT = []; ally = []
    for s in SEAS:
        tr, te = C[C.season != s], C[C.season == s]
        if lab.startswith('T σημερα'):
            T = te.T0.values
        else:
            N = int(lab[2:]); xtr = np.array([XG[N][str(m)] for m in tr.mid]); xte = np.array([XG[N][str(m)] for m in te.mid])
            b = np.linalg.lstsq(np.c_[np.ones(len(tr)), tr.T0, xtr], tr.tot.values, rcond=None)[0]; T = np.maximum(b[0] + b[1] * te.T0.values + b[2] * xte, 0.5)
        per[s] = pll(T, te.tot.values); allT += list(T); ally += list(te.tot.values)
    res[lab] = (per, pll(allT, ally), float(np.mean(np.abs(np.array(allT) - np.array(ally)))))
    P(f'  {lab:28s} log-lik {res[lab][1]:.4f} · MAE {res[lab][2]:.3f} · ανα σεζον ' + ' '.join(f'{s}:{v:.3f}' for s, v in per.items()))
ref = res['N=12'][0]
for N in NS:
    if N == 12: continue
    b = sum(1 for s in SEAS if res[f'N={N}'][0][s] > ref[s] + 1e-12); P(f'  N={N} vs N=12: καλυτερο σε {b}/5 σεζον')

def load(f):
    b = pd.read_csv(f, dtype={'mid': str, 'season': str}); b = b[(b.win == '72ω') & b.model.isin(['M1', 'M2', 'M3'])].copy()
    b['mkt'] = np.where(b.rule == 'OVER', 'O', 'AH'); b['dir'] = np.where(b.rule == 'OVER', 0, b.side)
    return pd.DataFrame([g.sort_values('hours').iloc[0].to_dict() for _, g in b.groupby(['book', 'mid', 'mkt', 'dir']) if g.model.nunique() >= 2])
def cell(x):
    c, s = x[x.book == 'Crown'], x[x.book == 'SBOBET']
    if len(c) < 5 or len(s) < 5: return (np.nan, 0, '—')
    cy = x.groupby('season').pnl.mean(); avg = (c.pnl.mean() + s.pnl.mean()) / 2 * 100
    return (avg, (len(c) + len(s)) // 2, f"{avg:+6.1f}% (n~{(len(c) + len(s)) // 2}, {int((cy > 0).sum())}/{cy.size} σεζον, ~{(c.pnl.sum() + s.pnl.sum()) / 2:+.1f}u){' ⚠' if (c.pnl.mean() > 0) != (s.pnl.mean() > 0) else ''}")
P('\nROI ΣΥΝΑΙΝΕΣΗΣ 72ω (μεσος 2 βιβλιων)')
base = load('intl_window_test_proper_ahhybrid_gddeepfav_bets.csv'); RO = {}
P(f"  {'T σημερα':12s} over {cell(base[base.rule == 'OVER'])[2]} · ολα {cell(base)[2]}")
for N in NS:
    b = load(f'intl_window_test_proper_ahhybrid_TmixN{N}_gddeepfav_bets.csv'); RO[N] = cell(b[b.rule == 'OVER'])[0]
    P(f"  {'N=' + str(N):12s} over {cell(b[b.rule == 'OVER'])[2]} · ολα {cell(b)[2]}")
P('\nΑΠΟΦΑΣΗ (1):')
for N in NS:
    if N == 12: continue
    b = sum(1 for s in SEAS if res[f'N={N}'][0][s] > ref[s] + 1e-12); ok = b >= 4 and RO[N] >= RO[12] - 1e-9
    P(f'  N={N}: log-lik {b}/5 · over {RO[N]:+.1f}% vs {RO[12]:+.1f}% → {"ΚΑΛΥΤΕΡΟ ΑΠΟ 12" if ok else "—"}')

P('\n(2) OVER ΣΕ ΜΗ ΚΟΝΤΙΝΑ ΜΑΤΣ (οχι κοντινο, οχι νοκ-αουτ) — συναινεση 72ω')
for lab, f in (('T σημερα', 'intl_window_test_proper_ahhybrid_overall_gddeepfav_bets.csv'), ('νεο T (N=12)', 'intl_window_test_proper_ahhybrid_overall_TmixN12_gddeepfav_bets.csv')):
    b = load(f); nc = b[(b.rule == 'OVER') & (~b.close.astype(bool)) & (~b.ko.astype(bool))]; cl = b[(b.rule == 'OVER') & (b.close.astype(bool) | b.ko.astype(bool))]
    rest = b[b.rule != 'OVER']
    P(f'  {lab:14s} μη κοντινα {cell(nc)[2]} · κοντινα/KO {cell(cl)[2]} · συνολο ΜΕ μη κοντινα {cell(pd.concat([rest, cl, nc]))[2]} · ΧΩΡΙΣ {cell(pd.concat([rest, cl]))[2]}')
    if lab.startswith('νεο'):
        c, s = nc[nc.book == 'Crown'], nc[nc.book == 'SBOBET']; cy = nc.groupby('season').pnl.mean()
        ok = c.pnl.mean() > 0 and s.pnl.mean() > 0 and (cy > 0).sum() >= 4 and cell(pd.concat([rest, cl, nc]))[0] >= cell(pd.concat([rest, cl]))[0] - 1e-9
        P(f'  ΑΠΟΦΑΣΗ (2): {"ΜΠΑΙΝΟΥΝ" if ok else "ΔΕΝ μπαινουν"} (Crown {c.pnl.mean() * 100:+.1f}%, SBOBET {s.pnl.mean() * 100:+.1f}%, θετικες σεζον {(cy > 0).sum()}/{cy.size})')
open('intl_tmix_n_eval_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
