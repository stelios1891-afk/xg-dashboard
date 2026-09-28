"""
core7_mech_eval.py — 28/9/2026 «ανατομια της συμπιεσης»: για καθε εκδοχη μηχανης (core7_mech_preds_<v>.csv) × DRAW_BOOST {1.13, 1.00}:
  Α. ΣΥΜΠΙΕΣΗ: κλιση γκολ ~ υπεροχη μοντελου (1 = σωστη), μεροληψια φαβορι αγορας (μοντελο − πραγματικο) ολα / φαβορι ≥0.75, vs αγορα
  Β. ισοπαλιες μοντελο vs πραγματικο · RPS 1Χ2
  Γ. PICKS (κανονες live, closing Pinnacle AH): dogs +≥0.5 και φαβορι ≤−0.5 (1.70-2.10, edge≥10%) — αγωνιστικες 7-14 και 15+
Μονο αγωνιστικες ≥7 (md ≥6). Περιγραφικο.
"""
import sys, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
src = open('sos_test.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('# ---------- team ratings')], ns)
VARS = [v for v in ('base', 'nocomp', 'pen76', 'both', 'k4') if os.path.exists(f'core7_mech_preds_{v}.csv')]
LAB = {'base': 'Α σημερα', 'nocomp': 'Β χωρις συμπιεση', 'pen76': 'Γ πεναλτι 0.76', 'both': 'Δ χωρις συμπ.+πεν.0.76', 'k4': 'Ε warm-start K=4'}
P0 = pd.read_csv('core7_mech_preds_base.csv', dtype={'season': str})
LG = sorted(P0.league.unique()); SEAS = sorted(P0.season.unique())
reg, resolvers = ns['build_odds_layer'](LG, SEAS)
ODDS = {}
for _, r in P0.iterrows():
    g = ns['reg_of'](r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], resolvers[g](r['home_name']), resolvers[g](r['away_name']), r['date'])
    if o is None: continue
    L, ah, aa = o.get('AHCh'), o.get('PCAHH'), o.get('PCAHA')
    if pd.notna(L) and pd.notna(ah) and pd.notna(aa):
        ODDS[str(r['mid'])] = (float(L), float(ah), float(aa))
_c = {}
def sup(line, oh, oa, T=2.7):
    key = (line, oh, oa)
    if key in _c: return _c[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(34):
        md = (lo + hi) / 2; d = picks.gd_dist(max((T + md) / 2, .05), max((T - md) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _c[key] = (lo + hi) / 2; return _c[key]
picks.DRAW_BOOST = 1.13
SM = {m: sup(*v) for m, v in ODDS.items()}
def rps(pm, y):
    o = np.zeros_like(pm); o[np.arange(len(y)), 2 - y] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
rows = []
for v in VARS:
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str}); P = P[(P.md >= 6) & P.gd.notna()].copy(); P['mid'] = P.mid.astype(str)
    P['s_mkt'] = P.mid.map(SM); P['xh'] = P.xg_h.clip(.05, 6); P['xa'] = P.xg_a.clip(.05, 6); P['s'] = P.xh - P.xa
    M = P[P.s_mkt.notna()]
    sf = np.sign(M.s_mkt).replace(0, 1); fm, fg, fk = sf * M.s, sf * M.gd, M.s_mkt.abs()
    slope = np.polyfit(M.s, M.gd, 1)[0]
    big = fk >= 0.75
    for db in (1.13, 1.00):
        picks.DRAW_BOOST = db
        y = np.where(P.gd > 0, 2, np.where(P.gd == 0, 1, 0)); pm = np.zeros((len(P), 3))
        for i, (a, b) in enumerate(zip(P.xh, P.xa)):
            d = picks.gd_dist(a, b); pm[i] = (sum(q for k, q in d.items() if k > 0), d.get(0, 0), sum(q for k, q in d.items() if k < 0))
        res = dict(εκδοχη=LAB[v], DB=db, κλιση=round(slope, 3), φαβ_vs_πραγμ=round((fm - fg).mean(), 3), φαβ075_vs_πραγμ=round((fm[big] - fg[big]).mean(), 3),
                   φαβ_vs_αγορα=round((fm - fk).mean(), 3), ισοπ_μοντ=round(100 * pm[:, 1].mean(), 1), ισοπ_πραγμ=round(100 * (P.gd == 0).mean(), 1), RPS=round(rps(pm, y), 5))
        bets = []
        for r in M.itertuples():
            L, ah, aa = ODDS[r.mid]
            for b in picks.evaluate_bet(r.xh, r.xa, L, ah, aa):        # dogs (+≥0.5) — ο live κανονας
                bets.append(('dog', '7-14' if r.md <= 13 else '15+', r.season, picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
            dist = picks.gd_dist(r.xh, r.xa)
            for side, ud, odds in ((1, L, ah), (-1, -L, aa)):
                if ud <= -0.5 and 1.70 <= odds <= 2.10:
                    pw, pp = picks.p_cover(dist, side, ud)
                    if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= 0.10:
                        bets.append(('fav', '7-14' if r.md <= 13 else '15+', r.season, picks.settle(r.gd, side, ud, odds)))
        B = pd.DataFrame(bets, columns=['role', 'win', 'season', 'pnl'])
        for role in ('dog', 'fav'):
            for win in ('7-14', '15+'):
                d = B[(B.role == role) & (B.win == win)]; ps = d.groupby('season').pnl.mean()
                res[f'{role} {win}'] = f"{len(d)} / {100*d.pnl.mean():+.1f}% / {d.pnl.sum():+.0f}u / {int((ps > 0).sum())}/4" if len(d) else '—'
        rows.append(res)
    print(f'{v} ok', flush=True)
picks.DRAW_BOOST = 1.13
T = pd.DataFrame(rows); pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
print('\nΑ-Β. ΣΥΜΠΙΕΣΗ / ΙΣΟΠΑΛΙΕΣ / RPS (αγωνιστικες 7+· μεροληψια: + = υπερεκτιμα το φαβορι της αγορας, − = το υποτιμα, σε γκολ)')
print(T[['εκδοχη', 'DB', 'κλιση', 'φαβ_vs_πραγμ', 'φαβ075_vs_πραγμ', 'φαβ_vs_αγορα', 'ισοπ_μοντ', 'ισοπ_πραγμ', 'RPS']].to_string(index=False))
print('\nΓ. PICKS (n / ROI / μοναδες / θετικες σεζον) — closing Pinnacle, κανονες live')
print(T[['εκδοχη', 'DB', 'dog 7-14', 'dog 15+', 'fav 7-14', 'fav 15+']].to_string(index=False))
