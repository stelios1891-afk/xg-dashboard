# -*- coding: utf-8 -*-
"""ufc_pin_log.py — ΚΑΤΑΓΡΑΦΗ τιμων + οριων Pinnacle για UFC (3/11/2026, Στελιος «στησε την καταγραφη χωρις αλερτς»).

ΜΟΝΟ καταγραφη: κανενα Telegram, κανενα pick. Πηγη: pin_api (guest API, 0 credits), league 1624 (UFC).
Καθε τρεξιμο (ωριαιο, ufc-pin-log.yml) γραφει στο ufc_pin_log.jsonl ΜΟΝΟ οσες αγορες αλλαξαν (version) απο το προηγουμενο:
  {"ts", "mid", "start", "f_home", "f_away", "type" (moneyline/total/...), "key", "points", "status",
   "home"/"away"/"over"/"under" (American), "limit" (maxRiskStake $), "first": true στην 1η εμφανιση = ανοιγμα
   ("first": "pre_existing" = ηταν ηδη ανοιχτη στο 1ο τρεξιμο 3/11, ΟΧΙ πραγματικο ανοιγμα)}
Σκοπος: ποτε ανοιγει η Pinnacle, ορια στο ανοιγμα → κλεισιμο, κινηση vs μοντελο (τεστ 4, ufc/t4_open_realism.py).
Κατασταση: ufc_pin_log_state.json (τελευταιο version ανα αγορα).
"""
import json, os, datetime as dt
import pin_api

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, 'ufc_pin_log.jsonl')
STATE = os.path.join(ROOT, 'ufc_pin_log_state.json')
LEAGUE = 1624


def main():
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        state = json.load(open(STATE, encoding='utf-8'))
        initial = False
    except Exception:
        state, initial = {}, True  # 1ο τρεξιμο: οσα ειναι ηδη ανοιχτα ΔΕΝ ειναι πραγματικο ανοιγμα
    M = pin_api._get(f'/leagues/{LEAGUE}/matchups') or []
    P = pin_api._get(f'/leagues/{LEAGUE}/markets/straight') or []
    info = {}
    for m in M:
        ps = {x.get('alignment'): x.get('name') for x in m.get('participants', [])}
        info[m['id']] = dict(start=m.get('startTime'), f_home=ps.get('home'), f_away=ps.get('away'),
                             type=m.get('type'), parent=m.get('parentId'),
                             special=(m.get('special') or {}).get('description'))
    rows = []
    for x in P:
        k = f"{x['matchupId']}|{x['key']}"
        if state.get(k) == x.get('version'):
            continue
        mi = info.get(x['matchupId'], {})
        r = dict(ts=now, mid=x['matchupId'], start=mi.get('start'), f_home=mi.get('f_home'), f_away=mi.get('f_away'),
                 type=x['type'], key=x['key'], period=x.get('period'), status=x.get('status'),
                 limit=next((l['amount'] for l in x.get('limits', []) if l.get('type') == 'maxRiskStake'), None))
        if mi.get('special'):
            r['special'] = mi['special']
        for pr in x.get('prices', []):
            r[pr.get('designation') or str(pr.get('participantId'))] = pr.get('price')
            if pr.get('points') is not None:
                r['points'] = pr['points']
        if k not in state:
            r['first'] = 'pre_existing' if initial else True
        state[k] = x.get('version')
        rows.append(r)
    if rows:
        with open(LOG, 'a', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    # καθαρισμος καταστασης: κραταμε αγορες αγωνων που υπαρχουν ακομα (προσωρινα κλειστη αγορα ΔΕΝ ξαναμετραει ως ανοιγμα)
    live = {str(i) for i in info}
    state = {k: v for k, v in state.items() if k.split('|')[0] in live}
    json.dump(state, open(STATE, 'w', encoding='utf-8'))
    print(f'{now}: αγωνες {len(M)} · αγορες {len(P)} · νεες/αλλαγμενες εγγραφες {len(rows)}')


if __name__ == '__main__':
    main()
