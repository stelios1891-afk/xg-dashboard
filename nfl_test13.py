"""NFL τεστ 13 — ΑΦΕΤΗΡΙΑ Α (πορεια NBA, ενα πραγμα τη φορα πανω στη βαση v2, QB ανοιγματος, LOSO 2016-25 +2026).

Α1 playoffs: μετρανε στις δυναμεις (σημερα) ή οχι
Α2 ποσες προηγουμενες σεζον μετρανε: 1 / 2 (σημερα) / 3
Α3 ΞΕΧΩΡΙΣΤΟ σβησιμο του περσινου καθως προχωραει η φετινη σεζον: σημερα τα περσινα σβηνουν με τον ιδιο ρυθμο με
   τα φετινα (μισο βαρος/10 εβδ.) × PREV. Εδω: βαρος περσινων στην 1η εβδομαδα = PREV, και μετα μισο βαρος καθε HLp
   φετινες εβδομαδες (HLp 3/5/8/13/20/40) — PREV 0.4-1.2 (≥1 = πιστευουμε το περσινο πιο πολυ απο ενα φετινο ματς)
Α4 εδρα: ξαναμετριεται καθε εβδομαδα (σημερα) ή σταθερη (μονο ο σταθερος ορος του τελικου μετασχηματισμου)
Κριτηριο: RMSE καλυτερη απο τη βαση v2 σε ≥4/5 σεζον 2021-25 — και ξεχωριστα στις εβδομαδες 1-6 (εκει κριθεται η αφετηρια).
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


def make(g, off, q, tg, p, extra):
    cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
    if p['sos'] is not None:
        cfg['sos'] = p['sos']
    cfg.update(extra)
    feats = E.build(g, off, cfg, p['win'])
    qbf = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=cfg['PREV'], target=tg)
    return G.frame(g, feats, qbf)


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base2_params.json'))
    for kind, y, lab in (('m', 'result', 'ΧΑΝΤΙΚΑΠ'), ('t', 'total', 'ΣΥΝΟΛΑ')):
        p = P[kind]
        Fs = [G.FM0 + [f'wt_d_{K}'] for K in T8.KS] if kind == 'm' else [G.FT0]
        V = {'βαση v2': {}}
        V['Α1 χωρις playoffs'] = {'post': False}
        V['Α2 1 σεζον πισω'] = {'nseas': 1}
        V['Α2 3 σεζον πισω'] = {'nseas': 3}
        for hp in (3, 5, 8, 13, 20, 40):
            for pv in (0.4, 0.6, 0.8, 1.0, 1.2):
                V[f'Α3 περσι {pv} · σβησιμο {hp}εβδ'] = {'HLp': hp, 'PREV': pv}
        V['Α4 σταθερη εδρα'] = {'home': False}
        res = {}
        print(f'\n=== {lab} (βαση v2: {p}) ===', flush=True)
        for name, ex in V.items():
            f = make(g, off, q, tg, p, ex)
            pr = T8.loso(f, y, Fs)
            e2 = (f[y] - pr) ** 2
            r = np.sqrt(e2.groupby(f.season).mean())
            r6 = np.sqrt(e2[f.wk <= 6].groupby(f.season[f.wk <= 6]).mean())
            res[name] = (r, r6)
        rb, rb6 = res['βαση v2']
        rows = []
        for name, (r, r6) in res.items():
            rows.append(dict(name=name, all=np.sqrt(np.mean(r[S10] ** 2)), w6=np.sqrt(np.mean(r6[S10] ** 2)),
                             b5=sum(r[s] < rb[s] - 1e-9 for s in S5), b10=sum(r[s] < rb[s] - 1e-9 for s in S10),
                             b5w=sum(r6[s] < rb6[s] - 1e-9 for s in S5), b10w=sum(r6[s] < rb6[s] - 1e-9 for s in S10),
                             y26=r.get(2026, np.nan)))
        d = pd.DataFrame(rows)
        d.to_csv(f'nfl_data/test13_{kind}.csv', index=False)
        show = d[~d.name.str.startswith('Α3')]
        a3 = d[d.name.str.startswith('Α3')].sort_values('all').head(6)
        print(f"  {'παραλλαγη':32} RMSE ολη  καλυτ.21-25 16-25 | εβδ1-6 RMSE καλυτ.21-25 16-25 | 2026")
        for _, r in pd.concat([show, a3]).iterrows():
            print(f"  {r['name']:32} {r['all']:.3f}   {r.b5}/5  {r.b10:2}/10 | {r.w6:.3f}      {r.b5w}/5  {r.b10w:2}/10 | {r.y26:.3f}")
        piv = d[d.name.str.startswith('Α3')].copy()
        piv['pv'] = piv.name.str.extract(r'περσι ([\d.]+)').astype(float)
        piv['hp'] = piv.name.str.extract(r'σβησιμο (\d+)').astype(int)
        print('  Α3 πινακας RMSE ολης σεζον (γραμμες: βαρος περσι στην 1η εβδ · στηλες: μισο βαρος καθε Χ φετινες εβδ):')
        print(piv.pivot(index='pv', columns='hp', values='all').round(3).to_string())
        print('  Α3 πινακας RMSE εβδ 1-6:')
        print(piv.pivot(index='pv', columns='hp', values='w6').round(3).to_string())


if __name__ == '__main__':
    main()
