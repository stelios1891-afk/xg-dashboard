"""NFL τεστ 15 — ΑΦΕΤΗΡΙΑ Γ: λιγοτερη εμπιστοσυνη στα περσινα ματς για ομαδες που αλλαξαν πολυ (NBA «αφετηρια απο ροστερ»).

Σημερα: καθε περσινο ματς μετραει ιδια για ολες τις ομαδες (χαντ 0.3 στην 1η εβδ., συνολα 0.8).
Νεο: το βαρος των ΠΡΟΗΓΟΥΜΕΝΩΝ σεζον πολλαπλασιαζεται ανα ομαδα — ΧΩΡΙΣΤΑ για επιθεση και αμυνα:
  Γ1 συνεχεια ροστερ: (ποσοστο περσινων φασεων που επαιξαν παικτες που εμειναν / μεσος ορος)^β, β 0.5/1/2
     (επιθεση με τη συνεχεια επιθεσης, αμυνα με της αμυνας· π.χ. Seattle 2025 επιθεση 0.39/0.63 → ×0.62 με β=1)
  Γ2 νεος QB (ο QB της 1ης αγωνιστικης ≠ ο βασικος περσι): επιθεση × q, q 0.25/0.5/0.75
  Γ3 νεος προπονητης: επιθεση & αμυνα × c, c 0.5/0.75
  Γ4 συνδυασμοι των καλυτερων.
Κριτηριο: RMSE καλυτερη απο βαση v3 σε ≥4/5 σεζον 2021-25 (ολη η σεζον και εβδ 1-6). Χαντικαπ και συνολα.
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
sys.stdout.reconfigure(encoding='utf-8')


def indicators(g):
    r = pd.read_csv('nfl_data/roster_cont.csv')
    r['co'] = r.ret_o / r.ret_o.mean()
    r['cd'] = r.ret_d / r.ret_d.mean()
    reg = g[g.game_type == 'REG']
    lg = pd.concat([reg[['season', 'wk', 'home_team', 'home_qb_id', 'home_coach']].set_axis(['season', 'wk', 'team', 'qb', 'coach'], axis=1),
                    reg[['season', 'wk', 'away_team', 'away_qb_id', 'away_coach']].set_axis(['season', 'wk', 'team', 'qb', 'coach'], axis=1)])
    main_qb = lg.groupby(['season', 'team']).qb.agg(lambda s: s.value_counts().index[0] if s.notna().any() else None)
    last_coach = lg.sort_values('wk').groupby(['season', 'team']).coach.last()
    first = lg.sort_values('wk').groupby(['season', 'team']).first()
    ind = {}
    for (S, T), row in first.iterrows():
        rc = r[(r.season == S) & (r.team == T)]
        ind[(S, T)] = dict(co=float(rc.co.iloc[0]) if len(rc) else 1.0, cd=float(rc.cd.iloc[0]) if len(rc) else 1.0,
                           nqb=int((S - 1, T) in main_qb.index and main_qb.get((S - 1, T)) != row.qb),
                           nco=int((S - 1, T) in last_coach.index and last_coach.get((S - 1, T)) != row.coach))
    return ind


def teamw_fn(ind, beta=0.0, q=1.0, c=1.0):
    def f(S):
        o, d = {}, {}
        for (s, t), v in ind.items():
            if s != S:
                continue
            o[t] = (v['co'] ** beta) * (q if v['nqb'] else 1.0) * (c if v['nco'] else 1.0)
            d[t] = (v['cd'] ** beta) * (c if v['nco'] else 1.0)
        return {'o': o, 'd': d}
    return f


def main():
    g, off = M.load()
    q_ = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base3_params.json'))
    ind = indicators(g)
    d = pd.DataFrame([dict(season=s, team=t, **v) for (s, t), v in ind.items()])
    print('νεοι QB ανα σεζον:', d.groupby('season').nqb.sum().to_dict())
    print('νεοι προπονητες ανα σεζον:', d.groupby('season').nco.sum().to_dict())
    print('παραδειγμα 2025:', d[(d.season == 2025) & d.team.isin(['SEA', 'NO', 'ARI', 'PIT', 'NYJ'])].round(2).to_dict('records'))
    for kind, y, lab in (('m', 'result', 'ΧΑΝΤΙΚΑΠ'), ('t', 'total', 'ΣΥΝΟΛΑ')):
        p = P[kind]
        Fs = [G.FM0 + [f'wt_d_{K}'] for K in T8.KS] if kind == 'm' else [G.FT0]

        def run(tw):
            cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
            cfg['sos'] = p['sos']
            for k in ('HLp', 'home'):
                if k in p:
                    cfg[k] = p[k]
            if tw is not None:
                cfg['teamw'] = tw
            feats = E.build(g, off, cfg, p['win'])
            qbf = Q.qb_features(g, q_, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
            f = G.frame(g, feats, qbf)
            pr = T8.loso(f, y, Fs)
            e2 = (f[y] - pr) ** 2
            return np.sqrt(e2.groupby(f.season).mean()), np.sqrt(e2[f.wk <= 6].groupby(f.season[f.wk <= 6]).mean())

        rb, rb6 = run(None)
        print(f'\n=== {lab} ===')
        print(f"  {'παραλλαγη':34} RMSE ολη καλυτ.21-25 16-25 | εβδ1-6 καλυτ.21-25 16-25 | 2026")
        print(f"  {'βαση v3':34} {np.sqrt(np.mean(rb[S10] ** 2)):.3f}   —          | {np.sqrt(np.mean(rb6[S10] ** 2)):.3f}   —          | {rb[2026]:.3f}")
        V = {}
        for b in (0.5, 1, 2):
            V[f'Γ1 συνεχεια ροστερ β{b}'] = dict(beta=b)
        for qq in (0.25, 0.5, 0.75):
            V[f'Γ2 νεος QB επιθεση ×{qq}'] = dict(q=qq)
        for cc in (0.5, 0.75):
            V[f'Γ3 νεος προπονητης ×{cc}'] = dict(c=cc)
        V['Γ4 β1 + QB×0.5'] = dict(beta=1, q=0.5)
        V['Γ4 β1 + QB×0.5 + προπ×0.75'] = dict(beta=1, q=0.5, c=0.75)
        V['Γ4 β2 + QB×0.25'] = dict(beta=2, q=0.25)
        for name, kw in V.items():
            r, r6 = run(teamw_fn(ind, **kw))
            print(f"  {name:34} {np.sqrt(np.mean(r[S10] ** 2)):.3f}   {sum(r[s] < rb[s] - 1e-9 for s in S5)}/5 {sum(r[s] < rb[s] - 1e-9 for s in S10):2}/10 |"
                  f" {np.sqrt(np.mean(r6[S10] ** 2)):.3f}   {sum(r6[s] < rb6[s] - 1e-9 for s in S5)}/5 {sum(r6[s] < rb6[s] - 1e-9 for s in S10):2}/10 | {r[2026]:.3f}", flush=True)


if __name__ == '__main__':
    main()
