# -*- coding: utf-8 -*-
"""bb3s_fetch.py — 3StepsBasket (δημοσιο API, χωρις λογαριασμο): ON-COURT στατιστικα παικτων ανα σεζον (9/10/2026, Στελιος «δες τα ολα»).
Για καθε διοργανωση/σεζον: league/{lg}/clubs-full-stats (συνολα ομαδων: ποντοι, κατοχες) + club/{slug}/players-stats (ανα παικτη: ποντοι
ομαδας/αντιπαλου και κατοχες ΟΣΟ ΕΙΝΑΙ ΣΤΟ ΠΑΡΚΕ, usage, ριμπαουντ % κλπ). competitionId euroleague-2018 = σεζον 2017-18 (= δικο μας E2017).
Αργα (1.2″ ανα κληση)· συνεχιζει απο οπου σταματησε. Εξοδος: bb3s_data.json"""
import os, sys, json, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
B = 'https://ycpcq74tr3.execute-api.eu-central-1.amazonaws.com/prod'
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Origin': 'https://3stepsbasket.com'}
OUT = 'bb3s_data.json'
D = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
def J(path):
    for i in range(3):
        try:
            time.sleep(1.2)
            return json.loads(urllib.request.urlopen(urllib.request.Request(B + path, headers=H), timeout=40).read().decode('utf-8'))
        except Exception as e:
            print('  σφαλμα', path, e, flush=True); time.sleep(5 * (i + 1))
    return None
for lg in ('euroleague', 'eurocup'):
    for y in range(2018, 2028):
        cid = f'{lg}-{y}'
        d = D.setdefault(cid, {})
        if not d.get('teams'):
            t = J(f'/league/{lg}/clubs-full-stats?competitionId={cid}')
            d['teams'] = (t or {}).get('teams') or []
        d.setdefault('players', {})
        todo = [t['clubId'] for t in d['teams'] if t['clubId'] not in d['players']]
        print(f'{cid}: ομαδες {len(d["teams"])} · προς fetch {len(todo)}', flush=True)
        for c in todo:
            p = J(f'/club/{c}/players-stats?competitionId={cid}')
            if p is not None: d['players'][c] = p
        json.dump(D, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('ΤΕΛΟΣ:', {k: (len(v.get('teams', [])), sum(len((x or {}).get('players') or []) for x in v.get('players', {}).values())) for k, v in D.items()})
