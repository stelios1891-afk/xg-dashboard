"""NFL τεστ 10: αποντες βασικοι ανα θεση (nfl_absence.py) πανω στη βαση v2 (QB ανοιγματος), LOSO 2016-25 (+2026).

Χαρακτηριστικα (γηπ − φιλ για χαντικαπ):
  F  = Out/Doubtful/εκτος ροστερ (γνωστο απο την Παρασκευη)   → αξιολογηση στη γραμμη 24ω / 3ω / κλεισιμο
  G  = F + inactive τη μερα του ματς (γνωστο ~90′ πριν)         → αξιολογηση στη γραμμη 30′ / κλεισιμο
  Q  = Questionable (μονο ως επιπλεον μετρηση)
  Συνολα: αθροισμα αποντων επιθεσης (QB/OL/WR/TE/RB) και αμυνας (EDGE/DL/LB/CB/S) και των 2 ομαδων.
Ποντοι ανα θεση = συντελεστες LOSO (αλλες σεζον) — οχι ο περιγραφικος πινακας.
Κριτηρια (προ-δηλωμενα): (1) RMSE καλυτερη απο βαση ≥4/5 σεζον 2021-25 · (2) ROI picks ≥2.5 θετικο ≥4/5 σεζον 2021-25.
Φιλτρο: κοψε picks οπου η ΔΙΚΗ ΜΑΣ ομαδα εχει ≥2 γνωστους αποντες βασικους (εκτος QB).
"""
import json
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test8 as T8
import nfl_test9 as T9
import nfl_test7 as T7
import nfl_market as K
from nfl_absence import GRPS, OFF

S5, S10 = G.S5, G.S10


def add_abs(f):
    a = pd.read_csv('nfl_data/absence_games.csv')
    h = a.rename(columns={'team': 'home_team'}).set_index(['game_id', 'home_team'])
    w = a.rename(columns={'team': 'away_team'}).set_index(['game_id', 'away_team'])
    f = f.join(h.add_prefix('h_'), on=['game_id', 'home_team']).join(w.add_prefix('a_'), on=['game_id', 'away_team'])
    f['has_abs'] = f['h_F_QB'].notna() & f['a_F_QB'].notna()
    for k in 'FGQ':
        for c in GRPS:
            f[f'{k}d_{c}'] = f[f'h_{k}_{c}'].fillna(0) - f[f'a_{k}_{c}'].fillna(0)
        f[f'{k}s_off'] = sum(f[f'h_{k}_{c}'].fillna(0) + f[f'a_{k}_{c}'].fillna(0) for c in GRPS if c in OFF)
        f[f'{k}s_def'] = sum(f[f'h_{k}_{c}'].fillna(0) + f[f'a_{k}_{c}'].fillna(0) for c in GRPS if c not in OFF)
        f[f'{k}h_n'] = sum(f[f'h_{k}_{c}'].fillna(0) for c in GRPS if c != 'QB')
        f[f'{k}a_n'] = sum(f[f'a_{k}_{c}'].fillna(0) for c in GRPS if c != 'QB')
    return f


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base2_params.json'))
    fm = add_abs(T8.base_frame(g, off, q, tg, P['m']))
    ft = add_abs(T8.base_frame(g, off, q, tg, P['t']))
    B = [G.FM0 + [f'wt_d_{K_}'] for K_ in T8.KS]
    Vm = {'βαση v2': B,
          '+F (Παρασκευη)': [b + [f'Fd_{c}' for c in GRPS] for b in B],
          '+F+Q': [b + [f'Fd_{c}' for c in GRPS] + [f'Qd_{c}' for c in GRPS] for b in B],
          '+G (90′ πριν)': [b + [f'Gd_{c}' for c in GRPS] for b in B]}
    Vt = {'βαση v2': [G.FT0], '+F': [G.FT0 + ['Fs_off', 'Fs_def']], '+G': [G.FT0 + ['Gs_off', 'Gs_def']]}
    preds = fm[['game_id', 'season', 'wk', 'home_team', 'away_team', 'result', 'total', 'spread_line', 'total_line',
                'Fh_n', 'Fa_n', 'Gh_n', 'Ga_n']].copy()
    for kind, f, V, y, lab in (('m', fm, Vm, 'result', 'ΧΑΝΤΙΚΑΠ'), ('t', ft, Vt, 'total', 'ΣΥΝΟΛΑ')):
        print(f'\n=== (1) ΑΚΡΙΒΕΙΑ {lab} ===')
        rb = None
        for name, Fs in V.items():
            pr = T8.loso(f, y, Fs)
            r = T8.rm_by_season(f, y, pr)
            if rb is None:
                rb = r
            b5 = sum(r[s] < rb[s] - 1e-9 for s in S5); b10 = sum(r[s] < rb[s] - 1e-9 for s in S10)
            print(f"  {name:15} RMSE 2016-25 {np.sqrt(np.mean(r[S10] ** 2)):.3f} · καλυτερη 2021-25 {b5}/5 · 2016-25 {b10}/10 · 2026 {r.get(2026, np.nan):.3f}")
            preds[f'{kind}|{name}'] = pr.values
        Fl = (B[3] if kind == 'm' else G.FT0) + (V['+F (Παρασκευη)'][3][len(B[3]):] if kind == 'm' else ['Fs_off', 'Fs_def'])
        c = np.linalg.lstsq(np.c_[np.ones((f.season <= 2025).sum()), f[f.season <= 2025][Fl].fillna(0).values],
                            f[f.season <= 2025][y].values, rcond=None)[0]
        n0 = len(B[3]) if kind == 'm' else len(G.FT0)
        print('  ποντοι ανα αποντα βασικο (F, ολες οι σεζον):', {k.replace('Fd_', '').replace('Fs_', ''): round(v, 2) for k, v in zip(Fl[n0:], c[n0 + 1:])})
    preds.to_csv('nfl_data/test10_preds.csv', index=False)

    print('\n=== (2) PICKS ΧΑΝΤΙΚΑΠ ανα ωρα (≥2.5 π.) ===')
    mk = K.market_feats(g, HLm=4)
    x = preds.merge(mk, on='game_id', how='left')
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    for name, Hs in (('βαση v2', ['wk', '24', '3', '0.5', 'close']), ('+F (Παρασκευη)', ['24', '3', 'close']),
                     ('+G (90′ πριν)', ['0.5', 'close'])):
        x['mp'] = x[f'm|{name}']
        x['mp_a'] = T7.loso_blend(x, 'result', ['mp', 'mk_d'])
        for col, lab2 in (('mp', ''), ('mp_a', ' +αγκυρα')):
            for H in Hs:
                z = T9.picks_at(x, H, col, o)
                print(T9.roi_line(f'{name}{lab2} · {H}', z, z.pick))
    print('\n=== (3) ΦΙΛΤΡΟ: η δικη μας ομαδα εχει ≥2 γνωστους αποντες βασικους (εκτος QB) ===')
    for name, H, k in (('βαση v2', 'wk', 'F'), ('βαση v2', '24', 'F'), ('+F (Παρασκευη)', '24', 'F'), ('βαση v2', '0.5', 'G')):
        x['mp'] = x[f'm|{name}']
        x['mp_a'] = T7.loso_blend(x, 'result', ['mp', 'mk_d'])
        for col, lab2 in (('mp', ''), ('mp_a', ' +αγκυρα')):
            z = T9.picks_at(x, H, col, o)
            ours = np.where(z.side > 0, z[f'{k}h_n'], z[f'{k}a_n'])
            T9.filt(f'{name}{lab2} · {H} · {k}', z, pd.Series(ours >= 2, index=z.index))


if __name__ == '__main__':
    main()
