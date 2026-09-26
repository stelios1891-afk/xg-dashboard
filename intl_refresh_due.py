"""
intl_refresh_due.py — ΑΝΑΝΕΩΣΗ ΕΘΝΙΚΩΝ ΑΜΕΣΩΣ ΜΕΤΑ ΤΟ ΤΕΛΟΣ ΚΑΘΕ ΜΑΤΣ (26/9/2026, εντολη Στελιου: «πιο αμεσα απο τις 12»).

Τρεχει σε καθε κυκλο του scanner (~5′). Αν υπαρχει ματς εθνικων (NL A-D) που ξεκινησε πριν απο ≥110′ (90′ + ημιχρονο + καθυστερησεις)
και ΔΕΝ εχει περασει ακομα στο intl_matches.csv → ζηταει (workflow_dispatch) το intl-refresh.yml: FotMob τελικο σκορ/xG/ενδεκαδες →
Elo/xElo (Μ1), αγκυρα (Μ2/Μ3), xG ομαδων, προβολες, dashboard + Telegram με αποτελεσματα και αλλαγες Elo.
Αν το FotMob δεν το εχει κλεισει ακομα (π.χ. παρατασεις), ξαναζηταει καθε 20′ για ως 8 ωρες μετα τη σεντρα.
Οι σταθερες ανανεωσεις 21:30 / 05:30 UTC μενουν ως εφεδρικες. State: intl_refresh_due_state.json.
"""
import os, sys, json, datetime as dt, urllib.request
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
import pandas as pd

ST_F = 'intl_refresh_due_state.json'
AFTER_MIN, UNTIL_H, RETRY_MIN = 110, 8, 20


def due_matches(now):
    try:
        D = json.load(open('intl_projections_dashboard.json', encoding='utf-8'))
        M = pd.read_csv('intl_matches.csv', dtype={'mid': str})
    except Exception:
        return []
    have = {(int(r.hid), int(r.aid), str(r.date)[:10]) for r in M.itertuples()}
    # προγραμμα: dashboard (επερχομενα) + intl_closing.jsonl (καθε ματς γραφεται στη σεντρα — τα αρχισμενα φευγουν απο το dashboard)
    sched = {}
    for c in D.get('comps', []):
        if str(c.get('comp', '')).startswith('NL'):
            for m in c.get('matches', []):
                sched[(int(m['hid']), int(m['aid']), m['utc'][:10])] = (c['comp'], m['home'], m['away'], m['utc'].replace(' ', 'T')[:16])
    try:
        for ln in open('intl_closing.jsonl', encoding='utf-8'):
            r = json.loads(ln)
            if str(r.get('comp', '')).startswith('NL'):
                sched.setdefault((int(r['hid']), int(r['aid']), str(r['ko'])[:10]), (r['comp'], r['home'], r['away'], str(r['ko'])[:16]))
    except Exception:
        pass
    out = []
    for k, (comp, h, a_, utc) in sched.items():
        try:
            ko = dt.datetime.fromisoformat(utc).replace(tzinfo=dt.timezone.utc)
        except Exception:
            continue
        mins = (now - ko).total_seconds() / 60
        if AFTER_MIN <= mins <= UNTIL_H * 60 and k not in have:
            out.append(f"{comp}|{h}|{a_}|{utc}")
    return sorted(out)


def dispatch():
    tok, repo = os.environ.get('GH_DISPATCH_TOKEN'), os.environ.get('GH_REPO')
    if not tok or not repo:
        print('intl refresh due: χωρις GH_DISPATCH_TOKEN/GH_REPO (τοπικα) — δεν ζηταω τιποτα'); return False
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/workflows/intl-refresh.yml/dispatches',
                                 data=json.dumps({'ref': 'main'}).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    try:
        urllib.request.urlopen(req, timeout=20).read(); return True
    except Exception as e:
        print(f'intl refresh due: dispatch απετυχε {type(e).__name__}: {e}'); return False


def main():
    now = dt.datetime.now(dt.timezone.utc)
    due = due_matches(now)
    try:
        st = json.load(open(ST_F, encoding='utf-8'))
    except Exception:
        st = {}
    st = {k: v for k, v in st.items() if k in due}          # καθαρισμα: οσα περασαν πια δεν χρειαζονται
    if not due:
        json.dump(st, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False)
        print('intl refresh due: κανενα τελειωμενο ματς που να λειπει'); return 0
    last = max((dt.datetime.fromisoformat(v) for v in st.values()), default=None)
    if last and (now - last).total_seconds() / 60 < RETRY_MIN:
        print(f'intl refresh due: {len(due)} ματς περιμενουν — ζητηθηκε ηδη {last:%H:%M} UTC, ξανα σε {RETRY_MIN}′'); return 0
    if dispatch():
        for k in due:
            st[k] = now.isoformat(timespec='minutes')
        print(f'intl refresh due: ζητηθηκε ανανεωση για {len(due)} ματς: {due}')
    json.dump(st, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
