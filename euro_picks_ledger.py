"""
euro_picks_ledger.py — ΗΜΕΡΟΛΟΓΙΟ ευρωπαϊκων picks (UCL/UEL/UECL) για το Pick History (26/9/2026, εντολη Στελιου).

Ιδιος κανονας με τα εγχωρια και τις εθνικες:
  • ΕΙΣΟΔΟΣ = η πρωτη σαρωση μεσα σε 72ω πριν τη σεντρα οπου το pick ειναι ενεργο (τιμη/γραμμη εκεινης της στιγμης)·
    ενα pick ανα ματς & πλευρα (AH γηπ./φιλοξ., over). Ενα pick που ηρθε νωριτερα μπαινει οταν «περασει» στις 72ω.
  • ΚΛΕΙΣΙΜΟ = τελευταια καταγραφη του euro_odds_hist.jsonl πριν τη σεντρα (Odds API, ιδιο feed με τα picks).
  • ΑΠΟΤΕΛΕΣΜΑ + xG = FotMob matchDetails (σκορ, αθροισμα xG σουτ ανα ομαδα).
  • UEL = ΣΚΙΑ (no_play) — γραφεται, δεν παιζεται. ΕΞΑΙΡΕΣΗ 9/10/2026: UEL φαβορι εντος (rule='uel_home_fav', κλειδι mid|1|uel_hf) = ΚΑΝΟΝΙΚΟ.
Τρεχει στον scanner (scanner_tick.sh) μετα το euro_shadow_scan.py. Αρχειο: euro_picks_ledger.jsonl.

Χρηση:  python euro_picks_ledger.py              (καταγραφη + εκκαθαριση)
        python euro_picks_ledger.py --backfill   (μια φορα: αναδρομικα απο το git ιστορικο του euro_value_latest.json)
"""
import os, sys, json, subprocess, datetime as dt
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
LED_F = os.path.join(ROOT, 'euro_picks_ledger.jsonl')
LATEST_F = os.path.join(ROOT, 'euro_value_latest.json')
HIST_F = os.path.join(ROOT, 'euro_odds_hist.jsonl')
UTC = dt.timezone.utc
ENTRY_H = 72


def _dt(s):
    try:
        d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
    except Exception:
        return None


def _jsonl(f):
    out = []
    if os.path.exists(f):
        for ln in open(f, encoding='utf-8'):
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def _key(p):
    if p.get('rule') == 'uel_home_fav':        # 9/10/2026: χωριστο ρευμα — το κανονικο UEL φαβορι εντος δεν μπλοκαρεται απο τη σκια
        return f"{p['mid']}|1|uel_hf"
    return f"{p['mid']}|{'over' if p.get('role') == 'over' else p['side']}"


def entries(picks, t, have):
    """picks (euro_value_latest) της σαρωσης τη στιγμη t → νεες εισοδοι ≤72ω (μια ανα ματς & πλευρα)."""
    out = []
    for p in picks:
        ko = _dt(p.get('ko'))
        if ko is None:
            continue
        hb = (ko - t).total_seconds() / 3600
        if p.get('rule') == 'uel_home_fav_wait':   # 9/10: UEL φαβορι εντος εκτος παραθυρου 12-36ω = μονο ενδειξη, δεν γραφεται
            continue
        k = _key(p)
        if 0 < hb <= ENTRY_H and k not in have:
            have.add(k)
            out.append(dict(key=k, seen=t.isoformat(timespec='minutes'), hours_before=round(hb, 1), mid=str(p['mid']), comp=p['comp'],
                            rnd=p.get('rnd'), ko=ko.strftime('%Y-%m-%dT%H:%M'), home=p['home'], away=p['away'], hid=p.get('hid'),
                            aid=p.get('aid'), mkt=('OVER' if p.get('role') == 'over' else 'AH'), role=p.get('role'), side=p['side'],
                            line=p['line'], odds=p['odds'], edge=p['edge'], band=p.get('band'), rule=p.get('rule'),
                            # UEL κλειστο 11/9 (σκια) — ΕΞΑΙΡΕΣΗ 9/10/2026: UEL φαβορι εντος (rule uel_home_fav) = κανονικο
                            no_play=(bool(p.get('no_play')) if p.get('rule') == 'uel_home_fav'
                                     else bool(p.get('no_play')) or p['comp'] == 'EuropaLeague')))
    return out


# 10/10/2026 (Στελιος): TELEGRAM για τα ΚΑΝΟΝΙΚΑ ευρωπαικα picks — ΜΟΝΟ Champions League (φαβορι/αουτσαιντερ) και
# UEL φαβορι εντος (rule uel_home_fav). ΟΧΙ Conference League («να το δουλεψουμε πρωτα»), ΟΧΙ overs («να τα δουμε ξανα»),
# ΟΧΙ σκιες. Ενα μηνυμα ανα pick, τη στιγμη που γραφεται στο ημερολογιο (πρωτη εμφανιση ≤72ω· UEL στο παραθυρο 12-36ω).
TG_COMPS = {'ChampionsLeague'}
COMP_LAB = {'ChampionsLeague': 'Champions League', 'EuropaLeague': 'Europa League', 'ConferenceLeague': 'Conference League'}
_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


def tg_ok(r):
    if r.get('no_play') or r.get('mkt') != 'AH' or r.get('role') not in ('fav', 'dog'):
        return False
    return r.get('rule') == 'uel_home_fav' or r.get('comp') in TG_COMPS


def _athens(ko):
    try:
        from zoneinfo import ZoneInfo
        return ko.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:                               # χωρις tzdata: θερινη ως την τελευταια Κυριακη Οκτωβριου
        last_sun = max(dt.date(ko.year, 10, d) for d in range(25, 32) if dt.date(ko.year, 10, d).weekday() == 6)
        dst = dt.date(ko.year, 3, 25) <= ko.date() < last_sun
        return ko + dt.timedelta(hours=3 if dst else 2)


def tg_msg(rows):
    NL = chr(10)
    out = [f"🌍 {len(rows)} ΝΕΑ ευρωπαϊκά picks"]
    for r in sorted(rows, key=lambda x: x['ko']):
        lk = _athens(_dt(r['ko']))
        team = r['home'] if r['side'] == 1 else r['away']
        tag = (NL + '⭐ UEL φαβορί εντός · μικρό stake') if r.get('rule') == 'uel_home_fav' else ''
        out.append(NL + f"📅 {_DAYS[lk.weekday()]} {lk.strftime('%d/%m %H:%M')} · {COMP_LAB.get(r['comp'], r['comp'])}" + NL +
                   f"{r['home']} - {r['away']}, {team} {'+' if r['line'] >= 0 else ''}{r['line']:g} @{r['odds']:.2f}" + NL +
                   f"edge {r['edge'] * 100:.0f}% · {'φαβορί' if r['role'] == 'fav' else 'αουτσάιντερ'}{tag}")
    return NL.join(out)


def record(now=None):
    try:
        d = json.load(open(LATEST_F, encoding='utf-8'))
    except Exception:
        return 0
    now = now or dt.datetime.now(UTC)
    have = {r['key'] for r in _jsonl(LED_F)}
    new = entries(d.get('picks', []), now, have)
    send = [r for r in new if tg_ok(r)]
    if send and os.environ.get('TELEGRAM_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'):
        try:
            import notify
            if notify.send(tg_msg(send)):
                stamp = now.isoformat(timespec='minutes')
                for r in send:
                    r['tg'] = stamp
        except Exception as e:
            print(f'Telegram σφαλμα (μη κρισιμο): {type(e).__name__}: {e}')
    if new:
        with open(LED_F, 'a', encoding='utf-8') as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False) + chr(10))
    return len(new)


def _closing(mid, ko):
    last = None
    for r in _jsonl(HIST_F):
        if str(r.get('mid')) == mid:
            t = _dt(r.get('t'))
            if t is not None and t < ko:
                last = r
    if not last:
        return None
    return {k: last.get(k) for k in ('t', 'line', 'oh', 'oa', 'tl', 'to', 'tu')}


def _result(mid):
    """FotMob: (γκολ γηπ., γκολ φιλοξ., xG γηπ., xG φιλοξ.) αν τελειωσε, αλλιως None."""
    import intl_fetch
    d = json.loads(intl_fetch.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    st = (d.get('header') or {}).get('status') or {}
    if not st.get('finished') or st.get('cancelled'):
        return None
    teams = (d.get('header') or {}).get('teams') or []
    hs, as_ = teams[0].get('score'), teams[1].get('score')
    hid = d['general']['homeTeam']['id']
    xh = xa = 0.0; has = False
    for s in ((d.get('content') or {}).get('shotmap') or {}).get('shots', []) or []:
        if s.get('isOwnGoal') or s.get('expectedGoals') is None:
            continue
        has = True
        if s.get('teamId') == hid:
            xh += s['expectedGoals']
        else:
            xa += s['expectedGoals']
    return int(hs), int(as_), (round(xh, 2) if has else None), (round(xa, 2) if has else None)


def settle(now=None):
    import picks, intl_pricing
    now = now or dt.datetime.now(UTC)
    rows = _jsonl(LED_F)
    changed = 0; cache = {}
    for r in rows:
        if r.get('pnl') is not None:
            continue
        ko = _dt(r['ko'])
        if ko is None or now < ko + dt.timedelta(hours=2, minutes=30):
            continue
        if r['mid'] not in cache:
            try:
                cache[r['mid']] = _result(r['mid'])
            except Exception as e:
                print(f'  FotMob {r["mid"]}: {type(e).__name__}'); cache[r['mid']] = None
        res = cache[r['mid']]
        if res is None:
            continue
        hs, as_, xh, xa = res
        r['score'] = f'{hs}-{as_}'; r['xg_h'], r['xg_a'] = xh, xa
        r['pnl'] = round(intl_pricing.settle_over(hs + as_, r['line'], r['odds']) if r['mkt'] == 'OVER'
                         else picks.settle(hs - as_, 1 if r['side'] == 1 else -1, r['line'], r['odds']), 4)
        r['close'] = _closing(r['mid'], ko)
        changed += 1
    if changed:
        with open(LED_F + '.tmp', 'w', encoding='utf-8') as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        os.replace(LED_F + '.tmp', LED_F)
    return changed


def backfill(since='2026-09-01'):
    log = subprocess.run(['git', 'log', '--reverse', f'--since={since}', '--format=%H %cI', '--', 'euro_value_latest.json'],
                         capture_output=True, text=True, cwd=ROOT).stdout.split('\n')
    have = {r['key'] for r in _jsonl(LED_F)}
    out = []; n = 0
    for ln in log:
        if not ln.strip():
            continue
        h, t = ln.split()
        try:
            d = json.loads(subprocess.run(['git', 'show', f'{h}:euro_value_latest.json'], capture_output=True, cwd=ROOT).stdout.decode('utf-8'))
        except Exception:
            continue
        n += 1
        out += entries(d.get('picks', []), dt.datetime.fromisoformat(t).astimezone(UTC), have)
    with open(LED_F, 'a', encoding='utf-8') as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'backfill: {n} σαρωσεις · {len(out)} εισοδοι ≤72ω')


if __name__ == '__main__':
    if '--backfill' in sys.argv:
        backfill()
    n_new = record()
    n_set = settle()
    rows = _jsonl(LED_F); st = [r for r in rows if r.get('pnl') is not None and not r.get('no_play')]
    print(f'euro ledger: +{n_new} νεες εισοδοι · {n_set} εκκαθαριστηκαν · συνολο {len(rows)}'
          + (f' · παιζομενα {len(st)} {sum(r["pnl"] for r in st):+.2f}μ' if st else ''))
