# -*- coding: utf-8 -*-
"""nba_live_roster_util.py — ΝΕΕΣ ΑΠΟΥΣΙΕΣ ανα ομαδα για το φιλτρο picks NBA (6/10/2026, Στελιος «οι απουσιες ειναι και για να αποφυγουμε κακα μπετς»).
Ιδιος ορισμος με το nba_more_tests (Τ8): παικτης με μεσο ≥20′ (10 τελευταια φετινα ματς· αλλιως περσινος μεσος, nba_mpg_prev.json) που επαιξε
σε 1 απο τα 3 τελευταια ματς της ομαδας (προετοιμασια μετραει· με <3 ματς ολοι μετρανε) και ειναι Out / Doubtful στη λιστα ESPN (nba_injuries.json)."""
import json, re, unicodedata, collections
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
def absence_minutes(teams, min_player=20.0, statuses=('out', 'doubtful')):
    INJ = json.load(open('nba_injuries.json', encoding='utf-8'))
    GM = json.load(open('nba_espn_games.json', encoding='utf-8'))
    PREV = json.load(open('nba_mpg_prev.json', encoding='utf-8'))['mpg']
    hist = collections.defaultdict(list); tg = collections.defaultdict(list)
    for g in sorted(GM.values(), key=lambda g: g['utc']):
        for t in (g['home'], g['away']):
            pl = {nk(n): mn for _, n, mn in g['players'].get(t, [])}
            tg[t].append(pl)
            if g['stype'] == 2:
                for k, mn in pl.items():
                    if mn > 0: hist[k].append(mn)
    out = {}
    for t in teams:
        inj = [nk(n) for v in INJ['teams'].values() if v.get('code') == t for n, stt, _ in v['players'] if str(stt or '').lower() in statuses]
        last3 = tg.get(t, [])[-3:]
        tot = 0.0
        for k in inj:
            rec = hist.get(k, [])[-10:]
            avg = sum(rec) / len(rec) if rec else PREV.get(k, 0.0)
            recent = len(last3) < 3 or any(pl.get(k, 0) > 0 for pl in last3)
            if avg >= min_player and recent: tot += avg
        out[t] = round(tot, 1)
    return out
if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    from nba_espn import TEAMNAME
    r = absence_minutes(sorted(set(TEAMNAME.values())))
    print('νεες απουσιες (λεπτα): ' + ' · '.join(f'{t} {v:.0f}' for t, v in sorted(r.items(), key=lambda kv: -kv[1]) if v > 0))
