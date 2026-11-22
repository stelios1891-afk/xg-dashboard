# -*- coding: utf-8 -*-
"""nfl_pin_build.py — γραμμες PINNACLE ανα ωρα απο τα στιγμιοτυπα TOA (nfl_data/toa_hist.jsonl) → nfl_data/pin_slots.csv

Στιγμιοτυπα: καθε μερα 16:00 UTC, KO−3ω, KO−30′ (2020→2025· λειπει τελος 2020 και το 2026).
Ιδια μορφη με sbr_slots.csv (spread = ποντοι υπερ γηπεδουχου), ωστε να τρεχουν τα ιδια τεστ:
  wk    πρωτο στιγμιοτυπο με Pinnacle ΜΕΤΑ το προηγουμενο ματς των ομαδων (4ω μετα την εναρξη του)
  72/24 τελευταιο στιγμιοτυπο με Pinnacle τουλαχιστον 72ω/24ω πριν την εναρξη
  3     το στιγμιοτυπο KO−3ω · close το στιγμιοτυπο KO−30′
Στηλη h_age: ποσες ωρες πριν την εναρξη ηταν το στιγμιοτυπο που χρησιμοποιηθηκε.
"""
import json, os
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_wintotals as W

D = M.D


def main():
    g = pd.read_csv(os.path.join(D, 'games.csv'), low_memory=False)
    g = g[(g.season >= 2019) & g.gametime.notna()].copy()
    for c in ('home_team', 'away_team'):
        g[c] = g[c].replace(M.RENAME)
    g['ko'] = pd.to_datetime(g.gameday + ' ' + g.gametime).dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    lg = pd.concat([g[['game_id', 'ko', 'home_team']].set_axis(['game_id', 'ko', 'team'], axis=1),
                    g[['game_id', 'ko', 'away_team']].set_axis(['game_id', 'ko', 'team'], axis=1)]).sort_values('ko')
    lg['prev'] = lg.groupby('team').ko.shift(1)
    pv = lg.groupby('game_id').prev.max()
    g['t_wk'] = [max(p + pd.Timedelta(hours=4), k - pd.Timedelta(days=8)) if pd.notna(p) else k - pd.Timedelta(days=8)
                 for p, k in zip(g.game_id.map(pv), g.ko)]
    idx = {}
    for r in g.itertuples():
        idx.setdefault((r.home_team, r.away_team), []).append((r.ko, r.game_id))
    info = g.set_index('game_id')[['ko', 't_wk']].to_dict('index')
    rows, unk, first = {}, set(), {}
    for line in open(os.path.join(D, 'toa_hist.jsonl'), encoding='utf-8'):
        s = json.loads(line)
        ts = pd.Timestamp(s['snap_ts'] or s['req_ts'])
        for ev in s['ev']:
            _, com, hn, an, bk = ev
            h, a = W.NAMES.get(hn), W.NAMES.get(an)
            if h is None or a is None:
                unk.add(hn if h is None else an)
                continue
            b = bk.get('pinnacle')
            if not b:
                continue
            st = pd.Timestamp(com)
            cand = [(abs((k - st).total_seconds()), gid, k) for k, gid in idx.get((h, a), [])]
            cand = [c for c in cand if c[0] < 36 * 3600]
            if not cand:
                continue
            _, gid, ko = min(cand)
            if ts >= ko:
                continue
            spread = hd = ad = total = od = ud = np.nan
            for nm, pt, pr in b.get('s', []):
                if nm == hn:
                    spread, hd = -pt, pr
                elif nm == an:
                    ad = pr
            for nm, pt, pr in b.get('t', []):
                if nm == 'Over':
                    total, od = pt, pr
                elif nm == 'Under':
                    ud = pr
            rows.setdefault(gid, []).append((ts, spread, hd, ad, total, od, ud, s['kind']))
    out = []
    for gid, rr in rows.items():
        rr.sort(key=lambda x: x[0])
        ko, twk = info[gid]['ko'], info[gid]['t_wk']
        pick = {}
        after = [x for x in rr if x[0] >= twk]
        if after:
            pick['wk'] = after[0]
        for H in (120, 72, 48, 24):
            c = [x for x in rr if x[0] <= ko - pd.Timedelta(hours=H)]
            if c:
                pick[str(H)] = c[-1]
        c = [x for x in rr if x[7] == 'ko-3h']
        if c:
            pick['3'] = c[-1]
        c = [x for x in rr if x[7] == 'ko-30m']
        if c:
            pick['close'] = c[-1]
        for H, x in pick.items():
            out.append(dict(game_id=gid, book='pinnacle', H=H, spread=x[1], h_dec=x[2], a_dec=x[3], total=x[4], o_dec=x[5],
                            u_dec=x[6], h_age=(ko - x[0]).total_seconds() / 3600))
        first[gid] = (ko - rr[0][0]).total_seconds() / 3600
    d = pd.DataFrame(out)
    d.to_csv(os.path.join(D, 'pin_slots.csv'), index=False)
    print('αγνωστες ομαδες:', unk)
    m = d.merge(g[['game_id', 'season', 'game_type']], on='game_id')
    print('ματς κανονικης ανα σεζον/ωρα:')
    print(m[m.game_type == 'REG'].pivot_table(index='season', columns='H', values='game_id', aggfunc='nunique').reindex(
        columns=['wk', '120', '72', '48', '24', '3', 'close']).to_string())
    print('ωρες πριν την εναρξη του στιγμιοτυπου «wk» (διαμεσος):', round(d[d.H == 'wk'].h_age.median(), 1))
    print('πρωτη εμφανιση Pinnacle: διαμεσος ωρες πριν', round(np.median(list(first.values())), 1))


if __name__ == '__main__':
    main()
