"""NFL τεστ 23 — ΑΠΟΤΕΛΕΣΜΑΤΑ WALK-FORWARD (nfl_walk.py): καθε σεζον 2021-26 με μηχανη & τιμολογηση μονο απο το παρελθον της.

Χαντικαπ: ομαλη × κλειδια (σ, κλειδια απο σεζον < S). Συνολα ανοιγματος/5 μερων (χωρις καιρο): ασυμμετρη κατανομη + β (απο σεζον < S).
Απεναντι σε Pinnacle (2021-25) και αμερικανικα (2021-26). Κριτηριο: ROI θετικο ≥4/5 σεζον 2021-25.
Διπλα το LOSO (βαρη απο ολες τις σεζον) στα ΙΔΙΑ χρονια, για να φανει ποσο ειχε φουσκωσει.
"""
import sys
import numpy as np
import pandas as pd
import nfl_test4 as T4
import nfl_test20 as T20

S5 = list(range(2021, 2026))
sys.stdout.reconfigure(encoding='utf-8')
Y = {'m': 'result', 't': 'total'}
COL = {'m': ('spread', 'h_dec', 'a_dec'), 't': ('total', 'o_dec', 'u_dec')}


def price_wf(preds, prior, kind, slot, sbr, H, seasons):
    y = Y[kind]
    line, oP, oN = COL[kind]
    s = slot[slot.H == H][['game_id', line, oP, oN]].rename(columns={line: 'L', oP: 'op', oN: 'on'})
    sb = sbr[sbr.H == H][['game_id', line]].rename(columns={line: 'Lb'})
    out = []
    grid = np.arange(-60, 61)
    lo, hi = (-70, 70) if kind == 'm' else (0, 120)
    for S in seasons:
        te = preds[(preds.kind == kind) & (preds.season == S)].merge(s, on='game_id').dropna(subset=['L', 'pred', y]).copy()
        pr = prior[(prior.kind == kind) & (prior.S == S)].dropna(subset=['pred', y])
        if te.empty:
            continue
        res = (pr[y] - pr.pred).values
        sd = np.sqrt(np.mean(res ** 2))
        ks = np.arange(lo, hi + 1)
        mu = te.pred.values
        if kind == 'm':
            ks, w = T4.key_weights(pr[y].values, pr.pred.values, sd, lo, hi)
            dens = None
        else:
            dens = T20.smooth_density(res, grid)
            exp = np.zeros(len(ks))
            for m in pr.pred.values:
                exp += np.interp(ks - m, grid, dens, left=0, right=0)
            exp /= exp.sum()
            obs = np.bincount(np.clip(pr[y].astype(int).values - lo, 0, hi - lo), minlength=len(ks)) / len(pr)
            w = np.clip(obs / np.clip(exp, 1e-9, None), 0.05, 5)
            b_ = pr.merge(sb, on='game_id').dropna(subset=['Lb'])
            beta = np.polyfit(b_.pred - b_.Lb, b_[y] - b_.Lb, 1)[0]
            mu = te.L.values + beta * (mu - te.L.values)
        P = np.array([T20.probs(m, l, ks, w, dens, grid, sd) for m, l in zip(mu, te.L)])
        te['pw'], te['pp'] = P[:, 0], P[:, 1]
        out.append(te)
    z = pd.concat(out)
    z['pl'] = 1 - z.pw - z.pp
    op, on = z.op.fillna(1.909).values, z.on.fillna(1.909).values
    ev_p, ev_n = z.pw * (op - 1) - z.pl, z.pl * (on - 1) - z.pw
    z['side'] = np.where(ev_p >= ev_n, 1, -1)
    z['ev'] = np.maximum(ev_p, ev_n)
    r = (z[y] - z.L) * z.side
    od = np.where(z.side > 0, op, on)
    z['pnl'] = np.where(r > 0, od - 1, np.where(r < 0, -1, 0))
    return z


def row(lab, d, seasons):
    if len(d) == 0:
        return f'  {lab:26} picks    0'
    per = {S: (int((d.season == S).sum()), d.pnl[d.season == S].sum()) for S in seasons}
    pos = sum(per[S][1] > 0 for S in S5 if S in per)
    win = (d.pnl > 0).sum() / max((d.pnl != 0).sum(), 1)
    return (f"  {lab:26} picks {len(d):4} ROI {100 * d.pnl.mean():+6.1f}% καλ. {100 * win:4.1f}% {d.pnl.sum():+6.1f}μ θετ 21-25 {pos}/5 | "
            + ' '.join(f"{S % 100}:{per[S][0]}/{100 * per[S][1] / max(per[S][0], 1):+.0f}" for S in seasons))


def main():
    preds = pd.read_csv('nfl_data/walk_preds.csv')
    prior = pd.read_csv('nfl_data/walk_prior.csv')
    base = pd.read_csv('nfl_data/base5_preds.csv')
    pin = pd.read_csv('nfl_data/pin_slots.csv')
    sbr = pd.read_csv('nfl_data/sbr_slots.csv'); sbr = sbr[sbr.book == 'cons']
    close = pin[pin.H == 'close'][['game_id', 'spread', 'total']].rename(columns={'spread': 'sc', 'total': 'tc'})
    print('=== ΑΚΡΙΒΕΙΑ (λαθος σε ποντους) walk-forward / LOSO / γραμμη κλεισιματος nflverse ===')
    for kind, col, line, lab in (('m', 'mp', 'spread_line', 'ΧΑΝΤΙΚΑΠ'), ('t', 'tp', 'total_line', 'ΣΥΝΟΛΑ')):
        y = Y[kind]
        x = preds[preds.kind == kind].merge(base[['game_id', col, line]], on='game_id').dropna(subset=[y])
        r = lambda d, c: np.sqrt(np.mean((d[y] - d[c]) ** 2))
        print(f' {lab}: ' + ' · '.join(f"{S % 100}: {r(d, 'pred'):.2f}/{r(d, col):.2f}/{r(d, line):.2f}" for S, d in x.groupby('season')))
        h = x[x.season <= 2025]
        print(f"   2021-25: {r(h, 'pred'):.3f} / {r(h, col):.3f} / {r(h, line):.3f}")
    print('\n=== ΧΑΝΤΙΚΑΠ απεναντι στην PINNACLE (2021-25) ===')
    for H, lb in (('wk', 'ανοιγμα'), ('120', '5 μερες'), ('72', '72ω'), ('24', '24ω*'), ('3', '3ω'), ('close', '30′')):
        z = price_wf(preds, prior, 'm', pin, sbr, H, S5)
        loso = T20.run(base, 'm', 'mp', pin, H=H); loso = loso[loso.season.isin(S5)]
        zc = z.merge(close, on='game_id', how='left')
        print(f'\n {lb}')
        for t in (0.06, 0.08, 0.10):
            d = zc[zc.ev >= t]
            l = loso[loso.ev >= t]
            print(row(f'WF edge ≥{int(t * 100)}%', d, S5) + f" | CLV {((d.sc - d.L) * d.side).mean():+.2f} π. || LOSO {len(l)} {100 * l.pnl.mean():+.1f}%")
        d = zc[zc.ev >= 0.06]
        fav = d.side == np.sign(d.L).replace(0, 1)
        print(row('  ΦΑΒΟΡΙ ≥6%', d[fav], S5)); print(row('  ΑΟΥΤΣΑΙΝΤΕΡ ≥6%', d[~fav], S5))
    print('\n=== ΧΑΝΤΙΚΑΠ απεναντι στα ΑΜΕΡΙΚΑΝΙΚΑ (2021-26) ===')
    for H, lb in (('wk', 'ανοιγμα'), ('120', '5 μερες'), ('close', 'κλεισιμο')):
        z = price_wf(preds, prior, 'm', sbr, sbr, H, list(range(2021, 2027)))
        for t in (0.06, 0.10):
            print(row(f'{lb} WF ≥{int(t * 100)}%', z[z.ev >= t], list(range(2021, 2027))))
    print('\n=== ΣΥΝΟΛΑ (χωρις καιρο, τιμολογηση v6 walk-forward) ===')
    for src, name, seas in ((pin, 'PINNACLE', S5), (sbr, 'ΑΜΕΡΙΚΑΝΙΚΑ', list(range(2021, 2027)))):
        for H, lb in (('wk', 'ανοιγμα'), ('120', '5 μερες')):
            z = price_wf(preds, prior, 't', src, sbr, H, seas)
            zc = z.merge(close, on='game_id', how='left')
            print(f'\n {name} {lb}')
            for t in (0.04, 0.06, 0.08, 0.10):
                d = zc[zc.ev >= t]
                print(row(f'WF edge ≥{int(t * 100)}%', d, seas) + (f" | CLV {((d.tc - d.L) * d.side).mean():+.2f} π." if len(d) else ''))
                if t in (0.06, 0.10):
                    print(row('   OVER', d[d.side > 0], seas)); print(row('   UNDER', d[d.side < 0], seas))
            l = T20.run(base, 't', 'tp', src, H=H, use_emp=True, use_beta=True); l = l[l.season.isin(seas) & l.total.notna()]
            print(f"   (LOSO ιδια χρονια: ≥6% {int((l.ev >= .06).sum())} {100 * l.pnl[l.ev >= .06].mean():+.1f}% · ≥10% {int((l.ev >= .10).sum())} {100 * l.pnl[l.ev >= .10].mean():+.1f}%)")


if __name__ == '__main__':
    main()
