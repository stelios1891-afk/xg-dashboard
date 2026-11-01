# -*- coding: utf-8 -*-
"""nba_metrics_oracle_test.py — NBA «ΤΕΛΕΙΑ ΠΛΗΡΟΦΟΡΙΑ» με ΟΛΟΥΣ τους δωρεαν δεικτες αξιας παικτη με ιστορικο (28/9/2026).
Συνεχεια του nba_raptor_oracle_test (RAPTOR σταματα 2023). Ιδιο στησιμο: αξια της ΠΡΟΗΓΟΥΜΕΝΗΣ σεζον (γνωστη πριν ξεκινησει),
  μαζεμα με περσινα λεπτα: v = δεικτης × mp/(mp + 500)· χωρις τιμη → «λεπτα αγνωστων»· λεπτα οπως Τ2 (ποιοι επαιξαν ΓΝΩΣΤΟ).
Δεικτες: BPM (Basketball-Reference advanced) · DARKO dpm · LEBRON · MAMBA · RAPM 3 ετων (λήγει περσι) — nbarapm.com/load/{csv}.
Σεζον-τεστ 2021-22 … 2025-26 (5), LOSO: βαρη μετρημενα μονο στις αλλες σεζον· «δικη μας αξια» (Τ2) επισης LOSO (εκτος σεζον).
Συγκριση: αγορα Crown closing · μοντελο ομαδων · δικη μας + ομαδα · καθε δεικτης + ομαδα · ολοι μαζι.
Εξοδος: nba_metrics_oracle_test_out.txt"""
import sys, re, json, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_oracle_test.py', encoding='utf-8').read().split("RESULTS = {}")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()

def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
A['k'] = A.PLAYER_NAME.map(nk)
A['season_end'] = A.season.str[:4].astype(int) + 1
A['pid'] = A.PLAYER_ID.astype(str)
MP = A.groupby(['pid', 'season_end']).MIN.sum().to_dict()                  # περσινα λεπτα (κανονικη περιοδος)
NAME2PID = A.drop_duplicates('k').set_index('k').pid.to_dict()

# ---- δεικτες: {(pid, season_end): τιμη} ----
M = {}
rows = []
for y in range(2021, 2026):
    t = open(f'bbref_cache/NBA_{y}_advanced.html', encoding='utf-8', errors='ignore').read()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and b and mp: rows.append((nk(nm.group(1)), y, float(b.group(1)), int(mp.group(1))))
br = pd.DataFrame(rows, columns=['k', 'y', 'bpm', 'mp']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
M['BPM'] = {(NAME2PID[k], y): v for k, y, v in zip(br.k, br.y, br.bpm) if k in NAME2PID}
def load(f): return json.load(open(f'nba_rapm/{f}.json', encoding='utf-8'))
M['DARKO'] = {(str(r['nba_id']), int(r['season'])): r['dpm'] for r in load('DARKO') if r.get('dpm') is not None}
M['LEBRON'] = {(str(r['nba_id']), int(r['year'])): r['LEBRON'] for r in load('lebron') if r.get('LEBRON') is not None}
M['MAMBA'] = {(str(r['nba_id']), int(r['year'])): r['MAMBA'] for r in load('mamba') if r.get('MAMBA') is not None}
M['RAPM3Y'] = {(str(r['nba_id']), int(r['Latest_Year'])): r['OVR_RAPM'] for r in load('SCALEDOUTPUT_SMALLER')
               if r['Year_Interval'] == '3Y' and r.get('OVR_RAPM') is not None}

TS = [2022, 2023, 2024, 2025, 2026]
Y = (G.hs - G.as_).values.astype(float)
cov_m = A.season_end.isin(TS).values
FEAT = {}
P('καλυψη λεπτων (σεζον-τεστ) με τιμη περσινης σεζον:')
for nm, D in M.items():
    raw = np.array([D.get((p, s - 1), np.nan) for p, s in zip(A.pid, A.season_end)], dtype=float)
    mp = np.array([MP.get((p, s - 1), 0.0) for p, s in zip(A.pid, A.season_end)])
    v = raw * mp / (mp + 500); known = ~np.isnan(v)
    ZV = np.zeros(len(G)); ZU = np.zeros(len(G))
    np.add.at(ZV, A.gi.values, sign * A.s2.values * np.nan_to_num(v))
    np.add.at(ZU, A.gi.values, sign * A.s2.values * (~known))
    FEAT[nm] = (ZV * PACE / 100, ZU)
    P(f'  {nm:7s} ' + ' · '.join(f'{s}: {np.average(known[cov_m & (A.season_end.values == s)], weights=A.MIN.values[cov_m & (A.season_end.values == s)]):.0%}' for s in TS))

# δικη μας αξια (Τ2), εκτος σεζον: ridge οπως στο nba_oracle_test
pl_ours = np.full(len(G), np.nan)
Axx = np.column_stack([HOMEI, Z2])
for s in TS:
    tr = np.isin(SEAS_G, [t for t in TS if t != s])
    c = np.linalg.lstsq(np.vstack([Axx[tr], np.column_stack([np.zeros(len(F)), np.eye(len(F))])]),
                        np.concatenate([Y100[tr], np.zeros(len(F))]), rcond=None)[0]
    pl_ours[SEAS_G == s] = (Axx @ c)[SEAS_G == s] * PACE / 100

def loso(cols):
    Xm = np.column_stack([HOMEI] + cols); pred = np.full(len(G), np.nan)
    for s in TS:
        tr = np.isin(SEAS_G, [t for t in TS if t != s]); te = SEAS_G == s
        c = np.linalg.lstsq(Xm[tr], Y[tr], rcond=None)[0]; pred[te] = (Xm @ c)[te]
    return pred
V = {'μοντελο ομαδων': loso([team_base]),
     'δικη μας αξια (Τ2) + ομαδα': loso([team_base, pl_ours])}
for nm, (zv, zu) in FEAT.items():
    V[f'{nm} μονο'] = loso([zv, zu])
    V[f'{nm} + ομαδα'] = loso([team_base, zv, zu])
V['ΟΛΟΙ οι δεικτες + ομαδα'] = loso([team_base] + [c for zz in FEAT.values() for c in zz])
V['ΟΛΟΙ + δικη μας + ομαδα'] = loso([team_base, pl_ours] + [c for zz in FEAT.values() for c in zz])

EV = [s for s in TS if s in EVAL]
mm = np.isin(SE, EV)
P('')
P(f'σεζον-τεστ {EV} · ματς με closing {mm.sum()} · ΑΓΟΡΑ Crown RMSE {np.sqrt(np.mean((ACT - MM)[mm] ** 2)):.2f} (' +
  ' '.join(f'{s}:{np.sqrt(np.mean((ACT - MM)[SE == s] ** 2)):.2f}' for s in EV) + ')')
P('')
for nm, m in V.items():
    e = ACT - m[IDX]; b = np.polyfit((m[IDX] - MM)[mm], (ACT - MM)[mm], 1)[0]
    cells = []
    for thr in (0.05, 0.08, 0.10):
        Rr = roi(m, thr, EV); pos = sum(1 for s in EV if len(Rr[Rr.season == s]) and Rr[Rr.season == s].p.mean() > 0)
        cells.append(f'≥{thr*100:.0f}%: {Rr.p.mean()*100:+.1f}% ({len(Rr)}) {pos}/{len(EV)}')
    per = ' '.join(f'{s}:{np.sqrt(np.mean(e[SE == s] ** 2)):.2f}' for s in EV)
    P(f'  {nm:28s} RMSE {np.sqrt(np.mean(e[mm] ** 2)):.2f} ({per}) · b {b:+.3f} | ' + ' | '.join(cells))
open('nba_metrics_oracle_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
