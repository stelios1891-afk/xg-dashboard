"""NFL τεστ 11: καιρος στα ΣΥΝΟΛΑ — εκπαιδευση στον ΠΡΑΓΜΑΤΙΚΟ καιρο 2016-23, εφαρμογη με ΠΡΟΓΝΩΣΗ 2024-26.

Βαση: συνολα βασης v2 (LOSO, nfl_test8 → test8_preds.csv 'tp').
Χαρακτηριστικα (μονο ανοιχτα γηπεδα· κλειστα/συρομενη σκεπη = 0, γιατι η σκεπη κλεινει σχεδον παντα):
  dome  = κλειστο γηπεδο ή συρομενη σκεπη (γνωστο απο την αρχη της σεζον)
  wind  = ανεμος mph (0-30) · cold = max(0, 50 − °F) · rain = βροχη (pbp κειμενο / προγνωση ≥1 mm στο 3ωρο)
(α) κλειστο γηπεδο μονο: LOSO 2016-25 στη βαση, αξιολογηση σε ΚΑΘΕ ωρα 2019-25 (γνωστο απο νωρις).
(β) καιρος: συντελεστες απο 2016-23 πραγματικο καιρο → προβλεψη 2024-26 με προγνωση d3 (γραμμη 72ω), d1 (24ω),
    d0 (3ω, κλεισιμο). Συγκριση: RMSE με/χωρις καιρο, b, ROI ≥3 π. ανα σεζον.
    Ελεγχος αγορας: κινειται η γραμμη συνολου (ανοιγμα → κλεισιμο) με την προγνωση ανεμου/βροχης;
"""
import re
import numpy as np
import pandas as pd
import nfl_fetch as F
import nfl_test as T
import nfl_test7 as T7
import nfl_test9 as T9


def rain_flags():
    out = {}
    for y in range(2016, 2027):
        p = pd.read_csv(f'{F.CACHE}/pbp_{y}.csv.gz', usecols=['game_id', 'weather'], low_memory=False)
        w = p.groupby('game_id').weather.first().fillna('').str.lower()
        out.update((w.str.contains('rain|shower|drizzle|thunder') & ~w.str.contains('no rain|0% chance')).astype(int).to_dict())
    return out


def tot_picks(x, H, col, o, thr=3):
    s = o[o.H == H][['game_id', 'total', 'o_dec', 'u_dec']].rename(columns={'total': 'L'})
    z = x.merge(s, on='game_id').dropna(subset=['L', col])
    e = z[col] - z.L
    z['pick'] = e.abs() >= thr
    z['side'] = np.sign(e)
    rr = (z.total - z.L) * z.side
    od = np.where(z.side > 0, z.o_dec, z.u_dec); od = np.where(np.isnan(od), 1.909, od)
    z['pnl'] = np.where(rr > 0, od - 1, np.where(rr < 0, -1, 0))
    z['result'] = z.total
    return z


def main():
    p = pd.read_csv('nfl_data/test8_preds.csv')[['game_id', 'season', 'wk', 'total', 'total_line', 'tp']]
    g = pd.read_csv('nfl_data/games.csv', low_memory=False)[['game_id', 'roof', 'wind', 'temp']]
    x = p.merge(g, on='game_id')
    x['dome'] = (~x.roof.isin(['outdoors'])).astype(int)          # ολα εκτος ανοιχτων = «κλειστο» (συρομενες κλεινουν ~90%)
    rf = rain_flags()
    out_ = x.dome == 0
    x['wind_a'] = np.where(out_, x.wind.clip(0, 30), 0)
    x['cold_a'] = np.where(out_, (50 - x.temp).clip(0, None), 0)
    x['rain_a'] = np.where(out_, x.game_id.map(rf).fillna(0), 0)
    x['wind_a'] = x.wind_a.fillna(pd.Series(np.where(out_, x.wind.median(), 0), index=x.index))
    x['cold_a'] = x.cold_a.fillna(0)
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']

    # ---- (α) κλειστο γηπεδο (γνωστο απο νωρις)
    print('=== (α) ΚΛΕΙΣΤΟ ΓΗΠΕΔΟ στη βαση συνολων (LOSO) ===')
    x['tp_d'] = T7.loso_blend(x, 'total', ['tp', 'dome'])
    c = T.ols(x[x.season <= 2025], ['tp', 'dome'], 'total')
    print(f'  συντελεστης κλειστου: {c[2]:+.2f} π.  (βαση ηδη {x[(x.season <= 2025) & (x.dome == 1)].tp.mean() - x[(x.season <= 2025) & (x.dome == 0)].tp.mean():+.2f} κλειστα−ανοιχτα, πραγμ {x[(x.season <= 2025) & (x.dome == 1)].total.mean() - x[(x.season <= 2025) & (x.dome == 0)].total.mean():+.2f})')
    r = {S: (np.sqrt(np.mean((d.total - d.tp) ** 2)), np.sqrt(np.mean((d.total - d.tp_d) ** 2))) for S, d in x.groupby('season')}
    print('  RMSE ' + ' · '.join(f"{S % 100}: {a:.2f}→{b:.2f}{'✓' if b < a else '✗'}" for S, (a, b) in r.items()))
    print(f"  καλυτερη 2021-25 {sum(r[S][1] < r[S][0] for S in range(2021, 2026))}/5 · 2016-25 {sum(r[S][1] < r[S][0] for S in range(2016, 2026))}/10")
    for col, lab in (('tp', 'βαση'), ('tp_d', '+κλειστο')):
        for H in ('wk', '72', '24', 'close'):
            z = tot_picks(x, H, col, o)
            print(T9.roi_line(f'{lab} · {H}', z, z.pick))

    # ---- (β) καιρος: εκπαιδευση 2016-23 στον πραγματικο, εφαρμογη 2024-26 στην προγνωση
    print('\n=== (β) ΚΑΙΡΟΣ: εκπαιδευση πραγματικος 2016-23 → προγνωση 2024-26 ===')
    tr = x[(x.season <= 2023)]
    Fw = ['tp', 'dome', 'wind_a', 'cold_a', 'rain_a']
    cw = T.ols(tr, Fw, 'total')
    c0 = T.ols(tr, ['tp', 'dome'], 'total')
    print('  συντελεστες (σταθ, βαση, κλειστο, ανεμος/mph, κρυο/°F, βροχη):', np.round(cw, 3))
    wf = pd.read_csv('nfl_data/weather_fc.csv')
    y = x[x.season >= 2024].merge(wf.drop(columns=['roof']), on='game_id', how='left')
    yo = y.dome == 0
    y['tp0'] = T.pred(y, ['tp', 'dome'], c0)
    for lab in ('d3', 'd1', 'd0'):
        y['wind_f'] = np.where(yo, y[f'wind_{lab}'].clip(0, 30), 0)
        y['cold_f'] = np.where(yo, (50 - y[f'temp_{lab}']).clip(0, None), 0)
        y['rain_f'] = np.where(yo, (y[f'rain_{lab}'] >= 1).astype(int), 0)
        Y = y.drop(columns=['wind_a', 'cold_a', 'rain_a']).rename(columns={'wind_f': 'wind_a', 'cold_f': 'cold_a', 'rain_f': 'rain_a'}).copy()
        Y[['wind_a', 'cold_a', 'rain_a']] = Y[['wind_a', 'cold_a', 'rain_a']].fillna(0)
        y[f'tpw_{lab}'] = T.pred(Y, Fw, cw)
    # πραγματικος καιρος (αναφορα, «τελεια γνωση»)
    y['tpw_act'] = T.pred(y, Fw, cw)
    yy = y[y.total.notna()]
    print('  RMSE συνολων 2024-26 (ματς με αποτελεσμα):')
    for col, lab in (('tp', 'βαση v2'), ('tp0', '+κλειστο'), ('tpw_d3', '+καιρος προγν. 3 μερες'), ('tpw_d1', '+καιρος προγν. 1 μερα'),
                     ('tpw_d0', '+καιρος προγν. ιδια μερα'), ('tpw_act', '+καιρος ΠΡΑΓΜΑΤΙΚΟΣ')):
        rs = {S: np.sqrt(np.mean((d.total - d[col]) ** 2)) for S, d in yy.groupby('season')}
        print(f"     {lab:26} " + ' · '.join(f'{S}: {v:.3f}' for S, v in rs.items()) + f" · ολα {np.sqrt(np.mean((yy.total - yy[col]) ** 2)):.3f}")
    print('  PICKS συνολων ≥3 π. (2024-26):')
    for col, H, lab in (('tp0', '72', '+κλειστο · 72ω'), ('tpw_d3', '72', '+καιρος d3 · 72ω'), ('tp0', '24', '+κλειστο · 24ω'),
                        ('tpw_d1', '24', '+καιρος d1 · 24ω'), ('tp0', '3', '+κλειστο · 3ω'), ('tpw_d0', '3', '+καιρος d0 · 3ω'),
                        ('tp0', 'close', '+κλειστο · κλεισιμο'), ('tpw_d0', 'close', '+καιρος d0 · κλεισιμο')):
        z = tot_picks(y, H, col, o)
        d = z[z.pick]
        per = {S: (len(d[d.season == S]), d[d.season == S].pnl.sum()) for S in (2024, 2025, 2026)}
        print(f"     {lab:24} picks {len(d):3} ROI {100 * d.pnl.sum() / max(len(d), 1):+6.1f}% | " +
              ' '.join(f'{S}: {n}/{100 * pl / max(n, 1):+.0f}%' for S, (n, pl) in per.items()))
    # κινειται η αγορα με την προγνωση;
    w = o[o.H.isin(['wk', 'close'])].pivot(index='game_id', columns='H', values='total').rename(columns={'wk': 'L_open', 'close': 'L_close'})
    m = y.merge(w, left_on='game_id', right_index=True)
    m = m[m.dome == 0]
    m['mv'] = m.L_close - m.L_open
    print('  ΑΓΟΡΑ (ανοιχτα γηπεδα 2024-26): κινηση συνολου ανοιγμα→κλεισιμο ανα προγνωση ανεμου (d1):')
    for lo, hi in ((0, 10), (10, 15), (15, 99)):
        s = m[(m.wind_d1 >= lo) & (m.wind_d1 < hi)]
        print(f"     ανεμος {lo}-{hi} mph: n {len(s):3} · κινηση {s.mv.mean():+.2f} · πραγμ − κλεισιμο {(s.total - s.L_close).mean():+.2f} · πραγμ − ανοιγμα {(s.total - s.L_open).mean():+.2f}")
    for flag in (0, 1):
        s = m[(m.rain_d1 >= 1).astype(int) == flag]
        print(f"     βροχη προγν. ≥1mm={flag}: n {len(s):3} · κινηση {s.mv.mean():+.2f} · πραγμ − κλεισιμο {(s.total - s.L_close).mean():+.2f}")


if __name__ == '__main__':
    main()
