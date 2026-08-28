"""
scan_value.py — αυτοματος scanner value picks (Windows Task Scheduler).

Τρεχει καθε Ν λεπτα:
  1. Τραβαει live Betfair odds → υπολογιζει value picks (live_odds.compute_picks).
  2. Κραταει STATE (τι εχει ηδη σταλει)· στελνει Telegram ΜΟΝΟ για ΝΕΑ picks ή
     αλλαγες αποδοσεων (>=ODDS_DELTA)· τα ηδη-σταλμενα & ιδια -> σιωπη.
  3. Γραφει value_picks_latest.json (το dashboard το διαβαζει ακαριαια, χωρις API).

Χρηση:  python scan_value.py            # scan + Telegram
        python scan_value.py --no-tg   # scan χωρις ειδοποιησεις (test)
Quota: ~7 OddsPapi requests/scan (free plan 250/μηνα -> ~1/μερα· 30' θελει paid plan).
"""
import os, sys, json, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(ROOT, 'value_scan_state.json')
LATEST_F = os.path.join(ROOT, 'value_picks_latest.json')
MARKET_F = os.path.join(ROOT, 'market_1x2_latest.json')   # market 1X2 για ΟΛΑ τα fixtures (dashboard)
HIST_F = os.path.join(ROOT, 'odds_history.jsonl')         # ιστορικο τιμων: μια γραμμη ανα ΑΛΛΑΓΗ (2026-08-28)
HSTATE_F = os.path.join(ROOT, 'odds_history_state.json')  # τελευταιο στιγμιοτυπο ανα ματς (για ανιχνευση αλλαγης)
RATINGS_SEASON = '2526'   # warm-start· αλλαξε σε '2627' οταν μαζευτουν φετινα ματς
ODDS_DELTA = 0.05         # κατωφλι αλλαγης αποδοσης για re-alert

def _load(path, default):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return default

def _save(path, obj):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)

def pick_key(p):
    return f"{p['lg']}|{p['home']}|{p['away']}|{p['side']}|{p['hcap']:g}"

_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']

def _local(when):
    """TOA commence_time (UTC) -> τοπικη ωρα (Ελλαδας, με DST απο το συστημα)."""
    try:
        return datetime.datetime.fromisoformat(when).replace(tzinfo=datetime.timezone.utc).astimezone()
    except Exception:
        return None

def _pick_line(p, prev_odds=None):
    team = p['home'] if p['side'] == 1 else p['away']
    dt = _local(p.get('when') or '')
    tm = dt.strftime('%H:%M') if dt else ''
    ch = f" (ηταν {prev_odds:.2f})" if prev_odds is not None else ""
    sign = '+' if p['hcap'] >= 0 else ''
    return (f"{p['lg']} {tm}\n"
            f"{p['home']} - {p['away']}, {team} {sign}{p['hcap']:g} @{p['odds']:.2f}{ch} bet {p['stake_final']*100:.1f}%\n"
            f"Fair odds {p['proj_odds']:.2f}, edge {p['edge']*100:.0f}%")

def _build_msg(new_alerts, changed_alerts):
    out = []
    if new_alerts:
        out.append(f"🎯 {len(new_alerts)} ΝΕΑ value picks")
        cur = None
        for p in sorted(new_alerts, key=lambda x: (x.get('when') or '')):
            dt = _local(p.get('when') or '')
            d = f"{_DAYS[dt.weekday()]} {dt.strftime('%d/%m')}" if dt else '—'
            if d != cur:
                out.append(f"\n📅 {d}"); cur = d
            out.append(_pick_line(p)); out.append("")
    if changed_alerts:
        out.append(f"\n🔄 {len(changed_alerts)} ΑΛΛΑΞΑΝ odds")
        for p, prev in sorted(changed_alerts, key=lambda x: (x[0].get('when') or '')):
            out.append(_pick_line(p, prev))
    return "\n".join(out)


def log_odds_history(odds_rows, now_utc):
    """Γραφει στο odds_history.jsonl ΜΟΝΟ τις αλλαγες (γραμμη/αποδοσεις/1Χ2) ανα ματς.
    Κραταει το τελευταιο στιγμιοτυπο στο HSTATE_F. Επιστρεφει ποσες αλλαγες γραφτηκαν."""
    hstate = _load(HSTATE_F, {})
    wrote = 0
    with open(HIST_F, 'a', encoding='utf-8') as fh:
        for r in odds_rows:
            key = f"{r['hid']}_{r['aid']}"
            sig = [r.get('line'), r.get('oh'), r.get('oa'), r.get('h2h')]
            if hstate.get(key, {}).get('sig') == sig:
                continue
            rec = dict(t=now_utc, **r)
            fh.write(json.dumps(rec, ensure_ascii=False) + chr(10))
            hstate[key] = dict(sig=sig, t=now_utc)
            wrote += 1
    # καθαρισμος state: κρατα μονο ματς με προσφατη καταγραφη (30 μερες) — το jsonl μενει ανεπαφο
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()
    hstate = {k: v for k, v in hstate.items() if v.get('t', '') >= cutoff}
    _save(HSTATE_F, hstate)
    return wrote

def scan(notify_tg=True):
    import toa_live
    res = toa_live.compute_picks_toa(list(toa_live.SPORT), RATINGS_SEASON)   # The Odds API (πληρωμενο)
    picks = res['picks']
    now = datetime.datetime.now().isoformat(timespec='minutes')
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')
    try:
        n_hist = log_odds_history(res.get('odds_rows', []), now_utc)
        print(f"odds_history: {n_hist} αλλαγες καταγραφηκαν ({len(res.get('odds_rows', []))} fixtures)")
    except Exception as e:
        print(f"odds_history ΣΦΑΛΜΑ (μη κρισιμο): {type(e).__name__}: {e}")
    state = _load(STATE_F, {})

    new_alerts, changed_alerts = [], []
    cur_keys = set()
    for p in picks:
        k = pick_key(p); cur_keys.add(k)
        prev = state.get(k)
        if prev is None:
            new_alerts.append(p)
            state[k] = dict(odds=p['odds'], edge=p['edge'], when=p.get('when'), first_seen=now)
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed_alerts.append((p, prev.get('odds')))
            state[k].update(odds=p['odds'], edge=p['edge'])

    # prune: πεταξε keys που το ματς τους περασε (η δεν εμφανιζονται εδω & πολυ παλια)
    today = now[:10]
    for k in list(state):
        w = state[k].get('when') or ''
        if w and w[:10] < today and k not in cur_keys:
            del state[k]

    _save(STATE_F, state)
    _save(LATEST_F, dict(scanned_at=now, ratings_season=RATINGS_SEASON,
                         gross=res['gross'], scale=res['scale'], cap=res['cap'],
                         credits_remaining=res.get('credits_remaining'), credits_cost=res.get('credits_cost'),
                         n_new=len(new_alerts), n_changed=len(changed_alerts), picks=picks))
    _save(MARKET_F, dict(scanned_at=now, odds=res.get('market_1x2', {})))   # market 1X2 -> dashboard cards

    # ---- Telegram ----
    if notify_tg and (new_alerts or changed_alerts):
        try:
            import notify
            notify.send(_build_msg(new_alerts, changed_alerts))
        except Exception as e:
            print("Telegram σφαλμα:", e)

    print(f"[{now}] {len(picks)} picks total · {len(new_alerts)} νεα · {len(changed_alerts)} changed")
    return new_alerts, changed_alerts

# ---------- ADAPTIVE gating (πυκνα κοντα σε ματς, αραια μεσοβδομαδα) ----------
FIX_CACHE = os.path.join(ROOT, 'value_fixtures_cache.json')   # πλησιεστερα kickoffs (FotMob, cached 6h)
LAST_SCAN = os.path.join(ROOT, 'value_last_scan.txt')

def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def _fetch_kickoffs():
    """Τα επομενα ~40 kickoffs ολων των λιγκων απο FotMob (δωρεαν)."""
    sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
    import build_data
    ks = []
    for lg in build_data.LEAGUE_FOTMOB:
        try:
            ks += [f['utc'] for f in build_data.fetch_upcoming(lg) if f.get('utc')]
        except Exception:
            pass
    now = _now_utc()
    fut = sorted(k for k in ks if _to_dt(k) and (_to_dt(k) - now).total_seconds() > -7200)
    return fut[:40]

def _to_dt(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None

def _nearest_kickoff_hours():
    now = _now_utc()
    cache = _load(FIX_CACHE, {})
    ca = _to_dt(cache.get('cached_at'))
    kicks = cache.get('kickoffs', [])
    fresh = ca and (now - ca).total_seconds() < 6 * 3600
    future = [(_to_dt(k) - now).total_seconds() / 3600 for k in kicks if _to_dt(k) and _to_dt(k) > now]
    if not fresh or not future:
        try:
            kicks = _fetch_kickoffs()
            _save(FIX_CACHE, {'cached_at': now.isoformat(), 'kickoffs': kicks})
            future = [(_to_dt(k) - now).total_seconds() / 3600 for k in kicks if _to_dt(k) and _to_dt(k) > now]
        except Exception as e:
            print("FotMob kickoff-check σφαλμα:", e)
            return 24.0   # ασφαλες default: σαν να ειναι ματς σε ~1 μερα (scan καθε 2h)
    return min(future) if future else 999.0

def _last_scan_hours():
    try:
        with open(LAST_SCAN, encoding='utf-8') as fh:
            return (_now_utc() - _to_dt(fh.read().strip())).total_seconds() / 3600
    except Exception:
        return 999.0

def auto():
    """Καλειται καθε 30' απο το Task Scheduler· κανει TOA scan ΜΟΝΟ οταν πρεπει."""
    h = _nearest_kickoff_hours()
    gap = 24.0 if h > 72 else (2.0 if h > 12 else 0.5)   # matchday 30' · <3μερες 2h · αλλιως 1×/μερα
    since = _last_scan_hours()
    if since >= gap:
        scan(notify_tg=True)
        with open(LAST_SCAN, 'w', encoding='utf-8') as fh:
            fh.write(_now_utc().isoformat())
    else:
        print(f"[{_now_utc().isoformat(timespec='minutes')}] skip · πλησιεστερο ματς {h:.1f}h · "
              f"gap {gap}h · τελευταιο scan {since:.1f}h πριν")

if __name__ == '__main__':
    if 'auto' in sys.argv:
        auto()
    else:
        scan(notify_tg=('--no-tg' not in sys.argv))
