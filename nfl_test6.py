"""NFL τεστ 6: η βαση μας απεναντι στη γραμμη ΚΑΘΕ ωρας (SBR, διαμεσος βιβλιων), 2019-2025 LOSO (+2026).

Βαση: χαντικαπ = τεστ 5 (ομαδες + QB + success rate + ειδικες + win totals), συνολα = τεστ 4 (ομαδες + QB + SR).
Οι προβλεψεις ειναι LOSO (συντελεστες απο τις αλλες σεζον) και ΔΕΝ εξαρτωνται απο την ωρα — αλλαζει μονο η γραμμη.
Για καθε ωρα H: ακριβεια γραμμης vs μοντελου (RMSE), b = κλιση (πραγμ − γραμμη_H) ~ (μοντελο − γραμμη_H),
ROI picks |μοντελο − γραμμη_H| ≥ X με τις διαμεσες αποδοσεις εκεινης της ωρας (push = 0),
CLV = ποσους ποντους κινηθηκε η γραμμη ΥΠΕΡ μας απο το H ως το κλεισιμο.
Κριτηριο: ROI θετικο σε ≥4/5 σεζον 2021-25.
"""
import numpy as np
import pandas as pd
import nfl_test as T

HS = ['wk', '120', '72', '48', '24', '12', '8', '3', 'close']
LAB = {'wk': 'ανοιγμα εβδ.', '120': '5 μερες', '72': '3 μερες', '48': '48ω', '24': '24ω', '12': '12ω', '8': '8ω',
       '3': '3ω', 'close': 'κλεισιμο'}
S5 = list(range(2021, 2026))


def main():
    pm = pd.read_csv('nfl_data/test5_preds.csv')[['game_id', 'season', 'wk', 'result', 'total', 'mp']]
    pt = pd.read_csv('nfl_data/test4_preds.csv')[['game_id', 'tp']]
    p = pm.merge(pt, on='game_id')
    p = p[p.season >= 2019]
    o = pd.read_csv('nfl_data/sbr_slots.csv')
    o = o[o.book == 'cons']
    close = o[o.H == 'close'][['game_id', 'spread', 'total']].rename(columns={'spread': 'sp_c', 'total': 'tot_c'})
    for kind, lab, line, oP, oN, y, mu, thr in (
            ('m', 'ΧΑΝΤΙΚΑΠ', 'spread', 'h_dec', 'a_dec', 'result', 'mp', [2.5]),
            ('t', 'ΣΥΝΟΛΑ', 'total', 'o_dec', 'u_dec', 'total', 'tp', [3])):
        print(f'\n=== {lab} (edge ≥{thr[0]} ποντοι) ===')
        print(f"{'ωρα':13} {'ματς':>5} | RMSE γραμμη/μοντ |   b   | picks  ROI 19-25 | 21-25 ROI θετ | CLV π. | 2026 picks μον | ανα σεζον")
        for H in HS:
            x = p.merge(o[o.H == H][['game_id', line, oP, oN]].rename(columns=lambda c: 'L' if c == line else c),
                        on='game_id').merge(close, on='game_id').dropna(subset=['L'])
            yv, m, L = x[y].values, x[mu].values, x.L.values
            hist = x.season <= 2025
            rL, rM = np.sqrt(np.mean((yv[hist] - L[hist]) ** 2)), np.sqrt(np.mean((yv[hist] - m[hist]) ** 2))
            b = np.polyfit(m[hist] - L[hist], yv[hist] - L[hist], 1)[0]
            edge = m - L
            pick = np.abs(edge) >= thr[0]
            side = np.sign(edge)
            r = (yv - L) * side
            od = np.where(side > 0, x[oP].values, x[oN].values)
            od = np.where(np.isnan(od), 1.909, od)
            pnl = np.where(r > 0, od - 1, np.where(r < 0, -1, 0))
            cl = ((x.sp_c if kind == 'm' else x.tot_c).values - L) * side
            per = {S: (pick[(x.season == S).values].sum(), pnl[pick & (x.season == S).values].sum()) for S in range(2019, 2027)}
            n7, p7 = sum(per[S][0] for S in range(2019, 2026)), sum(per[S][1] for S in range(2019, 2026))
            n5, p5 = sum(per[S][0] for S in S5), sum(per[S][1] for S in S5)
            pos = sum(per[S][1] > 0 for S in S5)
            clv = np.nanmean(cl[pick & hist.values])
            print(f"{LAB[H]:13} {hist.sum():5} | {rL:6.2f} / {rM:6.2f} | {b:+.2f} | {n7:4} {100 * p7 / max(n7, 1):+6.1f}% |"
                  f" {100 * p5 / max(n5, 1):+6.1f}% {pos}/5 | {clv:+.2f} | {per[2026][0]:4} {per[2026][1]:+6.1f} | "
                  + ' '.join(f"{S % 100}:{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in range(2019, 2026)))


if __name__ == '__main__':
    main()
