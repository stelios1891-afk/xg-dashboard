"""
core7_anchor_test.py — ΤΕΣΤ 28/9/2026 (Στελιος «ξεκινα»): ΑΓΚΥΡΑ ΑΓΟΡΑΣ στα εγχωρια (CORE7), οπως στις εθνικες (λ=0.3 εκει).
Μοντελο = live engine (europe_test_preds.csv, walk-forward xg_h/xg_a, 2223-2526). Αγορα = Pinnacle closing AH (AHCh, PCAHH/PCAHA)
→ υπεροχη s_mkt (σωστα τεταρτα, T = xg_h+xg_a του μοντελου).
ΑΓΚΥΡΑ: καθε ομαδα εχει διορθωση o (γκολ). Προβλεψη: s = s_mod + o_h − o_a (το συνολο T μενει του μοντελου).
Μετα το ματς: e = s_mkt − s · o_h += λ·e/2 · o_a −= λ·e/2 (ΜΟΝΟ πληροφορια πριν το επομενο ματς).
Παραλλαγες: λ ∈ {0,.1,.2,.3,.5,.7} × μεταφορα διορθωσης στη νεα σεζον c ∈ {0 (μηδενισμος), 1 (μεταφορα)}.
ΠΡΟ-ΔΗΛΩΣΗ: επιλογη (λ,c) με RPS LOSO ανα σεζον (fold = σεζον). ΠΕΡΝΑ αν (1) RPS < βαση (λ=0) ΚΑΙ καλυτερο σε ≥3/4 σεζον,
(2) picks md15+ (κανονες live: +handicap ≥0.5, 1.70-2.10, edge≥10%, closing) ROI ΚΑΙ μοναδες ΟΧΙ χειροτερα απο τη βαση.
Πληροφοριακα: md7-14, κλιση b vs closing. Δεν αλλαζει τιποτα live.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

src = open('sos_test.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('# ---------- team ratings')], ns)
P = pd.read_csv('europe_test_preds.csv', dtype={'season': str}); P = P[P.gd.notna()].copy()
LG = sorted(P.league.unique()); SEAS = sorted(P.season.unique())
reg, resolvers = ns['build_odds_layer'](LG, SEAS)
_c = {}
def sup(line, oh, oa, T):
    key = (line, oh, oa, round(T, 1))
    if key in _c: return _c[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(34):
        md = (lo + hi) / 2; d = picks.gd_dist(max((T + md) / 2, .05), max((T - md) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _c[key] = (lo + hi) / 2; return _c[key]
rows = []
for _, r in P.iterrows():
    g = ns['reg_of'](r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], resolvers[g](r['home_name']), resolvers[g](r['away_name']), r['date'])
    L = o.get('AHCh') if o is not None else None; ah = o.get('PCAHH') if o is not None else None; aa = o.get('PCAHA') if o is not None else None
    xh, xa = min(max(r.xg_h, .05), 6), min(max(r.xg_a, .05), 6)
    ok = o is not None and pd.notna(L) and pd.notna(ah) and pd.notna(aa)
    rows.append(dict(league=r.league, season=r.season, date=pd.to_datetime(r.date), md=int(r.md), h=r.home_name, a=r.away_name, gd=int(r.gd),
                     xh=xh, xa=xa, L=float(L) if ok else np.nan, ah=float(ah) if ok else np.nan, aa=float(aa) if ok else np.nan,
                     s_mkt=sup(float(L), float(ah), float(aa), xh + xa) if ok else np.nan))
D = pd.DataFrame(rows).sort_values(['league', 'date']).reset_index(drop=True)
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0)); D['win'] = np.where(D.md >= 15, 'md15+', np.where(D.md >= 7, 'md7-14', 'md<7'))
print(f'ματς {len(D)} · με closing AH {D.s_mkt.notna().sum()} · ανα σεζον ' + str(D.groupby("season").s_mkt.count().to_dict()))

def run(lam, carry):
    s_adj = np.zeros(len(D))
    for lg, idx in D.groupby('league').groups.items():
        off = {}; cur_sea = None
        for i in idx:
            r = D.loc[i]
            if r.season != cur_sea:
                off = {k: v * carry for k, v in off.items()}; cur_sea = r.season
            s = (r.xh - r.xa) + off.get(r.h, 0.0) - off.get(r.a, 0.0); s_adj[i] = s
            if lam > 0 and r.s_mkt == r.s_mkt:
                e = r.s_mkt - s; off[r.h] = off.get(r.h, 0.0) + lam * e / 2; off[r.a] = off.get(r.a, 0.0) - lam * e / 2
    return s_adj

def probs(s_arr):
    T = (D.xh + D.xa).values; out = np.zeros((len(D), 3))
    for i, (t, s) in enumerate(zip(T, s_arr)):
        d = picks.gd_dist(max((t + s) / 2, .05), max((t - s) / 2, .05))
        out[i] = (sum(v for k, v in d.items() if k > 0), d.get(0, 0.0), sum(v for k, v in d.items() if k < 0))
    return out
def rps(pm, y):
    o = np.zeros_like(pm); o[np.arange(len(y)), 2 - y] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
def bets(s_arr, mask):
    out = []
    for i in np.where(mask & D.s_mkt.notna().values)[0]:
        r = D.loc[i]; t = r.xh + r.xa; s = s_arr[i]
        for b in picks.evaluate_bet(max((t + s) / 2, .05), max((t - s) / 2, .05), r.L, r.ah, r.aa):
            out.append((picks.settle(r.gd, b['side'], b['hcap'], b['odds']), r.season))
    return out

res = {}
for lam in (0, .1, .2, .3, .5, .7):
    for carry in ((0,) if lam == 0 else (0, 1)):
        s_arr = run(lam, carry); pm = probs(s_arr); y = D.y.values
        row = {'ALL': rps(pm, y)}
        for s_ in SEAS: m = (D.season == s_).values; row[s_] = rps(pm[m], y[m])
        for w_ in ('md7-14', 'md15+'): m = (D.win == w_).values; row[w_] = rps(pm[m], y[m])
        mk = D.s_mkt.notna().values
        A = np.column_stack([np.ones(mk.sum()), D.s_mkt[mk], s_arr[mk] - D.s_mkt[mk]]); b = np.linalg.lstsq(A, D.gd[mk].astype(float), rcond=None)[0]
        row['b'] = b[2]; row['sd_διαφ'] = np.std(s_arr[mk] - D.s_mkt[mk])
        for w_ in ('md7-14', 'md15+'):
            bb = bets(s_arr, (D.win == w_).values); pn = np.array([x[0] for x in bb])
            row[f'n_{w_}'] = len(pn); row[f'ROI_{w_}'] = pn.mean() * 100 if len(pn) else np.nan; row[f'u_{w_}'] = pn.sum()
            if w_ == 'md15+':
                row['σεζον+'] = sum(np.mean([x[0] for x in bb if x[1] == s_]) > 0 for s_ in SEAS if any(x[1] == s_ for x in bb))
        res[(lam, carry)] = row
        print(f'  λ={lam} c={carry} ok', flush=True)
T = pd.DataFrame(res).T; pd.set_option('display.width', 250)
print('\nRPS (χαμηλοτερο = καλυτερο) ανα σεζον / παραθυρο · κλιση b vs closing · picks (κλεισιμο, κανονες live)')
print(T[['ALL'] + SEAS + ['md7-14', 'md15+', 'b', 'sd_διαφ']].round(5).to_string())
print(T[['n_md7-14', 'ROI_md7-14', 'u_md7-14', 'n_md15+', 'ROI_md15+', 'u_md15+', 'σεζον+']].round(2).to_string())
base = res[(0, 0)]
# LOSO επιλογη: για καθε σεζον, διαλεγω (λ,c) με το καλυτερο RPS στις ΑΛΛΕΣ σεζον, και μετραω στην ιδια
sel_rps = []; chosen = []
for s_ in SEAS:
    others = [x for x in SEAS if x != s_]
    best = min(res, key=lambda k: np.mean([res[k][x] for x in others]))
    chosen.append(best); sel_rps.append((res[best][s_], base[s_]))
print('\nLOSO επιλογη (λ,c) ανα σεζον: ' + ' · '.join(f'{s_}: {c} → {a:.5f} vs βαση {b_:.5f}' for s_, c, (a, b_) in zip(SEAS, chosen, sel_rps)))
wins = sum(a < b_ for a, b_ in sel_rps)
bestall = min(res, key=lambda k: res[k]['ALL'])
r_ = res[bestall]
c1 = np.mean([a for a, _ in sel_rps]) < np.mean([b_ for _, b_ in sel_rps]) and wins >= 3
c2 = r_['ROI_md15+'] >= base['ROI_md15+'] and r_['u_md15+'] >= base['u_md15+']
print(f'\nΚΡΙΣΗ: (1) RPS LOSO {np.mean([a for a, _ in sel_rps]):.5f} vs βαση {np.mean([b_ for _, b_ in sel_rps]):.5f}, καλυτερο σε {wins}/4 → {"✓" if c1 else "✗"} · '
      f'(2) καλυτερη παραλλαγη {bestall}: picks md15+ ROI {r_["ROI_md15+"]:+.1f}% / {r_["u_md15+"]:+.1f}u vs βαση {base["ROI_md15+"]:+.1f}% / {base["u_md15+"]:+.1f}u → {"✓" if c2 else "✗"} '
      f'→ {"ΠΕΡΝΑ" if c1 and c2 else "ΔΕΝ ΠΕΡΝΑ"}')
