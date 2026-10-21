# -*- coding: utf-8 -*-
"""el_pir_prev_build.py — PIR ΠΡΟΗΓΟΥΜΕΝΩΝ ΣΕΖΟΝ για την αξια απουσιας (22/10/2026, Στελιος «περνα το»: el_absence V1 = λεπτα + PIR).
Απο el_players.json (επισημο API, Ευρωλιγκα): για καθε παικτη τα τελευταια 60 ματς που επαιξε (λεπτα, PIR) ΠΡΙΝ την τρεχουσα σεζον.
Το live (el_absence.team_cost) τα ενωνει με τα φετινα (el_box.json, PIR απο το backfill) → τελευταια 60 → PIR/40 μαζεμενο (+200′).
Εξοδος: el_player_pir_prev.json  {season_before, players: {pid: {name, g: [[λεπτα, PIR], ...] (παλιο → νεο)}}}
Χρηση: python el_pir_prev_build.py [ΣΕΖΟΝ_ΠΡΙΝ]  (προεπιλογη: η μεγαλυτερη σεζον του el_players.json) — μια φορα το χρονο."""
import sys, json, collections
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
PL = json.load(open('el_players.json', encoding='utf-8'))
last = sys.argv[1] if len(sys.argv) > 1 else max(g['season'] for g in PL.values() if g.get('comp') == 'E')
H = collections.defaultdict(list); NM = {}
for g in PL.values():
    if g.get('comp') != 'E' or g.get('season', '') > last or 'ph' not in g or 'pa' not in g: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side in ('ph', 'pa'):
        for p in g[side]:
            if (p[3] or 0) > 0: H[p[0]].append((ts, round(float(p[3]), 1), int(p[18] or 0))); NM[p[0]] = p[1]
out = {pid: dict(name=NM[pid], g=[[m, v] for _, m, v in sorted(h)[-60:]]) for pid, h in H.items()}
json.dump(dict(season_before=last, players=out), open('el_player_pir_prev.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'παικτες {len(out)} · ως και {last}')
