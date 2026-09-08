# -*- coding: utf-8 -*-
"""toa_pin_hist_fetch.py — Ιστορικο Pinnacle closing (h2h + AH spread) για UCL/UEL/UECL 2223-2526
μεσω The Odds API HISTORICAL endpoints.

Τρεχει στο GitHub Actions (workflow toa-pin-hist.yml, secret TOA_KEY). Τοπικα χωρις TOA_KEY
δουλευουν μονο τα offline modes:
    python toa_pin_hist_fetch.py --plan      # πλανο snapshots + κοστος (0 κλησεις)
    python toa_pin_hist_fetch.py --selftest  # dry-run matcher σε πλαστο snapshot (0 κλησεις)
    python toa_pin_hist_fetch.py             # κανονικο fetch (θελει TOA_KEY)

ΣΧΕΔΙΟ: ενα snapshot ανα (comp, slot 30') στο min(KO του slot) − 10' → ~κλεισιμο γραμμων.
Κοστος: 10 credits × 2 markets (h2h,spreads) × 1 region (eu) = 20 credits/snapshot.
Αν το συνολο ξεπερναει το CREDIT_BUDGET, συγχωνευονται slots που απεχουν <90'
(snapshot στο αργοτερο slot − 10').

Εξοδος: toa_pin_hist.jsonl   (1 γραμμη/ματς: mid, sea, comp, ko, snap_ts, h,d,a, line, oh, oa, eid, ct)
        toa_pin_hist_state.json  (ποια snapshots εγιναν — idempotent resume)
Σεβεται x-requests-remaining: σταματα ευγενικα αν πεσει < 30000 και το γραφει στο stdout.
"""
import os, sys, json, time, datetime, argparse

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
FIX_F = os.path.join(ROOT, 'europe_fixtures.json')
OUT_F = os.path.join(ROOT, 'toa_pin_hist.jsonl')
STATE_F = os.path.join(ROOT, 'toa_pin_hist_state.json')

# συμβασεις ονοματων/parsers απο τον live euro scanner (ιδιο matcher παντου)
from euro_odds_scan import norm, sim, ALIAS_EU, _h2h, _spread, _pdt, SPORT_EU

SEASONS = ('2223', '2324', '2425', '2526')
COMPS = ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague')
SLOT_MIN = 30            # στρογγυλεμα ΚΟ σε slot 30'
SNAP_OFFSET_MIN = 10     # snapshot στο slot_KO − 10'
MERGE_MIN = 90           # συγχωνευση slots που απεχουν < 90' (μονο αν ξεφευγει το κοστος)
COST_PER_SNAP = 20       # 10 credits × 2 markets × 1 region
CREDIT_BUDGET = 8000     # πανω απο αυτο → συγχωνευση slots
STOP_REMAINING = 30000   # ευγενικο stop αν τα credits του λογαριασμου πεσουν κατω απο αυτο
MATCH_WIN_S = 1200       # ±20' παραθυρο ΚΟ για ταιριασμα event↔fixture
SIM_THRESH = 1.1         # ~0.55 ανα πλευρα (ιδιο με euro_odds_scan)


def load_fixtures():
    """[{mid, sea, comp, ko(datetime), home, away}] για 2223-2526, ολα τα comps."""
    d = json.load(open(FIX_F, encoding='utf-8'))
    out = []
    for comp in COMPS:
        for sea in SEASONS:
            for m in d.get(f'{comp}_{sea}', []):
                try:
                    ko = _pdt(m['utc'])
                except Exception:
                    continue
                out.append(dict(mid=str(m['mid']), sea=sea, comp=comp, ko=ko,
                                home=m['hname'], away=m['aname']))
    return out


def build_slots(fixtures):
    """Ομαδοποιηση ανα (comp, slot 30') → λιστα snapshots:
    [{sid, comp, snap(datetime), fixtures:[...]}] ταξινομημενη χρονικα."""
    groups = {}
    for f in fixtures:
        ko = f['ko']
        slot = ko.replace(minute=(ko.minute // SLOT_MIN) * SLOT_MIN, second=0, microsecond=0)
        groups.setdefault((f['comp'], slot), []).append(f)
    snaps = []
    for (comp, slot), fs in groups.items():
        # snapshot ΠΡΙΝ απο ολα τα ΚΟ του slot: min(KO) − 10'
        snap = min(x['ko'] for x in fs) - datetime.timedelta(minutes=SNAP_OFFSET_MIN)
        snaps.append(dict(comp=comp, snap=snap, fixtures=sorted(fs, key=lambda x: x['ko'])))
    snaps.sort(key=lambda s: (s['snap'], s['comp']))

    # αν το κοστος ξεφευγει: συγχωνευση διαδοχικων slots ιδιου comp που απεχουν < MERGE_MIN
    if len(snaps) * COST_PER_SNAP > CREDIT_BUDGET:
        merged = []
        by_comp = {}
        for s in snaps:
            by_comp.setdefault(s['comp'], []).append(s)
        for comp, ss in by_comp.items():
            cur = None
            for s in ss:
                if cur and (s['snap'] - cur['snap']).total_seconds() < MERGE_MIN * 60:
                    cur['fixtures'] += s['fixtures']
                    # «το αργοτερο − 10'»: κρατα το snap του αργοτερου slot
                    cur['snap'] = max(cur['snap'], s['snap'])
                else:
                    if cur:
                        merged.append(cur)
                    cur = dict(s)
                    cur['fixtures'] = list(s['fixtures'])
            if cur:
                merged.append(cur)
        merged.sort(key=lambda s: (s['snap'], s['comp']))
        snaps = merged

    for s in snaps:
        s['sid'] = f"{s['comp']}|{s['snap'].isoformat()}"
    return snaps


def match_events(events, fixtures):
    """Ταιριασμα TOA events → fixtures του slot. Επιστρεφει (pairs, unmatched_fixtures).
    pairs = [(fixture, event)]. Ιδια λογικη με euro_odds_scan (ΚΟ ±20' + ονοματα/ALIAS)."""
    pairs, used = [], set()
    for f in fixtures:
        best, bs = None, 0.0
        for g in events:
            gid = g.get('id')
            if gid in used:
                continue
            try:
                gko = _pdt(g.get('commence_time'))
            except Exception:
                continue
            if abs((f['ko'] - gko).total_seconds()) > MATCH_WIN_S:
                continue
            ht = ALIAS_EU.get(g.get('home_team'), g.get('home_team'))
            at = ALIAS_EU.get(g.get('away_team'), g.get('away_team'))
            s = sim(ht, f['home']) + sim(at, f['away'])
            if s > bs:
                bs, best = s, g
        if best is not None and bs >= SIM_THRESH:
            pairs.append((f, best))
            used.add(best.get('id'))
        else:
            pairs.append((dict(f, best_sim=round(bs, 2)), None))
    matched = [(f, g) for f, g in pairs if g is not None]
    unmatched = [f for f, g in pairs if g is None]
    return matched, unmatched


def rec_from_event(f, g, snap_iso):
    """Γραμμη jsonl απο fixture+event: pinnacle h2h + κυριο spread (home-persp)."""
    h2 = _h2h(g, bks=('pinnacle',))
    sp = _spread(g, bks=('pinnacle',))
    if not h2 and not sp:
        return None
    rec = dict(mid=f['mid'], sea=f['sea'], comp=f['comp'], ko=f['ko'].isoformat(),
               snap_ts=snap_iso, eid=g.get('id'), ct=g.get('commence_time'))
    if h2:
        rec.update(h=round(h2[0], 3), d=round(h2[1], 3), a=round(h2[2], 3))
    if sp:
        rec.update(line=sp[0], oh=round(sp[1], 3), oa=round(sp[2], 3))
    return rec


# ---------------------------------------------------------------- offline modes
def print_plan(snaps, head=5):
    n = len(snaps)
    nfix = sum(len(s['fixtures']) for s in snaps)
    print(f'ΠΛΑΝΟ: {n} snapshots · {nfix} ματς · κοστος {n * COST_PER_SNAP} credits '
          f'({COST_PER_SNAP}/snapshot: 10 × 2 markets × 1 region)')
    per = {}
    for s in snaps:
        per[s['comp']] = per.get(s['comp'], 0) + 1
    for c, v in sorted(per.items()):
        print(f'  {c}: {v} snapshots')
    print(f'πρωτα {head} slots:')
    for s in snaps[:head]:
        kos = ', '.join(x['ko'].strftime('%H:%M') for x in s['fixtures'])
        print(f"  {s['snap'].isoformat()}  {s['comp']:<17} {len(s['fixtures'])} ματς (KO: {kos})")


def selftest():
    """Dry-run matcher σε πλαστο snapshot (0 κλησεις)."""
    fx = load_fixtures()
    tgt = [f for f in fx if f['sea'] == '2223' and f['comp'] == 'ChampionsLeague'][:3]
    fake_events = []
    for i, f in enumerate(tgt):
        # TOA ονοματα οπως θα ερχονταν (με μικρες παραλλαγες) + pinnacle markets
        hname = {'FC København': 'FC Copenhagen', 'Inter': 'Inter Milan'}.get(f['home'], f['home'])
        fake_events.append(dict(
            id=f'fakeid{i}', commence_time=f['ko'].isoformat().replace('+00:00', 'Z'),
            home_team=hname, away_team=f['away'],
            bookmakers=[dict(key='pinnacle', markets=[
                dict(key='h2h', outcomes=[
                    dict(name=hname, price=1.5), dict(name='Draw', price=4.4),
                    dict(name=f['away'], price=6.0)]),
                dict(key='spreads', outcomes=[
                    dict(name=hname, point=-1.25, price=1.93),
                    dict(name=f['away'], point=1.25, price=1.97)])])]))
    # + ενα εκτος παραθυρου (δεν πρεπει να ταιριαξει)
    fake_events.append(dict(id='fakeX', commence_time='2030-01-01T12:00:00Z',
                            home_team='Foo', away_team='Bar', bookmakers=[]))
    matched, unmatched = match_events(fake_events, tgt)
    print(f'selftest: {len(matched)}/{len(tgt)} ταιριασαν, {len(unmatched)} unmatched')
    for f, g in matched:
        r = rec_from_event(f, g, '2030-01-01T00:00:00+00:00')
        print(' ', json.dumps(r, ensure_ascii=False))
    assert len(matched) == len(tgt), 'selftest ΑΠΕΤΥΧΕ: δεν ταιριασαν ολα'
    print('selftest OK')


# ---------------------------------------------------------------- fetch
def main_fetch(snaps):
    import requests
    key = os.environ.get('TOA_KEY')
    if not key:
        print('TOA_KEY δεν υπαρχει — τρεξε με --plan / --selftest τοπικα, το fetch θελει Actions.')
        return 1
    # state (resume) + ηδη γραμμενα mids
    state = {'done': {}}
    try:
        state = json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        pass
    have_mids = set()
    if os.path.exists(OUT_F):
        for ln in open(OUT_F, encoding='utf-8'):
            try:
                have_mids.add(json.loads(ln)['mid'])
            except Exception:
                pass

    todo = [s for s in snaps if s['sid'] not in state['done']]
    print(f'snapshots: {len(snaps)} συνολο, {len(state["done"])} ηδη, {len(todo)} προς ληψη '
          f'(~{len(todo) * COST_PER_SNAP} credits)')
    out = open(OUT_F, 'a', encoding='utf-8')
    rem = None
    n_written = n_snap = 0
    all_unmatched = []
    try:
        for s in todo:
            sport = SPORT_EU[s['comp']]
            snap_iso = s['snap'].isoformat().replace('+00:00', 'Z')
            r = requests.get(
                f'https://api.the-odds-api.com/v4/historical/sports/{sport}/odds',
                params=dict(apiKey=key, regions='eu', markets='h2h,spreads',
                            bookmakers='pinnacle', oddsFormat='decimal', date=snap_iso),
                timeout=60)
            rem = r.headers.get('x-requests-remaining', rem)
            if r.status_code == 429:
                print('429 rate limit — παυση 5s και ξανα')
                time.sleep(5)
                r = requests.get(
                    f'https://api.the-odds-api.com/v4/historical/sports/{sport}/odds',
                    params=dict(apiKey=key, regions='eu', markets='h2h,spreads',
                                bookmakers='pinnacle', oddsFormat='decimal', date=snap_iso),
                    timeout=60)
                rem = r.headers.get('x-requests-remaining', rem)
            if r.status_code != 200:
                print(f"{s['sid']}: TOA {r.status_code} — {r.text[:200]} · skip (θα ξαναδοκιμαστει)")
                time.sleep(1)
                continue
            payload = r.json()
            events = payload.get('data', []) if isinstance(payload, dict) else payload
            matched, unmatched = match_events(events, s['fixtures'])
            nw = 0
            for f, g in matched:
                if f['mid'] in have_mids:
                    continue
                rec = rec_from_event(f, g, payload.get('timestamp', snap_iso)
                                     if isinstance(payload, dict) else snap_iso)
                if rec:
                    out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    have_mids.add(f['mid'])
                    nw += 1
            out.flush()
            for f in unmatched:
                all_unmatched.append(f"{f['sea']} {f['comp'][:4]} {f['home']} vs {f['away']} "
                                     f"(sim {f.get('best_sim', 0)})")
            state['done'][s['sid']] = dict(ts=snap_iso, events=len(events),
                                           matched=len(matched), written=nw)
            n_written += nw
            n_snap += 1
            json.dump(state, open(STATE_F, 'w', encoding='utf-8'), ensure_ascii=False)
            if n_snap % 20 == 0:
                print(f'  ...{n_snap}/{len(todo)} snapshots · {n_written} γραμμες · credits left {rem}')
            try:
                if rem is not None and float(rem) < STOP_REMAINING:
                    print(f'ΣΤΑΜΑΤΩ ευγενικα: credits remaining {rem} < {STOP_REMAINING}. '
                          f'Ξανατρεξε το workflow αργοτερα — θα συνεχισει απο εκει που εμεινε.')
                    break
            except (TypeError, ValueError):
                pass
            time.sleep(0.4)
    finally:
        out.close()
        json.dump(state, open(STATE_F, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'ΤΕΛΟΣ: {n_snap} snapshots τωρα · {n_written} νεες γραμμες · '
          f'{len(state["done"])}/{len(snaps)} snapshots συνολικα · credits left {rem}')
    if all_unmatched:
        print(f'unmatched fixtures ({len(all_unmatched)}):')
        for u in all_unmatched[:40]:
            print('  ', u)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true', help='μονο πλανο snapshots/κοστος (offline)')
    ap.add_argument('--selftest', action='store_true', help='dry-run matcher (offline)')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    fx = load_fixtures()
    snaps = build_slots(fx)
    print_plan(snaps)
    if a.plan:
        return 0
    return main_fetch(snaps)


if __name__ == '__main__':
    sys.exit(main())
