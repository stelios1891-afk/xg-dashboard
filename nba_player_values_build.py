# -*- coding: utf-8 -*-
"""nba_player_values_build.py — ΑΞΙΕΣ ΠΑΙΚΤΩΝ για τη διορθωση απουσιων NBA (19/10/2026, Στελιος «περνα το live»).
Τρεχει ΤΟΠΙΚΑ (χρειαζεται nba_player_games.csv, nba_rapm/, bbref_cache/) μια φορα τον χρονο → nba_player_values.json (committed, το διαβαζει το cloud).
Ιδιοι ορισμοι με τα τεστ (absence_test.py / od_totals_test.py, scratchpad 19/10):
  συνολικη αξια v = μεσος περσινων DARKO dpm / LEBRON / BPM × λεπτα/(λεπτα+500)   (ιδιο με nba_roster_adj.value· αγνωστοι −1)
  επιθεση o / αμυνα d = μεσος περσινων DARKO o/d_dpm · O/D-LEBRON · OBPM/DBPM × ιδιο μαζεμα   (αγνωστοι −0.5 / −0.5)
Κλειδι = κανονικοποιημενο ονομα (nk, ιδιο με nba_live_roster_util) → [v, o, d]."""
import sys, re, json, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
CUR = 2027                                   # ετος ληξης τρεχουσας σεζον· αξιες απο την CUR−1 (ετησια ενημερωση)
Y = CUR - 1
src = open('nba_roster_adj.py', encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace('for y in range(2020, 2026):', f'for y in range(2020, {CUR}):')
NS = {}; exec(src, NS)
value, nk, NAME2PID, MPT, A = NS['value'], NS['nk'], NS['NAME2PID'], NS['MPT'], NS['A']
OD = collections.defaultdict(lambda: ([], [])); NAMES = collections.defaultdict(set)   # κλειδι (pid, ετος)
# 20/10 (roster_test «INJ»): οποιος ΔΕΝ επαιξε περσι αλλα επαιξε προπερσι (Haliburton, Lillard, Irving …) → αξιες ΠΡΟΠΕΡΣΙΝΕΣ (ηταν −1 = κοστος απουσιας 0)
for r in json.load(open('nba_rapm/DARKO.json', encoding='utf-8')):
    if int(r['season']) in (Y, Y - 1) and r.get('o_dpm') is not None and r.get('d_dpm') is not None:
        p = str(r['nba_id']); yy = int(r['season']); OD[(p, yy)][0].append(r['o_dpm']); OD[(p, yy)][1].append(r['d_dpm']); NAMES[p].add(nk(r['player_name']))
for r in json.load(open('nba_rapm/lebron.json', encoding='utf-8')):
    if int(r['year']) in (Y, Y - 1) and r.get('O-LEBRON') is not None and r.get('D-LEBRON') is not None and r.get('nba_id'):
        p = str(r['nba_id']); yy = int(r['year']); OD[(p, yy)][0].append(r['O-LEBRON']); OD[(p, yy)][1].append(r['D-LEBRON']); NAMES[p].add(nk(r['player_name']))
for yy in (Y, Y - 1):
    t = open(f'bbref_cache/NBA_{yy}_advanced.html', encoding='utf-8', errors='ignore').read(); seen = set()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        o = re.search(r'data-stat="obpm"[^>]*>([-\d.]+)<', tr); d = re.search(r'data-stat="dbpm"[^>]*>([-\d.]+)<', tr)
        if nm and o and d:
            k = nk(nm.group(1))
            if k in NAME2PID and k not in seen:
                seen.add(k); p = NAME2PID[k]; OD[(p, yy)][0].append(float(o.group(1))); OD[(p, yy)][1].append(float(d.group(1))); NAMES[p].add(k)
for p, nmx in A[A.s.isin([Y, Y - 1])][['pid', 'PLAYER_NAME']].drop_duplicates().itertuples(index=False): NAMES[p].add(nk(nmx))
out = {}; ret = []
for p, names in NAMES.items():
    yy = Y - 1 if ((p, Y) not in MPT and (p, Y - 1) in MPT) else Y
    if yy != Y: ret.append(p)
    v = value(p, yy)
    o_, d_ = OD.get((p, yy), ([], []))
    mp = MPT.get((p, yy), 0.0); sh = mp / (mp + 500)
    o = float(np.mean(o_)) * sh if o_ else -0.5; d = float(np.mean(d_)) * sh if d_ else -0.5
    for k in names:
        if k: out[k] = [round(float(v), 3), round(o, 3), round(d, 3)]
json.dump(dict(season=CUR, from_season=Y, built='2026-10-20', note='v=συνολικη, o=επιθεση, d=αμυνα (π./100, μαζεμενα)· αγνωστοι: v −1, o/d −0.5',
               values=out), open('nba_player_values.json', 'w', encoding='utf-8'), ensure_ascii=False)
top = sorted(out.items(), key=lambda kv: -kv[1][0])[:8]
print(f'nba_player_values.json: {len(out)} ονοματα ({len(NAMES)} παικτες, σεζον {Y}, επιστροφες με αξια {Y - 1}: {len(ret)}) · κορυφη: ' + ' · '.join(f'{k} {v[0]:+.1f} (o {v[1]:+.1f} d {v[2]:+.1f})' for k, v in top))
