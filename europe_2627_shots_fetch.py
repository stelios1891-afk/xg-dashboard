# -*- coding: utf-8 -*-
"""
europe_2627_shots_fetch.py — 9/10/2026: xG ανα σουτ για τα ΦΕΤΙΝΑ ευρωπαικα (UCL/UEL/UECL 2627) → data_Europe_2627.json.
Ιδια μορφη εγγραφης με europe_shots_fetch.py / dl.parse (πεδιο 'comp'). Πηγη ματς: europe_fixtures_2627.json (finished).
Κατεβαζει οσα λειπουν + ΞΑΝΑ-ελεγχος των ματς των τελευταιων 4 ημερων (η Opta αναθεωρει xG) + οσα δεν ειχαν σουτ.
Τρεχει στο euro-refresh μετα το europe_fixtures_2627_fetch.py, πριν τα projections (φετινα ευρωπαικα στο rating, Μ8 w=0.5).
"""
import sys, os, json, time
from datetime import datetime, timezone, timedelta
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl import parse

FX = 'europe_fixtures_2627.json'
OUT = 'data_Europe_2627.json'
RECHECK_DAYS = 4
fx = json.load(open(FX, encoding='utf-8'))
store = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
now = datetime.now(timezone.utc)
todo = []
for key, rows in fx.items():
    comp = key.rsplit('_', 1)[0]
    for m in rows:
        if not m.get('finished'):
            continue
        try:
            ko = datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
        except Exception:
            ko = now
        have = store.get(m['mid'])
        if have is None or not have.get('shots') or (now - ko) <= timedelta(days=RECHECK_DAYS):
            todo.append((m['mid'], comp))
print(f'data_Europe_2627: εχει {len(store)} · για κατεβασμα/ελεγχο {len(todo)}')
ok = 0
for mid, comp in todo:
    rec = None
    for i in range(3):
        try:
            rec = parse(mid); break
        except Exception as e:
            time.sleep(1.0 * (i + 1))
    if rec:
        rec['comp'] = comp
        store[mid] = rec; ok += 1
    time.sleep(0.4)
json.dump(store, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'ΟΚ {ok}/{len(todo)} · συνολο {len(store)} · με σουτ {sum(1 for v in store.values() if v.get("shots"))}')
