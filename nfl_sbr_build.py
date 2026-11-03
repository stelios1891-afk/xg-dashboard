# -*- coding: utf-8 -*-
"""nfl_sbr_build.py — απο το ακατεργαστο ιστορικο SBR (nfl_data/sbr_lines.jsonl) σε γραμμες ανα ΩΡΑ ΠΡΙΝ ΤΟ ΜΑΤΣ.

Αντιστοιχιση με nflverse: ιδιες ομαδες (γηπ/φιλ) + εναρξη ±36ω → game_id.  Μονο αλλαγες ΠΡΙΝ την εναρξη (οχι in-play).
Για καθε ματς, βιβλιο και ωρα H (ποσες ωρες πριν): η τελευταια γραμμη που ισχυε εκεινη τη στιγμη.
  H = open (πρωτη εμφανιση), 168, 120, 72, 48, 36, 24, 18, 12, 8, 6, 4, 3, 2, 1, 0.5, close (τελευταια πριν την εναρξη)
Χαντικαπ σε μορφη nflverse: spread = ποντοι ΥΠΕΡ γηπεδουχου (= −homeSpread του SBR).
Εξοδος nfl_data/sbr_slots.csv: game_id, book, H, spread, h_odds, a_odds, total, o_odds, u_odds, t_spread, t_total (ωρα UTC)
  + book = 'cons' : διαμεσος ολων των βιβλιων (γραμμη) με διαμεσες αποδοσεις.
"""
import json, os
import numpy as np
import pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
HS = ['open', 168, 120, 72, 48, 36, 24, 18, 12, 8, 6, 4, 3, 2, 1, 0.5, 'close']
MAP = {'JAC': 'JAX', 'LAR': 'LA', 'WSH': 'WAS', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LA'}


def at(rows, ko, H):
    """rows: [[t, ...]] ταξινομημενα, μονο πριν το ko. Επιστρεφει [t, ...] που ισχυε H ωρες πριν."""
    if not rows:
        return None
    if H == 'open':
        return rows[0]
    if H == 'close':
        return rows[-1]
    lim = ko - pd.Timedelta(hours=H)
    c = None
    for r in rows:
        if r[0] <= lim:
            c = r
        else:
            break
    return c


def main():
    g = pd.read_csv(os.path.join(D, 'games.csv'), low_memory=False)
    g = g[(g.season >= 2019) & g.gametime.notna()].copy()
    for c in ('home_team', 'away_team'):
        g[c] = g[c].replace(MAP)
    g['ko'] = pd.to_datetime(g.gameday + ' ' + g.gametime).dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    idx = {}
    for r in g.itertuples():
        idx.setdefault((r.home_team, r.away_team), []).append((r.ko, r.game_id))
    seen, out, miss = set(), [], []
    for line in open(os.path.join(D, 'sbr_lines.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        if r['id'] in seen:
            continue
        seen.add(r['id'])
        h, a = MAP.get(r['home'], r['home']), MAP.get(r['away'], r['away'])
        st = pd.Timestamp(r['start'])
        cand = [(abs((ko - st).total_seconds()), gid, ko) for ko, gid in idx.get((h, a), [])]
        cand = [c for c in cand if c[0] < 36 * 3600]
        if not cand:
            miss.append((r['id'], h, a, r['start']))
            continue
        _, gid, ko = min(cand)
        per = {}
        for book, b in r['books'].items():
            S = sorted([[pd.Timestamp(x[0]), x[1], x[2], x[3]] for x in b['s'] if x[1] is not None], key=lambda x: x[0])
            T = sorted([[pd.Timestamp(x[0]), x[1], x[2], x[3]] for x in b['t'] if x[1] is not None], key=lambda x: x[0])
            S, T = [x for x in S if x[0] < ko], [x for x in T if x[0] < ko]
            for H in HS:
                s, t = at(S, ko, H), at(T, ko, H)
                if s is None and t is None:
                    continue
                row = dict(game_id=gid, book=book, H=str(H),
                           spread=-s[1] if s else np.nan, h_odds=s[2] if s else np.nan, a_odds=s[3] if s else np.nan,
                           total=t[1] if t else np.nan, o_odds=t[2] if t else np.nan, u_odds=t[3] if t else np.nan,
                           t_spread=s[0].isoformat() if s else '', t_total=t[0].isoformat() if t else '')
                out.append(row)
                per.setdefault(str(H), []).append(row)
        for H, rows in per.items():
            x = pd.DataFrame(rows)
            out.append(dict(game_id=gid, book='cons', H=H, spread=x.spread.median(), h_odds=x.h_odds.median(),
                            a_odds=x.a_odds.median(), total=x.total.median(), o_odds=x.o_odds.median(),
                            u_odds=x.u_odds.median(), t_spread='', t_total=''))
    o = pd.DataFrame(out)
    o.to_csv(os.path.join(D, 'sbr_slots.csv'), index=False)
    ng = o.game_id.nunique()
    gs = g[g.result.notna()].groupby('season').game_id.nunique()
    got = o.merge(g[['game_id', 'season']], on='game_id').groupby('season').game_id.nunique()
    print(f'ματς με γραμμες: {ng} · αταιριαστα SBR: {len(miss)} {miss[:5]}')
    print('καλυψη ανα σεζον (παιγμενα nflverse):', {int(s): f'{got.get(s, 0)}/{n}' for s, n in gs.items()})
    print('βιβλια:', o[o.H == 'close'].book.value_counts().to_dict())


if __name__ == '__main__':
    main()
