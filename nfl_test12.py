"""NFL τεστ 12: edge σε ΠΟΣΟΣΤΟ αντι για ποντους, βαση v2 (± αγκυρα αγορας), 2019-25 (+2026).

Πιθανοτητα καλυψης = ομαλη κατανομη γυρω απο το μοντελο × βαρος καθε ακεραιου αποτελεσματος (κλειδια 3/7/10, push)
(nfl_test4.key_weights/probs_key)· σ και βαρη κλειδιων απο τις ΑΛΛΕΣ σεζον (LOSO).
edge = EV με την πραγματικη διαμεση αποδοση της ωρας (SBR) = P(νικη)·(αποδοση−1) − P(ηττα)  (push = 0).
Κατωφλια 2/4/6/8/10/12% + εμφωλευμενη επιλογη (για καθε σεζον το κατωφλι με το καλυτερο ROI στις αλλες σεζον 2019-25).
Συγκριση με τον κανονα ποντων (≥2.5 χαντ / ≥3 συνολα). Κριτηριο: ROI θετικο ≥4/5 σεζον 2021-25.
"""
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_test4 as T4
import nfl_test7 as T7
import nfl_market as K

THR = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
S7, S5 = list(range(2019, 2026)), list(range(2021, 2026))


def evs(x, kind, col, H, o):
    line, oP, oN, y = (('spread', 'h_dec', 'a_dec', 'result') if kind == 'm' else ('total', 'o_dec', 'u_dec', 'total'))
    s = o[o.H == H][['game_id', line, oP, oN]].rename(columns={line: 'L', oP: 'op', oN: 'on'})
    z = x.merge(s, on='game_id').dropna(subset=['L', col]).copy()
    lo, hi = (-70, 70) if kind == 'm' else (0, 120)
    z['ev'] = np.nan; z['side'] = 0.0; z['pnl'] = np.nan; z['pts'] = (z[col] - z.L).abs()
    for S in sorted(z.season.unique()):
        tr = x[(x.season != S) & x.season.between(2016, 2025)].dropna(subset=[col, y])
        sd = np.sqrt(np.mean((tr[y] - tr[col]) ** 2))
        ks, w = T4.key_weights(tr[y].values, tr[col].values, sd, lo, hi)
        te = z.season == S
        P = np.array([T4.probs_key(m, l, sd, ks, w) for m, l in zip(z.loc[te, col], z.loc[te, 'L'])])
        pw, pp = P[:, 0], P[:, 1]; pl = 1 - pw - pp
        op = z.loc[te, 'op'].fillna(1.909).values; on = z.loc[te, 'on'].fillna(1.909).values
        ev_p, ev_n = pw * (op - 1) - pl, pl * (on - 1) - pw
        side = np.where(ev_p >= ev_n, 1, -1)
        z.loc[te, 'ev'] = np.maximum(ev_p, ev_n)
        z.loc[te, 'side'] = side
        r = (z.loc[te, y].values - z.loc[te, 'L'].values) * side
        od = np.where(side > 0, op, on)
        z.loc[te, 'pnl'] = np.where(np.isnan(z.loc[te, y].values), np.nan, np.where(r > 0, od - 1, np.where(r < 0, -1, 0)))
    return z


def table(z, lab, pts_thr):
    rows = []
    rules = [('ποντοι ≥%g' % pts_thr, z.pts >= pts_thr)] + [(f'edge ≥{int(t * 100)}%', z.ev >= t) for t in THR]
    out = {}
    for name, m in rules:
        per = {S: (int((m & (z.season == S)).sum()), z.pnl[m & (z.season == S)].sum()) for S in range(2019, 2027)}
        out[name] = per
        n7, p7 = sum(per[S][0] for S in S7), sum(per[S][1] for S in S7)
        pos = sum(per[S][1] > 0 for S in S5)
        print(f"  {lab} {name:11} picks {n7:4} ROI {100 * p7 / max(n7, 1):+6.1f}% · 21-25 θετ {pos}/5 · 2026 {per[2026][0]:3}/{per[2026][1]:+5.1f}μ | "
              + ' '.join(f"{S % 100}:{per[S][0]}/{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in S7))
    # εμφωλευμενη επιλογη κατωφλιου
    tot = {'n': 0, 'p': 0.0}; pos = 0; ch = {}
    for S in range(2019, 2027):
        best = max(THR, key=lambda t: sum(out[f'edge ≥{int(t * 100)}%'][s][1] for s in S7 if s != S) /
                   max(sum(out[f'edge ≥{int(t * 100)}%'][s][0] for s in S7 if s != S), 1))
        ch[S] = int(best * 100)
        n, p = out[f'edge ≥{int(best * 100)}%'][S]
        if S <= 2025:
            tot['n'] += n; tot['p'] += p
            pos += (p > 0) if S in S5 else 0
    print(f"  {lab} ΕΜΦΩΛ. κατωφλι (επιλογες {ch}): picks {tot['n']} ROI {100 * tot['p'] / max(tot['n'], 1):+.1f}% · 21-25 θετ {pos}/5")


def main():
    g, off = M.load()
    p = pd.read_csv('nfl_data/test8_preds.csv')
    p['mp'] = p['mp_βαση v2']
    p['mp_a'] = T7.loso_blend(p, 'result', ['mp', 'mk_d'])
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    for H, hl in (('wk', 'ΑΝΟΙΓΜΑ ΕΒΔ.'), ('72', '3 ΜΕΡΕΣ'), ('24', '24ω'), ('close', 'ΚΛΕΙΣΙΜΟ')):
        print(f'\n=== {hl} ===')
        for col, lab in (('mp', 'χαντ βαση  '), ('mp_a', 'χαντ +αγκυρα')):
            table(evs(p, 'm', col, H, o), lab, 2.5)
        table(evs(p, 't', 'tp', H, o), 'συνολα     ', 3)


if __name__ == '__main__':
    main()
