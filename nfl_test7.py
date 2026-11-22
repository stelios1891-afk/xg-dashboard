"""NFL τεστ 7: νεα βαση (πλεγμα 2, QB ανοιγματος = χωρις διαρροη) + «δυναμεις αγορας» ως αγκυρα, απεναντι σε καθε ωρα.

(α) Αγκυρα: χαντ = a + b·μοντελο + c·mk_d (mk_d = γραμμη απο τις δυναμεις της αγορας ως την προηγ. εβδομαδα),
    συνολα ομοια με mk_t. Συντελεστες LOSO (αλλες σεζον). Κριτηριο ακριβειας: RMSE καλυτερη απο νεα βαση ≥4/5 2021-25.
(β) Για βαση και βαση+αγκυρα: απεναντι στη γραμμη SBR (διαμεσος βιβλιων) σε καθε ωρα — b, ROI, CLV, ανα σεζον.
    Κριτηριο κερδους: ROI θετικο σε ≥4/5 σεζον 2021-25.
"""
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_market as K
import nfl_test as T

HS = ['wk', '120', '72', '48', '24', '12', '3', 'close']
LAB = {'wk': 'ανοιγμα εβδ.', '120': '5 μερες', '72': '3 μερες', '48': '48ω', '24': '24ω', '12': '12ω', '8': '8ω',
       '3': '3ω', 'close': 'κλεισιμο'}
S5, S7 = list(range(2021, 2026)), list(range(2019, 2026))


def loso_blend(p, y, F):
    out = pd.Series(np.nan, index=p.index)
    for S in sorted(p.season.unique()):
        tr = p[(p.season != S) & (p.season <= 2025)].dropna(subset=F + [y])
        c = T.ols(tr, F, y)
        te = p.season == S
        out[te] = T.pred(p[te].fillna(0), F, c)
    return out


def slots(p, mcol, tcol, title):
    o = pd.read_csv('nfl_data/sbr_slots.csv')
    o = o[o.book == 'cons']
    close = o[o.H == 'close'][['game_id', 'spread', 'total']].rename(columns={'spread': 'sp_c', 'total': 'tot_c'})
    for kind, lab, line, oP, oN, y, mu, thr in (('m', 'ΧΑΝΤΙΚΑΠ', 'spread', 'h_dec', 'a_dec', 'result', mcol, 2.5),
                                                ('t', 'ΣΥΝΟΛΑ', 'total', 'o_dec', 'u_dec', 'total', tcol, 3)):
        print(f'\n--- {title} · {lab} (edge ≥{thr}) ---')
        print(f"{'ωρα':13} | RMSE γραμ/μοντ |   b   | picks ROI 19-25 | 21-25 ROI θετ | CLV  | 2026 picks μον | ανα σεζον")
        for H in HS:
            x = p.merge(o[o.H == H][['game_id', line, oP, oN]].rename(columns={line: 'L'}), on='game_id') \
                 .merge(close, on='game_id').dropna(subset=['L', mu])
            yv, m, L = x[y].values, x[mu].values, x.L.values
            h = (x.season <= 2025).values
            rL, rM = np.sqrt(np.mean((yv[h] - L[h]) ** 2)), np.sqrt(np.mean((yv[h] - m[h]) ** 2))
            b = np.polyfit(m[h] - L[h], yv[h] - L[h], 1)[0]
            side = np.sign(m - L)
            pick = np.abs(m - L) >= thr
            r = (yv - L) * side
            od = np.where(side > 0, x[oP].values, x[oN].values)
            od = np.where(np.isnan(od), 1.909, od)
            pnl = np.where(r > 0, od - 1, np.where(r < 0, -1, 0))
            cl = ((x.sp_c if kind == 'm' else x.tot_c).values - L) * side
            per = {S: (pick[(x.season == S).values].sum(), pnl[pick & (x.season == S).values].sum()) for S in range(2019, 2027)}
            n7, p7 = sum(per[S][0] for S in S7), sum(per[S][1] for S in S7)
            n5, p5 = sum(per[S][0] for S in S5), sum(per[S][1] for S in S5)
            pos = sum(per[S][1] > 0 for S in S5)
            print(f"{LAB[H]:13} | {rL:6.2f}/{rM:6.2f} | {b:+.2f} | {n7:4} {100 * p7 / max(n7, 1):+5.1f}% | {100 * p5 / max(n5, 1):+5.1f}% {pos}/5 |"
                  f" {np.nanmean(cl[pick & h]):+.2f} | {per[2026][0]:3} {per[2026][1]:+5.1f} | "
                  + ' '.join(f"{S % 100}:{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in S7))


def main():
    g, off = M.load()
    p = pd.read_csv('nfl_data/base2_preds.csv')
    best = None
    for hl in (4, 8, 16):
        mk = K.market_feats(g, HLm=hl)
        x = p.merge(mk, on='game_id', how='left')
        x['mp_a'] = loso_blend(x, 'result', ['mp', 'mk_d'])
        x['tp_a'] = loso_blend(x, 'total', ['tp', 'mk_t'])
        hist = x[x.season <= 2025]
        sc = np.mean((hist.result - hist.mp_a) ** 2)
        if best is None or sc < best[0]:
            best = (sc, hl, x)
    _, hl, x = best
    print(f'=== (α) ΑΓΚΥΡΑ ΑΓΟΡΑΣ (HLm={hl}) ===')
    for y, a, b_, lab in (('result', 'mp', 'mp_a', 'ΧΑΝΤΙΚΑΠ'), ('total', 'tp', 'tp_a', 'ΣΥΝΟΛΑ')):
        r = {S: (np.sqrt(np.mean((d[y] - d[a]) ** 2)), np.sqrt(np.mean((d[y] - d[b_]) ** 2))) for S, d in x.groupby('season')}
        print(f'{lab}: ' + ' · '.join(f"{S % 100}: {v[0]:.2f}→{v[1]:.2f}{'✓' if v[1] < v[0] else '✗'}" for S, v in r.items()))
        print(f'   καλυτερη 2021-25 {sum(r[S][1] < r[S][0] for S in S5)}/5 · 2016-25 {sum(r[S][1] < r[S][0] for S in range(2016, 2026))}/10')
        c = T.ols(x[x.season <= 2025].dropna(subset=[a, 'mk_d' if y == 'result' else 'mk_t']), [a, 'mk_d' if y == 'result' else 'mk_t'], y)
        print(f'   βαρη (σταθ, μοντελο, αγορα): {np.round(c, 2)}')
    x.to_csv('nfl_data/test7_preds.csv', index=False)
    print('\n=== (β) ΑΠΕΝΑΝΤΙ ΣΕ ΚΑΘΕ ΩΡΑ ===')
    slots(x, 'mp', 'tp', 'ΝΕΑ ΒΑΣΗ (QB ανοιγματος)')
    slots(x, 'mp_a', 'tp_a', 'ΝΕΑ ΒΑΣΗ + ΑΓΚΥΡΑ ΑΓΟΡΑΣ')


if __name__ == '__main__':
    main()
