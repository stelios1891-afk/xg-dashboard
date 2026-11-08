# -*- coding: utf-8 -*-
"""nba_snapshots.py — ΚΑΘΗΜΕΡΙΝΑ ΣΤΙΓΜΙΟΤΥΠΑ φετινων δεικτων παικτη (22/10/2026, Στελιος «αποθηκευε απο σημερα για τα φετινα ματς οτι
ενδεχομενως θα χρειαστουμε»): DARKO και LEBRON οπως ειναι ΣΗΜΕΡΑ (nbarapm.com/load/{DARKO,lebron}) → nba_snap/{darko,lebron}_{ημερα}.json.
Σκοπος: σε μερικους μηνες, ΤΙΜΙΟ τεστ «φρεσκο DARKO/LEBRON vs η μιξη μας» (ιστορικες ημερησιες τιμες δεν υπαρχουν πουθενα).
Κραταει ΜΟΝΟ τη φετινη σεζον· αν δεν εχει βγει ακομα, δεν γραφει τιποτα. Τρεχει απο το nba_refresh.py (euro-refresh, καθημερινα)."""
import os, json, urllib.request, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_snap')
CUR = 2027                                                     # ετησια ενημερωση (ιδιο με nba_refresh.CUR)
SRC = {'darko': ('DARKO', 'season', ('nba_id', 'player_name', 'team_name', 'age', 'dpm', 'o_dpm', 'd_dpm', 'box_odpm', 'box_ddpm', 'on_off_odpm', 'on_off_ddpm')),
       'lebron': ('lebron', 'year', ('nba_id', 'player_name', 'LEBRON', 'O-LEBRON', 'D-LEBRON', 'Minutes'))}
def run():
    os.makedirs(OUT, exist_ok=True); day = dt.datetime.now(dt.timezone.utc).date().isoformat(); msg = []
    for nm, (f, ycol, keep) in SRC.items():
        fn = os.path.join(OUT, f'{nm}_{day}.json')
        if os.path.exists(fn): msg.append(f'{nm} ηδη'); continue
        try:
            req = urllib.request.Request(f'https://www.nbarapm.com/load/{f}', headers={'User-Agent': 'Mozilla/5.0'})
            rows = json.loads(urllib.request.urlopen(req, timeout=90).read().decode('utf-8'))
            cur = [{k: r.get(k) for k in keep} for r in rows if str(r.get(ycol)) == str(CUR)]
            if not cur: msg.append(f'{nm}: φετινη σεζον οχι ακομα (τελευταια {max(str(r.get(ycol)) for r in rows)})'); continue
            json.dump(dict(fetched=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=CUR, rows=cur),
                      open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
            msg.append(f'{nm} {len(cur)} παικτες')
        except Exception as e:
            msg.append(f'{nm} σφαλμα {type(e).__name__}')
    return ' · '.join(msg)
if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8'); print(run())
