"""
core7_goals_gap_diag.py — ΔΙΑΓΝΩΣΗ 1/10/2026 (Στελιος: «βαθια αναλυση — που υστερουμε στα γκολ σε συγκριση με την αγορα· πρωτα
το προβλημα, μετα η λυση»). CORE7 2223-2526, αγων. 7+ (md≥6). Μηχανη LIVE (σωστο SoS 0.75).
ΑΓΟΡΑ: Crown κλεισιμο συνολου (Nowgoal, πραγματικη γραμμη) + Pinnacle κλεισιμο AH (υπεροχη s_mkt) → λυνω T_mkt (Dixon-Coles,
ιδια κατανομη με το μοντελο) ωστε P(over) = τιμη χωρις γκανιοτα· λ_γηπ = (T+s)/2, λ_φιλ = (T−s)/2.
Α. επιπεδο (μεσα γκολ: πραγματικα / μοντελο / αγορα) · Β. ποιος ξερει: γκολ ~ T_αγορας + b·(T_μοντ − T_αγορας)
Γ. ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΙΝΤΕΡ (κατα αγορα) ανα ζωνη υπεροχης · Δ. γηπεδουχος/φιλοξενουμενος · Ε. λιγκα · ΣΤ. περιοδος σεζον
Ζ. εκταση (το μοντελο «συμπιεζει» τα συνολα;) · Η. διαφωνιες ≥0.3 · Θ. σχημα κατανομης (0-0, 0 γκολ, ≥5)
Ι. ΜΗΧΑΝΙΣΜΟΙ (15+ μονο, οπου παλια=νεα μηχανη): nocomp (χωρις συμπιεση Caley) · pen76 (πεναλτι 0.76) · both · d0 (αμυνα μονο xG)
   · d50 · a125 — ιδια μετρα (b, RMSE, χασμα φαβορι/ντογκ).
Περιγραφικο — δεν αλλαζει τιποτα live.
"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'gg'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, picks, ns, reg, resolvers, sup = g['D'], g['picks'], g['ns'], g['reg'], g['resolvers'], g['sup']
key = ['league', 'season', 'h', 'a', 'date']
def load(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str}); P['date'] = pd.to_datetime(P.date)
    m = D[key].merge(P[['league', 'season', 'home_name', 'away_name', 'date', 'xg_h', 'xg_a', 'mid']],
                     left_on=key, right_on=['league', 'season', 'home_name', 'away_name', 'date'], how='left')
    assert len(m) == len(D) and m.xg_h.notna().mean() > .99
    return m.xg_h.clip(.05, 6).values, m.xg_a.clip(.05, 6).values, m.mid.values
XH, XA, MID = load('cur_0.75_6_13'); D['mid'] = MID; D['xh'] = XH; D['xa'] = XA
# σκορ
_M, _ = picks.load_matches(sorted(D.league.unique()), sorted(D.season.unique()))
SC = {str(k): (h, a) for k, h, a in zip(_M.mid, _M.hg, _M.ag)}
FULL = {}
for f in glob.glob('odds_full/*_fd.csv'):
    lg_, sea_ = os.path.basename(f)[:-7].rsplit('_', 1)
    try: X = pd.read_csv(f)
    except Exception: continue
    for x in X.to_dict('records'): FULL[(lg_, sea_, x.get('HomeTeam'), x.get('AwayTeam'))] = x
hg, ag = [], []
for r in D.itertuples():
    s_ = SC.get(str(r.mid))
    if s_ is None:
        gg_ = ns['reg_of'](r.season); hn, an = resolvers[gg_](r.h), resolvers[gg_](r.a)
        o = picks.match_odds(reg[gg_]['Om'], r.season, hn, an, r.date); o = {} if o is None else o
        x = FULL.get((r.league, r.season, hn, an)) or {}
        try: s_ = (int(o.get('FTHG', x.get('FTHG'))), int(o.get('FTAG', x.get('FTAG'))))
        except Exception: s_ = (np.nan, np.nan)
    hg.append(s_[0]); ag.append(s_[1])
D['hg'] = hg; D['ag'] = ag; D['tg'] = D.hg + D.ag
# Crown OU κλεισιμο & ανοιγμα
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
    except Exception: return None
OU = {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') != 3 or not r.get('ou'): continue
        rows = []
        for mt, ov, gl, un in r['ou']:
            L = pl(gl)
            try: oo, uu = float(ov) + 1, float(un) + 1
            except (TypeError, ValueError): continue
            if L is None or mt is None or oo <= 1 or uu <= 1: continue
            rows.append((mt, L, oo, uu))
        if rows: rows.sort(); OU[str(r['mid'])] = (rows[0][1:], rows[-1][1:])
def tdist(h, a):
    M = picks.score_matrix_dom(h, a); d = {}
    for i in range(13):
        for j in range(13): d[i + j] = d.get(i + j, 0) + M[i, j]
    return d
_cT = {}
def T_of(L, oo, uu, s):
    k = (L, oo, uu, round(s, 2))
    if k in _cT: return _cT[k]
    tgt = (1 / oo) / (1 / oo + 1 / uu); lo, hi = 0.8, 5.5
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
    for _ in range(30):
        T = (lo + hi) / 2; d = tdist(max((T + s) / 2, .05), max((T - s) / 2, .05)); pw = pp = 0
        for x in parts:
            pw += sum(v for kk, v in d.items() if kk > x + .01); pp += sum(v for kk, v in d.items() if abs(kk - x) < .01)
        pl_ = sum(v for kk, v in d.items() for x in parts if kk < x - .01)
        pe = pw / max(pw + pl_, 1e-9)
        lo, hi = (T, hi) if pe < tgt else (lo, T)
    _cT[k] = (lo + hi) / 2; return _cT[k]
Tm, To = [], []
for r in D.itertuples():
    q = OU.get(str(r.mid)); s = r.s_mkt if r.s_mkt == r.s_mkt else (r.xh - r.xa)
    Tm.append(T_of(*q[1], s) if q else np.nan); To.append(T_of(*q[0], s) if q else np.nan)
D['T_mkt'] = Tm; D['T_open'] = To; D['T_mod'] = D.xh + D.xa
D['s_mod'] = D.xh - D.xa
W = D[D.T_mkt.notna() & D.tg.notna() & D.s_mkt.notna()].copy()
W['win'] = np.where(W.md >= 25, '26+', np.where(W.md >= 14, '15-25', '7-14'))
print(f'ματς με σκορ + Crown συνολο + Pinnacle AH: {len(W)} / {len(D)}')
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + X); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / (len(y) - X.shape[1])); return b, b / np.sqrt(np.diag(cov))
def line(x, lab):
    b, t = ols(x.tg.values.astype(float), [x.T_mkt.values, (x.T_mod - x.T_mkt).values])
    rm_m = np.sqrt(((x.tg - x.T_mod) ** 2).mean()); rm_k = np.sqrt(((x.tg - x.T_mkt) ** 2).mean())
    return (f'  {lab:22s} n{len(x):5d} · γκολ {x.tg.mean():.3f} · μοντ {x.T_mod.mean():.3f} ({x.T_mod.mean()-x.tg.mean():+.3f}) · αγορα {x.T_mkt.mean():.3f} '
            f'({x.T_mkt.mean()-x.tg.mean():+.3f}) · RMSE μοντ {rm_m:.4f} αγορα {rm_k:.4f} · b {b[2]:+.2f} (t {t[2]:+.1f})')
print('\nΑ/Β. ΕΠΙΠΕΔΟ & ΠΟΙΟΣ ΞΕΡΕΙ (b = ποσο απο τη διαφορα μοντελου−αγορας «ερχεται»· 0 = τιποτα, <0 = το μοντελο κανει λαθος)')
print(line(W, 'ΟΛΑ'))
for s_ in sorted(W.season.unique()): print(line(W[W.season == s_], s_))
for w_ in ('7-14', '15-25', '26+'): print(line(W[W.win == w_], f'αγων. {w_}'))
print('\nΕ. ΑΝΑ ΛΙΓΚΑ')
for lg in sorted(W.league.unique()): print(line(W[W.league == lg], lg))
# Γ. φαβορι / ντογκ κατα αγορα
W['fav_home'] = W.s_mkt >= 0
W['lm_fav'] = np.where(W.fav_home, (W.T_mkt + W.s_mkt) / 2, (W.T_mkt - W.s_mkt) / 2)
W['lm_dog'] = W.T_mkt - W.lm_fav
W['lo_fav'] = np.where(W.fav_home, W.xh, W.xa); W['lo_dog'] = np.where(W.fav_home, W.xa, W.xh)
W['g_fav'] = np.where(W.fav_home, W.hg, W.ag); W['g_dog'] = np.where(W.fav_home, W.ag, W.hg)
W['zone'] = pd.cut(W.s_mkt.abs(), [-.01, .3, .7, 1.2, 9], labels=['ισορροπ. <0.3', 'μικρο 0.3-0.7', 'μεσαιο 0.7-1.2', 'μεγαλο 1.2+'])
print('\nΓ. ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΙΝΤΕΡ (κατα αγορα) — γκολ πραγματικα · μοντελο (Δ) · αγορα (Δ)')
for z, x in W.groupby('zone', observed=True):
    print(f'  {z:15s} n{len(x):5d} · ΦΑΒ {x.g_fav.mean():.3f}: μοντ {x.lo_fav.mean():.3f} ({x.lo_fav.mean()-x.g_fav.mean():+.3f}) αγορα {x.lm_fav.mean():.3f} ({x.lm_fav.mean()-x.g_fav.mean():+.3f})'
          f' · ΝΤΟΓΚ {x.g_dog.mean():.3f}: μοντ {x.lo_dog.mean():.3f} ({x.lo_dog.mean()-x.g_dog.mean():+.3f}) αγορα {x.lm_dog.mean():.3f} ({x.lm_dog.mean()-x.g_dog.mean():+.3f})')
for side, (gm, lo, lm) in (('ΦΑΒΟΡΙ', ('g_fav', 'lo_fav', 'lm_fav')), ('ΑΟΥΤΣΑΙΝΤΕΡ', ('g_dog', 'lo_dog', 'lm_dog'))):
    b, t = ols(W[gm].values.astype(float), [W[lm].values, (W[lo] - W[lm]).values])
    print(f'  {side:12s} πληροφορια μοντελου περα απο αγορα: b {b[2]:+.2f} (t {t[2]:+.1f}) · ανα σεζον: ' +
          ' '.join(f'{s_}: {ols(x[gm].values.astype(float), [x[lm].values, (x[lo] - x[lm]).values])[0][2]:+.2f}' for s_, x in W.groupby('season')))
print('\nΔ. ΓΗΠΕΔΟΥΧΟΣ / ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ — γκολ · μοντ (Δ) · αγορα (Δ)')
lmh = (W.T_mkt + W.s_mkt) / 2; lma = (W.T_mkt - W.s_mkt) / 2
print(f'  γηπ  {W.hg.mean():.3f}: μοντ {W.xh.mean():.3f} ({W.xh.mean()-W.hg.mean():+.3f}) αγορα {lmh.mean():.3f} ({lmh.mean()-W.hg.mean():+.3f})')
print(f'  φιλ  {W.ag.mean():.3f}: μοντ {W.xa.mean():.3f} ({W.xa.mean()-W.ag.mean():+.3f}) αγορα {lma.mean():.3f} ({lma.mean()-W.ag.mean():+.3f})')
print('\nΖ. ΕΚΤΑΣΗ — κλιση μοντελου πανω στην αγορα (1 = ιδια εκταση, <1 = το μοντελο συμπιεζει) & ανα πενταδα T_αγορας')
b, t = ols(W.T_mod.values, [W.T_mkt.values]); print(f'  T_μοντ = {b[0]:.2f} + {b[1]:.2f}·T_αγορας · sd μοντ {W.T_mod.std():.3f} vs αγορα {W.T_mkt.std():.3f}')
W['q'] = pd.qcut(W.T_mkt, 5, labels=['Q1 χαμηλα', 'Q2', 'Q3', 'Q4', 'Q5 ψηλα'])
for q, x in W.groupby('q', observed=True):
    print(f'  {q:10s} n{len(x):5d} · γκολ {x.tg.mean():.3f} · μοντ {x.T_mod.mean():.3f} ({x.T_mod.mean()-x.tg.mean():+.3f}) · αγορα {x.T_mkt.mean():.3f} ({x.T_mkt.mean()-x.tg.mean():+.3f})')
print('\nΗ. ΔΙΑΦΩΝΙΕΣ |T_μοντ − T_αγορας| ≥ 0.3 — ποιος ειχε δικιο; (+ = πιο κοντα το μοντελο)')
for lab, msk in (('μοντελο ΠΙΟ ΨΗΛΑ', W.T_mod - W.T_mkt >= 0.3), ('μοντελο ΠΙΟ ΧΑΜΗΛΑ', W.T_mod - W.T_mkt <= -0.3)):
    x = W[msk]
    print(f'  {lab:18s} n{len(x):5d} · γκολ {x.tg.mean():.3f} · μοντ {x.T_mod.mean():.3f} · αγορα {x.T_mkt.mean():.3f} · '
          f'κινηση αγορας ανοιγμα→κλεισιμο {(x.T_mkt - x.T_open).mean():+.3f}')
print('\nΘ. ΣΧΗΜΑ — προβλεπομενη vs πραγματικη συχνοτητα (μοντελο | αγορα-κατανομη με T_αγορας)')
pm = {'0 γκολ': [], '≤1': [], '≥4': [], '≥5': [], '0-0': [], 'ισοπαλια': []}; pk = {k: [] for k in pm}; ob = {k: [] for k in pm}
for r in W.itertuples():
    for store, (h, a) in ((pm, (r.xh, r.xa)), (pk, (max((r.T_mkt + r.s_mkt) / 2, .05), max((r.T_mkt - r.s_mkt) / 2, .05)))):
        M = picks.score_matrix_dom(h, a); tot = {}
        for i in range(13):
            for j in range(13): tot[i + j] = tot.get(i + j, 0) + M[i, j]
        store['0 γκολ'].append(tot[0]); store['≤1'].append(tot[0] + tot[1]); store['≥4'].append(1 - sum(tot[k] for k in range(4)))
        store['≥5'].append(1 - sum(tot[k] for k in range(5))); store['0-0'].append(M[0, 0]); store['ισοπαλια'].append(float(np.trace(M)))
    ob['0 γκολ'].append(r.tg == 0); ob['≤1'].append(r.tg <= 1); ob['≥4'].append(r.tg >= 4); ob['≥5'].append(r.tg >= 5)
    ob['0-0'].append(r.tg == 0); ob['ισοπαλια'].append(r.hg == r.ag)
for k in pm:
    print(f'  {k:9s} πραγματικο {100*np.mean(ob[k]):5.1f}% · μοντελο {100*np.mean(pm[k]):5.1f}% · αγορα {100*np.mean(pk[k]):5.1f}%')
# Ι. μηχανισμοι (15+)
print('\nΙ. ΜΗΧΑΝΙΣΜΟΙ ΕΙΣΟΔΟΥ (αγων. 15+, οπου παλια μηχανη = νεα) — b, RMSE, χασμα ΦΑΒ/ΝΤΟΓΚ (μοντ − πραγματικα)')
W15 = W[W.md >= 14]
for lab, v in (('ΣΗΜΕΡΑ', 'cur_0.75_6_13'), ('χωρις συμπιεση Caley', 'nocomp'), ('πεναλτι 0.76', 'pen76'), ('και τα δυο', 'both'),
               ('αμυνα μονο xG (d0)', 'd0'), ('αμυνα 50% γκολ (d50)', 'd50'), ('επιθεση γκολ ×1.25', 'a125')):
    try: xh, xa, _ = load(v)
    except Exception as e: print(f'  {lab}: —'); continue
    xh = pd.Series(xh, index=D.index).loc[W15.index].values; xa = pd.Series(xa, index=D.index).loc[W15.index].values
    T = xh + xa; b, t = ols(W15.tg.values.astype(float), [W15.T_mkt.values, T - W15.T_mkt.values])
    fav = np.where(W15.fav_home, xh, xa); dog = T - fav
    print(f'  {lab:22s} μεσο T {T.mean():.3f} (γκολ {W15.tg.mean():.3f}) · RMSE {np.sqrt(((W15.tg - T) ** 2).mean()):.4f} (αγορα {np.sqrt(((W15.tg - W15.T_mkt) ** 2).mean()):.4f})'
          f' · b {b[2]:+.2f} (t {t[2]:+.1f}) · ΦΑΒ {fav.mean() - W15.g_fav.mean():+.3f} · ΝΤΟΓΚ {dog.mean() - W15.g_dog.mean():+.3f}')
W.to_csv('core7_goals_gap_rows.csv', index=False)
