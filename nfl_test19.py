"""NFL τεστ 19 — ΑΞΙΟΛΟΓΗΣΗ ΝΕΑΣ ΜΗΧΑΝΗΣ απεναντι στη γραμμη καθε ωρας (SBR, διαμεσος βιβλιων), edge %, 2019-25 (+2026).

Χαντικαπ: βαση v3 (QB ανοιγματος). Συνολα: v4 στο ανοιγμα/5 μερες (χωρις καιρο)· v5 κοντα στο ματς με προγνωση
(d3→72ω, d1→24ω, d0→3ω/κλεισιμο) — ΠΡΟΣΟΧΗ: προγνωση υπαρχει μονο 2024+, για 2019-23 μπαινει ο πραγματικος καιρος
(αισιοδοξο), γι' αυτο δειχνουμε και ξεχωριστα 2024-26.
Κριτηριο: ROI θετικο σε ≥4/5 σεζον 2021-25. Κατωφλια 6/8/10/12%.
Φιλτρα (χαντικαπ, γνωστα την ωρα του pick):
  Φ1 αλλαξε ο QB της δικης μας πλευρας (απο 3 μερες και μετα) · Φ2 «αργο» pick: δεν ηταν pick στο ανοιγμα
  Φ3 η δικη μας ομαδα εχει ≥2 αποντες βασικους (24ω/3ω: Παρασκευη · κλεισιμο: inactive 90′)
"""
import sys
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_engine as E
import nfl_test12 as T12

S7, S5 = list(range(2019, 2026)), list(range(2021, 2026))
THR = [0.06, 0.08, 0.10, 0.12]
LAB = {'wk': 'ανοιγμα εβδ.', '120': '5 μερες', '72': '3 μερες', '48': '48ω', '24': '24ω', '12': '12ω', '3': '3ω', 'close': 'κλεισιμο'}
sys.stdout.reconfigure(encoding='utf-8')


def line(lab, z, m):
    per = {S: (int((m & (z.season == S)).sum()), z.pnl[m & (z.season == S)].sum()) for S in range(2019, 2027)}
    n, p = sum(per[S][0] for S in S7), sum(per[S][1] for S in S7)
    pos = sum(per[S][1] > 0 for S in S5)
    return (f"  {lab:32} picks {n:4} ROI {100 * p / max(n, 1):+6.1f}% · {p:+6.1f}μ · 21-25 θετ {pos}/5 · 2026 {per[2026][0]:3}/{per[2026][1]:+5.1f}μ | "
            + ' '.join(f"{S % 100}:{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in S7))


def main():
    g, off = M.load()
    p = pd.read_csv('nfl_data/base5_preds.csv')
    a = pd.read_csv('nfl_data/test10_preds.csv')[['game_id', 'Fh_n', 'Fa_n', 'Gh_n', 'Ga_n']]
    p = p.merge(a, on='game_id', how='left')
    tg = E.qb_open_targets(g)
    gq = g.set_index('game_id')
    p['chg_h'] = [tg.get((i, t)) != gq.home_qb_id.get(i) for i, t in zip(p.game_id, p.home_team)]
    p['chg_a'] = [tg.get((i, t)) != gq.away_qb_id.get(i) for i, t in zip(p.game_id, p.away_team)]
    for k, d in (('n72', 'tp_d3'), ('n24', 'tp_d1'), ('n3', 'tp_d0')):
        p[k] = p[d].fillna(p.tp_wx)
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    cl = o[o.H == 'close'][['game_id', 'spread', 'total']].rename(columns={'spread': 'sp_c', 'total': 'to_c'})

    print('=== ΧΑΝΤΙΚΑΠ, βαση v3 ===')
    zo = T12.evs(p, 'm', 'mp', 'wk', o)
    for H in ('wk', '120', '72', '48', '24', '12', '3', 'close'):
        z = T12.evs(p, 'm', 'mp', H, o).merge(cl, on='game_id', how='left')
        h = z.season.between(2019, 2025)
        b = np.polyfit((z.mp - z.L)[h], (z.result - z.L)[h], 1)[0]
        clv = ((z.sp_c - z.L) * z.side)
        rl = np.sqrt(np.mean((z.result - z.L)[h] ** 2)); rm = np.sqrt(np.mean((z.result - z.mp)[h] ** 2))
        print(f'\n {LAB[H]}: RMSE γραμμη {rl:.2f} / μοντελο {rm:.2f} · b {b:+.2f} · CLV picks ≥8% {clv[h & (z.ev >= 0.08)].mean():+.2f} π.')
        for t in THR:
            print(line(f'edge ≥{int(t * 100)}%', z, z.ev >= t))
    print('\n=== ΣΥΝΟΛΑ (v4 ανοιγμα, v5 με καιρο κοντα στο ματς) ===')
    for H, col, lb in (('wk', 'tp', 'ανοιγμα, χωρις καιρο'), ('120', 'tp', '5 μερες, χωρις καιρο'), ('72', 'n72', '3 μερες, προγν. 3μ'),
                       ('24', 'n24', '24ω, προγν. 1μ'), ('3', 'n3', '3ω, προγν. ιδια μερα'), ('close', 'n3', 'κλεισιμο, προγν. ιδια μερα')):
        z = T12.evs(p, 't', col, H, o).merge(cl, on='game_id', how='left')
        h = z.season.between(2019, 2025)
        b = np.polyfit((z[col] - z.L)[h], (z.total - z.L)[h], 1)[0]
        rl = np.sqrt(np.mean((z.total - z.L)[h] ** 2)); rm = np.sqrt(np.mean((z.total - z[col])[h] ** 2))
        print(f'\n {lb}: RMSE γραμμη {rl:.2f} / μοντελο {rm:.2f} · b {b:+.2f}')
        for t in THR:
            m = z.ev >= t
            print(line(f'edge ≥{int(t * 100)}%', z, m))
            if H != 'wk' and H != '120':
                k = m & z.season.between(2024, 2026)
                print(f"    μονο 2024-26 (τιμια προγνωση): picks {int(k.sum())} ROI {100 * z.pnl[k].sum() / max(k.sum(), 1):+.1f}%")
        ov = (z.side > 0) & (z.ev >= 0.08); un = (z.side < 0) & (z.ev >= 0.08)
        print(line('  OVER ≥8%', z, ov)); print(line('  UNDER ≥8%', z, un))

    print('\n=== ΦΙΛΤΡΑ ΧΑΝΤΙΚΑΠ (edge ≥8%) ===')
    pko = zo[zo.ev >= 0.08][['game_id', 'side']].rename(columns={'side': 's0'})
    for H in ('72', '24', '3', 'close'):
        z = T12.evs(p, 'm', 'mp', H, o).merge(pko, on='game_id', how='left')
        m = z.ev >= 0.08
        ours_qb = np.where(z.side > 0, z.chg_h, z.chg_a).astype(bool)
        late = ~(z.s0 == z.side)
        cols = ('Gh_n', 'Ga_n') if H == 'close' else ('Fh_n', 'Fa_n')
        ours_ab = np.where(z.side > 0, z[cols[0]].fillna(0), z[cols[1]].fillna(0)) >= 2
        print(f'\n {LAB[H]}:')
        print(line('χωρις φιλτρο', z, m))
        for lab, cut in (('Φ1 QB δικης μας πλευρας', ours_qb), ('Φ2 αργο pick', late.values), ('Φ3 ≥2 αποντες δικης μας', ours_ab)):
            c = m & cut
            print(line(f'{lab}: ΚΟΒΟΝΤΑΙ', z, c))
            print(line(f'{lab}: ΜΕΝΟΥΝ', z, m & ~cut))
        print(line('ΟΛΑ ΤΑ ΦΙΛΤΡΑ: μενουν', z, m & ~ours_qb & ~late.values & ~ours_ab))


if __name__ == '__main__':
    main()
