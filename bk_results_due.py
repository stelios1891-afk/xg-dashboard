# -*- coding: utf-8 -*-
"""bk_results_due.py — ΑΠΟΤΕΛΕΣΜΑΤΑ ΜΠΑΣΚΕΤ ΑΜΕΣΩΣ ΜΕΤΑ ΤΑ ΜΑΤΣ (3/10/2026, Στελιος: «γιατι δεν ανανεωθηκαν τα picks στο Pick History;»).
Το euro-refresh (el_refresh/ec_refresh) ειναι προγραμματισμενο 06:00 UTC, αλλα το GitHub το ξεκιναει με ~6ω καθυστερηση → τα αποτελεσματα
αργουσαν μισο μερα. Τρεχει σε καθε τικ του scanner: αν καποιο ματς Ευρωλιγκας/EuroCup ξεκινησε πριν απο ≥2.5ω και δεν εχει ακομα σκορ
στο {el,ec}_projections.json → τρεχει το αντιστοιχο refresh (το πολυ 1 φορα / 30′ ανα διοργανωση, ως 18ω μετα το ματς).
State: bk_results_due_state.json"""
import os, sys, json, subprocess, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
ST_F = os.path.join(ROOT, 'bk_results_due_state.json')
GAP_MIN, AFTER_H, GIVEUP_H = 30, 2.5, 18
JOBS = (('el', 'el_projections.json', 'el_refresh.py'), ('ec', 'ec_projections.json', 'ec_refresh.py'))

def main():
    now = dt.datetime.now(dt.timezone.utc)
    try: st = json.load(open(ST_F, encoding='utf-8'))
    except Exception: st = {}
    for key, proj_f, script in JOBS:
        try: P = json.load(open(os.path.join(ROOT, proj_f), encoding='utf-8'))
        except Exception: continue
        due = []
        for g in P.get('games', []):
            if g.get('played'): continue
            try: ko = dt.datetime.fromisoformat(str(g['utc']).replace('Z', '+00:00'))
            except Exception: continue
            h = (now - ko).total_seconds() / 3600
            if AFTER_H <= h <= GIVEUP_H: due.append(f"{g['home']} - {g['away']}")
        if not due:
            print(f'{key}: κανενα ματς σε αναμονη αποτελεσματος'); continue
        last = st.get(key)
        if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < GAP_MIN * 60:
            print(f'{key}: {len(due)} ματς χωρις σκορ · τελευταια προσπαθεια πριν <{GAP_MIN}′ — skip'); continue
        print(f'{key}: {len(due)} ματς χωρις σκορ ({"; ".join(due[:4])}) → {script}', flush=True)
        st[key] = now.isoformat(timespec='minutes')
        try:
            subprocess.run([sys.executable, script], cwd=ROOT, timeout=600, check=False)
        except Exception as e:
            print(f'{key}: {script} σφαλμα: {e}')
    json.dump(st, open(ST_F, 'w', encoding='utf-8'))

if __name__ == '__main__':
    main()
