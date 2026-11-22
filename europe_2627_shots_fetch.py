# -*- coding: utf-8 -*-
"""
europe_2627_shots_fetch.py — 9/10/2026: xG ανα σουτ για τα ΦΕΤΙΝΑ ευρωπαικα (UCL/UEL/UECL 2627) → data_Europe_2627.json.
Ιδια μορφη εγγραφης με europe_shots_fetch.py / dl.parse (πεδιο 'comp'). Πηγη ματς: europe_fixtures_2627.json (finished).
Κατεβαζει οσα λειπουν (16/10: και οσα η σεντρα περασε ≥2.5ω, ακομα κι αν το προγραμμα δεν τα εχει «finished») + ΞΑΝΑ-ελεγχος των ματς των τελευταιων 4 ημερων (η Opta αναθεωρει xG) + οσα δεν ειχαν σουτ.
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
        try:
            ko = datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
        except Exception:
            ko = now
        # 16/10/2026: ΚΑΙ ματς που δεν ειναι «finished» στο προγραμμα αλλα η σεντρα περασε ≥2.5ω — το europe_fixtures_2627_fetch
        # δεν ανανεωνε το αρχειο στο cloud απο 26/9 → τα φετινα ευρωπαικα (UCL 2η, UEL 2η, UECL 1η) δεν εμπαιναν στο rating.
        # Το matchDetails (dl.parse) δουλευει στο cloud· κραταμε μονο οσα γυρισουν με σκορ + σουτ.
        if not m.get('finished') and (now - ko) < timedelta(hours=2.5):
            continue
        have = store.get(m['mid'])
        if have is not None and have.get('shots') and have.get('hs') is not None and (now - ko) > timedelta(days=RECHECK_DAYS):
            continue
        todo.append((m['mid'], comp, m))
print(f'data_Europe_2627: εχει {len(store)} · για κατεβασμα/ελεγχο {len(todo)}')
ok = fxu = 0
for mid, comp, m in todo:
    rec = None
    for i in range(3):
        try:
            rec = parse(mid); break
        except Exception as e:
            time.sleep(1.0 * (i + 1))
    if rec and rec.get('hs') is not None and rec.get('as') is not None and rec.get('shots'):
        rec['comp'] = comp
        store[mid] = rec; ok += 1
        if not m.get('finished'):                     # 16/10: και το προγραμμα (σκορ στο dashboard) αν δεν το ειχε
            m['finished'] = True; m['score'] = f"{rec['hs']} - {rec['as']}"; fxu += 1
    time.sleep(0.4)
json.dump(store, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
if fxu:
    json.dump(fx, open(FX, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'προγραμμα: {fxu} ματς σημειωθηκαν τελειωμενα απο το matchDetails')
print(f'ΟΚ {ok}/{len(todo)} · συνολο {len(store)} · με σουτ {sum(1 for v in store.values() if v.get("shots"))}')
