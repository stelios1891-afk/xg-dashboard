
"""
intl_mkt_anchor.py — ΤΕΣΤ «rating που μαθαινει απο την αγορα» (21/9/2026, εντολη Στελιου «δοκιμασε πραγματα οπως στο UCL»). ΠΡΟ-ΔΗΛΩΣΗ:
Μηχανη E0/X3 (Elo K ανα τυπο, xElo 50/50, HFA 80). ΝΕΟ: μετα απο καθε ματς που εχει closing AH Crown, τα ratings μετακινουνται προς τη
διαφορα δυναμης που υπονοει η αγορα: d_mkt = s_mkt / 0.0049 (γκολ→Elo)· R_h += λ·(d_mkt − d)/2, R_a −= λ·(d_mkt − d)/2.
Χρησιμοποιει ΜΟΝΟ πληροφορια ΠΡΙΝ το επομενο ματς (ο πηχης του ματς δεν μπαινει στη δικη του προβλεψη). λ ∈ {0, .1, .2, .3, .5, .7}.
Επιλογη λ = LOSO RPS (ordered logit) αγωνιστικα 2122-2425· κριση 2526 (ολα + υποσυνολο με αγορα vs αγορα). Ολα αναφορα.
"""
import sys, math, json
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
src = open('intl_rating.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('def run2(mode)')], ns)
M, SEED, HFA, FAV_D, adj_xg, exp_score, margin_mult, K_TYPE = ns['M'], ns['SEED'], ns['HFA'], ns['FAV_D'], ns['adj_xg'], ns['exp_score'], ns['margin_mult'], ns['K_TYPE']
exec(src[src.index('def sig(x):'):src.index("EVAL_SEASONS = ")], ns); fit_ol, probs, rps = ns['fit_ol'], ns['probs'], ns['rps']
import os, datetime as _dt
# 25/9/2026 (αυτοματο refresh εθνικων): closing απο τον φακελο Nowgoal (τοπικα) Ή απο το συμπαγες intl_close_hist.json (Actions — ιδιο περιεχομενο,
# intl_close_compact.py)· ΣΥΝ closing του Odds API (intl_closing.jsonl, Pinnacle/Bovada στο ΚΟ) για ματς χωρις closing Nowgoal (π.χ. NL 2026-27).
if os.path.isdir('nowgoal_intl_odds') and not os.environ.get('INTL_CLOSE_COMPACT'):
    src2 = open('intl_vs_market.py', encoding='utf-8').read(); n2 = {}; exec(src2[:src2.index("M = pd.read_csv('intl_matches.csv'")], n2); close = n2['close']
else:
    close = json.load(open('intl_close_hist.json', encoding='utf-8')); n2 = {'close': close}
    print(f'closing απο intl_close_hist.json: {len(close)} ματς')
_n_toa = 0
if os.path.exists('intl_closing.jsonl'):
    _ix = {}
    for _r in M.itertuples():
        _ix.setdefault((int(_r.hid), int(_r.aid)), []).append((pd.Timestamp(_r.date), str(_r.mid)))
    for _ln in open('intl_closing.jsonl', encoding='utf-8'):
        try:
            _c = json.loads(_ln); _ko = pd.Timestamp(_c['ko'])
        except Exception:
            continue
        if _c.get('line') is None or not _c.get('oh') or not _c.get('oa'):
            continue
        _cand = [mid for d, mid in _ix.get((int(_c['hid']), int(_c['aid'])), []) if abs((d - _ko).total_seconds()) <= 36 * 3600]
        if len(_cand) == 1 and _cand[0] not in close:
            close[_cand[0]] = dict(ah_line=float(_c['line']), ah_h=float(_c['oh']), ah_a=float(_c['oa']), src='toa_' + str(_c.get('book')),
                                   **({'op': (float(_c['h']), float(_c['d']), float(_c['a']))} if _c.get('h') and _c.get('d') and _c.get('a') else {}))
            _n_toa += 1
print(f'closing Odds API (intl_closing.jsonl) που προστεθηκαν: {_n_toa}')
out = []
def P_(s=''):
    print(s, flush=True); out.append(s)
def sup_from_line(line, oh, oa, T=2.6):
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -4.0, 4.0
    for _ in range(30):
        mid = (lo + hi) / 2; lh_ = max((T + mid) / 2, 0.15); la_ = max((T - mid) / 2, 0.15)
        pw, pp_ = picks.p_cover(picks.gd_dist(lh_, la_), 1, line); p_eff = pw / max(1 - pp_, 1e-9)
        lo, hi = (mid, hi) if p_eff < tgt else (lo, mid)
    return (lo + hi) / 2
SMK = {}
for mid, v in close.items():
    if v.get('ah_line') is not None and v.get('ah_h') and v.get('ah_a'):
        try: SMK[mid] = sup_from_line(float(v['ah_line']), float(v['ah_h']), float(v['ah_a']))
        except Exception: pass
P_(f'ματς με s_mkt (closing AH Crown): {len(SMK)}')
GOAL_PER_ELO = 0.0049
raw = adj = 0.0; XS = {}
for r in M[M.has_xg].itertuples():
    a, b = adj_xg(r.shots, 0, 'gs'); raw += r.xg_h + r.xg_a; adj += a + b
scale = raw / adj
for r in M[M.has_xg].itertuples():
    XS[r.mid] = {}
    for fav in (-1, 0, 1):
        xh, xa = adj_xg(r.shots, fav, 'gs'); xh *= scale; xa *= scale
        XS[r.mid][fav] = (exp_score(xh, xa), margin_mult(round(xh - xa)))
ROWS = [(r.mid, r.season, r.ctype, r.comp, r.hid, r.aid, bool(r.neutral), int(r.hs) - int(r.ag), bool(r.has_xg)) for r in M.itertuples()]
def run(lam, keep=False):
    R = dict(SEED); diffs = np.empty(len(ROWS))
    for i, (mid, sea, ct, comp, hid, aid, neu, gd, hx) in enumerate(ROWS):
        rh = R.get(hid, 1500.0); ra = R.get(aid, 1500.0); d = rh + (0 if neu else HFA) - ra; diffs[i] = d
        E = 1 / (1 + 10 ** (-d / 400)); S_res = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        if hx:
            fav = 1 if d >= FAV_D else (-1 if d <= -FAV_D else 0); S_x, mm_x = XS[mid][fav]; S = 0.5 * S_x + 0.5 * S_res; mm = 0.5 * mm_x + 0.5 * margin_mult(gd)
        else:
            S, mm = S_res, margin_mult(gd)
        k = K_TYPE.get(ct, 30) * mm; R[hid] = rh + k * (S - E); R[aid] = ra - k * (S - E)
        if lam > 0 and mid in SMK:
            d_mkt = SMK[mid] / GOAL_PER_ELO; sh = lam * (d_mkt - d) / 2; R[hid] += sh; R[aid] -= sh
    if keep: return diffs, R
    return diffs
BASE = pd.DataFrame([dict(mid=a, season=b, ctype=c, gd=h) for a, b, c, d, e, f, g, h, i in ROWS]); BASE['y'] = np.where(BASE.gd > 0, 2, np.where(BASE.gd == 0, 1, 0))
COMP = BASE.ctype.isin(['nl', 'qual', 'tourn']); SEL = ['2122', '2223', '2324', '2425']; TEST = '2526'
def loso_rps(diffs, seasons=SEL, extra=None):
    m = COMP & BASE.season.isin(seasons)
    if extra is not None: m = m & extra
    d = BASE[m].copy(); d['diff'] = diffs[m.values]; Pr = np.full((len(d), 3), np.nan)
    for s in seasons:
        tr = d[d.season != s]; te = (d.season == s).values
        if te.sum() == 0: continue
        p = fit_ol(tr['diff'].values, tr.y.values); Pr[te] = probs(d['diff'].values[te], p)
    return rps(Pr, d.y.values), len(d)
def test_rps(diffs, extra=None):
    m = COMP & BASE.season.isin(SEL); t = COMP & (BASE.season == TEST)
    if extra is not None: t = t & extra
    p = fit_ol(diffs[m.values], BASE.y.values[m.values]); return rps(probs(diffs[t.values], p), BASE.y.values[t.values]), int(t.sum())
HASM = BASE.mid.isin(SMK.keys())
rows = []; D = {}
for lam in (0, .1, .2, .3, .5, .7):
    dd = run(lam); D[lam] = dd
    sel, n_sel = loso_rps(dd); t_all, n_t = test_rps(dd); t_m, n_tm = test_rps(dd, HASM); s_m, _ = loso_rps(dd, extra=HASM)
    rows.append(dict(λ=lam, LOSO_2122_2425=round(sel, 5), LOSO_με_αγορα=round(s_m, 5), κριση_2526=round(t_all, 4), n_2526=n_t, κριση_2526_με_αγορα=round(t_m, 4), n=n_tm))
pd.set_option('display.width', 220); P_('\nRATING ΜΕ ΑΓΚΥΡΑ ΑΓΟΡΑΣ (λ = ποσο μετακινειται προς την αγορα μετα απο καθε ματς με closing)'); P_(pd.DataFrame(rows).to_string(index=False))
best = min(rows, key=lambda r: r['LOSO_2122_2425'])['λ']; P_(f'επιλογη απο LOSO: λ={best}')
# αγορα στο 2526 υποσυνολο (για συγκριση)
C = n2['close']; import pandas as pd
mk = []
for mid in BASE.mid[(COMP & (BASE.season == TEST) & HASM).values]:
    v = close.get(mid, {}); op = v.get('op')
    mk.append(op)
ok = [i for i, o in enumerate(mk) if o]
if ok:
    Pm = np.vstack([np.array([1 / o[0], 1 / o[1], 1 / o[2]]) / sum(1 / x for x in o) for o in mk if o]); yy = BASE.y.values[(COMP & (BASE.season == TEST) & HASM).values][ok]
    P_(f'αγορα closing 1Χ2 στο ιδιο 2526 υποσυνολο (n={len(ok)}): RPS {rps(Pm, yy):.4f}')
pd.DataFrame(dict(mid=BASE.mid, **{f'diff_lam{l}': D[l] for l in D})).to_csv('intl_preds_anchor.csv', index=False)
_, R3 = run(0.3, keep=True); pd.Series(R3, name='R').rename_axis('tid').to_csv('intl_ratings_anchor.csv')
open('intl_mkt_anchor_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
