"""NFL τεστ 18 — ΥΠΕΡΩΡΙΕΣ & ΟΥΔΕΤΕΡΑ ΓΗΠΕΔΑ, πανω στις βασεις v3 (χαντ) / v4 (συνολα ανοιγματος) / v5 (συνολα με καιρο).

Υπερωριες (188 ματς 2015-26, μεσος ορος 4.6 ποντοι παρατασης· nfl_data/reg_scores.csv απο pbp):
  Υ1 οι δυναμεις «ποντων» μετριουνται με το σκορ ΚΑΝΟΝΙΚΟΥ χρονου (οι ποντοι της παρατασης ειναι τυχαιοι)
  Υ2 συνολα: + πιθανοτητα παρατασης = max(0, 3 − |προβλεψη χαντικαπ|) (κοντινα ματς → περισσοτερες παρατασεις)
Ουδετερα γηπεδα (Λονδινο, Γερμανια, Μεξικο, Βραζιλια...):
  Ο1 χαντικαπ: η σταθερη εδρα ΔΕΝ δινεται σε ουδετερο (σημερα ο σταθερος ορος πεφτει σε ολα τα ματς)
  Ο2 συνολα: σημαια ουδετερου
Κριτηριο: RMSE καλυτερη σε ≥4/5 σεζον 2021-25.
"""
import json, sys
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test8 as T8
import nfl_test16 as T16
import nfl_test17 as T17

S5, S10 = G.S5, G.S10
sys.stdout.reconfigure(encoding='utf-8')


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base5_params.json', encoding='utf-8'))
    rs = pd.read_csv('nfl_data/reg_scores.csv').set_index('game_id')
    off_reg = off.copy()
    side_home = off_reg.home >= 0  # home=+1 γηπ, −1 φιλοξ, 0 ουδετερο (γηπ-πλευρα ορισμενη απο games)
    hs = off_reg.game_id.map(rs.home_reg)
    as_ = off_reg.game_id.map(rs.away_reg)
    hteam = off_reg.game_id.map(g.set_index('game_id').home_team)
    off_reg['pts'] = np.where(off_reg.team == hteam, hs, as_)
    off_reg['pts'] = off_reg.pts.fillna(off.pts)
    b5 = pd.read_csv('nfl_data/base5_preds.csv')[['game_id', 'mp']]

    def frame(p, o):
        cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
        if p['sos'] is not None:
            cfg['sos'] = p['sos']
        for k in ('HLp', 'home'):
            if k in p:
                cfg[k] = p[k]
        feats = E.build(g, o, cfg, p['win'])
        qbf = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
        f = T17.add_wx(T16.venue_feats(G.frame(g, feats, qbf), g), g)
        f = f.merge(b5, on='game_id', how='left')
        f['ot_p'] = (3 - f.mp.abs()).clip(0, None)
        f['hflag'] = 1 - f.neutral
        return f

    def show(lab, V, y):
        rb = None
        for name, (f, Fs) in V.items():
            pr = T8.loso(f, y, Fs)
            r = np.sqrt(((f[y] - pr) ** 2).groupby(f.season).mean())
            if rb is None:
                rb = r
            print(f"  {lab} {name:34} RMSE {np.sqrt(np.mean(r[S10] ** 2)):.3f} · καλυτερη 2021-25 {sum(r[s] < rb[s] - 1e-9 for s in S5)}/5 · 2016-25 {sum(r[s] < rb[s] - 1e-9 for s in S10)}/10 · 2026 {r.get(2026, np.nan):.3f}", flush=True)

    pm = P['m']
    fm0, fm1 = frame(pm, off), frame(pm, off_reg)
    B = [G.FM0 + [f'wt_d_{K}'] for K in T8.KS]
    print('=== ΧΑΝΤΙΚΑΠ (βαση v3) ===')
    print('  ουδετερα ματς κανονικης 2016-25:', int(fm0[(fm0.season <= 2025)].neutral.sum()))
    show('', {'βαση v3': (fm0, B), 'Υ1 ποντοι κανονικου χρονου': (fm1, B),
              'Ο1 οχι εδρα σε ουδετερο': (fm0, [b + ['hflag'] for b in B]),
              'Υ1 + Ο1': (fm1, [b + ['hflag'] for b in B])}, 'result')
    pt = P['t']
    ft0, ft1 = frame(pt, off), frame(pt, off_reg)
    F4 = G.FT0 + pt['FT_extra']
    F5 = F4 + pt['WX']
    for lab, F in (('ΣΥΝΟΛΑ ανοιγματος (v4)', F4), ('ΣΥΝΟΛΑ με καιρο (v5)', F5)):
        print(f'\n=== {lab} ===')
        show('', {'βαση': (ft0, [F]), 'Υ1 ποντοι κανονικου χρονου': (ft1, [F]), 'Υ2 + πιθανοτητα παρατασης': (ft0, [F + ['ot_p']]),
                  'Ο2 + ουδετερο': (ft0, [F + ['neutral']]), 'Υ1 + Υ2 + Ο2': (ft1, [F + ['ot_p', 'neutral']])}, 'total')
    h = ft0[ft0.season <= 2025]
    c = np.linalg.lstsq(np.c_[np.ones(len(h)), h[F4 + ['ot_p', 'neutral']].values], h.total.values, rcond=None)[0]
    print(f'\n  συντελεστες συνολων: πιθανοτητα παρατασης {c[-2]:+.2f} π. ανα μοναδα (κοντινο ματς |χαντ| 0 → +{3 * c[-2]:.1f} π.) · ουδετερο {c[-1]:+.2f}')
    h = fm0[fm0.season <= 2025]
    c = np.linalg.lstsq(np.c_[np.ones(len(h)), h[B[3] + ['hflag']].values], h.result.values, rcond=None)[0]
    print(f'  χαντικαπ: σταθερος ορος (ουδετερο) {c[0]:+.2f} · εδρα (μη ουδετερο) {c[-1]:+.2f}')


if __name__ == '__main__':
    main()
