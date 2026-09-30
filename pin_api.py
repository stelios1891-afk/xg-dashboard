# -*- coding: utf-8 -*-
"""pin_api.py — ΤΙΜΕΣ PINNACLE απο τη δημοσια υπηρεσια της (guest.api.arcadia.pinnacle.com, χωρις λογαριασμο/κλειδι, 0 credits)
ΣΤΗΝ ΙΔΙΑ ΜΟΡΦΗ με το The Odds API (1/10/2026, Στελιος: «περναμε στην Pinnacle, με την προυποθεση οτι αν κατι γινει ξαναπερναμε
στο Odds API αμεσα»).
  • toa_like(league) → λιστα ματς οπως το /v4/sports/{sport}/odds του Odds API (commence_time, home_team, away_team,
    bookmakers=[{key:'pinnacle', markets=[h2h, spreads, totals, alternate_spreads, alternate_totals]}]) — τα υπαρχοντα
    σεναρια δεν αλλαζουν τιποτα αλλο. Επιπλεον πεδια (αγνοουνται απο τον παλιο κωδικα): 'limits' ανα αγορα, 'pin_id'.
  • ΔΙΑΚΟΠΤΗΣ: odds_source.json {"source": "pinnacle" | "toa"} (+ ανα κομματι, π.χ. {"brazil": "toa"}).
    Για επιστροφη στο Odds API: "source": "toa" — μια λεξη. Χωρις αρχειο = "pinnacle".
  • ΕΦΕΔΡΕΙΑ: αν η Pinnacle δεν απαντα / δινει αδεια / σπασμενα δεδομενα → PinError → το σεναριο γυριζει ΜΟΝΟ ΤΟΥ στο Odds API
    για εκεινη τη σαρωση, και fallback_notice() στελνει ΜΙΑ ειδοποιηση ανα 6 ωρες στο info bot.
League ids (Pinnacle): Euroleague 382 · EuroCup 377 · Brazil Serie A 1834 · EPL 1980 · La Liga 2196 · Bundesliga 1842 · Serie A 2436 ·
  Ligue 1 2036 · Eredivisie 1928 · Primeira Liga 2386 · UCL 2627 · UEL 2630 · UECL 214101 · Nations League A 200719 / B 200721 / D 200727."""
import os, json, time, datetime as dt
import requests
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = 'https://guest.api.arcadia.pinnacle.com/0.1'
HEAD = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json',
        'Referer': 'https://www.pinnacle.com/', 'Origin': 'https://www.pinnacle.com'}
LEAGUES = dict(euroleague=382, eurocup=377, brazil=1834, epl=1980, laliga=2196, bundesliga=1842, seriea=2436, ligue1=2036,
               eredivisie=1928, primeira=2386, ucl=2627, uel=2630, uecl=214101, nl_a=200719, nl_b=200721, nl_d=200727)
class PinError(Exception):
    pass
def source(part=None):
    """'pinnacle' ή 'toa' — γενικα ή για ενα κομματι (π.χ. 'brazil', 'euroleague')."""
    try:
        cfg = json.load(open(os.path.join(ROOT, 'odds_source.json'), encoding='utf-8'))
    except Exception:
        return 'pinnacle'
    return str(cfg.get(part) or cfg.get('source') or 'pinnacle').lower() if part else str(cfg.get('source') or 'pinnacle').lower()
def dec(a):
    if a is None: return None
    a = float(a)
    return round(1 + (a / 100.0 if a > 0 else 100.0 / -a), 3)
def _get(path, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(f'{BASE}{path}', headers=HEAD, timeout=25)
            if r.status_code == 200:
                return r.json()
            last = f'HTTP {r.status_code}'
        except Exception as e:
            last = str(e)[:120]
        time.sleep(2 * (i + 1))
    raise PinError(f'{path}: {last}')
def toa_like(league, include_alt=True):
    """Ματς ενος πρωταθληματος της Pinnacle στη μορφη του Odds API. Σηκωνει PinError αν κατι παει στραβα."""
    lid = LEAGUES.get(league, league)
    M = _get(f'/leagues/{lid}/matchups'); MK = _get(f'/leagues/{lid}/markets/straight')
    if not isinstance(M, list) or not isinstance(MK, list):
        raise PinError(f'league {lid}: αγνωστη μορφη')
    byid = {}
    for x in MK:
        if x.get('period') == 0 and x.get('status', 'open') == 'open':
            byid.setdefault(x.get('matchupId'), []).append(x)
    out = []
    for m in M:
        ps = m.get('participants') or []
        if len(ps) != 2 or m.get('parentId') or (m.get('special') is not None):
            continue
        home = next((p['name'] for p in ps if p.get('alignment') == 'home'), ps[0]['name'])
        away = next((p['name'] for p in ps if p.get('alignment') == 'away'), ps[1]['name'])
        mk_out, limits = [], {}
        alt_sp, alt_tot = [], []
        for x in byid.get(m['id'], []):
            pr = {p.get('designation'): p for p in x.get('prices', [])}
            lim = max([l.get('amount', 0) for l in x.get('limits', [])] or [0])
            t, alt = x.get('type'), bool(x.get('isAlternate'))
            if t == 'moneyline' and not alt and 'home' in pr and 'away' in pr:
                oc = [dict(name=home, price=dec(pr['home']['price'])), dict(name=away, price=dec(pr['away']['price']))]
                if 'draw' in pr: oc.append(dict(name='Draw', price=dec(pr['draw']['price'])))
                mk_out.append(dict(key='h2h', outcomes=oc)); limits['h2h'] = lim
            elif t == 'spread' and 'home' in pr and 'away' in pr:
                oc = [dict(name=home, price=dec(pr['home']['price']), point=pr['home'].get('points')),
                      dict(name=away, price=dec(pr['away']['price']), point=pr['away'].get('points'))]
                if alt: alt_sp += oc
                else: mk_out.append(dict(key='spreads', outcomes=oc)); limits['spreads'] = lim
            elif t == 'total' and 'over' in pr and 'under' in pr:
                oc = [dict(name='Over', price=dec(pr['over']['price']), point=pr['over'].get('points')),
                      dict(name='Under', price=dec(pr['under']['price']), point=pr['under'].get('points'))]
                if alt: alt_tot += oc
                else: mk_out.append(dict(key='totals', outcomes=oc)); limits['totals'] = lim
        if include_alt:
            main_sp = [o for k in mk_out if k['key'] == 'spreads' for o in k['outcomes']]
            main_tot = [o for k in mk_out if k['key'] == 'totals' for o in k['outcomes']]
            if alt_sp or main_sp: mk_out.append(dict(key='alternate_spreads', outcomes=main_sp + alt_sp))
            if alt_tot or main_tot: mk_out.append(dict(key='alternate_totals', outcomes=main_tot + alt_tot))
        if not mk_out:
            continue
        upd = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        out.append(dict(id=f"pin{m['id']}", pin_id=m['id'], commence_time=m['startTime'], home_team=home, away_team=away,
                        bookmakers=[dict(key='pinnacle', title='Pinnacle', last_update=upd, markets=mk_out, limits=limits)]))
    return out
def fallback_notice(part, why):
    """ΜΙΑ ειδοποιηση ανα 6 ωρες ανα κομματι οταν η Pinnacle αποτυγχανει και γυριζουμε στο Odds API."""
    fn = os.path.join(ROOT, 'pin_fallback_state.json')
    try: st = json.load(open(fn, encoding='utf-8'))
    except Exception: st = {}
    now = dt.datetime.now(dt.timezone.utc)
    last = st.get(part)
    print(f'PINNACLE ΑΠΕΤΥΧΕ ({part}): {why} → Odds API σε αυτη τη σαρωση')
    if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < 6 * 3600:
        return
    st[part] = now.isoformat(timespec='minutes')
    try: json.dump(st, open(fn, 'w', encoding='utf-8'))
    except Exception: pass
    try:
        import notify
        notify.send(f'⚠️ Pinnacle δεν απαντα ({part}): {why}\nΟ scanner γυρισε αυτοματα στο Odds API (credits). '
                    f'Αν συνεχιστει: odds_source.json → "source": "toa".', channel='info')
    except Exception:
        pass
