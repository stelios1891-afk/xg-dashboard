"""NFL τεστ 16 — ΓΗΠΕΔΑ, πανω στη βαση v3 (QB ανοιγματος, LOSO 2016-25 +2026). Ολα γνωστα απο την αρχη της σεζον.

Ειδος γηπεδου του ΜΑΤΣ (απο το γηπεδο, οχι απο το αν ανοιξε η σκεπη):
  σταθερο κλειστο (DET, MIN, NO, LV, LA/LAC SoFi) · συρομενη σκεπη (ATL, DAL, HOU, IND, ARI — κλεινει ~85%) · ανοιχτο
  χλοοταπητας: συνθετικο (fieldturf, a_turf, astroturf, matrix, sport) / φυσικο · υψομετρο: Denver
ΣΥΝΟΛΑ
  Σ1 + κλειστο & συρομενη (σημαιες)        Σ2 + Σ1 με «καθαρες» δυναμεις (η μηχανη μετραει το κλειστο ξεχωριστα)
  Σ3 + συνθετικο                            Σ4 + Denver                    Σ5 ολα
ΧΑΝΤΙΚΑΠ (γηπ − φιλ)
  Χ1 εδρα Denver (υψομετρο)                 Χ2 γηπεδουχος σε κλειστο (εδρα αλλη σε κλειστα;)
  Χ3 ομαδα κλειστου που παιζει εξω απο εβδ 13 (κρυο) · Χ4 διαφορα χλοοταπητα (γηπ συνθετικο & φιλοξ φυσικο ή αναποδα)
  Χ5 ολα · Χ6 Χ5 με «καθαρες» δυναμεις
Κριτηριο: RMSE καλυτερη απο βαση v3 σε ≥4/5 σεζον 2021-25 (ολη η σεζον).
"""
import json, sys
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test8 as T8

S5, S10 = G.S5, G.S10
FIXED = {'DET', 'MIN', 'NO', 'LV', 'LA', 'LAC'}
RETR = {'ATL', 'DAL', 'HOU', 'IND', 'ARI'}
sys.stdout.reconfigure(encoding='utf-8')


def venue_feats(f, g):
    gg = g.set_index('game_id')
    sid = f.game_id.map(gg.stadium_id)
    roof = f.game_id.map(gg.roof)
    surf = f.game_id.map(gg.surface).fillna('').str.strip()
    # το γηπεδο του ματς: σταθερο κλειστο / συρομενη / ανοιχτο (απο το ποιος ειναι γηπεδουχος — ουδετερα απο το roof)
    neutral = f.neutral == 1
    f['v_fixed'] = np.where(neutral, roof.isin(['dome']).astype(int), f.home_team.isin(FIXED).astype(int))
    f['v_retr'] = np.where(neutral, 0, f.home_team.isin(RETR).astype(int))
    turf = surf.str.contains('turf|astro|matrix|sport')
    # κενα: συνηθισμενο ταπητα του γηπεδου
    f['v_turf'] = turf.astype(int)
    f['v_den'] = ((f.home_team == 'DEN') & ~neutral).astype(int)
    # εδρα ομαδας: συνθετικο ή οχι (πλειοψηφια εντος ματς της σεζον)
    reg = g[(g.game_type == 'REG') & (g.location == 'Home')].copy()
    reg['turf'] = reg.surface.fillna('').str.strip().str.contains('turf|astro|matrix|sport').astype(int)
    hturf = reg.groupby(['season', 'home_team']).turf.mean().round().to_dict()
    ht = np.array([hturf.get((s, t), 0) for s, t in zip(f.season, f.home_team)])
    at = np.array([hturf.get((s, t), 0) for s, t in zip(f.season, f.away_team)])
    f['h_turfmis'] = np.where(neutral, 0, (ht == 1) & (at == 0)).astype(int) - np.where(neutral, 0, (ht == 0) & (at == 1)).astype(int)
    f['h_den'] = f.v_den
    f['h_dome'] = (f.v_fixed + f.v_retr).clip(0, 1) * (~neutral)
    a_dome = f.away_team.isin(FIXED | RETR)
    h_dome_team = f.home_team.isin(FIXED | RETR)
    f['h_cold'] = ((f.wk >= 13) & a_dome & ~h_dome_team & ~neutral).astype(int) - ((f.wk >= 13) & h_dome_team & ~a_dome & neutral).astype(int)
    return f


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base3_params.json'))

    def frame(p, venue):
        cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
        cfg['sos'] = p['sos']
        for k in ('HLp', 'home'):
            if k in p:
                cfg[k] = p[k]
        if venue:
            cfg['venue'] = True
        feats = E.build(g, off, cfg, p['win'])
        qbf = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
        return venue_feats(G.frame(g, feats, qbf), g)

    def score(f, y, Fs):
        pr = T8.loso(f, y, Fs)
        e2 = (f[y] - pr) ** 2
        return np.sqrt(e2.groupby(f.season).mean()), pr

    for kind, y, lab in (('t', 'total', 'ΣΥΝΟΛΑ'), ('m', 'result', 'ΧΑΝΤΙΚΑΠ')):
        p = P[kind]
        f0, f1 = frame(p, False), frame(p, True)
        B = [G.FM0 + [f'wt_d_{K}'] for K in T8.KS] if kind == 'm' else [G.FT0]
        add = lambda cols: [b + cols for b in B]
        if kind == 't':
            V = {'βαση v3': (f0, B), 'Σ1 +κλειστο/συρομενη': (f0, add(['v_fixed', 'v_retr'])),
                 'Σ2 Σ1 + καθαρες δυναμεις': (f1, add(['v_fixed', 'v_retr'])), 'Σ3 +συνθετικο': (f0, add(['v_turf'])),
                 'Σ4 +Denver': (f0, add(['v_den'])), 'Σ5 ολα': (f0, add(['v_fixed', 'v_retr', 'v_turf', 'v_den'])),
                 'Σ5 ολα + καθαρες δυναμεις': (f1, add(['v_fixed', 'v_retr', 'v_turf', 'v_den']))}
        else:
            V = {'βαση v3': (f0, B), 'Χ1 εδρα Denver': (f0, add(['h_den'])), 'Χ2 γηπ σε κλειστο': (f0, add(['h_dome'])),
                 'Χ3 ομαδα κλειστου εξω απο εβδ 13': (f0, add(['h_cold'])), 'Χ4 διαφορα χλοοταπητα': (f0, add(['h_turfmis'])),
                 'Χ5 ολα': (f0, add(['h_den', 'h_dome', 'h_cold', 'h_turfmis'])),
                 'Χ6 ολα + καθαρες δυναμεις': (f1, add(['h_den', 'h_dome', 'h_cold', 'h_turfmis']))}
        print(f'\n=== {lab} ===')
        rb = None
        for name, (f, Fs) in V.items():
            r, pr = score(f, y, Fs)
            if rb is None:
                rb = r
            print(f"  {name:34} RMSE {np.sqrt(np.mean(r[S10] ** 2)):.3f} · καλυτερη 2021-25 {sum(r[s] < rb[s] - 1e-9 for s in S5)}/5 · 2016-25 {sum(r[s] < rb[s] - 1e-9 for s in S10)}/10 · 2026 {r.get(2026, np.nan):.3f}", flush=True)
        Fl = V['Σ5 ολα' if kind == 't' else 'Χ5 ολα'][1][-1]
        c = np.linalg.lstsq(np.c_[np.ones((f0.season <= 2025).sum()), f0[f0.season <= 2025][Fl].fillna(0).values], f0[f0.season <= 2025][y].values, rcond=None)[0]
        print('  συντελεστες (ποντοι):', {k: round(v, 2) for k, v in zip(Fl[-4:], c[-4:])})
        hist = f0[f0.season <= 2025]
        if kind == 't':
            for col in ('v_fixed', 'v_retr', 'v_turf', 'v_den'):
                print(f'   {col}: ματς {int(hist[col].sum())}')
        else:
            for col in ('h_den', 'h_dome', 'h_cold', 'h_turfmis'):
                print(f'   {col}: ματς ≠0 {int((hist[col] != 0).sum())}')


if __name__ == '__main__':
    main()
