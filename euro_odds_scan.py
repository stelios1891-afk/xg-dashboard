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

HOURS_AHEAD = 48     # "συντομα": σεντρα εντος 48 ωρων (καλυπτει ολο το 2ημερο μιας αγωνιστικης)
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
    for m in P.get('matches', []):
        try:
            ko = _pdt(m['utc'])
        except Exception:
            continue
        if m.get('finished'):
            continue
        if -HOURS_BACK * 3600 <= (ko - now).total_seconds() <= HOURS_AHEAD * 3600:
            upc.setdefault(m['comp'], []).append(dict(mid=m['mid'], ko=ko,
                                                      home=m['home'], away=m['away']))
    # prune παλιες εγγραφες
    odds = {k: v for k, v in old.items()
            if v.get('ko') and (now - _pdt(v['ko'])).total_seconds() < PRUNE_H * 3600}
    if not upc:
        print('κανενα ευρωπαϊκο ματς στο παραθυρο — 0 credits')
        json.dump(dict(scanned_at=now.isoformat()[:16], odds=odds, note='no upcoming'),
                  open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
        return

    if not os.environ.get('TOA_KEY'):
        print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — δεν γινεται fetch, το αρχειο μενει ως εχει')
        return
    rem = None; nmatch = 0; unmatched = []
    for comp, fixtures in upc.items():
        sport = SPORT_EU[comp]
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                         params=dict(apiKey=_key(), regions='eu', markets='h2h,spreads',
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
            h2 = _h2h(g); sp = _spread(g)
            rec = dict(ko=best['ko'].isoformat(), when=now.isoformat()[:16])
            if h2:
                rec.update(h=round(h2[0], 2), d=round(h2[1], 2), a=round(h2[2], 2))
            if sp:
                rec.update(line=sp[0], oh=round(sp[1], 2), oa=round(sp[2], 2))
            if h2 or sp:
                odds[best['mid']] = rec; nmatch += 1
        time.sleep(0.3)

    json.dump(dict(scanned_at=now.isoformat()[:16], odds=odds,
                   credits_remaining=rem, unmatched=unmatched[:20]),
              open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'ματς στο παραθυρο: {sum(len(v) for v in upc.values())} · ταιριασαν {nmatch} · '
          f'unmatched {len(unmatched)} · credits left {rem}')
    if unmatched:
        print('  unmatched:', '; '.join(unmatched[:8]))


if __name__ == '__main__':
    main()
