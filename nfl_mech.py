"""NFL τεστ 3: μηχανισμοι βασης, ΕΝΑΣ-ΕΝΑΣ πανω στη βαση του τεστ 2 (ομαδες + QB), LOSO 2016-2025 (+2026).

Κριτηριο (οπως NBA): ακριβεια (RMSE) καλυτερη απο τη βαση σε ≥4/5 σεζον 2021-25 + δειχνουμε ROI vs κλεισιμο.
Μηχανισμοι:
  M1a τυχη φαμπλ    : EPA οπου ολες οι φασεις με φαμπλ παιρνουν τον ιδιο μεσο EPA (αντι για cl_epa)
  M1b success rate  : + rating ποσοστου «επιτυχημενων» φασεων
  M1c πασα/τρεξιμο  : EPA πασας και τρεξιματος χωριστα (αντι για ενιαιο)
  M2  εδρα σταθερη  : χωρις εδρα στα ratings, μονο σταθερα του μετασχηματισμου (μετριεται στις αλλες σεζον)
  M3  αποσυμπιεση   : + ορος διαφορα×|διαφορα| (μεγαλα φαβορι μεγαλυτερα)
  M5  προγραμμα     : διαφορα ξεκουρασης, σημαια bye (≥12 μερες), σημαια συντομης εβδομαδας (≤5), δυτικη ομαδα 1μμ ET στα ανατολικα
  M6  εβδομαδα 18   : αλληλεπιδραση εβδ18 × διαφορα (συμπιεση οταν ξεκουραζουν βασικους)
  M7  συνολα καιρος : αερας, θερμοκρασια, κλειστο γηπεδο (μονο στα συνολα)
  M8  επιπεδο σκορ  : μεσος ορος συνολων των τελευταιων 48 ματς λιγκας (μονο στα συνολα)
"""
import json
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_test as T

BASE = dict(HL=16, PREV=0.6, LAM={})
QB = dict(HLQ=40, N0=300, M0=-0.15)
TZ = {**{k: 0 for k in 'ATL BAL BOS BUF CAR CIN CLE DET IND JAX MIA NE NYG NYJ PHI PIT TB WAS'.split()},
      **{k: 1 for k in 'CHI DAL GB HOU KC MIN NO TEN'.split()}, 'DEN': 2, 'ARI': 2,
      **{k: 3 for k in 'LA LAC LV SEA SF'.split()}}


def frame(g, off, q, stats=M.STATS, home=True):
    f = M.build(g, off, stats=stats, home=home, **BASE)
    f = f[(f.game_type == 'REG') & f.spread_line.notna()].copy()
    qf = Q.qb_features(g, q, HL=BASE['HL'], PREV=BASE['PREV'], **QB)
    f = f.merge(qf, on='game_id', how='left')
    f['qb_d'] = f.home_qbadj.fillna(0) - f.away_qbadj.fillna(0)
    f['qb_s'] = f.home_qbadj.fillna(0) + f.away_qbadj.fillna(0)
    # προγραμμα
    hr, ar = f.home_rest.clip(4, 14), f.away_rest.clip(4, 14)
    f['rest_d'] = (hr - ar).clip(-7, 7)
    f['bye_d'] = (f.home_rest >= 12).astype(int) - (f.away_rest >= 12).astype(int)
    f['short_d'] = (f.home_rest <= 5).astype(int) - (f.away_rest <= 5).astype(int)
    early = f.gametime.fillna('13:00').str[:2].astype(int) < 14
    f['west_early'] = (early & (f.away_team.map(TZ) - f.home_team.map(TZ) >= 2) & (f.home_team.map(TZ) == 0)).astype(int) \
        - (early & (f.home_team.map(TZ) - f.away_team.map(TZ) >= 2) & (f.neutral == 1)).astype(int) * 0
    f['wk18_d'] = (f.wk == 18) * f.pts_diff
    # καιρος
    dome = f.roof.isin(['dome', 'closed'])
    f['dome'] = dome.astype(int)
    f['wind'] = np.where(dome, 0, f.wind.fillna(f.wind.median()))
    f['cold'] = np.where(dome, 0, (60 - f.temp.fillna(60)).clip(0, None))
    # επιπεδο σκορ λιγκας (μονο προηγουμενα ματς)
    allg = g[g.result.notna()].sort_values('t')
    lvl = allg.total.rolling(48).mean().shift(1)
    lv = pd.Series(lvl.values, index=allg.game_id)
    # ιδια εβδομαδα δεν βλεπει τα ματς της ιδιας εβδομαδας
    first = allg.groupby('t').game_id.first()
    wk_lvl = lv.loc[first.values].values
    f['lvl'] = f.t.map(dict(zip(first.index, wk_lvl)))
    for s in stats:
        if s not in ('pts', 'plays'):
            pass
    return f


def run(f, FM, FT, seasons=range(2016, 2027)):
    out = []
    for S in seasons:
        tr = f[(f.season != S) & (f.season <= 2025)].dropna(subset=FM + FT)
        te = f[f.season == S].copy()
        cm, ct = T.ols(tr, FM, 'result'), T.ols(tr, FT, 'total')
        te['mp'], te['tp'] = T.pred(te.fillna(0), FM, cm), T.pred(te.fillna(0), FT, ct)
        out.append(te)
    return pd.concat(out)


def score(p):
    r = {}
    for S, d in p.groupby('season'):
        e = T.evaluate(d, d.mp.values, d.tp.values)
        r[S] = e
    return r


def main():
    g, off = M.load()
    q = Q.load_qb()
    FM0 = ['cl_epa_diff', 'pts_diff', 'qb_d']
    FT0 = ['pts_sum', 'cl_epa_sum', 'plays_sum', 'qb_s']
    base = frame(g, off, q)
    V = {'B βαση (τεστ 2)': (base, FM0, FT0)}
    f = frame(g, off, q, stats=('cl_nf_epa', 'pts', 'plays'))
    V['M1a τυχη φαμπλ'] = (f, ['cl_nf_epa_diff', 'pts_diff', 'qb_d'], ['pts_sum', 'cl_nf_epa_sum', 'plays_sum', 'qb_s'])
    f = frame(g, off, q, stats=('cl_epa', 'pts', 'plays', 'cl_sr'))
    V['M1b +success rate'] = (f, FM0 + ['cl_sr_diff'], FT0 + ['cl_sr_sum'])
    f = frame(g, off, q, stats=('cl_p_epa', 'cl_r_epa', 'pts', 'plays'))
    V['M1c πασα/τρεξιμο'] = (f, ['cl_p_epa_diff', 'cl_r_epa_diff', 'pts_diff', 'qb_d'],
                             ['pts_sum', 'cl_p_epa_sum', 'cl_r_epa_sum', 'plays_sum', 'qb_s'])
    f = frame(g, off, q, home=False)
    V['M2 εδρα σταθερη'] = (f, FM0, FT0)
    b = base.copy()
    b['pd2'] = b.pts_diff * b.pts_diff.abs() / 10
    b['ed2'] = b.cl_epa_diff * b.cl_epa_diff.abs()
    V['M3 αποσυμπιεση'] = (b, FM0 + ['pd2', 'ed2'], FT0)
    V['M5 προγραμμα'] = (base, FM0 + ['rest_d', 'bye_d', 'short_d', 'west_early'], FT0)
    V['M6 εβδομαδα 18'] = (base, FM0 + ['wk18_d'], FT0)
    V['M7 καιρος (συνολα)'] = (base, FM0, FT0 + ['wind', 'cold', 'dome'])
    V['M8 επιπεδο σκορ (συνολα)'] = (base, FM0, FT0 + ['lvl'])
    res = {k: score(run(*v)) for k, v in V.items()}
    B = res['B βαση (τεστ 2)']
    S10, S5 = list(range(2016, 2026)), list(range(2021, 2026))
    print('RMSE: «καλυτερες σεζον» = ποσες σεζον η RMSE πεφτει vs βαση (χαντ / συνολα)\n')
    hdr = f"{'μηχανισμος':26} | ΧΑΝΤ RMSE  Δ   21-25 16-25 | ΣΥΝ RMSE  Δ   21-25 16-25 | ROI χαντ≥2.5 (21-25 θετ)  | ROI συν≥3 (21-25 θετ) | 2026 χαντ/συν RMSE"
    print(hdr)
    rows = []
    for k, R in res.items():
        def agg(key, ss):
            return np.sqrt(np.mean([R[s][key] ** 2 for s in ss]))
        def better(key, ss):
            return sum(R[s][key] < B[s][key] - 1e-9 for s in ss)
        def roi(key, t, ss):
            n = sum(R[s][key][t][0] for s in ss); pl = sum(R[s][key][t][1] for s in ss)
            return n, 100 * pl / max(n, 1), sum(R[s][key][t][1] > 0 for s in S5)
        rm, rt = agg('rmse_m', S10), agg('rmse_t', S10)
        dm, dt_ = rm - agg('rmse_m', S10) * 0 - np.sqrt(np.mean([B[s]['rmse_m'] ** 2 for s in S10])), \
            rt - np.sqrt(np.mean([B[s]['rmse_t'] ** 2 for s in S10]))
        nm, rom, pm = roi('roi_m', 2.5, S10)
        nt, rot, pt = roi('roi_t', 3, S10)
        print(f"{k:26} | {rm:8.3f} {dm:+.3f}  {better('rmse_m', S5)}/5  {better('rmse_m', S10):2}/10 |"
              f" {rt:7.3f} {dt_:+.3f}  {better('rmse_t', S5)}/5  {better('rmse_t', S10):2}/10 |"
              f" {nm:4} {rom:+5.1f}% ({pm}/5)     | {nt:4} {rot:+5.1f}% ({pt}/5) |"
              f" {R[2026]['rmse_m']:.2f}/{R[2026]['rmse_t']:.2f}")
        rows.append(dict(mech=k, rmse_m=rm, d_m=dm, b5_m=better('rmse_m', S5), b10_m=better('rmse_m', S10),
                         rmse_t=rt, d_t=dt_, b5_t=better('rmse_t', S5), b10_t=better('rmse_t', S10),
                         roi_m=(nm, rom, pm), roi_t=(nt, rot, pt)))
    mk = np.sqrt(np.mean([B[s]['rmse_m_mkt'] ** 2 for s in S10])), np.sqrt(np.mean([B[s]['rmse_t_mkt'] ** 2 for s in S10]))
    print(f"\nαγορα (κλεισιμο) 2016-25: χαντ {mk[0]:.3f} · συνολα {mk[1]:.3f}")
    json.dump(rows, open('nfl_data/test3_mech.json', 'w', encoding='utf-8'), ensure_ascii=False, default=float, indent=1)


if __name__ == '__main__':
    main()
