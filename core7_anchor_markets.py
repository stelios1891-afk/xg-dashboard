"""
core7_anchor_markets.py — ΤΕΣΤ 28/9/2026 (Στελιος: «δεν τεσταραμε στις υπολοιπες αγορες»· ΜΟΝΟ τεστ, καμια αποφαση).
ΑΓΚΥΡΑ ΣΕ ΟΛΕΣ ΤΙΣ ΑΓΟΡΕΣ — εγχωρια CORE7, 2223-2526, ολες οι αγωνιστικες (europe_test_preds_all.csv).
Μοντελα: LIVE (σημερα) vs ΑΓΚΥΡΑ (λ=0.5, διορθωσεις απο ολα τα ματς, μεταφορα σεζον) · δευτερη εκδοχη ΑΓΚΥΡΑ-χωρις-1-6.
  Υπεροχη: διορθωση ομαδας προς το closing AH Pinnacle (ολες οι σεζον).
  Συνολο γκολ: διορθωση ΓΚΟΛ ομαδας προς το closing O/U 2.5 (Avg, μονο 2223/2324 — εκει υπαρχει)· T = T_mod + g_h + g_a.
ΑΓΟΡΕΣ (closing): AH φαβορι (≤−0.5, 1.70-2.10, edge≥10%, κουρεμα 3%, p_cover οπως τα εγχωρια) · AH dog (≥+0.5, ιδια — αναφορα) ·
  1Χ2 Pinnacle (edge≥5%: φαβορι τιμη<2.0 / ισοπαλια / αουτσαιντερ τιμη≥3.0 / μεσαια) — 2223/2324 · O/U 2.5 Avg (edge≥5% over/under) — 2223/2324.
Παραθυρα: αγωνιστικες 7-14 (md 6-13) και 15+ (md ≥14).
ΠΡΟ-ΔΗΛΩΣΗ ανα αγορα & παραθυρο: η ΑΓΚΥΡΑ «κερδιζει» αν ROI > LIVE ΚΑΙ μοναδες ≥ LIVE ΚΑΙ θετικη σε ≥3/4 σεζον (≥2/2 οπου 2 σεζον).
"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

src = open('sos_test.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('# ---------- team ratings')], ns)
P = pd.read_csv('europe_test_preds_all.csv', dtype={'season': str}); P = P[P.gd.notna()].copy()
LG = sorted(P.league.unique()); SEAS = sorted(P.season.unique())
reg, resolvers = ns['build_odds_layer'](LG, SEAS)

def T_from_ou(po):
    lo, hi = 0.5, 6.0
    for _ in range(40):
        m = (lo + hi) / 2; p = 1 - math.exp(-m) * (1 + m + m * m / 2)
        lo, hi = (m, hi) if p < po else (lo, m)
    return (lo + hi) / 2
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
def f(o, k):
    v = o.get(k) if o is not None else None
    return float(v) if v is not None and pd.notna(v) else np.nan

rows = []
for _, r in P.iterrows():
    g = ns['reg_of'](r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], resolvers[g](r['home_name']), resolvers[g](r['away_name']), r['date'])
    xh, xa = min(max(r.xg_h, .05), 6), min(max(r.xg_a, .05), 6)
    L, ah, aa = f(o, 'AHCh'), f(o, 'PCAHH'), f(o, 'PCAHA'); ov, un = f(o, 'AvgC>2.5'), f(o, 'AvgC<2.5')
    T_m = T_from_ou((1 / ov) / (1 / ov + 1 / un)) if ov == ov and un == un else np.nan
    hg, ag = f(o, 'FTHG'), f(o, 'FTAG')
    rows.append(dict(league=r.league, season=r.season, date=pd.to_datetime(r.date), md=int(r.md), h=r.home_name, a=r.away_name, gd=int(r.gd),
                     tot=hg + ag if hg == hg and ag == ag else np.nan, xh=xh, xa=xa, L=L, ah=ah, aa=aa, ov=ov, un=un, T_mkt=T_m,
                     o1=f(o, 'PSCH'), ox=f(o, 'PSCD'), o2=f(o, 'PSCA'),
                     s_mkt=sup(L, ah, aa, T_m if T_m == T_m else xh + xa) if L == L and ah == ah and aa == aa else np.nan))
D = pd.DataFrame(rows).sort_values(['league', 'date']).reset_index(drop=True)
md = D.md.values
print(f'ματς {len(D)} · AH {D.s_mkt.notna().sum()} · 1Χ2 {D.o1.notna().sum()} · O/U {D.T_mkt.notna().sum()} · γκολ {D.tot.notna().sum()}')

def anchor(lam, upd_ok):
    s_adj = np.zeros(len(D)); t_adj = np.zeros(len(D))
    for lg, idx in D.groupby('league').groups.items():
        so, go = {}, {}
        for i in idx:
            r = D.loc[i]
            s = (r.xh - r.xa) + so.get(r.h, 0.0) - so.get(r.a, 0.0); t = (r.xh + r.xa) + go.get(r.h, 0.0) + go.get(r.a, 0.0)
            s_adj[i] = s; t_adj[i] = max(t, 0.8)
            if upd_ok[i]:
                if r.s_mkt == r.s_mkt:
                    e = r.s_mkt - s; so[r.h] = so.get(r.h, 0.0) + lam * e / 2; so[r.a] = so.get(r.a, 0.0) - lam * e / 2
                if r.T_mkt == r.T_mkt:
                    e = r.T_mkt - t; go[r.h] = go.get(r.h, 0.0) + lam * e / 2; go[r.a] = go.get(r.a, 0.0) + lam * e / 2
    return s_adj, t_adj
MODELS = {'LIVE': ((D.xh - D.xa).values, (D.xh + D.xa).values),
          'ΑΓΚΥΡΑ': anchor(0.5, np.ones(len(D), bool)),
          'ΑΓΚΥΡΑ-χωρις-1-6': anchor(0.5, md >= 6)}

def p_over25(T):
    return 1 - math.exp(-T) * (1 + T + T * T / 2)
def bets_for(s_arr, t_arr):
    out = []
    for i in range(len(D)):
        r = D.loc[i]
        if r.md < 6: continue
        win = '7-14' if r.md <= 13 else '15+'; s, t = s_arr[i], t_arr[i]
        lh, la = max((t + s) / 2, .05), max((t - s) / 2, .05)
        if r.s_mkt == r.s_mkt:
            dist = picks.gd_dist(lh, la)
            for side, ud, odds in ((1, r.L, r.ah), (-1, -r.L, r.aa)):
                if not (1.70 <= odds <= 2.10): continue
                pw, pp = picks.p_cover(dist, side, ud); e = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                if e >= 0.10 and (ud <= -0.5 or ud >= 0.5):
                    out.append(dict(win=win, season=r.season, mkt='AH φαβορι' if ud < 0 else 'AH dog', pnl=picks.settle(r.gd, side, ud, odds)))
        if r.o1 == r.o1:
            d = picks.gd_dist(lh, la); p1 = sum(v for k, v in d.items() if k > 0); px = d.get(0, 0.0); p2 = 1 - p1 - px
            for p, odds, hit in ((p1, r.o1, r.gd > 0), (px, r.ox, r.gd == 0), (p2, r.o2, r.gd < 0)):
                if p * odds - 1 >= 0.05:
                    typ = '1Χ2 ισοπαλια' if odds == r.ox else ('1Χ2 φαβορι (<2.0)' if odds < 2.0 else ('1Χ2 αουτσαιντερ (≥3.0)' if odds >= 3.0 else '1Χ2 μεσαια'))
                    out.append(dict(win=win, season=r.season, mkt=typ, pnl=(odds - 1) if hit else -1.0))
        if r.T_mkt == r.T_mkt and r.tot == r.tot:
            po = p_over25(t)
            if po * r.ov - 1 >= 0.05: out.append(dict(win=win, season=r.season, mkt='OVER 2.5', pnl=(r.ov - 1) if r.tot > 2.5 else -1.0))
            if (1 - po) * r.un - 1 >= 0.05: out.append(dict(win=win, season=r.season, mkt='UNDER 2.5', pnl=(r.un - 1) if r.tot < 2.5 else -1.0))
    return pd.DataFrame(out)
B = {k: bets_for(*v) for k, v in MODELS.items()}
MK = ['AH φαβορι', 'AH dog', '1Χ2 φαβορι (<2.0)', '1Χ2 μεσαια', '1Χ2 ισοπαλια', '1Χ2 αουτσαιντερ (≥3.0)', 'OVER 2.5', 'UNDER 2.5']
for win in ('7-14', '15+'):
    print(f'\n================ ΑΓΩΝΙΣΤΙΚΕΣ {win} ================')
    for mk in MK:
        line = []; st = {}
        for k, b in B.items():
            d = b[(b.win == win) & (b.mkt == mk)] if len(b) else b
            if not len(d): line.append(f'{k}: —'); st[k] = None; continue
            ps = d.groupby('season').pnl.mean(); pos, ns_ = int((ps > 0).sum()), len(ps)
            st[k] = (d.pnl.mean(), d.pnl.sum(), pos, ns_)
            line.append(f'{k}: n{len(d)} {100*d.pnl.mean():+.1f}% (±{100*d.pnl.std()/np.sqrt(len(d)):.1f}) {d.pnl.sum():+.1f}u {pos}/{ns_}')
        verdict = ''
        if st.get('LIVE') and st.get('ΑΓΚΥΡΑ'):
            a, l = st['ΑΓΚΥΡΑ'], st['LIVE']; need = 3 if a[3] >= 4 else a[3]
            verdict = '→ ΑΓΚΥΡΑ ΚΕΡΔΙΖΕΙ' if (a[0] > l[0] and a[1] >= l[1] and a[2] >= need) else '→ οχι'
        print(f'  {mk:24s} ' + ' · '.join(line) + f'  {verdict}')
