"""
euro_refresh_due.py — ΤΟ euro-refresh ΣΤΗΝ ΩΡΑ ΤΟΥ (10/10/2026, Στελιος «περνα το»).

Προβλημα: τα προγραμματισμενα (cron) του GitHub καθυστερουν πολυ — το πρωινο 06:00 UTC (09:00 Ελλαδας) ετρεχε στην πραξη ~12:45 UTC
(~7 ωρες αργα), το βραδινο Τρ/Τετ/Πεμ 23:00 UTC ~02:30-02:50 UTC (3-4 ωρες) — και μπορει και να παραλειφθει.
Λυση (ιδια με τον scanner / intl_refresh_due): ο scanner (καθε ~5′) τρεχει αυτο το script:
  ΤΡΟΠΟΣ dispatch (default): βρισκει την τελευταια «ωρα» του euro-refresh (καθε μερα 06:00 UTC · Τρ/Τετ/Πεμ 23:00 UTC). Αν περασαν ≥10′ και
    ΔΕΝ υπαρχει run του euro-refresh που ξεκινησε μετα απο αυτη (ή υπαρχει μονο αποτυχημενο, πανω απο 60′ πριν) → το ζηταει (workflow_dispatch).
  ΤΡΟΠΟΣ --guard (πρωτο job του euro-refresh): αν το run ειναι το ΑΡΓΟΠΟΡΗΜΕΝΟ προγραμματισμενο και ηδη εγινε επιτυχημενο (ή τρεχει) run
    μετα την ιδια ωρα → skip=true (να μην τρεχει διπλο).
Χρειαζεται GH_DISPATCH_TOKEN (ή GITHUB_TOKEN) και GH_REPO/GITHUB_REPOSITORY απο το Actions· τοπικα δεν κανει τιποτα.
"""
import os, sys, json, datetime as dt, urllib.request
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
WF = 'euro-refresh.yml'
GRACE_MIN, RETRY_FAIL_MIN = 10, 60


def last_slot(now):
    """Τελευταια προγραμματισμενη ωρα ≤ now: καθε μερα 06:00 UTC, Τρ/Τετ/Πεμ 23:00 UTC (cron '0 6 * * *' και '0 23 * * 2,3,4')."""
    c = []
    for d in range(0, 3):
        day = (now - dt.timedelta(days=d)).date()
        c.append(dt.datetime(day.year, day.month, day.day, 6, 0, tzinfo=dt.timezone.utc))
        if day.weekday() in (1, 2, 3):                       # Τριτη, Τεταρτη, Πεμπτη
            c.append(dt.datetime(day.year, day.month, day.day, 23, 0, tzinfo=dt.timezone.utc))
    return max(x for x in c if x <= now)


def _api(path, method='GET', data=None):
    tok = os.environ.get('GH_DISPATCH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GH_REPO') or os.environ.get('GITHUB_REPOSITORY')
    if not tok or not repo:
        return None
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/{path}', method=method,
                                 data=(json.dumps(data).encode() if data is not None else None),
                                 headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    r = urllib.request.urlopen(req, timeout=20).read()
    return json.loads(r) if r else {}


def _runs():
    d = _api(f'actions/workflows/{WF}/runs?per_page=20')
    if d is None:
        return None
    out = []
    for r in d.get('workflow_runs', []):
        out.append(dict(id=r['id'], created=dt.datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')),
                        status=r['status'], conclusion=r.get('conclusion'), event=r.get('event')))
    return out


def dispatch_mode():
    now = dt.datetime.now(dt.timezone.utc); s = last_slot(now)
    if (now - s).total_seconds() / 60 < GRACE_MIN:
        print(f'euro-refresh due: ωρα {s:%d/%m %H:%M} UTC — περιμενω {GRACE_MIN}′'); return
    R = _runs()
    if R is None:
        print('euro-refresh due: χωρις token/repo (τοπικα) — τιποτα'); return
    after = [r for r in R if r['created'] >= s]
    ok = [r for r in after if r['status'] != 'completed' or r['conclusion'] == 'success']
    if ok:
        print(f'euro-refresh due: ωρα {s:%d/%m %H:%M} UTC ✓ (run {ok[0]["id"]} {ok[0]["event"]} {ok[0]["status"]})'); return
    if after and (now - max(r['created'] for r in after)).total_seconds() / 60 < RETRY_FAIL_MIN:
        print(f'euro-refresh due: τελευταιο run μετα τις {s:%H:%M} UTC απετυχε — ξανα σε {RETRY_FAIL_MIN}′'); return
    try:
        _api(f'actions/workflows/{WF}/dispatches', method='POST', data={'ref': 'main'})
        print(f'euro-refresh due: ΖΗΤΗΘΗΚΕ (ωρα {s:%d/%m %H:%M} UTC, καθυστερηση GitHub {int((now - s).total_seconds() / 60)}′)')
    except Exception as e:
        print(f'euro-refresh due: dispatch απετυχε {type(e).__name__}: {e}')


def guard_mode():
    """Γραφει skip=true|false στο GITHUB_OUTPUT. Skip ΜΟΝΟ για αργοπορημενο προγραμματισμενο run που εχει ηδη καλυφθει."""
    skip = False
    try:
        if os.environ.get('GITHUB_EVENT_NAME') == 'schedule':
            now = dt.datetime.now(dt.timezone.utc); s = last_slot(now); me = int(os.environ.get('GITHUB_RUN_ID', '0'))
            R = _runs() or []
            done = [r for r in R if r['id'] != me and r['created'] >= s and (r['status'] != 'completed' or r['conclusion'] == 'success')]
            if done:
                skip = True
                print(f'guard: η ωρα {s:%d/%m %H:%M} UTC καλυφθηκε ηδη απο run {done[0]["id"]} ({done[0]["event"]}) → skip')
    except Exception as e:
        print(f'guard: σφαλμα {type(e).__name__}: {e} → τρεχει κανονικα')
    print(f'skip={str(skip).lower()}')
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a') as fh:
            fh.write(f'skip={str(skip).lower()}\n')


if __name__ == '__main__':
    guard_mode() if '--guard' in sys.argv else dispatch_mode()
