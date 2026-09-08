# -*- coding: utf-8 -*-
"""euro_odds_scan.py — Αποδοσεις αγορας (TOA) για τα ευρωπαϊκα ματς του dashboard.

Τρεχει στον scanner (GitHub Actions). GATING: κανει request ΜΟΝΟ αν υπαρχει ματς
UCL/UEL/UECL με σεντρα στις επομενες HOURS_AHEAD ωρες (αλλιως 0 credits).
Κοστος οταν τρεχει: 1 credit ανα διοργανωση με κοντινο ματς (max 3).

Εξοδος: euro_odds_latest.json  {scanned_at, odds: {mid: {h,d,a,line,oh,oa,when,ko}}}
Ταιριασμα TOA→fixtures: παραθυρο ΚΟ ±20' + fuzzy ονοματα (+ ALIAS_EU οποτε φανει block).
"""
import os, sys, json, time, datetime, unicodedata, re
from difflib import SequenceMatcher
import requests

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ_F = os.path.join(ROOT, 'euro_projections.json')
OUT_F = os.path.join(ROOT, 'euro_odds_latest.json')

LIVE_HOURS = 2.5     # in-play καταγραφη σε euro_live_odds.jsonl εως 2.5h μετα το ΚΟ (αιτημα 9/9)
HOURS_AHEAD = 96     # αιτημα Στελιου 9/9: απο ΔΕΥΤΕΡΑ αποδοσεις για ΟΛΗ την ευρωπαικη εβδομαδα
                     # (Τρ+Τετ+Πεμ)· 96h ωστε τα ματς της Πεμπτης να πιανονται απο Δευτερα πρωι.
                     # Κοστος: ~3 credits/scan μονο τις μερες Δευ-Πεμ ευρωπαικων εβδομαδων.
HOURS_BACK = 3       # κρατα και ματς που μολις αρχισαν (για το τελευταιο snapshot)
PRUNE_H = 48         # ποσο κρατιουνται παλιες εγγραφες στο αρχειο

SPORT_EU = {'ChampionsLeague': 'soccer_uefa_champs_league',
            'EuropaLeague': 'soccer_uefa_europa_league',
            'ConferenceLeague': 'soccer_uefa_europa_conference_league'}

# TOA ονομα -> ονομα fixture μας (προσθηκες οποτε δουμε unmatched στην εξοδο)
ALIAS_EU = {'Red Star Belgrade': 'FK Crvena Zvezda', 'FC Copenhagen': 'FC København',
            'Inter Milan': 'Inter', 'AC Milan': 'Milan', 'Sporting Lisbon': 'Sporting CP',
            'Union Saint-Gilloise': 'Union St.Gilloise', 'Paphos': 'Pafos FC',
            'Kairat': 'Kairat Almaty', 'Paris Saint Germain': 'Paris Saint-Germain',
            'Crvena Zvezda': 'FK Crvena Zvezda', 'Zalgiris Kauno': 'FK Kauno Žalgiris',
            'PSV': 'PSV Eindhoven', 'Hearts': 'Heart of Midlothian',
            'Slavia Praha': 'Slavia Prague', 'Sparta Praha': 'Sparta Prague',
            'FC Midtjylland': 'FC Midtjylland', 'Bragantino': 'RB Bragantino'}


def _key():
    k = os.environ.get('TOA_KEY')
    if not k:
        raise RuntimeError('TOA_KEY δεν βρεθηκε στο environment.')
    return k


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(fc|fk|cf|sc|ac|as|sk|ik|bk|if|club|cp|de|the)\b', ' ', s)
    return re.sub(r'[^a-z ]', '', s).strip()


def sim(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    r = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    tok = len(ta & tb) / max(len(ta | tb), 1)
    return max(r, tok)


def _pdt(s):
    return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def _h2h(g, bks=('pinnacle', 'matchbook')):
    ht, at = g.get('home_team'), g.get('away_team')
    for bk in bks:
        for b in g.get('bookmakers', []):
            if b.get('key') != bk:
                continue
            for m in b.get('markets', []):
                if m.get('key') == 'h2h':
                    h = d = a = None
                    for o in m.get('outcomes', []):
                        nm = o.get('name')
                        if nm == ht:
                            h = o.get('price')
                        elif nm == at:
                            a = o.get('price')
                        elif nm and str(nm).lower() == 'draw':
                            d = o.get('price')
                    if h and d and a:
                        return (float(h), float(d), float(a))
    return None


def _total(g, bks=('pinnacle', 'matchbook')):
    """Κυρια γραμμη total -> (line, over_odds, under_odds)."""
    for bk in bks:
        for b in g.get('bookmakers', []):
            if b.get('key') != bk:
                continue
            for m in b.get('markets', []):
                if m.get('key') == 'totals':
                    tl = to = tu = None
                    for o in m.get('outcomes', []):
                        nm = str(o.get('name', '')).lower()
                        if nm == 'over':
                            tl = o.get('point'); to = o.get('price')
                        elif nm == 'under':
                            tu = o.get('price')
                    if tl is not None and to and tu:
                        return (float(tl), float(to), float(tu))
    return None


def _spread(g, bks=('pinnacle', 'matchbook')):
    ht, at = g.get('home_team'), g.get('away_team')
    for bk in bks:
        for b in g.get('bookmakers', []):
            if b.get('key') != bk:
                continue
            for m in b.get('markets', []):
                if m.get('key') == 'spreads':
                    hp = ho = ao = None
                    for o in m.get('outcomes', []):
                        if o.get('name') == ht:
                            hp = o.get('point'); ho = o.get('price')
                        elif o.get('name') == at:
                            ao = o.get('price')
                    if hp is not None and ho and ao:
                        return (float(hp), float(ho), float(ao))
    return None


def _ladders(g, bks=('pinnacle', 'matchbook')):
    """ΟΛΕΣ οι γραμμες (κυριες + alternates) του πρωτου book που εχει: -> (ah, ou)
    ah = sorted [[line, oh, oa]], ou = sorted [[line, over, under]]."""
    ht, at = g.get('home_team'), g.get('away_team')
    for bk in bks:
        ah = {}; ou = {}
        for b in g.get('bookmakers', []):
            if b.get('key') != bk:
                continue
            for m in b.get('markets', []):
                key = m.get('key')
                if key in ('spreads', 'alternate_spreads'):
                    for o in m.get('outcomes', []):
                        pt = o.get('point'); pr = o.get('price')
                        if pt is None or not pr:
                            continue
                        if o.get('name') == ht:
                            ah.setdefault(float(pt), [None, None])[0] = float(pr)
                        elif o.get('name') == at:
                            # το point του away ειναι το αντιθετο της γραμμης του home
                            ah.setdefault(-float(pt), [None, None])[1] = float(pr)
                elif key in ('totals', 'alternate_totals'):
                    for o in m.get('outcomes', []):
                        pt = o.get('point'); pr = o.get('price')
                        if pt is None or not pr:
                            continue
                        nm = str(o.get('name', '')).lower()
                        if nm == 'over':
                            ou.setdefault(float(pt), [None, None])[0] = float(pr)
                        elif nm == 'under':
                            ou.setdefault(float(pt), [None, None])[1] = float(pr)
        ah_l = sorted([ln, round(v[0], 2), round(v[1], 2)] for ln, v in ah.items()
                      if v[0] and v[1])
        ou_l = sorted([ln, round(v[0], 2), round(v[1], 2)] for ln, v in ou.items()
                      if v[0] and v[1])
        if ah_l or ou_l:
            return ah_l, ou_l
    return [], []


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        P = json.load(open(PROJ_F, encoding='utf-8'))
    except Exception as e:
        print(f'χωρις euro_projections.json ({e}) — τιποτα να κανω')
        return
    # φορτωσε υπαρχον αρχειο (κραταμε προσφατες εγγραφες μεταξυ scans)
    old = {}
    try:
        old = json.load(open(OUT_F, encoding='utf-8')).get('odds', {})
    except Exception:
        pass
    upc = {}
    livefx = {}      # ματς ΣΕ ΕΞΕΛΙΞΗ (εως LIVE_HOURS μετα το ΚΟ): καταγραφη in-play σε ΧΩΡΙΣΤΟ αρχειο
    for m in P.get('matches', []):
        try:
            ko = _pdt(m['utc'])
        except Exception:
            continue
        if m.get('finished'):
            continue
        dt_s = (ko - now).total_seconds()
        # ΜΟΝΟ ματς που ΔΕΝ εχουν σεντραρει μπαινουν στο κυριο αρχειο: μετα το ΚΟ η εγγραφη
        # παγωνει στην τελευταια προ-ΚΟ τιμη (= το «κλεισιμο» μας).
        if 0 <= dt_s <= HOURS_AHEAD * 3600:
            upc.setdefault(m['comp'], []).append(dict(mid=m['mid'], ko=ko,
                                                      home=m['home'], away=m['away']))
        elif -LIVE_HOURS * 3600 <= dt_s < 0:
            livefx.setdefault(m['comp'], []).append(dict(mid=m['mid'], ko=ko,
                                                         home=m['home'], away=m['away']))
    # prune παλιες εγγραφες
    odds = {k: v for k, v in old.items()
            if v.get('ko') and (now - _pdt(v['ko'])).total_seconds() < PRUNE_H * 3600}
    if not upc and not livefx:
        print('κανενα ευρωπαϊκο ματς στο παραθυρο — 0 credits')
        json.dump(dict(scanned_at=now.isoformat()[:16], odds=odds, note='no upcoming'),
                  open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
        return

    # gating συχνοτητας (κοστος 5 markets/comp πλεον): μακρια απο σεντρα φτανει ~45λεπτο refresh·
    # μεσα στο 6ωρο προ ΚΟ γυρναμε σε καθε scan (κλεισιμο γραμμων)
    try:
        last = json.load(open(OUT_F, encoding='utf-8')).get('scanned_at')
        age_min = (now - _pdt(last + ':00+00:00' if len(str(last)) == 16 else last)).total_seconds() / 60
    except Exception:
        age_min = 1e9
    nearest_h = min([(f['ko'] - now).total_seconds() / 3600
                     for fs in upc.values() for f in fs] or [1e9])
    has_lad = (not odds) or any('ah' in v for v in odds.values())
    if age_min < 45 and nearest_h > 6 and has_lad and not livefx:
        print(f'φρεσκο αρχειο ({age_min:.0f}λ) και κοντινοτερο ΚΟ σε {nearest_h:.1f}h — skip (0 credits)')
        return
    if not os.environ.get('TOA_KEY'):
        print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — δεν γινεται fetch, το αρχειο μενει ως εχει')
        return
    rem = None; nmatch = 0; unmatched = []
    live_rows = []
    comps_all = sorted(set(upc) | set(livefx))
    for comp in comps_all:
        fixtures = upc.get(comp, [])
        sport = SPORT_EU[comp]
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                         params=dict(apiKey=_key(), regions='eu', markets='h2h,spreads,totals',
                                     bookmakers='pinnacle,matchbook', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        if r.status_code != 200:
            print(f'{comp}: TOA {r.status_code} — skip')
            continue
        for g in r.json():
            try:
                gko = _pdt(g.get('commence_time'))
            except Exception:
                continue
            ht = ALIAS_EU.get(g.get('home_team'), g.get('home_team'))
            at = ALIAS_EU.get(g.get('away_team'), g.get('away_team'))
            # --- LIVE ματς: καταγραφη σε χωριστο append-only αρχειο, ΟΧΙ στο κυριο ---
            lcands = [f for f in livefx.get(comp, [])
                      if abs((f['ko'] - gko).total_seconds()) <= 1200]
            lbest = None; lbs = 0.0
            for f in lcands:
                s = sim(ht, f['home']) + sim(at, f['away'])
                if s > lbs:
                    lbs, lbest = s, f
            if lbest is not None and lbs >= 1.1:
                h2 = _h2h(g); sp = _spread(g); tt = _total(g)
                lr = dict(t=now.isoformat()[:16], mid=lbest['mid'],
                          min_ko=round((now - lbest['ko']).total_seconds() / 60))
                if h2:
                    lr.update(h=round(h2[0], 2), d=round(h2[1], 2), a=round(h2[2], 2))
                if sp:
                    lr.update(line=sp[0], oh=round(sp[1], 2), oa=round(sp[2], 2))
                if tt:
                    lr.update(tl=tt[0], to=round(tt[1], 2), tu=round(tt[2], 2))
                if h2 or sp or tt:
                    live_rows.append(lr)
                continue
            cands = [f for f in fixtures if abs((f['ko'] - gko).total_seconds()) <= 1200]
            best = None; bs = 0.0
            for f in cands:
                s = sim(ht, f['home']) + sim(at, f['away'])
                if s > bs:
                    bs, best = s, f
            if best is None or bs < 1.1:      # ~0.55 μεσος ορος ανα πλευρα
                if cands:                     # TOA event εκτος παραθυρου μας = οχι πραγματικο mismatch
                    unmatched.append(f"{g.get('home_team')} vs {g.get('away_team')} ({bs:.2f})")
                continue
            h2 = _h2h(g); sp = _spread(g); tt = _total(g)
            old_rec = odds.get(best['mid']) or {}
            rec = dict(ko=best['ko'].isoformat(), when=now.isoformat()[:16],
                       eid=g.get('id'), sport=sport)
            # κρατα τις σκαλες του προηγουμενου scan (ανανεωνονται με δικο τους ρυθμο)
            for k in ('ah', 'ou', 'alt_when'):
                if k in old_rec:
                    rec[k] = old_rec[k]
            if h2:
                rec.update(h=round(h2[0], 2), d=round(h2[1], 2), a=round(h2[2], 2))
            if sp:
                rec.update(line=sp[0], oh=round(sp[1], 2), oa=round(sp[2], 2))
            if tt:
                rec.update(tl=tt[0], to=round(tt[1], 2), tu=round(tt[2], 2))
            if h2 or sp or tt:
                odds[best['mid']] = rec; nmatch += 1
        time.sleep(0.3)

    # ---- ΣΚΑΛΕΣ (alternate lines): per-event endpoint του TOA, με δικο τους ρυθμο ----
    ALT_REFRESH_MIN = 120     # μακρια απο ΚΟ: ανανεωση ανα 2ωρο (2 credits/ματς)
    ALT_NEAR_MIN = 30         # <3h προ ΚΟ: ανα 30'
    n_alt = 0
    for mid, rec in odds.items():
        eid, sport = rec.get('eid'), rec.get('sport')
        if not eid or not sport:
            continue
        try:
            ko = _pdt(rec['ko']); h_to_ko = (ko - now).total_seconds() / 3600
        except Exception:
            continue
        if h_to_ko < -HOURS_BACK:
            continue
        try:
            aw = _pdt(rec['alt_when'] + ':00+00:00' if len(str(rec.get('alt_when', ''))) == 16
                      else rec['alt_when'])
            age = (now - aw).total_seconds() / 60
        except Exception:
            age = 1e9
        need = age > (ALT_NEAR_MIN if 0 <= h_to_ko <= 3 else ALT_REFRESH_MIN)
        if not need:
            continue
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/events/{eid}/odds',
                         params=dict(apiKey=_key(), regions='eu',
                                     markets='alternate_spreads,alternate_totals',
                                     bookmakers='pinnacle,matchbook', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        if r.status_code != 200:
            continue
        ahl, oul = _ladders(r.json())
        # σιγουρεψε οτι η ΚΥΡΙΑ γραμμη υπαρχει στη σκαλα
        if rec.get('line') is not None and not any(abs(x[0] - rec['line']) < 0.01 for x in ahl):
            ahl = sorted(ahl + [[rec['line'], rec.get('oh'), rec.get('oa')]])
        if rec.get('tl') is not None and not any(abs(x[0] - rec['tl']) < 0.01 for x in oul):
            oul = sorted(oul + [[rec['tl'], rec.get('to'), rec.get('tu')]])
        if ahl:
            rec['ah'] = ahl
        if oul:
            rec['ou'] = oul
        rec['alt_when'] = now.isoformat()[:16]
        n_alt += 1
        time.sleep(0.2)

    json.dump(dict(scanned_at=now.isoformat()[:16], odds=odds,
                   credits_remaining=rem, unmatched=unmatched[:20]),
              open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'σκαλες: ανανεωθηκαν {n_alt} ματς (per-event alternates)')
    if live_rows:
        with open(os.path.join(os.path.dirname(OUT_F), 'euro_live_odds.jsonl'),
                  'a', encoding='utf-8') as lf:
            for lr in live_rows:
                lf.write(json.dumps(lr, ensure_ascii=False) + '\n')
        print(f'live καταγραφη: {len(live_rows)} γραμμες (in-play, χωριστο αρχειο)')
    print(f'ματς στο παραθυρο: {sum(len(v) for v in upc.values())} · ταιριασαν {nmatch} · '
          f'unmatched {len(unmatched)} · credits left {rem}')
    if unmatched:
        print('  unmatched:', '; '.join(unmatched[:8]))


if __name__ == '__main__':
    main()
