# -*- coding: utf-8 -*-
"""nfl_sbr_build.py — απο το ακατεργαστο ιστορικο SBR (nfl_data/sbr_lines.jsonl) σε γραμμες ανα ΩΡΑ ΠΡΙΝ ΤΟ ΜΑΤΣ.

Αντιστοιχιση με nflverse: ιδιες ομαδες (γηπ/φιλ) + εναρξη ±36ω → game_id.  Μονο αλλαγες ΠΡΙΝ την εναρξη (οχι in-play).
Για καθε ματς, βιβλιο και ωρα H (ποσες ωρες πριν): η τελευταια γραμμη που ισχυε εκεινη τη στιγμη.
  H = open (πρωτη εμφανιση ποτε), wk (ανοιγμα εβδομαδας: πρωτη γραμμη μετα το προηγουμενο ματς των ομαδων), 168, 120, 72, 48, 36, 24, 18, 12, 8, 6, 4, 3, 2, 1, 0.5, close (τελευταια πριν την εναρξη)
Χαντικαπ σε μορφη nflverse: spread = ποντοι ΥΠΕΡ γηπεδουχου (= −homeSpread του SBR).
Εξοδος nfl_data/sbr_slots.csv: game_id, book, H, spread, h_odds, a_odds, total, o_odds, u_odds, t_spread, t_total (ωρα UTC)
  + book = 'cons' : διαμεσος ολων των βιβλιων (γραμμη) με διαμεσες αποδοσεις.  *_dec = δεκαδικες αποδοσεις.
"""
import json, os
import numpy as np
import pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
HS = ['open', 'wk', 168, 120, 72, 48, 36, 24, 18, 12, 8, 6, 4, 3, 2, 1, 0.5, 'close']
MAP = {'JAC': 'JAX', 'LAR': 'LA', 'WSH': 'WAS', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LA'}


def dec(a):
    """αμερικανικη → δεκαδικη (NaN αν λειπει ή ειναι ακυρη)."""
    try:
        a = float(a)
    except (TypeError, ValueError):
        return np.nan
    if np.isnan(a) or abs(a) < 100:
        return np.nan
    return 1 + a / 100 if a > 0 else 1 + 100 / abs(a)


def at(rows, ko, H, t_wk=None):
    """rows: [[t, ...]] ταξινομημενα, μονο πριν το ko. Επιστρεφει [t, ...] που ισχυε H ωρες πριν.
    H='wk' → «ανοιγμα εβδομαδας»: πρωτη γραμμη μετα το t_wk (αν δεν αλλαξε, αυτη που ισχυε τοτε)."""
    if not rows:
        return None
    if H == 'open':
        return rows[0]
    if H == 'close':
        return rows[-1]
    if H == 'wk':
        after = [r for r in rows if r[0] >= t_wk]
        if after:
            return after[0]
        before = [r for r in rows if r[0] < t_wk]
        return before[-1] if before else None
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
    # «ανοιγμα εβδομαδας»: 4ω μετα την εναρξη του προηγουμενου ματς της ομαδας που επαιξε πιο προσφατα (ουτε πριν απο 8 μερες)
    lg = pd.concat([g[['game_id', 'ko', 'home_team']].set_axis(['game_id', 'ko', 'team'], axis=1),
                    g[['game_id', 'ko', 'away_team']].set_axis(['game_id', 'ko', 'team'], axis=1)]).sort_values('ko')
    lg['prev'] = lg.groupby('team').ko.shift(1)
    pv = lg.groupby('game_id').prev.max()
    g['t_wk'] = [max(p + pd.Timedelta(hours=4), k - pd.Timedelta(days=8)) if pd.notna(p) else k - pd.Timedelta(days=8)
                 for p, k in zip(g.game_id.map(pv), g.ko)]
    twk = dict(zip(g.game_id, g.t_wk))
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
                s, t = at(S, ko, H, twk[gid]), at(T, ko, H, twk[gid])
                if s is None and t is None:
                    continue
                row = dict(game_id=gid, book=book, H=str(H),
                           spread=-s[1] if s else np.nan, h_odds=s[2] if s else np.nan, a_odds=s[3] if s else np.nan,
                           total=t[1] if t else np.nan, o_odds=t[2] if t else np.nan, u_odds=t[3] if t else np.nan,
                           t_spread=s[0].isoformat() if s else '', t_total=t[0].isoformat() if t else '')
                for k in ('h', 'a', 'o', 'u'):
                    row[f'{k}_dec'] = dec(row[f'{k}_odds'])
                out.append(row)
                per.setdefault(str(H), []).append(row)
        for H, rows in per.items():
            x = pd.DataFrame(rows)
            # διαμεσος: γραμμη, και αποδοσεις ΣΕ ΔΕΚΑΔΙΚΗ μορφη (η διαμεσος αμερικανικων −110/+100 ειναι ακυρη)
            out.append(dict(game_id=gid, book='cons', H=H, spread=x.spread.median(), total=x.total.median(),
                            h_dec=x.h_dec.median(), a_dec=x.a_dec.median(), o_dec=x.o_dec.median(),
                            u_dec=x.u_dec.median(), t_spread='', t_total=''))
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
