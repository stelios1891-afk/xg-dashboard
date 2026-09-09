# -*- coding: utf-8 -*-
"""dom_odds_scan.py — Αποδοσεις αγορας (TOA) για τα εγχωρια ματς των CORE7 (dashboard Match Odds).

Εγχωριο αντιστοιχο του euro_odds_scan.py: bulk h2h/spreads/totals ανα λιγκα (το bulk
endpoint ΔΕΝ δινει alternates — 422) + per-event alternate σκαλες (AH & O/U), ωστε τα
projections να δειχνουν μοντελο vs αγορα. ΔΕΝ αγγιζει τη live μηχανη picks
(toa_live/scan_value/picks/live_odds — μονο imports, καμια αλλαγη).

GATING (7 λιγκες = πολλα credits, προσοχη):
  - bulk ανα λιγκα ΜΟΝΟ αν εχει ματς με ΚΟ εντος 72h ΚΑΙ το τελευταιο bulk της ειναι
    >45' παλιο (ΚΟ εντος 6h -> καθε τρεξιμο). Κοστος bulk: 3 credits/λιγκα.
  - alternates ανα ματς ΜΟΝΟ για ΚΟ εντος 30h, refresh ανα 3h (30' οταν ΚΟ εντος 3h).
    Κοστος: 2 credits/ματς.

Ταιριασμα TOA ονοματων -> FotMob ids: live_odds.assign()/team_match() (ΙΔΙΑ μηχανη με το
live toa_live.compute_picks_toa), fixtures απο build_data.fetch_upcoming (FotMob, δωρεαν,
cache 6h στο dom_fix_cache.json). Κλειδι εξοδου: "{home_id}_{away_id}" — ιδιο σχημα με το
market_1x2_latest.json / build_data._market_1x2 (τα διαβαζει το dashboard ακαριαια).

Εξοδος: dom_odds_latest.json  {scanned_at, odds: {"H_A": {ko, when, h,d,a, line,oh,oa,
        tl,to,tu, ah, ou, alt_when, lg}}, lg_when, credits_remaining}
Χωρις TOA_KEY (τοπικο τρεξιμο): μηνυμα και εξοδος — το αρχειο ΔΕΝ πειραζεται.

Χρηση:  python dom_odds_scan.py              # κανονικο (scanner)
        python dom_odds_scan.py --dry-run    # μονο το name-matching path, 0 TOA requests
"""
import os, sys, json, time, datetime
import requests

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
import toa_live                 # SPORT dict (CORE7 -> TOA sport keys)
import live_odds                # assign()/team_match() — ο matcher του live (μην τον ξαναγραψεις)
import build_data               # fetch_upcoming(): FotMob fixtures με home_id/away_id
import euro_odds_scan as eos    # parsers: _h2h/_spread/_total/_ladders/_pdt (ιδια συμβαση προσημων)

OUT_F = os.path.join(ROOT, 'dom_odds_latest.json')
FIXC_F = os.path.join(ROOT, 'dom_fix_cache.json')   # FotMob fixtures cache (TTL 6h)
HIST_F = os.path.join(ROOT, 'dom_odds_hist.jsonl')  # διαδρομες γραμμων: append-on-change
                                                    # (εντολη Στελιου 9/9: κραταμε ΟΛΕΣ τις
                                                    # αποδοσεις που τραβαμε, οχι μονο το latest)


def _hist_sig(rec):
    return tuple(rec.get(k) for k in ('h', 'd', 'a', 'line', 'oh', 'oa', 'tl', 'to', 'tu'))


def _hist_append(fh_list, now, kid, rec, old_rec):
    if _hist_sig(rec) == _hist_sig(old_rec):
        return
    row = dict(t=now.isoformat()[:16], k=kid, lg=rec.get('lg'), ko=rec.get('ko'))
    for f in ('h', 'd', 'a', 'line', 'oh', 'oa', 'tl', 'to', 'tu'):
        if rec.get(f) is not None:
            row[f] = rec[f]
    try:
        if eos._pdt(rec['ko']) < now:
            row['inplay'] = 1   # μετα το ΚΟ: κραταμε αλλα με σημαια (live τεστ, οχι closing)
    except Exception:
        pass
    fh_list.append(row)

HOURS_AHEAD = 96      # παραθυρο ΚΟ για bulk (96h, οπως τα ευρωπαικα — αιτημα Στελιου 9/9)
HOURS_BACK = 3        # κρατα και ματς που μολις αρχισαν (τελευταιο snapshot)
PRUNE_H = 24          # εγγραφες >24h μετα το ΚΟ πετιουνται
BULK_REFRESH_MIN = 45  # bulk ανα λιγκα το πολυ ανα 45' (ΚΟ εντος 48h)
BULK_FAR_MIN = 180    # ΚΟ 48-96h: bulk ανα 3h (κρατα τα credits χαμηλα)
NEAR_H = 6            # ΚΟ εντος 6h -> bulk σε καθε τρεξιμο
ALT_HOURS = 96        # σκαλες σε ολο το παραθυρο (οπως τα ευρωπαικα)
ALT_REFRESH_MIN = 180  # refresh σκαλων ανα 3h (ΚΟ εντος 30h)
ALT_FAR_MIN = 360     # ΚΟ 30-96h: σκαλες ανα 6h
ALT_NEAR_MIN = 30     # <3h προ ΚΟ: ανα 30'
FIX_TTL_H = 6         # FotMob fixtures cache TTL
FIX_KEEP_H = 8 * 24   # κρατα στο cache μονο fixtures εως 8 μερες μπροστα (μικρο αρχειο)

# TOA ονομα -> FotMob ονομα (προσθηκες οποτε δουμε unmatched στην εξοδο· τα κοινα
# περιπτωσιολογικα τα πιανει ηδη το live_odds.ALIAS + assign)
DOM_ALIAS = {}


def _load(path, default):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return default


def _save(path, obj):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _dt(s):
    """iso string (και 16-char 'YYYY-MM-DDTHH:MM') -> aware datetime (UTC)."""
    s = str(s)
    if len(s) == 16:
        s += ':00+00:00'
    return eos._pdt(s)


def _al(n):
    return DOM_ALIAS.get(n, n)


def upcoming(now):
    """{league: [fixtures]} απο FotMob (build_data.fetch_upcoming), με cache 6h.
    Καθε fixture: utc, home_name, home_id, away_name, away_id."""
    cache = _load(FIXC_F, {})
    try:
        fresh = (now - _dt(cache.get('cached_at'))).total_seconds() < FIX_TTL_H * 3600
    except Exception:
        fresh = False
    if fresh and cache.get('fx'):
        return cache['fx']
    fx = {}
    for lg in toa_live.SPORT:
        try:
            rows = []
            for f in build_data.fetch_upcoming(lg):
                try:
                    if (_dt(f['utc']) - now).total_seconds() > FIX_KEEP_H * 3600:
                        continue
                except Exception:
                    continue
                rows.append(dict(utc=f.get('utc'), home_name=f.get('home_name'),
                                 home_id=f.get('home_id'), away_name=f.get('away_name'),
                                 away_id=f.get('away_id')))
            fx[lg] = rows
        except Exception as e:
            fx[lg] = (cache.get('fx') or {}).get(lg, [])
            print(f'{lg}: FotMob fixtures σφαλμα ({type(e).__name__}) — cache fallback ({len(fx[lg])})')
        time.sleep(0.2)
    _save(FIXC_F, dict(cached_at=now.isoformat(), fx=fx))
    return fx


def match_events(lg, events, fixtures):
    """TOA events -> fixtures μας, με τον matcher του live (assign/team_match).
    Επιστρεφει ([(event, fixture)], unmatched_names)."""
    fot_names = sorted({n for f in fixtures for n in (f['home_name'], f['away_name']) if n})
    toa_names = sorted({_al(n) for g in events
                        for n in (g.get('home_team'), g.get('away_team')) if n})
    res = live_odds.assign(toa_names, fot_names)
    byname = {(f['home_name'], f['away_name']): f for f in fixtures}
    pairs, unmatched = [], []
    for g in events:
        hfot, hok, _ = live_odds.team_match(_al(g.get('home_team')), res)
        afot, aok, _ = live_odds.team_match(_al(g.get('away_team')), res)
        f = byname.get((hfot, afot)) if (hok and aok) else None
        if f is None:
            unmatched.append(f"{g.get('home_team')} vs {g.get('away_team')}")
            continue
        pairs.append((g, f))
    return pairs, unmatched


def _alt_due(rec, now):
    """Χρειαζεται refresh σκαλας (per-event alternates) αυτο το ματς;"""
    if not rec.get('eid') or not rec.get('sport'):
        return False
    try:
        h = (_dt(rec['ko']) - now).total_seconds() / 3600
    except Exception:
        return False
    if not (-HOURS_BACK <= h <= ALT_HOURS):
        return False
    try:
        age = (now - _dt(rec['alt_when'])).total_seconds() / 60
    except Exception:
        age = 1e9
    lim = ALT_NEAR_MIN if 0 <= h <= 3 else (ALT_REFRESH_MIN if h <= 30 else ALT_FAR_MIN)
    return age > lim


def main(dry=False):
    now = datetime.datetime.now(datetime.timezone.utc)
    FX = upcoming(now)
    data = _load(OUT_F, {})
    lg_when = data.get('lg_when', {})
    # prune: εγγραφες >PRUNE_H μετα το ΚΟ πετιουνται
    odds = {}
    for k, v in (data.get('odds') or {}).items():
        try:
            if (now - _dt(v.get('ko'))).total_seconds() < PRUNE_H * 3600:
                odds[k] = v
        except Exception:
            pass
    # ματς στο παραθυρο ανα λιγκα
    upc = {}
    for lg in toa_live.SPORT:
        fs = []
        for f in FX.get(lg, []):
            try:
                ko = _dt(f['utc'])
            except Exception:
                continue
            if not (f.get('home_id') and f.get('away_id')):
                continue
            if -HOURS_BACK * 3600 <= (ko - now).total_seconds() <= HOURS_AHEAD * 3600:
                fs.append(dict(f, ko=ko))
        if fs:
            upc[lg] = fs
    if not upc:
        print(f'κανενα εγχωριο ματς σε {HOURS_AHEAD}h — 0 credits')
        _save(OUT_F, dict(scanned_at=now.isoformat()[:16], odds=odds, lg_when=lg_when,
                          credits_remaining=data.get('credits_remaining'), note='no upcoming'))
        return

    # ---- dry-run: μονο το name-matching path (FotMob ονοματα ως ψευδο-TOA events) ----
    if dry:
        for lg, fs in sorted(upc.items()):
            ev = [dict(home_team=f['home_name'], away_team=f['away_name'],
                       commence_time=f['ko'].isoformat(), bookmakers=[]) for f in fs]
            pairs, unm = match_events(lg, ev, fs)
            keys = [f"{f['home_id']}_{f['away_id']}" for _, f in pairs]
            print(f'{lg}: {len(fs)} fixtures σε {HOURS_AHEAD}h · matched {len(pairs)} · '
                  f'unmatched {len(unm)}' + (f' ({"; ".join(unm[:4])})' if unm else ''))
            if keys:
                print(f'   κλειδια: {", ".join(keys[:4])}{" …" if len(keys) > 4 else ""}')
        print('dry-run: 0 TOA requests, το dom_odds_latest.json δεν αλλαξε')
        return

    # ---- gating: ποιες λιγκες θελουν bulk & αν χρωσταμε σκαλες ----
    fetch_lgs = []
    for lg, fs in upc.items():
        nearest = min((f['ko'] - now).total_seconds() / 3600 for f in fs)
        try:
            age_min = (now - _dt(lg_when.get(lg))).total_seconds() / 60
        except Exception:
            age_min = 1e9
        need_min = BULK_REFRESH_MIN if nearest <= 48 else BULK_FAR_MIN
        if nearest <= NEAR_H or age_min > need_min:
            fetch_lgs.append(lg)
    alt_pending = any(_alt_due(v, now) for v in odds.values())
    if not fetch_lgs and not alt_pending:
        print('ολες οι λιγκες φρεσκες (<45\') και καμια σκαλα δεν χρωσταει — skip (0 credits)')
        return
    if not os.environ.get('TOA_KEY'):
        print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — δεν γινεται fetch, το αρχειο μενει ως εχει')
        return
    apikey = os.environ['TOA_KEY']

    # ---- bulk ανα λιγκα: h2h + κυρια spread + κυριο total ----
    rem = data.get('credits_remaining'); cost = 0; nmatch = 0; unmatched_all = []
    hist_rows = []
    for lg in fetch_lgs:
        sport = toa_live.SPORT[lg]
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                         params=dict(apiKey=apikey, regions='eu', markets='h2h,spreads,totals',
                                     bookmakers='pinnacle,matchbook', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        try:
            cost += int(r.headers.get('x-requests-last') or 0)
        except ValueError:
            pass
        if r.status_code != 200:
            print(f'{lg}: TOA {r.status_code} — skip')
            continue
        events = []
        for g in r.json():
            try:
                gko = eos._pdt(g.get('commence_time'))
            except Exception:
                continue
            if -HOURS_BACK * 3600 <= (gko - now).total_seconds() <= HOURS_AHEAD * 3600:
                events.append(g)
        pairs, unm = match_events(lg, events, upc[lg])
        unmatched_all += [f'[{lg}] {u}' for u in unm]
        for g, f in pairs:
            kid = f"{f['home_id']}_{f['away_id']}"
            h2 = eos._h2h(g); sp = eos._spread(g); tt = eos._total(g)
            old_rec = odds.get(kid) or {}
            rec = dict(ko=f['ko'].isoformat(), when=now.isoformat()[:16], lg=lg,
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
                _hist_append(hist_rows, now, kid, rec, old_rec)
                odds[kid] = rec; nmatch += 1
        lg_when[lg] = now.isoformat()[:16]
        time.sleep(0.3)

    # ---- σκαλες (alternate lines): per-event endpoint, με δικο τους ρυθμο ----
    n_alt = 0
    for kid, rec in odds.items():
        if not _alt_due(rec, now):
            continue
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/{rec['sport']}/events/{rec['eid']}/odds",
                         params=dict(apiKey=apikey, regions='eu',
                                     markets='alternate_spreads,alternate_totals',
                                     bookmakers='pinnacle,matchbook', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        try:
            cost += int(r.headers.get('x-requests-last') or 0)
        except ValueError:
            pass
        if r.status_code != 200:
            continue
        ahl, oul = eos._ladders(r.json())
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

    if hist_rows:
        with open(HIST_F, 'a', encoding='utf-8') as fh:
            for row in hist_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    _save(OUT_F, dict(scanned_at=now.isoformat()[:16], odds=odds, lg_when=lg_when,
                      credits_remaining=rem, unmatched=unmatched_all[:20]))
    print(f'bulk: {len(fetch_lgs)} λιγκες ({", ".join(fetch_lgs) or "—"}) · ταιριασαν {nmatch} ματς · '
          f'σκαλες {n_alt} ματς · hist +{len(hist_rows)}')
    print(f'credits αυτου του scan ~{cost} (x-requests-last: bulk 3/λιγκα + alt 2/ματς) · left {rem}')
    if unmatched_all:
        print('  unmatched (θελουν DOM_ALIAS):', '; '.join(unmatched_all[:8]))


if __name__ == '__main__':
    main(dry='--dry-run' in sys.argv)
