# -*- coding: utf-8 -*-
"""nba_injrep_ci_probe.py — ΔΟΚΙΜΗ ΑΠΟ ΤΟ CLOUD (21/10/2026, Στελιος «οκ ξεκινα το»): κατεβαινει η ΕΠΙΣΗΜΗ αναφορα τραυματιων του NBA
(PDF, ak-static.cms.nba.com) απο το GitHub Actions; Ο CDN δινει 403 και για «δεν υπαρχει» και για μπλοκαρισμα → ελεγχος canary.
Καθε 15′ (για ~5ω40′ ανα τρεξιμο): βρισκει την πιο προσφατη αναφορα (μορφη _HH_MMAM/PM, ανα 15′), την κατεβαζει, τη διαβαζει
(nba_injrep_fetch.parse) και γραφει μια γραμμη στο nba_injrep_probe.jsonl: ωρα, αρχειο, καθυστερηση απο την ωρα της αναφορας,
γραμμες, ποσοι Out/Doubtful/Questionable/Probable, μπλοκαρισμα. Λιγα αιτηματα: μονο τα νεα 15λεπτα απο την τελευταια που βρεθηκε.
Σταματα μονο του μετα τις 23/10/2026 12:00 UTC."""
import os, sys, json, time, datetime as dt, urllib.request, urllib.error, tempfile, collections
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
import nba_injrep_fetch as N
ET = ZoneInfo('America/New_York'); END = dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.timezone.utc)
OUT = 'nba_injrep_probe.jsonl'; RUN_S = int(os.environ.get('PROBE_SECONDS', 5 * 3600 + 40 * 60))
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
def url_of(t):
    return N.URL.format(d=t.strftime('%Y-%m-%d'), h=t.strftime('%I_%M%p'))
def head(u):
    try:
        urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers=H), timeout=20); return 200
    except urllib.error.HTTPError as e: return e.code
    except Exception: return -1
def slot(t): return t.replace(minute=(t.minute // 15) * 15, second=0, microsecond=0)
def main():
    t0 = time.time(); last = None; rows_out = []
    while time.time() - t0 < RUN_S and dt.datetime.now(dt.timezone.utc) < END:
        now_utc = dt.datetime.now(dt.timezone.utc); now_et = now_utc.astimezone(ET)
        cands = []; s = slot(now_et)
        lo = last + dt.timedelta(minutes=15) if last else s - dt.timedelta(hours=3)
        while s >= lo: cands.append(s); s -= dt.timedelta(minutes=15)
        found, codes = None, []
        for c in cands:                                   # νεοτερη πρωτα
            code = head(url_of(c)); codes.append(code)
            if code == 200: found = c; break
        rec = dict(t=now_utc.isoformat(timespec='seconds'), et=now_et.strftime('%m/%d %H:%M'), tried=len(cands), codes=collections.Counter(codes) and dict(collections.Counter(codes)))
        if found:
            last = found
            try:
                p = os.path.join(tempfile.gettempdir(), 'probe_rep.pdf')
                r = urllib.request.urlopen(urllib.request.Request(url_of(found), headers=H), timeout=40); open(p, 'wb').write(r.read())
                rows = N.parse(p); st = collections.Counter(x[7] for x in rows)
                rec.update(file=os.path.basename(url_of(found)), lag_min=round((now_et - found).total_seconds() / 60, 1), rows=len(rows), status=dict(st),
                           games=len({x[3] for x in rows}))
            except Exception as e: rec.update(file=os.path.basename(url_of(found)), error=str(e)[:200])
        else:
            rec['blocked'] = N.blocked()
            rec['last_found'] = last.strftime('%m/%d %H:%M') if last else None
        print(json.dumps(rec, ensure_ascii=False), flush=True); rows_out.append(rec)
        with open(OUT, 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        nxt = 15 * 60 - (time.time() - t0) % (15 * 60)
        if time.time() - t0 + nxt >= RUN_S: break
        time.sleep(nxt)
if __name__ == '__main__':
    main()
