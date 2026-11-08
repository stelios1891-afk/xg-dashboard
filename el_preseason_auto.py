# -*- coding: utf-8 -*-
"""el_preseason_auto.py — ΑΥΤΟΜΑΤΗ ΠΡΟΕΤΟΙΜΑΣΙΑ καθε σεζον (1/10/2026, Στελιος «τρεξε το 5»). Τρεχει στο euro-refresh ΠΡΙΝ το el_refresh.
Παραθυρο 1 Σεπτ. – 31 Οκτ.· σταματα μολις το el_preseason_prior.json της σεζον ειναι «τελικο» (φτιαχτηκε ≥2 μερες μετα την πρεμιερα,
  οποτε εχουν αντιστοιχιστει και οι νεες ομαδες). Βηματα (Flashscore, ευγενικα):
  1. flashscore_bk_preseason.py --current  (φιλικα & Super Cups φετος)
  2. flashscore_bk_domestic.py --current   (περσινη σεζον αν ειναι ελλιπης + φετινη EL για την αντιστοιχιση· χωρις στατιστικα)
  3. el_preseason_prior.py                 (αποδοση προετοιμασιας χαντικαπ κ .5 & ταση ποντων συνολων κ .25)
Επισης: μια φορα ανα σεζον ενημερωση στο info bot αν λειπουν τα ΧΕΙΡΟΚΙΝΗΤΑ της νεας σεζον (ειδικοι el_expert_prior.json, νεες ομαδες).
Χρηση: python el_preseason_auto.py [--force]"""
import sys, os, json, subprocess, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
from el_season import Y, SEASON
today = dt.datetime.now(dt.timezone.utc).date()
FORCE = '--force' in sys.argv
def first_game():
    try:
        S = json.load(open('el_sched.json', encoding='utf-8')).get(SEASON, [])
        return min(dt.date.fromisoformat(x['utc'][:10]) for x in S) if S else None
    except Exception:
        return None
def warn_once():
    WF = 'el_season_warned.txt'
    try: done = open(WF, encoding='utf-8').read().split()
    except FileNotFoundError: done = []
    if SEASON in done: return
    miss = []
    try:
        if json.load(open('el_expert_prior.json', encoding='utf-8')).get('season') != SEASON: miss.append('ειδικοι (el_expert_prior.json, BasketNews)')
    except Exception:
        miss.append('ειδικοι (el_expert_prior.json λειπει)')
    msg = (f'🏀 Νεα σεζον Ευρωλιγκας {SEASON}: η προετοιμασια ενημερωνεται αυτοματα (φιλικα/Super Cups ως την πρεμιερα).'
           + (f'\nΧΡΕΙΑΖΕΤΑΙ χειροκινητα: {", ".join(miss)} · νεες ομαδες κατω απο τη μεση (NEWCOMER_PRIOR στο el_refresh.py).' if miss else
              '\nΘυμησου: νεες ομαδες κατω απο τη μεση (NEWCOMER_PRIOR στο el_refresh.py).'))
    print(msg)
    try:
        import notify; notify.send(msg, channel='info')
    except Exception as e:
        print('Telegram:', e)
    open(WF, 'w', encoding='utf-8').write(' '.join(done + [SEASON]))
def main():
    if not FORCE and not (dt.date(today.year, 9, 1) <= today <= dt.date(today.year, 10, 31)):
        print(f'προετοιμασια: εκτος παραθυρου (1/9-31/10) — τιποτα'); return
    fg = first_game()
    try: pp = json.load(open('el_preseason_prior.json', encoding='utf-8'))
    except Exception: pp = {}
    if not FORCE and pp.get('season') == SEASON and fg and dt.date.fromisoformat(pp.get('generated', '1900-01-01')[:10]) >= fg + dt.timedelta(days=2):
        print(f'προετοιμασια {SEASON}: τελικη (φτιαχτηκε {pp["generated"][:10]}, πρεμιερα {fg}) — τιποτα'); return
    warn_once()
    for cmd in (['flashscore_bk_preseason.py', '--current'], ['flashscore_bk_domestic.py', '--current'], ['el_preseason_prior.py', str(Y)]):
        print('▶', ' '.join(cmd), flush=True)
        r = subprocess.run([sys.executable] + cmd, timeout=3000)
        if r.returncode != 0:
            print(f'ΣΦΑΛΜΑ στο {cmd[0]} (κωδικος {r.returncode}) — σταματω, μενει το προηγουμενο el_preseason_prior.json'); return
if __name__ == '__main__':
    main()
