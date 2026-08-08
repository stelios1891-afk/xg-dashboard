"""
dl.py  -  ΒΗΜΑ 2 του pipeline: κατεβασμα shot-level data απο το FotMob.

Διατηρει τον πυρηνα που δουλευε (resume: δεν ξανακατεβαζει οσα υπαρχουν),
και προσθετει RE-CHECK: ξανακατεβαζει τα ματς των τελευταιων N ημερων (default 4),
γιατι η Opta αναθεωρει τα xG μερικες μερες μετα τον αγωνα.

Χρηση:
    python dl.py EPL_2526                     # missing + re-check τελευταιων 4 ημερων
    python dl.py EPL_2526 --recheck-days 4    # ρυθμιση παραθυρου re-check
    python dl.py EPL_2526 --no-recheck        # μονο τα missing (παλια συμπεριφορα)

    # flags για ΔΟΚΙΜΗ (χωρις να πειραζουμε τα πραγματικα data files):
    python dl.py EPL_2526 --out data_test.json --limit 5     # κατεβασε 5 σε αλλο αρχειο
    python dl.py EPL_2526 --now 2025-08-18                   # "σημερα" = δοσμενη μερα (test re-check)
"""
import urllib.request, json, gzip, time, sys, os
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(url, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=25).read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def parse(mid):
    d = json.loads(get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    c = d['content']; gen = d['general']; head = d.get('header', {})
    teams = head.get('teams', [])
    hs = teams[0].get('score') if len(teams) > 0 else None
    as_ = teams[1].get('score') if len(teams) > 1 else None
    hid = gen['homeTeam']['id']; aid = gen['awayTeam']['id']
    shots = []
    for s in c.get('shotmap', {}).get('shots', []):
        if s.get('isOwnGoal'):
            continue
        shots.append({'tid': s.get('teamId'), 'xg': s.get('expectedGoals'),
                      'min': s.get('min'), 'sit': s.get('situation'),
                      'goal': s.get('eventType') == 'Goal'})
    reds = []
    for e in c.get('matchFacts', {}).get('events', {}).get('events', []):
        if e.get('type') == 'Card' and e.get('card') in ('Red', 'RedYellow'):
            reds.append({'home': bool(e.get('isHome')), 'min': e.get('time')})
    return {'mid': mid, 'date': gen.get('matchTimeUTC') or gen.get('matchTimeUTCDate'),
            'home': {'name': gen['homeTeam']['name'], 'id': hid},
            'away': {'name': gen['awayTeam']['name'], 'id': aid},
            'hs': hs, 'as': as_, 'shots': shots, 'reds': reds}


def match_date(s):
    """'Fri, Aug 15, 2025, 19:00 UTC' -> datetime (ή None αν δεν παρσαρεται)."""
    if not s:
        return None
    try:
        return datetime.strptime(s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d')
        except Exception:
            return None


def total_xg(m):
    return round(sum(s['xg'] for s in m.get('shots', []) if s.get('xg') is not None), 3)


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('--'):
        print(__doc__)
        sys.exit(1)
    key = args[0]

    # --- flags ---
    def flag_val(name, default=None):
        if name in args:
            i = args.index(name)
            if i + 1 < len(args):
                return args[i + 1]
        return default

    recheck = '--no-recheck' not in args
    recheck_days = float(flag_val('--recheck-days', 4))
    out_path = flag_val('--out', f'data_{key}.json')
    index_path = flag_val('--index', 'match_index.json')
    limit = flag_val('--limit')
    limit = int(limit) if limit else None
    now_s = flag_val('--now')
    now = datetime.strptime(now_s, '%Y-%m-%d') if now_s else datetime.now(timezone.utc).replace(tzinfo=None)

    idx = json.load(open(index_path, encoding='utf-8'))
    if key not in idx:
        print(f"SKIP {key}: δεν υπαρχει στο {index_path} (0 finished ματς ακομα;) — προσπερναω.")
        sys.exit(0)
    mids = idx[key]

    done = {}
    if os.path.exists(out_path):
        done = json.load(open(out_path, encoding='utf-8'))

    # 1) missing: στο index αλλα οχι κατεβασμενα
    missing = [str(m) for m in mids if str(m) not in done]

    # 2) re-check: ηδη κατεβασμενα ματς των τελευταιων N ημερων (αναθεωρησεις Opta)
    recheck_ids = []
    if recheck:
        for mid, m in done.items():
            dt = match_date(m.get('date'))
            if dt is None:
                continue
            age = (now - dt).total_seconds() / 86400.0
            if -1.0 <= age <= recheck_days:
                recheck_ids.append(str(mid))

    # todo = missing πρωτα, μετα re-check (dedup, διατηρωντας σειρα)
    seen = set()
    todo = []
    for mid in missing + recheck_ids:
        if mid not in seen:
            seen.add(mid); todo.append(mid)
    if limit:
        todo = todo[:limit]

    print(f"{key}:  {len(done)} ηδη κατεβασμενα  |  {len(missing)} νεα(missing)  |  "
          f"{len(recheck_ids)} re-check(≤{recheck_days:g}μερ)  |  θα κατεβω: {len(todo)}"
          + (f"  [limit {limit}]" if limit else ""))
    print(f"  αρχειο: {out_path}  |  now={now.date()}")

    err = 0; changed = 0; revised = 0
    for n, mid in enumerate(todo, 1):
        was = done.get(mid)
        old_xg = total_xg(was) if was else None
        try:
            fresh = parse(mid)
            done[mid] = fresh
            changed += 1
            new_xg = total_xg(fresh)
            if old_xg is not None and abs(new_xg - old_xg) > 1e-6:
                revised += 1
                print(f"  ⟳ ΑΝΑΘΕΩΡΗΣΗ {mid}: {fresh['home']['name']} vs {fresh['away']['name']}"
                      f"  xG {old_xg} → {new_xg}")
        except Exception as e:
            err += 1
            if err <= 5:
                print(f"  err {mid}: {type(e).__name__} {str(e)[:60]}")
        if n % 50 == 0:
            json.dump(done, open(out_path, 'w'))
            print(f"  ...{n}/{len(todo)} (errors {err})")
        time.sleep(0.15)

    json.dump(done, open(out_path, 'w'))
    nshots = sum(len(v['shots']) for v in done.values())
    print(f"DONE {key}: συνολο {len(done)} ματς, {nshots} σουτ  |  "
          f"κατεβηκαν {changed}, αναθεωρησεις {revised}, errors {err}")


if __name__ == '__main__':
    main()
