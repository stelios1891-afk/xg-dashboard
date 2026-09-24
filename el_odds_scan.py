# -*- coding: utf-8 -*-
"""el_odds_scan.py — Αποδοσεις αγορας (TOA) για την Ευρωλιγκα (σελιδα 🏀 Euroleague του dashboard).

Τρεχει στον scanner (GitHub Actions, scanner_tick.sh). ΕΝΑ bulk request:
  /v4/sports/basketball_euroleague/odds?regions=eu&markets=h2h,spreads,totals  = 3 credits
(ολα τα επερχομενα ματς, ~12-27 βιβλια μαζι με Pinnacle).

GATING (για να μην καιγονται credits):
  * request ΜΟΝΟ αν καποιο ματς του el_projections.json (fallback el_sched.json) ξεκινα μεσα σε 48h
  * το πολυ 1 request / 60' — αλλα 1 / 15' οταν καποιο ματς ξεκινα μεσα σε 2h (για το «κλεισιμο»)
  * αλλιως 0 credits (τυπωνει γιατι). Χωρις TOA_KEY (τοπικα) -> βγαινει ησυχα, 0 credits.
  * ΚΑΜΙΑ ημερομηνιακη παυση εδω: η παυση TOA του ποδοσφαιρου (ως 6/10) ΔΕΝ αφορα το μπασκετ.
  * EL_FORCE=1 -> παρακαμπτει το χρονικο gating (οχι το 48ωρο παραθυρο).

Εξοδος:
  el_odds_latest.json  {scanned_at, season, credits_remaining, unmatched, odds: {code: rec}}
     rec = {code, round, hcode, acode, home, away, commence, when, toa_id, toa_home, toa_away, swapped,
            pin:  {line, oh, oa, tl, to, tu, mh, ma}      Pinnacle (γραμμη ΓΗΠΕΔΟΥΧΟΥ μας, π.χ. -2.5 = δινει 2.5)
            cons: {line, tl, n_sp, n_tot}                 διαμεσος γραμμων ολων των βιβλιων
            best: {line, oh, oh_bk, oa, oa_bk, tl, to, to_bk, tu, tu_bk, mh, mh_bk, ma, ma_bk}
                  καλυτερη τιμη σε ΟΛΑ τα βιβλια, στη γραμμη αναφορας (Pinnacle, αλλιως διαμεσος)}
     Μετα το τζαμπολ η εγγραφη ΠΑΓΩΝΕΙ (= κλεισιμο)· κρατιεται 48h.
  el_odds_hist.jsonl   append-on-change διαδρομη γραμμων: {t, code, commence, line, oh, oa, tl, to, tu, mh, ma (Pinnacle),
                       cl, ctl (διαμεσος), bl, boh, boa, btl, bto, btu, bmh, bma (καλυτερες τιμες)}.
                       Η τελευταια γραμμη με t < commence = το «κλεισιμο» (το διαβαζει το dashboard για παιγμενα).
Ταιριασμα TOA -> προγραμμα μας: ωρα ±30' + κοινες «ουσιαστικες» λεξεις ονοματος
(τα ονοματα διαφερουν: "Olympiacos" vs "Olympiacos Piraeus", "KK Crvena zvezda" vs
"Crvena Zvezda Meridianbet Belgrade"...)· οι αποδοσεις αντιστοιχιζονται με ΑΚΡΙΒΕΣ ονομα outcome
== home_team/away_team του TOA.
"""
import os, sys, json, datetime, unicodedata, re, statistics

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:      # το dashboard το κανει import (parse του toa_el_now.json)
    pass
ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ_F = os.path.join(ROOT, 'el_projections.json')
SCHED_F = os.path.join(ROOT, 'el_sched.json')
OUT_F = os.path.join(ROOT, 'el_odds_latest.json')
HIST_F = os.path.join(ROOT, 'el_odds_hist.jsonl')

SPORT = 'basketball_euroleague'
WINDOW_H = 48        # request μονο αν καποιο ματς ξεκινα μεσα σε 48h
MIN_GAP_MIN = 60     # μακρια απο τζαμπολ: το πολυ 1 request / ωρα
NEAR_H = 2           # ... αλλα μεσα στο 2ωρο πριν απο τζαμπολ:
NEAR_GAP_MIN = 15    #     1 request / 15'
MATCH_MIN = 30       # παραθυρο ωρας για ταιριασμα TOA <-> προγραμμα
PRUNE_H = 48         # ποσο κρατιουνται οι εγγραφες μετα το τζαμπολ
FORCE = os.environ.get('EL_FORCE') == '1'

# λεξεις που ΔΕΝ ξεχωριζουν ομαδα (κοινες σε πολλες: πολεις, «KK», «Basketball»...)
GENERIC = {'kk', 'bc', 'fc', 'sk', 'jk', 'as', 'cb', 'bk', 'pbc', 'sad', 'club', 'the', 'de',
           'basket', 'basketball', 'basquet', 'pallacanestro', 'istanbul', 'belgrade', 'tel', 'aviv',
           'athens', 'piraeus', 'kaunas', 'lyon', 'vitoria', 'gasteiz'}
# TOA ονομα -> ονομα μας (μονο οπου οι λεξεις δεν αρκουν· προσθηκες οταν φανει unmatched)
ALIAS = {}


def _pdt(s):
    s = str(s)
    if len(s) == 16:
        s += ':00+00:00'
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))


def _tokens(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = s.replace('.', '')
    s = re.sub(r'[^a-z ]', ' ', s)
    return {t for t in s.split() if t and t not in GENERIC}


def _tok_match(a, b):
    return a == b or (len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5])   # milan~milano


def name_score(toa_name, our_name):
    ta, tb = _tokens(ALIAS.get(toa_name, toa_name)), _tokens(our_name)
    return sum(1 for x in ta if any(_tok_match(x, y) for y in tb))


def our_games(now):
    """Επερχομενα ματς μας [{code, round, utc(dt), hcode, acode, home, away}] + season."""
    try:
        P = json.load(open(PROJ_F, encoding='utf-8'))
        season = P.get('season')
        gs = [dict(code=g['code'], round=g.get('round'), utc=_pdt(g['utc']), hcode=g['hcode'],
                   acode=g['acode'], home=g['home'], away=g['away']) for g in P.get('games', [])
              if not g.get('played')]      # 25/9: το json εχει πλεον ΟΛΗ τη σεζον (και παιγμενα)
        if gs:
            return gs, season
    except Exception as e:
        print(f'el_projections.json μη διαθεσιμο ({e}) — δοκιμαζω el_sched.json')
    try:
        S = json.load(open(SCHED_F, encoding='utf-8'))
        season = sorted(S)[-1]
        gs = [dict(code=x['code'], round=x.get('rnd'), utc=_pdt(x['utc']), hcode=x['hcode'],
                   acode=x['acode'], home=x['home'], away=x['away'])
              for x in S[season] if not x.get('played')]
        return gs, season
    except Exception as e:
        print(f'ουτε el_sched.json ({e})')
        return [], None


# ---------------- parsing ενος TOA game (προοπτικη ΤΟΥ ΔΙΚΟΥ ΜΑΣ γηπεδουχου) ----------------
def _book_lines(b, h_name, a_name):
    """-> dict(sp=(line_home, oh, oa), tot=(tl, over, under), ml=(mh, ma)) για ενα βιβλιο."""
    out = {}
    for m in b.get('markets', []):
        key = m.get('key'); oc = m.get('outcomes', [])
        if key == 'spreads':
            hp = ho = ao = None
            for o in oc:
                if o.get('name') == h_name:
                    hp, ho = o.get('point'), o.get('price')
                elif o.get('name') == a_name:
                    ao = o.get('price')
            if hp is not None and ho and ao:
                out['sp'] = (float(hp), float(ho), float(ao))
        elif key == 'totals':
            tl = to = tu = None
            for o in oc:
                nm = str(o.get('name', '')).lower()
                if nm == 'over':
                    tl, to = o.get('point'), o.get('price')
                elif nm == 'under':
                    tu = o.get('price')
            if tl is not None and to and tu:
                out['tot'] = (float(tl), float(to), float(tu))
        elif key == 'h2h':
            mh = ma = None
            for o in oc:
                if o.get('name') == h_name:
                    mh = o.get('price')
                elif o.get('name') == a_name:
                    ma = o.get('price')
            if mh and ma:
                out['ml'] = (float(mh), float(ma))
    return out


def _best(vals):
    """[(price, book)] -> (max price, book) ή (None, None)."""
    vals = [v for v in vals if v[0]]
    if not vals:
        return None, None
    p, bk = max(vals, key=lambda v: v[0])
    return round(p, 3), bk


def parse_game(g, swapped=False):
    """Pinnacle + διαμεσος + καλυτερες τιμες, στην προοπτικη του ΔΙΚΟΥ μας γηπεδουχου."""
    h_name, a_name = g.get('home_team'), g.get('away_team')
    if swapped:
        h_name, a_name = a_name, h_name
    books = {b.get('key'): _book_lines(b, h_name, a_name) for b in g.get('bookmakers', [])}
    pin = {}
    P = books.get('pinnacle') or {}
    if 'sp' in P:
        pin.update(line=P['sp'][0], oh=P['sp'][1], oa=P['sp'][2])
    if 'tot' in P:
        pin.update(tl=P['tot'][0], to=P['tot'][1], tu=P['tot'][2])
    if 'ml' in P:
        pin.update(mh=P['ml'][0], ma=P['ml'][1])
    sps = [v['sp'][0] for v in books.values() if 'sp' in v]
    tts = [v['tot'][0] for v in books.values() if 'tot' in v]
    cons = dict(n_sp=len(sps), n_tot=len(tts))
    if sps:
        cons['line'] = float(statistics.median(sps))
    if tts:
        cons['tl'] = float(statistics.median(tts))
    best = {}
    ref_sp = pin.get('line', cons.get('line'))
    if ref_sp is not None:
        at = [(bk, v['sp']) for bk, v in books.items() if 'sp' in v and abs(v['sp'][0] - ref_sp) < 0.01]
        best['line'] = ref_sp
        best['oh'], best['oh_bk'] = _best([(s[1], bk) for bk, s in at])
        best['oa'], best['oa_bk'] = _best([(s[2], bk) for bk, s in at])
    ref_tl = pin.get('tl', cons.get('tl'))
    if ref_tl is not None:
        at = [(bk, v['tot']) for bk, v in books.items() if 'tot' in v and abs(v['tot'][0] - ref_tl) < 0.01]
        best['tl'] = ref_tl
        best['to'], best['to_bk'] = _best([(s[1], bk) for bk, s in at])
        best['tu'], best['tu_bk'] = _best([(s[2], bk) for bk, s in at])
    best['mh'], best['mh_bk'] = _best([(v['ml'][0], bk) for bk, v in books.items() if 'ml' in v])
    best['ma'], best['ma_bk'] = _best([(v['ml'][1], bk) for bk, v in books.items() if 'ml' in v])
    best = {k: v for k, v in best.items() if v is not None}
    return pin, cons, best, len(books)


def match_game(g, games):
    """-> (our_game, swapped) ή (None, None). Ωρα ±30' + κοινες λεξεις (και οι 2 πλευρες ≥1)."""
    try:
        gko = _pdt(g.get('commence_time'))
    except Exception:
        return None, None
    th, ta = g.get('home_team', ''), g.get('away_team', '')
    best, bsw, bs = None, None, 0
    for f in games:
        if abs((f['utc'] - gko).total_seconds()) > MATCH_MIN * 60:
            continue
        for sw in (False, True):
            sh = name_score(ta if sw else th, f['home'])
            sa = name_score(th if sw else ta, f['away'])
            if min(sh, sa) < 1:
                continue
            s = sh + sa - (0.5 if sw else 0)       # ισοπαλια -> προτιμα τον κανονικο προσανατολισμο
            if s > bs:
                best, bsw, bs = f, sw, s
    return best, bsw


def _sig(rec):
    p, c = rec.get('pin', {}), rec.get('cons', {})
    return tuple(p.get(k) for k in ('line', 'oh', 'oa', 'tl', 'to', 'tu', 'mh', 'ma')) + \
        (c.get('line'), c.get('tl'))


def build_records(toa_games, games, now, old_odds):
    """Ενημερωνει/επιστρεφει (odds, hist_rows, unmatched, nmatch). ΜΟΝΟ ματς που δεν ξεκινησαν."""
    odds = {k: v for k, v in old_odds.items()
            if v.get('commence') and (now - _pdt(v['commence'])).total_seconds() < PRUNE_H * 3600}
    upcoming = [f for f in games if f['utc'] > now]
    hist_rows, unmatched, nmatch = [], [], 0
    for g in toa_games:
        try:
            if _pdt(g.get('commence_time')) <= now:      # ξεκινησε -> in-play τιμες, οχι στο κλεισιμο
                continue
        except Exception:
            continue
        f, sw = match_game(g, upcoming)
        if f is None:
            unmatched.append(f"{g.get('home_team')} vs {g.get('away_team')} {str(g.get('commence_time'))[:16]}")
            continue
        pin, cons, best, nbk = parse_game(g, sw)
        if not pin and not cons.get('n_sp') and not cons.get('n_tot') and not best:
            continue
        key = str(f['code'])
        rec = dict(code=f['code'], round=f.get('round'), hcode=f['hcode'], acode=f['acode'],
                   home=f['home'], away=f['away'], commence=f['utc'].isoformat(),
                   when=now.isoformat()[:16], toa_id=g.get('id'),
                   toa_home=g.get('home_team'), toa_away=g.get('away_team'), swapped=bool(sw),
                   n_books=nbk, pin=pin, cons=cons, best=best)
        if _sig(rec) != _sig(odds.get(key) or {}):
            row = dict(t=rec['when'], code=f['code'], commence=rec['commence'])
            row.update({k: v for k, v in pin.items()})
            if cons.get('line') is not None:
                row['cl'] = cons['line']
            if cons.get('tl') is not None:
                row['ctl'] = cons['tl']
            # καλυτερες τιμες ολων των βιβλιων στη γραμμη αναφορας (fallback αν λειπει Pinnacle)
            for k_src, k_dst in (('line', 'bl'), ('oh', 'boh'), ('oa', 'boa'), ('tl', 'btl'),
                                 ('to', 'bto'), ('tu', 'btu'), ('mh', 'bmh'), ('ma', 'bma')):
                if best.get(k_src) is not None:
                    row[k_dst] = best[k_src]
            hist_rows.append(row)
        odds[key] = rec
        nmatch += 1
    return odds, hist_rows, unmatched, nmatch


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    games, season = our_games(now)
    fut = [(f['utc'] - now).total_seconds() / 3600 for f in games if f['utc'] > now]
    nearest_h = min(fut) if fut else None
    if nearest_h is None or nearest_h > WINDOW_H:
        why = 'κανενα επερχομενο ματς' if nearest_h is None else f'κοντινοτερο τζαμπολ σε {nearest_h:.1f}h'
        print(f'Ευρωλιγκα: {why} (> {WINDOW_H}h) — 0 credits')
        return
    try:
        old = json.load(open(OUT_F, encoding='utf-8'))
    except Exception:
        old = {}
    try:
        age_min = (now - _pdt(old['scanned_at'])).total_seconds() / 60
    except Exception:
        age_min = 1e9
    gap = NEAR_GAP_MIN if nearest_h <= NEAR_H else MIN_GAP_MIN
    if age_min < gap and not FORCE:
        print(f'Ευρωλιγκα: τελευταιο request πριν {age_min:.0f}λ < {gap}λ '
              f'(κοντινοτερο τζαμπολ σε {nearest_h:.1f}h) — skip, 0 credits')
        return
    key = os.environ.get('TOA_KEY')
    if not key:
        print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — δεν γινεται fetch, 0 credits, το αρχειο μενει ως εχει')
        return
    import requests
    r = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
                     params=dict(apiKey=key, regions='eu', markets='h2h,spreads,totals', oddsFormat='decimal'),
                     timeout=45)
    rem = r.headers.get('x-requests-remaining')
    used = r.headers.get('x-requests-last')
    if r.status_code != 200:
        print(f'Ευρωλιγκα: TOA {r.status_code} ({r.text[:200]}) — τιποτα δεν γραφτηκε')
        return
    odds, hist_rows, unmatched, nmatch = build_records(r.json(), games, now, old.get('odds', {}))
    json.dump(dict(scanned_at=now.isoformat()[:16], season=season, credits_remaining=rem,
                   n_games=nmatch, unmatched=unmatched[:20], odds=odds),
              open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
    if hist_rows:
        with open(HIST_F, 'a', encoding='utf-8') as hf:
            for row in hist_rows:
                hf.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'Ευρωλιγκα: TOA {len(r.json())} ματς · ταιριαξαν {nmatch} · unmatched {len(unmatched)} · '
          f'hist +{len(hist_rows)} · credits used {used} · left {rem}')
    if unmatched:
        print('  unmatched:', '; '.join(unmatched[:8]))


if __name__ == '__main__':
    main()
