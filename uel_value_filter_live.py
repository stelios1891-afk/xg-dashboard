"""uel_value_filter_live.py — 15/10/2026. Το φιλτρο Φ2 («η αξια ενδεκαδας βλεπει την ομαδα του pick ≥0.5 γκολ χειροτερη απο το μοντελο») πανω στον
LIVE κανονα «UEL φαβορι εντος» (80% xG, ≤−0.5, edge ≥4%, 36-12ω, Crown & SBOBET). Ευθεια αξιας LOSO (ολα τα ευρωπαικα, ln λογου αξιας + εδρα).
"""
import sys, pickle
src = open('uel_home_fav_xi.py', encoding='utf-8').read().split('rows = []')[0]
exec(src)
TV = pickle.load(open('euro_team_value.pkl', 'rb'))
idx = [i for i in range(len(MIDS)) if COMP[i] in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague') and str(MIDS[i]) in TV]
VF = {}
for s in ('2223', '2324', '2425', '2526'):
    tr = [i for i in idx if SEA[i] != s]
    VF[s] = np.polyfit([np.log(TV[str(MIDS[i])][0] / TV[str(MIDS[i])][1]) for i in tr], [float(GD[i]) for i in tr], 1)
rows = []
for i in range(len(MIDS)):
    if COMP[i] != 'EuropaLeague' or str(MIDS[i]) not in I8: continue
    k = I8[str(MIDS[i])]
    if not D8['FM'][k]: continue
    dist = sdist(D8['LH'][k], D8['LA'][k])
    for bk in ('Crown', 'SBOBET'):
        for h in (36, 24, 18, 12):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            if L <= -0.5 and 1.70 <= oh <= 2.10 and edge(*cover_q(dist, 1, L), oh) >= .04:
                mid = str(MIDS[i]); dis = np.nan
                if mid in TV:
                    vm = VF[SEA[i]][0] * np.log(TV[mid][0] / TV[mid][1]) + VF[SEA[i]][1]; dis = vm - (D8['LH'][k] - D8['LA'][k])
                rows.append(dict(sea=SEA[i], bk=bk, pnl=picks.settle(GD[i], 1, L, oh), dis=dis))
                break
P = pd.DataFrame(rows)
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% ({m.mean() * n:+5.1f}μ) (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print('LIVE κανονας «UEL φαβορι εντος» + φιλτρο αξιας Φ2')
print(f'   ολα                       {cc(P)}')
print(f'   ΚΟΒΟΝΤΑΙ (αξια ≥0.5 κατω)  {cc(P[P.dis <= -.5])}')
print(f'   ΜΕΝΟΥΝ                    {cc(P[~(P.dis <= -.5)])}')
print(f'   (χωρις αξια: {P.dis.isna().sum()} picks ανα βιβλιο-συνολο)')
