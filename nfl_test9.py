"""NFL τεστ 9: πλαισιο ματς πανω στη βαση v2 (+ αγκυρα αγορας), 2019-25 (picks) / 2016-25 (σφαλμα).

(α) ΚΙΝΗΤΡΟ εβδ 15-18 απο τη βαθμολογια ΠΡΙΝ το ματς (προσεγγιση, οχι επισημα clinch):
    ΕΚΤΟΣ    = νικες + υπολοιπα ματς < νικες της 7ης ομαδας της περιφερειας (μαθηματικα σχεδον αποκλεισμενη)
    ΚΛΕΙΔΩΜ. = 1η της περιφερειας με διαφορα > υπολοιπα ματς απο τη 2η (το Νο1 εξασφαλισμενο)
    ΜΑΧΗ     = ολες οι αλλες
    Μετραμε: (πραγμ − μοντελο) και (πραγμ − κλεισιμο) υπερ καθε γκρουπ· picks ανοιγματος υπερ ομαδας χωρις κινητρο
    (ΕΚΤΟΣ/ΚΛΕΙΔΩΜ.) κοντρα σε ΜΑΧΗ — ο κανονας του NBA (71-75 αγωνας).
(β) ΜΑΤΣ ΚΑΤΗΓΟΡΙΑΣ (div_game): (πραγμ − μοντελο) στην πλευρα του φαβορι, picks ανοιγματος.
(γ) ΦΙΛΤΡΑ για picks που μπαινουν ΑΡΓΟΤΕΡΑ (3 μερες / 24ω πριν):
    Φ1 η γραμμη κινηθηκε ≥1.5 π. ΚΟΝΤΡΑ μας απο το ανοιγμα εβδομαδας → μην παιζεις
    Φ2 «αργο» pick: δεν ηταν pick στο ανοιγμα, γεννηθηκε απο την κινηση → μην παιζεις
    Φ3 ο QB αλλαξε μεσα στην εβδομαδα (QB που ξεκινησε ≠ QB του προηγουμενου ματς) στην πλευρα μας / του αντιπαλου
    Κριτηριο φιλτρου (οπως NBA): τα picks που κοβονται χειροτερα απο οσα μενουν σε ≥4/5 σεζον 2021-25.
"""
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_engine as E
import nfl_test7 as T7

DIV = {'AFC East': 'BUF MIA NE NYJ', 'AFC North': 'BAL CIN CLE PIT', 'AFC South': 'HOU IND JAX TEN',
       'AFC West': 'DEN KC LV LAC', 'NFC East': 'DAL NYG PHI WAS', 'NFC North': 'CHI DET GB MIN',
       'NFC South': 'ATL CAR NO TB', 'NFC West': 'ARI LA SF SEA'}
CONF = {t: d[:3] for d, ts in DIV.items() for t in ts.split()}
S5 = list(range(2021, 2026))


def standings_groups(g):
    """Γκρουπ κινητρου καθε ομαδας πριν απο καθε ματς κανονικης περιοδου."""
    reg = g[g.game_type == 'REG'].sort_values('t')
    out = {}
    for S, gs in reg.groupby('season'):
        n_games = 16 if S <= 2020 else 17
        W = {t: 0.0 for t in CONF}
        P = {t: 0 for t in CONF}
        for t_now, wk in gs.groupby('t'):
            for c in ('AFC', 'NFC'):
                teams = sorted([t for t in CONF if CONF[t] == c], key=lambda t: -W[t])
                w7 = W[teams[6]]
                first, second = teams[0], teams[1]
                for t in teams:
                    rem = n_games - P[t]
                    if W[t] + rem < w7:
                        grp = 'ΕΚΤΟΣ'
                    elif t == first and W[first] - W[second] > n_games - P[second]:
                        grp = 'ΚΛΕΙΔΩΜ.'
                    else:
                        grp = 'ΜΑΧΗ'
                    for r in wk.itertuples():
                        if t in (r.home_team, r.away_team):
                            out[(r.game_id, t)] = grp
            for r in wk.itertuples():
                if pd.isna(r.result):
                    continue
                P[r.home_team] += 1; P[r.away_team] += 1
                W[r.home_team] += 1 if r.result > 0 else 0.5 if r.result == 0 else 0
                W[r.away_team] += 1 if r.result < 0 else 0.5 if r.result == 0 else 0
    return out


def picks_at(x, H, col, o, thr=2.5):
    s = o[o.H == H][['game_id', 'spread', 'h_dec', 'a_dec']].rename(columns={'spread': f'L', 'h_dec': 'hd', 'a_dec': 'ad'})
    z = x.merge(s, on='game_id').dropna(subset=['L'])
    e = z[col] - z.L
    z['pick'] = e.abs() >= thr
    z['side'] = np.sign(e)
    rr = (z.result - z.L) * z.side
    od = np.where(z.side > 0, z.hd, z.ad); od = np.where(np.isnan(od), 1.909, od)
    z['pnl'] = np.where(rr > 0, od - 1, np.where(rr < 0, -1, 0))
    return z


def roi_line(lab, z, mask):
    d = z[mask & z.pick & z.season.between(2019, 2025)]
    per = {S: (len(d[d.season == S]), d[d.season == S].pnl.sum()) for S in range(2019, 2026)}
    pos = sum(per[S][1] > 0 for S in S5)
    return f"  {lab:46} picks {len(d):4} ROI {100 * d.pnl.sum() / max(len(d), 1):+6.1f}% · 21-25 θετ {pos}/5 | " + \
        ' '.join(f"{S % 100}:{per[S][0]}/{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in range(2019, 2026))


def filt(lab, z, cut):
    """cut: μασκα picks που ΚΟΒΟΝΤΑΙ. Συγκριση κομμενων vs υπολοιπων ανα σεζον."""
    h = z.pick & z.season.between(2019, 2025)
    a, b = z[h & cut], z[h & ~cut]
    worse = sum((a[a.season == S].pnl.mean() if (a.season == S).any() else 0) < b[b.season == S].pnl.mean() for S in S5)
    print(f"  {lab:44} κοβονται {len(a):3} ROI {100 * a.pnl.mean():+6.1f}% · μενουν {len(b):4} ROI {100 * b.pnl.mean():+5.1f}% "
          f"(πριν {100 * z[h].pnl.mean():+5.1f}%) · κομμενα χειροτερα 21-25 {worse}/5")


def main():
    g, off = M.load()
    p = pd.read_csv('nfl_data/test8_preds.csv')
    p['mp'] = p['mp_βαση v2']
    p['mp_a'] = T7.loso_blend(p, 'result', ['mp', 'mk_d'])
    x = p.merge(g[['game_id', 'home_team', 'away_team', 'div_game', 'home_qb_id', 'away_qb_id']], on='game_id')
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    cl = o[o.H == 'close'][['game_id', 'spread']].rename(columns={'spread': 'close'})
    x = x.merge(cl, on='game_id', how='left')
    x['close'] = x.close.fillna(x.spread_line)

    # (α) κινητρο
    G_ = standings_groups(g)
    x['gh'] = [G_.get((a, b), 'ΜΑΧΗ') for a, b in zip(x.game_id, x.home_team)]
    x['ga'] = [G_.get((a, b), 'ΜΑΧΗ') for a, b in zip(x.game_id, x.away_team)]
    late = x.wk >= 15
    print('=== (α) ΚΙΝΗΤΡΟ (εβδ 15-18) ===')
    print('  ματς ανα γκρουπ (ομαδα-ματς 2016-25):', pd.concat([x[late & (x.season <= 2025)].gh, x[late & (x.season <= 2025)].ga]).value_counts().to_dict())
    rows = []
    for side, oth, sg in (('home', 'away', 1), ('away', 'home', -1)):
        d = x[late & (x.season <= 2025)].copy()
        d['grp'] = d['gh' if side == 'home' else 'ga']
        d['ogrp'] = d['ga' if side == 'home' else 'gh']
        d['res_m'] = (d.result - d.mp) * sg
        d['res_c'] = (d.result - d.close) * sg
        d['wk18'] = d.wk == 18
        rows.append(d[['season', 'grp', 'ogrp', 'res_m', 'res_c', 'wk18']])
    R = pd.concat(rows)
    for wk18 in (False, True):
        sub = R[R.wk18 == wk18]
        print(f"  {'εβδ 18' if wk18 else 'εβδ 15-17'}: πραγμ − μοντελο / πραγμ − κλεισιμο υπερ της ομαδας (ποντοι, ±σφαλμα):")
        for grp in ('ΕΚΤΟΣ', 'ΚΛΕΙΔΩΜ.', 'ΜΑΧΗ'):
            s = sub[sub.grp == grp]
            if len(s):
                print(f"     {grp:9} n {len(s):4}  μοντελο {s.res_m.mean():+5.2f}±{s.res_m.std() / np.sqrt(len(s)):.2f} · κλεισιμο {s.res_c.mean():+5.2f}±{s.res_c.std() / np.sqrt(len(s)):.2f}")
    for col, lab in (('mp', 'βαση v2'), ('mp_a', 'βαση+αγκυρα')):
        z = picks_at(x, 'wk', col, o)
        fav_h = z.side > 0
        our = np.where(fav_h, z.gh, z.ga); their = np.where(fav_h, z.ga, z.gh)
        nomot = np.isin(our, ['ΕΚΤΟΣ', 'ΚΛΕΙΔΩΜ.']) & (their == 'ΜΑΧΗ') & (z.wk >= 15)
        print(f'  ανοιγμα, {lab}:')
        print(roi_line('picks εβδ 15-18 ολα', z, z.wk >= 15))
        print(roi_line('υπερ ομαδας ΧΩΡΙΣ κινητρο κοντρα σε ΜΑΧΗ', z, nomot))
        print(roi_line('κοντρα σε ομαδα χωρις κινητρο (ΜΑΧΗ υπερ)', z, (their != 'ΜΑΧΗ') & (our == 'ΜΑΧΗ') & (z.wk >= 15)))
        filt('φιλτρο: κοψε υπερ χωρις-κινητρο vs ΜΑΧΗ', z, pd.Series(nomot, index=z.index))

    # (β) ματς κατηγοριας
    print('\n=== (β) ΜΑΤΣ ΚΑΤΗΓΟΡΙΑΣ ===')
    h = x.season <= 2025
    for dv in (1, 0):
        d = x[h & (x.div_game == dv)]
        fs = np.sign(d.close).replace(0, 1)
        print(f"  {'κατηγοριας' if dv else 'αλλα'}: n {len(d)} · πραγμ − μοντελο υπερ φαβορι {((d.result - d.mp) * fs).mean():+.2f} · πραγμ − κλεισιμο {((d.result - d.close) * fs).mean():+.2f}")
    for col, lab in (('mp', 'βαση v2'), ('mp_a', 'βαση+αγκυρα')):
        z = picks_at(x, 'wk', col, o)
        print(f'  ανοιγμα, {lab}:')
        print(roi_line('ματς κατηγοριας', z, z.div_game == 1))
        print(roi_line('αλλα ματς', z, z.div_game == 0))
        favpick = (z.side == np.sign(z.L).replace(0, 1))
        print(roi_line('κατηγοριας, pick στο αουτσαιντερ', z, (z.div_game == 1) & ~favpick))
        print(roi_line('κατηγοριας, pick στο φαβορι', z, (z.div_game == 1) & favpick))

    # (γ) φιλτρα για αργοτερη εισοδο
    print('\n=== (γ) ΦΙΛΤΡΑ (εισοδος αργοτερα) ===')
    tg = E.qb_open_targets(g)
    x['qb_chg_h'] = [tg.get((a, t)) != q for a, t, q in zip(x.game_id, x.home_team, x.home_qb_id)]
    x['qb_chg_a'] = [tg.get((a, t)) != q for a, t, q in zip(x.game_id, x.away_team, x.away_qb_id)]
    for col, lab in (('mp', 'βαση v2'), ('mp_a', 'βαση+αγκυρα')):
        zo = picks_at(x, 'wk', col, o)[['game_id', 'pick', 'side', 'L']].rename(columns={'pick': 'pick_o', 'side': 'side_o', 'L': 'L_o'})
        for H, hl in (('72', '3 μερες'), ('24', '24ω')):
            z = picks_at(x, H, col, o).merge(zo, on='game_id', how='left')
            # κοντρα μας: παιζουμε γηπ (side +1) και η γραμμη ανεβηκε (θελει μεγαλυτερη νικη), ή φιλοξ. και κατεβηκε
            against = (z.L - z.L_o) * z.side >= 1.5
            born = ~z.pick_o.fillna(False).astype(bool) | (z.side_o != z.side)
            ours_chg = np.where(z.side > 0, z.qb_chg_h, z.qb_chg_a).astype(bool)
            opp_chg = np.where(z.side > 0, z.qb_chg_a, z.qb_chg_h).astype(bool)
            print(f'  {lab} · εισοδος {hl}:')
            print(roi_line('ολα τα picks', z, z.pick))
            filt('Φ1 γραμμη ≥1.5 π. κοντρα απο ανοιγμα', z, against)
            filt('Φ2 «αργο» pick (οχι pick στο ανοιγμα)', z, born)
            filt('Φ3α αλλαγη QB στην ΠΛΕΥΡΑ ΜΑΣ', z, pd.Series(ours_chg, index=z.index))
            filt('Φ3β αλλαγη QB στον ΑΝΤΙΠΑΛΟ', z, pd.Series(opp_chg, index=z.index))


if __name__ == '__main__':
    main()
