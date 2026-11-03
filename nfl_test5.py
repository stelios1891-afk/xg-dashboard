"""NFL τεστ 5: αφετηρια σεζον απο win totals (+ αλλαγη προπονητη), LOSO 2016-25 (+2026).

Βαση = ομαδες + QB + success rate + ειδικες ομαδες (τεστ 4).
Νεο χαρακτηριστικο:  wt_d = (wpct γηπ − wpct φιλ) × K/(K + n)
   wpct = αναμενομενες νικες/ματς απο win totals (κεντραρισμενο στη σεζον), n = μεσος αριθμος φετινων ματς των 2 ομαδων
   πριν απο αυτο → πληρες βαρος στην 1η αγωνιστικη, σβηνει οσο μαζευονται ματς. K ∈ {2, 4, 8, 16, ∞(σταθερο)}.
   Συντελεστης ΚΑΙ K μετριουνται μονο στις αλλες σεζον.
Παραλλαγη Π: + νεος προπονητης (διαφορετικος head coach απο την περσινη τελευταια αγωνιστικη) × K/(K+n), γηπ − φιλ.
Κριτηριο (προ-δηλωμενο): RMSE χαντικαπ εβδ 1-6 καλυτερη απο βαση σε ≥4/5 σεζον 2021-25. Δειχνουμε και ολη τη σεζον + ROI.
"""
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_mech as X
import nfl_test as T

FM = ['cl_epa_diff', 'pts_diff', 'qb_d', 'cl_sr_diff', 'st_net_diff']
FT = ['pts_sum', 'cl_epa_sum', 'plays_sum', 'qb_s', 'cl_sr_sum']
KS = [2, 4, 8, 16, None]
S5, S10 = list(range(2021, 2026)), list(range(2016, 2026))


def add_feats(f, g):
    w = pd.read_csv('nfl_data/win_totals.csv')
    w['wc'] = w.wpct - w.groupby('season').wpct.transform('mean')
    wm = w.set_index(['season', 'team']).wc
    f['wt_h'] = [wm.get((s, t), 0.0) for s, t in zip(f.season, f.home_team)]
    f['wt_a'] = [wm.get((s, t), 0.0) for s, t in zip(f.season, f.away_team)]
    # φετινα ματς πριν απο αυτο (κανονικη περιοδος)
    gg = g[g.game_type == 'REG'].sort_values('t')
    long = pd.concat([gg[['game_id', 'season', 't', 'home_team']].set_axis(['game_id', 'season', 't', 'team'], axis=1),
                      gg[['game_id', 'season', 't', 'away_team']].set_axis(['game_id', 'season', 't', 'team'], axis=1)])
    long = long.sort_values('t')
    long['n'] = long.groupby(['season', 'team']).cumcount()
    nm = long.set_index(['game_id', 'team']).n
    f['n_h'] = [nm.get((a, b), 0) for a, b in zip(f.game_id, f.home_team)]
    f['n_a'] = [nm.get((a, b), 0) for a, b in zip(f.game_id, f.away_team)]
    f['n'] = (f.n_h + f.n_a) / 2
    # νεος προπονητης: διαφορετικος απο τον head coach της τελευταιας περσινης αγωνιστικης
    last = long.merge(g[['game_id', 'home_team', 'home_coach', 'away_coach']], on='game_id')
    last['coach'] = np.where(last.team == last.home_team, last.home_coach, last.away_coach)
    lc = last.sort_values('t').groupby(['season', 'team']).coach.last()
    f['nc_h'] = [int(lc.get((s - 1, t), c) != c) for s, t, c in zip(f.season, f.home_team, f.home_coach)]
    f['nc_a'] = [int(lc.get((s - 1, t), c) != c) for s, t, c in zip(f.season, f.away_team, f.away_coach)]
    for K in KS:
        dec = 1.0 if K is None else K / (K + f.n)
        f[f'wt_d_{K}'] = (f.wt_h - f.wt_a) * dec
        f[f'nc_d_{K}'] = (f.nc_h - f.nc_a) * dec
    return f


def loso(f, feats_by_K):
    """Για καθε σεζον: διαλεγει K με RMSE στις αλλες σεζον, επιστρεφει προβλεψεις."""
    out = []
    for S in range(2016, 2027):
        tr = f[(f.season != S) & (f.season <= 2025)]
        best = None
        for K, F in feats_by_K.items():
            c = T.ols(tr, F, 'result')
            sc = np.mean((tr.result - T.pred(tr, F, c)) ** 2)
            if best is None or sc < best[0]:
                best = (sc, K, F, c)
        _, K, F, c = best
        te = f[f.season == S].copy()
        te['mp'] = T.pred(te, F, c)
        te['K'] = K
        te['coef'] = c[-1]
        out.append(te)
    return pd.concat(out)


def report(lab, p, base):
    print(f'\n=== {lab} ===')
    print(f"{'σεζον':6} K   συντ | εβδ1-6 RMSE βαση/νεο/αγορα     | ολη RMSE βαση/νεο")
    w16, wall = [], []
    for S in range(2016, 2027):
        a, b = base[base.season == S], p[p.season == S]
        e1 = a.wk <= 6
        r = lambda d, c: np.sqrt(np.mean((d.result - d[c]) ** 2))
        x1, y1, m1 = r(a[e1], 'mp'), r(b[e1.values], 'mp'), r(a[e1], 'spread_line')
        x2, y2 = r(a, 'mp'), r(b, 'mp')
        w16.append((S, y1 < x1)); wall.append((S, y2 < x2))
        print(f"{S:6} {str(b.K.iloc[0]):4} {b.coef.iloc[0]:+5.1f} | {x1:6.3f} {y1:6.3f} {m1:6.3f} {'✓' if y1 < x1 else '✗'} | {x2:6.3f} {y2:6.3f} {'✓' if y2 < x2 else '✗'}")
    print(f"εβδ 1-6 καλυτερη: 2021-25 {sum(v for s, v in w16 if s in S5)}/5 · 2016-25 {sum(v for s, v in w16 if s in S10)}/10"
          f" | ολη: 2021-25 {sum(v for s, v in wall if s in S5)}/5 · 2016-25 {sum(v for s, v in wall if s in S10)}/10")
    for nm, d in (('ολη', p), ('εβδ 1-6', p[p.wk <= 6])):
        d = d[d.season <= 2025]
        L, y, mp = d.spread_line.values, d.result.values, d.mp.values
        rm, rk = np.sqrt(np.mean((y - mp) ** 2)), np.sqrt(np.mean((y - L) ** 2))
        b = np.polyfit(mp - L, y - L, 1)[0]
        (n, pl), = T.roi(mp - L, y - L, T.dec(d.home_spread_odds), T.dec(d.away_spread_odds), [2.5]).values()
        print(f"  {nm}: RMSE {rm:.3f} (αγορα {rk:.3f}) b {b:+.2f} · ROI ≥2.5 π. {n} picks {100 * pl / max(n, 1):+.1f}%")


def main():
    g, off = M.load()
    q = Q.load_qb()
    f = X.frame(g, off, q, stats=('cl_epa', 'pts', 'plays', 'cl_sr', 'st_net'))
    f = add_feats(f, g)
    base = loso(f, {'-': FM})
    report('ΒΑΣΗ (τεστ 4)', base, base)
    p1 = loso(f, {K: FM + [f'wt_d_{K}'] for K in KS})
    report('Τ5α: + WIN TOTALS', p1, base)
    p2 = loso(f, {K: FM + [f'wt_d_{K}', f'nc_d_{K}'] for K in KS})
    report('Τ5β: + WIN TOTALS + ΝΕΟΣ ΠΡΟΠΟΝΗΤΗΣ', p2, base)
    p1.to_csv('nfl_data/test5_preds.csv', index=False)
    # ελεγχος: ποσοι νεοι προπονητες ανα σεζον
    nc = pd.concat([f[['season', 'home_team', 'nc_h']].set_axis(['s', 't', 'nc'], axis=1),
                    f[['season', 'away_team', 'nc_a']].set_axis(['s', 't', 'nc'], axis=1)]).drop_duplicates(['s', 't'])
    print('\nνεοι προπονητες ανα σεζον:', nc.groupby('s').nc.sum().to_dict())


if __name__ == '__main__':
    main()
