"""
intl_xi60_test.py — ΤΕΣΤ 28/9/2026 (Στελιος, αφορμη Γεωργια−Ουκρανια: η αγορα κουνηθηκε −0.3 γκολ στις ενδεκαδες, εμεις −0.07).
Στις −60′ το live μετρα την top-11 αξια των 23 της αποστολης → οι ακριβοι στον ΠΑΓΚΟ μετρανε σαν να παιζουν.
ΕΚΔΟΧΕΣ (αξια που ξερουμε στις −60′):  V_w = XI + w·(V23 − XI)   (XI = αξια βασικης 11αδας, V23 = top-11 των 23)
   w=1 → σημερινο live · w=0 → μονο η 11αδα · w=0.25/0.5 → μερικο βαρος στον παγκο
ΠΡΟ-ΔΗΛΩΣΗ: βαση = Elo H3 (intl_preds_H diff) + ln(V_w,h / V_w,a), ordered logit, LOSO ανα σεζον (2021-2526, αγωνιστικα).
   Νεα εκδοχη ΠΕΡΝΑ μονο αν RPS < w=1 ΚΑΙ καλυτερη σε ≥4/6 σεζον.
   Πληροφοριακα: (α) αποσταση απο το closing (υπεροχη μοντελου vs αγορας), (β) ROI picks στο closing AH Crown
   (|γραμμη|≥0.5, τιμη 1.70-2.10, edge≥10%, κουρεμα 3%, σωστα τεταρτα + Σχεδιο Β) — απλοποιημενη τιμολογηση (T=2.6), μονο για ΣΥΓΚΡΙΣΗ εκδοχων.
Μονο μετρηση — δεν αλλαζει τιποτα live.
"""
import sys, io, json, bisect, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, intl_pricing as ip

class _Q(io.StringIO):
    def reconfigure(self, **k): pass

# ---- harness (ιδιο με intl_value2) ----
_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
sig, nelder_mead, rps, logloss = _ns['sig'], _ns['nelder_mead'], _ns['rps'], _ns['logloss']
_v = open('intl_value.py', encoding='utf-8').read(); _n2 = {'np': np, 'sig': sig, 'nelder_mead': nelder_mead}
exec(_v[_v.index('def fit_ol_multi'):_v.index('FEATS = ')], _n2)
fit_ol_multi, probs_multi = _n2['fit_ol_multi'], _n2['probs_multi']

# ---- closing αγορας (σωστη αναγνωση τεταρτων για την υπεροχη) ----
src = open('intl_mkt_anchor.py', encoding='utf-8').read()
pre = src[:src.index('GOAL_PER_ELO = 0.0049')].replace("sys.stdout.reconfigure(encoding='utf-8'); ", '')
OLD = "        pw, pp_ = picks.p_cover(picks.gd_dist(lh_, la_), 1, line); p_eff = pw / max(1 - pp_, 1e-9)"
NEW = ("        _parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]; _d = picks.gd_dist(lh_, la_)\n"
       "        _c = [picks.p_cover(_d, 1, L_) for L_ in _parts]; p_eff = sum(c_[0] for c_ in _c) / max(sum(1 - c_[1] for c_ in _c), 1e-9)")
assert OLD in pre
g = {'__name__': 'xi60'}
with contextlib.redirect_stdout(_Q()):
    exec(pre.replace(OLD, NEW), g)
SMK, CLOSE = g['SMK'], g['close']

# ---- δεδομενα ----
PV = json.load(open('intl_player_values.json', encoding='utf-8'))
SQ = json.load(open('intl_squads.json', encoding='utf-8'))
M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str}, parse_dates=['date'])
M['gd'] = M.hs - M['as']
PH = pd.read_csv('intl_preds_H.csv', dtype={'mid': str})[['mid', 'diff']]
H = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h:
        H[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now'):
        H[int(pid)] = (['2026-09-19'], [float(v['mv_now'])])

def val(pid, dstr):
    h = H.get(int(pid))
    if not h:
        return None
    i = bisect.bisect_right(h[0], dstr) - 1
    return h[1][i] if i >= 0 else h[1][0]

rows = []
for r in M[M.ctype.isin(['nl', 'qual', 'tourn'])].itertuples():
    s = SQ.get(r.mid)
    if not s:
        continue
    dstr = r.date.strftime('%Y-%m-%d'); f = {}
    for side in ('h', 'a'):
        t = s.get(side) or {}; st = [int(x) for x in (t.get('st') or [])]; dressed = [int(k) for k in (t.get('p') or {})]
        if len(st) < 10 or len(dressed) < 14:
            break
        xs = [val(p, dstr) for p in st]; ds = [val(p, dstr) for p in dressed]
        if sum(1 for x in xs if x) < 9 or sum(1 for x in ds if x) < 12:
            break
        xi = sum(x for x in xs if x) * 11 / sum(1 for x in xs if x)            # αναγωγη σε 11 αν λειπουν 1-2 τιμες
        v23 = sum(sorted([x for x in ds if x], reverse=True)[:11])
        f[side] = (xi, max(v23, xi))
    if len(f) == 2:
        rows.append(dict(mid=r.mid, season=r.season, ctype=r.ctype, gd=int(r.gd), xi_h=f['h'][0], v23_h=f['h'][1], xi_a=f['a'][0], v23_a=f['a'][1]))
D = pd.DataFrame(rows).merge(PH, on='mid', how='inner')
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
D['s_mkt'] = D.mid.map(SMK)
WS = [1.0, 0.5, 0.25, 0.0]
for w in WS:
    D[f'L{w}'] = np.log((D.xi_h + w * (D.v23_h - D.xi_h)) / (D.xi_a + w * (D.v23_a - D.xi_a)))
D['rot_h'] = D.xi_h / D.v23_h; D['rot_a'] = D.xi_a / D.v23_a
SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
D = D[D.season.isin(SEAS)].reset_index(drop=True)
print(f'αγωνιστικα ματς με 11αδα + αποστολη και αξιες: {len(D)} · με closing {D.s_mkt.notna().sum()}')
print(f'«ροτεισον» XI/V23: μεσο {D[["rot_h","rot_a"]].stack().mean():.2f} · p10 {D[["rot_h","rot_a"]].stack().quantile(.1):.2f} · '
      f'ομαδες-ματς με XI < 70% του V23: {int((D[["rot_h","rot_a"]].stack() < .7).sum())}')

# ---- 1. RPS LOSO ----
res = {}; PRED = {}
for w in WS:
    fs = ['diff', f'L{w}']; row = {}; allP = []; ally = []; idx = []
    for s_ in SEAS:
        tr = D[D.season != s_]; te = D[D.season == s_]
        b, c1, c2 = fit_ol_multi(tr[fs].values.astype(float), tr['y'].values)
        Pm = probs_multi(te[fs].values.astype(float), b, c1, c2)
        row[s_] = rps(Pm, te['y'].values); allP.append(Pm); ally.append(te['y'].values); idx.append(te.index.values)
    Pm = np.vstack(allP); yy = np.concatenate(ally)
    row['ALL'] = rps(Pm, yy); row['LL'] = logloss(Pm, yy)
    bfull = fit_ol_multi(D[fs].values.astype(float), D['y'].values)[0]; row['Elo/ln'] = bfull[1] / bfull[0]
    res[w] = row
T = pd.DataFrame(res).T
print('\n1. RPS LOSO (χαμηλοτερο = καλυτερο)')
print(T[SEAS + ['ALL', 'LL', 'Elo/ln']].round(5).to_string())
base = res[1.0]
for w in WS[1:]:
    better = sum(res[w][s_] < base[s_] for s_ in SEAS)
    print(f'  w={w}: ΔRPS {res[w]["ALL"] - base["ALL"]:+.5f} · καλυτερο σε {better}/6 σεζον → {"ΠΕΡΝΑ" if res[w]["ALL"] < base["ALL"] and better >= 4 else "δεν περνα"}')

# ---- 2. αποσταση απο closing + 3. ROI picks στο closing ----
print('\n2-3. ΑΓΟΡΑ (ματς με closing Crown) — υπεροχη μοντελου = OLS γκολ ~ Elo + ln(V_w), LOSO')
Dm = D[D.s_mkt.notna()].copy()
def settle(gd, side, line, odds):
    return picks.settle(gd, side, line, odds)
for w in WS:
    L = f'L{w}'; sm = np.full(len(Dm), np.nan)
    for s_ in SEAS:
        tr = D[D.season != s_]; te = (Dm.season == s_).values
        A = np.column_stack([tr['diff'], tr[L]]); b = np.linalg.lstsq(A, tr.gd.values, rcond=None)[0]
        sm[te] = Dm.loc[te, 'diff'].values * b[0] + Dm.loc[te, L].values * b[1]
    Dm[f's{w}'] = sm
    err = sm - Dm.s_mkt.values
    # picks στο closing AH
    pnl = []
    for r, s in zip(Dm.itertuples(), sm):
        c = CLOSE.get(r.mid) or {}
        if c.get('ah_line') is None or not c.get('ah_h') or not c.get('ah_a'):
            continue
        T0 = 2.6; dist = picks.gd_dist(max((T0 + s) / 2, .05), max((T0 - s) / 2, .05))
        line = float(c['ah_line'])
        for side, ud, odds in ((1, line, float(c['ah_h'])), (-1, -line, float(c['ah_a']))):
            if abs(ud) < 0.5 or not (1.70 <= odds <= 2.10):
                continue
            if ip.ah_ev(dist, side, ud, odds, picks.MARGIN) >= 0.10:
                pnl.append(settle(r.gd, side, ud, odds))
    pnl = np.array(pnl)
    print(f'  w={w}: συσχετιση με αγορα {np.corrcoef(sm, Dm.s_mkt)[0,1]:.4f} · RMSE vs αγορα {np.sqrt(np.mean(err**2)):.4f} γκολ · '
          f'picks closing n={len(pnl)} ROI {pnl.mean()*100:+.1f}% (±{pnl.std()/np.sqrt(max(len(pnl),1))*100:.1f})')
# ματς με ΜΕΓΑΛΟ ροτεισον (η περιπτωση Ουκρανιας): ποιος ειναι πιο κοντα στην αγορα;
big = (np.minimum(Dm.rot_h, Dm.rot_a) < 0.7).values
print(f'\n  ματς με ροτεισον <70% σε μια ομαδα (n={big.sum()}): RMSE vs αγορα · ' +
      ' · '.join(f'w={w}: {np.sqrt(np.mean((Dm[f"s{w}"].values[big] - Dm.s_mkt.values[big])**2)):.4f}' for w in WS))
print('  ιδια ματς, μεση υπεροχη ομαδας με ροτεισον (μοντελο − αγορα): ' +
      ' · '.join(f'w={w}: {np.mean(np.where(Dm.rot_h.values[big] < Dm.rot_a.values[big], 1, -1) * (Dm[f"s{w}"].values[big] - Dm.s_mkt.values[big])):+.3f}' for w in WS))
D.to_csv('intl_xi60_rows.csv', index=False)
