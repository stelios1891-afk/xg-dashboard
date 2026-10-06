# -*- coding: utf-8 -*-
"""nba_refresh.py — NBA LIVE ΜΗΧΑΝΗ: καθημερινη ενημερωση (6/10/2026, Στελιος «φτιαξε τη μηχανη»).
Ρυθμισεις απο το καθαρο τεστ (nba_full_clean_test + nba_fix_test + nba_more_tests):
  ΧΑΝΤΙΚΑΠ  περσι .8 · K 8 · HL 60 · τυχη .75 · μ_w 5 · ροστερ ×1 · ειδικοι/αποδοσεις κx .75 · φιλικα κp .25 · εδρα 2 · + back-to-back 3 π.
  ΣΥΝΟΛΑ    περσι .7 · K 8 · HL 60 · τυχη .5 · μ_w 5 · (χωρις ροστερ/ειδικους/φιλικα) · + Φ3 επιπεδο: μεσο (πραγματικο − μοντελο) των τελευταιων 150 ματς
1. ESPN (nba_espn.py): ματς/box/λεπτα/τραυματιες · ρόστερ (nba_live_roster.py)
2. Τρεχουσα σεζον → nba_gamelogs.csv (ιδια μορφη με Basketball-Reference, ωστε η ιδια μηχανη να τα διαβαζει)
3. Ειδικοι/αποδοσεις (z) & φιλικα (υπολοιπο) τρεχουσας σεζον → nba_full_z.json · ρόστερ → αφετηρια
4. Walk-forward μηχανη (nba_full_clean_test.run_all) → nba_state.json: ratings καθε ομαδας σημερα + Φ3 + αριθμος ματς / τελευταια μερα.
Χρηση: python nba_refresh.py [--no-fetch]"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, subprocess, collections, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
CUR, LAB = 2027, '2026-27'                                # ετησια ενημερωση
CFG_H = (0.8, 8, 60, .75, 5.0, 1.0, .75, .25)            # (περσι, K, HL, τυχη, μ_w, ροστερ, ειδικοι, φιλικα)
CFG_T = (0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0)
B2B_K, H_ADV = 3.0, 2.0
SIG_M, SIG_T = 13.5, 18.0                                 # sd (πραγματικο − κλεισιμο) 2021-26
if '--no-fetch' not in sys.argv:
    for cmd in (['python', 'nba_espn.py'],) + ((['python', 'nba_live_roster.py'],) if os.path.exists('nba_player_games.csv') else ()):   # ρόστερ: τοπικα (θελει nba_player_games.csv)· στο GitHub διαβαζεται το nba_roster_live.json
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        print(f'{cmd[1]}: exit {r.returncode} · ' + ((r.stdout.strip().splitlines() or [''])[-1])[:160])
GM = json.load(open('nba_espn_games.json', encoding='utf-8'))
# ---- 2. τρεχουσα σεζον → nba_gamelogs.csv ----
L = pd.read_csv('nba_gamelogs.csv', low_memory=False)
L = L[L.season_end != CUR]
rows = []
for g in sorted(GM.values(), key=lambda g: g['utc']):
    if g['stype'] != 2: continue
    for me, op, loc, s1, s2 in ((g['home'], g['away'], 'N' if g['neutral'] else '', g['hs'], g['as_']), (g['away'], g['home'], 'N' if g['neutral'] else '@', g['as_'], g['hs'])):
        b, o = g['box'][me], g['box'][op]
        rows.append(dict(date=g['date'], game_location=loc, opp_name_abbr=op, team_game_score=s1, opp_team_game_score=s2, overtimes=('OT' if g['ot'] == 1 else f"{g['ot']}OT") if g['ot'] else '',
                         fga=b['fga'], fta=b['fta'], orb=b['orb'], tov=b['tov'], fg3=b['fg3'], fg3a=b['fg3a'], ft=b['ft'],
                         opp_fga=o['fga'], opp_fta=o['fta'], opp_orb=o['orb'], opp_tov=o['tov'], opp_fg3=o['fg3'], opp_fg3a=o['fg3a'], opp_ft=o['ft'],
                         team=me, season_end=CUR, table='team_game_log_reg'))
if rows: L = pd.concat([L, pd.DataFrame(rows)], ignore_index=True)
L.to_csv('nba_gamelogs.csv', index=False)
n_cur = sum(1 for g in GM.values() if g['stype'] == 2)
print(f'τρεχουσα σεζον: {n_cur} ματς κανονικης περιοδου στο nba_gamelogs.csv')
# ---- 3. z ειδικων/αποδοσεων + φιλικα ----
nd = NormalDist()
Z = json.load(open('nba_full_z.json', encoding='utf-8'))
O = json.load(open('nba_preseason_odds.json', encoding='utf-8'))['seasons'].get(LAB, {}).get('teams', {})
RK = json.load(open('nba_power_rankings.json', encoding='utf-8'))['sources']
def zs(d):
    v = np.array(list(d.values()), float); m, s = v.mean(), v.std(); return {t: (x - m) / s for t, x in d.items()} if s > 0 and len(v) >= 20 else {}
def tdec(v):
    return v.get('title_odds_decimal') or (v.get('secondary_sportsoddshistory') or {}).get('title_odds_last_pre_opener_decimal')
zw = zs({t: v['win_total'] for t, v in O.items() if v.get('win_total') is not None})
zt = zs({t: -math.log(tdec(v)) for t, v in O.items() if tdec(v)})
acc = collections.defaultdict(list); srcs = []
for src, ss in RK.items():
    r = ss.get(LAB)
    if not r or r.get('kind', '') != 'preseason_final' or len(r.get('ranking', [])) < 30: continue
    srcs.append(src)
    for i, t in enumerate(r['ranking'], 1): acc[t].append(nd.inv_cdf(1 - (i - .5) / 30))
zr = {t: float(np.mean(v)) for t, v in acc.items()}
for t in set(zw) | set(zt) | set(zr):
    Z['C'][f'{CUR}|{t}'] = float(np.mean([d[t] for d in (zw, zt, zr) if t in d]))
print(f'ειδικοι/αποδοσεις {LAB}: νικες {len(zw)} · τιτλος {len(zt)} · rankings {len(zr)} ({", ".join(srcs)})')
Lp = pd.read_csv('nba_gamelogs.csv', low_memory=False); Lp = Lp[(Lp.table == 'team_game_log_reg') & (Lp.season_end == CUR - 1)]
Rp = {t: float(np.mean(g.team_game_score - g.opp_team_game_score)) for t, g in Lp.groupby('team')}
res = collections.defaultdict(list)
for g in GM.values():
    if g['stype'] != 1: continue
    for me, op, m in ((g['home'], g['away'], g['hs'] - g['as_']), (g['away'], g['home'], g['as_'] - g['hs'])):
        if me in Rp and op in Rp: res[me].append(float(np.clip(m, -30, 30)) - (Rp[me] - Rp[op]))
for t, v in res.items(): Z['P'][f'{CUR}|{t}'] = sum(v) / (len(v) + 4)
json.dump(Z, open('nba_full_z.json', 'w', encoding='utf-8'))
print(f'φιλικα {LAB}: {sum(len(v) for v in res.values()) // 2} ματς · {len(res)} ομαδες')
# ---- 4. μηχανη ----
import nba_full_clean_test as F
F._init(); C = F._W['C']; F._W['Z'] = Z
RL = json.load(open('nba_roster_live.json', encoding='utf-8'))
R2 = C._radj2()['V0|W1']
for t, v in RL.get('delta', {}).items(): R2[f'{CUR}|{t}'] = v
G = C.G
out = {}
for nm, cfg in (('h', CFG_H), ('t', CFG_T)):
    _, mg, tt, fin = F.run_all(cfg)
    carry, beta, kx, kp = cfg[0], cfg[5], cfg[6], cfg[7]
    if CUR in fin:
        f = fin[CUR]; src = f'{CUR}: {int((G.season.values == CUR).sum())} ματς'
    else:                                                   # πριν το 1ο ματς: αφετηρια = περσι × carry + ροστερ/ειδικοι/φιλικα (ιδια με run_all)
        p = fin[CUR - 1]; f = dict(mu=p['mu'], pm=p['pm'], O={}, D={}, P={})
        for t in p['O']:
            adj = beta * R2.get(f'{CUR}|{t}', 0.0) + kx * Z['C'].get(f'{CUR}|{t}', 0.0) + kp * Z['P'].get(f'{CUR}|{t}', 0.0)
            f['O'][t] = carry * p['O'][t] + adj / 2; f['D'][t] = carry * p['D'][t] - adj / 2; f['P'][t] = carry * p['P'][t]
        src = f'αφετηρια {CUR} (περσι × {carry} + ροστερ/ειδικοι/φιλικα)'
    out[nm] = dict(f, src=src); out[nm + '_pred'] = (mg, tt)
# Φ3: επιπεδο συνολων απο τα τελευταια 150 ματς της σεζον (μονο οσα εχουν παιχτει)
mg_t, tt_t = out['t_pred']; m = (G.season.values == CUR) & np.isfinite(tt_t)
resid = ((G.hs + G.as_).values.astype(float) - tt_t)[m][-150:]
RES = float(np.mean(resid)) if len(resid) >= 30 else 0.0
# αριθμος ματς & τελευταια μερα ανα ομαδα
gp, last = collections.Counter(), {}
for g in sorted(GM.values(), key=lambda g: g['utc']):
    if g['stype'] != 2: continue
    for t in (g['home'], g['away']): gp[t] += 1; last[t] = g['date']
state = dict(built=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=CUR, sig_m=SIG_M, sig_t=SIG_T, b2b_k=B2B_K, h=H_ADV,
             cfg_h=list(CFG_H), cfg_t=list(CFG_T), res_t=RES, n_res=int(len(resid)),
             h_eng={k: v for k, v in out['h'].items()}, t_eng={k: v for k, v in out['t'].items()}, gp=dict(gp), last=last,
             roster=RL.get('delta', {}), z=dict(C={k.split('|')[1]: v for k, v in Z['C'].items() if k.startswith(f'{CUR}|')}, P={k.split('|')[1]: v for k, v in Z['P'].items() if k.startswith(f'{CUR}|')}),
             model=f'NBA: χαντικαπ {CFG_H} + B2B {B2B_K} · συνολα {CFG_T} + Φ3')
json.dump(state, open('nba_state.json', 'w', encoding='utf-8'), ensure_ascii=False)
h = out['h']; net = {t: (h['O'][t] - h['D'][t]) for t in h['O']}
print(f"nba_state.json: {h['src']} · Φ3 {RES:+.2f} ({len(resid)} ματς) · κορυφη: " + ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(net.items(), key=lambda kv: -kv[1])[:5])
      + ' · τελος: ' + ' · '.join(f'{t} {v:+.1f}' for t, v in sorted(net.items(), key=lambda kv: kv[1])[:3]))
