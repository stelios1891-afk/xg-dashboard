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
    # BTTS: ξεχωριστο «ειδικο» ματς (special «Both Teams To Score?», συμμετεχοντες Yes/No) κατω απο το κυριο (parentId)
    btts = {}
    for m in M:
        sp = m.get('special') or {}
        if m.get('parentId') and sp.get('description') == 'Both Teams To Score?':
            pid = {p['id']: p.get('name') for p in (m.get('participants') or [])}
            for x in byid.get(m['id'], []):
                oc = [dict(name=pid.get(p.get('participantId')), price=dec(p.get('price'))) for p in x.get('prices', [])]
                if {o['name'] for o in oc} >= {'Yes', 'No'}:
                    btts[m['parentId']] = (oc, max([l.get('amount', 0) for l in x.get('limits', [])] or [0]))
    out = []; LAD = {}                         # LAD: σκαλα για το αρχειο ΠΑΝΤΑ (ακομα κι οταν include_alt=False)
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
        if m['id'] in btts:
            mk_out.append(dict(key='btts', outcomes=btts[m['id']][0])); limits['btts'] = btts[m['id']][1]
        main_sp = [o for k in mk_out if k['key'] == 'spreads' for o in k['outcomes']]
        main_tot = [o for k in mk_out if k['key'] == 'totals' for o in k['outcomes']]
        LAD[m['id']] = (main_sp + alt_sp, main_tot + alt_tot)
        if include_alt:
            if alt_sp or main_sp: mk_out.append(dict(key='alternate_spreads', outcomes=main_sp + alt_sp))
            if alt_tot or main_tot: mk_out.append(dict(key='alternate_totals', outcomes=main_tot + alt_tot))
        if not mk_out:
            continue
        upd = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        out.append(dict(id=f"pin{m['id']}", pin_id=m['id'], commence_time=m['startTime'], home_team=home, away_team=away,
                        bookmakers=[dict(key='pinnacle', title='Pinnacle', last_update=upd, markets=mk_out, limits=limits)]))
    try:
        archive(league, out, LAD)
    except Exception as e:                     # το αρχειο δεν πρεπει ποτε να ριξει τη σαρωση
        print(f'pin archive σφαλμα ({league}): {e}')
    return out

# ---------------------------------------------------------------------------------------------------------------------
# ΑΡΧΕΙΟ PINNACLE (1/10/2026, Στελιος: «οτι τιμη βαζουμε στο μοντελο απο την αρχη μεχρι το κλεισιμο να μενει αποθηκευμενη»,
# ωστε του χρονου να τρεχουμε οποιο τεστ θελουμε χωρις credits). ΟΛΕΣ οι ροες που περνανε απο εδω (ποδοσφαιρο CORE7/εγχωρια/
# Ευρωπη, Ευρωλιγκα, EuroCup, Βραζιλια). Γραφει ΜΟΝΟ στο GitHub (GITHUB_ACTIONS) ή με PIN_ARCHIVE=1 — οχι στα τοπικα τεστ.
#   pin_archive/YYYY-MM.jsonl:
#     kind 'main'   — καθε ΑΛΛΑΓΗ: κυρια γραμμη χαντικαπ [γραμμη γηπ., τιμη γηπ., τιμη φιλ., οριο] · συνολο [γραμμη, over, under, οριο] ·
#                     νικητης [γηπ., φιλ., (ισοπ.), οριο] · btts [yes, no, οριο]
#     kind 'ladder' — ΟΛΗ η σκαλα (εναλλακτικες γραμμες χαντικαπ [γραμμη γηπ., τιμη γηπ., τιμη φιλ.] & συνολου [γραμμη, over, under]):
#                     καθε 6ω (>24ω πριν), καθε ωρα (2-24ω), καθε 10′ στο τελευταιο 2ωρο, μονο αν αλλαξε κατι (η τελευταια πριν το τζαμπολ = κλεισιμο σκαλας)
#   pin_archive_state.json — τι γραφτηκε τελευταιο ανα ματς (για να γραφονται μονο αλλαγες)
ARCH_DIR = os.path.join(ROOT, 'pin_archive')
ARCH_STATE = os.path.join(ROOT, 'pin_archive_state.json')
def _mk(rec, key):
    for b in rec.get('bookmakers', []):
        for m in b.get('markets', []):
            if m.get('key') == key: return m.get('outcomes', [])
    return []
def archive(league, games, lad_src=None):
    if not (os.environ.get('GITHUB_ACTIONS') or os.environ.get('PIN_ARCHIVE')):
        return
    now = dt.datetime.now(dt.timezone.utc)
    try: st = json.load(open(ARCH_STATE, encoding='utf-8'))
    except Exception: st = {}
    rows = []
    for g in games:
        mid = str(g['pin_id']); home, away = g['home_team'], g['away_team']
        try: hrs = (dt.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00')) - now).total_seconds() / 3600
        except Exception: hrs = 99
        if hrs <= 0: continue                                   # μονο πριν το τζαμπολ/σεντρα
        lim = (g['bookmakers'][0].get('limits') or {})
        sp = _mk(g, 'spreads'); tot = _mk(g, 'totals'); ml = _mk(g, 'h2h'); bt = _mk(g, 'btts')
        main = {}
        h = next((o for o in sp if o['name'] == home), None); a = next((o for o in sp if o['name'] == away), None)
        if h and a: main['sp'] = [h.get('point'), h['price'], a['price'], lim.get('spreads')]
        ov = next((o for o in tot if o['name'] == 'Over'), None); un = next((o for o in tot if o['name'] == 'Under'), None)
        if ov and un: main['tot'] = [ov.get('point'), ov['price'], un['price'], lim.get('totals')]
        if ml:
            d_ = {o['name']: o['price'] for o in ml}
            main['ml'] = [d_.get(home), d_.get(away)] + ([d_['Draw']] if 'Draw' in d_ else []) + [lim.get('h2h')]
        if bt:
            d_ = {o['name']: o['price'] for o in bt}; main['btts'] = [d_.get('Yes'), d_.get('No'), lim.get('btts')]
        if not main: continue
        s0 = st.setdefault(mid, {}); s0['start'] = g['commence_time']
        sig = json.dumps(main, sort_keys=True)
        if s0.get('m') != sig:
            rows.append(dict(t=now.isoformat(timespec='minutes')[:16], kind='main', lg=league, mid=int(mid), start=g['commence_time'],
                             home=home, away=away, **main)); s0['m'] = sig
        if lad_src is not None and g['pin_id'] in lad_src:
            lad_sp, lad_tot = {}, {}
            for o in lad_src[g['pin_id']][0]:
                if o.get('point') is None: continue
                if o['name'] == home: lad_sp.setdefault(float(o['point']), [None, None])[0] = o['price']
                elif o['name'] == away: lad_sp.setdefault(-float(o['point']), [None, None])[1] = o['price']
            for o in lad_src[g['pin_id']][1]:
                if o.get('point') is None: continue
                lad_tot.setdefault(float(o['point']), [None, None])[0 if o['name'] == 'Over' else 1] = o['price']
            lad = dict(sp=sorted([k] + v for k, v in lad_sp.items() if None not in v), tot=sorted([k] + v for k, v in lad_tot.items() if None not in v))
            gap = 10 if hrs <= 2 else (60 if hrs <= 24 else 360)      # >24ω: καθε 6ω · 2-24ω: καθε ωρα · τελευταιο 2ωρο: καθε 10′
            last = s0.get('lt')
            due = not last or (now - dt.datetime.fromisoformat(last)).total_seconds() >= gap * 60 - 30
            lsig = json.dumps(lad)
            if (lad['sp'] or lad['tot']) and due and s0.get('ls') != lsig:
                rows.append(dict(t=now.isoformat(timespec='minutes')[:16], kind='ladder', lg=league, mid=int(mid), start=g['commence_time'],
                                 home=home, away=away, **lad)); s0['ls'] = lsig; s0['lt'] = now.isoformat(timespec='minutes')
    # καθαρισμα state: ματς που ξεκινησαν πριν απο 2+ μερες
    for k in [k for k, v in st.items() if v.get('start', '9') < (now - dt.timedelta(days=2)).isoformat()[:10]]:
        st.pop(k, None)
    if rows:
        os.makedirs(ARCH_DIR, exist_ok=True)
        with open(os.path.join(ARCH_DIR, f'{now:%Y-%m}.jsonl'), 'a', encoding='utf-8') as fh:
            for r in rows: fh.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + chr(10))
    json.dump(st, open(ARCH_STATE, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
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
