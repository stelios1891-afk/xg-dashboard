"""NFL τεστ 17 — ΚΑΙΡΟΣ ΜΕΣΑ ΣΤΗ ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ, πανω στη βαση v4 (γηπεδα). Μονο για picks κοντα στο ματς.

Καιρος ματς (μονο ανοιχτα γηπεδα, κλειστα = 0): ανεμος mph (0-30), κρυο = max(0, 50 − °F), βροχη (ναι/οχι).
(α) Ακριβεια με τον ΠΡΑΓΜΑΤΙΚΟ καιρο (≈ η προγνωση λιγες ωρες πριν), LOSO 2016-25:
    W1 καιρος στον τελικο μετασχηματισμο · W2 W1 + «καθαρες» δυναμεις (η μηχανη μετραει κλειστο & καιρο χωριστα,
    π.χ. η επιθεση του Buffalo δεν «τιμωρειται» για τα ματς με χιονι) · Κριτηριο ≥4/5 σεζον 2021-25.
(β) Με την ΠΡΟΓΝΩΣΗ που υπηρχε (Open-Meteo, 2024-26): 3 μερες πριν → γραμμη 72ω, 1 μερα → 24ω, ιδια μερα → 3ω/κλεισιμο.
    Συντελεστες καιρου απο τις ΑΛΛΕΣ σεζον (πραγματικος καιρος). RMSE + picks με edge % (8% / 10%) ανα σεζον.
"""
import json, sys
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test as T
import nfl_test8 as T8
import nfl_test12 as T12
import nfl_test16 as T16

S5, S10 = G.S5, G.S10
WX = ['wx_wind', 'wx_cold', 'wx_rain']
sys.stdout.reconfigure(encoding='utf-8')


def add_wx(f, g):
    gg = g.set_index('game_id')
    roof = f.game_id.map(gg.roof)
    outd = ~roof.isin(['dome', 'closed'])
    wind, temp = f.game_id.map(gg.wind), f.game_id.map(gg.temp)
    f['wx_wind'] = np.where(outd, wind.clip(0, 30).fillna(wind.median()), 0)
    f['wx_cold'] = np.where(outd, (50 - temp).clip(0, None).fillna(0), 0)
    f['wx_rain'] = np.where(outd, f.game_id.map(M.RAIN).fillna(0), 0)
    f['outd'] = outd.astype(int)
    return f


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    p = json.load(open('nfl_data/base4_params.json'))['t']

    def frame(venue):
        cfg = {k: p[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d')}
        if p['sos'] is not None:
            cfg['sos'] = p['sos']
        if venue:
            cfg['venue'] = venue
        feats = E.build(g, off, cfg, p['win'])
        qbf = Q.qb_features(g, q, HLQ=p['HLQ'], N0=p['N0'], M0=p['M0'], HL=p['HL'], PREV=p['PREV'], target=tg)
        return add_wx(T16.venue_feats(G.frame(g, feats, qbf), g), g)

    F4 = G.FT0 + p['FT_extra']
    f0 = frame(None)
    f2 = frame(['dome'] + WX)
    V = {'βαση v4': (f0, F4), 'W1 + καιρος': (f0, F4 + WX), 'W2 W1 + καθαρες δυναμεις': (f2, F4 + WX)}
    print('=== (α) ΑΚΡΙΒΕΙΑ με πραγματικο καιρο (LOSO) ===')
    rb, P = None, {}
    for name, (f, Fl) in V.items():
        pr = T8.loso(f, 'total', [Fl])
        r = np.sqrt(((f.total - pr) ** 2).groupby(f.season).mean())
        ro = np.sqrt(((f.total - pr) ** 2)[f.outd == 1].groupby(f.season[f.outd == 1]).mean())
        if rb is None:
            rb, rbo = r, ro
        P[name] = pr
        print(f"  {name:28} RMSE {np.sqrt(np.mean(r[S10] ** 2)):.3f} · καλυτερη 2021-25 {sum(r[s] < rb[s] - 1e-9 for s in S5)}/5 · 2016-25 {sum(r[s] < rb[s] - 1e-9 for s in S10)}/10"
              f" · μονο ανοιχτα {np.sqrt(np.mean(ro[S10] ** 2)):.3f} · 2026 {r.get(2026, np.nan):.3f}")
    c = T.ols(f0[f0.season <= 2025], F4 + WX, 'total')
    print('  ποντοι: ανεμος/mph %.2f · κρυο/°F %.2f · βροχη %.2f' % tuple(c[-3:]))

    print('\n=== (β) ΠΡΟΓΝΩΣΗ 2024-26 ===')
    wf = pd.read_csv('nfl_data/weather_fc.csv').drop(columns=['roof'])
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    for name, f in (('W1', f0), ('W2', f2)):
        x = f.merge(wf, on='game_id', how='left')
        x = x[x.season >= 2024].copy()
        x['tp_v4'] = P['βαση v4'][f.season >= 2024].values if name == 'W1' else np.nan
        cols = {}
        for S in (2024, 2025, 2026):
            tr = f[(f.season != S) & (f.season <= 2025)]
            cw = T.ols(tr, F4 + WX, 'total')
            te = x.season == S
            for lab in ('d3', 'd1', 'd0'):
                X = x.loc[te].copy()
                od = X.outd == 1
                X['wx_wind'] = np.where(od, X[f'wind_{lab}'].clip(0, 30), 0)
                X['wx_cold'] = np.where(od, (50 - X[f'temp_{lab}']).clip(0, None), 0)
                X['wx_rain'] = np.where(od, (X[f'rain_{lab}'] >= 1).astype(int), 0)
                X[WX] = X[WX].fillna(0)
                x.loc[te, f'tp_{lab}'] = T.pred(X, F4 + WX, cw)
        x['tp_act'] = P['W1 + καιρος' if name == 'W1' else 'W2 W1 + καθαρες δυναμεις'][f.season >= 2024].values
        if name == 'W1':
            base_x = x.copy()
        yy = x[x.total.notna()]
        print(f'  {name}: RMSE ' + ' · '.join(f"{lab} {np.sqrt(np.mean((yy.total - yy[c]) ** 2)):.3f}" for lab, c in
                                           (('βαση v4', 'tp_v4') if name == 'W1' else ('', 'tp_act'),
                                            ('προγν. 3 μερες', 'tp_d3'), ('1 μερα', 'tp_d1'), ('ιδια μερα', 'tp_d0'),
                                            ('πραγματικος', 'tp_act')) if c in yy and yy[c].notna().any()))
        allx = pd.concat([f[(f.season < 2024)].assign(**{k: P['βαση v4'][f.season < 2024].values for k in ('tp_v4', 'tp_d3', 'tp_d1', 'tp_d0')}), x])
        for H, col, hl in (('72', 'tp_d3', '72ω προγν. 3μ'), ('24', 'tp_d1', '24ω προγν. 1μ'), ('3', 'tp_d0', '3ω ιδια μερα'), ('close', 'tp_d0', 'κλεισιμο')):
            for cc, lab in (('tp_v4', 'βαση v4'), (col, f'{name} καιρος')):
                if name == 'W2' and cc == 'tp_v4':
                    continue
                z = T12.evs(allx, 't', cc, H, o)
                z = z[z.season >= 2024]
                for t in (0.08, 0.10):
                    m = z.ev >= t
                    per = {S: (int((m & (z.season == S)).sum()), z.pnl[m & (z.season == S)].sum()) for S in (2024, 2025, 2026)}
                    n, pl = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
                    print(f"     {hl:15} {lab:12} edge ≥{int(t * 100)}%: picks {n:3} ROI {100 * pl / max(n, 1):+6.1f}% | "
                          + ' '.join(f'{S}: {v[0]}/{100 * v[1] / max(v[0], 1):+.0f}%' for S, v in per.items()))


if __name__ == '__main__':
    main()
