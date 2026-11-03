"""NFL τεστ 8: πανω στη ΒΑΣΗ v2 (QB ανοιγματος) — (1) αφετηρια: συνεχεια ροστερ + αποδοσεις Super Bowl,
(2) τυχη: κλεψιματα, κοκκινη ζωνη, field goals (ομαδας & αντιπαλου απεναντι της). LOSO 2016-25 (+2026).

(1) d_ret_o/d_ret_d/d_inc_o/d_inc_d (γηπ − φιλ, nfl_extra.roster_cont) και sb_d (ln πιθανοτητας SB γηπ − φιλ),
    × K/(K+n) οπως τα win totals (n = φετινα ματς)· K εμφωλευμενο.
(2) Για καθε ομαδα πριν το ματς: σταθμισμενος μεσος (μισο βαρος/10 εβδ., 2 σεζον, μαζεμα n0) του ποσοστου
    INT/att, TD/κοκκινη ζωνη, FG% — δικα της και του αντιπαλου απεναντι της — μειον μεσο λιγκας.
    Υποθεση: η «τυχη» γυριζει στον μεσο ορο → ο συντελεστης λεει ποσο υπερ/υποτιμα το μοντελο τις «τυχερες».
Κριτηριο: RMSE καλυτερη απο τη βαση v2 σε ≥4/5 σεζον 2021-25· για οτι περασει → αξιολογηση στο ανοιγμα (τεστ 7).
"""
import json
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test as T
import nfl_test5 as T5
import nfl_test7 as T7

S5, S10 = G.S5, G.S10
KS = [2, 4, 8, 16, None]


def base_frame(g, off, q, tg, p):
    cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
    if p['sos'] is not None:
        cfg['sos'] = p['sos']
    for k in ('HLp', 'home', 'post', 'nseas'):          # βαση v3+: επιπλεον ρυθμισεις αφετηριας (τεστ 13)
        if k in p:
            cfg[k] = p[k]
    feats = E.build(g, off, cfg, p['win'])
    qbf = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
    return G.frame(g, feats, qbf)


def add_start(f):
    r = pd.read_csv('nfl_data/roster_cont.csv').set_index(['season', 'team'])
    sb = pd.read_csv('nfl_data/sb_odds.csv').set_index(['season', 'team']).sb
    for c in ('ret_o', 'ret_d', 'inc_o', 'inc_d'):
        mu = r[c].mean()
        h = np.array([r[c].get((s, t), mu) for s, t in zip(f.season, f.home_team)])
        a = np.array([r[c].get((s, t), mu) for s, t in zip(f.season, f.away_team)])
        f[f'd_{c}'] = h - a
    f['sb_d'] = [sb.get((s, h), 0) - sb.get((s, a), 0) for s, h, a in zip(f.season, f.home_team, f.away_team)]
    for K in KS:
        dec = 1.0 if K is None else K / (K + f.n)
        for c in ('d_ret_o', 'd_ret_d', 'd_inc_o', 'd_inc_d', 'sb_d'):
            f[f'{c}_{K}'] = f[c] * dec
    return f


def add_luck(f, g, HLl=10, n0=None):
    L = pd.read_csv('nfl_data/luck_games.csv')
    t = g.set_index('game_id').t
    L['t'] = L.game_id.map(t)
    L = L[L.t.notna()]
    rates = {'int': ('ints', 'att', 150), 'rz': ('rz_td', 'rz', 20), 'fg': ('fgm', 'fga', 15),
             'oint': ('o_ints', 'o_att', 150), 'orz': ('o_rz_td', 'o_rz', 20), 'ofg': ('o_fgm', 'o_fga', 15)}
    lg = {k: L[a].sum() / L[b].sum() for k, (a, b, _) in rates.items()}
    out = []
    for t_now, wk in f.groupby('t'):
        S = int(wk.season.iloc[0])
        x = L[(L.t < t_now) & (L.season >= S - 1)]
        w = 0.5 ** ((t_now - x.t) / HLl)
        agg = {}
        for k, (a, b, nn) in rates.items():
            num = (w * x[a]).groupby(x.team).sum()
            den = (w * x[b]).groupby(x.team).sum()
            agg[k] = ((num + nn * lg[k]) / (den + nn) - lg[k]).to_dict()
        for r in wk.itertuples():
            d = {'game_id': r.game_id}
            for k in rates:
                hv, av = agg[k].get(r.home_team, 0), agg[k].get(r.away_team, 0)
                d[f'L_{k}_d'], d[f'L_{k}_s'] = hv - av, hv + av
            out.append(d)
    return f.merge(pd.DataFrame(out), on='game_id', how='left')


def loso(f, y, Fs):
    """Fs: λιστα εναλλακτικων λιστων χαρακτηριστικων (π.χ. ανα K) → εμφωλευμενη επιλογη."""
    out = pd.Series(np.nan, index=f.index)
    hist = f[f.season <= 2025]
    for S in range(2016, 2027):
        tr = hist[hist.season != S]
        best = None
        for F in Fs:
            c = T.ols(tr, F, y)
            sc = np.mean((tr[y] - T.pred(tr, F, c)) ** 2)
            if best is None or sc < best[0]:
                best = (sc, F, c)
        te = f.season == S
        out[te] = T.pred(f[te].fillna(0), best[1], best[2])
    return out


def rm_by_season(f, y, p):
    return np.sqrt(((f[y] - p) ** 2).groupby(f.season).mean())


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base2_params.json'))
    res = {}
    for kind, y, lab in (('m', 'result', 'ΧΑΝΤΙΚΑΠ'), ('t', 'total', 'ΣΥΝΟΛΑ')):
        f = base_frame(g, off, q, tg, P[kind])
        f = add_start(f)
        f = add_luck(f, g)
        if kind == 'm':
            B = [G.FM0 + [f'wt_d_{K}'] for K in KS]
            V = {
                'βαση v2': B,
                '+ροστερ': [b + [f'{c}_{K}' for c in ('d_ret_o', 'd_ret_d', 'd_inc_o', 'd_inc_d')] for b, K in zip(B, KS)],
                '+Super Bowl': [b + [f'sb_d_{K}'] for b, K in zip(B, KS)],
                '+τυχη': [b + ['L_int_d', 'L_rz_d', 'L_fg_d', 'L_oint_d', 'L_orz_d', 'L_ofg_d'] for b in B],
            }
            V['+ολα'] = [a + [c for c in V['+Super Bowl'][i][-1:]] + V['+τυχη'][i][len(B[i]):] for i, a in enumerate(V['+ροστερ'])]
        else:
            B = [G.FT0]
            V = {
                'βαση v2': B,
                '+ροστερ': [G.FT0 + [f'{c}_{K}' for c in ('d_ret_o', 'd_ret_d', 'd_inc_o', 'd_inc_d')] for K in KS],
                '+τυχη': [G.FT0 + ['L_int_s', 'L_rz_s', 'L_fg_s', 'L_oint_s', 'L_orz_s', 'L_ofg_s']],
            }
        print(f'\n=== {lab} ===')
        rb = None
        for name, Fs in V.items():
            pr = loso(f, y, Fs)
            r = rm_by_season(f, y, pr)
            if rb is None:
                rb = r
            b5 = sum(r[s] < rb[s] - 1e-9 for s in S5); b10 = sum(r[s] < rb[s] - 1e-9 for s in S10)
            tot = np.sqrt(np.mean(r[S10] ** 2))
            print(f"  {name:12} RMSE 2016-25 {tot:.3f} · καλυτερη απο βαση 2021-25 {b5}/5 · 2016-25 {b10}/10 · 2026 {r.get(2026, np.nan):.3f} | "
                  + ' '.join(f"{s % 100}:{r[s]:.2f}" for s in r.index))
            res[(kind, name)] = (f, pr)
        # συντελεστες τυχης (ολες οι σεζον) για ερμηνεια
        Fl = (G.FM0 + ['wt_d_16'] if kind == 'm' else G.FT0) + [c for c in f.columns if c.startswith('L_') and c.endswith('_d' if kind == 'm' else '_s')]
        c = T.ols(f[f.season <= 2025].fillna(0), Fl, y)
        print('  συντελεστες τυχης (ποντοι ανα +1% αποκλιση):', {k: round(v / 100, 2) for k, v in zip(Fl[-6:], c[-6:])})
        if kind == 'm':
            Fr = G.FM0 + ['wt_d_16', 'd_ret_o_16', 'd_ret_d_16', 'd_inc_o_16', 'd_inc_d_16', 'sb_d_16']
            c = T.ols(f[f.season <= 2025].fillna(0), Fr, y)
            print('  συντελεστες αφετηριας (K=16):', {k: round(v, 2) for k, v in zip(Fr[-6:], c[-6:])})
    pickle_out = {f'{k}|{n}': v[1] for (k, n), v in res.items()}
    pd.DataFrame(pickle_out).to_csv('nfl_data/test8_preds_raw.csv', index=False)
    # αξιολογηση στο ανοιγμα για ολες τις παραλλαγες χαντικαπ (με και χωρις αγκυρα αγορας)
    import nfl_market as K
    mk = K.market_feats(g, HLm=4)
    fm = res[('m', 'βαση v2')][0]
    ft = res[('t', 'βαση v2')][0]
    out = fm[['game_id', 'season', 'wk', 'result', 'total', 'spread_line', 'total_line']].copy()
    out['tp'] = res[('t', 'βαση v2')][1].values
    for name in ('βαση v2', '+ροστερ', '+Super Bowl', '+τυχη', '+ολα'):
        out[f'mp_{name}'] = res[('m', name)][1].values
    out = out.merge(mk, on='game_id', how='left')
    out.to_csv('nfl_data/test8_preds.csv', index=False)
    for name in ('βαση v2', '+ροστερ', '+Super Bowl', '+τυχη', '+ολα'):
        x = out.copy()
        x['mp'] = x[f'mp_{name}']
        x['mp_a'] = T7.loso_blend(x, 'result', ['mp', 'mk_d'])
        o = pd.read_csv('nfl_data/sbr_slots.csv')
        o = o[(o.book == 'cons') & (o.H == 'wk')][['game_id', 'spread', 'h_dec', 'a_dec']]
        z = x.merge(o, on='game_id').dropna(subset=['spread'])
        for col, lab2 in (('mp', 'χωρις αγκυρα'), ('mp_a', 'με αγκυρα')):
            e = z[col] - z.spread
            pk = e.abs() >= 2.5
            sd = np.sign(e)
            rr = (z.result - z.spread) * sd
            od = np.where(sd > 0, z.h_dec, z.a_dec); od = np.where(np.isnan(od), 1.909, od)
            pnl = np.where(rr > 0, od - 1, np.where(rr < 0, -1, 0))
            h = z.season.between(2019, 2025)
            per = {S: pnl[pk & (z.season == S)].sum() / max((pk & (z.season == S)).sum(), 1) for S in range(2019, 2027)}
            pos = sum(per[S] > 0 for S in S5)
            print(f"  ΑΝΟΙΓΜΑ {name:12} {lab2:13}: picks {int((pk & h).sum()):4} ROI 19-25 {100 * pnl[pk & h].sum() / max((pk & h).sum(), 1):+5.1f}% · 21-25 θετ {pos}/5 · 2026 {int((pk & (z.season == 2026)).sum())} picks {pnl[pk & (z.season == 2026)].sum():+.1f}μ | "
                  + ' '.join(f"{S % 100}:{100 * v:+.0f}%" for S, v in per.items() if S <= 2025))


if __name__ == '__main__':
    main()
