"""NFL αποντες βασικοι ανα θεση, ΟΠΩΣ ΗΤΑΝ ΓΝΩΣΤΟΙ πριν το ματς → nfl_data/absence_games.csv

  python nfl_absence.py

Βασικος = ≥60% των φασεων (επιθεσης ή αμυνας) κατα μεσο ορο στα 3 προηγουμενα ματς της ομαδας την ιδια σεζον.
Για καθε ομαδα-ματς και ομαδα θεσεων (QB, OL, WR, TE, RB, EDGE, DL, LB, CB, S):
  F_x  = βασικοι Out/Doubtful στην επισημη αναφορα (Παρασκευη) Η εκτος ενεργου ροστερ (IR/PUP/αποβολη/κομμενος/
         αλλη ομαδα) την εβδομαδα του ματς              → γνωστο ~1-2 μερες πριν
  Q_x  = βασικοι Questionable (στις αναφορες ~75-80% τελικα παιζουν)
  G_x  = F_x + δηλωμενοι inactive τη μερα του ματς (INA) → γνωστο ~90′ πριν
  A_x  = πραγματικα δεν επαιξαν (0 φασεις) — μονο για ελεγχο, ΟΧΙ για το μοντελο
Ταυτοποιηση παικτη: snap counts (pfr_id) ↔ κεντρικη λιστα nflverse players.csv (pfr_id ↔ gsis_id) ↔ ροστερ/αναφορες (gsis_id).
"""
import os
import numpy as np
import pandas as pd
import nfl_model as M

D = M.D
POS = {'QB': 'QB', 'T': 'OL', 'G': 'OL', 'C': 'OL', 'OT': 'OL', 'OG': 'OL', 'OL': 'OL', 'WR': 'WR', 'TE': 'TE',
       'RB': 'RB', 'FB': 'RB', 'HB': 'RB', 'DE': 'EDGE', 'OLB': 'EDGE', 'EDGE': 'EDGE', 'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
       'ILB': 'LB', 'LB': 'LB', 'MLB': 'LB', 'CB': 'CB', 'DB': 'CB', 'S': 'S', 'SS': 'S', 'FS': 'S', 'SAF': 'S'}
GRPS = ['QB', 'OL', 'WR', 'TE', 'RB', 'EDGE', 'DL', 'LB', 'CB', 'S']
OFF = {'QB', 'OL', 'WR', 'TE', 'RB'}
GONE = {'RES', 'CUT', 'RET', 'EXE', 'TRC', 'TRD', 'E01', 'SUS', 'PUP', 'NON', 'DEV'}


PL = pd.read_csv(os.path.join(D, 'cache', 'players.csv'), low_memory=False, usecols=['pfr_id', 'gsis_id']).dropna()


def main():
    out = []
    for y in range(2016, 2027):
        sn = pd.read_csv(os.path.join(D, 'cache', 'snaps', f'snap_{y}.csv'))
        sn = sn[sn.game_type == 'REG'].copy()
        sn['team'] = sn.team.replace(M.RENAME)
        sn['grp'] = sn.position.map(POS)
        sn = sn[sn.grp.notna()]
        sn['pct'] = np.where(sn.grp.isin(OFF), sn.offense_pct, sn.defense_pct)
        ro = pd.read_csv(os.path.join(D, 'cache', 'rost', f'rost_{y}.csv'), low_memory=False)
        ro = ro[ro.game_type == 'REG']
        ro['team'] = ro.team.replace(M.RENAME)
        # κεντρικη λιστα παικτων nflverse (εχει και τους OL) + οτι εχει το ροστερ
        pfr2gsis = pd.concat([PL, ro.dropna(subset=['pfr_id', 'gsis_id'])[['pfr_id', 'gsis_id']]])             .drop_duplicates('pfr_id').set_index('pfr_id').gsis_id
        rstat = ro.set_index(['week', 'gsis_id']).status
        rteam = ro.set_index(['week', 'gsis_id']).team
        rstat = rstat[~rstat.index.duplicated()]
        rteam = rteam[~rteam.index.duplicated()]
        inj = pd.read_csv(os.path.join(D, 'cache', 'inj', f'inj_{y}.csv'))
        inj = inj[inj.game_type == 'REG']
        istat = inj.drop_duplicates(['week', 'gsis_id'], keep='last').set_index(['week', 'gsis_id']).report_status
        games = sn[['game_id', 'week', 'team']].drop_duplicates().sort_values(['team', 'week'])
        for T, gt in games.groupby('team'):
            s = sn[sn.team == T]
            P = s.pivot_table(index=['pfr_player_id', 'grp'], columns='week', values='pct', aggfunc='max')
            wks = list(gt.week)
            P = P.reindex(columns=wks).fillna(0)
            for i, (gid, wk) in enumerate(zip(gt.game_id, gt.week)):
                if i < 3:
                    continue
                prev = P[wks[i - 3:i]].mean(axis=1)
                st = prev[prev >= 0.6]
                rec = {'game_id': gid, 'team': T}
                for c in GRPS:
                    for k in 'FQGA':
                        rec[f'{k}_{c}'] = 0
                for (pid, grp), _ in st.items():
                    gs = pfr2gsis.get(pid)
                    status = rstat.get((wk, gs)) if gs is not None else None
                    team_now = rteam.get((wk, gs)) if gs is not None else None
                    rep = istat.get((wk, gs)) if gs is not None else None
                    gone = (status in GONE) or (gs is not None and team_now is not None and team_now != T) or \
                           (gs is not None and status is None)
                    f = gone or rep in ('Out', 'Doubtful')
                    rec[f'F_{grp}'] += int(f)
                    rec[f'Q_{grp}'] += int((not f) and rep == 'Questionable')
                    rec[f'G_{grp}'] += int(f or status == 'INA')
                    rec[f'A_{grp}'] += int(P.at[(pid, grp), wk] == 0)
                out.append(rec)
        print(y, 'ομαδα-ματς', sum(1 for r in out if r['game_id'].startswith(str(y))), flush=True)
    d = pd.DataFrame(out)
    d.to_csv(os.path.join(D, 'absence_games.csv'), index=False)
    # ελεγχος: ποσο ταιριαζει «γνωστο» με «πραγματικο»
    for k in 'FG':
        tot_a = sum(d[f'A_{c}'].sum() for c in GRPS)
        tot_k = sum(d[f'{k}_{c}'].sum() for c in GRPS)
        both = sum(np.minimum(d[f'{k}_{c}'], d[f'A_{c}']).sum() for c in GRPS)
        print(f'{k}: δηλωμενοι αποντες {tot_k} · πραγματικοι {tot_a} · κοινοι {both} ({100 * both / max(tot_a, 1):.0f}% των πραγματικων)')
    print('μεσος ανα ομαδα-ματς (F):', {c: round(d[f'F_{c}'].mean(), 2) for c in GRPS})


if __name__ == '__main__':
    main()
