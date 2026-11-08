# -*- coding: utf-8 -*-
"""nba_pbpstats_fetch.py — pbpstats.com API: ανα ματς στατιστικα ΟΜΑΔΑΣ (Team) και ΤΙ ΑΦΗΣΕ ΣΤΟΝ ΑΝΤΙΠΑΛΟ (Opponent), 2021-22 → τρεχουσα.
Ζωνες σουτ (AtRim / ShortMid / LongMid / Corner3 / Arc3), βολες, ριμπαουντ, Pace, ShotQualityAvg. Δωρεαν, χωρις κλειδι.
Εξοδος: nba_pbpstats/{season}_{Team|Opponent}_{ABBR}.json (ενα αρχειο ανα ομαδα-σεζον). Τρεχει ξανα → κατεβαζει μονο οσα λειπουν
(η τρεχουσα σεζον ξανακατεβαινει παντα). Χρηση: python nba_pbpstats_fetch.py [σεζον ...]"""
import os, sys, json, time, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_pbpstats'); os.makedirs(OUT, exist_ok=True)
API = 'https://api.pbpstats.com'
FIX = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}   # pbpstats → δικοι μας κωδικοι (G / _t35)
CUR = '2026-27'
def get(u):
    for k in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40)
            return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            print('  retry', k, e, flush=True); time.sleep(5 * (k + 1))
    return None
seasons = sys.argv[1:] or ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', CUR]
teams = get(f'{API}/get-teams/nba')['teams']
for s in seasons:
    for t in teams:
        ab = FIX.get(t['text'], t['text'])
        for et in ('Team', 'Opponent'):
            fn = os.path.join(OUT, f'{s}_{et}_{ab}.json')
            if os.path.exists(fn) and s != CUR: continue
            d = get(f"{API}/get-game-logs/nba?Season={s}&SeasonType=Regular%20Season&EntityId={t['id']}&EntityType={et}")
            if not d: print('FAIL', s, ab, et, flush=True); continue
            json.dump(d.get('multi_row_table_data', []), open(fn, 'w', encoding='utf-8'))
            time.sleep(1.0)
        print(s, ab, 'ok', flush=True)
print('DONE')
